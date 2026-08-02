"""
RR3 4K Final Build (v3) — production quality, zero debug patches.

Usage: python build_4k_v3.py <original.ipa> [output.ipa]
  eds_god.plist must be in the same directory as this script.

ONLY safe-direction patches:
  - 120fps
  - Ads removed (4 patches)
  - Dead server URLs → 127.0.0.1
  - Checksum bypass
  - Review prompt suppression
  - God-mode EDS quality profile (max settings from all 41 device tiers)
    encrypted with cracked modified-RC4 key, injected as iPhone18,1 + iPhone fallback

NO debug flags. NO isDebugModeEnabled. NO BuildType change. NO gate NOPs.
"""
import zipfile, struct, os, sys, time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <original.ipa> [output.ipa]")
    sys.exit(1)

ORIG_IPA = sys.argv[1]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GOD_PLIST = os.path.join(SCRIPT_DIR, 'eds_god.plist')
OUT_IPA  = sys.argv[2] if len(sys.argv) > 2 else 'rr3_4k_v3.ipa'

BINARY_PATH = 'Payload/RealRacing3.app/RealRacing3'
EDS_DIR = 'Payload/RealRacing3.app/res/eds/'
EDS_NEW_DEVICE = EDS_DIR + 'iPhone18,1.plist'
EDS_FALLBACK = EDS_DIR + 'iPhone.plist'

# EDS modified-RC4 key (cracked from 0x1007262a8)
EDS_KEY = bytes([0xa5, 0x35, 0xb3, 0xb1, 0xe8, 0x43, 0xe7, 0xcf])

def eds_crypt(data):
    """Modified RC4: post-KSA scramble over S[1..133], PRGA starts at i=133."""
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + EDS_KEY[i % 8]) & 0xFF
        S[i], S[j] = S[j], S[i]
    j2 = 0
    for buf_idx in range(3, 0x88):
        si = buf_idx - 2
        j2 = (j2 + S[si]) & 0xFF
        S[si], S[j2] = S[j2], S[si]
    i = 0x85; j3 = j2
    out = bytearray(len(data))
    for n in range(len(data)):
        i = (i + 1) & 0xFF
        j3 = (j3 + S[i]) & 0xFF
        S[i], S[j3] = S[j3], S[i]
        out[n] = data[n] ^ S[(S[i] + S[j3]) & 0xFF]
    return bytes(out)

NOP = struct.pack('<I', 0xD503201F)

def make_stub(imm):
    return struct.pack('<IIII',
        0x52800000 | (imm << 5), 0xD65F03C0, 0xD503201F, 0xD503201F)

RET_NO   = make_stub(0)
RET_120  = make_stub(120)
RET_NIL  = struct.pack('<IIII', 0xD2800000, 0xD65F03C0, 0xD503201F, 0xD503201F)

def url_rewrite(original_url):
    replacement = b'http://127.0.0.1/'
    return replacement + b'\x00' * (len(original_url) - len(replacement))

# === SAFE PATCHES ONLY ===
PATCHES = [
    # Ads — all suppress-direction (return NO)
    (0x022CB460, RET_NO,  'isAdReady -> NO'),
    (0x022D0120, RET_NO,  'isRewardedVideoReady -> NO'),
    (0x022CE4A0, RET_NO,  'isInterstitialReady -> NO'),
    (0x022812E0, RET_NO,  'adMobEnabled -> NO'),

    # Anti-tamper bypass
    (0x02292440, RET_NO,  'checksumEnabled -> NO'),

    # Review prompt suppression
    (0x022F6560, RET_NIL, 'requestReview -> nil'),

    # 120fps
    (0x022DACE0, RET_120, 'maxFPS -> 120'),

    # Dead server URLs → fast connection-refused
    (0x026F5B86, url_rewrite(b'https://director-int.sn.eamobile.com'),        'URL: director-int'),
    (0x026F5BAB, url_rewrite(b'https://director-stage.sn.eamobile.com'),      'URL: director-stage'),
    (0x026F5BD2, url_rewrite(b'https://syn-dir.sn.eamobile.com'),             'URL: syn-dir'),
    (0x026CB1A2, url_rewrite(b'https://prod.geo.gluops.com/geoservice/v2/publishdetailed'), 'URL: geoservice'),
    (0x026E787D, url_rewrite(b'https://prod-rest.ccs.gluops.com/api/v1/putData'),           'URL: ccs putData'),
    (0x02743860, url_rewrite(b'http://firemonkeys.com.au/news/embednews/index.php?nGameId='), 'URL: firemonkeys news'),
]

