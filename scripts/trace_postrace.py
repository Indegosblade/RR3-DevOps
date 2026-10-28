"""Trace exact-build post-race completion and prepare an experimental timeout plan.

Default operation is read-only. The candidate changes one timeout immediate and
retains the existing error/completion callback; it is NOT a validated game fix.
No signing, device access or production-builder change is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from build_4k_v3 import BINARY_PATH, SUPPORTED_MACHO_UUID, eds_crypt, macho_uuid

BASE = 0x100000000
TIMER_START = 0x1567B4
TIMER_LIMIT = 0x1567D4
TIMER_CALLER = 0x3E5EF4
ORIGINAL_TICKS = 30000
# The complete 80-byte leaf timer, guarded independently of surrounding code.
TIMEOUT_CODE = bytes.fromhex(
    '08f043391f0500712102005408184439e8010037080841b90801010b080801b9'
    '09a68e521f01096b2b01005428008052081804391ff00339001440f9800000b4'
    '080040f9011940f920001fd6c0035fd6'
)
TIMEOUT_SHA256 = '36a0ed5712d0a805fa1cce2db7951b47948d6df5a89186b3bb6007710f5de7ed'
TIMER_CALL = struct.pack('<I', 0x94000000 | (((TIMER_START - TIMER_CALLER) // 4) & 0x3FFFFFF))


def sections(binary):
    """Return file-backed Mach-O sections with validated command bounds."""
    if len(binary) < 32 or struct.unpack_from('<I', binary)[0] != 0xFEEDFACF:
        raise ValueError('Expected a little-endian 64-bit Mach-O')
    end = 32 + struct.unpack_from('<I', binary, 20)[0]
    if end > len(binary):
        raise ValueError('Truncated load commands')
    result = []
    offset = 32
    for _ in range(struct.unpack_from('<I', binary, 16)[0]):
        if offset + 8 > end:
            raise ValueError('Truncated load command')
        command, size = struct.unpack_from('<II', binary, offset)
        if size < 8 or offset + size > end:
            raise ValueError('Invalid load command')
        if command == 0x19:
            if size < 72:
                raise ValueError('Truncated segment')
            count = struct.unpack_from('<I', binary, offset + 64)[0]
            if 72 + count * 80 > size:
                raise ValueError('Truncated section table')
            for index in range(count):
                entry = offset + 72 + index * 80
                name = binary[entry:entry + 16].split(b'\0')[0].decode()
                segment = binary[entry + 16:entry + 32].split(b'\0')[0].decode()
                address, length, file_offset = struct.unpack_from('<QQI', binary, entry + 32)
                flags = struct.unpack_from('<I', binary, entry + 64)[0]
                # Zerofill sections have no corresponding bytes in the file.
                if flags & 0xFF in (1, 0xC, 0x12):
                    continue
                if file_offset + length > len(binary):
                    raise ValueError('Section extends beyond executable')
                result.append({'name': name, 'segment': segment, 'address': address,
                               'offset': file_offset, 'size': length})
        offset += size
    return result


def direct_branch_target(word, address):
    """Resolve an ARM64 BL; ordinary branches/indirect calls are not BL sites."""
    if word & 0xFC000000 != 0x94000000:
        return None
    immediate = word & 0x3FFFFFF
    if immediate & (1 << 25):
        immediate -= 1 << 26
    return address + immediate * 4


def validate_timer(binary):
    if macho_uuid(binary) != SUPPORTED_MACHO_UUID:
        raise ValueError('Unsupported executable UUID')
    if binary[TIMER_START:TIMER_START + len(TIMEOUT_CODE)] != TIMEOUT_CODE:
        raise ValueError('Original timeout function does not match')
    if binary[TIMER_CALLER:TIMER_CALLER + 4] != TIMER_CALL:
        raise ValueError('Aggregate-screen timeout caller does not match')


def patch_timeout(binary, timeout_ticks):
    """Return an EXPERIMENTAL one-instruction change; no files are written."""
    if type(timeout_ticks) is not int or not 1 <= timeout_ticks < ORIGINAL_TICKS:
        raise ValueError('Experimental timeout must be an integer from 1 to 29999 ticks')
    validate_timer(binary)
    replacement = struct.pack('<I', 0x52800009 | (timeout_ticks << 5))
    output = bytearray(binary)
    output[TIMER_LIMIT:TIMER_LIMIT + 4] = replacement
    return bytes(output), {
        'experimental': True,
        'device_validated': False,
        'scope': 'TimeTrialTournamentAggregateScreen helper timeout; not all Time Trials',
        'file_offset': hex(TIMER_LIMIT), 'virtual_address': hex(BASE + TIMER_LIMIT),
        'original': binary[TIMER_LIMIT:TIMER_LIMIT + 4].hex(),
        'replacement': replacement.hex(),
        'original_ticks': ORIGINAL_TICKS, 'replacement_ticks': timeout_ticks,
        'input_units': 'integer update delta; no runtime clock measurement in this audit',
        'expected_function_sha256': TIMEOUT_SHA256,
        'requires_resigning_if_packaged': True,
        'preserved': 'normal timeout error flag, pending clear, one-shot callback, result and Continue handlers',
    }


def trace(binary):
    validate_timer(binary)
    section_list = sections(binary)
    callers = []
    for section in section_list:
        if section['name'] != '__text':
            continue
        data = binary[section['offset']:section['offset'] + section['size']]
        if len(data) % 4:
            raise ValueError('Unaligned ARM64 text section')
        for index, (word,) in enumerate(struct.iter_unpack('<I', data)):
            address = section['address'] + index * 4
            if direct_branch_target(word, address) == BASE + TIMER_START:
                callers.append(hex(address))
    return {
        'evidence': 'static instructions and retained RTTI; not a runtime performance trace',
        'executable_uuid': SUPPORTED_MACHO_UUID.hex(),
        'timeout_function': hex(BASE + TIMER_START),
        'timeout_function_sha256': hashlib.sha256(TIMEOUT_CODE).hexdigest(),
        'timeout_ticks': ORIGINAL_TICKS,
        'direct_callers': callers,
        'indirect_call_caveat': 'Direct BL scanning cannot exclude computed/indirect function calls',
        'model_fields': {'pending': '0xfc', 'first_response': '0x104',
                         'second_response': '0x105', 'error_or_timeout': '0x106',
                         'elapsed_ticks': '0x108', 'completion_closure': '0x28'},
        'request_pair': [
            {'class': 'CC_Helpers::LeaderBoardGroupSync', 'vtable': '0x102b60970',
             'start': '0x100154da8', 'response_callback': '0x100156560'},
            {'class': 'CC_Helpers::LeaderBoardSync', 'vtable': '0x102b60900',
             'start': '0x100153724', 'response_callback': '0x100156660'},
        ],
        'transitions': [
            {'event': 'request start', 'site': '0x1001564e0',
             'effect': 'pending=1; response flags, error and elapsed counter cleared'},
            {'event': 'first/second response', 'sites': ['0x100156560', '0x100156660'],
             'effect': 'both response flags or any error can clear pending and invoke callback once'},
            {'event': 'timeout tick', 'site': '0x1001567b4',
             'effect': 'while pending and not already errored, accumulate delta; at 30000 set error, clear pending, invoke callback'},
            {'event': 'aggregate callback', 'site': '0x1003e6f78',
             'effect': 'error/empty entries choose error UI; populated ranked result builds aggregate UI; populated result lacking rank can finish task'},
            {'event': 'Continue event', 'site': '0x1003e6e58',
             'effect': 'event type1 and BTN_CONTINUE set screen completion byte+0x264'},
            {'event': 'screen cleanup', 'site': '0x1003e5150',
             'effect': 'destroys helper; cleanup0x100156020 calls request abandonment0x100165494 and deletes outstanding handles'},
        ],
        'limits': [
            'No proof this tournament screen is the delayed screen in the community report.',
            'Changing the timeout does not disable requests or prove CPU/disk improvement.',
            'No local-save write or save-transaction ordering has been established from these functions.',
            'The request bridge uses a virtual manager interface; synchronous/asynchronous delivery guarantees are not established here.',
            'A shorter timeout can reject a slow valid response; the candidate is for controlled offline testing only.',
        ],
    }


def gui_bindings(archive):
    result = []
    for name in archive.namelist():
        if not name.endswith('.gui') or 'TimeTrialTournamentAggregate' not in name:
            continue
        root = ET.fromstring(eds_crypt(archive.read(name)))
        wanted = {'FRAME_SYNCING', 'SYNCING_TEXT', 'SYNCING_ERROR', 'AGGREGATE_INFO_FRAME', 'BTN_CONTINUE'}
        result.extend({'layout': name.split('/res/', 1)[-1], 'id': node.get('id'),
                       'name': node.get('id_string'), 'text': node.get('text')}
                      for node in root.iter() if node.get('id_string') in wanted)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='Original/final-build executable or IPA')
    parser.add_argument('--output', type=Path, help='Write analysis JSON, refusing overwrite')
    parser.add_argument('--experimental-timeout-ticks', type=int)
    parser.add_argument('--candidate-output', type=Path, help='Write a patch-plan JSON, not an IPA or executable')
    args = parser.parse_args()
    if (args.experimental_timeout_ticks is None) != (args.candidate_output is None):
        parser.error('--experimental-timeout-ticks and --candidate-output must be used together')
    if zipfile.is_zipfile(args.input):
        with zipfile.ZipFile(args.input) as archive:
            binary = archive.read(BINARY_PATH)
            bindings = gui_bindings(archive)
    else:
        binary = args.input.read_bytes()
        bindings = []
    report = trace(binary)
    report['aggregate_gui_bindings'] = bindings
    if args.candidate_output:
        _, plan = patch_timeout(binary, args.experimental_timeout_ticks)
        with args.candidate_output.open('x', encoding='utf-8') as output:
            json.dump(plan, output, indent=2)
            output.write('\n')
        report['experimental_candidate'] = plan
    rendered = json.dumps(report, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as output:
            output.write(rendered)
    print(rendered, end='')


if __name__ == '__main__':
    main()
