"""Build profile-free, ad-hoc v1.2 release IPAs using Python and zsign.

No certificate, private key, Apple account or device connection is accepted.
Run from the repository with the unmodified researched source IPA.
"""
import argparse
import json
from pathlib import Path
import plistlib
import stat
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_4k_v3 as builder
from scripts.audit_release import audit_archive
from scripts.validate_url_literals import inspect_literals


def package(source, destination, signer, work, compatible):
    payload = work / 'extracted'
    with zipfile.ZipFile(source) as archive:
        items = archive.infolist()
        if any(stat.S_ISLNK(item.external_attr >> 16) for item in items):
            raise ValueError('Symbolic-link archive requires explicit preservation')
        archive.extractall(payload)
    stripped = []
    for path in payload.rglob('*'):
        if path.is_file() and path.name.lower().endswith(('.mobileprovision', '.provisionprofile', '.xcent')):
            stripped.append(path.relative_to(payload).as_posix())
            path.unlink()
    licenses = payload / 'Payload' / 'RealRacing3.app' / 'RR3DevOps-Licenses'
    licenses.mkdir(exist_ok=True)
    (licenses / 'RR3-DevOps-MIT.txt').write_bytes((ROOT / 'LICENSE').read_bytes())
    if compatible:
        (licenses / 'hefti-MIT.txt').write_bytes((ROOT / 'third_party' / 'hefti' / 'LICENSE').read_bytes())
    empty = work / 'empty-entitlements.plist'
    empty.write_bytes(plistlib.dumps({}))
    command = [str(signer), '-a', '-R', '-e', str(empty), '-f',
               '-t', str(work), str(payload / 'Payload' / 'RealRacing3.app')]
    result = subprocess.run(command, cwd=work, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (work / 'adhoc-signing.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError('Ad-hoc signing failed: ' + (result.stdout + result.stderr)[-3000:])
    original_names = {item.filename for item in items}
    with zipfile.ZipFile(destination, 'x') as output:
        for item in items:
            path = payload / item.filename
            if item.is_dir():
                output.writestr(item, b'')
            elif path.is_file():
                output.writestr(item, path.read_bytes())
        for path in sorted((payload / 'Payload').rglob('*')):
            name = path.relative_to(payload).as_posix()
            if path.is_file() and name not in original_names and not any(part.startswith('.zsign') for part in path.parts):
                info = zipfile.ZipInfo(name)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                output.writestr(info, path.read_bytes())
    return stripped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--zsign', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'release-dist' / 'importer-v1.2')
    parser.add_argument('--deny-markers', type=Path, help='Local-only JSON marker array for the privacy audit')
    args = parser.parse_args()
    source = args.input.resolve()
    signer = args.zsign.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    markers = json.loads(args.deny_markers.read_text()) if args.deny_markers else []
    records = []
    for mode, compatible in (('Production-Quality', False), ('SE-Compatibility', True)):
        name = f'RR3-DevOps-v1.2-{mode}.ipa'
        destination = output / name
        if destination.exists():
            raise FileExistsError(f'Refusing to overwrite {destination}')
        with tempfile.TemporaryDirectory(prefix='rr3-release-', dir=output) as temporary:
            work = Path(temporary)
            intermediate = work / 'patched.ipa'
            candidate = work / name
            builder.build(str(source), str(intermediate), str(ROOT / 'eds_god.plist'), se_compat=compatible)
            stripped = package(intermediate, candidate, signer, work, compatible)
            with zipfile.ZipFile(candidate) as archive:
                records_url = inspect_literals(archive.read(builder.BINARY_PATH))
            if len(records_url) != 5 or not all(record['valid'] for record in records_url):
                raise ValueError('Release contains an invalid shortened URL literal')
            audit = audit_archive(candidate, markers)
            candidate.rename(destination)
        audit.update(mode=mode, binary_operations=20 if compatible else 18,
                     source_ipa_sha256=builder.file_sha256(source),
                     stripped_provisioning_files=len(stripped))
        records.append(audit)
        print(json.dumps(audit), flush=True)
    (output / 'RELEASE_AUDIT.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
    (output / 'SHA256SUMS.txt').write_text(''.join(f'{record["sha256"]} *{record["asset"]}\n' for record in records), encoding='utf-8')


if __name__ == '__main__':
    main()
