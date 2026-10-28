"""Create a separate cache candidate containing the verified original movie.

The original cache and manifests are immutable inputs. Existing compressed ZIP
members are copied intact; one matching missing member is appended. This is
asset recovery, not a claim that the reported black backgrounds are fixed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.recover_speedrush_video import EXPECTED_BYTES, EXPECTED_MD5

SOURCE_CACHE_SHA256 = '96aeb92f1bb6c5ddee73e1a5fb2f4b33ef2e5a5e03fd86380b847cd771a7fc8e'
CACHE_MEMBER = 'Caches/SpeedRush_TV_commercial.mp4'


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def restore(source, video, destination):
    source, video, destination = map(Path, (source, video, destination))
    if destination.resolve() in (source.resolve(), video.resolve()) or destination.exists():
        raise FileExistsError('Output must be a new path distinct from both inputs')
    if video.stat().st_size != EXPECTED_BYTES:
        raise ValueError('Movie size does not match the preserved manifest')
    data = video.read_bytes()
    if hashlib.md5(data).hexdigest() != EXPECTED_MD5:
        raise ValueError('Movie digest does not match the preserved manifest')
    if sha256(source) != SOURCE_CACHE_SHA256:
        raise ValueError('Source cache differs from the preserved original; refusing to modify a copy')
    with zipfile.ZipFile(source) as original:
        original_names = original.namelist()
        if CACHE_MEMBER in original_names:
            raise ValueError('Cache already contains the target resource')
        if len(original_names) != len(set(original_names)):
            raise ValueError('Source cache has duplicate archive entries')
        expected = {item.filename: (item.CRC, item.file_size, item.compress_size,
                                   item.header_offset, item.compress_type, item.external_attr,
                                   item.date_time) for item in original.infolist()}
        comment = original.comment
    required_bytes = source.stat().st_size + len(data) + 1024**2
    if shutil.disk_usage(destination.parent).free < required_bytes:
        raise OSError('Insufficient free space for the separate cache candidate')
    created = False
    try:
        with source.open('rb') as input_stream, destination.open('x+b') as output:
            created = True
            shutil.copyfileobj(input_stream, output, 1024**2)
            with zipfile.ZipFile(output, 'a') as candidate:
                info = zipfile.ZipInfo(CACHE_MEMBER)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                candidate.writestr(info, data)
        with zipfile.ZipFile(destination) as candidate:
            if candidate.namelist() != original_names + [CACHE_MEMBER] or candidate.comment != comment:
                raise ValueError('Candidate archive entries changed unexpectedly')
            for item in candidate.infolist():
                if item.filename != CACHE_MEMBER:
                    actual = (item.CRC, item.file_size, item.compress_size, item.header_offset,
                              item.compress_type, item.external_attr, item.date_time)
                    if actual != expected[item.filename]:
                        raise ValueError('Existing archive member metadata changed')
            recovered = candidate.read(CACHE_MEMBER)
            if recovered != data:
                raise ValueError('Recovered member readback failed')
        return {'source_cache_sha256': SOURCE_CACHE_SHA256,
                'candidate_sha256': sha256(destination),
                'candidate_bytes': destination.stat().st_size,
                'added_resource': CACHE_MEMBER, 'added_bytes': len(data),
                'video_md5': EXPECTED_MD5,
                'original_entries_preserved': len(original_names),
                'manifest_or_ledger_changed': False,
                'device_import_or_playback_tested': False}
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_cache', type=Path)
    parser.add_argument('verified_video', type=Path)
    parser.add_argument('output_cache', type=Path)
    args = parser.parse_args()
    print(json.dumps(restore(args.source_cache, args.verified_video, args.output_cache), indent=2))


if __name__ == '__main__':
    main()
