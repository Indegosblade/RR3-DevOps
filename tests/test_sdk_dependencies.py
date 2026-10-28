"""Synthetic linker/metadata fixtures, containing no game or device bytes."""
import contextlib
import hashlib
import io
from pathlib import Path
import plistlib
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts.audit_sdk_dependencies import ARM64, MachO, audit_archive, main


TEXT = 0x100010000
DATA = 0x100020000


def dylib_command(name, weak=False):
    encoded = name.encode() + b'\0'
    size = (24 + len(encoded) + 7) & ~7
    return struct.pack('<6I', 0x80000018 if weak else 0xC, size, 24, 0, 0, 0) + encoded.ljust(size - 24, b'\0')


def segment(name, vm, offset, length, section, section_size, flags=0):
    header = struct.pack('<II16sQQQQIIII', 0x19, 152, name.encode(), vm,
                         length + 0x1000, offset, length, 7, 5, 1, 0)
    entry = struct.pack('<16s16sQQ8I', section.encode(), name.encode(), vm,
                        section_size, offset, 3, 0, 0, flags, 0, 0, 0)
    return header + entry


def macho_fixture(loads=(), symbols=(), rpaths=(), text_size=4, sdk_class=None):
    data = bytearray(0x1400)
    commands = [segment('__TEXT', TEXT, 0x400, 0x800, '__text', text_size, 0x80000400),
                segment('__DATA_CONST', DATA, 0xC00, 0x400, '__objc_classlist', 8 if sdk_class else 0)]
    commands.extend(dylib_command(name, weak) for name, weak in loads)
    for name in rpaths:
        encoded = name.encode() + b'\0'
        size = (12 + len(encoded) + 7) & ~7
        commands.append(struct.pack('<III', 0x8000001C, size, 12) + encoded.ljust(size - 12, b'\0'))
    strings = bytearray(b'\0')
    for index, (name, ordinal, weak) in enumerate(symbols):
        struct.pack_into('<IBBHQ', data, 0x1050 + index * 16, len(strings), 1, 0,
                         ordinal << 8 | (0x40 if weak else 0), 0)
        strings.extend(name.encode() + b'\0')
    data[0x1100:0x1100 + len(strings)] = strings
    commands.append(struct.pack('<6I', 2, 24, 0x1050, len(symbols), 0x1100, len(strings)))
    commands.append(struct.pack('<II16s', 0x1B, 24, b'\x11' * 16))
    blob = b''.join(commands)
    assert len(blob) + 32 <= 0x400
    struct.pack_into('<8I', data, 0, 0xFEEDFACF, ARM64, 0, 2, len(commands), len(blob), 0, 0)
    data[32:32 + len(blob)] = blob
    if sdk_class:
        struct.pack_into('<Q', data, 0xC00, DATA + 0x40)
        struct.pack_into('<Q', data, 0xC40 + 32, DATA + 0x80)
        struct.pack_into('<Q', data, 0xC80 + 24, DATA + 0xC0)
        encoded = sdk_class.encode() + b'\0'
        data[0xCC0:0xCC0 + len(encoded)] = encoded
    return bytes(data)


