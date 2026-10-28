"""Exact original bounded windows plus synthetic metadata, heap and server policy.

The additional fixture is 1592 instruction bytes; the base fixture is shared with
request-delivery tests. No IPA, device, save or service is needed.
"""
import base64
import struct
import unittest
import zlib

from test_request_delivery import fixture as delivery_fixture
from scripts.probe_inline_rejection import (
    CAVE, CAVE_SIZE, ID_STORE, PRE_CALL, VTABLES, WINDOWS,
    patch_fresh_zero_store, probe, validate,
)

CODE = (
    'eJylU1FoW1UY/s89CZ6kXWU07WZFkrRzrC97KhalbDdL7JbOrlIDYRuYtGKbtI49jM2HIAtLkHb1wQsZwh6mMtTegFAxghmocYXB'
    'KIpBNl/T+pIuT7LS3Vt2uX4nMW4kVR98CDn3/75zvu98/3/sDCsbMUXfjnJ9a8KhWymnbgWZtsVZ/iGnvFgJvCycNHxxTi3ecxjD'
    '1Qxb6b133PytK2BEHVRITqvFxBm1aPDe/AO+L3/SrxYvs5752hcf9+3/+ur1sdPzxpxtf+PlvbWSQhH3gFqMAX9HrlNy7ZpnWLsu'
    'q8WjTMx/yigizqrF5Ctq0QvMj28aGNUVRmtT/SFdMLYWI1GbIopcSGVzPkFDFU7a+yeiuQT2VL1UlN/rF0i7QunJF8aiuWR9n2tN'
    'WMd+bcV7gF8E/oMiaiq0lkfVb1s5neAkDqqm5DDbjsj7tnK45LzZXrfCqE+31x/J+kx7/Q/UN/Bd4d35de7Ju49TTuKXcD8r9Sp6'
    'FEKvgroRO6bbGaaVeOy+6yZpVZl/fyPbB8hefPXR9Udn5ox3Zfast5ZGXm5/Ax/HWvLjfaoZt+zCJifTRao5+JxqrkNLmWKajx29'
    '/096dpCVt6MKMI55wcxwpj3EvGxhXqTXZ4PR3MIuvfg8FM0t/ksvbgC/9h+9uAbOwlO9WNilFx+Emhl6kGF3/rNAI8O9QZlhCL6D'
    'uBPuE2zc5/H5W/rOLNN3ewd2RpTlW9jG3TD7v/S8p5oV3pO/+bMrR4yGPjmimp7Rfbkq8BLyrLxBheoSmZcU8iz2BwblDCunKCIx'
    'n5MKNjCBrIXMOujQbm+QRsi6n8gDLa01853ZgP74/J3leu6rvLw54Dq3M+sG1gFOJ7h74LVLtzL87zcr32jT5+zdJz5/CjR8yr6n'
    '98NnN5lv0xOfGx0UkVilAz67n/KZaXg8Da6VOgXNcWi/Bg8n4W9M3xwIn4O3epZbE9/DD0N2pEkvJ15nK4Id0ASRST7MG1EhfpDM'
    'L2eyeBekST0v3rOczwow4UxPKtARjvSknMlDyYQhteV7sFIBaN9evjGT9eyq8+OLbTrj/0PnCHTknYYOt+sR9g0fzuaqE+xD4d9T'
    '141fKY1QOj2S6EJunWQ2z5FnNHmHpL90aUR0QhMcH/gSl78+6LgPBHThkLNydWmO6KW6t3DCsFepbKUU9Jm0QdQ2n8Feh2qhV1bl'
    'efpufaDRIxv1Cta/k5x1zPgqac3z757Nely+gK7gfHIuLiVxvuyxEp42/PhXyVvnLf7F4y08Hn6rzouD9ye9WoA4'
)


