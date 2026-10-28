import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import restore_speedrush_cache as restoration


class CacheRestorationTests(unittest.TestCase):
    media = b'synthetic original-content candidate'

    def fixture(self, directory, *, include_movie=False):
        source, video = Path(directory) / 'cache.zip', Path(directory) / 'video.mp4'
        entry = zipfile.ZipInfo('Caches/retained.bin', (2020, 2, 3, 4, 5, 6))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = 0o100644 << 16
        with zipfile.ZipFile(source, 'w') as archive:
            archive.comment = b'original synthetic metadata'
            archive.writestr(entry, b'existing bytes' * 10)
            archive.writestr('Caches/kept-directory/', b'')
            if include_movie:
                archive.writestr(restoration.CACHE_MEMBER, self.media)
        video.write_bytes(self.media)
        return source, video

    def guards(self, source):
        return (patch.object(restoration, 'SOURCE_CACHE_SHA256', restoration.sha256(source)),
                patch.object(restoration, 'EXPECTED_BYTES', len(self.media)),
                patch.object(restoration, 'EXPECTED_MD5', hashlib.md5(self.media).hexdigest()))

    def test_adds_one_member_preserving_inputs_and_original_compressed_record_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            source, video = self.fixture(directory)
            before = source.read_bytes()
            output = Path(directory) / 'candidate.zip'
            first, second, third = self.guards(source)
            with first, second, third:
                result = restoration.restore(source, video, output)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(video.read_bytes(), self.media)
            with zipfile.ZipFile(source) as old, zipfile.ZipFile(output) as new:
                self.assertEqual(new.namelist(), old.namelist() + [restoration.CACHE_MEMBER])
                self.assertEqual(new.comment, old.comment)
                self.assertEqual(new.read(restoration.CACHE_MEMBER), self.media)
                self.assertEqual(output.read_bytes()[:old.start_dir], before[:old.start_dir])
                for item in old.infolist():
                    self.assertEqual(new.read(item.filename), old.read(item))
            self.assertFalse(result['manifest_or_ledger_changed'])
            self.assertFalse(result['device_import_or_playback_tested'])

    def test_existing_output_and_in_place_output_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            source, video = self.fixture(directory)
            output = Path(directory) / 'existing.zip'
            output.write_bytes(b'keep existing file')
            before = source.read_bytes()
            for target in (source, video, output):
                with self.subTest(target=target.name), self.assertRaises(FileExistsError):
                    restoration.restore(source, video, target)
            self.assertEqual(output.read_bytes(), b'keep existing file')
            self.assertEqual(source.read_bytes(), before)

    def test_wrong_cache_wrong_movie_and_already_present_member_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            source, video = self.fixture(directory)
            output = Path(directory) / 'candidate.zip'
            with patch.object(restoration, 'EXPECTED_BYTES', len(self.media)), \
                    patch.object(restoration, 'EXPECTED_MD5', hashlib.md5(self.media).hexdigest()):
                with self.assertRaisesRegex(ValueError, 'Source cache'):
                    restoration.restore(source, video, output)
            video.write_bytes(b'X' + self.media[1:])
            first, second, third = self.guards(source)
            with first, second, third, self.assertRaisesRegex(ValueError, 'Movie digest'):
                restoration.restore(source, video, output)
            self.assertFalse(output.exists())
        with tempfile.TemporaryDirectory() as directory:
            source, video = self.fixture(directory, include_movie=True)
            first, second, third = self.guards(source)
            with first, second, third, self.assertRaisesRegex(ValueError, 'already contains'):
                restoration.restore(source, video, Path(directory) / 'candidate.zip')

    def test_failed_candidate_is_removed_without_changing_original(self):
        with tempfile.TemporaryDirectory() as directory:
            source, video = self.fixture(directory)
            before = source.read_bytes()
            output = Path(directory) / 'candidate.zip'
            first, second, third = self.guards(source)
            with first, second, third, patch.object(zipfile.ZipFile, 'writestr', side_effect=OSError('simulated disk error')):
                with self.assertRaisesRegex(OSError, 'disk error'):
                    restoration.restore(source, video, output)
            self.assertFalse(output.exists())
            self.assertEqual(source.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
