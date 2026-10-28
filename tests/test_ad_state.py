"""Synthetic ARM64 ownership fixtures; no game executable or private data."""
import struct
import unittest

from scripts.trace_ad_state import (
    CALLBACK_VTABLE, CLOSE_LABEL, POPUP_VTABLE, UUID, WINDOWS,
    direct_byte_accesses, emulate_game_initialisation, emulate_popup_event,
    trace_image,
)
from scripts.trace_sdk_lifecycle import verify_window
from test_sdk_lifecycle import SparseImage, adrp, branch, words


def cbz(pc, target, register, bits64=True, nonzero=False):
    return ((0xB4000000 if bits64 else 0x34000000) |
            (int(nonzero) << 24) | (((target - pc) // 4 & 0x7FFFF) << 5) | register)


def fixture():
    """Equivalent small typed-event flow with a different instruction layout."""
    start = WINDOWS['popup_event'][0]
    end = start + 21 * 4
    handler = words([
        0xA9BE53F3, 0xA9017BFD, 0x910043FD, 0xAA0003F3, 0xAA0103F4,
        cbz(start + 20, end, 2), 0xAA0203E0,
        branch(start + 28, 0x102271004, True), cbz(start + 32, end, 0),
        0x7100069F, 0x54000001 | (((end - (start + 40)) // 4 & 0x7FFFF) << 5),
        0x9100E000, adrp(start + 48, CLOSE_LABEL, 1),
        0x91000021 | ((CLOSE_LABEL & 4095) << 10),
        branch(start + 56, 0x10227314C, True),
        cbz(start + 60, end, 0, bits64=False, nonzero=True),
        0xAA1303E0, 0xF9400008,
        0xF9400108 | ((0x1E8 // 8) << 10), 0xD63F0100, 0xD503201F,
        0xA9417BFD, 0xA8C253F3, 0xD65F03C0,
    ])
    close = WINDOWS['modal_close'][0]
    modal = words([
        0xA9BF7BF3, 0xAA0003F3, 0xF9400000 | ((0x298 // 8) << 10),
        cbz(close + 12, close + 28, 0), 0xF9400008,
        0xF9400108 | ((0x30 // 8) << 10), 0xD63F0100,
        branch(close + 28, 0x1007FB814, True), 0xAA1303E1,
        0xA8C17BF3, branch(close + 40, 0x1007FBB80),
    ])
    binder = words([0xF9400C08, 0xF9400401, 0xAA0803E0, 0xD61F0020])
    clear = words([0x3900001F | (0x1B4 << 10), 0xD65F03C0])
    popup_table, callback_table = bytearray(0x210), bytearray(0x38)
    struct.pack_into('<Q', popup_table, 0x1E8, close)
    struct.pack_into('<Q', callback_table, 0x30, WINDOWS['callback_dispatch'][0])

    def padded(name, content):
        return WINDOWS[name][0], content + bytes(WINDOWS[name][1] - len(content))

    return SparseImage([
        padded('popup_event', handler), padded('modal_close', modal),
        padded('callback_dispatch', binder), padded('ad_close', clear),
        (POPUP_VTABLE, popup_table), (CALLBACK_VTABLE, callback_table),
        (CLOSE_LABEL, b'BTN_CLOSE\0'),
        (0x10008D060, words([0x52802009, 0x79000000 | (0xA0 << 10) | (19 << 5) | 9])),
    ])


class AdStateTests(unittest.TestCase):
    def test_initialization_sets_state_true_and_preserves_neighbors(self):
        self.assertEqual(emulate_game_initialisation(fixture()), {
            'byte_0x140': 0, 'byte_0x141': 1, 'adjacent_bytes_preserved': True})

    def test_accepted_close_clears_latch_and_requests_removal(self):
        result = emulate_popup_event(fixture())
        self.assertEqual(result['pending_after'], 0)
        self.assertTrue(result['modal_removal_requested'])
        self.assertTrue(result['caller_stack_and_registers_restored'])

    def test_wrong_event_type_preserves_owned_latch(self):
        for value in (0, 2):
            with self.subTest(event_type=value):
                result = emulate_popup_event(fixture(), event_type=value)
                self.assertEqual(result['pending_after'], 1)
                self.assertFalse(result['modal_removal_requested'])

    def test_wrong_label_and_null_event_are_ignored(self):
        for case in ({'label': 'OTHER'}, {'event_present': False}):
            with self.subTest(case=case):
                result = emulate_popup_event(fixture(), **case)
                self.assertEqual(result['pending_after'], 1)
                self.assertFalse(result['modal_removal_requested'])

    def test_missing_callback_probe_does_not_invent_latch_owner(self):
        result = emulate_popup_event(fixture(), callback_present=False)
        self.assertTrue(result['modal_removal_requested'])
        self.assertEqual(result['pending_after'], 1)

    def test_unsigned_byte_scan_is_explicitly_bounded(self):
        start = 0x1000
        image = SparseImage([(start, words([
            0x39400000 | (0x141 << 10) | (19 << 5),
            0x39000000 | (0x141 << 10) | (20 << 5),
            0x39400000 | (0x140 << 10) | (19 << 5),
            0x79000000 | (0xA0 << 10) | (19 << 5),
        ]))])
        image.sections = [{'name': '__text', 'address': start, 'size': 16}]
        self.assertEqual(direct_byte_accesses(image), [
            {'address': '0x1000', 'operation': 'load', 'base_register': 19},
            {'address': '0x1004', 'operation': 'store', 'base_register': 20}])

    def test_uuid_rejected_before_any_code_is_examined(self):
        image = fixture()
        image.uuid = 'unsupported'
        with self.assertRaisesRegex(ValueError, 'UUID'):
            trace_image(image)

    def test_researched_window_guard_rejects_synthetic_code(self):
        image = fixture()
        image.uuid = UUID
        with self.assertRaisesRegex(ValueError, 'Changed instruction window'):
            verify_window(image, *WINDOWS['popup_event'])


if __name__ == '__main__':
    unittest.main()
