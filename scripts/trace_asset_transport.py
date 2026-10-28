"""Trace the guarded asset finalizer and verify FMASZ1 atlas representations.

Read-only by default. Optional recovery writes only exact manifest matches under
ignored research storage; no IPA, working cache, signature or device is changed.
"""
import argparse
from collections import defaultdict
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
from build_4k_v3 import BINARY_PATH, SUPPORTED_MACHO_UUID, macho_uuid
from scripts.audit_sdk_dependencies import MachO
from scripts.recover_optional_assets import PREFIX, safe_logical_path
from scripts.recover_speedrush_video import (ARCHIVE_URL, ARCHIVE_BYTES, SOURCE_PAGE,
                                              BoundedRangeReader)
from scripts.trace_sdk_lifecycle import imported_symbol_at

MAGIC = b'FMASZ1'
MAX_ATLAS = 8 * 1024**2
MAX_TOTAL = 16 * 1024**2
FINALIZER = 0x1016CC0C4
FINALIZER_BYTES = 876
FINALIZER_SHA256 = '009fd7510f0e51ea9db179da0f28a23ab20e4215a60eeba26a83fc818b38b9a8'
TARGET_ROOT = 'gui_assets/2048x1536/quests/hybrid_highway/'
TARGETS = tuple(TARGET_ROOT + folder + 'sprites.ios.atlas' for folder in ('', 'splash/', 'large/'))
IMPORTS = {0x102272420: '_inflateInit_', 0x1022723FC: '_inflate',
           0x102272408: '_inflateEnd', 0x102271820: '_fread',
           0x1022718B0: '_fwrite', 0x102272D74: '_remove', 0x102272D8C: '_rename'}


def atlas_transport(stored):
    """Reconstruct the observed level-6 zlib representation, without editing XML."""
    if not 0 < len(stored) <= MAX_ATLAS:
        raise ValueError('Atlas stored bytes exceed the bounded scope')
    return MAGIC + zlib.compress(stored, 6)


def decode_transport(data, *, max_output=MAX_ATLAS):
    """Strict bounded host validation; reject truncation and trailing streams."""
    if not data.startswith(MAGIC) or not 0 < max_output <= MAX_ATLAS:
        raise ValueError('Expected FMASZ1 transport and a bounded output size')
    stream = zlib.decompressobj()
    try:
        result = stream.decompress(data[len(MAGIC):], max_output + 1)
    except zlib.error as exc:
        raise ValueError('Invalid zlib asset payload') from exc
    if len(result) > max_output or stream.unconsumed_tail:
        raise ValueError('Asset decompression exceeds the output limit')
    if not stream.eof or stream.unused_data:
        raise ValueError('Truncated asset or extra bytes after its zlib stream')
    return result


def verify_stored(stored, expected):
    """The manifest MD5 belongs to the transport, not the expanded XML file."""
    if len(stored) != expected['stored_bytes']:
        raise ValueError('Atlas stored size differs from the iOS manifest')
    transport = atlas_transport(stored)
    digest = hashlib.md5(transport).hexdigest()
    if len(transport) != expected['transport_bytes'] or digest != expected['md5']:
        raise ValueError('Atlas reconstructed transport differs from the iOS manifest')
    if decode_transport(transport) != stored:
        raise ValueError('Atlas transport failed its lossless host round trip')
    return {'stored_bytes': len(stored), 'stored_sha256': hashlib.sha256(stored).hexdigest(),
            'transport_bytes': len(transport), 'transport_md5': digest,
            'transport_sha256': hashlib.sha256(transport).hexdigest(),
            'exact_ios_manifest_representation': True}


def atlas_records(ipa):
    records, owners = defaultdict(set), defaultdict(set)
    for info in ipa.infolist():
        name = info.filename.rsplit('/', 1)[-1]
        if not name.startswith('asset_list_') or not name.endswith('.txt'):
            continue
        for line in ipa.read(info).decode('utf-8', errors='strict').splitlines():
            fields = line.rsplit(None, 3)
            if len(fields) != 4 or not fields[0].endswith('.ios.atlas'):
                continue
            if not re.fullmatch('[0-9a-f]{32}', fields[1]) or not all(x.isdecimal() for x in fields[2:]):
                raise ValueError('Malformed iOS atlas manifest representation')
            path = fields[0].lstrip('/')
            records[path].add((fields[1], int(fields[2]), int(fields[3])))
            owners[path].add(name)
    return {path: {'representations': [dict(md5=h, transport_bytes=t, stored_bytes=s)
                                      for h, t, s in sorted(values)],
                   'manifests': sorted(owners[path])}
            for path, values in sorted(records.items())}


