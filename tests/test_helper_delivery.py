"""Original bounded constructor/cleanup/timer windows and synthetic heap/UI."""
import base64
import struct
import unittest
import zlib
from test_inline_rejection import fixture as inline_fixture
from scripts.probe_helper_delivery import WINDOWS, CAVE, CAVE_SIZE, patch_helper_delivery, probe

CODE = (
    'eJxtVF9oW2UUP9+9Sf2ybp21SVpfduMGkqAollrN2nU37Tq2IZuE6nzr7UBIV5lutJM5a25r1cTJ9LqMwHywG2P0XhWKZLMRxM7u'
    'YdgH15c+CGo6JxQiUmYa8tVm8fetKYyyh8P3nXPPn+/8fufc4uEf7MIhZpdPK3b5fbL+VckpQBJ1XVPPk57VmG9ghFGPcanLVhjN'
    'Bi/rdojx2V7y5K8T9RRV5iyo3Ln31lhqQfU7JqOW8wplv1RYPofvwYRu7yc+u6Pcec64TZb0/eXIf+kgmdFYsytcPt2J+hG7eHhm'
    'YlrtnS9ueE9BVRz5Ju1dsgObdUGMMhqxPM4eTrrgHmnbPW/4SWwi8sZxcpyxTrJiuMsYD/xCW3Qhawfgm1D0bKyZsvH3XHZ8G4nz'
    'l3Tby3x5Azlb3KXvcqrX+XtgLGWMqrafvGdOPkmI9Tm3YU8eH0ud3C5rmI/FopSlO3TI6Pyg3ej8EPIRJAFJQj5uj1+jrIfMz/uv'
    '1Nr9P6PevS12/CgJeytbCgz/tMsYPdseW4H9rhqOKS4rvolltedoKq6w7Do+ObXB2YhR3xtjqWuVSuNGrCROhF7HiTL3salfwyau'
    'kDBqHmKvISFrDx7VRQa4Gsd0sYgeNfLmp8EdBdS53y6spqV+sVLpicFv8BiJHHD8QuIT1YWBnMarJNJS31vVD5A4J/WdVb2DxKfQ'
    'B5/RRYtCmaFmXUiMf1S8+RHUkbzJu5yXibt/vHj1CM0lKpXWcUUXI4gT6NVA7GAziWGZd1s1L3g4BV1ybfh1oRHPm8iRk326zaiC'
    'vNxlRiX/wf5YSfb8MDwrM2yu1KtCd8HuBp41wJNZy6rqFDF/Bcy4xDbRxm7x+m7BGXBqJPHPnZX0vg7YRh6xMHOCR2ot/igT2k3X'
    'KT7useRsYE6/8e2D7SUmJlbpFoW7y/QyK8tdef2vlXROlTvR4FwfVVJXWz+JvrLTOSFtF3GP4P79AXdq3WcKPve/KVpz5gH7t+v2'
    'OqqffcD+ddXOCsloX5tz4ga+0XYzOvXsO6ll9NMIbAiSgV6E/loHm2z60yd7meQLu6ymANl4ty19voJPE3qcHp1uJ9Nsv1mHOdqM'
    'WWiQ8+B3LsgcO1AXkqvuyq8zy+mhg0wsNoAb5s+Ds55FcNMIbjzAMNT/dilX3cmhgxEh4xYQF7ixnDagM+xABPfYm+wzGl6bX0+y'
    'kkaeFtNFW40oKy826iLZxiZD4CWEnLsZzzPs8RrPe8FnN3jdY5d6u2zwbEm+f8dbPYGIzVzYA3fyTD9Rq9wLtr+vFCBtPgh7cpWW'
    'QsmnLb7UFdbcdPwJBf+bpj3hRUYvcB7JcsZqOWdZz5WzUY15Bp5CTbmzvMkV1pbUMHl1YVb3jT2uC5lX1v4fjroaHg=='
)


