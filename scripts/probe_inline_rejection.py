"""Conditional rejection lifetime probe using original ARM64 instruction windows.

All objects, allocation and server rejection decisions are synthetic. This does
not establish real rejection-set contents or explain an observed device failure.
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
from scripts.trace_request_delivery import BASE, _Machine, validate as validate_delivery

# Bounded response windows include every instruction executed by empty replies;
# the successful response parsers between those windows are deliberately absent.
WINDOWS = {
    'entries_start': (0x153724, 0x153958, 'f226d9c4af33078e53f61acced6157e044afacbe8f42c19e4788dce24c8eb72c'),
    'group_start': (0x154DA8, 0x154E78, 'f56daa9c595f86cf8c000b953a5cd4a76cead64d942dd3a694d38265077dfd00'),
    'entries_response_entry': (0x153A6C, 0x153AD0, 'b47cc6f81916e81858cf805eecf9b626b58aae2e2d3fe63c4fc485bd25ae8598'),
    'entries_empty_response': (0x15448C, 0x1544B0, 'dbb99949a898d3ff560889d101cc20fe4d034a201dd917ba1ca2c737c9c5205d'),
    'entries_response_return': (0x154534, 0x154554, '54584dc986e7db7c705ab2c35374bd23218d2aef12efa6415c843fca8906e441'),
    'group_response_entry': (0x154F5C, 0x154FC0, 'a0c02b4451ef8324c9063ec987bfa3f84b22f8ce828c10a2680854d5d255a9ff'),
    'group_empty_response': (0x155138, 0x155158, '33b6a0aae02ed47c2d100d8f4dd48e791b40c6cd9141709709a03a415d1daf9c'),
    'group_response_return': (0x1552B8, 0x1552D8, '4ba78b4d33f7d40f3bb472c24215531df8079d573c295a4d9a3ad4a19185e240'),
    'entries_deleting_destructor': (0x15742C, 0x157494, 'dbf801a974aed62f6352a3c465ce40eb723c86b38c2a70501fbe4d49968529a9'),
    'group_deleting_destructor': (0x1575AC, 0x157614, 'c344b587f91011d9309c71362a2f08b552c9df835e8336ff7734047c0fbecdab'),
    'request_closure': (0x165634, 0x1656FC, '433b7836508bede8eb779b530b6cc446625de04162492eb9b7684a35a91c7ed1'),
    'group_closure': (0x159FE0, 0x15A008, '91f97a19d6fd86a6c428759b140291b4b59d929e6299e8a19e4608347c5925c3'),
    'entries_closure': (0x15A0E0, 0x15A108, 'e43956ed78049def9221326810fd700764c817e4b940e986e31be22ff05309db'),
}
VTABLES = {
    0x102B60900: {8: 0x10015742C, 0x10: 0x100153724, 0x18: 0x100153A6C},
    0x102B60970: {8: 0x1001575AC, 0x10: 0x100154DA8, 0x18: 0x100154F5C},
    0x102B61348: {0x28: 0x1001656A0, 0x30: 0x1001656A4},
    0x102B60B20: {0x28: 0x100159FE4, 0x30: 0x100159FE8},
    0x102B60BE0: {0x28: 0x10015A0E4, 0x30: 0x10015A0E8},
}
PRE_CALL = 0x16556C
ID_STORE = 0x165574
CAVE = 0x3900
CAVE_SIZE = 32


def _branch(source, target):
    delta = target - source
    if delta % 4 or not -(1 << 27) <= delta < (1 << 27):
        raise ValueError('Unencodable branch')
    return 0x14000000 | ((delta // 4) & 0x3FFFFFF)


def patch_fresh_zero_store(binary):
    """Experimental fresh-ID guard; returns bytes/plan without writing files.

    x26 is already spilled at bridge +4 and restored before return. The exact
    guarded bridge has no other x26 reads or writes. It is only a temporary
    initial-ID latch; callback order and object deletion are unchanged.
    """
    validate(binary)
    image = MachO(binary)
    command_count, command_bytes = struct.unpack_from('<II', binary, 16)
    command_end = 32 + command_bytes
    first_section = min(section['offset'] for section in image.sections
                        if section['size'] and section['offset']
                        and section['flags'] & 0xFF not in (1, 0xC, 0x12))
    if not command_end <= CAVE < CAVE + CAVE_SIZE <= first_section:
        raise ValueError('Cave is not inside header padding')
    position, executable_mapping = 32, False
    for _ in range(command_count):
        command, size = struct.unpack_from('<II', binary, position)
        if command == 0x19 and binary[position + 8:position + 24].rstrip(b'\0') == b'__TEXT':
            vm, virtual_size, offset, file_size, maxprot, initprot = struct.unpack_from('<QQQQii', binary, position + 24)
            executable_mapping = (vm == BASE and offset == 0 and initprot & 4
                                  and CAVE + CAVE_SIZE <= min(virtual_size, file_size))
        position += size
    if not executable_mapping:
        raise ValueError('Cave lacks the expected executable __TEXT mapping')
    if not (CAVE >= 0x3900 and CAVE + CAVE_SIZE <= 0x4000):
        raise ValueError('Cave overlaps reserved SE area or first text page')
    if any(binary[CAVE:CAVE + CAVE_SIZE]):
        raise ValueError('Experimental cave is not zero')
    # Pre-call: ldr w26,[x21,#0x10]; displaced mov x3,x23; b original BLR.
    # Post-call: cbnz w0,store; cbnz w26,store; b after; original str; b after.
    words = [0xB94012BA, struct.unpack_from('<I', binary, PRE_CALL)[0],
             _branch(CAVE + 8, PRE_CALL + 4), 0x35000060, 0x3500005A,
             _branch(CAVE + 20, ID_STORE + 4), struct.unpack_from('<I', binary, ID_STORE)[0],
             _branch(CAVE + 28, ID_STORE + 4)]
    output = bytearray(binary)
    output[CAVE:CAVE + CAVE_SIZE] = struct.pack('<8I', *words)
    output[PRE_CALL:PRE_CALL + 4] = struct.pack('<I', _branch(PRE_CALL, CAVE))
    output[ID_STORE:ID_STORE + 4] = struct.pack('<I', _branch(ID_STORE, CAVE + 12))
    changes = [{'file_offset': hex(offset), 'original': binary[offset:offset + size].hex(),
                'replacement': bytes(output[offset:offset + size]).hex()}
               for offset, size in ((PRE_CALL, 4), (ID_STORE, 4), (CAVE, CAVE_SIZE))]
    return bytes(output), {'experimental': True, 'device_validated': False,
                           'scope': 'Skip post-submit ID store only when both pre-call and returned IDs are zero',
                           'changes': changes, 'header_command_end': hex(command_end),
                           'first_section_offset': hex(first_section),
                           'not_fixed': ['Reused nonzero-ID request lifetime error', 'Helper early-response state loss',
                                         'Unknown live server rejection policy'],
                           'requires_resigning_if_packaged': True}


def validate(binary):
    validate_delivery(binary)
    for name, (start, end, digest) in WINDOWS.items():
        if hashlib.sha256(binary[start:end]).hexdigest() != digest:
            raise ValueError('Changed original ' + name + ' instructions')
    image = MachO(binary)
    for address, slots in VTABLES.items():
        if any(image.vm_pointer(address + offset) != target for offset, target in slots.items()):
            raise ValueError('Changed request/closure vtable')


def probe(binary, *, rejected=(), experimental=False, initial_request_id=0,
          manager_present=True, counter_seed=0):
    """Run the actual helper launch, Start, bridge, manager and empty callbacks.

    The allocator records delete calls without unmapping memory, allowing the
    original post-delete write to be recorded and execution to finish. It does
    not simulate allocator reuse, a hardware fault, or a complete C++ runtime.
    """
    validate(binary)
    if (type(experimental) is not bool or type(manager_present) is not bool
            or type(initial_request_id) is not int or not 0 <= initial_request_id <= 0xFFFFFFFF
            or type(counter_seed) is not int or not 0 <= counter_seed <= 0xFFFFFFFF):
        raise ValueError('Invalid synthetic probe state')
    rejected = tuple(rejected)
    if any(type(op) is not int or op not in (0x28F4, 0x28ED) for op in rejected):
        raise ValueError('Only the two tournament operations may be rejected')
    execution = patch_fresh_zero_store(binary)[0] if experimental else binary
    m = _Machine(execution)
    image = MachO(binary)
    for start, end, _ in WINDOWS.values():
        m.map(BASE + start, end - start)
        m.uc.mem_write(BASE + start, execution[start:end])
    if experimental:
        m.map(BASE + CAVE, CAVE_SIZE)
        m.uc.mem_write(BASE + CAVE, execution[CAVE:CAVE + CAVE_SIZE])
    for address in VTABLES:
        m.map(address, 0x38)
        m.uc.mem_write(address, binary[image.vm_offset(address):image.vm_offset(address) + 0x38])
    for address in (0x10234C9F0, 0x10234CA00):
        m.map(address, 16)
        m.uc.mem_write(address, binary[image.vm_offset(address):image.vm_offset(address) + 16])
    helper, ids, cloud, cloud_vt, wrapper, wrapper_vt, manager, manager_vt, pending = [
        m.data + i * 0x200 for i in range(1, 10)]
    m.put(helper + 0x30, '<I', 7)
    m.put(helper + 0x38, '<QQQ', ids, ids + 4, ids + 4)
    m.put(ids, '<I', 1234)
    m.map(0x103287FF0)
    m.put(0x103287FF0, '<Q', cloud)
    m.put(cloud, '<Q', cloud_vt)
    m.put(cloud_vt + 0x18, '<Q', m.data + 0xD000)
    m.put(wrapper, '<Q', wrapper_vt)
    m.put(wrapper + 0x10, '<Q', manager if manager_present else 0)
    m.put(wrapper_vt + 0x10, '<Q', 0x1016FD468)
    m.put(manager, '<Q', manager_vt)
    m.put(manager_vt + 0x10, '<Q', 0x10170B62C)
    m.put(manager + 0x18, '<QQQ', pending, pending, pending + 0xA0)
    completion, completion_vt = m.data + 0x1400, m.data + 0x1500
    m.put(helper + 0x28, '<Q', completion)
    m.put(completion, '<Q', completion_vt)
    m.put(completion_vt + 0x30, '<Q', m.data + 0xD008)
    m.map(0x1031D10F8)
    m.put(0x1032EBB80, '<I', counter_seed)
    allocations, freed, events, starts, post_delete_writes = {}, set(), [], [], []
    next_allocation = [m.data + 0x2000]
    for index in range(19, 30):
        m.uc.reg_write(getattr(m.regs, 'UC_ARM64_REG_X' + str(index)), 0xABCD0000 + index)
    for index in range(8, 16):
        m.uc.reg_write(getattr(m.regs, 'UC_ARM64_REG_D' + str(index)), 0xFEDC0000 + index)
    m.uc.reg_write(m.regs.UC_ARM64_REG_NZCV, 0xA0000000)
    boundary_flags = []

    def allocate(machine):
        size = machine.x(0)
        address = next_allocation[0]
        next_allocation[0] += 0x100
        if next_allocation[0] >= m.data + 0xC000:
            raise RuntimeError('Synthetic allocator exhausted')
        allocations[address] = size
        machine.result(address)

    def delete(machine):
        address = machine.x(0)
        if address in freed or address not in allocations:
            raise AssertionError('Invalid synthetic delete')
        freed.add(address)
        events.append({'event': 'delete', 'address': hex(address), 'size': allocations[address],
                       'sync_lock_held': bool(m.get(manager + 0x10, '<B'))})

    def copy(machine):
        machine.uc.mem_write(machine.x(0), bytes(machine.uc.mem_read(machine.x(1), machine.x(2))))

    def lock(machine):
        machine.put(machine.x(0), '<Q', machine.x(1))
        machine.put(machine.x(1), '<B', 1)

    def blob_copy(machine):
        machine.uc.mem_write(machine.x(0), bytes(machine.uc.mem_read(machine.x(1), 24)))

    def move_callback(machine):
        machine.put(machine.x(0) + 0x18, '<Q', machine.get(machine.x(1) + 0x18))
        machine.put(machine.x(1) + 0x18, '<Q', 0)

    m.stub(0x102270F2C, 'operator_new', allocate)
    m.stub(0x102270F08, 'operator_delete', delete)
    m.stub(0x1022725B8, 'memcpy', copy)
    m.stub(0x1022737B8, 'time', lambda machine: machine.result(123))
    m.stub(m.data + 0xD000, 'sync_getter', lambda machine: machine.result(wrapper))
    m.stub(m.data + 0xD008, 'helper_completion')
    m.stub(0x1003C752C, 'local_response_override', lambda machine: machine.result(0))
    m.stub(0x10170CE20, 'lock', lock)
    m.stub(0x10170CEB8, 'rejection_lookup', lambda machine: machine.result(
        int(machine.get(machine.x(1), '<I') in rejected)))
    m.stub(0x101725A04, 'blob_init', lambda machine: machine.put(machine.x(0), '<QQQ', 0, 0, 0))
    m.stub(0x101725A74, 'blob_copy', blob_copy)
    m.stub(0x1017253B0, 'move_callback', move_callback)
    for address in (0x101726078, 0x101725A78, 0x101725AA4, 0x101713AD8):
        m.stub(address, 'opaque_blob_or_log')

    from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE

    def observe(uc, address, size, _):
        if address in (0x100153724, 0x100154DA8):
            obj = m.x(0)
            # Nonzero values deliberately model an unproved reused-request
            # state. The ordinary constructor's original initialized value is 0.
            if initial_request_id:
                m.put(obj + 0x10, '<I', initial_request_id)
            starts.append({'address': hex(obj), 'operation': hex(m.get(obj + 8, '<I')),
                           'cache_key': m.get(obj + 0x68, '<i') if address == 0x100153724 else None})
        if address in (0x100156560, 0x100156660):
            events.append({'event': 'helper_response', 'response': 'group' if address == 0x100156560 else 'entries',
                           'empty': m.x(1) == 0, 'pending': m.get(helper + 0xFC, '<B'),
                           'sync_lock_held': bool(m.get(manager + 0x10, '<B'))})
        if address == 0x100165574:
            events.append({'event': 'bridge_result', 'address': hex(m.x(21)),
                           'request_id': m.x(0), 'already_deleted': m.x(21) in freed})
            boundary_flags.append([uc.reg_read(m.regs.UC_ARM64_REG_NZCV)])
        if address == 0x100165578:
            boundary_flags[-1].append(uc.reg_read(m.regs.UC_ARM64_REG_NZCV))
        if address == 0x1001564E0:
            events.append({'event': 'before_arm', 'group_received': m.get(helper + 0x104, '<B'),
                           'entries_received': m.get(helper + 0x105, '<B'),
                           'error': m.get(helper + 0x106, '<B')})

    def write(uc, access, address, size, value, _):
        for obj in freed:
            if obj <= address < obj + allocations[obj]:
                post_delete_writes.append({'pc': hex(uc.reg_read(m.regs.UC_ARM64_REG_PC)),
                                           'object': hex(obj), 'offset': hex(address - obj),
                                           'size': size, 'value': value})

    m.uc.hook_add(UC_HOOK_CODE, observe)
    m.uc.hook_add(UC_HOOK_MEM_WRITE, write)
    try:
        m.run(0x1001561FC, helper, 0)
    except Exception as error:
        raise RuntimeError('Probe stopped at ' + hex(m.uc.reg_read(m.regs.UC_ARM64_REG_PC))
                           + '; recent hooks: ' + repr(m.calls[-8:])) from error
    return {'rejected_operations': [hex(op) for op in rejected], 'experimental': experimental,
            'synthetic_initial_id': initial_request_id, 'concrete_manager_present': manager_present,
            'starts': starts,
            'events': events, 'post_delete_writes': post_delete_writes,
            'helper': {'group_handle': hex(m.get(helper)), 'entries_handle': hex(m.get(helper + 8)),
                       'pending': m.get(helper + 0xFC, '<B'),
                       'group_received': m.get(helper + 0x104, '<B'),
                       'entries_received': m.get(helper + 0x105, '<B'),
                       'error': m.get(helper + 0x106, '<B')},
            'pending_records': (m.get(manager + 0x20) - pending) // 0x50,
            'helper_completions': m.calls.count('helper_completion'),
            'live_request_ids': {item['operation']: m.get(int(item['address'], 16) + 0x10, '<I')
                                 for item in starts if int(item['address'], 16) not in freed},
            'boundary_nzcv': boundary_flags,
            'caller_state': {'callee_saved': [m.x(index) for index in range(19, 30)],
                             'vector_callee_saved': [m.uc.reg_read(getattr(m.regs, 'UC_ARM64_REG_D' + str(index)))
                                                     for index in range(8, 16)],
                             'sp': m.uc.reg_read(m.regs.UC_ARM64_REG_SP),
                             'nzcv': m.uc.reg_read(m.regs.UC_ARM64_REG_NZCV)},
            'sync_lock_after': m.get(manager + 0x10, '<B'),
            'limit': 'Rejection decisions, allocator, local override and blob APIs are synthetic; server reachability unknown'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', type=Path, help='JSON report, refusing overwrite')
    parser.add_argument('--experimental-fresh-id-store-guard', action='store_true',
                        help='Emulate exact guarded candidate; emit plan only, no executable')
    args = parser.parse_args()
    if zipfile.is_zipfile(args.input):
        with zipfile.ZipFile(args.input) as archive:
            binary = archive.read(BINARY_PATH)
    else:
        binary = args.input.read_bytes()
    report = {name: probe(binary, rejected=ops) for name, ops in (
        ('accepted', ()), ('group_rejected', (0x28F4,)), ('entries_rejected', (0x28ED,)),
        ('both_rejected', (0x28F4, 0x28ED)))}
    if args.experimental_fresh_id_store_guard:
        report = {'plan': patch_fresh_zero_store(binary)[1], 'baseline': report,
                  'candidate': {name: probe(binary, rejected=ops, experimental=True) for name, ops in (
                      ('accepted', ()), ('group_rejected', (0x28F4,)), ('entries_rejected', (0x28ED,)),
                      ('both_rejected', (0x28F4, 0x28ED)))}}
    output = json.dumps(report, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(output)
    print(output, end='')


if __name__ == '__main__':
    main()
