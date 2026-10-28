import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

from scripts.recover_optional_assets import (GUI_PREFIX, PREFIX, inventory_candidates,
    missing_hd_records, recover_optional, safe_logical_path)
from scripts.recover_speedrush_video import BoundedRangeReader


class Response(io.BytesIO):
    status = 206

    def __init__(self, data, content_range):
        super().__init__(data)
        self.headers = {'Content-Range': content_range}


def reader_for(data, budget=65536):
    def opener(request, timeout):
        first, last = map(int, re.fullmatch(r'bytes=(\d+)-(\d+)', request.get_header('Range')).groups())
        return Response(data[first:last + 1], f'bytes {first}-{last}/{len(data)}')
    return BoundedRangeReader('https://example.invalid/preservation.zip', len(data),
                              opener=opener, max_total_bytes=budget)


class OptionalRecoveryTests(unittest.TestCase):
    def fixtures(self, directory, specifications):
        """Synthetic bytes and manifests only; no original game assets."""
        root = Path(directory)
        ipa, cache = root / 'fixture.ipa', root / 'cache.zip'
        lines, archive_data = [], io.BytesIO()
        with zipfile.ZipFile(archive_data, 'w') as remote:
            for path, expected, actual, transported in specifications:
                lines.append('/' + path + '\t' + hashlib.md5(expected).hexdigest()
                             + f'\t{len(expected) if transported is None else transported}\t{len(expected)}\n')
                if actual is not None:
                    remote.writestr(PREFIX + path, actual)
        with zipfile.ZipFile(ipa, 'w') as output:
            output.writestr('Payload/RealRacing3.app/res/asset_list_test.txt', ''.join(lines))
        with zipfile.ZipFile(cache, 'w'):
            pass
        return ipa, cache, archive_data.getvalue(), root / 'recovered'

    def test_exact_name_size_and_md5_are_required_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            good, wrong = GUI_PREFIX + 'event/good.rgb.pvr.z', GUI_PREFIX + 'event/wrong.rgb.pvr.z'
            ipa, cache, data, output = self.fixtures(directory, [
                (good, b'original fixture', b'original fixture', None),
                (wrong, b'expected fixture', b'different data!!', None),
            ])
            report = recover_optional(ipa, cache, output, reader=reader_for(data), max_total_bytes=65536, recover=True)
            self.assertEqual(len(report['recovered']), 1)
            self.assertEqual(report['recovered'][0]['logical_path'], good)
            self.assertEqual((output / good).read_bytes(), b'original fixture')
            self.assertFalse((output / wrong).exists())
            self.assertEqual(report['rejected'][0]['reason'], 'ios_manifest_hash_or_size_mismatch')
            provenance = json.loads((output / (good + '.provenance.json')).read_text())
            self.assertTrue(provenance['zip_crc_verified'])
            self.assertTrue(provenance['exact_ios_manifest_representation'])
            self.assertLessEqual(report['range_bytes_read'], 65536)

    def test_transport_representation_and_platform_atlases_are_not_guessed(self):
        with tempfile.TemporaryDirectory() as directory:
            ipa, cache, data, output = self.fixtures(directory, [
                (GUI_PREFIX + 'event/page.rgb.pvr.z', b'expanded', b'expanded', 3),
                (GUI_PREFIX + 'event/sprites.ios.atlas', b'ios', None, None),
            ])
            report = recover_optional(ipa, cache, output, reader=reader_for(data), max_total_bytes=65536, recover=True)
            self.assertEqual(report['candidate_count'], 0)
            self.assertEqual(report['excluded_reasons']['transport_and_stored_sizes_differ'], 1)
            self.assertEqual(report['excluded_reasons']['outside_exact_rgb_texture_scope'], 1)
            self.assertFalse(output.exists())

    def test_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = GUI_PREFIX + 'event/page.rgb.pvr.z'
            ipa, cache, data, output = self.fixtures(directory, [(path, b'bytes', b'bytes', None)])
            existing = output / path
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b'keep existing')
            report = recover_optional(ipa, cache, output, reader=reader_for(data), max_total_bytes=65536, recover=True)
            self.assertEqual(existing.read_bytes(), b'keep existing')
            self.assertEqual(report['rejected'][0]['reason'], 'destination_exists')

    def test_inventory_only_never_writes_and_size_mismatches_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            ipa, cache, data, output = self.fixtures(directory, [
                (GUI_PREFIX + 'event/good.rgb.pvr.z', b'bytes', b'bytes', None),
                (GUI_PREFIX + 'event/size.rgb.pvr.z', b'longer', b'tiny', None),
            ])
            report = recover_optional(ipa, cache, output, reader=reader_for(data), max_total_bytes=65536)
            self.assertEqual(report['candidate_count'], 1)
            self.assertEqual(report['excluded_reasons']['stored_size_mismatch'], 1)
            self.assertFalse(output.exists())
            self.assertEqual(report['recovered'], [])

    def test_unsafe_paths_and_conflicting_manifest_records_are_excluded(self):
        self.assertFalse(safe_logical_path(GUI_PREFIX + '../escape.rgb.pvr.z'))
        self.assertFalse(safe_logical_path(GUI_PREFIX + 'event/./page.rgb.pvr.z'))
        with tempfile.TemporaryDirectory() as directory:
            path = GUI_PREFIX + 'event/page.rgb.pvr.z'
            ipa, cache, data, _ = self.fixtures(directory, [(path, b'bytes', b'bytes', None)])
            records = missing_hd_records(ipa, cache)
            records[path]['representations'].append(dict(md5='f' * 32, transport_bytes=5, stored_bytes=5))
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                candidates, excluded = inventory_candidates(records, archive)
            self.assertEqual(candidates, [])
            self.assertEqual(excluded[0]['reason'], 'conflicting_ios_manifest_representations')

    def test_verified_local_bytes_are_deduplicated_without_another_member_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = GUI_PREFIX + 'event/page.rgb.pvr.z'
            ipa, cache, data, output = self.fixtures(directory, [(path, b'bytes', b'bytes', None)])
            first = recover_optional(ipa, cache, output, reader=reader_for(data), max_total_bytes=65536, recover=True)
            second = recover_optional(ipa, cache, output, reader=reader_for(data), max_total_bytes=65536, recover=True)
            self.assertEqual(len(first['recovered']), 1)
            self.assertEqual(second['recovered'], [])
            self.assertEqual(second['already_verified_local'][0]['path'], path)
            self.assertEqual(second['range_bytes_read'], second['inventory_range_bytes'])

    def test_member_is_deferred_when_the_remaining_total_budget_is_too_small(self):
        with tempfile.TemporaryDirectory() as directory:
            path = GUI_PREFIX + 'event/page.rgb.pvr.z'
            ipa, cache, data, output = self.fixtures(directory, [(path, b'x' * 10000, b'x' * 10000, None)])
            report = recover_optional(ipa, cache, output, reader=reader_for(data, budget=1024), max_total_bytes=1024, recover=True)
            self.assertEqual(report['recovered'], [])
            self.assertEqual(report['deferred'][0]['reason'], 'remaining_range_budget')
            self.assertLessEqual(report['range_bytes_read'], 1024)
            self.assertFalse(output.exists())

    def test_invalid_zip_crc_prevents_any_asset_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = GUI_PREFIX + 'event/page.rgb.pvr.z'
            ipa, cache, data, output = self.fixtures(directory, [(path, b'original', b'original', None)])
            damaged = bytearray(data)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                info = archive.getinfo(PREFIX + path)
                name_size, extra_size = len(info.filename.encode()), len(info.extra)
                damaged[info.header_offset + 30 + name_size + extra_size] ^= 1
            report = recover_optional(ipa, cache, output, reader=reader_for(damaged), max_total_bytes=65536, recover=True)
            self.assertEqual(report['recovered'], [])
            self.assertEqual(report['rejected'][0]['reason'], 'retrieval_or_zip_integrity_error')
            self.assertIn('CRC', report['rejected'][0]['detail'])
            self.assertFalse(output.exists())

    def test_wrong_archive_root_is_not_reported_as_zero_recoverable_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = GUI_PREFIX + 'event/page.rgb.pvr.z'
            ipa, cache, _, output = self.fixtures(directory, [(path, b'bytes', b'bytes', None)])
            alternate = io.BytesIO()
            with zipfile.ZipFile(alternate, 'w') as archive:
                archive.writestr('different-root/.depot/' + path, b'bytes')
            with self.assertRaisesRegex(ValueError, 'prefix is absent'):
                recover_optional(ipa, cache, output, reader=reader_for(alternate.getvalue()), max_total_bytes=65536)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