def trace_binary(binary):
    if macho_uuid(binary) != SUPPORTED_MACHO_UUID:
        raise ValueError('Unsupported main executable UUID')
    image = MachO(binary)
    offset = image.vm_offset(FINALIZER, FINALIZER_BYTES)
    digest = hashlib.sha256(image.data[offset:offset + FINALIZER_BYTES]).hexdigest()
    if digest != FINALIZER_SHA256:
        raise ValueError('Asset finalizer instructions differ from the researched build')
    for address, expected in IMPORTS.items():
        if imported_symbol_at(image, address) != expected:
            raise ValueError('Asset finalizer import binding differs from the researched build')
    for address, expected in ((0x102740F7D, 'DecompressAsset'),
                              (0x102740F8D, 'AssetManager.cpp'),
                              (0x102740B00, 'FinaliseDownloadedAssetFile')):
        if image.vm_string(address) != expected:
            raise ValueError('Asset finalizer diagnostic identity differs')
    return {'executable_uuid': SUPPORTED_MACHO_UUID.hex(), 'function': hex(FINALIZER),
            'function_bytes': FINALIZER_BYTES, 'function_sha256': digest,
            'imported_symbols': {hex(a): name for a, name in IMPORTS.items()},
            'magic': MAGIC.decode(), 'header_bytes': len(MAGIC),
            'codec': 'zlib stream after six-byte FMASZ1 header; no XOR in this finalizer',
            'evidence': 'Guarded ARM64 instructions and bound imported symbols; no device execution'}


def validate_existing(ipa_path, cache_path):
    """Validate all unambiguous compressed atlas representations available locally."""
    counts = defaultdict(int)
    failures = []
    with zipfile.ZipFile(ipa_path) as ipa, zipfile.ZipFile(cache_path) as cache:
        records = atlas_records(ipa)
        available = defaultdict(list)
        for archive, prefix in ((ipa, 'Payload/RealRacing3.app/res/'), (cache, 'Caches/')):
            for info in archive.infolist():
                if info.filename.startswith(prefix) and not info.is_dir():
                    available[info.filename[len(prefix):]].append((archive, info))
        for path, record in records.items():
            if len(record['representations']) != 1:
                counts['conflicting_manifest_paths'] += 1
                continue
            expected = record['representations'][0]
            if expected['transport_bytes'] == expected['stored_bytes']:
                counts['equal_size_paths_excluded'] += 1
                continue
            sources = available.get(path, [])
            if not sources:
                counts['missing_compressed_paths'] += 1
                continue
            counts['existing_compressed_paths'] += 1
            for archive, info in sources:
                counts['existing_compressed_members'] += 1
                try:
                    if info.file_size > MAX_ATLAS:
                        raise ValueError('Atlas archive member exceeds memory bound')
                    verify_stored(archive.read(info), expected)
                    counts['exact_transport_matches'] += 1
                except ValueError as exc:
                    failures.append({'path': path, 'reason': str(exc)})
        binary_trace = trace_binary(ipa.read(BINARY_PATH))
    return {'binary_trace': binary_trace, 'local_atlas_validation': dict(counts),
            'failures': failures, 'zlib_runtime_version': zlib.ZLIB_RUNTIME_VERSION,
            'codec_validation_complete': not failures and counts['exact_transport_matches'] > 0,
            'cache_modified': False, 'device_tested': False}


