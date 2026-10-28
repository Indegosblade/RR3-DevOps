"""Read-only trace of researched RR3 SDK initialization and interstitial tasks."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile

try:
    from scripts.audit_sdk_dependencies import MachO, unpack
except ModuleNotFoundError:
    from audit_sdk_dependencies import MachO, unpack

UUID = '06ed5b50c44c3b69a5840701b8a88451'
BASE = 0x100000000
WINDOWS = {
    'collection_prefix': (0x10092D9D8, 44, 'f1f6c4ad50eb3b91a3c88a06d0bcf9512b4b6ced5b29839044bc728e2f4f2b7d'),
    'remote_init': (0x100820094, 88, '1d551273147663cd0c4a30855d3abd1aae610f5c3b481efac45e4a68ced60a01'),
    'fetch_wrapper': (0x1008200EC, 36, '49245e830d1be3850a20a60dbff114349f9210ee9d8bfb9c977f7eaa562d7d6e'),
    'callback': (0x100820110, 24, '37a8bc45967455976773c355e6a7cd0fc8d74571ab25e2f6f8b5983e51b83db6'),
    'settings_init': (0x101ED93D8, 68, 'b11514141c10fc9b7021fa6fa7a034569ed052054c415d8fad242a138ed8577f'),
    'interstitial_start': (0x1003CBAFC, 72, '6f5df79f17d6216419d7828b4cb3ddadfaead8aee51002f4a95bca89dae34f23'),
    'interstitial_poll': (0x1003CBB9C, 52, '3b8cb80ca79f69cb02cb874af88a7d664b1c9d726f9667d6ba30b8460a535b92'),
    'interstitial_close': (0x10066DB6C, 8, '620b2cf970196cf378cb98f777170d13a174d90d4494d5ef0dc0f27c22f783c7'),
    'interstitial_show': (0x10066D5B0, 296, '31c87f622b7c272c1a5d76391fec6a9e72c15f45f5a5bb4fbc2f74ff5b107741'),
}
CALLBACK_BLOCK = 0x102BE82D8
FETCH_TAIL = 0x10082010C
RET = bytes.fromhex('c0035fd6')


def read_vm(image, address, size):
    offset = image.vm_offset(address, size)
    return image.data[offset:offset + size]


def objc_methods(image, names):
    """Resolve selected class definitions/methods, without interpreting callers."""
    result = {}
    width = image.pointer_size
    for section in image.sections:
        if section['name'] != '__objc_classlist':
            continue
        for index in range(section['size'] // width):
            cls = image.vm_pointer(section['address'] + index * width)
            try:
                ro = image.vm_pointer(cls + width * 4) & ~(7 if image.is64 else 3)
                name = image.vm_string(image.vm_pointer(ro + (24 if image.is64 else 16)))
            except ValueError:
                continue
            if name not in names:
                continue
            methods = []
            for class_method in (False, True):
                target = image.vm_pointer(cls) if class_method else cls
                if not target:
                    continue
                target_ro = image.vm_pointer(target + width * 4) & ~(7 if image.is64 else 3)
                pointer = image.vm_pointer(target_ro + (32 if image.is64 else 20))
                if not pointer:
                    continue
                flags, count = unpack('<II', read_vm(image, pointer, 8))
                stride = flags & 0xFFFC
                relative = bool(flags & 0x80000000)
                if stride != (12 if relative else width * 3) or count > 100000:
                    raise ValueError('Unsupported Objective-C method list')
                for ordinal in range(count):
                    entry = pointer + 8 + ordinal * stride
                    if relative:
                        name_delta, type_delta, implementation_delta = unpack('<iii', read_vm(image, entry, 12))
                        selector = entry + name_delta
                        if not flags & 0x40000000:
                            selector = image.vm_pointer(selector)
                        types = entry + 4 + type_delta
                        implementation = entry + 8 + implementation_delta
                    else:
                        selector = image.vm_pointer(entry)
                        types = image.vm_pointer(entry + width)
                        implementation = image.vm_pointer(entry + width * 2)
                    methods.append({'selector': image.vm_string(selector),
                                    'class_method': class_method,
                                    'implementation': implementation,
                                    'type_encoding': image.vm_string(types)})
            result[name] = {'class_address': cls, 'methods': methods}
    return result


def branch_target(word, pc):
    if word & 0x7C000000 != 0x14000000:
        return None
    immediate = word & 0x3FFFFFF
    if immediate & 0x2000000:
        immediate -= 1 << 26
    return pc + immediate * 4


def imported_symbol_at(image, address):
    """Resolve a stub or GOT slot through the Mach-O indirect-symbol table."""
    indirect = None
    slots = []
    position = 32 if image.is64 else 28
    for _ in range(unpack('<I', image.data, 16)[0]):
        command, size = unpack('<II', image.data, position)
        if command == 0xB:
            if size < 80:
                raise ValueError('Truncated dynamic symbol table')
            indirect = unpack('<II', image.data, position + 56)
        elif command in (1, 0x19):
            is64 = command == 0x19
            count = unpack('<I', image.data, position + (64 if is64 else 48))[0]
            for index in range(count):
                at = position + (72 if is64 else 56) + index * (80 if is64 else 68)
                start, length = unpack('<QQ' if is64 else '<II', image.data, at + 32)
                flags, first, stride = unpack('<III', image.data, at + (64 if is64 else 56))
                kind = flags & 0xFF
                if kind in (6, 7, 8) and start <= address < start + length:
                    slots.append((start, length, first, stride if kind == 8 else image.pointer_size))
        position += size
    if indirect is None or image.symtab is None or len(slots) != 1:
        return None
    start, _, first, stride = slots[0]
    if not stride or (address - start) % stride:
        raise ValueError('Misaligned indirect symbol address')
    table, count = indirect
    index = first + (address - start) // stride
    if index >= count:
        raise ValueError('Indirect symbol index outside table')
    symbol = unpack('<I', image.data, table + index * 4)[0]
    if symbol & 0xC0000000:
        return None
    symbols, symbol_count, strings, string_bytes = image.symtab
    if symbol >= symbol_count:
        raise ValueError('Indirect symbol outside symbol table')
    string_index = unpack('<I', image.data, symbols + symbol * (16 if image.is64 else 12))[0]
    from_string = strings + string_index
    if from_string >= strings + string_bytes:
        raise ValueError('Indirect symbol name outside string table')
    stop = image.data.find(b'\0', from_string, strings + string_bytes)
    if stop < 0:
        raise ValueError('Unterminated indirect symbol name')
    return image.data[from_string:stop].decode('utf-8', errors='replace')


def selector_at_stub(image, address):
    """Resolve the exact ADRP x1 / LDR x1 selector-stub form in this build."""
    first, second = unpack('<II', read_vm(image, address, 8))
    if first & 0x9F00001F != 0x90000001 or second & 0xFFC003FF != 0xF9400021:
        return None
    immediate = ((first >> 5) & 0x7FFFF) << 2 | ((first >> 29) & 3)
    if immediate & (1 << 20):
        immediate -= 1 << 21
    page = (address & ~0xFFF) + immediate * 4096
    offset = ((second >> 10) & 0xFFF) * 8
    return image.vm_string(image.vm_pointer(page + offset))


def selector_calls(image, wanted):
    stubs, calls = {}, {name: [] for name in wanted}
    for section in image.sections:
        if section['name'] != '__objc_stubs':
            continue
        for offset in range(0, section['size'] - 8, 4):
            address = section['address'] + offset
            selector = selector_at_stub(image, address)
            if selector in wanted:
                stubs[address] = selector
    for section in image.sections:
        if section['name'] != '__text':
            continue
        for offset in range(0, section['size'], 4):
            address = section['address'] + offset
            word = unpack('<I', read_vm(image, address, 4))[0]
            target = branch_target(word, address)
            if target in stubs:
                calls[stubs[target]].append({'address': address,
                                             'branch': 'BL' if word & 0x80000000 else 'B'})
    return calls


def method(metadata, owner, selector, class_method=False):
    matches = [item for item in metadata[owner]['methods']
               if item['selector'] == selector and item['class_method'] == class_method]
    if len(matches) != 1:
        raise ValueError('Expected one method implementation: ' + owner + ' ' + selector)
    return matches[0]


def verify_window(image, address, size, expected):
    digest = hashlib.sha256(read_vm(image, address, size)).hexdigest()
    if digest != expected:
        raise ValueError('Changed instruction window at ' + hex(address))
    return digest


def global_block(image, address):
    _, flags, _, invoke, descriptor = unpack('<QIIQQ', read_vm(image, address, 32))
    if not flags & 0x10000000:
        raise ValueError('Expected a global completion block')
    size = image.vm_pointer(descriptor + 8)
    if size < 32:
        raise ValueError('Invalid completion block size')
    return {'address': hex(address), 'invoke': hex(invoke),
            'size': size, 'captured_bytes': size - 32}


def verify_selector_call(image, address, expected):
    word = unpack('<I', read_vm(image, address, 4))[0]
    target = branch_target(word, address)
    if target is None or selector_at_stub(image, target) != expected:
        raise ValueError('Unexpected selector call at ' + hex(address))
    return {'address': hex(address), 'selector': expected, 'stub': hex(target)}


def verify_import_call(image, address, expected):
    word = unpack('<I', read_vm(image, address, 4))[0]
    target = branch_target(word, address)
    if target is None or imported_symbol_at(image, target) != expected:
        raise ValueError('Unexpected imported call at ' + hex(address))
    return {'address': hex(address), 'symbol': expected, 'stub': hex(target)}


def _emulator(image, windows, hooks, stop):
    """Execute original ARM64 windows with explicit external-call mocks."""
    try:
        from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
        from unicorn.arm64_const import UC_ARM64_REG_PC
    except ImportError as error:
        raise RuntimeError('Emulation requires unicorn==2.1.4') from error
    machine = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    mapped = set()
    def mapping(address, size):
        for page in range(address & ~4095, (address + size + 4095) & ~4095, 4096):
            if page not in mapped:
                machine.mem_map(page, 4096)
                mapped.add(page)
    for address, size in windows:
        mapping(address, size)
        machine.mem_write(address, read_vm(image, address, size))
    for address in [*hooks, stop]:
        mapping(address, 4)
        machine.mem_write(address, RET)
    stack = 0x700000000
    machine.mem_map(stack, 0x4000)
    reached = []
    def on_code(uc, address, size, user):
        if address == stop:
            reached.append(address)
            uc.emu_stop()
        elif address in hooks:
            hooks[address](uc)
    machine.hook_add(UC_HOOK_CODE, on_code)
    return machine, stack + 0x2000, reached


def emulate_collection_flag(image, enabled):
    """Check the real prefix forwards both BOOLs into the same remote init."""
    from unicorn.arm64_const import (UC_ARM64_REG_PC, UC_ARM64_REG_LR,
                                    UC_ARM64_REG_SP, UC_ARM64_REG_X0,
                                    UC_ARM64_REG_X2, UC_ARM64_REG_X19)
    calls = []
    def return_from(uc):
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))
    def analytics(uc):
        calls.append({'operation': 'analytics_collection', 'enabled': bool(uc.reg_read(UC_ARM64_REG_X2))})
        return_from(uc)
    def remote_init(uc):
        calls.append({'operation': 'remote_config_init'})
        return_from(uc)
    hooks = {0x102302400: analytics,
             0x10227272C: lambda uc: (uc.reg_write(UC_ARM64_REG_X0, 0x50002000), return_from(uc)),
             0x10227B800: remote_init}
    start = WINDOWS['collection_prefix'][0]
    stop = start + WINDOWS['collection_prefix'][1]
    machine, sp, reached = _emulator(image, [(start, stop - start)], hooks, stop)
    # The prefix reads only these two class references; no SDK implementation is run.
    machine.mem_map(0x103140000, 4096)
    for offset in (0x3B8, 0x5A8):
        machine.mem_write(0x103140000 + offset, read_vm(image, 0x103140000 + offset, 8))
    machine.reg_write(UC_ARM64_REG_SP, sp)
    machine.reg_write(UC_ARM64_REG_X0, 0x50001000)
    machine.reg_write(UC_ARM64_REG_X2, int(enabled))
    machine.emu_start(start, 0, count=100)
    if reached != [stop] or machine.reg_read(UC_ARM64_REG_SP) != sp - 32:
        raise ValueError('Collection-prefix emulation did not reach the expected boundary')
    if machine.reg_read(UC_ARM64_REG_X19) != int(enabled):
        raise ValueError('Collection policy register was not preserved')
    return {'enabled': bool(enabled), 'calls': calls, 'own_frame_bytes': 32}


def emulate_fetch_wrapper(image, suppress_fetch=False):
    """Compare original dispatch and a proposed tail RET in emulator memory only."""
    from unicorn.arm64_const import (UC_ARM64_REG_PC, UC_ARM64_REG_LR,
                                    UC_ARM64_REG_SP, UC_ARM64_REG_X0,
                                    UC_ARM64_REG_X2, UC_ARM64_REG_X19,
                                    UC_ARM64_REG_X29)
    calls = []
    def return_from(uc):
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))
    def remote_config(uc):
        calls.append('remote_config_singleton')
        uc.reg_write(UC_ARM64_REG_X0, 0x50003000)
        return_from(uc)
    def fetch(uc):
        if uc.reg_read(UC_ARM64_REG_X2) != CALLBACK_BLOCK:
            raise ValueError('Wrong completion block forwarded to the SDK')
        calls.append('sdk_fetch_and_activate')
        return_from(uc)
    hooks = {0x1022F1EE0: remote_config, 0x1022AB040: fetch}
    start, size, _ = WINDOWS['fetch_wrapper']
    stop = 0x50010000
    machine, sp, reached = _emulator(image, [(start, size)], hooks, stop)
    machine.mem_map(0x103140000, 4096)
    machine.mem_write(0x103140518, read_vm(image, 0x103140518, 8))
    if suppress_fetch:
        machine.mem_write(FETCH_TAIL, RET)
    machine.reg_write(UC_ARM64_REG_SP, sp)
    machine.reg_write(UC_ARM64_REG_LR, stop)
    machine.reg_write(UC_ARM64_REG_X19, 0x12345678)
    machine.reg_write(UC_ARM64_REG_X29, 0x87654321)
    machine.emu_start(start, 0, count=100)
    if reached != [stop] or machine.reg_read(UC_ARM64_REG_SP) != sp:
        raise ValueError('Fetch wrapper did not restore its caller stack')
    if machine.reg_read(UC_ARM64_REG_X19) != 0x12345678:
        raise ValueError('Fetch wrapper changed a callee-saved register')
    if machine.reg_read(UC_ARM64_REG_X29) != 0x87654321:
        raise ValueError('Fetch wrapper did not restore the caller frame pointer')
    return {'suppressed_in_emulator': suppress_fetch, 'calls': calls,
            'caller_stack_restored': True, 'callee_saved_register_preserved': True}


def emulate_completion(image, status, error_present):
    from unicorn import UC_HOOK_MEM_WRITE
    from unicorn.arm64_const import (UC_ARM64_REG_PC, UC_ARM64_REG_LR,
                                    UC_ARM64_REG_SP, UC_ARM64_REG_X1,
                                    UC_ARM64_REG_X2, UC_ARM64_REG_X19)
    events, writes = [], []
    def log(uc):
        events.append('success_log')
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))
    start, size, _ = WINDOWS['callback']
    stop = 0x50010000
    machine, sp, reached = _emulator(image, [(start, size)], {0x101713AD8: log}, stop)
    machine.hook_add(UC_HOOK_MEM_WRITE, lambda *args: writes.append(True))
    machine.reg_write(UC_ARM64_REG_SP, sp)
    machine.reg_write(UC_ARM64_REG_LR, stop)
    machine.reg_write(UC_ARM64_REG_X1, status)
    machine.reg_write(UC_ARM64_REG_X2, 0x1111 if error_present else 0)
    machine.reg_write(UC_ARM64_REG_X19, 0x12345678)
    machine.emu_start(start, 0, count=100)
    if (reached != [stop] or writes or machine.reg_read(UC_ARM64_REG_SP) != sp
            or machine.reg_read(UC_ARM64_REG_X19) != 0x12345678):
        raise ValueError('Completion callback has unexpected effects')
    return {'status': status, 'error_present': bool(error_present), 'events': events,
            'memory_writes': len(writes)}


def _ad_memory(machine, pending=0, game_bit=0):
    manager, game = 0x50003000, 0x50006000
    machine.mem_map(0x103251000, 4096)
    machine.mem_write(0x103251F08, struct.pack('<Q', manager))
    machine.mem_write(0x103251E60, struct.pack('<Q', game))
    machine.mem_map(manager, 4096)
    machine.mem_map(game, 4096)
    machine.mem_write(manager + 0x1B4, bytes([pending]))
    machine.mem_write(game + 0x141, bytes([game_bit]))
    return manager, game


def emulate_interstitial_poll(image, pending, game_bit):
    from unicorn import UC_HOOK_MEM_WRITE
    from unicorn.arm64_const import UC_ARM64_REG_LR, UC_ARM64_REG_SP, UC_ARM64_REG_W0
    start, size, _ = WINDOWS['interstitial_poll']
    stop = 0x50010000
    machine, sp, reached = _emulator(image, [(start, size)], {}, stop)
    _ad_memory(machine, pending, game_bit)
    writes = []
    machine.hook_add(UC_HOOK_MEM_WRITE, lambda *args: writes.append(True))
    machine.reg_write(UC_ARM64_REG_SP, sp)
    machine.reg_write(UC_ARM64_REG_LR, stop)
    machine.emu_start(start, 0, count=100)
    if reached != [stop] or writes:
        raise ValueError('Interstitial poll has unexpected effects')
    return {'manager_pending': bool(pending & 1), 'game_state_bit': bool(game_bit & 1),
            'task_done': bool(machine.reg_read(UC_ARM64_REG_W0)), 'memory_writes': len(writes)}


def emulate_interstitial_close(image):
    from unicorn.arm64_const import UC_ARM64_REG_LR, UC_ARM64_REG_SP, UC_ARM64_REG_X0
    start, size, _ = WINDOWS['interstitial_close']
    stop = 0x50010000
    machine, sp, reached = _emulator(image, [(start, size)], {}, stop)
    manager, _ = _ad_memory(machine, 1, 1)
    machine.reg_write(UC_ARM64_REG_SP, sp)
    machine.reg_write(UC_ARM64_REG_LR, stop)
    machine.reg_write(UC_ARM64_REG_X0, manager)
    machine.emu_start(start, 0, count=100)
    if reached != [stop] or machine.mem_read(manager + 0x1B4, 1) != b'\0':
        raise ValueError('Interstitial close did not clear its manager latch')
    return {'pending_before': True, 'pending_after': False}


def emulate_interstitial_no_fill(image, pending=False):
    from unicorn import UC_HOOK_MEM_WRITE
    from unicorn.arm64_const import (UC_ARM64_REG_LR, UC_ARM64_REG_SP,
                                    UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_W0)
    start, size, _ = WINDOWS['interstitial_show']
    stop = 0x50010000
    machine, sp, reached = _emulator(image, [(start, size)], {}, stop)
    manager, _ = _ad_memory(machine, int(pending), 1)
    machine.mem_map(0x102B56000, 4096)
    machine.mem_map(0x5000B000, 4096)
    machine.mem_write(0x102B56A20, struct.pack('<Q', 0x5000B000))
    machine.mem_write(0x5000B000, struct.pack('<Q', 0x123456789ABCDEF0))
    manager_writes = []
    def on_write(uc, access, address, size, value, user):
        if manager <= address < manager + 4096:
            manager_writes.append((address, size, value))
    machine.hook_add(UC_HOOK_MEM_WRITE, on_write)
    machine.reg_write(UC_ARM64_REG_SP, sp)
    machine.reg_write(UC_ARM64_REG_LR, stop)
    machine.reg_write(UC_ARM64_REG_X0, manager)
    machine.reg_write(UC_ARM64_REG_X1, 0)  # Null GuiAdvertisement after no fill.
    machine.emu_start(start, 0, count=100)
    after = bool(machine.mem_read(manager + 0x1B4, 1)[0])
    if reached != [stop] or manager_writes or after != bool(pending):
        raise ValueError('No-fill path unexpectedly changed the modal latch')
    if machine.reg_read(UC_ARM64_REG_SP) != sp:
        raise ValueError('No-fill path did not restore its caller stack')
    return {'gui_advertisement': None, 'pending_before': bool(pending),
            'pending_after': after, 'return_value': bool(machine.reg_read(UC_ARM64_REG_W0)),
            'manager_memory_writes': len(manager_writes)}


def emulate_interstitial_start(image, helper_result):
    from unicorn.arm64_const import (UC_ARM64_REG_PC, UC_ARM64_REG_LR, UC_ARM64_REG_SP,
                                    UC_ARM64_REG_X0, UC_ARM64_REG_X1)
    calls = []
    def helper(uc):
        calls.append({'operation': 'last_placement_helper', 'placement': uc.reg_read(UC_ARM64_REG_X1)})
        uc.reg_write(UC_ARM64_REG_X0, int(helper_result))
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))
    def show(uc):
        calls.append({'operation': 'show_requested_placement', 'placement': uc.reg_read(UC_ARM64_REG_X1)})
        uc.reg_write(UC_ARM64_REG_X0, 0)
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))
    start, size, _ = WINDOWS['interstitial_start']
    stop = 0x50010000
    machine, sp, reached = _emulator(image, [(start, size)], {0x10066D718: helper, 0x10066D448: show}, stop)
    manager, _ = _ad_memory(machine)
    machine.mem_write(manager + 0x1AC, struct.pack('<I', 7))
    task = 0x50008000
    machine.mem_map(task, 4096)
    machine.mem_write(task + 8, struct.pack('<I', 3))
    machine.reg_write(UC_ARM64_REG_SP, sp)
    machine.reg_write(UC_ARM64_REG_LR, stop)
    machine.reg_write(UC_ARM64_REG_X0, task)
    machine.emu_start(start, 0, count=100)
    if reached != [stop] or machine.reg_read(UC_ARM64_REG_SP) != sp:
        raise ValueError('Interstitial start did not return normally')
    return {'helper_result': bool(helper_result), 'calls': calls, 'caller_stack_restored': True}


def trace_image(image, emulate=False):
    if image.uuid != UUID:
        raise ValueError('Unsupported executable UUID')
    fingerprints = {name: verify_window(image, address, size, expected)
                    for name, (address, size, expected) in WINDOWS.items()}
    metadata = objc_methods(image, {'fmRemoteConfig', 'RealRacingAppDelegate',
                                   'FIRRemoteConfigSettings', 'FIRRemoteConfig',
                                   'RCNConfigFetch', 'RCNConfigSettings'})
    wrapper = method(metadata, 'fmRemoteConfig', 'FetchAndActivateRemoteConfig', True)
    if wrapper['implementation'] != WINDOWS['fetch_wrapper'][0] or wrapper['type_encoding'] != 'v16@0:8':
        raise ValueError('Unexpected fetch-wrapper ABI')
    block = global_block(image, CALLBACK_BLOCK)
    if block['invoke'] != hex(WINDOWS['callback'][0]) or block['captured_bytes']:
        raise ValueError('Completion callback now captures state')
    for caller in (0x1004D7804, 0x1004D792C):
        if branch_target(unpack('<I', read_vm(image, caller, 4))[0], caller) != 0x1003CBAE8:
            raise ValueError('Changed Time Trial interstitial construction site')
    task_type = image.vm_string(image.vm_pointer(image.vm_pointer(0x102BAA000 - 8) + 8))
    if task_type != '23DisplayInterstitialTask':
        raise ValueError('Unexpected task RTTI')
    calls_to_verify = [
        (0x10092D9F0, 'setAnalyticsCollectionEnabled:'),
        (0x10092DA00, 'Init'),
        (0x1008200B4, 'setMinimumFetchInterval:'),
        (0x1008200C8, 'setConfigSettings:'),
        (0x1008200D4, 'FetchAndActivateRemoteConfig'),
        (FETCH_TAIL, 'fetchAndActivateWithCompletionHandler:'),
        (0x101EE5668, 'hasMinimumFetchIntervalElapsed:'),
        (0x101EE567C, 'isFetchInProgress'),
        (0x101EE56D4, 'shouldThrottle'),
        (0x101EE572C, 'refreshInstallationsTokenWithFetchHeader:completionHandler:updateCompletionHandler:'),
        (0x101EE5D68, 'authTokenWithCompletion:'),
        (0x101EE7AA8, 'setTimeoutIntervalForRequest:'),
        (0x101EE7AB8, 'setTimeoutIntervalForResource:'),
        (0x101EE7D88, 'dataTaskWithRequest:completionHandler:'),
        (0x101EE6D30, 'resume'),
        (0x101EE746C, 'updateExponentialBackoffTime'),
        (0x101EE7648, 'updateConfigContentWithResponse:forNamespace:'),
        (0x101EE77E0, 'updateMetadataWithFetchSuccessStatus:templateVersion:'),
        (0x101EE54CC, 'invalidateAndCancel'),
        (0x101EDADD0, 'activeConfig'),
        (0x101EDAEB8, 'defaultValueForFullyQualifiedNamespace:key:'),
    ]
    verified_calls = [verify_selector_call(image, address, selector) for address, selector in calls_to_verify]
    queue_calls = [verify_import_call(image, address, symbol) for address, symbol in (
        (0x101ED9F58, '_dispatch_async'), (0x101EE55E4, '_dispatch_async'),
        (0x101EDACF8, '_dispatch_sync'), (0x101EDA200, '_dispatch_async'))]
    if imported_symbol_at(image, 0x102B56A48) != '__dispatch_main_q':
        raise ValueError('Unexpected completion dispatch queue')
    relevant_selectors = {'FetchAndActivateRemoteConfig', 'EnableFirebaseCollection:',
                          'GetIntValueFromRemoteConfig:', 'GetStringValueFromRemoteConfig:',
                          'GetBoolValueFromRemoteConfig:'}
    callers = selector_calls(image, relevant_selectors)
    minimum, timeout = unpack('<dd', read_vm(image, 0x1024F03C0, 16))
    result = {
        'executable_uuid': image.uuid, 'verified_instruction_windows': fingerprints,
        'methods': metadata,
        'collection_policy': {
            'producer_pointer': '0x103255dd0', 'producer_virtual_offset': '0x90',
            'nil_producer_value': False, 'non_nil_value': 'return of unresolved engine virtual method',
            'remote_config_init_is_gated_by_collection_flag': False,
            'forwarding_thunk': '0x100931308',
        },
        'settings': {'sdk_default_minimum_fetch_interval_seconds': minimum,
                     'app_minimum_fetch_interval_seconds': 0.0,
                     'sdk_default_fetch_timeout_seconds': timeout},
        'app_completion': block,
        'verified_calls': verified_calls,
        'queue_calls': queue_calls,
        'completion_queue': 'SDK fetch-and-activate forwards its app completion onto __dispatch_main_q',
        'direct_selector_callers': {name: [{'address': hex(call['address']), 'branch': call['branch']}
                                           for call in calls] for name, calls in callers.items()},
        'consumer_boundary': {
            'int_bridge': '0x1001e3f40', 'string_bridge': '0x1001e3fe4', 'bool_bridge': '0x1001e4084',
            'keys': 'caller-supplied std::string; complete engine/script consumers are unresolved',
            'reads': 'SDK active config, then default/static fallback, through a synchronous SDK queue',
        },
        'experimental_candidate': {
            'status': 'not_release_ready', 'site': hex(FETCH_TAIL),
            'file_offset': hex(image.vm_offset(FETCH_TAIL, 4)),
            'original': read_vm(image, FETCH_TAIL, 4).hex(), 'replacement': RET.hex(),
            'scope': 'skip only game-owned fire-and-forget fetch dispatch; retain initialization and all getters',
            'risks': ['No fresh config activation; gameplay configuration consumers are not fully identified.',
                      'Existing cached/default state must remain usable; this does not disable SDK-owned background activity.',
                      'No device, race, save-continuity, network or timing acceptance test has been performed.'],
        },
        'interstitial_task': {
            'time_trial_constructor_calls': ['0x1004d7804', '0x1004d792c'],
            'start': '0x1003cbafc', 'poll': '0x1003cbb9c', 'cleanup': '0x1003cbb44',
            'manager_pointer': '0x103251f08', 'pending_offset': '0x1b4',
            'game_pointer': '0x103251e60', 'game_state_offset': '0x141',
            'poll_condition': 'not(manager.pending & 1) and (game.state_byte_0x141 & 1)',
            'game_state_bit_meaning': 'not identified; must not be forced true',
            'modal': 'FrontEnd2::InterstitialAdPopup / InterstitialAdPopup.xml / CONTENT_FRAME',
            'modal_schedule': '0x10066d670', 'pending_set': '0x10066d698',
            'close_callback': '0x10066db6c',
            'no_fill_behavior': 'GuiAdvertisement null path returns before modal allocation and does not set pending',
            'provider_limits': 'PCSP virtual provider and placement fallback exist; equivalence to patched Objective-C readiness selectors is not proven',
            'patch_status': 'no demonstrated stuck latch and no task-completion patch proposed',
        },
        'limitations': [
            'Static direct selector callers are not a complete dynamic call graph.',
            'No evidence ties this operation to a specific black background or Time Trial delay.',
            'Emulation mocks every SDK/system call; it validates the local ABI/control flow, not network or gameplay behavior.',
            'No input bytes are changed and no suppression patch is applied by this tool.',
        ],
    }
    if emulate:
        result['emulation'] = {
            'collection_flags': [emulate_collection_flag(image, value) for value in (False, True)],
            'fetch_wrapper': [emulate_fetch_wrapper(image, value) for value in (False, True)],
            'completion_cases': [emulate_completion(image, status, error)
                                 for status in (0, 1, 2) for error in (False, True)],
            'interstitial_start': [emulate_interstitial_start(image, value) for value in (False, True)],
            'interstitial_poll': [emulate_interstitial_poll(image, pending, state)
                                  for pending in (0, 1) for state in (0, 1)],
            'interstitial_close': emulate_interstitial_close(image),
            'interstitial_no_fill': [emulate_interstitial_no_fill(image, value) for value in (False, True)],
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa', type=Path)
    parser.add_argument('--emulate', action='store_true', help='Run original/experimental ARM64 windows with Unicorn mocks')
    parser.add_argument('--output', type=Path, help='Optional new JSON report path')
    args = parser.parse_args()
    if args.output and args.output.resolve() == args.ipa.resolve():
        parser.error('Report must not overwrite the IPA')
    with zipfile.ZipFile(args.ipa) as archive:
        result = trace_image(MachO(archive.read('Payload/RealRacing3.app/RealRacing3')), args.emulate)
    with args.ipa.open('rb') as stream:
        result['input_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = json.dumps(result, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(report)
    else:
        print(report, end='')


if __name__ == '__main__':
    main()
