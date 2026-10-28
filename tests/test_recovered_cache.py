import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import build_recovered_cache as builder
from scripts import restore_speedrush_cache as restoration
from scripts.trace_asset_transport import atlas_transport
from scripts.trace_cache_registration import parse_ledger


class RecoveredCacheTests(unittest.TestCase):
    media = b'synthetic movie bytes, not an original asset'
    xml = b'<atlas_images texture_formats=".rgb.pvr"><image name="test.png" width="1" height="1"><pos id="0" x="0" y="0"/></image></atlas_images>'

    def fixture(self, directory):
        root = Path(directory)
        ipa, cache, movie, assets = root / 'input.ipa', root / 'cache.zip', root / 'movie.mp4', root / 'assets'
        movie.write_bytes(self.media)
        lines = []
        for name in sorted(builder.TARGETS):
            data = self.xml if name.endswith('.ios.atlas') else b'synthetic texture page ' + name.encode()
            transport = atlas_transport(data) if name.endswith('.ios.atlas') else data
            target = assets.joinpath(*name.split('/'))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            lines.append('/' + name + '\t' + hashlib.md5(transport).hexdigest()
                         + f'\t{len(transport)}\t{len(data)}\n')
        manifest = ''.join(lines).encode()
        with zipfile.ZipFile(ipa, 'w') as output:
            output.writestr(builder.MANIFEST_PATH, manifest)
        ledger = (struct.pack('<II', 0xA4F6F39D, 4) + b'7469\n/retained.bin\t' + b'a' * 32
                  + b'\n/SpeedRush_TV_commercial.mp4\t' + hashlib.md5(self.media).hexdigest().encode() + b'\n')
        with zipfile.ZipFile(cache, 'w') as output:
            output.comment = b'retain archive comment'
            output.writestr('Caches/retained.bin', b'original synthetic data')
            output.writestr(restoration.RECEIPT_LEDGER, ledger)
            output.writestr('Caches/kept-directory/', b'')
        return ipa, cache, movie, assets, manifest, ledger

    def run_guarded(self, inputs, output):
        ipa, cache, movie, assets, manifest, _ = inputs
        with patch.object(builder, 'MANIFEST_SHA256', hashlib.sha256(manifest).hexdigest()), \
                patch.object(restoration, 'SOURCE_CACHE_SHA256', restoration.sha256(cache)), \
                patch.object(restoration, 'EXPECTED_BYTES', len(self.media)), \
                patch.object(restoration, 'EXPECTED_MD5', hashlib.md5(self.media).hexdigest()):
            return builder.build(ipa, cache, movie, assets, output)

    def test_seven_resources_and_six_additive_receipts_preserve_original_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs = self.fixture(directory)
            ipa, cache, movie, assets, manifest, ledger = inputs
            before = {p: p.read_bytes() for p in (ipa, cache, movie)}
            output = Path(directory) / 'candidate.zip'
            report = self.run_guarded(inputs, output)
            for path, data in before.items():
                self.assertEqual(path.read_bytes(), data)
            with zipfile.ZipFile(output) as candidate:
                self.assertEqual(len(candidate.namelist()), len(set(candidate.namelist())))
                self.assertEqual(candidate.read('Caches/retained.bin'), b'original synthetic data')
                new_ledger = candidate.read(restoration.RECEIPT_LEDGER)
                self.assertTrue(new_ledger.startswith(ledger))
                parsed = parse_ledger(new_ledger)
                self.assertEqual(parsed['client_revision_token'], '7469')
                self.assertEqual(parsed['entry_count'], 8)
                for path in builder.TARGETS:
                    self.assertEqual(candidate.read('Caches/' + path), assets.joinpath(*path.split('/')).read_bytes())
                    self.assertIn(path, parsed['records'])
                for proof in report['recovered_gui_resources']:
                    self.assertEqual(parsed['records'][proof['path']], proof['transport_md5'])
                    if proof['path'].endswith('.ios.atlas'):
                        self.assertNotEqual(parsed['records'][proof['path']], hashlib.md5(self.xml).hexdigest())
            self.assertEqual(len(report['added_resources']), 7)
            self.assertEqual(report['matching_transport_receipts_added'], 6)
            self.assertTrue(report['receipt_ledger_changed'])
            self.assertFalse(report['manifest_changed'])
            self.assertFalse(report['runtime_cache_registration_verified'])

    def test_changed_manifest_or_recovered_bytes_create_no_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs = self.fixture(directory)
            output = Path(directory) / 'candidate.zip'
            with self.assertRaisesRegex(ValueError, 'manifest differs'):
                builder.recovered_resources(inputs[0], inputs[2], inputs[3])
            target = inputs[3].joinpath(*sorted(builder.TARGETS)[0].split('/'))
            data = target.read_bytes()
            target.write_bytes(b'X' + data[1:])
            with self.assertRaisesRegex(ValueError, 'manifest'):
                self.run_guarded(inputs, output)
            self.assertFalse(output.exists())

    def test_missing_resource_or_existing_output_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs = self.fixture(directory)
            output = Path(directory) / 'candidate.zip'
            output.write_bytes(b'keep existing')
            with self.assertRaises(FileExistsError):
                self.run_guarded(inputs, output)
            self.assertEqual(output.read_bytes(), b'keep existing')
            output.unlink()
            inputs[3].joinpath(*sorted(builder.TARGETS)[0].split('/')).unlink()
            with self.assertRaises(FileNotFoundError):
                self.run_guarded(inputs, output)
            self.assertFalse(output.exists())

    def test_receipt_writer_refuses_hash_replacement_and_control_characters(self):
        with tempfile.TemporaryDirectory() as directory:
            *_, ledger = self.fixture(directory)
            for receipts, resources in (
                ({'retained.bin': 'b' * 32}, {'Caches/retained.bin': b'replacement'}),
                ({'new\npath': 'b' * 32}, {'Caches/new\npath': b'x'}),
                ({'new': 'not an MD5'}, {'Caches/new': b'x'}),
                ({'new': 'b' * 32}, {}),
            ):
                with self.subTest(receipts=receipts), self.assertRaises(ValueError):
                    restoration.append_receipts(ledger, receipts, resources)
            same, added = restoration.append_receipts(ledger, {'retained.bin': 'a' * 32}, {'Caches/retained.bin': b'x'})
            self.assertEqual(same, ledger)
            self.assertEqual(added, [])

    def test_changed_header_or_missing_final_newline_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            *_, ledger = self.fixture(directory)
            for changed in (b'X' + ledger[1:], ledger[:-1]):
                with self.subTest(changed=changed[:8]), self.assertRaises(ValueError):
                    restoration.append_receipts(changed, {'new.bin': 'b' * 32}, {'Caches/new.bin': b'x'})

    def test_ledger_rewrite_failure_removes_only_new_output(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs = self.fixture(directory)
            before = inputs[1].read_bytes()
            output = Path(directory) / 'candidate.zip'
            with patch.object(zipfile.ZipFile, 'writestr', side_effect=OSError('synthetic rewrite failure')):
                with self.assertRaisesRegex(OSError, 'rewrite failure'):
                    self.run_guarded(inputs, output)
            self.assertFalse(output.exists())
            self.assertEqual(inputs[1].read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
