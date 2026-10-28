"""Synthetic content identity, representation and bounded-write tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

from scripts.recover_local_assets import MAX_TOTAL, PREFIXES, recover_local, write_verified


class LocalAssetRecoveryTests(unittest.TestCase):
    def fixtures(self, directory, targets, source_members):
        root = Path(directory)
        ipa, cache = root / 'original.ipa', root / 'original-cache.zip'
        lines = ''.join('/' + path + '\t' + hashlib.md5(transport).hexdigest()
                        + f'\t{len(transport)}\t{len(stored)}\n'
                        for path, stored, transport in targets)
        with zipfile.ZipFile(ipa, 'w') as archive:
            archive.writestr(PREFIXES[0] + 'asset_list_fixture.txt', lines)
            for origin, name, data in source_members:
                if origin == 0:
                    archive.writestr(PREFIXES[0] + name, data)
        with zipfile.ZipFile(cache, 'w') as archive:
            for origin, name, data in source_members:
                if origin == 1:
                    archive.writestr(PREFIXES[1] + name, data)
        return ipa, cache, root / 'recovery', len(lines.encode())

    def test_different_name_exact_hash_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = 'gui_assets/2048x1536/event/original.rgb.pvr.z'
            ipa, cache, output, _ = self.fixtures(directory, [(path, b'original', b'original')],
                                                 [(1, 'other/event/renamed.bin', b'original')])
            result = recover_local(ipa, cache, output, recover=True)
            self.assertEqual(result['original_missing_hd_paths'], 1)
            self.assertEqual((output / path).read_bytes(), b'original')
            self.assertEqual(result['recovered'][0]['source_member'], 'Caches/other/event/renamed.bin')
            provenance = json.loads((output / (path + '.provenance.json')).read_text())
            self.assertTrue(provenance['zip_crc_verified'])
            self.assertTrue(provenance['exact_ios_manifest_representation'])

    def test_same_basename_wrong_hash_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = 'gui_assets/2048x1536/event/sprites_0.rgb.pvr.z'
            ipa, cache, output, _ = self.fixtures(directory, [(path, b'original', b'original')],
                                                 [(1, 'different/event/sprites_0.rgb.pvr.z', b'wrong!!!')])
            result = recover_local(ipa, cache, output, recover=True)
            self.assertEqual(result['recovered'], [])
            self.assertEqual(result['candidate_members_without_exact_match'], 1)
            self.assertFalse(output.exists())

    def test_atlas_transport_hash_is_checked_instead_of_stored_xml_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = 'gui_assets/2048x1536/event/sprites.ios.atlas'
            stored = b'<atlas><synthetic name="fixture"/></atlas>' * 10
            transport = b'FMASZ1' + zlib.compress(stored, 6)
            ipa, cache, output, _ = self.fixtures(directory, [(path, stored, transport)],
                                                 [(0, 'unrelated/metadata.bin', stored)])
            result = recover_local(ipa, cache, output, recover=True)
            self.assertEqual((output / path).read_bytes(), stored)
            self.assertEqual(result['recovered'][0]['transport_md5'], hashlib.md5(transport).hexdigest())
            self.assertNotEqual(result['recovered'][0]['transport_md5'], hashlib.md5(stored).hexdigest())

    def test_unknown_compressed_representation_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = 'gui_assets/2048x1536/event/file.bin'
            ipa, cache, output, _ = self.fixtures(directory, [(path, b'original', b'transport')],
                                                 [(1, 'other/file.bin', b'original')])
            result = recover_local(ipa, cache, output, recover=True)
            self.assertEqual(result['excluded_reasons'], {'unsupported_transport_representation': 1})
            self.assertFalse(output.exists())

    def test_unknown_existing_destination_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = 'gui_assets/2048x1536/event/file.bin'
            ipa, cache, output, _ = self.fixtures(directory, [(path, b'original', b'original')],
                                                 [(1, 'other/file.bin', b'original')])
            existing = output / path
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b'unknown!')
            result = recover_local(ipa, cache, output, recover=True)
            self.assertEqual(existing.read_bytes(), b'unknown!')
            self.assertEqual(result['rejected'][0]['reason'], 'unknown_existing_destination')
            self.assertIn(path, result['unresolved_target_paths'])

    def test_unknown_sidecar_without_payload_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = 'gui_assets/2048x1536/event/file.bin'
            ipa, cache, output, _ = self.fixtures(directory, [(path, b'original', b'original')],
                                                 [(1, 'other/file.bin', b'original')])
            sidecar = output / (path + '.provenance.json')
            sidecar.parent.mkdir(parents=True)
            sidecar.write_text('keep existing provenance', encoding='utf-8')
            result = recover_local(ipa, cache, output, recover=True)
            self.assertEqual(sidecar.read_text(), 'keep existing provenance')
            self.assertEqual(result['recovered'], [])
            self.assertFalse((output / path).exists())

    def test_provenance_write_failure_removes_only_owned_creations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = 'gui_assets/2048x1536/event/file.bin'
            with patch('scripts.recover_local_assets.json.dump', side_effect=OSError('disk full')):
                with self.assertRaisesRegex(OSError, 'disk full'):
                    write_verified(root, path, b'original', {'synthetic': True})
            self.assertFalse((root / path).exists())
            self.assertFalse((root / (path + '.provenance.json')).exists())

    def test_asset_close_failure_removes_owned_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = 'gui_assets/2048x1536/event/file.bin'
            original_open = Path.open

            class CloseFailure:
                def __init__(self, stream):
                    self.stream = stream

                def __enter__(self):
                    return self.stream

                def __exit__(self, *exception):
                    self.stream.close()
                    raise OSError('close failure')

            def injected_open(file, *args, **kwargs):
                stream = original_open(file, *args, **kwargs)
                return CloseFailure(stream) if str(file).endswith('file.bin') else stream

            with patch.object(Path, 'open', injected_open):
                with self.assertRaisesRegex(OSError, 'close failure'):
                    write_verified(root, path, b'original', {'synthetic': True})
            self.assertFalse((root / path).exists())

    def test_sidecar_collision_during_write_preserves_unknown_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = 'gui_assets/2048x1536/event/file.bin'
            original_open = Path.open

            def injected_open(file, *args, **kwargs):
                if str(file).endswith('.provenance.json'):
                    with original_open(file, 'x', encoding='utf-8') as stream:
                        stream.write('unknown concurrent provenance')
                    raise FileExistsError('sidecar occupied')
                return original_open(file, *args, **kwargs)

            with patch.object(Path, 'open', injected_open):
                with self.assertRaises(FileExistsError):
                    write_verified(root, path, b'original', {'synthetic': True})
            self.assertFalse((root / path).exists())
            self.assertEqual((root / (path + '.provenance.json')).read_text(), 'unknown concurrent provenance')

    def test_appledouble_and_research_report_bytes_are_not_discovery_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            path = 'gui_assets/2048x1536/event/file.bin'
            ipa, cache, output, _ = self.fixtures(directory, [(path, b'original', b'original')],
                                                 [(1, 'other/._file.bin', b'original'),
                                                  (1, 'investigation/file.bin', b'original'),
                                                  (1, 'reports/file.bin', b'original')])
            result = recover_local(ipa, cache, output, recover=True)
            self.assertEqual(result['size_candidate_members'], 0)
            self.assertEqual(result['recovered'], [])

    def test_duplicate_authoritative_manifest_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = 'gui_assets/2048x1536/event/file.bin'
            ipa, cache, output, _ = self.fixtures(directory, [(path, b'original', b'original')], [])
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with zipfile.ZipFile(ipa, 'a') as archive:
                    archive.writestr(PREFIXES[0] + 'asset_list_fixture.txt', 'different')
            with self.assertRaisesRegex(ValueError, 'Duplicate authoritative'):
                recover_local(ipa, cache, output, recover=True)

    def test_payload_budget_defers_before_reading_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = 'gui_assets/2048x1536/event/file.bin'
            ipa, cache, output, manifests = self.fixtures(directory, [(path, b'original', b'original')],
                                                         [(1, 'other/file.bin', b'original')])
            result = recover_local(ipa, cache, output, recover=True, max_total_bytes=manifests + 7)
            self.assertEqual(result['payload_bytes_read'], manifests)
            self.assertEqual(result['deferred'][0]['reason'], 'remaining_payload_budget')
            self.assertFalse(output.exists())
            with self.assertRaises(ValueError):
                recover_local(ipa, cache, output, max_total_bytes=MAX_TOTAL + 1)

    def test_authentic_previous_recovery_is_deduplicated_without_changing_original_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = 'gui_assets/2048x1536/event/file.bin'
            ipa, cache, output, _ = self.fixtures(directory, [(path, b'original', b'original')],
                                                 [(1, 'other/file.bin', b'original')])
            recover_local(ipa, cache, output, recover=True)
            result = recover_local(ipa, cache, output, recover=True)
            self.assertEqual(result['original_missing_hd_paths'], 1)
            self.assertEqual(len(result['already_verified_local']), 1)
            self.assertEqual(result['recovered'], [])
            self.assertEqual(result['scanned_candidate_members'], 0)

    def test_bad_crc_never_writes_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = 'gui_assets/2048x1536/event/file.bin'
            ipa, cache, output, _ = self.fixtures(directory, [(path, b'original', b'original')],
                                                 [(1, 'other/file.bin', b'original')])
            data = bytearray(cache.read_bytes())
            with zipfile.ZipFile(cache) as archive:
                info = archive.infolist()[0]
                offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
            data[offset] ^= 1
            cache.write_bytes(data)
            result = recover_local(ipa, cache, output, recover=True)
            self.assertEqual(result['recovered'], [])
            self.assertEqual(result['rejected'][0]['reason'], 'zip_integrity_or_read_failure')
            self.assertFalse(output.exists())

    def test_inventory_mode_finds_exact_match_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = 'gui_assets/2048x1536/event/file.bin'
            ipa, cache, output, _ = self.fixtures(directory, [(path, b'original', b'original')],
                                                 [(1, 'other/file.bin', b'original')])
            result = recover_local(ipa, cache, output)
            self.assertEqual(len(result['exact_matches']), 1)
            self.assertEqual(result['recovered'], [])
            self.assertFalse(output.exists())

    def test_cleanup_failure_does_not_replace_the_original_write_error(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory).resolve()
            original = OSError('original write failure')
            opener = Path.open

            class BrokenWriter:
                def __init__(self, stream):
                    self.stream = stream
                def __enter__(self):
                    return self
                def write(self, data):
                    self.stream.write(data[:1])
                    raise original
                def __exit__(self, *args):
                    self.stream.close()

            def broken_open(path, mode='r', *args, **kwargs):
                stream = opener(path, mode, *args, **kwargs)
                return BrokenWriter(stream) if mode == 'xb' else stream

            with patch.object(Path, 'open', broken_open), \
                    patch.object(Path, 'unlink', side_effect=OSError('cleanup failure')):
                with self.assertRaises(OSError) as caught:
                    write_verified(destination, 'gui_assets/2048x1536/test/data.bin', b'fixture', {})
            self.assertIs(caught.exception, original)


if __name__ == '__main__':
    unittest.main()
