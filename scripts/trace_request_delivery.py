"""Exact-build Cloudcell delivery ownership and synthetic ARM64 probes.

Read-only: no modified executable, network, device, or user-save access. The
probes execute original instructions; opaque allocation/blob/lock APIs are
controlled hooks, so this is not a whole-process concurrency or durability test.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from build_4k_v3 import BINARY_PATH, SUPPORTED_MACHO_UUID, macho_uuid
from scripts.audit_sdk_dependencies import MachO

BASE = 0x100000000
WINDOWS = {
    'submit': (0x170B62C, 0x170B7A0, 'f70e14d959148599b793c25e3711bf6bb3b1c6fcac717b7752f5ef9cba3b833d'),
    'cancel': (0x170BEE4, 0x170BFB0, '69f8e189775ad5b7bab459a779608e6548cafee21067e7e72fc8510c538362f8'),
    'dispatch': (0x170B7A0, 0x170B9A4, '0778781dce9d3ab053a41a7c7d5b39d7e34ca17eb76e2c1e69c9bb12446b5a11'),
    'reply': (0x170C07C, 0x170C398, '548d0da81d0df68bbe949d8b9d76882e648c9b8ee89146f437a714f89085b435'),
    'subsync_reply': (0x1725268, 0x17253B0, '072872573f2bd1b00d335cf85b67373613014dcc01e1a7264bb0a4d6d560475d'),
    'http_drain': (0x1732868, 0x1732AA0, 'd0d76d4d24b7316612508fe00f863553d08b3e7d72d4f644ee3801ab6906c8a0'),
    'http_finish': (0x1732C44, 0x1732CF4, '7b5c5481aa9a1f4d96cedbcd793b279e2bbcf72c9133e0b33c6e8ceb7d8be1ad'),
    'http_data': (0x1732B44, 0x1732C44, '71a97adc23c3e1124773d1d3bdbf61c3d9d4ea8e03d691f84cc0e0313f332425'),
    'cloudcell_update_entry': (0x16D1D4C, 0x16D1D70, '8bb00e626f0c7f9d464e29e2490dc0c7b85747f24b48e341b1a61aa04e968eb7'),
    'subsync_create': (0x172516C, 0x17251CC, 'aa5ed66be3a01f224ce77f42cfdae7f4775eeced44b6e8f7ebd187c63da7d335'),
    'atomic_lock': (0x170CE20, 0x170CEB8, 'ae52e9f7ccb7b1ab06a2ca32297a94c5ded337d2947eb58118c78a427331596b'),
    'queue_submit': (0x3E8450, 0x3E86E0, '378f667d9beab3eceb604690c46260934105e676de6b4ec4a2af6bd1e5d9743f'),
    'group_reply': (0x156560, 0x156660, 'f1bf1becb643a79a81e2e482e03d7be7072f1a06e729440c482ba73acf21579f'),
    'entries_reply': (0x156660, 0x156778, '0b85a22bd5b086963f235c8bbc6d53c25a03470c221e224eeaba1ed9b62b38fa'),
    'helper_arm': (0x1564E0, 0x15650C, '5540e4d3f8043fee3a0385a6afe4db1dcb0edbe90d378995e5e80c6e0263b8a2'),
    'helper_launch': (0x1561FC, 0x156560, '1cb45ee632779c09963929f6320c60db0ac1fce4f722b7dc79d76821def2d8ad'),
    'bridge': (0x165494, 0x165634, '1e7ae5e09fd7c2aec529d58170e3f7ddbc2efc08e88ad5e21b88de793106f1e9'),
    'sync_factory': (0x16FD2D0, 0x16FD3B8, '8af66a77682e6a94c3e7e4c76cd2f987bf9479928a71f889146277b8bd9cc6e0'),
    'sync_forwarders': (0x16FD450, 0x16FD4B0, 'c999f5d511379c3d6be72c70c166d252808d2cbb2ab37335db44889fdb718461'),
    'cloudcell_manager_creation': (0x16D09F0, 0x16D0A1C, 'fcb7d98e53bc04f97426d204111b4165174d9f69be3cac8411311bab1e97c113'),
    'cloudcell_getters': (0x16D2300, 0x16D2310, 'b6d6c457b2637657eda41a2bc842783dc0dd32885b9fd8b0a9237df9b611c354'),
}
VTABLES = {
    'cloudcell': (0x102C5E038, 'N2cc9CloudcellE',
                   {0x18: 0x1016D2300, 0x20: 0x1016D2308, 0x120: 0x1016D1D4C}),
    'sync_wrapper': (0x102C60B80, 'N2cc4sync11SyncManagerE',
                     {0x10: 0x1016FD468, 0x20: 0x1016FD480, 0x28: 0x1016FD498}),
    'sync_v34': (0x102C61E10, 'N2cc4sync10ManagerV34E',
                 {0x10: 0x10170B62C, 0x20: 0x10170B7A0, 0x28: 0x10170BEE4}),
    'http': (0x102C64B98, 'N2cc18HttpRequestManagerE', {0x18: 0x101731C54, 0x78: 0x101732868}),
}


def validate(binary):
    if macho_uuid(binary) != SUPPORTED_MACHO_UUID:
        raise ValueError('Unsupported executable UUID')
    for name, (start, end, checksum) in WINDOWS.items():
        if hashlib.sha256(binary[start:end]).hexdigest() != checksum:
            raise ValueError('Changed original ' + name + ' instructions')
    image = MachO(binary)
    for name, (address, expected, slots) in VTABLES.items():
        typeinfo = image.vm_pointer(address - 8)
        if image.vm_string(image.vm_pointer(typeinfo + 8)) != expected:
            raise ValueError('Changed ' + name + ' RTTI')
        if any(image.vm_pointer(address + slot) != target for slot, target in slots.items()):
            raise ValueError('Changed ' + name + ' vtable')


def trace(binary):
    validate(binary)
    return {
        'scope': 'Exact-build static ownership plus optional original-instruction probes; no runtime performance claim',
        'executable_uuid': SUPPORTED_MACHO_UUID.hex(),
        'interface': 'Cloudcell +0x18 getter returns sync manager member +0x1c8, not the HTTP manager',
        'factory': 'SyncManager wrapper +0x10 forwards to concrete ManagerV34; factory 0x1016fd2d0 supports protocol 34',
        'vtables': {name: {'address': hex(address), 'rtti': label,
                           'slots': {hex(slot): hex(target) for slot, target in slots.items()}}
                    for name, (address, label, slots) in VTABLES.items()},
        'queue_operation': {'id': '0x28d3', 'second_word': '0x1345', 'serialization': '0x1003e8450',
                            'snapshot': 'Payload serialized before virtual submission; reply still targets live queue'},
        'sync_state': {'record_size': '0x50', 'pending_vector': '+0x18', 'active_vector': '+0x30',
                       'record_id': '+0x20', 'callback': '+0x28 (target pointer +0x40)',
                       'delivered': '+0x48', 'abandoned': '+0x49', 'http_id': '+0xa8',
                       'lock': '+0x10 atomic byte', 'rejection_set': '+0x48'},
        'delivery': {'worker_data': '0x101732b44 buffers bytes under HTTP mutex',
                     'worker_finish': '0x101732c44 marks completed +0xc8 under HTTP mutex',
                     'drain': '0x1016d1d4c calls HTTP +0x78, 0x101732868 delivers completion after unlocking',
                     'sync_reply': '0x10170c07c detaches active vector before per-record callbacks',
                     'thread_limit': 'Delivery inherits Cloudcell update caller; exact OS/main-thread identity not proved'},
        'synchronous_exception': {'site': '0x10170b678',
                                  'condition': 'Operation found in manager rejection set',
                                  'effect': 'Immediate empty callback under sync lock, return ID zero, no append',
                                  'source': 'Set populated from successful response at 0x10170c2b0..0x10170c320',
                                  'reachability': 'No captured server response proves a relevant operation is rejected'},
        'tournament_exception': {'group_operation': '0x28f4', 'entries_operation': '0x28ed',
                                 'sequence': 'Early empty responses while pending=0 set flags/error; post-launch arm resets them and sets pending=1',
                                 'limit': 'Conditional sequencing hazard, not a demonstrated offline failure or safe patch'},
        'cancellation': 'ID lookup in pending and active vectors marks abandoned and clears callback; does not cancel shared HTTP',
        'retry': 'Failed batch delivers empty records and retires active vector; next dispatch considers pending, no failed-record requeue in this handler',
        'durability': 'No durable generation or safe skip-write invariant established; no behavioral patch',
        'limits': ['No device/network/user-save access or timing measurements.',
                   'No universal deferred-callback or main-thread guarantee.',
                   'No transport/platform-wide absence-of-retry claim.',
                   'Manager locks do not prove the live game result queue is immutable during flight.'],
    }


class _Machine:
    """Minimal private harness; all saves, records and closures are synthetic."""
    def __init__(self, binary):
        from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
        import unicorn.arm64_const as registers
        self.regs = registers
        self.uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self.pages, self.hooks, self.calls = set(), {}, []
        self.data = 0x700000000
        self.stack = 0x710000000
        self.finish = self.data + 0xF000
        self.map(self.data, 0x10000)
        self.map(self.stack, 0x10000)
        self.map(0x1032EB000)
        self.map(0x102B56000)
        self.put(0x102B56A20, '<Q', self.data + 0xE000)
        self.put(self.data + 0xE000, '<Q', 0x12345678)
        for start, end, _ in WINDOWS.values():
            self.map(BASE + start, end - start)
            self.uc.mem_write(BASE + start, binary[start:end])
        self.uc.hook_add(UC_HOOK_CODE, self._hook)
        self.uc.reg_write(registers.UC_ARM64_REG_SP, self.stack + 0xF000)

    def map(self, address, length=1):
        for page in range(address & ~4095, (address + length + 4095) & ~4095, 4096):
            if page not in self.pages:
                self.uc.mem_map(page, 4096)
                self.pages.add(page)

    def put(self, address, fmt, *values):
        self.uc.mem_write(address, struct.pack(fmt, *values))

    def get(self, address, fmt='<Q'):
        return struct.unpack(fmt, self.uc.mem_read(address, struct.calcsize(fmt)))[0]

    def x(self, index):
        return self.uc.reg_read(getattr(self.regs, 'UC_ARM64_REG_X' + str(index)))

    def result(self, value):
        self.uc.reg_write(self.regs.UC_ARM64_REG_X0, value)

    def stub(self, address, name, callback=None):
        self.map(address)
        self.uc.mem_write(address, bytes.fromhex('c0035fd6'))
        self.hooks[address] = (name, callback)

    def _hook(self, uc, address, size, _):
        if address not in self.hooks:
            return
        name, callback = self.hooks[address]
        self.calls.append(name)
        if callback:
            callback(self)
        uc.reg_write(self.regs.UC_ARM64_REG_PC, self.x(30))

    def run(self, address, *arguments):
        for index, value in enumerate(arguments):
            self.uc.reg_write(getattr(self.regs, 'UC_ARM64_REG_X' + str(index)), value)
        self.uc.reg_write(self.regs.UC_ARM64_REG_X30, self.finish)
        self.uc.emu_start(address, self.finish, count=10000)
        if self.uc.reg_read(self.regs.UC_ARM64_REG_PC) != self.finish:
            raise RuntimeError('Probe instruction budget exhausted')
        return self.x(0)


def probe_submit(binary, *, rejected=False):
    """A pending append remains possible with a synthetic active HTTP batch."""
    validate(binary)
    if type(rejected) is not bool:
        raise ValueError('rejected must be a boolean')
    m = _Machine(binary)
    manager, pending, active, blob, closure, target, vtable = [m.data + i * 0x100 for i in range(1, 8)]
    m.put(manager + 0x18, '<QQQ', pending, pending, pending + 0xA0)
    m.put(manager + 0x30, '<QQQ', active, active + 0x50, active + 0x50)
    m.put(manager + 0xA8, '<Q', 77)
    m.put(closure + 0x18, '<Q', target)
    m.put(target, '<Q', vtable)
    m.put(vtable + 0x30, '<Q', m.data + 0xD000)
    callbacks = []

    def lock(machine):
        machine.put(machine.x(0), '<Q', machine.x(1))
        machine.put(machine.x(1), '<B', 1)

    def blob_init(machine):
        machine.put(machine.x(0), '<QQQ', 0, 0, 0)

    def blob_copy(machine):
        machine.uc.mem_write(machine.x(0), bytes(machine.uc.mem_read(machine.x(1), 24)))

    def move_callback(machine):
        machine.put(machine.x(0) + 0x18, '<Q', machine.get(machine.x(1) + 0x18))
        machine.put(machine.x(1) + 0x18, '<Q', 0)

    def delivered(machine):
        callbacks.append({'sync_lock_held': bool(machine.get(manager + 0x10, '<B')),
                          'blob_pointer': machine.get(machine.x(1))})

    m.stub(0x10170CE20, 'lock', lock)
    m.stub(0x10170CEB8, 'rejection_lookup', lambda machine: machine.result(int(rejected)))
    m.stub(0x101725A04, 'blob_init', blob_init)
    m.stub(0x101725A74, 'blob_copy', blob_copy)
    m.stub(0x1017253B0, 'move_callback', move_callback)
    for address in (0x101725A78, 0x101725AA4, 0x101713AD8):
        m.stub(address, 'opaque_cleanup_or_log')
    m.stub(m.data + 0xD000, 'user_callback', delivered)
    request_id = m.run(0x10170B62C, manager, blob, 0x28D3, 0x1345, closure)
    return {'rejected': rejected, 'request_id': request_id, 'callbacks': callbacks,
            'pending_records': (m.get(manager + 0x20) - pending) // 0x50,
            'active_records': (m.get(manager + 0x38) - active) // 0x50,
            'active_http_id': m.get(manager + 0xA8),
            'sync_lock_after': m.get(manager + 0x10, '<B')}


def probe_cancel(binary, *, location='active', matching=True):
    validate(binary)
    if location not in ('pending', 'active') or type(matching) is not bool:
        raise ValueError('Expected pending/active location and boolean matching')
    m = _Machine(binary)
    manager, record, closure, vtable = [m.data + i * 0x100 for i in range(1, 5)]
    vector = 0x18 if location == 'pending' else 0x30
    m.put(manager + vector, '<QQQ', record, record + 0x50, record + 0x50)
    m.put(manager + 0xA8, '<Q', 77)
    m.put(record + 0x20, '<I', 42)
    m.put(record + 0x40, '<Q', closure)
    m.put(closure, '<Q', vtable)
    m.put(vtable + 0x28, '<Q', m.data + 0xD000)
    m.stub(0x10170CE20, 'lock', lambda machine: machine.put(machine.x(0), '<Q', machine.x(1)))
    m.stub(m.data + 0xD000, 'destroy_closure')
    m.run(0x10170BEE4, manager, 42 if matching else 43)
    return {'location': location, 'matching': matching,
            'abandoned': m.get(record + 0x49, '<B'),
            'callback_retained': bool(m.get(record + 0x40)),
            'active_http_id': m.get(manager + 0xA8),
            'closure_destructions': m.calls.count('destroy_closure')}


def probe_http_drain(binary, *, completed=True, callback_present=True):
    validate(binary)
    if type(completed) is not bool or type(callback_present) is not bool:
        raise ValueError('Expected boolean HTTP states')
    m = _Machine(binary)
    manager, vector, request, data = [m.data + i * 0x200 for i in range(1, 5)]
    m.put(manager + 0x38, '<QQQ', vector, vector + 8, vector + 8)
    m.put(vector, '<Q', request)
    m.put(request, '<Q', 77)
    m.put(request + 0xC8, '<B', int(completed))
    m.put(request + 0xD4, '<I', 4)
    m.put(request + 0xD8, '<Q', data)
    m.put(request + 0xF8, '<Q', m.data + 0xD000 if callback_present else 0)
    callbacks, held = [], [False]
    m.stub(0x1017248D4, 'try_lock', lambda machine: (held.__setitem__(0, True), machine.result(1)))
    m.stub(0x1017248F4, 'lock', lambda machine: held.__setitem__(0, True))
    m.stub(0x1017248FC, 'unlock', lambda machine: held.__setitem__(0, False))

    def delivered(machine):
        callbacks.append({'http_lock_held': held[0], 'http_id': machine.x(3),
                          'bytes': machine.x(2), 'buffer': machine.x(1) == data,
                          'delivery_claimed': m.get(request + 0xC9, '<B')})

    m.stub(0x101732A58, 'completed_callback', delivered)
    m.stub(0x1017319A8, 'destroy_request')
    m.stub(0x102270F08, 'free_request')
    m.run(0x101732868, manager)
    after_first = len(callbacks)
    m.run(0x101732868, manager)
    return {'completed': completed, 'callback_present': callback_present,
            'callbacks': callbacks, 'first_delivery_count': after_first,
            'after_second_drain_count': len(callbacks),
            'remaining_requests': (m.get(manager + 0x40) - vector) // 8,
            'request_destructions': m.calls.count('destroy_request')}


def probe_helper_early_responses(binary, *, early='both'):
    """Original empty helper callbacks followed by its original post-launch arm.

    This supplies hypothetical early callbacks. It does not prove that either
    operation is present in a real server-derived rejection set.
    """
    validate(binary)
    if early not in ('group', 'entries', 'both'):
        raise ValueError('Expected group, entries or both')
    m = _Machine(binary)
    helper, closure, vtable = [m.data + i * 0x200 for i in range(1, 4)]
    m.put(helper + 0x28, '<Q', closure)
    m.put(closure, '<Q', vtable)
    m.put(vtable + 0x30, '<Q', m.data + 0xD000)
    m.stub(m.data + 0xD000, 'helper_completion')
    if early in ('group', 'both'):
        m.run(0x100156560, helper, 0)
    if early in ('entries', 'both'):
        m.run(0x100156660, helper, 0)

    def state():
        return {'pending': m.get(helper + 0xFC, '<B'),
                'group_received': m.get(helper + 0x104, '<B'),
                'entries_received': m.get(helper + 0x105, '<B'),
                'error': m.get(helper + 0x106, '<B')}

    before = state()
    constant = 0x10234C9F0
    m.map(constant, 16)
    image = MachO(binary)
    m.uc.mem_write(constant, binary[image.vm_offset(constant):image.vm_offset(constant) + 16])
    m.uc.reg_write(m.regs.UC_ARM64_REG_X19, helper)
    m.uc.reg_write(m.regs.UC_ARM64_REG_X20, 123)
    m.uc.reg_write(m.regs.UC_ARM64_REG_X27, 0xFFFFFFFF)
    m.uc.emu_start(0x1001564E0, 0x10015650C, count=64)
    return {'injected_early_callbacks': early, 'before_post_launch_arm': before,
            'after_post_launch_arm': state(),
            'completion_calls': m.calls.count('helper_completion'),
            'limit': 'Conditional synthetic scheduling, no real rejection-set contents supplied'}


def probe_failed_batch(binary):
    """Original sync response and per-record empty completion, opaque HTTP APIs."""
    validate(binary)
    m = _Machine(binary)
    manager, pending, active, closure, cvt, mvt, cloudcell, http, hvt = [
        m.data + i * 0x200 for i in range(1, 10)]
    m.put(manager, '<Q', mvt)
    m.put(mvt + 0x20, '<Q', m.data + 0xD010)
    m.put(manager + 0x18, '<QQQ', pending, pending + 0x50, pending + 0x50)
    m.put(manager + 0x30, '<QQQ', active, active + 0x50, active + 0x50)
    m.put(manager + 0xA8, '<Q', 77)
    m.put(active + 0x40, '<Q', closure)
    m.put(closure, '<Q', cvt)
    m.put(cvt + 0x30, '<Q', m.data + 0xD008)
    m.map(0x103287FF0, 8)
    m.put(0x103287FF0, '<Q', cloudcell)
    m.put(cloudcell, '<Q', cvt)
    m.put(cvt + 0x20, '<Q', m.data + 0xD000)
    m.put(http, '<Q', hvt)
    m.put(hvt + 0x20, '<Q', m.data + 0xD018)
    deliveries, dispatches = [], []

    def zero_blob(machine):
        machine.put(machine.x(0), '<QQQ', 0, 0, 0)

    def completed(machine):
        deliveries.append({'empty_blob': machine.get(machine.x(1)) == 0,
                           'active_records': (machine.get(manager + 0x38) - machine.get(manager + 0x30)) // 0x50})

    def dispatch(machine):
        dispatches.append({'pending_records': (machine.get(manager + 0x20) - pending) // 0x50,
                           'active_http_id': machine.get(manager + 0xA8)})

    m.stub(0x10170CE20, 'lock', lambda machine: machine.put(machine.x(0), '<Q', machine.x(1)))
    m.stub(0x101725874, 'response_blob', zero_blob)
    m.stub(0x101725A04, 'empty_blob', zero_blob)
    m.stub(0x101725D80, 'remaining_blob_bytes', lambda machine: machine.result(0))
    for address in (0x101713AD8, 0x101725AA4, 0x101725A78, 0x10170CD68):
        m.stub(address, 'opaque_cleanup_or_log')
    m.stub(m.data + 0xD000, 'http_getter', lambda machine: machine.result(http))
    m.stub(m.data + 0xD018, 'http_status', lambda machine: machine.result(500))
    m.stub(m.data + 0xD008, 'record_callback', completed)
    m.stub(m.data + 0xD010, 'next_dispatch', dispatch)
    m.run(0x10170C07C, manager, 0, 0, 77)
    return {'deliveries': deliveries, 'next_dispatch_calls': dispatches,
            'pending_records': (m.get(manager + 0x20) - pending) // 0x50,
            'active_records': (m.get(manager + 0x38) - m.get(manager + 0x30)) // 0x50,
            'old_record_delivered': m.get(active + 0x48, '<B'),
            'limit': 'No failed-record requeue in this response path; next dispatch is a hook'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', type=Path, help='Write JSON report, refusing overwrite')
    parser.add_argument('--emulate', action='store_true')
    args = parser.parse_args()
    if zipfile.is_zipfile(args.input):
        with zipfile.ZipFile(args.input) as archive:
            binary = archive.read(BINARY_PATH)
    else:
        binary = args.input.read_bytes()
    report = trace(binary)
    if args.emulate:
        report['probes'] = {
            'accepted_during_flight': probe_submit(binary),
            'conditional_synchronous_rejection': probe_submit(binary, rejected=True),
            'cancel_pending': probe_cancel(binary, location='pending'),
            'cancel_active': probe_cancel(binary),
            'cancel_unknown': probe_cancel(binary, matching=False),
            'http_pending': probe_http_drain(binary, completed=False),
            'http_completed': probe_http_drain(binary),
            'http_abandoned': probe_http_drain(binary, callback_present=False),
            'helper_early_empty_responses': probe_helper_early_responses(binary),
            'failed_batch': probe_failed_batch(binary),
        }
    output = json.dumps(report, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(output)
    print(output, end='')


if __name__ == '__main__':
    main()
