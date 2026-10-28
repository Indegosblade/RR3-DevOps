"""Find missing HD GUI assets by exact content identity in original local ZIPs.

Logical names only identify manifest targets. Source member names never establish
identity: acceptance requires the target transport size and MD5. No network or
working cache writes are performed.
"""
import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.recover_optional_assets import GUI_PREFIX, safe_logical_path

MAX_MEMBER = 16 * 1024**2
MAX_TOTAL = 4 * 1024**3
PREFIXES = ('Payload/RealRacing3.app/res/', 'Caches/')


class PayloadBudget:
    """Charge declared expanded member bytes before opening a ZIP payload."""
    def __init__(self, maximum):
        if not 0 < maximum <= MAX_TOTAL:
            raise ValueError('Payload budget must be from 1 byte through 4 GiB')
        self.maximum = maximum
        self.used = 0

    def read(self, archive, info):
        if self.used + info.file_size > self.maximum:
            return None
        self.used += info.file_size  # Failed CRC reads still consume their reservation.
        data = archive.read(info)  # Complete reads validate ZIP CRC.
        if len(data) != info.file_size:
            raise ValueError('ZIP member length differs from declared length')
        return data


def resource_name(info, prefix):
    if info.is_dir() or not info.filename.startswith(prefix):
        return None
    logical = info.filename[len(prefix):]
    parts = logical.split('/')
    if any(part in ('', '.', '..', '__MACOSX', 'investigation', 'reports', 'runtime', 'private')
           or part.startswith('._') or ':' in part for part in parts):
        return None
    if '\\' in logical or any(ord(char) < 32 for char in logical):
        return None
    return logical


def original_records(archives, budget):
    """Keep original missing inventory independent of separately recovered bytes."""
    available, records, owners, manifest_sources = set(), defaultdict(set), defaultdict(set), {}
    for archive, prefix in zip(archives, PREFIXES):
        available.update(name for info in archive.infolist()
                         if (name := resource_name(info, prefix)) is not None)
    ipa = archives[0]
    names = Counter(info.filename for info in ipa.infolist())
    for info in ipa.infolist():
        logical = resource_name(info, PREFIXES[0])
        if logical is None or not logical.startswith('asset_list_') or not logical.endswith('.txt'):
            continue
        if names[info.filename] != 1:
            raise ValueError('Duplicate authoritative manifest ZIP member')
        if info.file_size > MAX_MEMBER:
            raise ValueError('Manifest exceeds the per-member bound')
        data = budget.read(ipa, info)
        if data is None:
            raise ValueError('Payload budget cannot cover authoritative manifest inventory')
        manifest_sources[info.filename] = hashlib.sha256(data).hexdigest()
        for line in data.decode('utf-8', errors='strict').splitlines():
            fields = line.rsplit(None, 3)
            if len(fields) != 4 or not fields[0].startswith('/' + GUI_PREFIX):
                continue
            if not re.fullmatch('[0-9a-f]{32}', fields[1]) or not all(x.isdecimal() for x in fields[2:]):
                raise ValueError('Malformed HD manifest record')
            path = fields[0].lstrip('/')
            records[path].add((fields[1], int(fields[2]), int(fields[3])))
            owners[path].add(info.filename)
    return {path: {'representations': [dict(md5=h, transport_bytes=t, stored_bytes=s)
                                      for h, t, s in sorted(values)],
                   'manifests': sorted(owners[path])}
            for path, values in sorted(records.items()) if path not in available}, manifest_sources


def representation(data, expected, mode):
    if len(data) != expected['stored_bytes']:
        return None
    transport = data if mode == 'identical_stored_transport' else b'FMASZ1' + zlib.compress(data, 6)
    if len(transport) != expected['transport_bytes'] or hashlib.md5(transport).hexdigest() != expected['md5']:
        return None
    return {'stored_bytes': len(data), 'stored_sha256': hashlib.sha256(data).hexdigest(),
            'transport_bytes': len(transport), 'transport_md5': expected['md5'],
            'transport_sha256': hashlib.sha256(transport).hexdigest(), 'representation': mode}


