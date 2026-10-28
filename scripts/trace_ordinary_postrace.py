"""Read-only ordinary Time Trial flow and pending-result persistence probes.

The optional ARM64 probe executes the original callback/save instructions with
synthetic records and an in-memory file interface. It never reads a user's save,
connects to a device or network service, patches code, or signs an IPA.
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
CALLBACK = 0x3E8794
CALLBACK_END = 0x3E8860
SAVE = 0x3E8348
SAVE_END = 0x3E8450
WINDOWS = {
    'queue_callback': (CALLBACK, CALLBACK_END,
                       '90a1823f0fe89f624e49bdab7d69166a7563d7d597cdd55e549c77bdda29041a'),
    'queue_save': (SAVE, SAVE_END,
                   '386b8b69a852cf10e6a12799f03e122170419b314ca62c78e93208bbcd15095c'),
}
POLL_OFFSET = 0x3D1704
POLL = bytes.fromhex('080c40f9480000b408c5513900010012c0035fd6')
ROUTE_OFFSET = 0x4D80F0
ROUTE = bytes.fromhex('b8010034')  # cbz w24, remote-path
RECORD_SIZE = 0x44
EVENTS_UPDATE = 0x27D424
EVENTS_UPDATE_END = 0x27D518
ACTIVATION_TAIL = 0x27D9CC
ACTIVATION_TAIL_END = 0x27D9F4
CADENCE_WINDOWS = {
    'events_update': (EVENTS_UPDATE, EVENTS_UPDATE_END,
                      '7ce1d0652c8b932f00cc527f63a7bf4cf2d6c60010575f91bb56e41b72880df8'),
    'activation_tail': (ACTIVATION_TAIL, ACTIVATION_TAIL_END,
                        '1a078d3fd36782ce3bc1ac82ea2199ce19ee8c7c70a022f58abfc30d746f0ae6'),
}
ENTRY_DISPATCH = bytes.fromhex('680240f9080941f9e00313aa00013fd6e00313aa59630a9428008052684202b9')


def validate(binary):
    if macho_uuid(binary) != SUPPORTED_MACHO_UUID:
        raise ValueError('Unsupported executable UUID')
    for name, (start, end, checksum) in WINDOWS.items():
        if hashlib.sha256(binary[start:end]).hexdigest() != checksum:
            raise ValueError('Changed original ' + name + ' instructions')
    if binary[POLL_OFFSET:POLL_OFFSET + len(POLL)] != POLL:
        raise ValueError('Changed shared leaderboard completion predicate')
    if binary[ROUTE_OFFSET:ROUTE_OFFSET + len(ROUTE)] != ROUTE:
        raise ValueError('Changed local/remote route branch')


def trace(binary):
    validate_cadence(binary)
    image = MachO(binary)
    classes = {}
    for label, pointer in (('remote_task', 0x102BAB638), ('local_task', 0x102BAB5D0),
                           ('upload_task', 0x102BAEBA8), ('events_screen', 0x102B85908)):
        typeinfo = image.vm_pointer(pointer - 8)
        classes[label] = image.vm_string(image.vm_pointer(typeinfo + 8))
    return {
        'scope': 'Static ordinary/local Time Trial task and persistence trace; no runtime diagnosis',
        'executable_uuid': SUPPORTED_MACHO_UUID.hex(),
        'classes': classes,
        'task_selection': {
            'owner': 'TimeTrialMode::EndRace', 'entry': '0x1004d7408',
            'selector_lookup': '0x1004d7a58', 'selector_index': 65,
            'selector_kind': 'configured bitset lookup at this branch; no inline connectivity probe',
            'route_branch': '0x1004d80f0', 'local_constructor': '0x1003d1330',
            'remote_constructor': '0x1003d1614',
            'local_constructor_calls': ['0x1004d811c'],
            'remote_constructor_calls': ['0x1004d796c', '0x1004d814c'],
            'local_option_type': 4, 'remote_option_types': [0, 5],
            'caveat': 'The configuration source and semantic flag name are not established.',
        },
        'screen_completion': {
            'constructor': '0x1003d0058', 'shared_poll': '0x1003d1704',
            'screen_done_offset': '0x471', 'exit_started_offset': '0x470',
            'producers': ['pit-lane button handling0x1003d03fc',
                          'UI-manager transition-state update0x1003d08ac'],
            'caveat': 'The flag is not just a remote-request completion signal; forcing it skips UI transitions.',
        },
        'persistence': {
            'pending_remote_results': {'filename': 'rres.bin', 'record_bytes': RECORD_SIZE,
                                       'load': '0x1003e7f48', 'upsert': '0x1003e8170',
                                       'save': hex(BASE + SAVE), 'reply': hex(BASE + CALLBACK),
                                       'enqueue_then_save': ['0x1003e9fb4', '0x1003e9fcc'],
                                       'flush_direct_caller': '0x10027d9e8'},
            'local_ranking': {'filename': 'localleaderboard.bin', 'writer': '0x1002b3330',
                              'reader': '0x1002b3488', 'table_rebuild_read': '0x10025c7dc',
                              'reader_direct_calls': ['0x10017588c', '0x100254a44', '0x10025c7dc'],
                              'rebuild_direct_calls': ['0x100254854', '0x100254adc', '0x1003d1594'],
                              'rebuild_read_position': 'once before its row/tree loops, not once per row',
                              'callback_overlap': 'The callback reading at0x100254a44 can also rebuild at0x100254adc, producing a second read.',
                              'runtime_frequency': 'not measured'},
            'invariant': 'Open-write failure in the existing queue save retains loaded RAM records; no unconditional skip-write/unload is safe.',
        },
        'other_endrace_tasks': ['DisplayInterstitialTask', 'CompetitionUploadResultTask',
                               'TTCPostRaceTask', 'UploadResultTask'],
        'upload_task': {
            'poll': '0x1003ea8d0', 'done_byte': '0x1f',
            'constructor_default_done': True, 'direct_upload_pending_write': '0x1003ea18c',
            'response_callback': '0x1003ea5c4',
            'retry_callback': '0x1003ea458', 'cancel_callback': '0x1003ea584',
            'retry_ui': ['GAMETEXT_RETRY_UPLOAD_HEADER', 'GAMETEXT_RETRY_UPLOAD_BODY',
                         'GAMETEXT_RETRY', 'GAMETEXT_CANCEL'],
        },
        'queue_scheduling': {
            'entry_owner': 'FrontEnd2::EventsScreen', 'entry_method': '0x10027d5b4',
            'entry_vtable_slot': '0x210', 'common_entry_dispatch': '0x10029e490',
            'frame_update': '0x10027d424', 'update_vtable_slot': '0xa8',
            'flush_call': '0x10027d9e8',
            'queue_reply': 'No retry/backoff timer or resubmission call on the guarded empty-reply path.',
            'view_debounce': {'site': '0x10027d4d0', 'updates': 10,
                              'action': '0x1000e95ec',
                              'behavior': 'one action after a stable view-derived value; counter then saturates at -1 until value changes'},
            'separate_work': 'Flush0x1003e86e0 submits results then also advances a separate ghost queue0x1003ebbfc.',
            'caveat': 'Screen re-entry and lower request-manager retry cadence remain possible; not a measured runtime rate.',
        },
        'limits': ['No per-frame queue retry loop or measured file-write frequency was established.',
                   'Request-manager callback thread/reentrancy ownership remains unresolved.',
                   'No character.2.dat write transaction or complete local-save ordering was established.',
                   'No behavioral patch is emitted; pending results must not be deleted to hide a delay.'],
    }


def validate_cadence(binary):
    validate(binary)
    for name, (start, end, checksum) in CADENCE_WINDOWS.items():
        if hashlib.sha256(binary[start:end]).hexdigest() != checksum:
            raise ValueError('Changed original ' + name + ' instructions')
    if binary[0x29E490:0x29E490 + len(ENTRY_DISPATCH)] != ENTRY_DISPATCH:
        raise ValueError('Changed common screen-entry dispatcher')


def probe_events_cadence(binary, *, updates=50, view_values=None):
    """Exercise original activation-tail, frame-update and debounce instructions.

    The UI object is synthetic and neutral. Opaque UI/API helpers are hooks; this
    establishes local control-flow behavior, not a whole-application retry rate.
    """
    validate_cadence(binary)
    if type(updates) is not int or not 0 <= updates <= 500:
        raise ValueError('Probe update count must be an integer from zero to 500')
    values = [5] * 25 + [7] * 25 if view_values is None else list(view_values)
    if len(values) > 1000 or any(type(value) is not int or not 0 <= value < 0x80000000 for value in values):
        raise ValueError('Probe view values must be at most 1000 nonnegative signed words')
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm64_const import (UC_ARM64_REG_PC, UC_ARM64_REG_SP,
                                     UC_ARM64_REG_X0, UC_ARM64_REG_X1,
                                     UC_ARM64_REG_X19, UC_ARM64_REG_X20,
                                     UC_ARM64_REG_X22, UC_ARM64_REG_X30)
    machine = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    code_page, finish = BASE + 0x27D000, BASE + 0x27DFF0
    screen, context, queue, event, stack = 0x700000000, 0x700010000, 0x700020000, 0x700030000, 0x710000000
    for address, size in ((code_page, 4096), (screen, 4096), (context, 0x2000),
                          (queue, 4096), (event, 4096), (stack, 0x10000), (0x103250000, 4096)):
        machine.mem_map(address, size)
    machine.mem_write(BASE + EVENTS_UPDATE, binary[EVENTS_UPDATE:EVENTS_UPDATE_END])
    machine.mem_write(BASE + ACTIVATION_TAIL, binary[ACTIVATION_TAIL:ACTIVATION_TAIL_END])
    machine.mem_write(0x103250E48, struct.pack('<Q', context))
    machine.mem_write(context + 0x14A8, struct.pack('<i', -1))
    machine.mem_write(screen + 0x2D0, struct.pack('<i', -1))
    machine.mem_write(event + 0x10, struct.pack('<I', 99))
    stubs = {0x10027A578: 'refresh', 0x1003E7EDC: 'queue_getter',
             0x1003E7F48: 'queue_load', 0x1003E86E0: 'queue_flush',
             0x1000E95EC: 'debounced_action'}
    pages = {code_page, 0x103250000}
    calls = []
    for address in stubs:
        if address & ~4095 not in pages:
            machine.mem_map(address & ~4095, 4096)
            pages.add(address & ~4095)
        machine.mem_write(address, bytes.fromhex('c0035fd6'))

    def hook(uc, address, size, user):
        name = stubs.get(address)
        if name is None:
            return
        calls.append({'name': name, 'argument': uc.reg_read(UC_ARM64_REG_X0)})
        uc.reg_write(UC_ARM64_REG_X0, queue if name == 'queue_getter' else 0)
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_X30))

    machine.hook_add(UC_HOOK_CODE, hook)
    machine.reg_write(UC_ARM64_REG_SP, stack + 0xF000)

    def activate():
        machine.reg_write(UC_ARM64_REG_X22, screen)
        machine.emu_start(BASE + ACTIVATION_TAIL, BASE + ACTIVATION_TAIL_END, count=64)

    def flush_count():
        return sum(call['name'] == 'queue_flush' for call in calls)

    activate()
    first_count = flush_count()
    for _ in range(updates):
        machine.reg_write(UC_ARM64_REG_X0, screen)
        machine.reg_write(UC_ARM64_REG_X30, finish)
        machine.emu_start(BASE + EVENTS_UPDATE, finish, count=128)
    after_updates = flush_count()
    activate()
    after_reentry = flush_count()
    action_update_indices = []
    for index, value in enumerate(values):
        old_count = sum(call['name'] == 'debounced_action' for call in calls)
        machine.reg_write(UC_ARM64_REG_X0, value)
        machine.reg_write(UC_ARM64_REG_X1, value)
        machine.reg_write(UC_ARM64_REG_X19, screen)
        machine.reg_write(UC_ARM64_REG_X20, event)
        machine.emu_start(BASE + 0x27D4D0, BASE + 0x27D50C, count=64)
        new_count = sum(call['name'] == 'debounced_action' for call in calls)
        if new_count != old_count:
            action_update_indices.append(index)
    return {'evidence': 'original activation-tail/update/debounce instructions; neutral synthetic UI and opaque helper hooks',
            'frame_updates_exercised': updates, 'flushes_after_activation': first_count,
            'flushes_after_updates': after_updates, 'flushes_after_second_activation': after_reentry,
            'debounce_action_update_indices': action_update_indices,
            'debounce_final_counter': struct.unpack('<i', machine.mem_read(screen + 0x2D4, 4))[0],
            'limits': 'No inference about real screen re-entry frequency, indirect helper effects or request-manager retries.'}


def probe_queue_reply(binary, *, response=None, memory_records=2, persisted_records=1, writable=True):
    """Execute the original callback + save under controlled, synthetic I/O.

    response is None for an empty BinaryBlobRef, otherwise two raw response words.
    File wrappers and acknowledgement bookkeeping are hooks, not game simulation.
    """
    validate(binary)
    if any(type(count) is not int or not 0 <= count <= 32 for count in (memory_records, persisted_records)):
        raise ValueError('Probe record counts must be between zero and 32')
    if response is not None and (len(response) != 2 or any(type(v) is not int or not 0 <= v <= 0xFFFFFFFF for v in response)):
        raise ValueError('Probe response must contain two unsigned words')
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm64_const import (
        UC_ARM64_REG_PC, UC_ARM64_REG_SP, UC_ARM64_REG_X0,
        UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X30,
    )
    machine = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    object_at, records_at, blob_at, payload_at = 0x700000000, 0x700001000, 0x700002000, 0x700003000
    stack, finish = 0x710000000, 0x1003E9000
    machine.mem_map(object_at, 0x4000)
    machine.mem_map(stack, 0x10000)
    machine.mem_map(BASE + 0x3E8000, 0x2000)
    machine.mem_write(BASE + SAVE, binary[SAVE:SAVE_END])
    machine.mem_write(BASE + CALLBACK, binary[CALLBACK:CALLBACK_END])
    machine.mem_write(object_at, b'\x01')
    machine.mem_write(object_at + 8, struct.pack('<QQQ', records_at,
                                               records_at + memory_records * RECORD_SIZE,
                                               records_at + 32 * RECORD_SIZE))
    for index in range(memory_records):
        machine.mem_write(records_at + index * RECORD_SIZE, struct.pack('<I', index + 1) + bytes(RECORD_SIZE - 4))
    payload = b'' if response is None else struct.pack('<II', *response)
    machine.mem_write(payload_at, payload or b'\0')
    machine.mem_write(blob_at, struct.pack('<QII', payload_at, len(payload), 0))
    stubs = {
        0x100942400: 'file_ctor', 0x1005E0884: 'key', 0x100942B64: 'open_write',
        0x100942ECC: 'write_header', 0x1003E7E00: 'write_record',
        0x100942E64: 'finalize', 0x10094258C: 'close', 0x1009424DC: 'file_dtor',
        0x10172616C: 'read_word', 0x101725A78: 'release_blob',
        0x100060F1C: 'log', 0x1003E8914: 'acknowledge',
    }
    pages = {BASE + 0x3E8000, BASE + 0x3E9000}
    for address in stubs:
        page = address & ~4095
        if page not in pages:
            machine.mem_map(page, 4096)
            pages.add(page)
        machine.mem_write(address, bytes.fromhex('c0035fd6'))
    events, headers, written = [], [], []
    disk_count = persisted_records

    def hook(uc, address, size, user):
        nonlocal disk_count
        name = stubs.get(address)
        if name is None:
            return
        x0, x1, x2 = (uc.reg_read(register) for register in (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2))
        events.append(name)
        result = 0
        if name == 'file_ctor':
            uc.mem_write(x0, bytes(0x30))
        elif name == 'open_write':
            result = int(writable)
        elif name == 'write_header':
            headers.append(x1 & 0xFFFFFFFF)
        elif name == 'write_record':
            written.append(bytes(uc.mem_read(x0, RECORD_SIZE)))
        elif name == 'close':
            disk_count = len(written)
        elif name == 'read_word':
            pointer, total, cursor = struct.unpack('<QII', uc.mem_read(x0, 16))
            if x2 != 4 or cursor + 4 > total:
                raise ValueError('Synthetic BinaryBlobRef read overflow')
            uc.mem_write(x1, bytes(uc.mem_read(pointer + cursor, 4)))
            uc.mem_write(x0 + 12, struct.pack('<I', cursor + 4))
        uc.reg_write(UC_ARM64_REG_X0, result)
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_X30))

    machine.hook_add(UC_HOOK_CODE, hook)
    machine.reg_write(UC_ARM64_REG_SP, stack + 0xF000)
    machine.reg_write(UC_ARM64_REG_X0, object_at)
    machine.reg_write(UC_ARM64_REG_X1, blob_at)
    machine.reg_write(UC_ARM64_REG_X30, finish)
    machine.emu_start(BASE + CALLBACK, finish, count=10000)
    start, end = struct.unpack('<QQ', machine.mem_read(object_at + 8, 16))
    return {'evidence': 'original ARM64 callback/save instructions; synthetic file/API hooks',
            'response_words': response, 'writable': writable, 'input_memory_records': memory_records,
            'input_persisted_records': persisted_records, 'output_loaded': machine.mem_read(object_at, 1)[0],
            'output_memory_records': (end - start) // RECORD_SIZE,
            'output_persisted_records': disk_count, 'written_records': len(written),
            'headers': headers, 'events': events}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', type=Path, help='Write report JSON, refusing overwrite')
    parser.add_argument('--emulate-queue', action='store_true')
    parser.add_argument('--emulate-events', action='store_true')
    args = parser.parse_args()
    if zipfile.is_zipfile(args.input):
        with zipfile.ZipFile(args.input) as archive:
            binary = archive.read(BINARY_PATH)
    else:
        binary = args.input.read_bytes()
    report = trace(binary)
    if args.emulate_queue:
        report['controlled_probes'] = {
            'empty_response_write_succeeds': probe_queue_reply(binary),
            'empty_response_write_fails': probe_queue_reply(binary, writable=False),
            'acknowledged_response': probe_queue_reply(binary, response=(1, 1)),
        }
    if args.emulate_events:
        report['controlled_event_cadence'] = probe_events_cadence(binary)
    rendered = json.dumps(report, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as output:
            output.write(rendered)
    print(rendered, end='')


if __name__ == '__main__':
    main()
