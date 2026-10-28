"""Controlled original-instruction tests of pending-result durability boundaries.

Two short instruction fixtures run with synthetic records and file/API hooks.
They do not simulate the whole game, real file codec, or character save.
"""
import struct
import unittest

from build_4k_v3 import SUPPORTED_MACHO_UUID
from scripts.trace_ordinary_postrace import (
    ACTIVATION_TAIL, CALLBACK, ENTRY_DISPATCH, EVENTS_UPDATE,
    POLL, POLL_OFFSET, ROUTE, ROUTE_OFFSET, SAVE,
    probe_events_cadence, probe_queue_reply, validate,
)

CALLBACK_CODE = bytes.fromhex(
    'ff4301d1f65702a9f44f03a9fd7b04a9fd030191f30300aa292041291f01096b'
    '620400542a0040f9ea0300f9e9230129e91300b9ff1f00b9e0030091e1730091'
    '8200805265f64c94f51f40b9ff1f00b9e0030091e1730091820080525ff64c94'
    'f41f40b9ff0300f9e00300919ef44c94f5010034bf0e0071e1000054410d01f0'
    '21e80a91420d01f0423c0c9140008052bee1f1979f0600716100005460220091'
    '38000094680640f9680a00f9e00313aa21008052c0feff97fd7b44a9f44f43a9'
    'f65742a9ff430191c0035fd6'
)
SAVE_CODE = bytes.fromhex(
    'ffc301d1f85f03a9f65704a9f44f05a9fd7b06a9fd830191f40301aaf30300aa'
    '81fc00f021e80491e00300912368159443e10794e20300aa410d01f0214c0a91'
    'e0030091f669159400050034e0030091a1008052cc6a159469a240a9080109cb'
    '08fd42d3351e9e52151ebe72017d151be0030091c46a159468a640a9290108cb'
    '29fd42d3297d151b3f050071cb010054160080d2170080d20001168be1030091'
    '86feff97f706009168a640a9290108cb29fd42d3297d151bd6120191ffc229eb'
    'cbfeff54e133c039e0030091946a1594e00300915c681594940000367f020039'
    '680640f9680a00f9e00300912a681594fd7b46a9f44f45a9f65744a9f85f43a9'
    'ffc30191c0035fd6'
)
EVENTS_UPDATE_CODE = bytes.fromhex(
    'f44fbea9fd7b01a9fd430091f30300aa08984b391f050071810000547f9a0b39'
    '609e40f963941494887e01f008213991080140f908a954b91f05003140010054'
    '689e40f900fd41f92100805222008052b74b1694689e40f900fd41f921008052'
    '4a4a1694605a41f9000100b4c87e019008a13991080140f9080940f91f0100f1'
    'e1179f1a1d0e0a94604641f9e00200b4743e41f9b40200b4883240b91f1d0071'
    '41020054f1861d94e10300aa68d242b91f00086bc100005468d642b908050071'
    'c000005408a19f5a0700001461d202b94801805204000014801240b93bb0f997'
    '0800805268d602b9fd7b41a9f44fc2a8c0035fd6'
)
ACTIVATION_TAIL_CODE = bytes.fromhex(
    'e00316aaeaf2ff97df920b39dfa20b3940a905945aa905943ea905943eab0594'
    '28008052c89e0b39'
)


def fixture():
    binary = bytearray(ROUTE_OFFSET + len(ROUTE))
    struct.pack_into('<8I', binary, 0, 0xFEEDFACF, 0x100000C, 0, 2, 1, 24, 0, 0)
    struct.pack_into('<II16s', binary, 32, 0x1B, 24, SUPPORTED_MACHO_UUID)
    binary[CALLBACK:CALLBACK + len(CALLBACK_CODE)] = CALLBACK_CODE
    binary[SAVE:SAVE + len(SAVE_CODE)] = SAVE_CODE
    binary[POLL_OFFSET:POLL_OFFSET + len(POLL)] = POLL
    binary[ROUTE_OFFSET:ROUTE_OFFSET + len(ROUTE)] = ROUTE
    binary[EVENTS_UPDATE:EVENTS_UPDATE + len(EVENTS_UPDATE_CODE)] = EVENTS_UPDATE_CODE
    binary[ACTIVATION_TAIL:ACTIVATION_TAIL + len(ACTIVATION_TAIL_CODE)] = ACTIVATION_TAIL_CODE
    binary[0x29E490:0x29E490 + len(ENTRY_DISPATCH)] = ENTRY_DISPATCH
    return bytes(binary)


class OrdinaryPostraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = fixture()

    def test_empty_response_rewrites_the_current_queue_then_unloads(self):
        result = probe_queue_reply(self.binary, response=None, memory_records=2, persisted_records=1)
        self.assertEqual(result['headers'], [5, 2])
        self.assertEqual(result['written_records'], 2)
        self.assertEqual(result['output_persisted_records'], 2)
        self.assertEqual((result['output_loaded'], result['output_memory_records']), (0, 0))
        self.assertNotIn('acknowledge', result['events'])

    def test_failed_write_preserves_unsaved_records_added_while_request_pending(self):
        result = probe_queue_reply(self.binary, memory_records=2, persisted_records=1, writable=False)
        self.assertEqual(result['written_records'], 0)
        self.assertEqual(result['output_persisted_records'], 1)
        self.assertEqual((result['output_loaded'], result['output_memory_records']), (1, 2))
        self.assertNotIn('close', result['events'])
        # A subsequent successful attempt can persist the retained newer record.
        retry = probe_queue_reply(self.binary, memory_records=result['output_memory_records'],
                                  persisted_records=result['output_persisted_records'])
        self.assertEqual(retry['output_persisted_records'], 2)

    def test_nonzero_response_acknowledges_then_persists_empty_queue(self):
        result = probe_queue_reply(self.binary, response=(1, 1))
        self.assertEqual(result['headers'], [5, 0])
        self.assertEqual(result['output_persisted_records'], 0)
        self.assertEqual(result['events'].count('acknowledge'), 1)
        self.assertLess(result['events'].index('acknowledge'), result['events'].index('open_write'))
        self.assertEqual(result['written_records'], 0)

    def test_zero_response_status_preserves_queue_contents_before_rewrite(self):
        result = probe_queue_reply(self.binary, response=(0, 0))
        self.assertEqual(result['headers'], [5, 2])
        self.assertEqual(result['output_persisted_records'], 2)
        self.assertNotIn('acknowledge', result['events'])

    def test_exact_instruction_guards_and_probe_arguments_are_enforced(self):
        validate(self.binary)
        for offset in (40, CALLBACK, SAVE, POLL_OFFSET, ROUTE_OFFSET):
            modified = bytearray(self.binary)
            modified[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                probe_queue_reply(bytes(modified))
        for kwargs in ({'memory_records': 33}, {'persisted_records': -1},
                       {'memory_records': True}, {'response': (1,)}, {'response': (-1, 0)}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                probe_queue_reply(self.binary, **kwargs)

    def test_activation_flushes_once_and_neutral_updates_do_not_repeat_it(self):
        result = probe_events_cadence(self.binary, updates=100, view_values=[])
        self.assertEqual(result['flushes_after_activation'], 1)
        self.assertEqual(result['flushes_after_updates'], 1)
        self.assertEqual(result['flushes_after_second_activation'], 2)

    def test_view_debounce_fires_once_until_the_input_changes(self):
        stable = probe_events_cadence(self.binary, updates=0, view_values=[5] * 100)
        self.assertEqual(stable['debounce_action_update_indices'], [10])
        self.assertEqual(stable['debounce_final_counter'], -1)
        changed = probe_events_cadence(self.binary, updates=0, view_values=[5] * 25 + [7] * 25)
        self.assertEqual(changed['debounce_action_update_indices'], [10, 35])
        self.assertEqual(changed['debounce_final_counter'], -1)

    def test_cadence_window_guards_and_input_bounds_are_enforced(self):
        for offset in (EVENTS_UPDATE, ACTIVATION_TAIL, 0x29E490):
            modified = bytearray(self.binary)
            modified[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                probe_events_cadence(bytes(modified))
        for kwargs in ({'updates': True}, {'updates': 501}, {'view_values': [-1]},
                       {'view_values': [True]}, {'view_values': [0] * 1001}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                probe_events_cadence(self.binary, **kwargs)


if __name__ == '__main__':
    unittest.main()
