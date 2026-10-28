"""Read-only receipt-ledger and group-admission trace for the preserved iOS build.

Reports catalog/receipt/payload boundaries without generating a cache ledger or
changing an IPA/cache. Synthetic host emulation covers one guarded decision
fragment, not full application execution or device event eligibility.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from build_4k_v3 import BINARY_PATH, SUPPORTED_MACHO_UUID, macho_uuid
from scripts.audit_sdk_dependencies import MachO
from scripts.trace_sdk_lifecycle import imported_symbol_at

LEDGER = 'Caches/asset_list_base.txtCache.txt'
GROUP = 'asset_list_quest_hybrid_highway_assets.txt'
GROUP_PREFIX = 'gui_assets/2048x1536/quests/hybrid_highway/'
CACHE_MAGIC, CACHE_VERSION = 0xA4F6F39D, 4
MAX_LEDGER_BYTES = 16 * 1024**2
REGIONS = {
    'load_cache_list': (0x1016C3564, 1544, '71df12ee9be3a72f82c24306e3008a7db3c8e2db2982d6913c8f1cc66ae421c4'),
    'save_cache_list': (0x1016C70BC, 580, 'c0ddf7ad19e8291a35089705ab7371ca6006bf1426e8761518a0b0f470db4191'),
    'load_asset_list': (0x1016C4FC8, 3956, '6bec9e09f2d313715aaad48ca6f9790b871005cb9ffea7ea4c81d7a430936c78'),
    'downloaded_check': (0x1016CAC38, 140, '1ad336086960dbbe7ebc2301fd24af06ce1ad59c6d90254122956bfa4e67aff3'),
    'compare_receipt': (0x1016CAA10, 224, '80d2f41db11ee8d96208acf4acc811275f18304b21297ebff5f3ffcea4564951'),
    'finalize_and_receipt': (0x1016CB864, 2144, 'b4d29266423bcf204f1a99f440720a5abe2671c004d6e26ced4c0a2c432daa34'),
    'path_resolver': (0x1016C3B80, 632, '38c90c13a0ccbf5b5ed77e96150d99f74fb32035ec989e9188b4667999343231'),
    'receipt_tree_emplace': (0x1016CF50C, 392, 'bc2fe607b7e4c0f4b687666531f42a3428d507619721a001f183981a3557b072'),
    'receipt_tree_lookup': (0x1016CF6E4, 140, '9ab0bf18e0c3fc37032913f0b7739ecff695342e83c7d0fc206936c2c4d31cd0'),
}
STRINGS = {0x102740387: '/asset_list_base.txtCache.txt',
           0x102740406: '%[^\n]\n%n', 0x10274040F: '%[^\t]\t%n',
           0x1027404AC: '%u\n', 0x10273FFAA: '%s\t%s\n',
           0x102740F66: '%08x%08x%08x%08x',
           0x102740504: 'Untracked asset file in cache: %s\n'}
IMPORTS = {0x102271850: '_fscanf', 0x1022717FC: '_fprintf',
           0x102271820: '_fread', 0x1022718B0: '_fwrite',
           0x1022725AC: '_memcmp', 0x1022730F8: '_stat',
           0x1022717A8: '_fflush', 0x1022717C0: '_fileno', 0x102271880: '_fsync'}


def logical_path(value):
    path = value.lstrip('/')
    if (not value.startswith('/') or value.startswith('//') or not path or '\\' in path or '\0' in path
            or any(part in ('', '.', '..') or ':' in part for part in path.split('/'))):
        raise ValueError('Unsafe ledger/catalog logical path')
    return path


def parse_ledger(data):
    """Parse the observed v4 receipts; the first text line is not an entry count."""
    if not 8 < len(data) <= MAX_LEDGER_BYTES:
        raise ValueError('Ledger length outside the bounded v4 scope')
    magic, version = struct.unpack_from('<II', data)
    if (magic, version) != (CACHE_MAGIC, CACHE_VERSION):
        raise ValueError('Unsupported cache-ledger magic/version')
    lines = data[8:].decode('utf-8', errors='strict').splitlines()
    if not lines or not re.fullmatch(r'\d+', lines[0]):
        raise ValueError('Expected the client revision token after the binary header')
    records = {}
    for line in lines[1:]:
        fields = line.split('\t')
        if len(fields) != 2 or not re.fullmatch('[0-9a-f]{32}', fields[1]):
            raise ValueError('Malformed path/transport-MD5 cache receipt')
        path = logical_path(fields[0])
        if path in records:
            raise ValueError('Duplicate cache receipt; no last-write interpretation is guessed')
        records[path] = fields[1]
    return {'magic': hex(magic), 'format_version': version,
            'client_revision_token': lines[0], 'entry_count': len(records), 'records': records}


def parse_catalog(data):
    records = {}
    for line in data.decode('utf-8', errors='strict').splitlines():
        fields = line.rsplit(None, 3)
        if (len(fields) != 4 or not re.fullmatch('[0-9a-f]{32}', fields[1])
                or not all(value.isdecimal() for value in fields[2:])):
            raise ValueError('Malformed asset catalog entry')
        path = logical_path(fields[0])
        if path in records:
            raise ValueError('Duplicate group catalog path')
        records[path] = dict(md5=fields[1], transport_bytes=int(fields[2]), stored_bytes=int(fields[3]))
    return records


def classify_catalog(catalog, receipts, available):
    """Static receipt projection, not execution of platform filtering or loaders."""
    rows = []
    for path, expected in sorted(catalog.items()):
        recorded = receipts.get(path)
        status = ('receipt_missing' if recorded is None else 'receipt_matches_catalog'
                  if recorded == expected['md5'] else 'receipt_differs_from_catalog')
        rows.append({'path': path, 'stored_file_present': path in available,
                     'receipt_status': status,
                     'expected_transport_md5': expected['md5'],
                     'recorded_transport_md5': recorded})
    return {'paths': len(rows), 'receipt_status_counts': dict(Counter(r['receipt_status'] for r in rows)),
            'stored_files_present': sum(r['stored_file_present'] for r in rows), 'rows': rows,
            'evidence': 'Projection of catalog/ledger membership; no platform-agent filter or device execution'}


def trace_binary(binary):
    if macho_uuid(binary) != SUPPORTED_MACHO_UUID:
        raise ValueError('Unsupported executable UUID')
    image = MachO(binary)
    regions = {}
    for name, (address, length, expected) in REGIONS.items():
        offset = image.vm_offset(address, length)
        digest = hashlib.sha256(image.data[offset:offset + length]).hexdigest()
        if digest != expected:
            raise ValueError(f'Unexpected {name} instructions')
        regions[name] = dict(address=hex(address), bytes=length, sha256=digest)
    for address, expected in STRINGS.items():
        if image.vm_string(address) != expected:
            raise ValueError('Unexpected ledger format/diagnostic string')
    for address, expected in IMPORTS.items():
        if imported_symbol_at(image, address) != expected:
            raise ValueError('Unexpected receipt trace import binding')
    if image.vm_string(image.vm_pointer(image.vm_pointer(0x102C5DC90) + 8)) != 'N2cc12AssetManagerE':
        raise ValueError('Unexpected AssetManager RTTI')
    if image.vm_pointer(0x102C5DD90) != 0x1016CAC38:
        raise ValueError('Unexpected downloaded-check virtual slot')
    return {'executable_uuid': SUPPORTED_MACHO_UUID.hex(), 'guarded_regions': regions,
            'vtable': '0x102c5dc98', 'downloaded_check_slot': '0xf8',
            'ledger_fixed_logical_path': STRINGS[0x102740387],
            'evidence': 'Static exact-build functions, strings, imports and RTTI'}


def probe_admission_fragment(binary):
    """Execute the guarded receipt-count branch with synthetic map/result state.

    Only the hash-comparison helper is intercepted with a supplied equality
    result; file I/O, path resolution, full loading and game startup do not run.
    """
    trace_binary(binary)
    try:
        from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
        from unicorn.arm64_const import (UC_ARM64_REG_PC, UC_ARM64_REG_SP,
                                        UC_ARM64_REG_X23, UC_ARM64_REG_W0)
    except ImportError:
        return {'available': False, 'reason': 'Optional Unicorn runtime unavailable'}
    image = MachO(binary)
    code = 0x1016C5000
    offset = image.vm_offset(code, 4096)
    rows = []
    for case, exists, equal in [('receipt_missing', False, False),
                                ('receipt_matches_catalog', True, True),
                                ('receipt_differs_from_catalog', True, False)]:
        emulator = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        emulator.mem_map(code, 4096)
        emulator.mem_write(code, image.data[offset:offset + 4096])
        base, stack = 0x70000000, 0x70001000
        emulator.mem_map(base, 0x5000)
        sentinel, entry, result = base + 0x2000, base + 0x3000, base + 0x4000
        emulator.reg_write(UC_ARM64_REG_SP, stack)
        emulator.reg_write(UC_ARM64_REG_X23, entry if exists else sentinel)
        emulator.mem_write(stack + 0x90, struct.pack('<Q', sentinel))
        emulator.mem_write(stack + 0x98, struct.pack('<Q', result))
        emulator.mem_write(stack + 0x78, struct.pack('<Q', 100))
        stopped = []

        def hook(uc, address, _size, _user):
            if address in (0x1016C5268, 0x1016C5770, 0x1016C5778):
                stopped.append(hex(address))
                uc.emu_stop()
            elif address == 0x1016C573C:
                uc.reg_write(UC_ARM64_REG_W0, int(equal))
                uc.reg_write(UC_ARM64_REG_PC, address + 4)

        emulator.hook_add(UC_HOOK_CODE, hook)
        emulator.emu_start(0x1016C5728, 0x1016C577C, count=64)
        completed = struct.unpack('<I', emulator.mem_read(result + 4, 4))[0]
        if not stopped or completed != int(exists and equal):
            raise ValueError('Guarded receipt-count fragment behaved unexpectedly')
        rows.append({'case': case, 'completed_count_increment': completed, 'stop': stopped[0]})
    return {'available': True, 'cases': rows,
            'entry': '0x1016c5728', 'intercepted_helper_call': '0x1016c573c',
            'evidence': 'Host ARM64 fragment execution with synthetic map state and supplied MD5-comparison result',
            'full_asset_manager_executed': False, 'device_tested': False}


def audit(ipa_path, cache_path, *, probe=False):
    with zipfile.ZipFile(ipa_path) as ipa, zipfile.ZipFile(cache_path) as cache:
        binary = ipa.read(BINARY_PATH)
        traced = trace_binary(binary)
        ledger_info = cache.getinfo(LEDGER)
        if ledger_info.file_size > MAX_LEDGER_BYTES:
            raise ValueError('Ledger archive member exceeds the bounded scope')
        ledger_bytes = cache.read(ledger_info)
        ledger = parse_ledger(ledger_bytes)
        names = [info for info in ipa.infolist() if info.filename.rsplit('/', 1)[-1] == GROUP]
        if len(names) != 1:
            raise ValueError('Expected one original Hybrid Highway group catalog')
        if names[0].file_size > MAX_LEDGER_BYTES:
            raise ValueError('Group catalog exceeds the bounded audit scope')
        catalog_bytes = ipa.read(names[0])
        catalog = parse_catalog(catalog_bytes)
        available = set()
        for archive, prefix in ((ipa, 'Payload/RealRacing3.app/res/'), (cache, 'Caches/')):
            available.update(info.filename[len(prefix):] for info in archive.infolist()
                             if info.filename.startswith(prefix) and not info.is_dir())
        receipt_records = ledger.pop('records')
        hd = {p: e for p, e in catalog.items() if p.startswith(GROUP_PREFIX)}
        speedrush = 'SpeedRush_TV_commercial.mp4'
        report = {'binary_trace': traced, 'ledger': {**ledger, 'sha256': hashlib.sha256(ledger_bytes).hexdigest()},
                  'group_manifest': GROUP, 'group_manifest_sha256': hashlib.sha256(catalog_bytes).hexdigest(),
                  'entire_group_without_runtime_filter': classify_catalog(catalog, receipt_records, available),
                  'hd_hybrid_highway_subset': classify_catalog(hd, receipt_records, available),
                  'speedrush_comparison': {'stored_file_present': speedrush in available,
                                           'receipt_present': speedrush in receipt_records,
                                           'recorded_transport_md5': receipt_records.get(speedrush)},
                  'ledger_archive_members': [info.filename for info in cache.infolist()
                                            if info.filename.endswith('Cache.txt') and '__MACOSX/' not in info.filename],
                  'cache_modified': False, 'device_tested': False,
                  'limits': ['Runtime agent filtering and selected event eligibility were not executed.',
                             'A receipt match is bookkeeping evidence; it does not rehash expanded payload bytes.',
                             'No candidate ledger or registration format is generated.']}
    if probe:
        report['admission_fragment_probe'] = probe_admission_fragment(binary)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ipa', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--probe-branch', action='store_true')
    args = parser.parse_args()
    allowed = (ROOT / 'investigation/recovered_assets/optional').resolve()
    if not args.report.resolve().is_relative_to(allowed):
        parser.error('Private reports must stay under ignored investigation/recovered_assets/optional/')
    if args.report.exists():
        raise FileExistsError('Refusing to overwrite an existing registration report')
    report = audit(args.ipa, args.cache, probe=args.probe_branch)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