def write_verified(destination, path, data, provenance):
    output = destination.joinpath(*PurePosixPath(path).parts)
    sidecar = output.with_name(output.name + '.provenance.json')
    if not output.resolve().is_relative_to(destination):
        raise ValueError('Recovery output leaves its destination')
    if output.exists() or sidecar.exists() or output.is_symlink() or sidecar.is_symlink():
        raise FileExistsError('Refusing to replace existing asset or provenance')
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.resolve().is_relative_to(destination):
        raise ValueError('Recovery output leaves its destination')
    owned_output, owned_sidecar = False, False
    try:
        with output.open('xb') as stream:
            owned_output = True
            stream.write(data)
        with sidecar.open('x', encoding='utf-8') as stream:
            owned_sidecar = True
            json.dump(provenance, stream, indent=2)
            stream.write('\n')
    except BaseException:
        # Only exclusive creations owned by this call may be removed. A file
        # that occupied either path before our open must survive the failure.
        for created, path in ((owned_sidecar, sidecar), (owned_output, output)):
            if created:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass  # Preserve the original write/close failure.
        raise


def recover_local(ipa_path, cache_path, destination, *, max_total_bytes=MAX_TOTAL,
                  recover=False, dedupe_roots=(), progress=None):
    budget = PayloadBudget(max_total_bytes)
    destination = Path(destination).resolve()
    sources = [Path(ipa_path).resolve(), Path(cache_path).resolve()]
    matched, recovered, existing, excluded, rejected, deferred = [], [], [], [], [], []
    with ExitStack() as stack:
        archives = [stack.enter_context(zipfile.ZipFile(path)) for path in sources]
        records, manifests = original_records(archives, budget)
        manifest_bytes = budget.used
        indexes = defaultdict(list)
        eligible = {}
        for path, record in records.items():
            reason = None
            if not safe_logical_path(path) or any(ord(char) < 32 for char in path):
                reason = 'unsafe_target_path'
            elif len(record['representations']) != 1:
                reason = 'conflicting_manifest_representations'
            else:
                expected = record['representations'][0]
                if not 0 < expected['stored_bytes'] <= MAX_MEMBER:
                    reason = 'target_exceeds_member_bound'
                elif expected['transport_bytes'] == expected['stored_bytes']:
                    mode = 'identical_stored_transport'
                elif path.endswith('.ios.atlas'):
                    mode = 'FMASZ1_zlib_level_6'
                else:
                    reason = 'unsupported_transport_representation'
            if reason:
                excluded.append({'path': path, 'reason': reason})
                continue
            eligible[path] = (expected, mode)

        # Authenticate earlier recoveries independently; they do not alter the
        # original missing-path count and are never used as discovery sources.
        for path, (expected, mode) in eligible.items():
            for root in dict.fromkeys([destination, *(Path(p).resolve() for p in dedupe_roots)]):
                output = root.joinpath(*PurePosixPath(path).parts)
                sidecar = output.with_name(output.name + '.provenance.json')
                if not output.exists() and not output.is_symlink() and not sidecar.exists():
                    continue
                proof = None
                if (output.resolve().is_relative_to(root) and output.is_file() and not output.is_symlink()
                        and output.stat().st_size == expected['stored_bytes']):
                    if budget.used + expected['stored_bytes'] <= budget.maximum:
                        budget.used += expected['stored_bytes']
                        proof = representation(output.read_bytes(), expected, mode)
                    else:
                        deferred.append({'path': path, 'reason': 'local_deduplication_budget'})
                if proof:
                    existing.append({'path': path, 'file': str(output), **proof})
                    break
                if root == destination:
                    rejected.append({'path': path, 'reason': 'unknown_existing_destination'})
                    break
        completed = {item['path'] for item in existing} | {item['path'] for item in rejected}
        for path, (expected, mode) in eligible.items():
            if path not in completed:
                indexes[(expected['stored_bytes'], mode)].append(path)
        # Index sizes, never basenames. This permits original bytes under a
        # different resource path without accepting similar-looking artwork.
        candidates, inventory = [], Counter()
        for source_index, (archive, prefix) in enumerate(zip(archives, PREFIXES)):
            duplicates = Counter(info.filename for info in archive.infolist())
            for info in archive.infolist():
                if resource_name(info, prefix) is None:
                    inventory['outside_resource_scope'] += 1
                elif duplicates[info.filename] != 1:
                    inventory['duplicate_source_name'] += 1
                elif not 0 < info.file_size <= MAX_MEMBER or info.compress_size > MAX_MEMBER:
                    inventory['source_exceeds_member_bound'] += 1
                elif any((info.file_size, mode) in indexes for mode in
                         ('identical_stored_transport', 'FMASZ1_zlib_level_6')):
                    candidates.append((source_index, info))
                else:
                    inventory['no_target_stored_size'] += 1
        candidates.sort(key=lambda pair: (pair[1].file_size, pair[0], pair[1].filename))
        if progress:
            progress({'phase': 'inventory', 'original_missing_hd_paths': len(records),
                      'size_candidate_members': len(candidates), 'already_verified_local': len(existing),
                      'manifest_payload_bytes': manifest_bytes})
        scanned, no_match = 0, 0
        for source_index, info in candidates:
            pending = [path for mode in ('identical_stored_transport', 'FMASZ1_zlib_level_6')
                       for path in indexes.get((info.file_size, mode), []) if path not in completed]
            if not pending:
                continue
            try:
                data = budget.read(archives[source_index], info)
            except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
                rejected.append({'source_member': info.filename, 'source_archive': str(sources[source_index]),
                                 'reason': 'zip_integrity_or_read_failure', 'detail': str(exc)[:240]})
                continue
            if data is None:
                deferred.append({'source_archive': str(sources[source_index]), 'source_member': info.filename,
                                 'bytes': info.file_size, 'reason': 'remaining_payload_budget'})
                continue
            scanned += 1
            proofs = {}
            for mode in ('identical_stored_transport', 'FMASZ1_zlib_level_6'):
                if any(eligible[path][1] == mode for path in pending):
                    transport = data if mode == 'identical_stored_transport' else b'FMASZ1' + zlib.compress(data, 6)
                    proofs[mode] = (len(transport), hashlib.md5(transport).hexdigest())
            matches = [path for path in pending if proofs[eligible[path][1]] ==
                       (eligible[path][0]['transport_bytes'], eligible[path][0]['md5'])]
            no_match += not matches
            for path in matches:
                expected, mode = eligible[path]
                proof = representation(data, expected, mode)
                provenance = {'logical_path': path, 'source_archive': str(sources[source_index]),
                              'source_archive_bytes': sources[source_index].stat().st_size,
                              'source_member': info.filename, 'source_member_crc32': f'{info.CRC:08x}',
                              'manifest_members_sha256': {name: manifests[name] for name in records[path]['manifests']},
                              **proof, 'zip_crc_verified': True, 'exact_ios_manifest_representation': True,
                              'zlib_runtime_version': zlib.ZLIB_RUNTIME_VERSION, 'stored_bytes_edited': False,
                              'cache_modified': False, 'device_tested': False}
                matched.append(provenance)
                if recover:
                    write_verified(destination, path, data, provenance)
                    recovered.append(provenance)
                completed.add(path)
                if progress:
                    progress({'phase': 'exact_match', 'path': path, 'source_member': info.filename,
                              'matched_count': len(matched), 'payload_bytes_read': budget.used})
    return {'scope': 'Content-hash search within original IPA res and cache Caches resource roots',
            'original_missing_hd_paths': len(records), 'eligible_target_paths': len(eligible),
            'size_candidate_members': len(candidates), 'scanned_candidate_members': scanned,
            'candidate_members_without_exact_match': no_match, 'source_inventory_exclusions': dict(inventory),
            'excluded_targets': excluded, 'excluded_reasons': dict(Counter(item['reason'] for item in excluded)),
            'already_verified_local': existing, 'exact_matches': matched, 'recovered': recovered,
            'rejected': rejected, 'deferred': deferred,
            'unresolved_target_paths': sorted(set(records) - {item['path'] for item in existing}
                                             - {item['logical_path'] for item in matched}),
            'manifest_payload_bytes': manifest_bytes, 'payload_bytes_read': budget.used,
            'payload_budget_bytes': budget.maximum, 'maximum_member_bytes': MAX_MEMBER,
            'recovery_requested': recover, 'source_archives_modified': False, 'device_tested': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ipa', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--recover', action='store_true')
    parser.add_argument('--max-total-mib', type=int, default=4096)
    args = parser.parse_args()
    allowed = (ROOT / 'investigation/recovered_assets/local').resolve()
    if not args.output_directory.resolve().is_relative_to(allowed) or not args.report.resolve().is_relative_to(allowed):
        parser.error('Outputs and reports must remain under ignored investigation/recovered_assets/local/')
    if not 1 <= args.max_total_mib <= 4096:
        parser.error('--max-total-mib must be from 1 to 4096')
    if args.report.exists() or args.report.is_symlink():
        raise FileExistsError('Refusing to replace an existing recovery report')
    result = recover_local(args.ipa, args.cache, args.output_directory, recover=args.recover,
                           max_total_bytes=args.max_total_mib * 1024**2,
                           dedupe_roots=[ROOT / 'investigation/recovered_assets/optional'],
                           progress=lambda value: print(json.dumps(value), flush=True))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: len(value) if isinstance(value, list) else value
                      for key, value in result.items()}, indent=2))


if __name__ == '__main__':
    main()