def fixture():
    binary = bytearray(inline_fixture())
    raw, cursor = zlib.decompress(base64.b64decode(CODE)), 0
    for start, end, _ in WINDOWS.values():
        size = end - start
        binary[start:end] = raw[cursor:cursor + size]
        cursor += size
    assert cursor == len(raw)
    struct.pack_into('<I', binary, 0x3E5EF4, 0x94000000 | (((0x1567B4 - 0x3E5EF4) // 4) & 0x3FFFFFF))
    # Exact original vtable slots; synthetic local pointers and constants.
    for address, target in ((0x102BAE588, 0x1003E71E8), (0x102BAE598, 0x1003E7248),
                            (0x102BAE5A0, 0x1003E724C), (0x102BAE5A8, 0x1003E7250),
                            (0x102B60920, 0x100165494), (0x102B60990, 0x100165494)):
        struct.pack_into('<Q', binary, address - 0x100000000, target)
    return bytes(binary)


class HelperDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = fixture()

    def check_completion(self, result, error):
        self.assertEqual(len(result['completions']), 1)
        event = result['completions'][0]
        self.assertTrue(event['ready'])
        self.assertFalse(event['lock'])
        self.assertEqual(event['state']['pending'], 0)
        self.assertEqual(event['state']['error'], error)
        self.assertEqual(result['screen_done'], 0)
        self.assertTrue(all(item['pending'] == 0 and not item['ready'] for item in result['starts']))
        self.assertEqual(result['constructor_registers'], [0xABCD0000 + i for i in range(19, 30)])
        self.assertEqual(result['final_registers'], [0xABCD0000 + i for i in range(19, 30)])
        self.assertEqual(result['preserved_d'], [0xFEDC0000 + i for i in range(8, 16)])
        self.assertEqual(result['sp'], 0x71000F000)

    def test_original_erases_early_error(self):
        result = probe(self.binary, early=(('group', 'error'),))
        self.assertEqual(result['snapshots'][-1]['state']['error'], 1)
        self.assertEqual(result['constructed']['error'], 0)
        self.assertEqual(result['completions'], [])

    def test_each_early_error_completes_on_first_update(self):
        for early in ((('group', 'error'),), (('entries', 'error'),),
                      (('group', 'error'), ('entries', 'error'))):
            with self.subTest(early=early):
                self.check_completion(probe(self.binary, early=early, candidate=True), 1)

    def test_success_both_early_preserves_rank_and_defers(self):
        result = probe(self.binary, early=(('group', 'success'), ('entries', 'success')), candidate=True)
        self.check_completion(result, 0)
        self.assertEqual(result['constructed']['rank_bytes'], result['snapshots'][-1]['state']['rank_bytes'])
        self.assertNotEqual(result['constructed']['rank_bytes'], result['snapshots'][0]['state']['rank_bytes'])
        self.assertEqual(result['final']['elapsed'], 0)

    def test_each_early_success_waits_for_other_late_response(self):
        for first, second in (('group', 'entries'), ('entries', 'group')):
            early = ((first, 'success'),)
            waiting = probe(self.binary, early=early, candidate=True)
            self.assertEqual(waiting['completions'], [])
            self.assertEqual(waiting['final']['pending'], 1)
            self.check_completion(probe(self.binary, early=early, late=((second, 'success'),), candidate=True), 0)
            self.check_completion(probe(self.binary, early=early, late=((second, 'error'),), candidate=True), 1)

    def test_accepted_late_orders_remain_identical(self):
        for late in ((('group', 'success'), ('entries', 'success')),
                     (('entries', 'success'), ('group', 'success')),
                     (('group', 'error'),), (('entries', 'error'),)):
            original = probe(self.binary, late=late)
            candidate = probe(self.binary, late=late, candidate=True)
            self.assertEqual(original['constructed'], candidate['constructed'])
            self.assertEqual(original['final'], candidate['final'])
            self.assertEqual(original['completions'], candidate['completions'])
            self.check_completion(candidate, int(any(kind == 'error' for _, kind in late)))

    def test_neither_and_timeout_unchanged(self):
        for ticks in (0, 1, 29999, 30000):
            original = probe(self.binary, ticks=ticks)
            candidate = probe(self.binary, ticks=ticks, candidate=True)
            self.assertEqual(original['final'], candidate['final'])
            self.assertEqual(original['completions'], candidate['completions'])
        self.check_completion(probe(self.binary, ticks=30000, candidate=True), 1)

    def test_duplicates_and_cancellation_do_not_complete_twice(self):
        late = (('group', 'success'), ('entries', 'success'), ('entries', 'success'), ('group', 'error'))
        self.check_completion(probe(self.binary, late=late, candidate=True), 0)
        for early in ((), (('group', 'error'),), (('group', 'success'), ('entries', 'success'))):
            result = probe(self.binary, early=early, candidate=True, cancel=True)
            self.assertEqual(result['completions'], [])
            self.assertEqual(result['final']['pending'], 0)
            self.assertEqual(len(result['cancelled']), 2 - len(early))

    def test_constructor_initializes_sentinel_heap(self):
        result = probe(self.binary, candidate=True, updates=0)
        initial = result['snapshots'][0]['state']
        self.assertEqual([initial[key] for key in ('pending', 'group', 'entries', 'error', 'elapsed')], [0] * 5)
        self.assertEqual(result['constructed']['pending'], 1)
        self.assertEqual(result['completions'], [])

    def test_patch_is_bounded_reversible_and_original_guarded(self):
        for combined in (False, True):
            changed, plan = patch_helper_delivery(self.binary, include_fresh_id_guard=combined)
            restored = bytearray(changed)
            allowed = set()
            for region in plan['changes']:
                offset = int(region['file_offset'], 16)
                old, new = bytes.fromhex(region['original']), bytes.fromhex(region['replacement'])
                self.assertEqual(changed[offset:offset + len(new)], new)
                restored[offset:offset + len(old)] = old
                allowed.update(range(offset, offset + len(old)))
            self.assertEqual(bytes(restored), self.binary)
            self.assertTrue(all(i in allowed for i, (a, b) in enumerate(zip(self.binary, changed)) if a != b))
            with self.assertRaises(ValueError):
                patch_helper_delivery(changed)
        for offset in (CAVE, CAVE + CAVE_SIZE - 1, 0x155FF4, 0x3E50F8, 0x1567C4, 0x1564EC, 0x2BAE5A8):
            changed = bytearray(self.binary)
            changed[offset] ^= 1
            with self.assertRaises(ValueError):
                patch_helper_delivery(bytes(changed))


if __name__ == '__main__':
    unittest.main()
