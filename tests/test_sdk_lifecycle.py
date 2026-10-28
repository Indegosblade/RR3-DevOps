"""Synthetic ARM64 callback/ABI tests; no game executable or device data."""
import hashlib
import struct
import unittest

from scripts.audit_sdk_dependencies import MachO
from scripts.trace_sdk_lifecycle import (
    CALLBACK_BLOCK, FETCH_TAIL, WINDOWS, branch_target, emulate_collection_flag,
    emulate_completion, emulate_fetch_wrapper, global_block, imported_symbol_at,
    objc_methods, verify_window, emulate_interstitial_poll, emulate_interstitial_close,
    emulate_interstitial_no_fill, emulate_interstitial_start,
)
from test_sdk_dependencies import DATA, TEXT, macho_fixture


def words(values):
    return struct.pack('<' + 'I' * len(values), *values)


def branch(pc, target, link=False):
    delta = target - pc
    if delta % 4 or not -(1 << 27) <= delta < (1 << 27):
        raise ValueError('Branch outside ARM64 range')
    return (0x94000000 if link else 0x14000000) | ((delta // 4) & 0x3FFFFFF)


def adrp(pc, target, register):
    immediate = (((target & ~4095) - (pc & ~4095)) // 4096) & 0x1FFFFF
    return 0x90000000 | ((immediate & 3) << 29) | ((immediate >> 2) << 5) | register


class SparseImage:
    def __init__(self, regions):
        self.regions = []
        data = bytearray()
        for address, content in regions:
            self.regions.append((address, len(data), len(content)))
            data.extend(content)
        self.data = bytes(data)

    def vm_offset(self, address, size=1):
        for start, offset, length in self.regions:
            if start <= address and address + size <= start + length:
                return offset + address - start
        raise ValueError('Unmapped synthetic address')

    def vm_pointer(self, address):
        return struct.unpack_from('<Q', self.data, self.vm_offset(address, 8))[0]


def lifecycle_fixture(captured_bytes=0):
    start = WINDOWS['fetch_wrapper'][0]
    # Standard frame + singleton mock + global block + tail call. The class
    # lookup instructions are NOPs, so this is not a copied game function.
    wrapper = words([0xA9BF7BFD, 0x910003FD, 0xD503201F, 0xD503201F,
                     branch(start + 16, 0x1022F1EE0, True),
                     adrp(start + 20, CALLBACK_BLOCK, 2),
                     0x91000042 | ((CALLBACK_BLOCK & 4095) << 10),
                     0xA8C17BFD, branch(start + 32, 0x1022AB040)])
    callback_start = WINDOWS['callback'][0]
    callback = words([0xB50000A1, 0xB5000082,
                      adrp(callback_start + 8, 0x100000000, 0), 0x91000000,
                      branch(callback_start + 16, 0x101713AD8), 0xD65F03C0])
    prefix_start = WINDOWS['collection_prefix'][0]
    prefix = words([0xD10083FF, 0xA9017BFD, 0x910043FD, 0xAA0203F3,
                    0xD503201F, 0xD503201F,
                    branch(prefix_start + 24, 0x102302400, True),
                    0xD503201F, 0xD503201F, 0xD503201F,
                    branch(prefix_start + 40, 0x10227B800, True)])
    descriptor = 0x50002000
    block = struct.pack('<QIIQQ', 0x1234, 0x50000000, 0, callback_start, descriptor)
    return SparseImage([(start, wrapper), (callback_start, callback),
                        (prefix_start, prefix), (CALLBACK_BLOCK, block),
                        (descriptor, struct.pack('<QQ', 0, 32 + captured_bytes)),
                        (0x1031403B8, struct.pack('<Q', 0x50004000)),
                        (0x103140518, struct.pack('<Q', 0x50005000)),
                        (0x1031405A8, struct.pack('<Q', 0x50006000))])


def interstitial_fixture():
    start = WINDOWS['interstitial_poll'][0]
    page = 0x103251000
    # A generic two-flag task predicate using x9 instead of the original x8.
    poll = words([adrp(start, page, 9), 0xF9400129 | ((0xF08 // 8) << 10),
                  0x39400129 | (0x1B4 << 10), 0x36000069,
                  0x52800000, 0xD65F03C0,
                  adrp(start + 24, page, 9), 0xF9400129 | ((0xE60 // 8) << 10),
                  0x39400129 | (0x141 << 10), 0x12000120, 0xD65F03C0,
                  0xD503201F, 0xD503201F])
    close = words([0x3900001F | (0x1B4 << 10), 0xD65F03C0])
    # The model's null-input path reads the existing flag without modifying it.
    no_fill = words([0x39400008 | (0x1B4 << 10), 0x12000100, 0xD65F03C0])
    no_fill += words([0xD503201F] * ((WINDOWS['interstitial_show'][1] - len(no_fill)) // 4))
    entry = WINDOWS['interstitial_start'][0]
    task_start = words([0xD10083FF, 0xA9017BFD, 0x910043FD, 0xAA0003F3,
                        adrp(entry + 16, 0x103251F08, 20), 0x91000294 | (0xF08 << 10),
                        0xF9400280, 0xB9400001 | ((0x1AC // 4) << 10),
                        branch(entry + 32, 0x10066D718, True), 0x36000080,
                        0xA9417BFD, 0x910083FF, 0xD65F03C0,
                        0xF9400280, 0xB9400A61, 0xA9417BFD, 0x910083FF,
                        branch(entry + 68, 0x10066D448)])
    return SparseImage([(start, poll), (WINDOWS['interstitial_close'][0], close),
                        (WINDOWS['interstitial_show'][0], no_fill), (entry, task_start)])


class LifecycleTests(unittest.TestCase):
    def test_branch_target_sign_extension_and_link_bit(self):
        self.assertEqual(branch_target(branch(0x1000, 0x800), 0x1000), 0x800)
        self.assertEqual(branch_target(branch(0x800, 0x1000, True), 0x800), 0x1000)
        self.assertIsNone(branch_target(0xD65F03C0, 0x1000))

    def test_changed_instruction_window_is_refused(self):
        image = SparseImage([(0x1000, b'original')])
        digest = hashlib.sha256(b'original').hexdigest()
        self.assertEqual(verify_window(image, 0x1000, 8, digest), digest)
        with self.assertRaisesRegex(ValueError, 'Changed instruction'):
            verify_window(SparseImage([(0x1000, b'changed!')]), 0x1000, 8, digest)

    def test_global_completion_captures_are_measured(self):
        self.assertEqual(global_block(lifecycle_fixture(), CALLBACK_BLOCK)['captured_bytes'], 0)
        self.assertEqual(global_block(lifecycle_fixture(16), CALLBACK_BLOCK)['captured_bytes'], 16)

    def test_remote_init_is_not_gated_by_collection_bool(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                result = emulate_collection_flag(lifecycle_fixture(), enabled)
                self.assertEqual(result['calls'], [
                    {'operation': 'analytics_collection', 'enabled': enabled},
                    {'operation': 'remote_config_init'},
                ])

    def test_original_and_experimental_tail_preserve_caller_abi(self):
        image = lifecycle_fixture()
        before = image.data
        original = emulate_fetch_wrapper(image)
        experiment = emulate_fetch_wrapper(image, True)
        self.assertEqual(original['calls'], ['remote_config_singleton', 'sdk_fetch_and_activate'])
        self.assertEqual(experiment['calls'], ['remote_config_singleton'])
        self.assertTrue(original['caller_stack_restored'] and experiment['caller_stack_restored'])
        self.assertTrue(original['callee_saved_register_preserved'] and experiment['callee_saved_register_preserved'])
        self.assertEqual(image.data, before)

    def test_success_cached_and_error_callback_paths_do_not_write_state(self):
        for status in (0, 1, 2):
            for error in (False, True):
                with self.subTest(status=status, error=error):
                    result = emulate_completion(lifecycle_fixture(), status, error)
                    self.assertEqual(result['events'], ['success_log'] if status == 0 and not error else [])
                    self.assertEqual(result['memory_writes'], 0)

    def test_indirect_symbol_table_resolves_stub_and_local_entry(self):
        data = bytearray(macho_fixture(loads=(('/usr/lib/libSystem.B.dylib', False),),
                                       symbols=(('_dispatch_async', 1, False),), text_size=24))
        count, size = struct.unpack_from('<II', data, 16)
        command = bytearray(80)
        struct.pack_into('<II', command, 0, 0xB, 80)
        struct.pack_into('<II', command, 56, 0x1000, 2)
        data[32 + size:32 + size + 80] = command
        struct.pack_into('<II', data, 16, count + 1, size + 80)
        struct.pack_into('<III', data, 104 + 64, 0x80000408, 0, 12)
        struct.pack_into('<II', data, 0x1000, 0, 0x80000000)
        image = MachO(data)
        self.assertEqual(imported_symbol_at(image, TEXT), '_dispatch_async')
        self.assertIsNone(imported_symbol_at(image, TEXT + 12))
        with self.assertRaisesRegex(ValueError, 'Misaligned'):
            imported_symbol_at(image, TEXT + 4)

    def test_generic_method_lookup_uses_vm_mapping(self):
        data = bytearray(macho_fixture(sdk_class='fmRemoteConfig'))
        struct.pack_into('<Q', data, 0xC80 + 32, DATA + 0x100)
        struct.pack_into('<IIQQQ', data, 0xD00, 24, 1, DATA + 0x160, DATA + 0x180, TEXT + 0x20)
        data[0xD60:0xD65] = b'Init\0'
        data[0xD80:0xD89] = b'v16@0:8\0\0'
        result = objc_methods(MachO(data), {'fmRemoteConfig'})
        self.assertEqual(result['fmRemoteConfig']['methods'], [
            {'selector': 'Init', 'class_method': False, 'implementation': TEXT + 0x20,
             'type_encoding': 'v16@0:8'}])

    def test_interstitial_poll_requires_both_clear_latch_and_game_state(self):
        for pending in (0, 1):
            for state in (0, 1):
                with self.subTest(pending=pending, state=state):
                    result = emulate_interstitial_poll(interstitial_fixture(), pending, state)
                    self.assertEqual(result['task_done'], not pending and bool(state))
                    self.assertEqual(result['memory_writes'], 0)

    def test_interstitial_no_fill_does_not_arm_or_clear_an_existing_latch(self):
        for pending in (False, True):
            with self.subTest(pending=pending):
                result = emulate_interstitial_no_fill(interstitial_fixture(), pending)
                self.assertEqual(result['pending_after'], pending)
                self.assertEqual(result['return_value'], pending)
                self.assertEqual(result['manager_memory_writes'], 0)

    def test_interstitial_close_callback_clears_the_manager_latch(self):
        self.assertEqual(emulate_interstitial_close(interstitial_fixture()),
                         {'pending_before': True, 'pending_after': False})

    def test_interstitial_start_helper_controls_show_without_waiting(self):
        for value in (False, True):
            with self.subTest(value=value):
                result = emulate_interstitial_start(interstitial_fixture(), value)
                expected = [{'operation': 'last_placement_helper', 'placement': 7}]
                if not value:
                    expected.append({'operation': 'show_requested_placement', 'placement': 3})
                self.assertEqual(result['calls'], expected)
                self.assertTrue(result['caller_stack_restored'])


if __name__ == '__main__':
    unittest.main()
