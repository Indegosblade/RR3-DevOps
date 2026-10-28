"""Scanner coverage boundaries and fail-closed guards; no game bytes required."""
import struct
import unittest
from unittest.mock import patch

from scripts.trace_remote_config_consumers import direct_calls, trace_image
from scripts.trace_sdk_lifecycle import UUID


class Image:
    uuid = UUID

    def __init__(self, sections, data):
        self.sections = sections
        self.data = data

    def vm_offset(self, address, size):
        if address < 0 or address + size > len(self.data):
            raise ValueError('Out of bounds')
        return address


class RemoteConfigTests(unittest.TestCase):
    def test_aligned_branches_only_and_no_data_section_calls(self):
        data = bytearray(32)
        # BL +16 and B -4 are both direct branch forms.
        struct.pack_into('<I', data, 0, 0x94000004)
        struct.pack_into('<I', data, 4, 0x17ffffff)
        struct.pack_into('<I', data, 8, 0xd63f0200)  # BLR x16 is unresolved.
        struct.pack_into('<I', data, 16, 0x94000000)  # data must not be scanned.
        image = Image([{'name': '__text', 'address': 0, 'size': 12},
                       {'name': '__data', 'address': 16, 'size': 4}], data)
        self.assertEqual(direct_calls(image, {0, 16}), {0: 16, 4: 0})

    def test_rejects_other_build_before_reading_code(self):
        image = Image([], b'')
        image.uuid = 'different-build'
        with self.assertRaisesRegex(ValueError, 'UUID'):
            trace_image(image)

    def test_changed_instruction_window_stops_report(self):
        image = Image([], b'')
        with patch('scripts.trace_remote_config_consumers.WINDOWS',
                   {'changed': (0, 4, '0' * 64)}):
            image.data = b'\0' * 4
            with self.assertRaisesRegex(ValueError, 'Changed instruction window'):
                trace_image(image)


if __name__ == '__main__':
    unittest.main()
