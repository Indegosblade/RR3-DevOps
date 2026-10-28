"""Read-only exact-build trace of the normal post-race backdrop and image gaps.

Static callbacks and names are not a demonstrated black-background diagnosis.
This tool writes reports only; it does not patch an executable or game asset.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from build_4k_v3 import BINARY_PATH, SUPPORTED_MACHO_UUID, macho_uuid
from scripts.audit_visual_assets import audit, gui_documents
from scripts.trace_postrace import direct_branch_target, sections

BASE = 0x100000000
CONSTRUCTOR = 0x3D2610
SETUP = 0x3D26C0
DRAW = 0x3D2708
DRAW_CODE = bytes.fromhex(
    '02041836080840f9c80300b4289846b9299046b91f0500312801881a1f25007101030054'
    'f44fbea9fd7b01a9fd430091087401f008c13891080140f9090140f9294140f900102e1e'
    '01102e1e02102e1e03102e1ef30300aae00308aa20013fd6600640f975ed0c94600a40f9'
    'c2ba0494600640f9fd7b41a9f44fc2a879ed0c14c0035fd6'
)
REGIONS = {
    'constructor': (CONSTRUCTOR, 24, '6514049b3ae67631d1648b4fa1b42b54f4f27648a99891bb1c95f05b27dd97c5'),
    'setup': (SETUP, 64, '9595cadb0a1adf311a7f28a3355871df8edb7aa81cce0482814c670a67457679'),
    'draw': (DRAW, 132, '36d7628422b088c61fabda36e0ff10686eccdf95cd7c998af31d236fa3a762a1'),
    'car_sale_selection': (0x71CF40, 512, '0606542bf3671fa4d31d9e5da0ee3fb208d33f862596f2ff3775e1a27fdc1163'),
}
STRINGS = {
    0x1025927B7: b'PostRaceBackground.xml\0',
    0x102379DB7: b'7SkyBurn\0',
    0x1025C3276: b'car_sales/cars/build_[0]/car_sales_car_[1].png\0',
    0x1025C32A5: b'car_sales/cars/accelerator_cars/car_sales_car_[0].png\0',
    0x1025C3341: b'car_sales/cars/car_sales_car_generic_silhoutte.png\0',
}


def adrp_add_target(first, second, address):
    """Resolve adjacent 64-bit ADRP+ADD-immediate using the ADRP destination.

    Non-adjacent data flow and pointer-table references are intentionally not
    inferred. Restricting the pair avoids crossing a return/register overwrite.
    """
    if first & 0x9F000000 != 0x90000000 or second & 0xFF000000 != 0x91000000:
        return None
    if first & 31 != (second >> 5) & 31:
        return None
    immediate = ((first >> 29) & 3) | (((first >> 5) & 0x7FFFF) << 2)
    if immediate & (1 << 20):
        immediate -= 1 << 21
    addend = ((second >> 10) & 4095) << (12 if second & (1 << 22) else 0)
    return (address & ~4095) + (immediate << 12) + addend


def validate_regions(binary):
    if macho_uuid(binary) != SUPPORTED_MACHO_UUID:
        raise ValueError('Unsupported main executable UUID')
    for name, (offset, size, expected) in REGIONS.items():
        if hashlib.sha256(binary[offset:offset + size]).hexdigest() != expected:
            raise ValueError(f'Expected {name} instructions do not match')


def trace_binary(binary):
    validate_regions(binary)
    parts = sections(binary)

    def read_address(address, length):
        for part in parts:
            if part['address'] <= address and address + length <= part['address'] + part['size']:
                offset = part['offset'] + address - part['address']
                return binary[offset:offset + length]
        raise ValueError('Address is not in a file-backed section')

    for address, expected in STRINGS.items():
        if read_address(address, len(expected)) != expected:
            raise ValueError('Expected backdrop/resource string does not match')
    typeinfo = struct.unpack('<Q', read_address(0x102BABAF0, 8))[0]
    name_address = struct.unpack('<Q', read_address(typeinfo + 8, 8))[0]
    if read_address(name_address, 9) != b'7SkyBurn\0':
        raise ValueError('Backdrop vtable does not resolve to the researched SkyBurn RTTI')
    string_refs = defaultdict(list)
    callers = []
    for part in parts:
        if part['name'] != '__text':
            continue
        data = binary[part['offset']:part['offset'] + part['size']]
        if len(data) % 4:
            raise ValueError('Unaligned ARM64 text section')
        words = memoryview(data)
        for offset in range(0, len(words), 4):
            word = struct.unpack_from('<I', words, offset)[0]
            address = part['address'] + offset
            if direct_branch_target(word, address) == BASE + CONSTRUCTOR:
                callers.append(hex(address))
            if offset + 8 <= len(words) and word & 0x9F000000 == 0x90000000:
                following = struct.unpack_from('<I', words, offset + 4)[0]
                target = adrp_add_target(word, following, address)
                if target in STRINGS:
                    string_refs[STRINGS[target][:-1].decode()].append(hex(address))
    return {
        'evidence': 'static exact-build instructions/RTTI; no connected device or visual validation',
        'executable_uuid': SUPPORTED_MACHO_UUID.hex(),
        'guarded_regions': {name: {'offset': hex(offset), 'bytes': size, 'sha256': checksum}
                            for name, (offset, size, checksum) in REGIONS.items()},
        'background_task': {'class': 'SkyBurn', 'vtable': '0x102babae8',
                            'constructor': hex(BASE + CONSTRUCTOR), 'setup': hex(BASE + SETUP),
                            'draw_callback': hex(BASE + DRAW)},
        'direct_constructor_callers': callers,
        'adjacent_adrp_add_string_references': dict(string_refs),
        'lifecycle': [
            {'site': '0x1003d2610', 'effect': 'store context pointer at task+0x08; GUI pointer at task+0x10 and predicate byte at task+0x18 initialized to zero'},
            {'site': '0x1003d26c0', 'effect': 'allocate 0x220-byte generic GUI object, store at task+0x10, load PostRaceBackground.xml via 0x100536ff0'},
            {'site': '0x1003d2708', 'effect': 'return unless callback flags have bit3, GUI exists and effective selector equals9'},
            {'site': '0x1003d2714', 'effect': 'effective selector uses context+0x698 unless it is -1, otherwise context+0x690'},
            {'site': '0x1003d2738', 'effect': 'global interface at 0x103255e30 virtual slot+0x80 receives four 1.0 float arguments'},
            {'site': '0x1003d276c', 'effect': 'view wrapper0x10070dd40; GUI draw0x10050127c; tail view wrapper0x10070dd68'},
            {'site': '0x1003d2628', 'effect': 'destructor deletes a non-null GUI object through its virtual destructor'},
        ],
        'online_dependency_observed_in_local_callback': False,
        'car_sale_path_selection': {
            'versioned_template_site': '0x10071cf80', 'accelerator_template_site': '0x10071cfc0',
            'candidate_lookups': ['0x10071d040', '0x10071d07c', '0x10071d08c'],
            'missing_image_log': '0x10071d0ac', 'silhouette_fallback_load': '0x10071d0fc',
            'interpretation': 'Versioned/accelerator candidates are constructed and tried before a generic silhouette fallback; do not rename unrelated atlas images by basename.'},
        'limits': [
            'Adjacent instruction and direct-call scans do not cover computed addresses or indirect callers.',
            'Selector9 and callback-bit3 meanings are not assigned a source-level enum name here.',
            'The four-float call resembles white tint/draw state, but its exact interface method name is not established.',
            'No online response flag is read in the local SkyBurn callback; higher-level state transitions and loader internals remain outside that statement.',
            'Static resource presence does not prove rendering, selected atlas family or visible screen eligibility.',
        ],
    }


def classify_references(references, sprite_families):
    """Classify evidence without turning lookalike filenames into replacements."""
    by_basename = defaultdict(list)
    casefold = defaultdict(list)
    for image in sprite_families:
        by_basename[PurePosixPath(image).name.lower()].append(image)
        casefold[image.lower()].append(image)
    results = []
    for reference in references:
        if reference['status'] != 'unresolved':
            continue
        image = reference['image']
        basename_matches = sorted(by_basename.get(PurePosixPath(image).name.lower(), ()))
        car = re.fullmatch(r'car_sales/cars/car_sales_car_(\d+)\.png', image)
        versioned = [match for match in basename_matches if car and re.fullmatch(
            r'car_sales/cars/(?:build_\d+|accelerator_cars)/car_sales_car_' + car[1] + r'\.png', match)]
        if versioned:
            category = 'runtime_car_sale_path_candidates_available'
        elif image.startswith('R4/'):
            category = 'prototype_named_namespace_runtime_use_unproven'
        elif reference['matching_absent_atlas_declarations']:
            category = 'absent_manifest_collection_candidate'
        elif 'placeholder' in image.lower():
            category = 'placeholder_named_reference_assignment_unproven'
        elif casefold.get(image.lower()):
            category = 'case_only_sprite_candidate_lookup_rules_unproven'
        else:
            category = 'unresolved_runtime_binding_or_content'
        results.append({'image': image, 'category': category,
                        'available_car_sale_candidates': versioned,
                        'same_basename_other_collections': basename_matches,
                        'case_only_candidates': sorted(casefold.get(image.lower(), ())),
                        'automatic_replacement_justified': False,
                        'layouts': sorted({use['layout'] for use in reference['uses']}),
                        'matching_absent_atlas_declarations': reference['matching_absent_atlas_declarations']})
    return {'counts': dict(Counter(item['category'] for item in results)), 'references': results,
            'same_basename_other_collection_reference_count': sum(bool(item['same_basename_other_collections']) for item in results),
            'same_basename_limited_time_series_reference_count': sum(item['image'].startswith('ltd_timed_series/') and bool(item['same_basename_other_collections']) for item in results),
            'case_only_sprite_reference_count': sum(bool(item['case_only_candidates']) for item in results),
            'limit': 'Category names describe static evidence, not confirmed visible failures or successful replacements.'}


def resource_trace(ipa_path, cache_path):
    inventory = audit(ipa_path, cache_path, map_layouts=True)
    sprite_families = defaultdict(set)
    editor_refs = set()
    with zipfile.ZipFile(ipa_path) as ipa, zipfile.ZipFile(cache_path) as cache:
        for archive, prefix in ((ipa, 'Payload/RealRacing3.app/res/'), (cache, 'Caches/')):
            for name in archive.namelist():
                if not name.startswith(prefix) or not name.endswith('.ios.atlas'):
                    continue
                match = re.match(r'gui_assets/(\d+x\d+)/(.*)/[^/]+\.ios\.atlas$', name[len(prefix):])
                if not match:
                    continue
                for image in ET.fromstring(archive.read(name)).findall('image'):
                    sprite_families[match[2] + '/' + image.get('name', '').replace('\\', '/')].add(match[1])
        for name in ipa.namelist():
            if not name.endswith('.gui'):
                continue
            try:
                documents = gui_documents(ipa.read(name))
            except ET.ParseError:
                continue
            for node in documents.iter():
                if node.get('editor_only_image', '').lower() == 'true':
                    editor_refs.update(value.replace('\\', '/').lstrip('/') for value in node.attrib.values()
                                       if value.lower().endswith(('.png', '.jpg', '.jpeg')))
        backdrop = gui_documents(ipa.read('Payload/RealRacing3.app/res/gui/processed/PostRaceBackground.gui'))
        backdrop_images = [{'image': node.get('image'), 'blend_type': node.get('blend_type'),
                            'mode': node.get('mode'), 'r': node.get('r'), 'g': node.get('g'),
                            'b': node.get('b'), 'a': node.get('a')}
                           for node in backdrop.iter() if node.get('image')]
    result = classify_references(inventory['layout_image_references'], sprite_families)
    result.update({'explicit_editor_only_image_names_excluded': len(editor_refs),
                   'postrace_layout_images': backdrop_images,
                   'postrace_image_families': sorted(sprite_families['rewards/post_race_sky_burn.png']),
                   'generic_car_silhouette_families': sorted(sprite_families['car_sales/cars/car_sales_car_generic_silhoutte.png'])})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='Researched executable or IPA')
    parser.add_argument('--cache', type=Path, help='With an IPA, map layout references to cache/bundled sprites')
    parser.add_argument('--output', type=Path, help='Write report JSON, refusing overwrite')
    args = parser.parse_args()
    is_ipa = zipfile.is_zipfile(args.input)
    if args.cache and not is_ipa:
        parser.error('--cache requires an IPA input')
    if is_ipa:
        with zipfile.ZipFile(args.input) as archive:
            binary = archive.read(BINARY_PATH)
    else:
        binary = args.input.read_bytes()
    report = trace_binary(binary)
    if args.cache:
        report['resource_classification'] = resource_trace(args.input, args.cache)
    rendered = json.dumps(report, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as output:
            output.write(rendered)
    summary = dict(report)
    if 'resource_classification' in summary:
        summary['resource_classification'] = {key: value for key, value in report['resource_classification'].items() if key != 'references'}
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
