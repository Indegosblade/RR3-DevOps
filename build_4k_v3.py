"""
RR3 DevOps production builder for the researched final iOS binary.

Usage: python build_4k_v3.py <original.ipa> [output.ipa]
  eds_god.plist must be in the same directory as this script.

Before changing anything, the builder verifies the main executable's Mach-O
UUID and the original bytes at every patch location. Re-signed or repackaged
copies remain usable; a different executable is refused.
"""
import hashlib
import os
import struct
import sys
import time
import zipfile

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BINARY_PATH = 'Payload/RealRacing3.app/RealRacing3'
EDS_DIR = 'Payload/RealRacing3.app/res/eds/'
EDS_NEW_DEVICE = EDS_DIR + 'iPhone18,1.plist'
EDS_FALLBACK = EDS_DIR + 'iPhone.plist'

# LC_UUID for the final iOS executable researched by this project. This is a
# build identity, not a signing or bundle-identifier check.
SUPPORTED_MACHO_UUID = bytes.fromhex('06ed5b50c44c3b69a5840701b8a88451')

# EDS modified-RC4 key (recovered from 0x1007262a8).
EDS_KEY = bytes([0xa5, 0x35, 0xb3, 0xb1, 0xe8, 0x43, 0xe7, 0xcf])


def eds_crypt(data):
    """Modified RC4: post-KSA scramble over S[1..133], PRGA starts at i=133."""
    state = list(range(256))
    j = 0
    for i in range(256):
        j = (j + state[i] + EDS_KEY[i % 8]) & 0xFF
        state[i], state[j] = state[j], state[i]
    j2 = 0
    for buf_idx in range(3, 0x88):
        state_index = buf_idx - 2
        j2 = (j2 + state[state_index]) & 0xFF
        state[state_index], state[j2] = state[j2], state[state_index]
    i = 0x85
    j3 = j2
    out = bytearray(len(data))
    for n in range(len(data)):
        i = (i + 1) & 0xFF
        j3 = (j3 + state[i]) & 0xFF
        state[i], state[j3] = state[j3], state[i]
        out[n] = data[n] ^ state[(state[i] + state[j3]) & 0xFF]
    return bytes(out)


def make_stub(imm):
    return struct.pack('<IIII',
        0x52800000 | (imm << 5), 0xD65F03C0, 0xD503201F, 0xD503201F)


def url_rewrite(original_url):
    replacement = b'http://127.0.0.1/'
    if len(replacement) > len(original_url):
        raise ValueError('replacement URL is longer than the original')
    return replacement + b'\x00' * (len(original_url) - len(replacement))


RET_NO = make_stub(0)
RET_120 = make_stub(120)
RET_NIL = struct.pack('<IIII', 0xD2800000, 0xD65F03C0, 0xD503201F, 0xD503201F)

# (file offset, expected original bytes, replacement bytes, description)
PATCHES = [
    (0x022CB460, bytes.fromhex('417200f0212041f9504400f010f244f9'), RET_NO, 'isAdReady -> NO'),
    (0x022D0120, bytes.fromhex('217200f021b842f9304400d010f244f9'), RET_NO, 'isRewardedVideoReady -> NO'),
    (0x022CE4A0, bytes.fromhex('41720090212847f95044009010f244f9'), RET_NO, 'isInterstitialReady -> NO'),
    (0x022812E0, bytes.fromhex('017400d021f044f9b04600b010f244f9'), RET_NO, 'adMobEnabled -> NO'),
    (0x02292440, bytes.fromhex('a17300b0211c47f93046009010f244f9'), RET_NO, 'checksumEnabled -> NO'),
    (0x022F6560, bytes.fromhex('417100d0214447f91043009010f244f9'), RET_NIL, 'requestReview -> nil'),
    (0x022DACE0, bytes.fromhex('01720090213440f9f043009010f244f9'), RET_120, 'maxFPS -> 120'),
    (0x026F5B86, b'https://director-int.sn.eamobile.com', url_rewrite(b'https://director-int.sn.eamobile.com'), 'URL: director-int'),
    (0x026F5BAB, b'https://director-stage.sn.eamobile.com', url_rewrite(b'https://director-stage.sn.eamobile.com'), 'URL: director-stage'),
    (0x026F5BD2, b'https://syn-dir.sn.eamobile.com', url_rewrite(b'https://syn-dir.sn.eamobile.com'), 'URL: syn-dir'),
    (0x026CB1A2, b'https://prod.geo.gluops.com/geoservice/v2/publishdetailed', url_rewrite(b'https://prod.geo.gluops.com/geoservice/v2/publishdetailed'), 'URL: geoservice'),
    (0x026E787D, b'https://prod-rest.ccs.gluops.com/api/v1/putData', url_rewrite(b'https://prod-rest.ccs.gluops.com/api/v1/putData'), 'URL: ccs putData'),
    (0x02743860, b'http://firemonkeys.com.au/news/embednews/index.php?nGameId=', url_rewrite(b'http://firemonkeys.com.au/news/embednews/index.php?nGameId='), 'URL: firemonkeys news'),
]


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def macho_uuid(binary):
    if len(binary) < 32 or struct.unpack_from('<I', binary, 0)[0] != 0xFEEDFACF:
        raise ValueError('main executable is not a 64-bit little-endian Mach-O')
    ncmds = struct.unpack_from('<I', binary, 16)[0]
    command_end = 32 + struct.unpack_from('<I', binary, 20)[0]
    if command_end > len(binary):
        raise ValueError('Mach-O load commands extend beyond the executable')

    offset = 32
    for _ in range(ncmds):
        if offset + 8 > command_end:
            raise ValueError('truncated Mach-O load command')
        command, command_size = struct.unpack_from('<II', binary, offset)
        if command_size < 8 or offset + command_size > command_end:
            raise ValueError('invalid Mach-O load-command size')
        if command == 0x1B:
            if command_size < 24:
                raise ValueError('truncated LC_UUID command')
            return binary[offset + 8:offset + 24]
        offset += command_size
    raise ValueError('main executable has no LC_UUID command')


