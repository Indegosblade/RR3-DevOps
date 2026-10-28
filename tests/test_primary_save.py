"""Evidence guards and original-instruction save scheduling counterexamples."""
import os
import importlib.util
from pathlib import Path
import unittest
import zipfile

from build_4k_v3 import BINARY_PATH
from scripts.trace_primary_save import probe_dispatch, trace, validate

ROOT = Path(__file__).resolve().parents[1]
INPUT = Path(os.environ.get('RR3_TEST_IPA', ROOT / '959112d6ace07153840144be3201b00f39ec0e91.ipa'))
HAS_UNICORN = importlib.util.find_spec('unicorn') is not None


class PrimarySaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not INPUT.is_file():
            raise unittest.SkipTest('Exact-build IPA unavailable')
        with zipfile.ZipFile(INPUT) as archive:
            cls.binary = archive.read(BINARY_PATH)

    @unittest.skipUnless(HAS_UNICORN, 'Optional unicorn emulator unavailable')
    def test_task_done_precedes_any_save_dispatch(self):
        result = probe_dispatch(self.binary)
        self.assertEqual(result['task_predicate'], 1)
        self.assertEqual(result['after_predicate'], result['after_request'])
        self.assertEqual(result['after_predicate']['pending'], 1)
        self.assertEqual(result['after_predicate']['serializer_calls'], 0)
        self.assertEqual(result['after_updates'][0]['serializer_calls'], 1)

    @unittest.skipUnless(HAS_UNICORN, 'Optional unicorn emulator unavailable')
    def test_zero_serializer_result_does_not_rearm_primary_request(self):
        result = probe_dispatch(self.binary, serializer_result=0, updates=2)
        first, second = result['after_updates']
        self.assertEqual(first, {'pending': 0, 'secondary_pending': 1,
                                 'serializer_calls': 1, 'secondary_calls': 0})
        self.assertEqual(second, {'pending': 0, 'secondary_pending': 0,
                                  'serializer_calls': 1, 'secondary_calls': 1})

    @unittest.skipUnless(HAS_UNICORN, 'Optional unicorn emulator unavailable')
    def test_wrong_thread_keeps_request_without_serializer_dispatch(self):
        result = probe_dispatch(self.binary, same_thread=False)
        self.assertEqual(result['after_updates'][0], result['after_request'])
        self.assertIn('wrong_thread_log', result['calls'])

    @unittest.skipUnless(HAS_UNICORN, 'Optional unicorn emulator unavailable')
    def test_blocked_update_preserves_primary_pending(self):
        result = probe_dispatch(self.binary, blocked=True)
        self.assertEqual(result['after_updates'][0], result['after_request'])
        self.assertNotIn('primary_serializer', result['calls'])

    @unittest.skipUnless(HAS_UNICORN, 'Optional unicorn emulator unavailable')
    def test_clear_character_byte_still_requests_primary_without_secondary(self):
        result = probe_dispatch(self.binary, character_byte_set=False)
        self.assertEqual(result['after_request']['pending'], 1)
        self.assertEqual(result['after_request']['secondary_pending'], 0)
        self.assertEqual(result['after_updates'][0]['serializer_calls'], 1)
        self.assertEqual(result['after_updates'][0]['secondary_calls'], 0)

    def test_guard_rejects_changed_predicate_update_and_name(self):
        for offset in (0x3C13E4, 0x646150, 0x25B45A4, 0x4F0280, 0x4F0494, 0x142494):
            altered = bytearray(self.binary)
            altered[offset] ^= 1
            with self.assertRaises(ValueError):
                validate(altered)
        self.assertEqual(trace(self.binary)['save_manager']['normal_filename'], 'character.2.dat')


if __name__ == '__main__':
    unittest.main()
