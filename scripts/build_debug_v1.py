"""
Build rr3_debug_v1.ipa: all existing 18 patches + NOP all debug gates.
Forces debug overlay/cheat menus ON regardless of boolean state.
Gate locations given as ADRP VAs — script auto-finds the conditional branch.
"""
import zipfile, struct, os, sys, time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ORIG_IPA = r'C:\Users\Kevin\Desktop\RR3_teardown\959112d6ace07153840144be3201b00f39ec0e91.ipa'
OUT_IPA = r'C:\Users\Kevin\Desktop\RR3_teardown\rr3_debug_v1.ipa'

BINARY_PATH = 'Payload/RealRacing3.app/RealRacing3'
EDS_DIR = 'Payload/RealRacing3.app/res/eds/'
EDS_BEST = EDS_DIR + 'iPad6,8.plist'
EDS_NEW_DEVICE = EDS_DIR + 'iPhone18,1.plist'
EDS_FALLBACK = EDS_DIR + 'iPhone.plist'

NOP = struct.pack('<I', 0xD503201F)

def make_stub(imm):
    return struct.pack('<IIII',
        0x52800000 | (imm << 5), 0xD65F03C0, 0xD503201F, 0xD503201F)

RET_YES  = make_stub(1)
RET_NO   = make_stub(0)
RET_120  = make_stub(120)
RET_NIL  = struct.pack('<IIII', 0xD2800000, 0xD65F03C0, 0xD503201F, 0xD503201F)

def url_rewrite(original_url):
    replacement = b'http://127.0.0.1/'
    return replacement + b'\x00' * (len(original_url) - len(replacement))

# Original 18 patches (from working rr3_4k_v2.ipa)
BASE_PATCHES = [
    (0x022CB460, RET_NO,  'isAdReady -> NO'),
    (0x022D0120, RET_NO,  'isRewardedVideoReady -> NO'),
    (0x022CE4A0, RET_NO,  'isInterstitialReady -> NO'),
    (0x02292440, RET_NO,  'checksumEnabled -> NO'),
    (0x022812E0, RET_NO,  'adMobEnabled -> NO'),
    (0x022F6560, RET_NIL, 'requestReview -> nil'),
    (0x026F5B86, url_rewrite(b'https://director-int.sn.eamobile.com'),        'URL: director-int'),
    (0x026F5BAB, url_rewrite(b'https://director-stage.sn.eamobile.com'),      'URL: director-stage'),
    (0x026F5BD2, url_rewrite(b'https://syn-dir.sn.eamobile.com'),             'URL: syn-dir'),
    (0x026CB1A2, url_rewrite(b'https://prod.geo.gluops.com/geoservice/v2/publishdetailed'), 'URL: geoservice'),
    (0x026E787D, url_rewrite(b'https://prod-rest.ccs.gluops.com/api/v1/putData'),           'URL: ccs putData'),
    (0x02743860, url_rewrite(b'http://firemonkeys.com.au/news/embednews/index.php?nGameId='), 'URL: firemonkeys news'),
    (0x022CCAA0, RET_YES, 'isDebugModeEnabled -> YES'),
    (0x022CE3E0, RET_YES, 'isInternalTestMode -> YES'),
    (0x022CB9C0, RET_YES, 'isAppDebuggable -> YES'),
    (0x01267420, NOP,     'debugMode CBZ -> NOP'),
    (0x024F6480, b'PRIVATE\x00', 'BuildType -> PRIVATE'),
    (0x022DACE0, RET_120, 'maxFPS -> 120'),
]

# Load binary and parse segments
with zipfile.ZipFile(ORIG_IPA, 'r') as z:
    raw_binary = z.read(BINARY_PATH)

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

def va_to_file(va):
    for seg in segments.values():
        if seg['vmaddr'] <= va < seg['vmaddr'] + seg['vmsize']:
            return va - seg['vmaddr'] + seg['fileoff']
    return None

def is_cond_branch(insn):
    """Check if instruction is B.cond, CBZ, CBNZ, TBZ, or TBNZ"""
    if (insn & 0xFF000000) == 0x54000000: return 'B.cond'
    if (insn & 0x7E000000) == 0x34000000:
        return 'CBNZ' if (insn >> 24) & 1 else 'CBZ'
    if (insn & 0x7E000000) == 0x36000000:
        return 'TBNZ' if (insn >> 24) & 1 else 'TBZ'
    return None

def branch_skip_size(insn):
    """Get the number of bytes skipped by a conditional branch"""
    kind = is_cond_branch(insn)
    if not kind: return 0
    if kind in ('B.cond',):
        imm19 = (insn >> 5) & 0x7FFFF
        if imm19 & 0x40000: imm19 -= 0x80000
        return abs(imm19 * 4)
    elif kind in ('CBZ', 'CBNZ'):
        imm19 = (insn >> 5) & 0x7FFFF
        if imm19 & 0x40000: imm19 -= 0x80000
        return abs(imm19 * 4)
    elif kind in ('TBZ', 'TBNZ'):
        imm14 = (insn >> 5) & 0x3FFF
        if imm14 & 0x2000: imm14 -= 0x4000
        return abs(imm14 * 4)
    return 0

