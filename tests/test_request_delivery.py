"""Original instruction windows with synthetic metadata, objects, and API hooks.

Fixtures contain only the 6,408 guarded instruction bytes, compressed for source
size. No IPA, device, signing material, save, or network service is required.
"""
import base64
import struct
import unittest
import zlib

from build_4k_v3 import SUPPORTED_MACHO_UUID
from scripts.trace_request_delivery import (
    BASE, VTABLES, WINDOWS, probe_cancel, probe_helper_early_responses,
    probe_http_drain, probe_submit, probe_failed_batch, trace, validate,
)

# Concatenated in WINDOWS insertion order, independently checked by SHA-256.
CODE = (
    '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'
)


def fixture():
    binary = bytearray(0x2C65000)
    struct.pack_into('<8I', binary, 0, 0xFEEDFACF, 0x100000C, 0, 2, 2, 96, 0, 0)
    struct.pack_into('<II16s', binary, 32, 0x1B, 24, SUPPORTED_MACHO_UUID)
    struct.pack_into('<II16sQQQQiiII', binary, 56, 0x19, 72, b'__TEXT',
                     BASE, len(binary), 0, len(binary), 7, 5, 0, 0)
    data, cursor = zlib.decompress(base64.b64decode(CODE)), 0
    for start, end, _ in WINDOWS.values():
        binary[start:end] = data[cursor:cursor + end - start]
        cursor += end - start
    assert cursor == len(data)
    for index, (address, label, slots) in enumerate(VTABLES.values()):
        ti, name = 0x1000 + index * 0x100, 0x1080 + index * 0x100
        struct.pack_into('<Q', binary, address - BASE - 8, BASE + ti)
        struct.pack_into('<Q', binary, ti + 8, BASE + name)
        binary[name:name + len(label) + 1] = label.encode() + b'\0'
        for slot, target in slots.items():
            struct.pack_into('<Q', binary, address - BASE + slot, target)
    return bytes(binary)


class RequestDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = fixture()

    def test_exact_build_and_complete_instruction_guards(self):
        validate(self.binary)
        for label, (start, end, _) in WINDOWS.items():
            with self.subTest(window=label):
                changed = bytearray(self.binary)
                changed[end - 1] ^= 1
                with self.assertRaisesRegex(ValueError, label):
                    validate(changed)
        changed = bytearray(self.binary)
        changed[40] ^= 1
        with self.assertRaisesRegex(ValueError, 'UUID'):
            validate(changed)

    def test_virtual_dispatch_mapping_is_guarded(self):
        changed = bytearray(self.binary)
        changed[0x2C61E20] ^= 1
        with self.assertRaisesRegex(ValueError, 'vtable'):
            validate(changed)

    def test_accepted_submit_can_append_while_previous_batch_is_active(self):
        result = probe_submit(self.binary)
        self.assertEqual(result['request_id'], 1)
        self.assertEqual(result['pending_records'], 1)
        self.assertEqual(result['active_records'], 1)
        self.assertEqual(result['active_http_id'], 77)
        self.assertEqual(result['callbacks'], [])
        self.assertEqual(result['sync_lock_after'], 0)

    def test_rejection_has_inline_empty_delivery_and_zero_id(self):
        result = probe_submit(self.binary, rejected=True)
        self.assertEqual(result['request_id'], 0)
        self.assertEqual(result['pending_records'], 0)
        self.assertEqual(result['callbacks'], [{'sync_lock_held': True, 'blob_pointer': 0}])
        self.assertEqual(result['active_http_id'], 77)
        self.assertEqual(result['sync_lock_after'], 0)

    def test_cancel_detaches_callback_in_either_vector_without_canceling_batch(self):
        for location in ('pending', 'active'):
            with self.subTest(location=location):
                result = probe_cancel(self.binary, location=location)
                self.assertEqual(result['abandoned'], 1)
                self.assertFalse(result['callback_retained'])
                self.assertEqual(result['closure_destructions'], 1)
                self.assertEqual(result['active_http_id'], 77)

    def test_unknown_cancellation_preserves_callback(self):
        result = probe_cancel(self.binary, matching=False)
        self.assertEqual(result['abandoned'], 0)
        self.assertTrue(result['callback_retained'])
        self.assertEqual(result['closure_destructions'], 0)

    def test_completed_http_callback_is_once_and_outside_mutex(self):
        result = probe_http_drain(self.binary)
        self.assertEqual(result['first_delivery_count'], 1)
        self.assertEqual(result['after_second_drain_count'], 1)
        self.assertEqual(result['remaining_requests'], 0)
        self.assertEqual(result['request_destructions'], 1)
        self.assertEqual(result['callbacks'], [{'http_lock_held': False, 'http_id': 77,
                                               'bytes': 4, 'buffer': True, 'delivery_claimed': 1}])

    def test_incomplete_http_request_is_retained_without_callback(self):
        result = probe_http_drain(self.binary, completed=False)
        self.assertEqual(result['callbacks'], [])
        self.assertEqual(result['remaining_requests'], 1)
        self.assertEqual(result['request_destructions'], 0)

    def test_completed_request_without_callback_still_retires(self):
        result = probe_http_drain(self.binary, callback_present=False)
        self.assertEqual(result['callbacks'], [])
        self.assertEqual(result['remaining_requests'], 0)
        self.assertEqual(result['request_destructions'], 1)

    def test_failed_batch_delivers_empty_and_does_not_requeue_old_record(self):
        result = probe_failed_batch(self.binary)
        self.assertEqual(result['deliveries'], [{'empty_blob': True, 'active_records': 0}])
        self.assertEqual(result['pending_records'], 1)
        self.assertEqual(result['active_records'], 0)
        self.assertEqual(result['old_record_delivered'], 1)
        self.assertEqual(result['next_dispatch_calls'], [{'pending_records': 1, 'active_http_id': 0}])

    def test_early_helper_error_is_cleared_by_post_launch_arm(self):
        for early in ('group', 'entries', 'both'):
            with self.subTest(early=early):
                result = probe_helper_early_responses(self.binary, early=early)
                before, after = result['before_post_launch_arm'], result['after_post_launch_arm']
                self.assertEqual(before['pending'], 0)
                self.assertEqual(before['error'], 1)
                self.assertEqual(before['group_received'], int(early in ('group', 'both')))
                self.assertEqual(before['entries_received'], int(early in ('entries', 'both')))
                self.assertEqual(after, {'pending': 1, 'group_received': 0,
                                         'entries_received': 0, 'error': 0})
                self.assertEqual(result['completion_calls'], 0)

    def test_report_bounds_the_claim_and_emits_no_candidate(self):
        result = trace(self.binary)
        self.assertIn('No universal deferred-callback', ' '.join(result['limits']))
        self.assertIn('No durable generation', result['durability'])
        self.assertNotIn('patch', result)

    def test_invalid_probe_parameters_are_rejected(self):
        for call in (lambda: probe_submit(self.binary, rejected=1),
                     lambda: probe_cancel(self.binary, location='all'),
                     lambda: probe_http_drain(self.binary, completed=1),
                     lambda: probe_helper_early_responses(self.binary, early='neither')):
            with self.assertRaises(ValueError):
                call()


if __name__ == '__main__':
    unittest.main()