class MachOTests(unittest.TestCase):
    def test_hard_and_weak_import_ordinals_remain_distinct(self):
        binary = macho_fixture(loads=(('@rpath/A.framework/A', False), ('@rpath/B.framework/B', True)),
                               symbols=(('_required', 1, False), ('_optional', 2, True)))
        report = MachO(binary).report()
        self.assertEqual([item['kind'] for item in report['loads']], ['load', 'weak'])
        self.assertEqual([item['dependency'] for item in report['undefined_symbols']],
                         ['@rpath/A.framework/A', '@rpath/B.framework/B'])
        self.assertEqual([item['weak_reference'] for item in report['undefined_symbols']], [False, True])
        self.assertEqual([item['undefined_symbol_count'] for item in report['loads']], [1, 1])

    def test_virtual_mapping_uses_segment_file_offsets_and_refuses_zero_fill(self):
        image = MachO(macho_fixture(sdk_class='FIRApp'))
        self.assertEqual(image.vm_offset(DATA + 0x40), 0xC40)
        self.assertEqual(image.sdk_classes(), ({'FIRApp': hex(DATA + 0x40)}, 0))
        with self.assertRaisesRegex(ValueError, 'not backed'):
            image.vm_offset(DATA + 0x600)

    def test_unreadable_class_pointer_is_reported_not_guessed(self):
        data = bytearray(macho_fixture(sdk_class='FIRApp'))
        struct.pack_into('<Q', data, 0xC00, 0x7FFFFFFFFFFFFFFF)
        self.assertEqual(MachO(data).sdk_classes(), ({}, 1))

    def test_selected_initialization_method_from_absolute_and_relative_lists(self):
        for relative in (False, True):
            with self.subTest(relative=relative):
                data = bytearray(macho_fixture(sdk_class='FIRApp'))
                struct.pack_into('<Q', data, 0xC80 + 32, DATA + 0x100)
                data[0xD60:0xD60 + len(b'configureCore\0')] = b'configureCore\0'
                data[0xD80:0xD80 + len(b'B16@0:8\0')] = b'B16@0:8\0'
                if relative:
                    struct.pack_into('<II', data, 0xD00, 0xC000000C, 1)
                    entry = DATA + 0x108
                    struct.pack_into('<iii', data, 0xD08, DATA + 0x160 - entry,
                                     DATA + 0x180 - (entry + 4), TEXT + 0x20 - (entry + 8))
                else:
                    struct.pack_into('<IIQQQ', data, 0xD00, 24, 1, DATA + 0x160,
                                     DATA + 0x180, TEXT + 0x20)
                methods = MachO(data).report()['initialization_methods']
                self.assertEqual(methods, [{'class': 'FIRApp', 'selector': 'configureCore',
                                           'class_method': False, 'implementation': hex(TEXT + 0x20),
                                           'type_encoding': 'B16@0:8'}])

    def test_fat_slice_offsets_do_not_leak_into_vm_mapping(self):
        native = macho_fixture(sdk_class='FIRApp')
        other = bytearray(native)
        struct.pack_into('<I', other, 4, 0x01000007)
        fat = bytearray(0x4400)
        struct.pack_into('>II', fat, 0, 0xCAFEBABE, 2)
        struct.pack_into('>IIIII', fat, 8, 0x01000007, 0, 0x1000, len(other), 12)
        struct.pack_into('>IIIII', fat, 28, ARM64, 0, 0x3000, len(native), 12)
        fat[0x1000:0x1000 + len(other)] = other
        fat[0x3000:0x3000 + len(native)] = native
        image = MachO(fat)
        self.assertEqual(image.slice_offset, 0x3000)
        self.assertEqual(image.vm_offset(DATA), 0xC00)
        self.assertIn('FIRApp', image.sdk_classes()[0])

    def test_truncated_dylib_command_is_refused(self):
        data = bytearray(macho_fixture(loads=(('@rpath/A.framework/A', False),)))
        # The dylib follows two 152-byte segment commands. Its name offset must
        # remain inside that command, not accidentally read the next command.
        struct.pack_into('<I', data, 32 + 304 + 8, 0xFFFFFF)
        with self.assertRaisesRegex(ValueError, 'name offset'):
            MachO(data)


def write_ipa(path):
    main = macho_fixture(loads=(('@rpath/A.framework/A', False),),
                         symbols=(('_A', 1, False),),
                         rpaths=('@executable_path/Frameworks',), sdk_class='FIRApp')
    images = {'A': macho_fixture(loads=(('@rpath/B.framework/B', False),), symbols=(('_B', 1, False),)),
              'B': macho_fixture(loads=(('@rpath/Missing.framework/Missing', True),)),
              'Spare': macho_fixture(text_size=0)}
    root = 'Payload/Test.app/'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(root + 'Info.plist', plistlib.dumps({'CFBundleExecutable': 'Main'}))
        archive.writestr(root + 'Main', main)
        for name, binary in images.items():
            folder = root + 'Frameworks/' + name + '.framework/'
            archive.writestr(folder + 'Info.plist', plistlib.dumps({'CFBundleExecutable': name}))
            archive.writestr(folder + name, binary)


class PackageTests(unittest.TestCase):
    def test_transitive_dependency_is_reachable_without_a_direct_main_import(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.ipa'
            write_ipa(path)
            before = path.read_bytes()
            report = audit_archive(path)
            frameworks = {Path(item['path']).name: item for item in report['frameworks']}
            self.assertTrue(frameworks['A.framework']['reachable_from_main'])
            self.assertTrue(frameworks['B.framework']['reachable_from_main'])
            self.assertFalse(frameworks['Spare.framework']['reachable_from_main'])
            self.assertEqual(report['summary']['zero_text_frameworks'], 1)
            missing = [edge for edge in report['edges'] if 'Missing.framework' in edge['name']]
            self.assertEqual([(edge['kind'], edge['resolution']) for edge in missing], [('weak', 'unresolved')])
            self.assertEqual(report['sdk_class_owners']['FIRApp'], ['Payload/Test.app/Main'])
            self.assertEqual(report['input_sha256'], hashlib.sha256(before).hexdigest())
            self.assertEqual(path.read_bytes(), before)

    def test_cli_refuses_to_overwrite_the_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.ipa'
            write_ipa(path)
            before = path.read_bytes()
            with patch('sys.argv', ['audit', str(path), '--output', str(path)]):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
                    main()
            self.assertEqual(result.exception.code, 2)
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
