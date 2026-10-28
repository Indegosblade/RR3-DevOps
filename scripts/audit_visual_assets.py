"""Read-only manifest/atlas audit of a preserved IPA and imported-cache ZIP.

Missing optional families are inventory findings, not proof of a visible bug.
Transport hashes are deliberately not compared with expanded stored-file bytes.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
import zlib


def gui_documents(data):
    """Decode the researched GUI format using the existing EDS transform.

    Some files concatenate a layout and separate animation documents. Wrapping
    those fragments for analysis avoids calling valid engine input corrupt XML.
    No decoded game content is written by this helper.
    """
    if not data.lstrip().startswith(b'<'):
        root = Path(__file__).resolve().parents[1]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from build_4k_v3 import eds_crypt
        data = eds_crypt(data)
    fragments = re.sub(rb'<\?xml\s[^?]*\?>', b'', data)
    return ET.fromstring(b'<resource_audit>' + fragments + b'</resource_audit>')


class TextureAuditLimit(ValueError):
    """A texture exceeds the caller's explicit memory/work bound."""


def pvr_dimensions(data, compressed):
    """Inspect only a PVR v2 header, optionally in the game's size+zlib wrapper."""
    if compressed:
        if len(data) < 5:
            raise ValueError('Truncated texture wrapper')
        data = zlib.decompressobj().decompress(data[4:], 52)
    if len(data) < 52:
        raise ValueError('Truncated PVR header')
    fields = struct.unpack_from('<13I', data)
    if fields[0] != 52 or fields[11] != 0x21525650:
        raise ValueError('Unsupported PVR header')
    height, width = fields[1:3]
    if not width or not height:
        raise ValueError('Zero-sized PVR texture')
    return width, height


def verify_texture_stream(data, compressed, max_bytes):
    """Check the whole wrapper/zlib/PVR payload, without decoding image pixels.

    Trailing zlib bytes are recorded rather than rejected: the engine's
    treatment of an otherwise complete stream's trailer is not established.
    """
    if len(data) > max_bytes:
        raise TextureAuditLimit('Stored texture exceeds the audit byte limit')
    trailing = 0
    if compressed:
        if len(data) < 5:
            raise ValueError('Truncated texture wrapper')
        declared = struct.unpack_from('<I', data)[0]
        if declared > max_bytes:
            raise TextureAuditLimit('Declared texture payload exceeds the audit byte limit')
        decoder = zlib.decompressobj()
        payload = decoder.decompress(data[4:], declared + 1)
        if len(payload) != declared:
            raise ValueError('Texture wrapper length does not match expanded payload')
        if not decoder.eof or decoder.unconsumed_tail:
            raise ValueError('Texture zlib stream is incomplete or exceeds its declared length')
        trailing = len(decoder.unused_data)
    else:
        payload = data
    pvr_dimensions(payload, False)
    fields = struct.unpack_from('<13I', payload)
    if fields[12] != 1:
        raise TextureAuditLimit('Full payload validation currently supports one PVR surface')
    if len(payload) != fields[0] + fields[5]:
        raise ValueError('PVR payload length does not match its texture-data size')
    return {'stored_bytes': len(data), 'expanded_bytes': len(payload), 'trailing_zlib_bytes': trailing}


