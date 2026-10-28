import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import recover_speedrush_video as recovery


class Response(io.BytesIO):
    def __init__(self, data, status, content_range):
        super().__init__(data)
        self.status = status
        self.headers = {'Content-Range': content_range}


def server(data, *, status=206, wrong_range=False, truncate=False):
    calls = []

    def open_range(request, timeout):
        span = request.get_header('Range').removeprefix('bytes=')
        start, end = map(int, span.split('-'))
        calls.append((start, end))
        payload = data[start:end + 1]
        if truncate:
            payload = payload[:-1]
        extent = f'bytes {start}-{end}/{len(data)}' if not wrong_range else 'bytes 0-0/1'
        return Response(payload, status, extent)
    return open_range, calls


class RangeTests(unittest.TestCase):
    def test_reads_only_requested_bytes_and_obeys_seek(self):
        opener, calls = server(b'0123456789')
        reader = recovery.BoundedRangeReader('https://example.test/a.zip', 10, opener=opener)
        reader.seek(-4, 2)
        self.assertEqual(reader.read(2), b'67')
        self.assertEqual(reader.read(), b'89')
        self.assertEqual(reader.read(), b'')
        self.assertEqual(calls, [(6, 7), (8, 9)])
        self.assertEqual((reader.transferred, reader.requests), (4, 2))
        for offset, whence in ((-1, 0), (11, 0), (0, 3)):
            with self.assertRaises(ValueError):
                reader.seek(offset, whence)

    def test_full_response_wrong_range_and_truncation_are_refused(self):
        for options in ({'status': 200}, {'wrong_range': True}, {'truncate': True}):
            with self.subTest(options=options):
                opener, _ = server(b'0123456789', **options)
                reader = recovery.BoundedRangeReader('https://example.test/a.zip', 10, opener=opener)
                with self.assertRaises(ValueError):
                    reader.read(4)
                self.assertEqual(reader.transferred, 0)

    def test_request_and_total_budgets_are_enforced_before_network_read(self):
        opener, calls = server(b'0123456789')
        reader = recovery.BoundedRangeReader('https://example.test/a.zip', 10, opener=opener,
                                             max_request_bytes=3, max_total_bytes=4)
        with self.assertRaisesRegex(ValueError, 'budget'):
            reader.read(4)
        self.assertEqual(calls, [])
        self.assertEqual(reader.read(3), b'012')
        with self.assertRaisesRegex(ValueError, 'budget'):
            reader.read(2)
        self.assertEqual(calls, [(0, 2)])