# Gate locations: (ADRP VA, var VA, description)
# Script will scan forward from ADRP to find the conditional branch
GATE_ADRP_LOCATIONS = [
    # var 0x10324f910 — strongest ImGui candidate (6 gates, up to 512B skip)
    (0x100210fec, 0x10324f910, 'var910 gate1'),
    (0x1002120a4, 0x10324f910, 'var910 gate2'),
    (0x100213754, 0x10324f910, 'var910 gate3'),
    (0x100775730, 0x10324f910, 'var910 gate4'),
    (0x1007763b8, 0x10324f910, 'var910 gate5'),
    (0x100955ef0, 0x10324f910, 'var910 gate6'),

    # var 0x10324f9d0 — MainMenuCheats.cpp context
    (0x10015e784, 0x10324f9d0, 'var9d0 gate1'),
    (0x10015e960, 0x10324f9d0, 'var9d0 gate2'),

    # var 0x10324f640 — 2 gates (112B + 416B skip)
    (0x100088fe4, 0x10324f640, 'var640 gate1'),

    # var 0x10324f9b0 — 1 gate (64B skip)
    # var 0x10324f9f0 — 1 gate (160B skip)
    # var 0x10324f648 — MainMenuCheatScreen (2 gates)
    (0x10009a330, 0x10324f648, 'var648 gate1'),
]

print(f"Building {OUT_IPA}")
print(f"  {len(BASE_PATCHES)} base patches")
print(f"  {len(GATE_ADRP_LOCATIONS)} gate locations to scan")

t0 = time.time()

with zipfile.ZipFile(ORIG_IPA, 'r') as zin:
    all_items = zin.infolist()
    file_cache = {}
    for item in all_items:
        file_cache[item.filename] = zin.read(item.filename)

binary_data = bytearray(file_cache[BINARY_PATH])
best_plist = file_cache[EDS_BEST]

# Apply base patches
print(f"\nBase patches:")
for off, patch, desc in BASE_PATCHES:
    binary_data[off:off+len(patch)] = patch
    print(f"  [{off:#010x}] {desc}")

# Apply gate NOP patches: scan forward from each ADRP to find the conditional branch
print(f"\nGate NOP patches (auto-detected from ADRP):")
gate_count = 0
for adrp_va, var_va, desc in GATE_ADRP_LOCATIONS:
    adrp_foff = va_to_file(adrp_va)
    if adrp_foff is None:
        print(f"  SKIP {desc} — ADRP VA 0x{adrp_va:x} not mappable!")
        continue

    # Scan up to 8 instructions forward from ADRP to find conditional branch
    found = False
    for j in range(1, 9):
        check_foff = adrp_foff + j * 4
        if check_foff + 4 > len(binary_data):
            break
        insn = struct.unpack_from('<I', binary_data, check_foff)[0]
        kind = is_cond_branch(insn)
        if kind:
            skip = branch_skip_size(insn)
            check_va = adrp_va + j * 4
            print(f"  [{check_foff:#010x}] {desc}: {kind} skip {skip}B (was 0x{insn:08x}) -> NOP")
            binary_data[check_foff:check_foff+4] = NOP
            gate_count += 1
            found = True
            break

    if not found:
        # Try deeper: sometimes there's more setup between ADRP and branch
        print(f"  WARN {desc} — no conditional branch found in 8 insns after ADRP 0x{adrp_va:x}")
        # Dump what we see
        for j in range(8):
            check_foff = adrp_foff + j * 4
            insn = struct.unpack_from('<I', binary_data, check_foff)[0]
            print(f"    +{j}: 0x{insn:08x}")

# Build output IPA
print(f"\nApplied {gate_count} gate NOPs")
print(f"Writing IPA...")
added_device = False
with zipfile.ZipFile(OUT_IPA, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in all_items:
        if item.filename == BINARY_PATH:
            zout.writestr(item, bytes(binary_data))
        elif item.filename == EDS_FALLBACK:
            zout.writestr(item, best_plist)
        else:
            zout.writestr(item, file_cache[item.filename])

        if item.filename.startswith(EDS_DIR) and item.filename.endswith('.plist') and not added_device:
            if EDS_NEW_DEVICE not in file_cache:
                new_info = zipfile.ZipInfo(EDS_NEW_DEVICE)
                new_info.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(new_info, best_plist)
                added_device = True

size_mb = os.path.getsize(OUT_IPA) / (1024*1024)
elapsed = time.time() - t0
print(f"\nDone: {OUT_IPA}")
print(f"Size: {size_mb:.1f} MB, Time: {elapsed:.1f}s")
print(f"Total patches: {len(BASE_PATCHES)} base + {gate_count} gates = {len(BASE_PATCHES) + gate_count}")