def audit(ipa_path, cache_path, *, verify_gui_streams=False, max_texture_bytes=64 * 1024 * 1024,
          map_layouts=False):
    with zipfile.ZipFile(ipa_path) as ipa, zipfile.ZipFile(cache_path) as cache:
        assets = {}
        counts = {}
        for label, archive, prefix in (
            ('bundled', ipa, 'Payload/RealRacing3.app/res/'),
            ('cache', cache, 'Caches/'),
        ):
            count = 0
            for item in archive.infolist():
                if item.is_dir() or not item.filename.startswith(prefix):
                    continue
                relative = item.filename[len(prefix):]
                if '..' in relative.split('/') or any(part.startswith('._') for part in relative.split('/')):
                    continue
                assets[relative] = (archive, item)
                count += 1
            counts[label] = count

        def read(name, limit=None):
            archive, item = assets[name]
            with archive.open(item) as stream:
                return stream.read(limit) if limit else stream.read()

        records = defaultdict(list)
        malformed = []
        ledger_name = 'asset_list_base.txtCache.txt'
        for name in sorted(assets):
            if name == ledger_name or not PurePosixPath(name).name.startswith('asset_list_') or not name.endswith('.txt'):
                continue
            for line in read(name).decode('utf-8', errors='replace').splitlines():
                fields = line.rsplit(None, 3)
                if not fields:
                    continue
                if len(fields) != 4 or not fields[0].startswith('/') or not re.fullmatch(r'[0-9a-f]{32}', fields[1]):
                    malformed.append({'manifest': name, 'line': line[:160]})
                    continue
                records[fields[0].lstrip('/')].append({'manifest': name, 'transport_bytes': int(fields[2]), 'stored_bytes': int(fields[3])})

        ledger = []
        if ledger_name in assets:
            for line in read(ledger_name).decode('utf-8', errors='replace').splitlines():
                fields = line.rsplit(None, 1)
                if len(fields) == 2 and fields[0].startswith('/') and re.fullmatch(r'[0-9a-f]{32}', fields[1]):
                    ledger.append(fields[0].lstrip('/'))

        families = defaultdict(Counter)
        high_missing = []
        for name in sorted(records):
            match = re.match(r'gui_assets/(\d+x\d+)/', name)
            if match:
                family = match[1]
                families[family]['declared'] += 1
                families[family]['present' if name in assets else 'absent'] += 1
                if family == '2048x1536' and name not in assets:
                    high_missing.append({'path': name, 'manifests': sorted({r['manifest'] for r in records[name]})})

        missing_pages, bad_headers, bad_bounds, bad_xml = [], [], [], []
        bad_streams, skipped_streams, stream_trailers = [], [], []
        verified_streams = stored_bytes_checked = expanded_bytes_checked = 0
        dimensions = {}
        sprites = defaultdict(set)
        atlas_count = image_count = 0
        for name in sorted(assets):
            if not name.endswith('.ios.atlas'):
                continue
            atlas_count += 1
            try:
                root = ET.fromstring(read(name))
            except (ET.ParseError, zipfile.BadZipFile) as exc:
                bad_xml.append({'atlas': name, 'error': str(exc)})
                continue
            texture_format = root.get('texture_formats', '')
            if texture_format not in ('.rgb.pvr', '.ptc.pvr'):
                bad_xml.append({'atlas': name, 'unsupported_texture_format': texture_format})
                continue
            images = root.findall('image')
            image_count += len(images)
            family = re.match(r'gui_assets/(\d+x\d+)/(.*)/[^/]+\.ios\.atlas$', name)
            if family:
                for image in images:
                    logical_image = family[2] + '/' + image.get('name', '').replace('\\', '/')
                    sprites[logical_image].add(family[1])
            for image in images:
                for position in image.findall('pos'):
                    base = name[:-len('.ios.atlas')] + '_' + position.attrib['id'] + texture_format
                    page = next((candidate for candidate in (base + '.z', base) if candidate in assets), None)
                    if page is None:
                        item = {'atlas': name, 'page': base, 'background_names': []}
                        if any(term in image.get('name', '').lower() for term in ('background', 'bg_', '_bg', 'splash')):
                            item['background_names'].append(image.get('name'))
                        missing_pages.append(item)
                        continue
                    if page not in dimensions:
                        try:
                            dimensions[page] = pvr_dimensions(read(page, 4096), page.endswith('.z'))
                        except (ValueError, zlib.error, struct.error, zipfile.BadZipFile) as exc:
                            dimensions[page] = None
                            bad_headers.append({'page': page, 'error': str(exc)})
                            if isinstance(exc, zipfile.BadZipFile) and verify_gui_streams and page.startswith('gui_assets/'):
                                bad_streams.append({'page': page, 'error': str(exc)})
                        if verify_gui_streams and page.startswith('gui_assets/') and dimensions[page] is not None:
                            try:
                                if assets[page][1].file_size > max_texture_bytes:
                                    raise TextureAuditLimit('Stored texture exceeds the audit byte limit')
                                # Reading the entire ZIP member also validates its ZIP CRC.
                                checked = verify_texture_stream(read(page), page.endswith('.z'), max_texture_bytes)
                                verified_streams += 1
                                stored_bytes_checked += checked['stored_bytes']
                                expanded_bytes_checked += checked['expanded_bytes']
                                if checked['trailing_zlib_bytes']:
                                    stream_trailers.append({'page': page, 'bytes': checked['trailing_zlib_bytes']})
                            except TextureAuditLimit as exc:
                                skipped_streams.append({'page': page, 'reason': str(exc)})
                            except (ValueError, zlib.error, struct.error, zipfile.BadZipFile) as exc:
                                bad_streams.append({'page': page, 'error': str(exc)})
                    if dimensions[page] is None:
                        continue
                    width, height = dimensions[page]
                    x, y = int(position.attrib['x']), int(position.attrib['y'])
                    sprite_w, sprite_h = int(image.attrib['width']), int(image.attrib['height'])
                    if min(x, y, sprite_w, sprite_h) < 0 or x + sprite_w > width or y + sprite_h > height:
                        bad_bounds.append({'atlas': name, 'image': image.get('name'), 'page': page,
                                           'rectangle': [x, y, sprite_w, sprite_h], 'page_size': [width, height]})

        # Multiple sprites on one missing page are one page finding.
        pages = {}
        for item in missing_pages:
            key = (item['atlas'], item['page'])
            existing = pages.setdefault(key, dict(item, background_names=[]))
            existing['background_names'].extend(item['background_names'])
        layout_errors = []
        layout_files = layout_documents = 0
        references = defaultdict(list)
        if map_layouts:
            for name in sorted(assets):
                if not name.endswith('.gui'):
                    continue
                try:
                    root = gui_documents(read(name))
                except (ET.ParseError, zipfile.BadZipFile) as exc:
                    layout_errors.append({'layout': name, 'error': str(exc)})
                    continue
                layout_files += 1
                layout_documents += len(root)
                for element in root.iter():
                    if element.get('editor_only_image', '').lower() == 'true':
                        continue
                    for key, value in element.attrib.items():
                        if value.lower().endswith(('.png', '.jpg', '.jpeg')):
                            logical = value.replace('\\', '/').lstrip('/')
                            references[logical].append({'layout': name, 'node': element.tag,
                                                        'id_string': element.get('id_string'), 'attribute': key})
        missing_atlases = [item for item in high_missing if item['path'].endswith('.ios.atlas')]
        reference_map = []
        for image, uses in sorted(references.items()):
            available_families = sorted(sprites.get(image, ()))
            if available_families:
                status = 'hd_sprite_available' if '2048x1536' in available_families else 'other_sprite_family_available'
            elif image in assets:
                status = 'standalone_image_available'
            else:
                status = 'unresolved'
            missing_declarations = []
            if status == 'unresolved':
                for atlas in missing_atlases:
                    collection = atlas['path'].split('/', 2)[2].rsplit('/', 1)[0]
                    if image.startswith(collection + '/'):
                        missing_declarations.append(atlas)
            reference_map.append({'image': image, 'status': status, 'available_families': available_families,
                                  'matching_absent_atlas_declarations': missing_declarations,
                                  'uses': uses})
        return {
            'scope': 'Static inventory of all declared families/events; not runtime selection or device validation',
            'archive_resource_counts': counts,
            'unique_available_resources': len(assets),
            'manifest_files': len({r['manifest'] for rows in records.values() for r in rows}),
            'manifest_unique_paths': len(records),
            'malformed_manifest_records': malformed,
            'base_ledger_paths': len(ledger),
            'base_ledger_missing': sorted(set(ledger) - set(assets)),
            'gui_family_coverage': {family: dict(values) for family, values in sorted(families.items())},
            'high_family_absent_declarations': high_missing,
            'atlases_inspected': atlas_count,
            'atlas_images_inspected': image_count,
            'texture_pages_inspected': len(dimensions),
            'available_atlas_missing_pages': list(pages.values()),
            'invalid_texture_headers': bad_headers,
            'out_of_bounds_atlas_images': bad_bounds,
            'invalid_atlas_xml': bad_xml,
            'gui_stream_verification_requested': verify_gui_streams,
            'gui_texture_streams_verified': verified_streams,
            'gui_texture_stored_bytes_checked': stored_bytes_checked,
            'gui_texture_expanded_bytes_checked': expanded_bytes_checked,
            'invalid_gui_texture_streams': bad_streams,
            'gui_texture_streams_skipped': skipped_streams,
            'gui_texture_stream_trailers': stream_trailers,
            'layout_mapping_requested': map_layouts,
            'gui_layout_files_decoded': layout_files,
            'gui_layout_documents_parsed': layout_documents,
            'gui_layout_decode_errors': layout_errors,
            'layout_unique_image_references': len(reference_map),
            'layout_reference_status_counts': dict(Counter(item['status'] for item in reference_map)),
            'layout_image_references': reference_map,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ipa', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify-gui-streams', action='store_true', help='Verify complete available GUI texture wrappers, zlib streams, PVR payload sizes and ZIP CRCs')
    parser.add_argument('--max-texture-mib', type=int, default=64, help='Maximum stored or expanded bytes per texture, in MiB (default: 64)')
    parser.add_argument('--map-layouts', action='store_true', help='Decode GUI layout/animation documents and map their image references to available atlas families')
    args = parser.parse_args()
    if args.max_texture_mib < 1:
        parser.error('--max-texture-mib must be positive')
    result = audit(args.ipa, args.cache, verify_gui_streams=args.verify_gui_streams,
                   max_texture_bytes=args.max_texture_mib * 1024 * 1024, map_layouts=args.map_layouts)
    rendered = json.dumps(result, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as output:
            output.write(rendered)
    summary = {key: len(value) if isinstance(value, list) else value for key, value in result.items()}
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
