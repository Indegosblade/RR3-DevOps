import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

from scripts.trace_asset_transport import (MAGIC, PREFIX, TARGETS, atlas_transport,
    decode_transport, recover_atlases, validate_existing, verify_stored)
from test_optional_recovery import reader_for


class AssetTransportTests(unittest.TestCase):
    def expectation(self, stored):
        transport = atlas_transport(stored)
        return dict(md5=hashlib.md5(transport).hexdigest(),
                    transport_bytes=len(transport), stored_bytes=len(stored))

    def fixture(self, directory, *, wrong_source=False, conflict=False):
        root = Path(directory)
        ipa, cache, output = root / 'original.ipa', root / 'cache.zip', root / 'recovered'
        buffer = io.BytesIO()
        lines = []
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as remote:
            for index, path in enumerate(TARGETS):
                stored = (f'<synthetic-atlas index="{index}">fixture</synthetic-atlas>\n').encode()
                expected = self.expectation(stored)
                lines.append(f"/{path} {expected['md5']} {expected['transport_bytes']} {len(stored)}\n")
                source = stored.replace(b'fixture', b'changed') if wrong_source and index == 0 else stored
                remote.writestr(PREFIX + path.replace('.ios.atlas', '.android.atlas'), source)
        with zipfile.ZipFile(ipa, 'w') as archive:
            archive.writestr('Payload/RealRacing3.app/res/asset_list_fixture.txt', ''.join(lines))
            if conflict:
                archive.writestr('Payload/RealRacing3.app/res/asset_list_conflict.txt',
                                 lines[0].replace(lines[0].split()[1], '0' * 32))
        with zipfile.ZipFile(cache, 'w'):
            pass
        return ipa, cache, output, buffer.getvalue()

    def test_transport_header_and_representation_hash(self):
        stored = b'<synthetic>atlas fixture</synthetic>\n' * 12
        transport = atlas_transport(stored)
        self.assertEqual(transport, b'FMASZ1' + zlib.compress(stored, 6))
        self.assertEqual(decode_transport(transport), stored)
        self.assertNotEqual(hashlib.md5(stored).hexdigest(), hashlib.md5(transport).hexdigest())
        self.assertTrue(verify_stored(stored, self.expectation(stored))['exact_ios_manifest_representation'])

    def test_wrong_hash_size_or_transport_size_is_rejected(self):
        stored = b'synthetic fixture' * 20
        for key, value in [('md5', '0' * 32), ('stored_bytes', len(stored) + 1),
                           ('transport_bytes', 1)]:
            expected = self.expectation(stored)
            expected[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_stored(stored, expected)

    def test_corrupt_truncated_trailing_and_overexpanding_payloads_are_rejected(self):
        transport = atlas_transport(b'synthetic fixture' * 100)
        for value in [transport[:-1], transport + b'extra', MAGIC + b'corrupt',
                      transport + transport, b'BADHDR' + transport[len(MAGIC):]]:
            with self.subTest(payload=value[:8]), self.assertRaises(ValueError):
                decode_transport(value)
        with self.assertRaises(ValueError):
            decode_transport(transport, max_output=10)

    @patch('scripts.trace_asset_transport.validate_existing',
           return_value={'codec_validation_complete': True})
    def test_exact_transport_guard_allows_stored_bytes_with_source_provenance(self, _validation):
        with tempfile.TemporaryDirectory() as directory:
            ipa, cache, output, remote = self.fixture(directory)
            report = recover_atlases(ipa, cache, output, reader=reader_for(remote))
            self.assertEqual(len(report['recovered']), 3)
            for entry in report['recovered']:
                stored = (output / entry['logical_path']).read_bytes()
                self.assertEqual(hashlib.md5(atlas_transport(stored)).hexdigest(), entry['transport_md5'])
                provenance = json.loads((output / (entry['logical_path'] + '.provenance.json')).read_text())
                self.assertIn('.android.atlas', provenance['source_member'])
                self.assertFalse(provenance['stored_bytes_edited'])
                self.assertTrue(provenance['zip_crc_verified'])
            # A verified rerun is idempotent; a changed local file cannot be overwritten.
            second = recover_atlases(ipa, cache, output, reader=reader_for(remote))
            self.assertTrue(all(entry['already_verified_local'] for entry in second['recovered']))
            (output / TARGETS[0]).write_bytes(b'keep existing')
            with self.assertRaises(FileExistsError):
                recover_atlases(ipa, cache, output, reader=reader_for(remote))
            self.assertEqual((output / TARGETS[0]).read_bytes(), b'keep existing')

    @patch('scripts.trace_asset_transport.validate_existing',
           return_value={'codec_validation_complete': True})
    def test_same_size_lookalike_or_manifest_conflict_is_rejected_before_write(self, _validation):
        for options in [dict(wrong_source=True), dict(conflict=True)]:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as directory:
                ipa, cache, output, remote = self.fixture(directory, **options)
                with self.assertRaises(ValueError):
                    recover_atlases(ipa, cache, output, reader=reader_for(remote))
                self.assertFalse(output.exists())

    @patch('scripts.trace_asset_transport.validate_existing',
           return_value={'codec_validation_complete': False})
    def test_recovery_requires_known_ios_representation_validation(self, _validation):
        with self.assertRaises(ValueError):
            recover_atlases('unused', 'unused', 'unused')

    @patch('scripts.trace_asset_transport.validate_existing',
           return_value={'codec_validation_complete': True})
    def test_zip_crc_and_bounded_metadata_reads_are_required(self, _validation):
        with tempfile.TemporaryDirectory() as directory:
            ipa, cache, output, remote = self.fixture(directory)
            corrupt = bytearray(remote)
            central = corrupt.index(b'PK\x01\x02')
            corrupt[central + 16] ^= 1  # Central-directory CRC, without changing member bytes.
            with self.assertRaises(zipfile.BadZipFile):
                recover_atlases(ipa, cache, output, reader=reader_for(bytes(corrupt)))
            self.assertFalse(output.exists())
            with self.assertRaises(ValueError):
                recover_atlases(ipa, cache, output, reader=reader_for(remote, budget=1))
            self.assertFalse(output.exists())

    @patch('scripts.trace_asset_transport.trace_binary', return_value={})
    def test_local_validation_checks_ipa_and_cache_and_preserves_failure(self, _trace):
        with tempfile.TemporaryDirectory() as directory:
            ipa, cache, _, _ = self.fixture(directory)
            stored = b'synthetic existing atlas' * 10
            expected = self.expectation(stored)
            path = 'gui_assets/2048x1536/fixture/sprites.ios.atlas'
            line = f"/{path} {expected['md5']} {expected['transport_bytes']} {len(stored)}\n"
            with zipfile.ZipFile(ipa, 'a') as archive:
                archive.writestr('Payload/RealRacing3.app/res/asset_list_existing.txt', line)
                archive.writestr('Payload/RealRacing3.app/RealRacing3', b'synthetic executable')
                archive.writestr('Payload/RealRacing3.app/res/' + path, stored)
            with zipfile.ZipFile(cache, 'a') as archive:
                archive.writestr('Caches/' + path, stored)
            report = validate_existing(ipa, cache)
            self.assertTrue(report['codec_validation_complete'])
            self.assertEqual(report['local_atlas_validation']['existing_compressed_paths'], 1)
            self.assertEqual(report['local_atlas_validation']['exact_transport_matches'], 2)
            self.assertEqual(report['failures'], [])
            with zipfile.ZipFile(cache, 'w') as archive:
                archive.writestr('Caches/' + path, stored.replace(b'existing', b'diverged'))
            rejected = validate_existing(ipa, cache)
            self.assertFalse(rejected['codec_validation_complete'])
            self.assertEqual(len(rejected['failures']), 1)


if __name__ == '__main__':
    unittest.main()
