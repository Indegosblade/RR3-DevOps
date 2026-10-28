"""Recover the manifest-matching original movie from a public preservation ZIP.

Reads bounded HTTPS ranges instead of downloading the multi-gigabyte archive.
Output is written only after ZIP CRC, expected length and MD5 checks succeed.
No cache, IPA, save, signature or device is modified.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ARCHIVE_URL = ('https://archive.org/download/com.ea.games.r3_row_ADRENO_14.0.1/'
               'com.ea.games.r3_row_ADRENO.zip')
ARCHIVE_BYTES = 6164903864
MEMBER = 'com.ea.games.r3_row/files/.depot/SpeedRush_TV_commercial.mp4'
EXPECTED_BYTES = 6925760
EXPECTED_MD5 = '7f9560c4abf3665fd4bd62e01aa9f689'
SOURCE_PAGE = 'https://viduxsh.github.io/Project_RR3/'


class BoundedRangeReader(io.RawIOBase):
    def __init__(self, url, size, *, opener=urllib.request.urlopen,
                 max_request_bytes=16 * 1024**2, max_total_bytes=32 * 1024**2):
        if not url.startswith('https://') or size <= 0:
            raise ValueError('Expected an HTTPS URL and a positive archive size')
        self.url, self.size, self.opener = url, size, opener
        self.max_request_bytes, self.max_total_bytes = max_request_bytes, max_total_bytes
        self.position = self.transferred = self.requests = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        if whence not in (0, 1, 2):
            raise ValueError('Invalid seek mode')
        target = (0 if whence == 0 else self.position if whence == 1 else self.size) + offset
        if not 0 <= target <= self.size:
            raise ValueError('Range seek outside archive')
        self.position = target
        return target

    def read(self, size=-1):
        if size is None or size < 0:
            size = self.size - self.position
        size = min(size, self.size - self.position)
        if not size:
            return b''
        if size > self.max_request_bytes or self.transferred + size > self.max_total_bytes:
            raise ValueError('Bounded range-read budget exceeded')
        start, end = self.position, self.position + size - 1
        request = urllib.request.Request(self.url, headers={
            'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity',
        })
        with self.opener(request, timeout=20) as response:
            expected = f'bytes {start}-{end}/{self.size}'
            if response.status != 206 or response.headers.get('Content-Range') != expected:
                raise ValueError('Server did not honor the exact bounded range')
            data = response.read(size + 1)
        if len(data) != size:
            raise ValueError('Unexpected range response length')
        self.position += size
        self.transferred += size
        self.requests += 1
        return data


def recover(destination, *, reader=None):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError('Refusing to overwrite an existing candidate')
    source = reader if reader is not None else BoundedRangeReader(ARCHIVE_URL, ARCHIVE_BYTES)
    with zipfile.ZipFile(source) as archive:
        if archive.namelist().count(MEMBER) != 1:
            raise ValueError('Expected exactly one original movie member')
        info = archive.getinfo(MEMBER)
        if info.file_size != EXPECTED_BYTES or info.compress_size > 16 * 1024**2:
            raise ValueError('Unexpected movie member size')
        data = archive.read(info)  # Reads the complete member and validates ZIP CRC.
    if len(data) != EXPECTED_BYTES or hashlib.md5(data).hexdigest() != EXPECTED_MD5:
        raise ValueError('Candidate does not match the preserved iOS manifest')
    with destination.open('xb') as output:
        output.write(data)
    return {'source_page': SOURCE_PAGE, 'archive_url': ARCHIVE_URL,
            'archive_bytes': ARCHIVE_BYTES, 'member': MEMBER,
            'bytes': len(data), 'md5': EXPECTED_MD5,
            'sha256': hashlib.sha256(data).hexdigest(),
            'zip_crc_verified': True, 'matches_ios_manifest': True,
            'range_bytes_read': getattr(source, 'transferred', None),
            'range_requests': getattr(source, 'requests', None),
            'cache_modified': False, 'device_playback_tested': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New output path outside a working app/cache')
    args = parser.parse_args()
    result = recover(args.output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