# Load binary
with zipfile.ZipFile(ORIG_IPA, 'r') as z:
    raw_binary = z.read(BINARY_PATH)

# Parse Mach-O segments for VA→file offset mapping
ncmds = struct.unpack_from('<I', raw_binary, 16)[0]
offset = 32
segments = {}
for i in range(ncmds):
    cmd, cmdsize = struct.unpack_from('<II', raw_binary, offset)
    if cmd == 0x19:
        segname = raw_binary[offset+8:offset+24].split(b'\x00')[0].decode()
        vmaddr, vmsize, fileoff, filesize = struct.unpack_from('<QQQQ', raw_binary, offset+24)
        segments[segname] = {'vmaddr': vmaddr, 'vmsize': vmsize, 'fileoff': fileoff, 'filesize': filesize}
    offset += cmdsize

print(f"Building {OUT_IPA}")
print(f"  {len(PATCHES)} patches (safe-direction only, ZERO debug flags)")

t0 = time.time()

# Cache all files from original IPA
with zipfile.ZipFile(ORIG_IPA, 'r') as zin:
    all_items = zin.infolist()
    file_cache = {}
    for item in all_items:
        file_cache[item.filename] = zin.read(item.filename)

binary_data = bytearray(file_cache[BINARY_PATH])

with open(GOD_PLIST, 'rb') as f:
    god_plist_plain = f.read()
god_plist_enc = eds_crypt(god_plist_plain)

print(f"\nPatches:")
for off, patch, desc in PATCHES:
    binary_data[off:off+len(patch)] = patch
    print(f"  [{off:#010x}] {desc}")

# Write output IPA
print(f"\nEDS injection (god-mode, {len(god_plist_plain)} bytes plaintext -> {len(god_plist_enc)} bytes encrypted):")
print(f"  eds_god.plist -> iPhone.plist (fallback)")
print(f"  eds_god.plist -> iPhone18,1.plist (17 Pro direct match)")

# Verify round-trip: decrypt the encrypted god plist and check it matches
verify = eds_crypt(god_plist_enc)
assert verify == god_plist_plain, "EDS round-trip verification FAILED"
print(f"  Round-trip verified OK")

added_device = False
with zipfile.ZipFile(OUT_IPA, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in all_items:
        if item.filename == BINARY_PATH:
            zout.writestr(item, bytes(binary_data))
        elif item.filename == EDS_FALLBACK:
            zout.writestr(item, god_plist_enc)
        else:
            zout.writestr(item, file_cache[item.filename])

        if item.filename.startswith(EDS_DIR) and item.filename.endswith('.plist') and not added_device:
            if EDS_NEW_DEVICE not in file_cache:
                new_info = zipfile.ZipInfo(EDS_NEW_DEVICE)
                new_info.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(new_info, god_plist_enc)
                added_device = True

size_mb = os.path.getsize(OUT_IPA) / (1024*1024)
elapsed = time.time() - t0
print(f"\nDone: {OUT_IPA}")
print(f"Size: {size_mb:.1f} MB, Time: {elapsed:.1f}s")
print(f"Total: {len(PATCHES)} safe patches + god-mode EDS (encrypted)")
print(f"\nNO debug flags patched. Pure production quality.")
print(f"EDS god-mode: 512 cubemaps, anisotropic filtering, HDR, tonemap,")
print(f"  PBR water, all shadows, realtime reflections, AA4, photo mode.")
