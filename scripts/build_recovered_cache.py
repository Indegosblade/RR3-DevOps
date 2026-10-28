"""Build a separate candidate from seven exact original recovered resources.

The Hybrid Highway manifest, original cache and each recovered representation
are guarded. A new archive adds six authentic transport-hash receipts while
preserving all original receipt bytes/header; no original input is edited.
Runtime import, registration and event behavior still need validation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.restore_speedrush_cache import CACHE_MEMBER, append_verified_assets, verified_movie
from scripts.trace_asset_transport import TARGET_ROOT, verify_stored

MANIFEST_PATH = 'Payload/RealRacing3.app/res/asset_list_quest_hybrid_highway_assets.txt'
MANIFEST_SHA256 = '93b0a2d0abe7b308ff36ba385db597fe126ef747be2d237cbd83190f986fdc4f'
TARGETS = {TARGET_ROOT + folder + filename for folder in ('', 'splash/', 'large/')
           for filename in ('sprites.ios.atlas', 'sprites_0.rgb.pvr.z')}


def recovered_resources(ipa_path, movie, asset_root):
    with zipfile.ZipFile(ipa_path) as archive:
        if archive.namelist().count(MANIFEST_PATH) != 1:
            raise ValueError('Expected one original Hybrid Highway manifest')
        manifest = archive.read(MANIFEST_PATH)
    if hashlib.sha256(manifest).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Hybrid Highway manifest differs from the preserved original')
    records = {}
    for line in manifest.decode('utf-8').splitlines():
        fields = line.rsplit(None, 3)
        if len(fields) != 4 or fields[0].lstrip('/') not in TARGETS:
            continue
        path = fields[0].lstrip('/')
        if path in records:
            raise ValueError('Duplicate target representation in manifest')
        records[path] = {'md5': fields[1], 'transport_bytes': int(fields[2]), 'stored_bytes': int(fields[3])}
    if set(records) != TARGETS:
        raise ValueError('Expected all six high-resolution GUI manifest entries')
    asset_root = Path(asset_root).resolve()
    additions, evidence = {CACHE_MEMBER: verified_movie(movie)}, []
    for path in sorted(records):
        candidate = asset_root.joinpath(*path.split('/'))
        if not candidate.resolve().is_relative_to(asset_root):
            raise ValueError('Recovered resource left the intended asset directory')
        expected = records[path]
        if candidate.stat().st_size != expected['stored_bytes'] or expected['stored_bytes'] > 16 * 1024**2:
            raise ValueError('Recovered resource size differs from manifest')
        data = candidate.read_bytes()
        if path.endswith('.ios.atlas'):
            proof = verify_stored(data, expected)
        else:
            if expected['transport_bytes'] != expected['stored_bytes'] or hashlib.md5(data).hexdigest() != expected['md5']:
                raise ValueError('Recovered texture differs from the original manifest representation')
            proof = {'stored_bytes': len(data), 'transport_md5': expected['md5'],
                     'exact_ios_manifest_representation': True}
        additions['Caches/' + path] = data
        evidence.append(dict(path=path, **proof))
    return additions, evidence


def build(ipa_path, source_cache, movie, asset_root, destination):
    destination = Path(destination)
    if destination.exists() or destination.resolve() in (Path(ipa_path).resolve(), Path(movie).resolve()):
        raise FileExistsError('Output must be a new path distinct from all inputs')
    additions, evidence = recovered_resources(ipa_path, movie, asset_root)
    receipts = {item['path']: item['transport_md5'] for item in evidence}
    result = append_verified_assets(source_cache, destination, additions, receipts=receipts)
    result.update(hybrid_gui_manifest_sha256=MANIFEST_SHA256,
                  recovered_gui_resources=evidence,
                  declared_hd_gui_group_members_present=6,
                  matching_transport_receipts_added=len(result['new_receipt_paths']),
                  runtime_cache_registration_verified=False,
                  complete_event_or_black_background_fix_verified=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ipa', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--movie', type=Path, required=True)
    parser.add_argument('--asset-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.ipa, args.cache, args.movie, args.asset_root, args.output), indent=2))


if __name__ == '__main__':
    main()
