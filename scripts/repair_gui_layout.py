"""EXPERIMENTAL exact-resource repair for one malformed encrypted GUI style.

This verifies XML syntax only. It is not a demonstrated black-background fix.
An output IPA must be re-signed before installation; no signing identity is used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from build_4k_v3 import eds_crypt

RESOURCE_PATH = ('Payload/RealRacing3.app/res/gui/processed/limited_time_series/'
                 'gameonix_2020_mazda_mx5/LocalStyles.gui')
SUPPORTED_RESOURCE_SHA256 = '3af680491c7073f47271a4ed2efe1d23117d7b67bf2e4b205322cde4537c549a'
BROKEN_ELEMENT = b'<Colour name="lts_popup_backing_color" r="221" g="221" b="221"\r\n'
REPAIRED_ELEMENT = BROKEN_ELEMENT[:-2] + b'/>\r\n'


def repair_resource(encrypted):
    actual = hashlib.sha256(encrypted).hexdigest()
    if actual != SUPPORTED_RESOURCE_SHA256:
        raise ValueError('Unsupported, changed or already-repaired GUI resource; refusing to modify it')
    plaintext = eds_crypt(encrypted)
    if plaintext.count(BROKEN_ELEMENT) != 1:
        raise ValueError('Expected malformed Colour element was not found exactly once')
    try:
        ET.fromstring(plaintext)
    except ET.ParseError:
        pass
    else:
        raise ValueError('Resource is already valid XML; no repair is required')
    repaired = plaintext.replace(BROKEN_ELEMENT, REPAIRED_ELEMENT, 1)
    ET.fromstring(repaired)
    output = eds_crypt(repaired)
    if eds_crypt(output) != repaired:
        raise ValueError('Encrypted GUI round-trip check failed')
    return output


def repair_ipa(source, destination):
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('Output IPA must not overwrite the input IPA')
    if destination.exists():
        raise FileExistsError('Output IPA already exists')
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
        if names.count(RESOURCE_PATH) != 1:
            raise ValueError('Expected exactly one supported GUI resource in the IPA')
        before = archive.read(RESOURCE_PATH)
        after = repair_resource(before)
        with zipfile.ZipFile(destination, 'x') as output:
            output.comment = archive.comment
            for item in archive.infolist():
                output.writestr(item, after if item.filename == RESOURCE_PATH else archive.read(item))
    return {'experimental': True, 'resource': RESOURCE_PATH,
            'input_resource_sha256': hashlib.sha256(before).hexdigest(),
            'output_resource_sha256': hashlib.sha256(after).hexdigest(),
            'plaintext_bytes_inserted': len(after) - len(before),
            'xml_syntax_verified': True, 'runtime_visual_effect_verified': False,
            'requires_user_resigning': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experimental', action='store_true', help='Acknowledge that runtime behavior is unverified')
    parser.add_argument('source_ipa', type=Path)
    parser.add_argument('output_ipa', type=Path)
    args = parser.parse_args()
    if not args.experimental:
        parser.error('This unvalidated resource repair requires --experimental')
    try:
        result = repair_ipa(args.source_ipa, args.output_ipa)
    except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f'Repair refused: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