def validate_binary(binary):
    actual_uuid = macho_uuid(binary)
    if actual_uuid != SUPPORTED_MACHO_UUID:
        raise ValueError(
            'unsupported main executable UUID: '
            f'{actual_uuid.hex()} (expected {SUPPORTED_MACHO_UUID.hex()})')

    for offset, expected, _replacement, description in PATCHES:
        end = offset + len(expected)
        if end > len(binary):
            raise ValueError(f'{description}: offset 0x{offset:x} is outside the executable')
        actual = binary[offset:end]
        if actual != expected:
            raise ValueError(
                f'{description}: original bytes do not match at 0x{offset:x}; '
                'refusing to patch an unsupported or already-modified executable')


def load_source_ipa(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f'input IPA not found: {path}')
    try:
        with zipfile.ZipFile(path, 'r') as source:
            items = source.infolist()
            cache = {item.filename: source.read(item.filename) for item in items}
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError(f'cannot read input IPA: {exc}') from exc

    missing = [name for name in (BINARY_PATH, EDS_FALLBACK) if name not in cache]
    if missing:
        raise ValueError(f'input IPA is missing required path(s): {", ".join(missing)}')
    validate_binary(cache[BINARY_PATH])
    return items, cache


def build(source_ipa, output_ipa, god_plist_path):
    if os.path.abspath(source_ipa) == os.path.abspath(output_ipa):
        raise ValueError('output IPA must not overwrite the input IPA')
    if os.path.exists(output_ipa):
        raise FileExistsError(f'output already exists: {output_ipa}')
    if not os.path.isfile(god_plist_path):
        raise FileNotFoundError(f'EDS profile not found: {god_plist_path}')

    items, file_cache = load_source_ipa(source_ipa)
    with open(god_plist_path, 'rb') as profile:
        god_plist_plain = profile.read()
    god_plist_enc = eds_crypt(god_plist_plain)
    if eds_crypt(god_plist_enc) != god_plist_plain:
        raise RuntimeError('EDS round-trip verification failed')

    binary_data = bytearray(file_cache[BINARY_PATH])
    print(f'Building {output_ipa}')
    print(f'  Input IPA SHA-256: {file_sha256(source_ipa)}')
    print(f'  Verified final-build UUID: {SUPPORTED_MACHO_UUID.hex()}')
    print(f'  {len(PATCHES)} expected-byte-checked operations (zero debug patches)')

    for offset, _expected, replacement, description in PATCHES:
        binary_data[offset:offset + len(replacement)] = replacement
        print(f'  [0x{offset:08x}] {description}')

    print(f'  EDS: {len(god_plist_plain)} plaintext bytes -> {len(god_plist_enc)} encrypted bytes')
    added_new_device = EDS_NEW_DEVICE in file_cache
    with zipfile.ZipFile(output_ipa, 'x', zipfile.ZIP_DEFLATED) as output:
        for item in items:
            if item.filename == BINARY_PATH:
                output.writestr(item, bytes(binary_data))
            elif item.filename in (EDS_FALLBACK, EDS_NEW_DEVICE):
                output.writestr(item, god_plist_enc)
            else:
                output.writestr(item, file_cache[item.filename])
        if not added_new_device:
            new_item = zipfile.ZipInfo(EDS_NEW_DEVICE)
            new_item.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(new_item, god_plist_enc)

    print(f'Done: {output_ipa}')
    print(f'Size: {os.path.getsize(output_ipa) / (1024 * 1024):.1f} MB')
    print('Production builder completed: verified final build, 13 safe-direction operations, encrypted EDS profile.')


def main(argv):
    if len(argv) not in (2, 3):
        print(f'Usage: {argv[0]} <original.ipa> [output.ipa]')
        return 1
    source_ipa = argv[1]
    output_ipa = argv[2] if len(argv) == 3 else 'RR3-DevOps-v1.0-Production-Quality.ipa'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    start = time.time()
    try:
        build(source_ipa, output_ipa, os.path.join(script_dir, 'eds_god.plist'))
    except (FileExistsError, FileNotFoundError, ValueError, OSError, zipfile.BadZipFile) as exc:
        print(f'Build refused: {exc}', file=sys.stderr)
        return 1
    print(f'Elapsed: {time.time() - start:.1f}s')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
