"""Create a separate cache candidate containing the verified original movie.

The original cache and manifests are immutable inputs. Existing compressed ZIP
members are copied intact; one matching missing member is appended. This is
asset recovery, not a claim that the reported black backgrounds are fixed.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
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
RECEIPT_LEDGER = 'Caches/asset_list_base.txtCache.txt'


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verified_movie(video):
    video = Path(video)
    if video.stat().st_size != EXPECTED_BYTES:
        raise ValueError('Movie size does not match the preserved manifest')
    data = video.read_bytes()
    if hashlib.md5(data).hexdigest() != EXPECTED_MD5:
        raise ValueError('Movie digest does not match the preserved manifest')
    return data


def append_receipts(original, receipts, additions):
    """Preserve existing v4 receipt bytes and append only authenticated new paths."""
    from scripts.trace_cache_registration import parse_ledger, logical_path
    before = parse_ledger(original)
    if not original.endswith(b'\n'):
        raise ValueError('Original receipt ledger lacks its expected final newline')
    lines, added = [], []
    for path, digest in sorted(receipts.items()):
        if (any(ord(ch) < 32 for ch in path) or logical_path('/' + path) != path
                or 'Caches/' + path not in additions or not re.fullmatch('[0-9a-f]{32}', digest)):
            raise ValueError('Receipt must name a supplied verified resource and transport MD5')
        existing = before['records'].get(path)
        if existing is not None:
            if existing != digest:
                raise ValueError('Refusing to replace an existing cache receipt hash')
            continue
        lines.append(('/' + path + '\t' + digest + '\n').encode())
        added.append(path)
    output = original + b''.join(lines)
    after = parse_ledger(output)
    if (after['client_revision_token'] != before['client_revision_token']
            or after['entry_count'] != before['entry_count'] + len(added)
            or any(after['records'].get(path) != digest for path, digest in before['records'].items())):
        raise ValueError('Existing cache receipts or revision token changed')
    return output, added


def append_verified_assets(source, destination, additions, *, receipts=None):
    """Append caller-verified resource bytes to a guarded original cache copy."""
    source, destination = map(Path, (source, destination))
    if destination.resolve() == source.resolve() or destination.exists():
        raise FileExistsError('Output must be a new path distinct from the input cache')
    if not additions:
        raise ValueError('No verified resources were supplied')
    for name, data in additions.items():
        parts = name.split('/')
        if (not name.startswith('Caches/') or any(part in ('', '.', '..') or ':' in part for part in parts)
                or '\\' in name or any(ord(ch) < 32 for ch in name)
                or type(data) is not bytes or not 0 < len(data) <= 16 * 1024**2):
            raise ValueError('Unsafe cache member path or unsupported resource size')
    if sha256(source) != SOURCE_CACHE_SHA256:
        raise ValueError('Source cache differs from the preserved original; refusing to modify a copy')
    with zipfile.ZipFile(source) as original:
        original_names = original.namelist()
        if set(additions).intersection(original_names):
            raise ValueError('Cache already contains a target resource')
        if len(original_names) != len(set(original_names)):
            raise ValueError('Source cache has duplicate archive entries')
        expected = {item.filename: (item.CRC, item.file_size, item.compress_size,
                                   item.header_offset, item.compress_type, item.external_attr,
                                   item.date_time) for item in original.infolist()}
        comment = original.comment
        ledger, new_receipts = None, []
        if receipts:
            if original_names.count(RECEIPT_LEDGER) != 1:
                raise ValueError('Expected one original global receipt ledger')
            ledger, new_receipts = append_receipts(original.read(RECEIPT_LEDGER), receipts, additions)
            if not new_receipts:
                ledger = None
        original_expanded_bytes = sum(item.file_size for item in original.infolist())
    required_bytes = (original_expanded_bytes if ledger is not None else source.stat().st_size)
    required_bytes += sum(map(len, additions.values())) + 5 * 1024**2
    if shutil.disk_usage(destination.parent).free < required_bytes:
        raise OSError('Insufficient free space for the separate cache candidate')
    created = False
    try:
        if ledger is None:
            with source.open('rb') as input_stream, destination.open('x+b') as output:
                created = True
                shutil.copyfileobj(input_stream, output, 1024**2)
                with zipfile.ZipFile(output, 'a') as candidate:
                    for name, data in additions.items():
                        info = zipfile.ZipInfo(name)
                        info.compress_type = zipfile.ZIP_DEFLATED
                        info.external_attr = (stat.S_IFREG | 0o644) << 16
                        candidate.writestr(info, data)
        else:
            # Public zipfile APIs rewrite one ledger without duplicate ZIP names.
            # All other uncompressed content and essential metadata are preserved;
            # compression bytes and archive offsets may be regenerated.
            with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination, 'x') as candidate:
                created = True
                candidate.comment = original.comment
                for item in original.infolist():
                    data = ledger if item.filename == RECEIPT_LEDGER else original.read(item)
                    candidate.writestr(copy.copy(item), data)
                for name, data in additions.items():
                    info = zipfile.ZipInfo(name)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = (stat.S_IFREG | 0o644) << 16
                    candidate.writestr(info, data)
        with zipfile.ZipFile(destination) as candidate:
            if candidate.namelist() != original_names + list(additions) or candidate.comment != comment:
                raise ValueError('Candidate archive entries changed unexpectedly')
            for item in candidate.infolist():
                if item.filename not in additions:
                    actual = (item.CRC, item.file_size, item.compress_size, item.header_offset,
                              item.compress_type, item.external_attr, item.date_time)
                    indices = range(7) if ledger is None else (0, 1, 4, 5, 6)
                    if ledger is not None and item.filename == RECEIPT_LEDGER:
                        indices = (4, 5, 6)
                    if any(actual[index] != expected[item.filename][index] for index in indices):
                        raise ValueError('Existing archive member metadata changed')
            if ledger is not None and candidate.read(RECEIPT_LEDGER) != ledger:
                raise ValueError('Updated receipt ledger readback failed')
            for name, data in additions.items():
                if candidate.read(name) != data:
                    raise ValueError('Recovered member readback failed')
        return {'source_cache_sha256': SOURCE_CACHE_SHA256,
                'candidate_sha256': sha256(destination),
                'candidate_bytes': destination.stat().st_size,
                'added_resources': [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                                    for name, data in additions.items()],
                'added_bytes': sum(map(len, additions.values())),
                'original_entries_preserved': len(original_names),
                'manifest_or_ledger_changed': ledger is not None,
                'manifest_changed': False, 'receipt_ledger_changed': ledger is not None,
                'new_receipt_paths': new_receipts,
                'original_compressed_records_copied': ledger is None,
                'device_import_or_playback_tested': False}
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise


def restore(source, video, destination):
    source, video, destination = map(Path, (source, video, destination))
    if destination.resolve() in (source.resolve(), video.resolve()) or destination.exists():
        raise FileExistsError('Output must be a new path distinct from both inputs')
    data = verified_movie(video)
    result = append_verified_assets(source, destination, {CACHE_MEMBER: data})
    result.update(added_resource=CACHE_MEMBER, video_md5=EXPECTED_MD5)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_cache', type=Path)
    parser.add_argument('verified_video', type=Path)
    parser.add_argument('output_cache', type=Path)
    args = parser.parse_args()
    print(json.dumps(restore(args.source_cache, args.verified_video, args.output_cache), indent=2))


if __name__ == '__main__':
    main()
