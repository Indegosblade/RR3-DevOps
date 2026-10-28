"""Recover only exact iOS-manifest matches from a public matching-version ZIP.

The archive originated on Android. A same filename is not compatibility proof:
this tool requires equal iOS transport/stored sizes and the exact expected MD5.
It performs no texture conversion, atlas renaming, cache update or installation.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import urllib.error
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.recover_speedrush_video import ARCHIVE_URL, ARCHIVE_BYTES, SOURCE_PAGE, BoundedRangeReader

PREFIX = 'com.ea.games.r3_row/files/.depot/'
GUI_PREFIX = 'gui_assets/2048x1536/'
MAX_REQUEST = 16 * 1024**2
MAX_TOTAL = 128 * 1024**2
ARCHIVE_SOURCES = {
    'adreno': (ARCHIVE_URL, ARCHIVE_BYTES),
    'mali': ('https://archive.org/download/com.ea.games.r3_row_MALI_14.0.1/com.ea.games.r3_row_MALI.zip', 5808584640),
}


def safe_logical_path(path):
    parts = path.split('/')
    return (path.startswith(GUI_PREFIX) and not any(part in ('', '.', '..') or ':' in part for part in parts)
            and '\\' not in path and '\0' not in path)


def missing_hd_records(ipa_path, cache_path):
    """Read exact manifest representations; keep conflicts rather than guessing."""
    available, records, owners = set(), defaultdict(set), defaultdict(set)
    with zipfile.ZipFile(ipa_path) as ipa, zipfile.ZipFile(cache_path) as cache:
        for archive, prefix in ((ipa, 'Payload/RealRacing3.app/res/'), (cache, 'Caches/')):
            available.update(item.filename[len(prefix):] for item in archive.infolist()
                             if item.filename.startswith(prefix) and not item.is_dir())
        for item in ipa.infolist():
            name = item.filename.rsplit('/', 1)[-1]
            if not name.startswith('asset_list_') or not name.endswith('.txt'):
                continue
            for line in ipa.read(item).decode('utf-8', errors='replace').splitlines():
                fields = line.rsplit(None, 3)
                if len(fields) != 4 or not fields[0].startswith('/' + GUI_PREFIX):
                    continue
                if not re.fullmatch(r'[0-9a-f]{32}', fields[1]) or not all(value.isdecimal() for value in fields[2:]):
                    continue
                path = fields[0].lstrip('/')
                records[path].add((fields[1], int(fields[2]), int(fields[3])))
                owners[path].add(name)
    return {path: {'representations': [dict(md5=md5, transport_bytes=transport, stored_bytes=stored)
                                      for md5, transport, stored in sorted(values)],
                   'manifests': sorted(owners[path])}
            for path, values in sorted(records.items()) if path not in available}


def inventory_candidates(records, archive):
    members = defaultdict(list)
    for info in archive.infolist():
        members[info.filename].append(info)
    candidates, excluded = [], []
    for path, record in records.items():
        reason = None
        if not safe_logical_path(path):
            reason = 'unsafe_logical_path'
        elif not path.endswith('.rgb.pvr.z'):
            reason = 'outside_exact_rgb_texture_scope'
        elif len(record['representations']) != 1:
            reason = 'conflicting_ios_manifest_representations'
        else:
            expected = record['representations'][0]
            matches = members.get(PREFIX + path, [])
            if expected['transport_bytes'] != expected['stored_bytes']:
                reason = 'transport_and_stored_sizes_differ'
            elif not matches:
                reason = 'exact_member_name_absent'
            elif len(matches) != 1:
                reason = 'duplicate_archive_member'
            elif matches[0].file_size != expected['stored_bytes']:
                reason = 'stored_size_mismatch'
            elif not 0 < matches[0].file_size <= MAX_REQUEST or matches[0].compress_size > MAX_REQUEST:
                reason = 'member_exceeds_per_request_or_memory_limit'
            else:
                candidates.append({'path': path, 'member': matches[0].filename,
                                   'compressed_bytes': matches[0].compress_size,
                                   'expected': expected, 'manifests': record['manifests']})
        if reason:
            excluded.append({'path': path, 'reason': reason})
    # Recover smaller exact-name candidates first within the fixed range budget.
    candidates.sort(key=lambda item: (item['compressed_bytes'], item['path']))
    return candidates, excluded


def archive_mapping(archive):
    names = archive.namelist()
    members = [name for name in names if name.startswith(PREFIX)]
    if not members:
        raise ValueError('Expected .depot member prefix is absent; a zero-candidate result would be unverified')
    return {'archive_entries': len(names), 'member_prefix': PREFIX,
            'matching_prefix_entries': len(members),
            'hd_gui_examples': [name for name in members if name.startswith(PREFIX + GUI_PREFIX)
                                and not name.endswith('/')][:8]}


def recover_optional(ipa_path, cache_path, destination, *, reader=None, max_total_bytes=MAX_TOTAL,
                     recover=False, progress=None, archive_source='adreno'):
    if not 0 < max_total_bytes <= MAX_TOTAL:
        raise ValueError('The complete range-payload budget must be from 1 byte to 128 MiB')
    if archive_source not in ARCHIVE_SOURCES:
        raise ValueError('Unknown preservation archive source')
    archive_url, archive_bytes = ARCHIVE_SOURCES[archive_source]
    records = missing_hd_records(ipa_path, cache_path)
    with Path(ipa_path).open('rb') as manifest_source:
        manifest_archive_sha256 = hashlib.file_digest(manifest_source, 'sha256').hexdigest()
    source = reader if reader is not None else BoundedRangeReader(
        archive_url, archive_bytes, max_request_bytes=MAX_REQUEST, max_total_bytes=max_total_bytes)
    if source.max_request_bytes > MAX_REQUEST or source.max_total_bytes > max_total_bytes:
        raise ValueError('Injected reader exceeds the requested range limits')
    effective_budget = min(max_total_bytes, source.max_total_bytes)
    destination = Path(destination).resolve()
    recovered, rejected, deferred, already_verified = [], [], [], []
    consecutive_errors = 0
    with zipfile.ZipFile(source) as archive:
        mapping = archive_mapping(archive)
        candidates, excluded = inventory_candidates(records, archive)
        inventory_bytes = source.transferred
        if progress:
            progress({'phase': 'inventory', 'missing_hd_paths': len(records), 'exact_name_size_candidates': len(candidates),
                      'excluded_reasons': dict(Counter(row['reason'] for row in excluded)),
                      'range_bytes_read': inventory_bytes})
        if recover:
            for index, candidate in enumerate(candidates):
                logical = candidate['path']
                output = destination.joinpath(*PurePosixPath(logical).parts)
                provenance_path = output.with_name(output.name + '.provenance.json')
                if not output.resolve().is_relative_to(destination):
                    raise ValueError('Recovery output left the intended directory')
                if output.exists() or provenance_path.exists():
                    expected = candidate['expected']
                    if output.is_file() and not output.is_symlink() and output.stat().st_size == expected['stored_bytes']:
                        with output.open('rb') as existing:
                            verified_md5 = hashlib.file_digest(existing, 'md5').hexdigest()
                        if verified_md5 == expected['md5']:
                            already_verified.append({'path': logical, 'reason': 'verified_local_file_already_present',
                                                     'md5': verified_md5, 'archive_member_not_downloaded': True})
                            continue
                    rejected.append({'path': logical, 'reason': 'destination_exists'})
                    continue
                # Header+name+extra reads are also counted by the underlying reader.
                info = archive.getinfo(candidate['member'])
                estimate = candidate['compressed_bytes'] + 30 + len(info.filename.encode('utf-8')) + len(info.extra)
                if source.transferred + estimate > effective_budget:
                    deferred.extend({'path': row['path'], 'reason': 'remaining_range_budget'} for row in candidates[index:])
                    break
                try:
                    data = archive.read(info)  # Complete ZIP member read validates CRC.
                    consecutive_errors = 0
                except (OSError, ValueError, zipfile.BadZipFile, urllib.error.URLError) as exc:
                    reason = 'range_budget' if 'budget' in str(exc).lower() else 'retrieval_or_zip_integrity_error'
                    rejected.append({'path': logical, 'reason': reason, 'detail': str(exc)[:240]})
                    consecutive_errors += 1
                    if reason == 'range_budget' or consecutive_errors >= 3:
                        deferred.extend({'path': row['path'], 'reason': reason} for row in candidates[index + 1:])
                        break
                    continue
                expected = candidate['expected']
                actual_md5 = hashlib.md5(data).hexdigest()
                if len(data) != expected['stored_bytes'] or actual_md5 != expected['md5']:
                    rejected.append({'path': logical, 'reason': 'ios_manifest_hash_or_size_mismatch',
                                     'actual_bytes': len(data), 'actual_md5': actual_md5})
                    continue
                provenance = {'source_page': SOURCE_PAGE, 'archive_url': source.url,
                              'archive_bytes': source.size, 'member': candidate['member'],
                              'ios_manifest_archive_sha256': manifest_archive_sha256,
                              'logical_path': logical, 'ios_manifests': candidate['manifests'],
                              'ios_transport_bytes': expected['transport_bytes'], 'ios_stored_bytes': expected['stored_bytes'],
                              'bytes': len(data), 'md5': actual_md5, 'sha256': hashlib.sha256(data).hexdigest(),
                              'zip_crc_verified': True, 'exact_ios_manifest_representation': True,
                              'platform_conversion_performed': False, 'cache_modified': False, 'device_tested': False}
                output.parent.mkdir(parents=True, exist_ok=True)
                if not output.resolve().is_relative_to(destination):
                    raise ValueError('Recovery output left the intended directory')
                with output.open('xb') as stream:
                    stream.write(data)
                with provenance_path.open('x', encoding='utf-8') as stream:
                    json.dump(provenance, stream, indent=2)
                    stream.write('\n')
                recovered.append(provenance)
                if progress:
                    progress({'phase': 'recovered', 'path': logical, 'bytes': len(data),
                              'recovered_count': len(recovered), 'range_bytes_read': source.transferred})
    return {'source_page': SOURCE_PAGE, 'archive_source': archive_source,
            'archive_url': source.url, 'archive_bytes': source.size,
            'archive_mapping': mapping,
            'ios_manifest_archive_sha256': manifest_archive_sha256,
            'scope': 'Exact-name .rgb.pvr.z paths absent from the current iOS HD inventory; no platform conversion',
            'missing_hd_paths': len(records), 'candidate_count': len(candidates), 'candidates': candidates,
            'excluded': excluded, 'excluded_reasons': dict(Counter(row['reason'] for row in excluded)),
            'recovery_requested': recover, 'recovered': recovered, 'already_verified_local': already_verified,
            'rejected': rejected, 'deferred': deferred,
            'inventory_range_bytes': inventory_bytes, 'range_bytes_read': source.transferred,
            'range_requests': source.requests, 'range_budget_bytes': effective_budget,
            'per_request_limit_bytes': MAX_REQUEST, 'cache_modified': False, 'device_tested': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ipa', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--recover', action='store_true', help='Write only verified original bytes; default is inventory only')
    parser.add_argument('--max-total-mib', type=int, default=128)
    parser.add_argument('--archive-source', choices=sorted(ARCHIVE_SOURCES), default='adreno')
    args = parser.parse_args()
    if not 1 <= args.max_total_mib <= 128:
        parser.error('--max-total-mib must be from 1 to 128')
    if args.report.exists():
        raise FileExistsError('Refusing to overwrite an existing recovery report')
    allowed = (ROOT / 'investigation/recovered_assets/optional').resolve()
    if not args.output_directory.resolve().is_relative_to(allowed) or not args.report.resolve().is_relative_to(allowed):
        parser.error('Recovery bytes and reports must stay under ignored investigation/recovered_assets/optional/')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    result = recover_optional(args.ipa, args.cache, args.output_directory,
                              max_total_bytes=args.max_total_mib * 1024**2, recover=args.recover,
                              archive_source=args.archive_source,
                              progress=lambda value: print(json.dumps(value), flush=True))
    with args.report.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps({key: len(value) if isinstance(value, list) else value for key, value in result.items()}, indent=2))


if __name__ == '__main__':
    main()
