"""Apply only the inherited-importer repair and English translation to an IPA.

The output needs re-signing. No game executable, save, cache, provisioning
profile or signing identity is created or edited by this helper.
"""
import argparse
import json
from pathlib import Path
import plistlib
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from importer_fix.patch import LIBRARY_PATH, patch_dylib, validate_config
from build_4k_v3 import BINARY_PATH, SUPPORTED_MACHO_UUID, macho_uuid

INFO_PATH = 'Payload/RealRacing3.app/Info.plist'


def repair(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError('Output must not overwrite input')
    if destination.exists():
        raise FileExistsError('Output already exists')
    owned = None
    try:
        with zipfile.ZipFile(source) as archive:
            items = archive.infolist()
            if len({item.filename for item in items}) != len(items):
                raise ValueError('Duplicate ZIP members are unsupported')
            if macho_uuid(archive.read(BINARY_PATH)) != SUPPORTED_MACHO_UUID:
                raise ValueError('Expected the researched final RR3 executable')
            validate_config(plistlib.loads(archive.read(INFO_PATH)))
            changed, report = patch_dylib(archive.read(LIBRARY_PATH))
            with destination.open('xb') as stream:
                stat = destination.stat()
                owned = stat.st_dev, stat.st_ino
                with zipfile.ZipFile(stream, 'w') as output:
                    for item in items:
                        output.writestr(item, changed if item.filename == LIBRARY_PATH else archive.read(item))
        return report
    except BaseException as error:
        if owned is not None:
            try:
                stat = destination.stat()
                if (stat.st_dev, stat.st_ino) == owned:
                    destination.unlink()
            except FileNotFoundError:
                pass
            except OSError as cleanup_error:
                error.add_note('Partial output cleanup failed: ' + str(cleanup_error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    report = repair(args.source, args.destination)
    print(json.dumps({'importer': report, 'requires_resigning': True}, indent=2))


if __name__ == '__main__':
    main()