def recover_atlases(ipa_path, cache_path, destination, *, reader=None):
    """Accept Android-origin stored bytes only after exact iOS transport proof."""
    validation = validate_existing(ipa_path, cache_path)
    if not validation['codec_validation_complete']:
        raise ValueError('Existing iOS atlases do not validate this transport reconstruction')
    with zipfile.ZipFile(ipa_path) as ipa, zipfile.ZipFile(cache_path) as cache:
        records = atlas_records(ipa)
        existing = set(cache.namelist()) | set(ipa.namelist())
    with Path(ipa_path).open('rb') as stream:
        manifest_sha256 = hashlib.file_digest(stream, 'sha256').hexdigest()
    source = reader if reader is not None else BoundedRangeReader(
        ARCHIVE_URL, ARCHIVE_BYTES, max_total_bytes=MAX_TOTAL)
    if source.max_total_bytes > MAX_TOTAL or source.max_request_bytes > MAX_TOTAL:
        raise ValueError('Range reader exceeds the 16 MiB recovery bound')
    destination = Path(destination).resolve()
    recovered = []
    with zipfile.ZipFile(source) as archive:
        for path in TARGETS:
            if not safe_logical_path(path):
                raise ValueError('Unsafe atlas logical path')
            if 'Caches/' + path in existing or 'Payload/RealRacing3.app/res/' + path in existing:
                raise ValueError('Target atlas already exists in the original inputs')
            record = records[path]
            if len(record['representations']) != 1:
                raise ValueError('Conflicting target iOS representations')
            expected = record['representations'][0]
            member = PREFIX + path.removesuffix('.ios.atlas') + '.android.atlas'
            matches = [info for info in archive.infolist() if info.filename == member]
            if len(matches) != 1 or matches[0].file_size != expected['stored_bytes']:
                raise ValueError('Expected one same-size source atlas member')
            info = matches[0]
            if not 0 < info.file_size <= MAX_ATLAS or info.compress_size > MAX_ATLAS:
                raise ValueError('Atlas member exceeds the bounded recovery scope')
            stored = archive.read(info)  # A complete read verifies the ZIP CRC.
            proof = verify_stored(stored, expected)
            provenance = {'logical_path': path, 'source_member': member,
                          'source_page': SOURCE_PAGE, 'archive_url': source.url,
                          'archive_bytes': source.size, 'ios_manifests': record['manifests'],
                          'ios_manifest_archive_sha256': manifest_sha256, **proof,
                          'transform': 'FMASZ1 + zlib.compress(stored, 6)',
                          'stored_bytes_edited': False, 'zip_crc_verified': True,
                          'zlib_runtime_version': zlib.ZLIB_RUNTIME_VERSION,
                          'cache_modified': False, 'device_tested': False}
            output = destination.joinpath(*PurePosixPath(path).parts)
            sidecar = output.with_name(output.name + '.provenance.json')
            if not output.resolve().is_relative_to(destination):
                raise ValueError('Atlas output left the intended directory')
            if output.exists() or sidecar.exists():
                if (output.is_file() and not output.is_symlink() and sidecar.is_file()
                        and not sidecar.is_symlink()
                        and output.read_bytes() == stored
                        and json.loads(sidecar.read_text(encoding='utf-8')) == provenance):
                    recovered.append({**provenance, 'already_verified_local': True})
                    continue
                raise FileExistsError('Refusing to overwrite an atlas or provenance record')
            output.parent.mkdir(parents=True, exist_ok=True)
            created = []
            try:
                with output.open('xb') as stream:
                    created.append(output)
                    stream.write(stored)
                with sidecar.open('x', encoding='utf-8') as stream:
                    created.append(sidecar)
                    json.dump(provenance, stream, indent=2)
                    stream.write('\n')
            except BaseException:
                for created_path in reversed(created):
                    try:
                        created_path.unlink(missing_ok=True)
                    except OSError:
                        pass  # Preserve the original write/close failure.
                raise
            recovered.append(provenance)
    return {**validation, 'recovered': recovered, 'range_bytes_read': source.transferred,
            'range_requests': source.requests, 'range_budget_bytes': MAX_TOTAL,
            'source_url': source.url, 'source_archive_bytes': source.size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ipa', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--recover', action='store_true')
    parser.add_argument('--output-directory', type=Path)
    args = parser.parse_args()
    allowed = (ROOT / 'investigation/recovered_assets/optional').resolve()
    if not args.report.resolve().is_relative_to(allowed):
        parser.error('Reports must stay under ignored investigation/recovered_assets/optional/')
    if args.recover and (args.output_directory is None
                        or not args.output_directory.resolve().is_relative_to(allowed)):
        parser.error('Recovery output must stay under ignored investigation/recovered_assets/optional/')
    if args.report.exists():
        raise FileExistsError('Refusing to overwrite an existing transport report')
    result = (recover_atlases(args.ipa, args.cache, args.output_directory) if args.recover
              else validate_existing(args.ipa, args.cache))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
