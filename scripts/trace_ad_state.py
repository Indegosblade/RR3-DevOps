"""Read-only, build-guarded trace of interstitial state and normal modal close."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile

try:
    from scripts.audit_sdk_dependencies import MachO
    from scripts.trace_sdk_lifecycle import UUID, read_vm, verify_window, _emulator
except ModuleNotFoundError:
    from audit_sdk_dependencies import MachO
    from trace_sdk_lifecycle import UUID, read_vm, verify_window, _emulator


WINDOWS = {
    'game_publish': (0x1006027BC, 0xCC, 'b5eef2d3837e104ec031aaa799a17109a2b3b61e36ea394c8f10fe0ab97c86a2'),
    'game_initialise': (0x10008CE60, 0x208, 'a4a91fc92220e1f55486b04a948066c891690f994c5ff081945cfc5b03f958f1'),
    'popup_event': (0x1001DEDAC, 0x9C, '4a52f9e32c74cbc39970f5c31e9998345308a169b40a4faa5392ae7f0b983c5d'),
    'modal_close': (0x1007E1084, 0x6C, 'd4f52ac1518ecad1dd49f7525bdac8346dfe1465f545d33c6729b91efcc20940'),
    'callback_dispatch': (0x10066FAE4, 0x1C, '7ea5b6293812fc7a3fdcad16d4c967ac5f795e864c482da67990129a89bcfcda'),
    'ad_close': (0x10066DB6C, 8, '620b2cf970196cf378cb98f777170d13a174d90d4494d5ef0dc0f27c22f783c7'),
    'provider_show': (0x100670514, 0x1A8, '86cb30f53e7b8e30526826ee6f555f7e330b7bb1de5a8e7d9575c4f60e5e29e7'),
    'provider_completion': (0x1006708B8, 0x1B4, 'da880d2faef6496bb9769c8e6113908693b0f5acc1eae7ad404606f47644df8c'),
    'provider_vtable': (0x102BD30E8, 0x48, '1079c8422b42b194279f4fe5eb9a8d01b596fc4a0e0e2755f61be79de7b12745'),
    'popup_vtable': (0x102B74568, 0x210, '20a71ce8ddbf7cf62ba9322f9201939707cfad106698a93b8bd156b163bdd14e'),
    'callback_vtable': (0x102BD2F28, 0x38, 'e774a6b4da99fb10ef55f7383a003e0eda2aeba0c7c50f75d2ac229e1122f0c4'),
}
CLOSE_LABEL = 0x10257B1E5
POPUP_VTABLE = WINDOWS['popup_vtable'][0]
CALLBACK_VTABLE = WINDOWS['callback_vtable'][0]


def direct_byte_accesses(image, displacement=0x141):
    """List unsigned-immediate LDRB/STRB only; this is not alias analysis."""
    result = []
    for section in image.sections:
        if section['name'] != '__text':
            continue
        code = read_vm(image, section['address'], section['size'])
        for offset in range(0, len(code) - 3, 4):
            word = struct.unpack_from('<I', code, offset)[0]
            operation = word & 0xFFC00000
            if operation not in (0x39000000, 0x39400000):
                continue
            if (word >> 10) & 0xFFF != displacement:
                continue
            result.append({'address': hex(section['address'] + offset),
                           'operation': 'load' if operation == 0x39400000 else 'store',
                           'base_register': (word >> 5) & 31})
    return result


def emulate_game_initialisation(image):
    """Execute the original two instructions that initialize the adjacent bytes."""
    from unicorn.arm64_const import UC_ARM64_REG_X19, UC_ARM64_REG_SP
    start, stop, game = 0x10008D060, 0x10008D068, 0x50000000
    machine, sp, reached = _emulator(image, [(start, 8)], {}, stop)
    machine.mem_map(game, 4096)
    machine.mem_write(game + 0x13F, bytes([0xA5] * 4))
    machine.reg_write(UC_ARM64_REG_SP, sp)
    machine.reg_write(UC_ARM64_REG_X19, game)
    machine.emu_start(start, 0, count=10)
    observed = bytes(machine.mem_read(game + 0x13F, 4))
    if reached != [stop] or observed != bytes([0xA5, 0, 1, 0xA5]):
        raise ValueError('Unexpected game-state initializer effect')
    return {'byte_0x140': observed[1], 'byte_0x141': observed[2],
            'adjacent_bytes_preserved': True}


def emulate_popup_event(image, event_type=1, label='BTN_CLOSE', event_present=True,
                       callback_present=True):
    """Run real event/close/binder/clear code; mock RTTI, strcmp and UI removal.

    This constructs a valid already-scheduled popup and its stored manager
    callback. It does not emulate provider/network code or prove UI rendering.
    """
    from unicorn.arm64_const import (UC_ARM64_REG_PC, UC_ARM64_REG_LR,
                                    UC_ARM64_REG_SP, UC_ARM64_REG_X0,
                                    UC_ARM64_REG_X1, UC_ARM64_REG_X2,
                                    UC_ARM64_REG_X19, UC_ARM64_REG_X20)
    region, popup, event, manager, callback, owner, stop = (
        0x50000000, 0x50001000, 0x50002000, 0x50003000,
        0x50004000, 0x50005000, 0x50010000)
    removals = []

    def returned(uc):
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))

    def dynamic_cast(uc):
        # The valid event object is an explicit fixture assumption.
        uc.reg_write(UC_ARM64_REG_X0, event if event_present else 0)
        returned(uc)

    def string(uc, address):
        value = bytearray()
        for index in range(64):
            byte = uc.mem_read(address + index, 1)[0]
            if byte == 0:
                return bytes(value)
            value.append(byte)
        raise ValueError('Unexpected unbounded event label')

    def compare(uc):
        left = string(uc, uc.reg_read(UC_ARM64_REG_X0))
        right = string(uc, uc.reg_read(UC_ARM64_REG_X1))
        uc.reg_write(UC_ARM64_REG_X0, int(left != right))
        returned(uc)

    def get_owner(uc):
        uc.reg_write(UC_ARM64_REG_X0, owner)
        returned(uc)

    def remove(uc):
        removals.append((uc.reg_read(UC_ARM64_REG_X0), uc.reg_read(UC_ARM64_REG_X1)))
        returned(uc)

    hooks = {0x102271004: dynamic_cast, 0x10227314C: compare,
             0x1007FB814: get_owner, 0x1007FBB80: remove}
    names = ('popup_event', 'modal_close', 'callback_dispatch', 'ad_close',
             'popup_vtable', 'callback_vtable')
    regions = [(WINDOWS[name][0], WINDOWS[name][1]) for name in names]
    regions.append((CLOSE_LABEL, len(b'BTN_CLOSE\0')))
    machine, sp, reached = _emulator(image, regions, hooks, stop)
    machine.mem_map(region, 0x6000)
    machine.mem_write(popup, struct.pack('<Q', POPUP_VTABLE))
    machine.mem_write(popup + 0x298, struct.pack('<Q', callback if callback_present else 0))
    machine.mem_write(callback, struct.pack('<QQQQ', CALLBACK_VTABLE,
                                          WINDOWS['ad_close'][0], 0, manager))
    machine.mem_write(event + 0x38, label.encode('ascii') + b'\0')
    machine.mem_write(event + 0x4F, bytes([len(label)]))
    machine.mem_write(manager + 0x1B4, b'\1')
    machine.reg_write(UC_ARM64_REG_SP, sp)
    machine.reg_write(UC_ARM64_REG_LR, stop)
    machine.reg_write(UC_ARM64_REG_X0, popup)
    machine.reg_write(UC_ARM64_REG_X1, event_type)
    machine.reg_write(UC_ARM64_REG_X2, event if event_present else 0)
    machine.reg_write(UC_ARM64_REG_X19, 0x12345678)
    machine.reg_write(UC_ARM64_REG_X20, 0x87654321)
    machine.emu_start(WINDOWS['popup_event'][0], 0, count=300)
    pending = machine.mem_read(manager + 0x1B4, 1)[0]
    accepted = event_present and event_type == 1 and label == 'BTN_CLOSE'
    if reached != [stop] or machine.reg_read(UC_ARM64_REG_SP) != sp:
        raise ValueError('Popup event did not restore caller stack')
    if (machine.reg_read(UC_ARM64_REG_X19), machine.reg_read(UC_ARM64_REG_X20)) != (0x12345678, 0x87654321):
        raise ValueError('Popup event changed callee-saved registers')
    if removals != ([(owner, popup)] if accepted else []):
        raise ValueError('Unexpected modal-removal request')
    if pending != (0 if accepted and callback_present else 1):
        raise ValueError('Unexpected manager-latch ownership')
    return {'event_type': event_type, 'label': label, 'event_present': event_present,
            'callback_present': callback_present, 'pending_after': pending,
            'modal_removal_requested': bool(removals),
            'caller_stack_and_registers_restored': True}


def trace_image(image, emulate=False):
    if image.uuid != UUID:
        raise ValueError('Unsupported executable UUID')
    windows = {name: verify_window(image, *value) for name, value in WINDOWS.items()}
    if image.vm_string(CLOSE_LABEL) != 'BTN_CLOSE':
        raise ValueError('Unexpected popup close label')
    provider_type = image.vm_pointer(WINDOWS['provider_vtable'][0] - 8)
    if image.vm_string(image.vm_pointer(provider_type + 8)) != 'N12_GLOBAL__N_116PCSPRealRacingAdE':
        raise ValueError('Unexpected PCSP provider RTTI')
    report = {
        'executable_uuid': image.uuid, 'verified_windows': windows,
        'game_state': {
            'global': '0x103251e60', 'offset': '0x141',
            'owner_evidence': '0x100602840 initializes x19; 0x100602884 publishes the same x19 to the game global.',
            'initializer': '0x10008d064: STRH 0x0100 at object + 0x140',
            'initial_value': 1,
            'meaning': 'Unresolved; true initialization is not a fade or provider-completion contract.',
            'direct_byte_accesses': direct_byte_accesses(image),
            'scan_limit': 'Unsigned-immediate LDRB/STRB only; no alias, indexed, wider-store or runtime proof.',
        },
        'normal_close': {
            'input': 'GUI event type 1 with BTN_CLOSE label',
            'handler': '0x1001dedac', 'popup_virtual_slot': '0x1e8',
            'modal_close': '0x1007e1084', 'stored_callback': 'popup + 0x298',
            'member_function_binder': '0x10066fae4',
            'manager_latch_clear': '0x10066db6c',
            'modal_removal_request': '0x1007fbb80',
        },
        'pcsp_provider': {
            'type': 'PCSPRealRacingAd', 'vtable': '0x102bd30e8',
            'load_virtual_0x10': '0x10067030c',
            'show_virtual_0x18': '0x100670514',
            'loaded_virtual_0x20': '0x1006706bc: provider + 0xc0 != null',
            'show_attach': '0x100670620 -> 0x10053b23c',
            'attachment_failure': 'False result returns before viewed callback; manager no-fill route owns deletion before modal scheduling.',
            'network_completion': '0x1006708b8 receives result and checks HTTP status/content before loaded callback.',
            'post_schedule_error_route': 'Not demonstrated; normal popup close is GUI-owned.',
        },
        'patch_status': 'No demonstrated stuck transition; no behavioral patch proposed or applied.',
        'runtime_observations_needed': [
            'Affected screen and timestamps for task start, provider result and modal schedule.',
            'Manager +0x1b4 and game +0x141 at the actual wait.',
            'BTN_CLOSE delivery, stored callback +0x298, callback invocation and modal removal.',
            'Any provider error after scheduling, tied to that same popup instance.',
        ],
        'limitations': [
            'No network, rendering, gameplay or device execution is performed.',
            'Initial value does not establish all producers or a semantic name for the state byte.',
            'Synthetic missing callbacks are ownership probes, not a reproduced game bug.',
        ],
    }
    if emulate:
        report['emulation'] = {
            'game_initialisation': emulate_game_initialisation(image),
            'popup_events': [emulate_popup_event(image, **case) for case in (
                {}, {'event_type': 0}, {'event_type': 2}, {'label': 'OTHER'},
                {'event_present': False}, {'callback_present': False})],
        }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa', type=Path)
    parser.add_argument('--emulate', action='store_true')
    parser.add_argument('--output', type=Path, help='Create a new JSON report; never overwrite')
    args = parser.parse_args()
    if args.output and args.output.resolve() == args.ipa.resolve():
        parser.error('Report must not overwrite input')
    with zipfile.ZipFile(args.ipa) as archive:
        report = trace_image(MachO(archive.read('Payload/RealRacing3.app/RealRacing3')), args.emulate)
    with args.ipa.open('rb') as stream:
        report['input_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
    rendered = json.dumps(report, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(rendered)
    else:
        print(rendered, end='')


if __name__ == '__main__':
    main()
