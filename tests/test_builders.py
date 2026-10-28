import contextlib
import io
from pathlib import Path
import plistlib
import struct
import tempfile
import unittest
import zipfile

import build_4k_v3 as builder
from fixtures import binary_fixture
from scripts.validate_url_literals import inspect_literals
import se_compat


class BuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = binary_fixture()

    def test_old_rewrite_is_a_failing_regression_control(self):
        old = bytearray(self.original)
        for offset, expected, replacement, description in builder.PATCHES:
            if not description.startswith('CFString:'):
                old[offset:offset + len(replacement)] = replacement
        records = inspect_literals(bytes(old))
        self.assertEqual(len(records), 5)
        self.assertTrue(all(not record['valid'] and record['contains_nul'] for record in records))

    def test_guard_rejects_changed_literal_metadata(self):
        modified = bytearray(self.original)
        struct.pack_into('<Q', modified, 0x2D51378, 58)
        with self.assertRaisesRegex(ValueError, 'CFString: geoservice'):
            builder.validate_binary(modified)

    def test_builds_valid_literals_and_opt_in_se_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.ipa'
            with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(builder.BINARY_PATH, self.original)
                archive.writestr(builder.EDS_FALLBACK, b'placeholder')
                archive.writestr('Payload/RealRacing3.app/kept/', b'')
            for compatible in (False, True):
                output = Path(directory) / f'output-{compatible}.ipa'
                with contextlib.redirect_stdout(io.StringIO()):
                    builder.build(str(source), str(output), str(Path(__file__).resolve().parents[1] / 'eds_god.plist'), se_compat=compatible)
                with zipfile.ZipFile(output) as archive:
                    binary = archive.read(builder.BINARY_PATH)
                    records = inspect_literals(binary)
                    self.assertEqual(len(records), 5)
                    self.assertTrue(all(record['valid'] for record in records))
                    self.assertIn('Payload/RealRacing3.app/kept/', archive.namelist())
                    direct = builder.EDS_DIR + 'iPhone12,8.plist'
                    self.assertEqual(direct in archive.namelist(), compatible)
                    profile = plistlib.loads(builder.eds_crypt(archive.read(builder.EDS_FALLBACK)))
                    self.assertEqual(profile['PLIST_IDENTIFIER'], 'iPad6,8')
                    self.assertEqual(profile['GUI_ATLAS_OVERRIDE'], '2048x1536' if compatible else '')
                    if compatible:
                        self.assertEqual(binary[se_compat.CAVE:se_compat.CAVE + len(se_compat.stub())], se_compat.stub())
                    else:
                        self.assertEqual(binary[se_compat.SITE:se_compat.SITE + 20], se_compat.original_instructions())


if __name__ == '__main__':
    unittest.main()
