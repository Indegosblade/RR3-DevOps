from pathlib import Path
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
import zlib

from scripts.audit_visual_assets import audit, gui_documents, pvr_dimensions, verify_texture_stream, TextureAuditLimit
from build_4k_v3 import eds_crypt


def texture(width=8, height=8):
    pixels = bytes(width * height * 4)
    header = struct.pack('<13I', 52, height, width, 0, 0x10012, len(pixels), 32,
                         0, 0, 0, 0, 0x21525650, 1)
    data = header + pixels
    return struct.pack('<I', len(data)) + zlib.compress(data)


class VisualAssetAuditTests(unittest.TestCase):
    def fixture(self, directory, *, include_page=True, x=1, page_data=None, layout=None):
        ipa, cache = Path(directory) / 'fixture.ipa', Path(directory) / 'cache.zip'
        folder = 'gui_assets/2048x1536/backgrounds/'
        atlas = (f'<atlas_images texture_formats=".rgb.pvr">'
                 f'<image name="background.png" width="4" height="4"><pos id="0" x="{x}" y="1"/></image>'
                 '<image name="shade.png" width="1" height="1"><pos id="0" x="0" y="0"/></image>'
                 '</atlas_images>').encode()
        manifest = (f'/{folder}sprites.ios.atlas\t' + 'a' * 32 + f'\t9\t{len(atlas)}\n'
                    + '/textures/file with spaces.bin\t' + 'b' * 32 + '\t1\t1\n')
        ledger = (b'\x00' * 8 + b'2\n/textures/file with spaces.bin\t' + b'b' * 32
                  + b'\n/optional movie.mp4\t' + b'c' * 32 + b'\n')
        with zipfile.ZipFile(ipa, 'w') as output:
            output.writestr('Payload/RealRacing3.app/res/asset_list_test.txt', manifest)
            if layout is not None:
                output.writestr('Payload/RealRacing3.app/res/gui/processed/Test.gui', eds_crypt(layout))
        with zipfile.ZipFile(cache, 'w') as output:
            output.writestr('Caches/' + folder + 'sprites.ios.atlas', atlas)
            output.writestr('Caches/textures/file with spaces.bin', b'x')
            output.writestr('Caches/asset_list_base.txtCache.txt', ledger)
            output.writestr('__MACOSX/Caches/._bad.ios.atlas', b'not XML')
            if include_page:
                output.writestr('Caches/' + folder + 'sprites_0.rgb.pvr.z', texture() if page_data is None else page_data)
        return ipa, cache

    def test_space_paths_metadata_and_transport_sizes_do_not_create_false_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            result = audit(*self.fixture(directory))
        self.assertEqual(result['base_ledger_paths'], 2)
        self.assertEqual(result['base_ledger_missing'], ['optional movie.mp4'])
        self.assertEqual(result['manifest_unique_paths'], 2)
        for key in ('malformed_manifest_records', 'available_atlas_missing_pages',
                    'invalid_texture_headers', 'out_of_bounds_atlas_images', 'invalid_atlas_xml'):
            self.assertEqual(result[key], [], key)

    def test_missing_page_is_counted_once_and_names_its_background(self):
        with tempfile.TemporaryDirectory() as directory:
            result = audit(*self.fixture(directory, include_page=False))
        self.assertEqual(len(result['available_atlas_missing_pages']), 1)
        self.assertEqual(result['available_atlas_missing_pages'][0]['background_names'], ['background.png'])

    def test_texture_bounds_and_invalid_header_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            result = audit(*self.fixture(directory, x=7))
        self.assertEqual(len(result['out_of_bounds_atlas_images']), 1)
        self.assertEqual(pvr_dimensions(texture(), True), (8, 8))
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            pvr_dimensions(b'bad', False)

    def test_complete_stream_passes_and_audit_limit_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            ipa, cache = self.fixture(directory)
            result = audit(ipa, cache, verify_gui_streams=True)
            limited = audit(ipa, cache, verify_gui_streams=True, max_texture_bytes=100)
        self.assertEqual(result['gui_texture_streams_verified'], 1)
        self.assertEqual(result['invalid_gui_texture_streams'], [])
        self.assertEqual(len(limited['gui_texture_streams_skipped']), 1)
        self.assertEqual(limited['invalid_gui_texture_streams'], [])
        with self.assertRaises(TextureAuditLimit):
            verify_texture_stream(texture(), True, 100)

    def test_corruption_after_a_valid_header_is_detected(self):
        broken = bytearray(texture())
        broken[-1] ^= 1  # Damage the zlib trailer while leaving the PVR header intact.
        self.assertEqual(pvr_dimensions(broken, True), (8, 8))
        with tempfile.TemporaryDirectory() as directory:
            result = audit(*self.fixture(directory, page_data=broken), verify_gui_streams=True)
        self.assertEqual(result['invalid_texture_headers'], [])
        self.assertEqual(len(result['invalid_gui_texture_streams']), 1)
        self.assertEqual(result['gui_texture_streams_verified'], 0)

    def test_pvr_length_mismatch_is_detected_after_valid_zlib(self):
        original = texture()
        payload = zlib.decompress(original[4:])[:-4]
        bad = struct.pack('<I', len(payload)) + zlib.compress(payload)
        self.assertEqual(pvr_dimensions(bad, True), (8, 8))
        with self.assertRaisesRegex(ValueError, 'PVR payload length'):
            verify_texture_stream(bad, True, 1024)

    def test_encrypted_layout_with_separate_animation_documents_is_supported(self):
        layout = (b'<?xml version="1.0"?><Screen><Image image="backgrounds\\background.png"/></Screen>'
                  b'<?xml version="1.0"?><animation><Image image="backgrounds/shade.png"/></animation>')
        self.assertEqual([node.tag for node in gui_documents(eds_crypt(layout))], ['Screen', 'animation'])
        with tempfile.TemporaryDirectory() as directory:
            result = audit(*self.fixture(directory, layout=layout), map_layouts=True)
        self.assertEqual(result['gui_layout_files_decoded'], 1)
        self.assertEqual(result['gui_layout_documents_parsed'], 2)
        self.assertEqual(result['gui_layout_decode_errors'], [])
        self.assertEqual(result['layout_reference_status_counts'], {'hd_sprite_available': 2})

    def test_unresolved_runtime_image_is_reported_but_editor_only_image_is_skipped(self):
        layout = (b'<Screen><Image image="missing/background.png"/>'
                  b'<Image image="editor/placeholder.png" editor_only_image="true"/></Screen>')
        with tempfile.TemporaryDirectory() as directory:
            result = audit(*self.fixture(directory, layout=layout), map_layouts=True)
        self.assertEqual(result['layout_reference_status_counts'], {'unresolved': 1})
        self.assertEqual(result['layout_image_references'][0]['image'], 'missing/background.png')

    def test_zip_crc_failure_is_reported_without_aborting_the_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            ipa, cache = self.fixture(directory)
            page = 'Caches/gui_assets/2048x1536/backgrounds/sprites_0.rgb.pvr.z'
            with zipfile.ZipFile(cache) as archive:
                item = archive.getinfo(page)
                offset, length = item.header_offset, item.compress_size
            with cache.open('r+b') as stream:
                stream.seek(offset + 26)
                name_size, extra_size = struct.unpack('<HH', stream.read(4))
                stream.seek(offset + 30 + name_size + extra_size + length - 1)
                byte = stream.read(1)
                stream.seek(-1, 1)
                stream.write(bytes([byte[0] ^ 1]))
            result = audit(ipa, cache, verify_gui_streams=True)
        self.assertEqual(len(result['invalid_gui_texture_streams']), 1)
        self.assertIn('CRC', result['invalid_gui_texture_streams'][0]['error'])

    def test_a_malformed_style_element_is_not_hidden_by_fragment_parsing(self):
        with self.assertRaises(ET.ParseError):
            gui_documents(eds_crypt(b'<Styles><Colour name="fixture"\r\n</Styles>'))


if __name__ == '__main__':
    unittest.main()
