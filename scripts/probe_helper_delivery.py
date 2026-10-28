"""Exact-build experimental two-phase helper delivery; never writes an IPA.

Start timing, payloads, allocation and UI APIs are synthetic. The original
screen/helper constructors, helper callbacks and timer execute in Unicorn.
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
from build_4k_v3 import BINARY_PATH
from scripts.audit_sdk_dependencies import MachO
from scripts.probe_inline_rejection import validate as validate_inline, patch_fresh_zero_store, _branch
from scripts.trace_request_delivery import BASE, _Machine
from scripts.trace_postrace import validate_timer

CAVE = 0x3A00
CAVE_SIZE = 80
# Filled from the exact read-only executable, independently checked in tests.
WINDOWS = {
    'helper_config': (0x15616c, 0x1561fc, '9b2226d34dfb84e9894c26e8c8f044563033181ddaa06c8975af8a80f3b0dcd3'),
    'helper_constructor': (0x155ef4, 0x156020, 'f46e740894c3fed43f13dbf41b6da706c9d7746830bdf19ef3997717508de88b'),
    'helper_cleanup': (0x156020, 0x156168, 'b682450d1da521c7dd4d5696e4b2eac83e35f37c110b3b76be0379100c622571'),
    'screen_constructor': (0x3e4f5c, 0x3e5150, '48a607e4e02c39598ec99cc0e2fbde0b7dfa89921ec5eba412af8169228b6ab2'),
    'completion_invoker': (0x3e7250, 0x3e7278, '5a8ac75d0255724902e916ca7dc74fbda8df6d7a429b203330ed3ed0ddc7dfa0'),
    'timer': (0x1567b4, 0x156804, '36a0ed5712d0a805fa1cce2db7951b47948d6df5a89186b3bb6007710f5de7ed'),
}


def validate(binary):
    validate_inline(binary)
    validate_timer(binary)
    for name, (start, end, digest) in WINDOWS.items():
        if hashlib.sha256(binary[start:end]).hexdigest() != digest:
            raise ValueError('Changed original ' + name + ' instructions')
    image = MachO(binary)
    for address, target in ((0x102BAE588, 0x1003E71E8), (0x102BAE598, 0x1003E7248),
                            (0x102BAE5A0, 0x1003E724C), (0x102BAE5A8, 0x1003E7250),
                            (0x102B60920, 0x100165494), (0x102B60990, 0x100165494)):
        if image.vm_pointer(address) != target:
            raise ValueError('Changed helper ownership/completion vtable')


def _adrp(register, pc, address):
    delta = (address >> 12) - (pc >> 12)
    if not -(1 << 20) <= delta < (1 << 20):
        raise ValueError('ADRP out of range')
    return 0x90000000 | ((delta & 3) << 29) | (((delta >> 2) & 0x7FFFF) << 5) | register


def _conditional(source, target, condition):
    delta = target - source
    if delta % 4 or not -(1 << 20) <= delta < (1 << 20):
        raise ValueError('Conditional branch out of range')
    return 0x54000000 | (((delta // 4) & 0x7FFFF) << 5) | condition


def patch_helper_delivery(binary, *, include_fresh_id_guard=False):
    """Validate original first; return reversible in-memory candidate/plan.

    No extra helper field, callback during launch, ABI register latch or changed
    timeout threshold is needed. Existing pending is the one-shot ownership bit.
    """
    if type(include_fresh_id_guard) is not bool:
        raise ValueError('Guard option must be boolean')
    validate(binary)
    # Reuse the independently guarded padding and executable-mapping checks,
    # then verify the separate helper cave against the same bounds.
    fresh, fresh_plan = patch_fresh_zero_store(binary)
    if not (int(fresh_plan['header_command_end'], 16) <= CAVE
            and CAVE + CAVE_SIZE <= int(fresh_plan['first_section_offset'], 16)
            and CAVE >= 0x3920 and CAVE + CAVE_SIZE <= 0x4000):
        raise ValueError('Helper cave is outside executable header padding')
    if any(binary[CAVE:CAVE + CAVE_SIZE]):
        raise ValueError('Helper cave is not zero')
    position, mapped = 32, False
    for _ in range(struct.unpack_from('<I', binary, 16)[0]):
        command, size = struct.unpack_from('<II', binary, position)
        if command == 0x19 and binary[position + 8:position + 24].rstrip(b'\0') == b'__TEXT':
            vm, virtual_size, offset, file_size, _, initprot = struct.unpack_from('<QQQQii', binary, position + 24)
            mapped = (vm == BASE and offset == 0 and bool(initprot & 4)
                      and CAVE + CAVE_SIZE <= min(virtual_size, file_size))
        position += size
    if not mapped:
        raise ValueError('Helper cave lacks executable file-backed mapping')
    word = lambda offset: struct.unpack_from('<I', binary, offset)[0]
    words = [word(0x1562BC), word(0x1564EC), word(0x1564F0), word(0x1564F4),
             _adrp(8, BASE + CAVE + 16, 0x10234C000), word(0x1564FC), word(0x156500),
             0x12800008, 0xB900FA68, _branch(CAVE + 36, 0x1562C0)]
    # Error bit -> existing clear-pending/closure tail; otherwise both exact
    # received bytes must equal one. Ordinary incomplete path resumes timer.
    words += [0x36000048, _branch(CAVE + 44, 0x1567E8),
              0x39441008, 0x7100051F, _conditional(CAVE + 56, CAVE + 76, 1),
              0x39441408, 0x7100051F, _conditional(CAVE + 68, CAVE + 76, 1),
              _branch(CAVE + 72, 0x1567E8), _branch(CAVE + 76, 0x1567C8)]
    cave_bytes = struct.pack('<' + 'I' * len(words), *words)
    size = len(cave_bytes)
    if size != CAVE_SIZE:
        raise AssertionError('Helper cave size changed without updating guards')
    output = bytearray(fresh if include_fresh_id_guard else binary)
    changes = []
    replacements = [(0x1562BC, struct.pack('<I', _branch(0x1562BC, CAVE))),
                    (0x1564EC, struct.pack('<7I', *([0xD503201F] * 7))),
                    (0x1567C4, struct.pack('<I', _branch(0x1567C4, CAVE + 40))),
                    (CAVE, cave_bytes)]
    for offset, replacement in replacements:
        changes.append({'file_offset': hex(offset), 'original': binary[offset:offset + len(replacement)].hex(),
                        'replacement': replacement.hex()})
        output[offset:offset + len(replacement)] = replacement
    if include_fresh_id_guard:
        changes += fresh_plan['changes']
    return bytes(output), {'experimental': True, 'device_validated': False,
                           'scope': 'Initialize before Start; latch while pending=0; consume at ordinary update',
                           'changes': changes, 'includes_fresh_id_guard': include_fresh_id_guard,
                           'cave_size': size, 'requires_resigning_if_packaged': True,
                           'limits': ['Synthetic callback timing and payloads', 'Server rejection reachability unknown',
                                      'Header-padding execution requires platform validation',
                                      'No cross-thread callback/cancellation guarantee']}


def probe(binary, *, early=(), late=(), candidate=False, ticks=1, cancel=False, updates=2):
    """Run actual constructors and callbacks, with synthetic Start delivery.

    Events are (group|entries, success|error). An early callback is run inside
    the Start hook with a synthetic manager-lock flag; late callbacks occur
    only after the full screen constructor returns. Copy/parser APIs are hooks.
    """
    validate(binary)
    early, late = tuple(early), tuple(late)
    events = early + late
    if any(tuple(item) not in ((a, b) for a in ('group', 'entries') for b in ('success', 'error'))
           for item in events):
        raise ValueError('Invalid synthetic response')
    if len({item[0] for item in early}) != len(early):
        raise ValueError('At most one early response per Start')
    if any(type(value) is not bool for value in (candidate, cancel)) or type(ticks) is not int or not 0 <= ticks <= 0x7FFFFFFF or type(updates) is not int or not 0 <= updates <= 10:
        raise ValueError('Invalid probe option')
    execution = patch_helper_delivery(binary)[0] if candidate else binary
    m = _Machine(execution)
    image = MachO(binary)
    for start, end, _ in WINDOWS.values():
        m.map(BASE + start, end - start)
        m.uc.mem_write(BASE + start, execution[start:end])
    m.map(0x100154DA8)
    m.map(0x100153724)
    m.map(BASE + CAVE, 128)
    m.uc.mem_write(BASE + CAVE, execution[CAVE:CAVE + 128])
    screen, parameters, ids = m.data + 0x200, m.data + 0x600, m.data + 0x800
    m.uc.mem_write(screen, bytes([0xA5]) * 0x2A8)
    m.put(parameters, '<I', 7)
    m.put(parameters + 8, '<QQQ', ids, ids + 4, ids + 4)
    m.put(ids, '<I', 1234)
    for address, length in ((0x10234C9F0, 32), (0x10237AA70, 8),
                            (0x102BAE578, 0x38), (0x102B60900, 0x38),
                            (0x102B60970, 0x38)):
        m.map(address, length)
        m.uc.mem_write(address, binary[image.vm_offset(address):image.vm_offset(address) + length])
    m.map(0x1031D10F8)
    m.map(0x103287FF0)
    cloud, cloud_vt = m.data + 0xA00, m.data + 0xB00
    m.put(0x103287FF0, '<Q', cloud)
    m.put(cloud, '<Q', cloud_vt)
    m.put(cloud_vt + 0x18, '<Q', m.data + 0xE010)
    next_allocation = [m.data + 0x2000]
    allocations, completions, starts, snapshots, cancelled = [], [], [], [], []
    context = {'ready': False, 'lock': False}

    def allocate(machine):
        size = machine.x(0)
        address = next_allocation[0]
        next_allocation[0] += 0x200
        machine.uc.mem_write(address, bytes([0xA5]) * max(size, 0x110))
        allocations.append({'address': address, 'size': size})
        machine.result(address)

    def copy(machine):
        machine.uc.mem_write(machine.x(0), bytes(machine.uc.mem_read(machine.x(1), machine.x(2))))

    def clone(machine):
        source = machine.x(0)
        machine.result(0x20)
        allocate(machine)
        machine.uc.mem_write(machine.x(0), bytes(machine.uc.mem_read(source, 0x20)))

    def state():
        helper = m.get(screen + 0x298)
        return {'pending': m.get(helper + 0xFC, '<B'), 'group': m.get(helper + 0x104, '<B'),
                'entries': m.get(helper + 0x105, '<B'), 'error': m.get(helper + 0x106, '<B'),
                'elapsed': m.get(helper + 0x108, '<I'),
                'rank_bytes': bytes(m.uc.mem_read(helper + 0xE8, 20)).hex()}

    def complete(machine):
        completions.append({'ready': context['ready'], 'lock': context['lock'],
                            'screen_argument': hex(machine.x(0)), 'state': state(),
                            'screen_done': m.get(screen + 0x264, '<B')})

    for address in (0x10029E34C, 0x10029E568, 0x100485AE4, 0x100537AE0, 0x100537B54,
                    0x100044098, 0x10002ED1C, 0x1001579A0, 0x10007CBF8, 0x1022725AC):
        m.stub(address, 'opaque_base_ui_or_copy')
    m.stub(0x1022725AC, 'memcmp', lambda machine: machine.result(0))
    m.stub(0x102270F2C, 'new_sentinel', allocate)
    m.stub(0x102270F08, 'delete')
    m.stub(0x1022725B8, 'memcpy', copy)
    m.stub(0x1022737B8, 'time', lambda machine: machine.result(123))
    m.stub(m.data + 0xE010, 'sync_getter', lambda machine: machine.result(cloud))
    m.stub(0x1003E71E8, 'clone_completion', clone)
    for address in (0x1003E7248, 0x1003E724C):
        m.stub(address, 'destroy_completion')
    m.stub(0x1003E6F78, 'aggregate_callback_entry', complete)
    m.stub(0x100165494, 'abandon', lambda machine: cancelled.append(hex(machine.x(0))))
    # Payloads have empty owned vectors. The entries response has one synthetic
    # rank record, so original arithmetic writes distinctive E8..F8 result data.
    group_payload, entries_payload, record = m.data + 0x1000, m.data + 0x1100, m.data + 0x1200
    m.put(group_payload, '<Q', 77)
    m.put(entries_payload, '<iff', 0, 2.0, 3.0)
    m.put(entries_payload + 0x18, '<QQQ', record, record + 0xC8, record + 0xC8)
    m.put(record + 0x84, '<ff', 8.0, 9.0)
    from unicorn import UC_HOOK_CODE

    def observe(uc, address, size, _):
        if address == 0x1001562BC:
            snapshots.append({'event': 'prelaunch', 'state': state()})
        if address in (0x100154DA8, 0x100153724):
            name = 'group' if address == 0x100154DA8 else 'entries'
            helper = m.get(screen + 0x298)
            starts.append({'name': name, 'pending': m.get(helper + 0xFC, '<B'), 'ready': context['ready']})
            response = next((kind for which, kind in early if which == name), None)
            if response:
                context['lock'] = True
                uc.reg_write(m.regs.UC_ARM64_REG_X0, helper)
                uc.reg_write(m.regs.UC_ARM64_REG_X1, 0 if response == 'error' else (group_payload if name == 'group' else entries_payload))
                uc.reg_write(m.regs.UC_ARM64_REG_PC, 0x100156560 if name == 'group' else 0x100156660)
            else:
                uc.reg_write(m.regs.UC_ARM64_REG_PC, m.x(30))
        if address in (0x1001563D8, 0x1001564E0):
            context['lock'] = False
        if address == 0x1001564E0:
            snapshots.append({'event': 'before_arm', 'state': state()})

    m.uc.hook_add(UC_HOOK_CODE, observe)
    for index in range(19, 30):
        m.uc.reg_write(getattr(m.regs, 'UC_ARM64_REG_X' + str(index)), 0xABCD0000 + index)
    for index in range(8, 16):
        m.uc.reg_write(getattr(m.regs, 'UC_ARM64_REG_D' + str(index)), 0xFEDC0000 + index)
    try:
        m.run(0x1003E4F5C, screen, parameters, 0, 0)
    except Exception as error:
        raise RuntimeError('Stopped at ' + hex(m.uc.reg_read(m.regs.UC_ARM64_REG_PC)) + repr(m.calls[-12:])) from error
    context['ready'] = True
    constructed = state()
    constructor_registers = [m.x(index) for index in range(19, 30)]
    helper = m.get(screen + 0x298)
    for name, kind in late:
        m.run(0x100156560 if name == 'group' else 0x100156660, helper,
              0 if kind == 'error' else (group_payload if name == 'group' else entries_payload))
    if cancel:
        m.run(0x100156020, helper)
    for _ in range(updates):
        m.run(0x1001567B4, helper, ticks)
    return {'candidate': candidate, 'constructed': constructed, 'final': state(),
            'starts': starts, 'snapshots': snapshots, 'completions': completions,
            'cancelled': cancelled, 'constructor_registers': constructor_registers,
            'final_registers': [m.x(index) for index in range(19, 30)],
            'preserved_d': [m.uc.reg_read(getattr(m.regs, 'UC_ARM64_REG_D' + str(index))) for index in range(8, 16)],
            'screen_done': m.get(screen + 0x264, '<B'), 'sp': m.uc.reg_read(m.regs.UC_ARM64_REG_SP),
            'limits': 'Synthetic Start timing/payloads and opaque UI/copy hooks; no server/thread/device claim'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--experimental-helper-delivery', action='store_true')
    parser.add_argument('--include-fresh-id-guard', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.include_fresh_id_guard and not args.experimental_helper_delivery:
        parser.error('fresh-ID combination requires experimental helper mode')
    if zipfile.is_zipfile(args.input):
        with zipfile.ZipFile(args.input) as archive:
            binary = archive.read(BINARY_PATH)
    else:
        binary = args.input.read_bytes()
    report = {'baseline': probe(binary, early=(('group', 'error'),))}
    if args.experimental_helper_delivery:
        report['plan'] = patch_helper_delivery(binary, include_fresh_id_guard=args.include_fresh_id_guard)[1]
        report['candidate'] = probe(binary, early=(('group', 'error'),), candidate=True)
    output = json.dumps(report, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(output)
    print(output, end='')


if __name__ == '__main__':
    main()
