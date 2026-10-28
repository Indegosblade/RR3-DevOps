"""Read-only primary-save dispatch trace; synthetic scheduling probe only.

The probe executes original request/update/predicate instructions. The primary
serializer and secondary-save body are hooks, so no filesystem durability or
complete postrace execution is claimed. No user saves or devices are accessed.
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
    'endrace': (0x4D7408, 0x4D85CC, '4d1ed67a9c839f163f7021da2687af60f73cc0924397c6085e20e8dcadaac56b'),
    'car_damage_task': (0x3C0D40, 0x3C13F4, 'd465a371aae127fb6620fd93c1b261a07c4eefb053bf8347be82a0903072e098'),
    'request': (0x645574, 0x645598, '26922891fb0a9cd70af0647d813693f303ce25d99ddc95434ef306945b3c3e82'),
    'update': (0x64605C, 0x64619C, '96ef0057d375c1b734be95bce7ba8b9ac945ecfe895091aff7e5d20185730ff9'),
    'primary_serializer': (0x6456D0, 0x645AEC, 'cf29a84733cd42c263b8d9aa1d07ec611f73388720830d5ff42e2bf7b3012eb8'),
    'name': (0x645AEC, 0x645C44, '3e07a04e8b82a972171e0fdc94b996f489b611cd08d5e9263b6fd6b534ab8eeb'),
    'writer': (0x943B60, 0x943D18, '07de31536721e80504451a63c726c5b6eab660aaef5845455e536ba81e2a1bcb'),
    'secondary_copy': (0x64356C, 0x6436B0, '04ba321df4451c4b261c8b2134958a77e91c363734f68e2ffbf925cbdd558b53'),
    'file_name': (0x6431C8, 0x64356C, '9f9a4d30f1fb8c5d9427183425f9dd191b44a9c924adb5da0d9c0a7cec7bda28'),
    'save_setup': (0x642868, 0x6431C8, '6a579666b87f8cccc98c8df7988cd160047faa50255b59a61e0e4bf02234f4d1'),
    'task_enqueue': (0x4EFF64, 0x4F0040, 'ac6570c0ce48fe6cd7121b59b7dbff71ce2cae8300858475e7e7ec70520944dc'),
    'task_scheduler': (0x4F01E0, 0x4F04D4, '29e2eadaa1dc11f93516905078309a0d3ad8061d69b2d704768a3267503af702'),
}
CALL_SITES = {
    # ldr x8,[x8,#0x10]; blr x8; cbz w0,...
    'task_completion_slot': (0x4F0280, bytes.fromhex('080940f900013fd660120034')),
    # ldr x8,[x8,#0x20]; blr x8
    'task_start_slot': (0x4F0490, bytes.fromhex('081140f900013fd6')),
    # ldr x0,[x22]; mov x1,x19; bl 0x10064605c
    'independent_update_caller': (0x14248C, bytes.fromhex('c00240f9e10313aaf20e1494')),
}


def validate(binary):
    if macho_uuid(binary) != SUPPORTED_MACHO_UUID:
        raise ValueError('Unsupported executable UUID')
    for name, (start, end, checksum) in WINDOWS.items():
        if hashlib.sha256(binary[start:end]).hexdigest() != checksum:
            raise ValueError('Changed original ' + name + ' instructions')
    for name, (start, expected) in CALL_SITES.items():
        if binary[start:start + len(expected)] != expected:
            raise ValueError('Changed original ' + name + ' call site')
    image = MachO(binary)
    table = 0x102BA9660
    typeinfo = image.vm_pointer(table - 8)
    if image.vm_string(image.vm_pointer(typeinfo + 8)) != '13CarDamageTask':
        raise ValueError('Changed CarDamageTask RTTI')
    if (image.vm_pointer(table + 0x10), image.vm_pointer(table + 0x20)) != (BASE + 0x3C13E4, BASE + 0x3C0D58):
        raise ValueError('Changed task predicate/start vtable slots')
    for offset, expected in ((0x25B45A1, b'%s.2.%s\0'),
                             (0x25B45E5, b'character\0'), (0x25987D2, b'dat\0')):
        if binary[offset:offset + len(expected)] != expected:
            raise ValueError('Changed primary-save naming evidence')


def trace(binary):
    validate(binary)
    return {
        'executable_uuid': SUPPORTED_MACHO_UUID.hex(),
        'evidence': 'Static exact-build control flow; no complete application/save transaction execution',
        'task': {'class': 'CarDamageTask', 'constructor_call': '0x1004d7994',
                 'enqueue_call': '0x1004d79a0', 'start': '0x1003c0d58',
                 'request_call': '0x1003c11b8', 'predicate': '0x1003c13e4',
                 'predicate_result': 'constant true; does not inspect SaveManager'},
        'save_manager': {'request': '0x100645574', 'pending_byte': '0x22',
                         'update': '0x10064605c', 'serializer_call': '0x10064614c',
                         'serializer': '0x1006456d0', 'character_serializer_call': '0x100645854',
                         'character_serializer': '0x10075ca10', 'character_offset': '0x478',
                         'writer_dispatch_call': '0x100645978', 'writer': '0x100943c08',
                         'normal_filename': 'character.2.dat',
                         'update_caveat': 'Pending is cleared after serializer returns, including return zero; that return is not a durable success report.'},
        'limits': ['Selected task branch only; not all EndRace routes execute CarDamageTask.',
                   'Task completion does not wait for primary-save dispatch or durable storage.',
                   'Main-loop scheduling relative to every task update has not been recovered.',
                   'No codec, close, flush, atomic replacement, crash consistency or cold restart proof.',
                   'No behavioral patch or retry policy is produced.'],
    }


def probe_dispatch(binary, *, character_byte_set=True, same_thread=True, blocked=False, serializer_result=1, updates=1):
    """Execute original request/predicate/update with opaque serializer hooks."""
    validate(binary)
    if serializer_result not in (0, 1) or updates not in (1, 2):
        raise ValueError('Probe supports boolean serializer result and one or two updates')
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm64_const import (UC_ARM64_REG_PC, UC_ARM64_REG_SP,
                                     UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X30)
    machine = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    manager, character, stack, finish = 0x700000000, 0x700010000, 0x710000000, 0x720000000
    mapped = set()

    def map_at(address, size=4096):
        for page in range(address & ~4095, (address + size + 4095) & ~4095, 4096):
            if page not in mapped:
                machine.mem_map(page, 4096)
                mapped.add(page)

    for address, size in ((manager, 4096), (character, 4096), (stack, 0x10000), (finish, 4096)):
        map_at(address, size)
    for start, end in ((0x645574, 0x645598), (0x64605C, 0x64619C), (0x3C13E4, 0x3C13EC)):
        map_at(BASE + start, end - start)
        machine.mem_write(BASE + start, binary[start:end])
    hooks = {0x102272CA8: 'current_thread', BASE + 0x6456D0: 'primary_serializer',
             BASE + 0x64619C: 'secondary_save', BASE + 0x060F1C: 'wrong_thread_log'}
    for address in hooks:
        map_at(address)
        machine.mem_write(address, bytes.fromhex('c0035fd6'))
    calls = []

    def hook(uc, address, size, user):
        name = hooks.get(address)
        if name is None:
            return
        calls.append(name)
        result = 0x1234 if name == 'current_thread' else serializer_result if name == 'primary_serializer' else 0
        uc.reg_write(UC_ARM64_REG_X0, result)
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_X30))

    machine.hook_add(UC_HOOK_CODE, hook)
    machine.mem_write(manager, struct.pack('<Q', character))
    machine.mem_write(manager + 0x158, struct.pack('<Q', 0x1234 if same_thread else 0x5678))
    machine.mem_write(character + 0x478, bytes([int(character_byte_set)]))
    machine.mem_write(manager + 0x1C, bytes([int(blocked)]))
    machine.reg_write(UC_ARM64_REG_SP, stack + 0xF000)

    def run(offset):
        machine.reg_write(UC_ARM64_REG_X0, manager)
        machine.reg_write(UC_ARM64_REG_X1, 16)
        machine.reg_write(UC_ARM64_REG_X30, finish)
        machine.emu_start(BASE + offset, finish, count=300)
        if machine.reg_read(UC_ARM64_REG_PC) != finish:
            raise RuntimeError('Probe instruction limit reached')
        return machine.reg_read(UC_ARM64_REG_X0)

    def state():
        return {'pending': machine.mem_read(manager + 0x22, 1)[0],
                'secondary_pending': machine.mem_read(manager + 0x23, 1)[0],
                'serializer_calls': calls.count('primary_serializer'),
                'secondary_calls': calls.count('secondary_save')}

    run(0x645574)
    after_request = state()
    done = run(0x3C13E4)
    after_predicate = state()
    states = []
    for _ in range(updates):
        run(0x64605C)
        states.append(state())
    return {'scope': 'Original scheduling instructions; serializer/file bodies are hooks',
            'after_request': after_request, 'task_predicate': done,
            'after_predicate': after_predicate, 'after_updates': states, 'calls': calls}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--emulate-dispatch', action='store_true')
    args = parser.parse_args()
    with zipfile.ZipFile(args.input) as archive:
        binary = archive.read(BINARY_PATH)
    report = trace(binary)
    if args.emulate_dispatch:
        report['probes'] = {
            'normal': probe_dispatch(binary),
            'serializer_zero': probe_dispatch(binary, serializer_result=0, updates=2),
            'wrong_thread': probe_dispatch(binary, same_thread=False),
            'blocked': probe_dispatch(binary, blocked=True),
        }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