def fixture():
    binary = bytearray(delivery_fixture())
    # Add one synthetic executable section so header-padding guards also run.
    struct.pack_into('<I', binary, 20, 176)
    struct.pack_into('<I', binary, 60, 152)
    struct.pack_into('<I', binary, 120, 1)
    struct.pack_into('<16s16sQQIIIIIIII', binary, 128, b'__text', b'__TEXT',
                     0x100004000, len(binary) - 0x4000, 0x4000, 2, 0, 0,
                     0x80000400, 0, 0, 0)
    raw, cursor = zlib.decompress(base64.b64decode(CODE)), 0
    for start, end, _ in WINDOWS.values():
        size = end - start
        binary[start:end] = raw[cursor:cursor + size]
        cursor += size
    assert cursor == len(raw)
    for address, slots in VTABLES.items():
        for offset, target in slots.items():
            struct.pack_into('<Q', binary, address - 0x100000000 + offset, target)
    return bytes(binary)


class InlineRejectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = fixture()

    def test_accepted_requests_keep_live_handles_and_defer_callbacks(self):
        result = probe(self.binary)
        self.assertEqual(result['pending_records'], 2)
        self.assertEqual(result['post_delete_writes'], [])
        self.assertTrue(all(not event['already_deleted'] and event['request_id'] > 0
                            for event in result['events'] if event['event'] == 'bridge_result'))
        self.assertNotEqual(result['helper']['group_handle'], '0x0')
        self.assertNotEqual(result['helper']['entries_handle'], '0x0')
        self.assertEqual(result['starts'][1]['cache_key'], -1)
        self.assertEqual(result['helper_completions'], 0)

    def test_each_conditional_rejection_deletes_before_store_then_loses_early_error(self):
        for rejected in ((0x28F4,), (0x28ED,), (0x28F4, 0x28ED)):
            with self.subTest(rejected=rejected):
                result = probe(self.binary, rejected=rejected)
                self.assertEqual(result['pending_records'], 2 - len(rejected))
                self.assertEqual(len(result['post_delete_writes']), len(rejected))
                starts = {item['operation']: item['address'] for item in result['starts']}
                for op in rejected:
                    obj = starts[hex(op)]
                    self.assertIn({'pc': '0x100165574', 'object': obj, 'offset': '0x10',
                                   'size': 4, 'value': 0}, result['post_delete_writes'])
                    deletes = [i for i, event in enumerate(result['events'])
                               if event['event'] == 'delete' and event['address'] == obj]
                    stores = [i for i, event in enumerate(result['events'])
                              if event['event'] == 'bridge_result' and event['address'] == obj]
                    self.assertEqual(len(deletes), 1)
                    self.assertLess(deletes[0], stores[0])
                    self.assertTrue(result['events'][deletes[0]]['sync_lock_held'])
                replies = [event for event in result['events'] if event['event'] == 'helper_response']
                self.assertEqual(len(replies), len(rejected))
                self.assertTrue(all(event['pending'] == 0 and event['empty']
                                    and event['sync_lock_held'] for event in replies))
                arm = [event for event in result['events'] if event['event'] == 'before_arm'][0]
                self.assertEqual(arm['error'], 1)
                self.assertEqual(arm['group_received'], int(0x28F4 in rejected))
                self.assertEqual(arm['entries_received'], int(0x28ED in rejected))
                state = result['helper']
                self.assertEqual(state['group_handle'] == '0x0', 0x28F4 in rejected)
                self.assertEqual(state['entries_handle'] == '0x0', 0x28ED in rejected)
                self.assertEqual((state['pending'], state['group_received'],
                                  state['entries_received'], state['error']), (1, 0, 0, 0))
                self.assertEqual(result['helper_completions'], 0)
                self.assertEqual(result['sync_lock_after'], 0)

    def test_changed_lifetime_window_and_vtable_are_refused(self):
        for offset in (0x15742C, 0x2B60978):
            with self.subTest(offset=offset):
                changed = bytearray(self.binary)
                changed[offset] ^= 1
                with self.assertRaises(ValueError):
                    validate(changed)

    def test_unrelated_rejection_operations_are_refused(self):
        with self.assertRaises(ValueError):
            probe(self.binary, rejected=(0x28D3,))

    def test_candidate_preserves_full_accepted_and_rejected_flow_except_dead_store(self):
        for rejected in ((), (0x28F4,), (0x28ED,), (0x28F4, 0x28ED)):
            with self.subTest(rejected=rejected):
                original = probe(self.binary, rejected=rejected)
                candidate = probe(self.binary, rejected=rejected, experimental=True)
                self.assertEqual(candidate['post_delete_writes'], [])
                self.assertEqual(len(original['post_delete_writes']), len(rejected))
                for key in ('events', 'starts', 'helper', 'helper_completions', 'pending_records',
                            'live_request_ids', 'caller_state', 'boundary_nzcv', 'sync_lock_after'):
                    self.assertEqual(candidate[key], original[key], key)
                self.assertTrue(all(before == after for before, after in candidate['boundary_nzcv']))
                self.assertEqual(candidate['caller_state']['callee_saved'],
                                 [0xABCD0000 + index for index in range(19, 30)])
                self.assertEqual(candidate['caller_state']['vector_callee_saved'],
                                 [0xFEDC0000 + index for index in range(8, 16)])

    def test_candidate_preserves_null_wrapper_and_nonzero_initial_id_contract(self):
        for initial in (0, 77):
            with self.subTest(initial=initial):
                original = probe(self.binary, initial_request_id=initial, manager_present=False)
                candidate = probe(self.binary, initial_request_id=initial, manager_present=False,
                                  experimental=True)
                for key in ('events', 'helper', 'live_request_ids', 'caller_state', 'boundary_nzcv',
                            'post_delete_writes', 'pending_records'):
                    self.assertEqual(candidate[key], original[key], key)
                self.assertEqual(candidate['live_request_ids'], {'0x28f4': 0, '0x28ed': 0})

    def test_nonzero_initial_id_rejection_is_deliberately_not_fixed(self):
        original = probe(self.binary, rejected=(0x28F4, 0x28ED), initial_request_id=77)
        candidate = probe(self.binary, rejected=(0x28F4, 0x28ED), initial_request_id=77,
                          experimental=True)
        self.assertEqual(len(candidate['post_delete_writes']), 2)
        self.assertEqual(candidate['events'], original['events'])
        self.assertTrue(all(write['pc'] == hex(0x100000000 + CAVE + 24)
                            for write in candidate['post_delete_writes']))

    def test_wrapped_accepted_zero_id_preserves_original_live_state(self):
        original = probe(self.binary, counter_seed=0xFFFFFFFF)
        candidate = probe(self.binary, counter_seed=0xFFFFFFFF, experimental=True)
        self.assertEqual(original['live_request_ids'], {'0x28f4': 0, '0x28ed': 1})
        self.assertEqual(candidate['live_request_ids'], original['live_request_ids'])
        self.assertEqual(candidate['events'], original['events'])
        self.assertEqual(candidate['post_delete_writes'], [])
        self.assertEqual(candidate['pending_records'], 2)

    def test_candidate_is_bounded_reversible_and_refuses_changed_guards(self):
        patched, plan = patch_fresh_zero_store(self.binary)
        allowed = {offset for start, size in ((PRE_CALL, 4), (ID_STORE, 4), (CAVE, CAVE_SIZE))
                   for offset in range(start, start + size)}
        self.assertEqual(len(patched), len(self.binary))
        self.assertTrue(all(offset in allowed for offset, (old, new) in enumerate(zip(self.binary, patched))
                            if old != new))
        restored = bytearray(patched)
        for change in plan['changes']:
            offset, data = int(change['file_offset'], 16), bytes.fromhex(change['original'])
            restored[offset:offset + len(data)] = data
        self.assertEqual(restored, self.binary)
        for offset in (48, 0x1654EC, 0x1538C4, 0x154E58, CAVE):
            with self.subTest(offset=offset):
                changed = bytearray(self.binary)
                changed[offset] ^= 1
                with self.assertRaises(ValueError):
                    patch_fresh_zero_store(changed)
        # Header commands ending beyond cave, an earlier first section and a
        # non-executable __TEXT mapping each independently invalidate the cave.
        for offset, value in ((20, 0x3900), (176, 0x3800), (116, 1)):
            with self.subTest(metadata=offset):
                changed = bytearray(self.binary)
                struct.pack_into('<I', changed, offset, value)
                with self.assertRaises(ValueError):
                    patch_fresh_zero_store(changed)
        with self.assertRaises(ValueError):
            patch_fresh_zero_store(patched)


if __name__ == '__main__':
    unittest.main()