class RecoveryTests(unittest.TestCase):
    media = b'synthetic media fixture; not a game asset'

    def archive(self, payload):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_STORED) as archive:
            archive.writestr(recovery.MEMBER, payload)
            archive.writestr('unrelated.bin', b'unrelated fixture')
        return stream.getvalue()

    def test_recovery_validates_zip_size_and_manifest_digest_before_output(self):
        data = self.archive(self.media)
        opener, calls = server(data)
        reader = recovery.BoundedRangeReader('https://example.test/a.zip', len(data), opener=opener)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'video.mp4'
            with patch.object(recovery, 'EXPECTED_BYTES', len(self.media)), \
                    patch.object(recovery, 'EXPECTED_MD5', hashlib.md5(self.media).hexdigest()):
                report = recovery.recover(output, reader=reader)
            self.assertEqual(output.read_bytes(), self.media)
            self.assertTrue(report['matches_ios_manifest'])
            with self.assertRaises(FileExistsError):
                recovery.recover(output, reader=io.BytesIO(data))
            self.assertEqual(output.read_bytes(), self.media)
        self.assertGreater(len(calls), 0)

    def test_size_or_digest_mismatch_never_creates_a_candidate(self):
        for payload in (self.media + b'x', b'X' + self.media[1:]):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'video.mp4'
                with patch.object(recovery, 'EXPECTED_BYTES', len(self.media)), \
                        patch.object(recovery, 'EXPECTED_MD5', hashlib.md5(self.media).hexdigest()):
                    with self.assertRaises(ValueError):
                        recovery.recover(output, reader=io.BytesIO(self.archive(payload)))
                self.assertFalse(output.exists())

    def test_corrupt_zip_member_never_creates_a_candidate(self):
        data = bytearray(self.archive(self.media))
        location = data.index(self.media)
        data[location] ^= 1
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'video.mp4'
            with patch.object(recovery, 'EXPECTED_BYTES', len(self.media)), \
                    patch.object(recovery, 'EXPECTED_MD5', hashlib.md5(self.media).hexdigest()):
                with self.assertRaises(zipfile.BadZipFile):
                    recovery.recover(output, reader=io.BytesIO(data))
            self.assertFalse(output.exists())

    def test_output_write_close_or_interrupt_failure_is_removed_and_retry_succeeds(self):
        for phase, error in (('write', OSError('injected disk full')),
                             ('close', OSError('injected close failure')),
                             ('write', KeyboardInterrupt('injected interruption'))):
            with self.subTest(phase=phase, error=type(error).__name__), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'video.mp4'
                archive = self.archive(self.media)
                original_open = Path.open

                class FailingOutput:
                    def __enter__(self):
                        self.stream = original_open(output, 'xb')
                        return self

                    def write(self, data):
                        self.stream.write(data[:4] if phase == 'write' else data)
                        if phase == 'write':
                            raise error

                    def __exit__(self, *_):
                        self.stream.close()
                        if phase == 'close':
                            raise error

                with patch.object(recovery, 'EXPECTED_BYTES', len(self.media)), \
                        patch.object(recovery, 'EXPECTED_MD5', hashlib.md5(self.media).hexdigest()):
                    with patch.object(Path, 'open', return_value=FailingOutput()):
                        with self.assertRaises(type(error)) as caught:
                            recovery.recover(output, reader=io.BytesIO(archive))
                    self.assertIs(caught.exception, error)
                    self.assertFalse(output.exists())
                    recovery.recover(output, reader=io.BytesIO(archive))
                self.assertEqual(output.read_bytes(), self.media)

    def test_exclusive_create_failure_preserves_output_created_by_another_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'video.mp4'
            original_open = Path.open

            def occupied_output(path, *args, **kwargs):
                with original_open(path, 'wb') as stream:
                    stream.write(b'other writer content')
                return original_open(path, *args, **kwargs)

            with patch.object(recovery, 'EXPECTED_BYTES', len(self.media)), \
                    patch.object(recovery, 'EXPECTED_MD5', hashlib.md5(self.media).hexdigest()), \
                    patch.object(Path, 'open', occupied_output):
                with self.assertRaises(FileExistsError):
                    recovery.recover(output, reader=io.BytesIO(self.archive(self.media)))
            self.assertEqual(output.read_bytes(), b'other writer content')

    def test_cleanup_failure_does_not_replace_original_write_error(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'video.mp4'
            original_open = Path.open
            error = OSError('original disk full')

            class FailingOutput:
                def __enter__(self):
                    self.stream = original_open(output, 'xb')
                    return self

                def write(self, data):
                    self.stream.write(data[:4])
                    raise error

                def __exit__(self, *_):
                    self.stream.close()

            with patch.object(recovery, 'EXPECTED_BYTES', len(self.media)), \
                    patch.object(recovery, 'EXPECTED_MD5', hashlib.md5(self.media).hexdigest()), \
                    patch.object(Path, 'open', return_value=FailingOutput()), \
                    patch.object(Path, 'unlink', side_effect=PermissionError('cleanup denied')):
                with self.assertRaises(OSError) as caught:
                    recovery.recover(output, reader=io.BytesIO(self.archive(self.media)))
            self.assertIs(caught.exception, error)


if __name__ == '__main__':
    unittest.main()
