"""Audit a re-sign-required release IPA without needing a signing identity."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import struct
import zipfile

PRIVATE_KEY_BLOCK = re.compile(
    rb'-----BEGIN ((?:[A-Z]+ )?PRIVATE KEY)-----\r?\n'
    rb'(?:[A-Za-z0-9+/=]{16,80}\r?\n){2,}-----END \1-----'
)
FORBIDDEN_SUFFIXES = ('.mobileprovision', '.provisionprofile', '.p12', '.pfx', '.key', '.ips', '.crash', '.log', '.xcent')


def slices(data):
    magic = data[:4]
    if magic in (b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe'):
        return [data]
    if magic in (b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf'):
        if len(data) < 8:
            raise ValueError('Truncated universal Mach-O')
        count = struct.unpack_from('>I', data, 4)[0]
        stride = 32 if magic[-1] == 0xBF else 20
        result = []
        if count > 32 or 8 + count * stride > len(data):
            raise ValueError('Invalid universal Mach-O table')
        for index in range(count):
            position = 8 + index * stride
            if stride == 32:
                _, _, offset, size, _, _ = struct.unpack_from('>IIQQII', data, position)
            else:
                _, _, offset, size, _ = struct.unpack_from('>IIIII', data, position)
            if offset + size > len(data):
                raise ValueError('Truncated universal Mach-O slice')
            result.append(data[offset:offset + size])
        return result
    return []


def audit_macho(binary):
    header_size = 32 if binary[:4] == b'\xcf\xfa\xed\xfe' else 28
    if len(binary) < header_size:
        raise ValueError('Truncated Mach-O')
    position = header_size
    end = position + struct.unpack_from('<I', binary, 20)[0]
    signature = None
    for _ in range(struct.unpack_from('<I', binary, 16)[0]):
        if position + 8 > min(end, len(binary)):
            raise ValueError('Truncated load command')
        command, size = struct.unpack_from('<II', binary, position)
        if size < 8 or position + size > min(end, len(binary)):
            raise ValueError('Invalid load command')
        if command == 0x1D:
            signature = struct.unpack_from('<II', binary, position + 8)
        position += size
    if not signature:
        raise ValueError('Release Mach-O has no ad-hoc signature')
    offset, size = signature
    if offset + size > len(binary) or size < 12:
        raise ValueError('Invalid signature bounds')
    magic, length, count = struct.unpack_from('>III', binary, offset)
    if magic != 0xFADE0CC0 or length > size or 12 + count * 8 > length:
        raise ValueError('Invalid signature superblob')
    directories = 0
    for index in range(count):
        slot, relative = struct.unpack_from('>II', binary, offset + 12 + index * 8)
        if relative + 8 > length:
            raise ValueError('Invalid signature child')
        start = offset + relative
        kind, child_size = struct.unpack_from('>II', binary, start)
        if child_size < 8 or relative + child_size > length:
            raise ValueError('Invalid signature child bounds')
        if slot == 0x10000 and child_size > 8:
            raise ValueError('Release contains a CMS signing identity')
        if kind == 0xFADE0C02:
            directories += 1
            if child_size < 44:
                raise ValueError('Truncated CodeDirectory')
            version, flags, hash_offset, identifier, special, pages, code_limit = struct.unpack_from('>7I', binary, start + 8)
            if not flags & 2:
                raise ValueError('Release signature is not ad-hoc')
            if version >= 0x20200 and child_size >= 52 and struct.unpack_from('>I', binary, start + 48)[0]:
                raise ValueError('Release CodeDirectory contains a team identifier')
            hash_size, hash_type, platform, page_shift = struct.unpack_from('4B', binary, start + 36)
            algorithms = {1: hashlib.sha1, 2: hashlib.sha256, 3: hashlib.sha256, 4: hashlib.sha384}
            if hash_type not in algorithms or page_shift > 20:
                raise ValueError('Unsupported code-page hash format')
            page_size = 1 << page_shift
            if code_limit > offset or pages != (code_limit + page_size - 1) // page_size:
                raise ValueError('Invalid signed code-page extent')
            if hash_offset + pages * hash_size > child_size:
                raise ValueError('Truncated code-page hashes')
            for page in range(pages):
                expected = binary[start + hash_offset + page * hash_size:start + hash_offset + (page + 1) * hash_size]
                actual = algorithms[hash_type](binary[page * page_size:min((page + 1) * page_size, code_limit)]).digest()[:hash_size]
                if actual != expected:
                    raise ValueError('Code-page hash mismatch')
        if slot == 5:
            entitlements = plistlib.loads(binary[start + 8:start + child_size])
            if entitlements.get('com.apple.developer.team-identifier'):
                raise ValueError('Release entitlements contain a developer team')
    if not directories:
        raise ValueError('No ad-hoc CodeDirectory')
    return directories


def audit_archive(path, deny_markers=()):
    image_count = 0
    directory_count = 0
    entry_count = 0
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive entries')
        for item in archive.infolist():
            name = item.filename
            lower = name.lower()
            if lower.endswith(FORBIDDEN_SUFFIXES) or any(part.startswith('.zsign') for part in lower.split('/')):
                raise ValueError(f'Private/runtime file in release: {name}')
            if not name.startswith('Payload/') or '..' in name.split('/') or name.startswith('/'):
                raise ValueError(f'Unexpected archive path: {name}')
            if item.is_dir():
                continue
            entry_count += 1
            data = archive.read(item)
            # Crypto libraries contain PEM parser label strings. Reject a real
            # armored key block, not the label by itself in executable code.
            if PRIVATE_KEY_BLOCK.search(data):
                raise ValueError(f'Private-key material in release: {name}')
            for marker in deny_markers:
                if marker and (marker.encode() in data or marker.encode('utf-16le') in data):
                    raise ValueError(f'Private marker in release file: {name}')
            images = slices(data)
            image_count += len(images)
            for image in images:
                directory_count += audit_macho(image)
        if not image_count:
            raise ValueError('No audited Mach-O images')
        app = 'Payload/RealRacing3.app/'
        info = plistlib.loads(archive.read(app + 'Info.plist'))
        if info.get('iPASTORE WEB') != 'https://ipa.store' or app + 'ipa.store' not in names:
            raise ValueError('Required upstream startup metadata is missing')
        if any(name.startswith(app + prefix) for prefix in ('Documents/', 'Library/', 'tmp/') for name in names):
            raise ValueError('Runtime data directory in app bundle')
    with open(path, 'rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'asset': Path(path).name, 'sha256': checksum, 'bytes': Path(path).stat().st_size,
            'files': entry_count, 'mach_o_slices': image_count, 'code_directories_verified': directory_count,
            'provisioning_profiles': 0, 'cms_signing_identities': 0, 'private_marker_hits': 0,
            'requires_user_resigning': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa', type=Path)
    parser.add_argument('--deny-markers', type=Path, help='Optional LOCAL JSON array of private markers; never upload this file')
    args = parser.parse_args()
    markers = json.loads(args.deny_markers.read_text()) if args.deny_markers else []
    print(json.dumps(audit_archive(args.ipa, markers), indent=2))


if __name__ == '__main__':
    main()
