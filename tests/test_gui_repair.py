import hashlib
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

from build_4k_v3 import eds_crypt
from scripts import repair_gui_layout as repair


class GuiRepairTests(unittest.TestCase):
    # Synthetic XML only; no game file is included in the test fixture.
    plaintext = b'<Styles><Colours>\r\n' + repair.BROKEN_ELEMENT + b'</Colours></Styles>'

    def test_two_byte_syntax_repair_and_roundtrip(self):
        encrypted = eds_crypt(self.plaintext)
        with patch.object(repair, 'SUPPORTED_RESOURCE_SHA256', hashlib.sha256(encrypted).hexdigest()):
            output = repair.repair_resource(encrypted)
        repaired = eds_crypt(output)
        self.assertEqual(repaired, self.plaintext.replace(repair.BROKEN_ELEMENT, repair.REPAIRED_ELEMENT))
        self.assertEqual(len(repaired) - len(self.plaintext), 2)
        colour = ET.fromstring(repaired).find('Colours/Colour')
        self.assertEqual(colour.attrib, {'name': 'lts_popup_backing_color', 'r': '221', 'g': '221', 'b': '221'})

    def test_changed_and_already_repaired_inputs_are_refused(self):
        encrypted = eds_crypt(self.plaintext)
        with patch.object(repair, 'SUPPORTED_RESOURCE_SHA256', hashlib.sha256(encrypted).hexdigest()):
            for altered in (encrypted + b'x', eds_crypt(self.plaintext.replace(repair.BROKEN_ELEMENT, repair.REPAIRED_ELEMENT))):
                with self.subTest(size=len(altered)), self.assertRaisesRegex(ValueError, 'Unsupported'):
                    repair.repair_resource(altered)

    def test_ipa_only_changes_guarded_resource_and_preserves_zip_metadata(self):
        encrypted = eds_crypt(self.plaintext)
        with tempfile.TemporaryDirectory() as directory:
            source, destination = Path(directory) / 'source.ipa', Path(directory) / 'candidate.ipa'
            resource = zipfile.ZipInfo(repair.RESOURCE_PATH, (2020, 2, 3, 4, 5, 6))
            resource.compress_type = zipfile.ZIP_DEFLATED
            resource.external_attr = 0o100644 << 16
            with zipfile.ZipFile(source, 'w') as archive:
                archive.comment = b'synthetic metadata'
                archive.writestr(resource, encrypted)
                archive.writestr('Payload/RealRacing3.app/unchanged.bin', b'unchanged fixture')
                archive.writestr('Payload/RealRacing3.app/kept-directory/', b'')
            with patch.object(repair, 'SUPPORTED_RESOURCE_SHA256', hashlib.sha256(encrypted).hexdigest()):
                result = repair.repair_ipa(source, destination)
            with zipfile.ZipFile(source) as before, zipfile.ZipFile(destination) as after:
                self.assertEqual(before.namelist(), after.namelist())
                self.assertEqual(before.comment, after.comment)
                for first, second in zip(before.infolist(), after.infolist()):
                    self.assertEqual((first.date_time, first.external_attr, first.compress_type),
                                     (second.date_time, second.external_attr, second.compress_type))
                    if first.filename != repair.RESOURCE_PATH:
                        self.assertEqual(before.read(first), after.read(second))
                ET.fromstring(eds_crypt(after.read(repair.RESOURCE_PATH)))
            self.assertTrue(result['xml_syntax_verified'])
            self.assertFalse(result['runtime_visual_effect_verified'])
            with self.assertRaises(FileExistsError):
                repair.repair_ipa(source, destination)
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                repair.repair_ipa(source, source)

    def test_guard_failure_does_not_create_an_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source, destination = Path(directory) / 'source.ipa', Path(directory) / 'candidate.ipa'
            with zipfile.ZipFile(source, 'w') as archive:
                archive.writestr(repair.RESOURCE_PATH, b'unsupported fixture')
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                repair.repair_ipa(source, destination)
            self.assertFalse(destination.exists())

    def test_cli_requires_explicit_experimental_opt_in(self):
        with patch('sys.argv', ['repair_gui_layout.py', 'source.ipa', 'candidate.ipa']), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                repair.main()
        self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
