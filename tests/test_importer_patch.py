import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from importer_fix import patch as fixer
from scripts.fix_importer import repair
from build_4k_v3 import BINARY_PATH, SUPPORTED_MACHO_UUID

ROOT = Path(__file__).resolve().parents[1]


class ImporterFormatTests(unittest.TestCase):
    def test_translation_preserves_format_arguments_and_upstream_brand(self):
        words = fixer.translations()
        self.assertEqual(len(words), 149)
        self.assertIn('iPA Store File Assistant', words.values())
        self.assertIn('Import Save & Close', words.values())
        for before, after in words.items():
            self.assertEqual(fixer.FORMATS.findall(before), fixer.FORMATS.findall(after))
            self.assertTrue(after.isascii())

    def test_chained_string_links_and_ascii_representation(self):
        data = bytearray(2048)
        struct.pack_into('<QQQQ', data, 256, 0, 0x7D0, (3 << 51) | 512, 2)
        data[512:516] = '\u4fdd\u5b58'.encode('utf-16le')
        metadata = {'chained': True, 'segments': [{'vm': 0, 'offset': 0, 'size': len(data)}],
                    'sections': {'__DATA:__cfstring': {'offset': 256, 'size': 32}}}
        self.assertEqual(list(fixer.constant_strings(data, metadata))[0][-1], '\u4fdd\u5b58')
        data[600:605] = b'Save\0'
        struct.pack_into('<QQQ', data, 264, 0x7C8, (3 << 51) | 600, 4)
        record = list(fixer.constant_strings(data, metadata))[0]
        self.assertEqual(record[-1], 'Save')
        self.assertEqual(record[2] >> 51, 3)
        struct.pack_into('<Q', data, 272, (1 << 63) | 600)
        with self.assertRaisesRegex(ValueError, 'authenticated'):
            list(fixer.constant_strings(data, metadata))

    def test_overlapping_fat_slices_and_truncated_commands_are_refused(self):
        data = bytearray(256)
        data[:8] = b'\xca\xfe\xba\xbe\0\0\0\x02'
        for index in range(2):
            struct.pack_into('>IIIII', data, 8+index*20, 0x100000C, 0, 64, 128, 0)
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            fixer.slices(data)
        data[:4] = b'\xcf\xfa\xed\xfe'
        struct.pack_into('<III', data, 4, 0x100000C, 0, 6)
        struct.pack_into('<II', data, 16, 100, 8)
        with self.assertRaises(ValueError):
            fixer.image(data)

    def test_native_payload_mismatch_is_rejected_before_parsing_input(self):
        with patch.object(fixer, 'PAYLOAD', b'changed'):
            with self.assertRaisesRegex(ValueError, 'identity'):
                fixer.patch_dylib(b'not an image')

    def test_other_container_configurations_are_refused(self):
        for info in ({}, {'AppDataSavePath': '/Library', 'AppDataDataPath': '/Library', 'AppDataFileTypes': ['dat']}):
            with self.assertRaises(ValueError):
                fixer.validate_config(info)

    @unittest.skipUnless(importlib.util.find_spec('unicorn'), 'Optional Unicorn unavailable')
    def test_trampoline_preserves_stack_and_supplies_relocated_context(self):
        from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
        from unicorn import arm64_const as r
        base, stack, block = 0x123000000, 0x70000000, 0x71000000
        machine = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        machine.mem_map(base, 0x4000)
        machine.mem_map(stack, 0x4000)
        machine.mem_write(base+fixer.TRAMPOLINE, fixer.trampoline(0x3000))
        machine.reg_write(r.UC_ARM64_REG_SP, stack+0x1000)
        machine.reg_write(r.UC_ARM64_REG_X29, stack+0x1070)
        machine.reg_write(r.UC_ARM64_REG_X18, 0x18181818)
        machine.mem_write(stack+0x1008, struct.pack('<Q', block))
        seen = []
        def hook(uc, address, size, context):
            if address == base+fixer.NATIVE+fixer.ENTRY:
                seen.append([uc.reg_read(x) for x in (r.UC_ARM64_REG_X0,r.UC_ARM64_REG_X1,r.UC_ARM64_REG_X2)])
                uc.reg_write(r.UC_ARM64_REG_X0,0)
                uc.reg_write(r.UC_ARM64_REG_PC,uc.reg_read(r.UC_ARM64_REG_X30))
            if address == base+0x3000:
                uc.emu_stop()
        machine.hook_add(UC_HOOK_CODE,hook)
        machine.emu_start(base+fixer.TRAMPOLINE,0,count=100)
        self.assertEqual(seen,[[block,base+fixer.API_TABLE,base]])
        self.assertEqual(machine.reg_read(r.UC_ARM64_REG_SP),stack+0x1000)
        self.assertEqual(machine.reg_read(r.UC_ARM64_REG_X18),0x18181818)
        self.assertEqual(bytes(machine.mem_read(stack+0x105F,1)),b'\0')


class OriginalImporterIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(os.environ.get('RR3_TEST_IPA', ROOT/'959112d6ace07153840144be3201b00f39ec0e91.ipa'))
        if not source.is_file():
            raise unittest.SkipTest('Preserved upstream IPA unavailable')
        with zipfile.ZipFile(source) as archive:
            cls.original = archive.read(fixer.LIBRARY_PATH)

    def test_all_architectures_are_english_and_differences_are_bounded(self):
        changed, report = fixer.patch_dylib(self.original)
        self.assertEqual(len(changed),len(self.original))
        self.assertEqual(len(report),2)
        words = fixer.translations()
        layouts=json.loads((fixer.ROOT/'layouts.json').read_text())
        for offset,size in fixer.slices(self.original):
            before,after=self.original[offset:offset+size],changed[offset:offset+size]
            metadata=fixer.image(before);layout=layouts[metadata['uuid']]
            originals=list(fixer.constant_strings(before,metadata))
            translated=list(fixer.constant_strings(after,metadata))
            self.assertEqual([r[-1] for r in translated],[words.get(r[-1],r[-1]) for r in originals])
            allowed=set(range(fixer.TRAMPOLINE,fixer.PADDING_END))
            allowed.update(range(layout['queue_site'],layout['queue_site']+8))
            allowed.update(range(layout['worker_site'],layout['worker_site']+4))
            for at,flags,pointer,text in originals:
                if text in words:allowed.update(range(at+8,at+32))
            self.assertTrue(all(i in allowed for i,(a,b) in enumerate(zip(before,after)) if a!=b))
        with self.assertRaises(ValueError):fixer.patch_dylib(changed)

    def test_mutations_in_code_metadata_or_occupied_padding_are_refused(self):
        offset,size=fixer.slices(self.original)[0]
        metadata=fixer.image(self.original[offset:offset+size]);layout=json.loads((fixer.ROOT/'layouts.json').read_text())[metadata['uuid']]
        cf=next(s for k,s in metadata['sections'].items() if k.endswith(':__cfstring'))
        for at in (layout['queue_site'],layout['worker_site'],cf['offset']+8,fixer.TRAMPOLINE):
            data=bytearray(self.original);data[offset+at]^=1
            with self.assertRaises(ValueError):fixer.patch_dylib(data)

    def test_archive_helper_changes_only_library_and_preserves_metadata(self):
        parent=ROOT/'investigation';parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='importer-zip-test-',dir=parent) as temporary:
            directory=Path(temporary).resolve()
            self.assertTrue(directory.is_relative_to(parent.resolve()))
            source,target=directory/'source.ipa',directory/'fixed.ipa'
            info={'AppDataSavePath':'/Documents','AppDataDataPath':'/Library','AppDataFileTypes':['dat']}
            with zipfile.ZipFile(source,'w') as archive:
                archive.writestr(fixer.LIBRARY_PATH,self.original)
                archive.writestr('Payload/RealRacing3.app/Info.plist',plistlib.dumps(info))
                main=bytearray(56)
                struct.pack_into('<8I',main,0,0xFEEDFACF,0x100000C,0,2,1,24,0,0)
                struct.pack_into('<II',main,32,0x1B,24)
                main[40:56]=SUPPORTED_MACHO_UUID
                archive.writestr(BINARY_PATH,main)
                kept=zipfile.ZipInfo('Payload/RealRacing3.app/kept.bin',(2020,1,2,3,4,6));kept.external_attr=0o100644<<16
                archive.writestr(kept,b'untouched')
            source_hash=hashlib.sha256(source.read_bytes()).digest()
            repair(source,target)
            with zipfile.ZipFile(source) as old,zipfile.ZipFile(target) as new:
                self.assertEqual(old.namelist(),new.namelist())
                for member in old.infolist():
                    if member.filename!=fixer.LIBRARY_PATH:
                        self.assertEqual(old.read(member),new.read(member.filename))
                    self.assertEqual(member.date_time,new.getinfo(member.filename).date_time)
                    self.assertEqual(member.external_attr,new.getinfo(member.filename).external_attr)
            with self.assertRaises(FileExistsError):repair(source,target)
            self.assertEqual(hashlib.sha256(source.read_bytes()).digest(),source_hash)
            self.assertTrue(directory.is_relative_to(parent.resolve()))
