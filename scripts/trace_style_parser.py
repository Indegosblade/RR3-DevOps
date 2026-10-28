"""Read-only exact-build GUI style rejection and optional ARM64 execution probe.

Extracts code/resources from the user's preserved original IPA at runtime. No
binary fixture, asset mutation, device access, or whole-game rendering claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from build_4k_v3 import BINARY_PATH, eds_crypt
from scripts.audit_sdk_dependencies import MachO
from scripts.repair_gui_layout import (RESOURCE_PATH, SUPPORTED_RESOURCE_SHA256,
                                       BROKEN_ELEMENT, REPAIRED_ELEMENT)

SUPPORTED_EXECUTABLE_SHA256 = '05f85ca03a46ae326774fc5960c6f7d0e6a8d03a6480e168a65882d6fbeb3a0f'
GLOBAL_PATH = 'Payload/RealRacing3.app/res/gui/processed/GlobalStyles.gui'
GLOBAL_PLAINTEXT_SHA256 = '6f128529b7b7d03d8c3d6716376a2443dac5519c9b3f755f9f096792cc424720'


def validate_binary(binary):
    if hashlib.sha256(binary).hexdigest() != SUPPORTED_EXECUTABLE_SHA256:
        raise ValueError('Expected preserved original executable SHA-256; refusing changed code')
    return MachO(binary)


def compare_colours(local_xml, global_xml):
    """Host XML is used only for value comparison, never engine acceptance."""
    local, global_root = ET.fromstring(local_xml), ET.fromstring(global_xml)
    global_colours = {node.get('name'): node for node in global_root.iter('Colour')}
    result = []
    for node in local.iter('Colour'):
        name = node.get('name')
        other = global_colours.get(name)
        def rgba(element):
            if element is None:
                return None
            return [int(element.get(key, '255' if key == 'a' else '0'))
                    for key in ('r', 'g', 'b', 'a')]
        own, default = rgba(node), rgba(other)
        result.append({'name': name, 'local_rgba': own, 'global_rgba': default,
                       'differs_from_global': own != default})
    return result


class EngineProbe:
    """Original ARM64 instructions with bounded, fail-closed libc/file hooks."""
    STOP = 0x200000000
    DOC = 0x200001000
    RESULT = 0x200002000
    BUFFER = 0x200010000
    STACK = 0x3000FF000

    def __init__(self, binary):
        from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
        from unicorn import arm64_const as registers
        self.r = registers
        self.image = validate_binary(binary)
        self.u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        for vm, virtual_size, offset, file_size in self.image.segments:
            if vm:
                self.u.mem_map(vm, (virtual_size + 4095) & ~4095)
                self.u.mem_write(vm, binary[offset:offset + file_size])
        self.u.mem_map(self.STOP, 0x1000000)
        self.u.mem_map(0x300000000, 0x100000)
        self.u.reg_write(registers.UC_ARM64_REG_CPACR_EL1, 0x300000)
        self.u.reg_write(registers.UC_ARM64_REG_SP, self.STACK)
        # Resolve the otherwise unbound stack-protector GOT slot in emulated RAM.
        self.u.mem_write(0x102B56A20, struct.pack('<Q', 0x200003000))
        self.heap = 0x200100000
        self.instructions = 0
        self.events = []
        self.encrypted = b''
        self.u.hook_add(UC_HOOK_CODE, self._hook)

    def reg(self, name):
        return self.u.reg_read(getattr(self.r, 'UC_ARM64_REG_' + name.upper()))

    def setreg(self, name, value):
        self.u.reg_write(getattr(self.r, 'UC_ARM64_REG_' + name.upper()), value)

    def cstring(self, address):
        data = bytes(self.u.mem_read(address, 4096))
        end = data.find(b'\0')
        if end < 0:
            raise ValueError('Unterminated emulated string')
        return data[:end]

    def _hook(self, uc, address, size, user):
        self.instructions += 1
        if address == self.STOP:
            uc.emu_stop()
            return
        if address in (0x10061978C, 0x102272588, 0x102270F2C):
            amount = self.reg('x0')
            if amount > 0x100000:
                raise ValueError('Emulated allocation exceeds probe bound')
            pointer = self.heap
            self.heap += (max(amount, 1) + 31) & ~31
            if self.heap >= 0x200F00000:
                raise ValueError('Emulated heap exhausted')
            self.setreg('x0', pointer)
        elif address in (0x100619790, 0x10227182C, 0x102270EFC, 0x102270F08):
            pass  # No address reuse is needed during these bounded probes.
        elif address in (0x1022725B8, 0x1022725C4):
            dst, src, length = self.reg('x0'), self.reg('x1'), self.reg('x2')
            if length > 0x100000:
                raise ValueError('Emulated copy exceeds probe bound')
            uc.mem_write(dst, bytes(uc.mem_read(src, length)))
        elif address == 0x1022731AC:
            self.setreg('x0', len(self.cstring(self.reg('x0'))))
        elif address == 0x1004FDD68:
            # Resource lookup/decompression is outside this probe. Supply the
            # actual encrypted member and actual length; original crypto runs.
            uc.mem_write(self.reg('x2'), struct.pack('<I', len(self.encrypted)))
            uc.mem_write(0x200080000, self.encrypted)
            self.setreg('x0', 0x200080000)
            self.events.append('encrypted_resource_supplied')
        elif address == 0x100061298:
            self.events.append('xml_load_error_logged')
        elif address == 0x100530E50:
            # This records admission to style ingestion, without pretending the
            # renderer or style-manager implementation has run.
            self.events.append('local_style_ingestion_called')
        elif address >= 0x102260000:
            raise ValueError(f'Unmodeled external call {address:#x}, LR={self.reg("lr"):#x}')
        else:
            return
        self.setreg('pc', self.reg('lr'))

    def call(self, address, arguments=(), result=None):
        for index, value in enumerate(arguments):
            self.setreg('x' + str(index), value)
        if result is not None:
            self.setreg('x8', result)
        self.setreg('lr', self.STOP)
        self.u.emu_start(address, 0, count=1000000)
        if self.reg('pc') != self.STOP:
            raise ValueError('Original instructions did not finish within probe bound')
        return self.reg('x0')

    def parse(self, plaintext):
        self.call(0x1006162F8, [self.DOC])
        self.u.mem_write(self.BUFFER, plaintext + b'\0')
        before = self.instructions
        self.call(0x1006163F8, [self.DOC, self.BUFFER, len(plaintext), 0x74, 0], self.RESULT)
        status, offset, encoding = struct.unpack('<I4xqI', bytes(self.u.mem_read(self.RESULT, 20)))
        accepted = self.call(0x1006162C0, [self.RESULT])
        description_ptr = self.call(0x1006162D0, [self.RESULT])
        return {'status': status, 'offset': offset, 'encoding': encoding,
                'accepted': bool(accepted), 'description': self.cstring(description_ptr).decode(),
                'original_instructions_executed': self.instructions - before}

    def load(self, encrypted):
        self.encrypted = encrypted
        self.call(0x1006162F8, [self.DOC])
        # libc++ short strings: payload inline, length in the last byte.
        self.u.mem_write(0x200004000, b'path' + b'\0' * 19 + b'\x04')
        self.u.mem_write(0x200005000, b'LocalStyles.xml' + b'\0' * 8 + b'\x0f')
        before = self.instructions
        accepted = self.call(0x1005042A8, [0x200004000, 0x200005000, self.DOC, 1])
        # Execute the original LocalStyles consumer decision/setup instructions.
        # Stop at the two original loop-continuation sites after its decision.
        from unicorn import UC_HOOK_CODE
        def continuation(uc, address, size, user):
            if address in (0x1005310F0, 0x1005310F4):
                uc.emu_stop()
        hook = self.u.hook_add(UC_HOOK_CODE, continuation)
        self.setreg('x0', accepted)
        self.setreg('x21', 0x200005000)
        self.setreg('x26', 15)
        self.setreg('x20', 0x200006000)
        self.u.emu_start(0x10053111C, 0, count=1000)
        self.u.hook_del(hook)
        if self.reg('pc') not in (0x1005310F0, 0x1005310F4):
            raise ValueError('Consumer decision did not reach original loop continuation')
        return {'loader_accepted': bool(accepted), 'events': list(self.events),
                'local_style_ingestion_called': 'local_style_ingestion_called' in self.events,
                'original_instructions_executed': self.instructions - before}


def audit(ipa, emulate=False):
    with zipfile.ZipFile(ipa) as archive:
        binary = archive.read(BINARY_PATH)
        image = validate_binary(binary)
        encrypted = archive.read(RESOURCE_PATH)
        if hashlib.sha256(encrypted).hexdigest() != SUPPORTED_RESOURCE_SHA256:
            raise ValueError('Expected exact original malformed style resource')
        plaintext = eds_crypt(encrypted)
        if plaintext.count(BROKEN_ELEMENT) != 1:
            raise ValueError('Expected one exact broken element')
        repaired = plaintext.replace(BROKEN_ELEMENT, REPAIRED_ELEMENT, 1)
        global_xml = eds_crypt(archive.read(GLOBAL_PATH))
        if hashlib.sha256(global_xml).hexdigest() != GLOBAL_PLAINTEXT_SHA256:
            raise ValueError('Expected preserved GlobalStyles resource')
    colours = compare_colours(repaired, global_xml)
    report = {
        'scope': 'Exact-build static call chain, resource comparison, optional original ARM64 probes',
        'executable_sha256': SUPPORTED_EXECUTABLE_SHA256,
        'resource': RESOURCE_PATH, 'resource_sha256': SUPPORTED_RESOURCE_SHA256,
        'parser': {'load_buffer': '0x1006163f8', 'flags': '0x74',
                   'success_test': '0x1006162c0: status == 0',
                   'source_identity': 'parse core 0x100617348 -> node allocator 0x100615c24 -> page allocator 0x10061829c; assertion at0x100618384 references pugixml.cpp',
                   'description_table': '0x102bd0578',
                   'status_11': image.vm_string(image.vm_pointer(0x102BD0578 + 11 * 8))},
        'call_chain': [
            '0x100531118/0x100531130: LocalStyles.xml -> path-specific loader 0x100504624',
            '0x100504754: -> 0x1005042a8 (resource read, original inline decryption)',
            '0x1005045b4: -> parser 0x1006163f8 with flags0x74',
            '0x1005045c4/0x1005045c8: test status; error -> log, return0',
            '0x10053111c/0x100531134: false -> next directory, skipping ingestion',
            '0x100531160: successful load -> style ingestion 0x100530e50',
            '0x100530ed8: Colours -> color ingestion 0x100531720',
            '0x100530d40/0x100530d70: GlobalStyles uses same parser and ingestion, global mode1',
        ],
        'colours': colours,
        'colour_count': len(colours),
        'colours_different_from_global': sum(item['differs_from_global'] for item in colours),
        'limits': [
            'No live event selection, actual resource path resolution, rendering, signing, or device execution.',
            'Failure skips this entire local style file; other active local style layers may still affect final colors.',
            'Host ElementTree is only used to compare repaired local values with global values.',
            'Consumer probe records the call boundary; it does not run style ingestion or renderer.',
        ],
    }
    if emulate:
        report['execution'] = {}
        for label, plain, crypt in [('original', plaintext, encrypted),
                                   ('repaired', repaired, eds_crypt(repaired))]:
            parser_probe = EngineProbe(binary)
            loader_probe = EngineProbe(binary)
            report['execution'][label] = {'parser': parser_probe.parse(plain),
                                          'loader_and_consumer': loader_probe.load(crypt)}
        report['execution_hooks'] = [
            'bounded malloc/new, non-reusing free/delete, memcpy/memmove, strlen',
            'resource reader returns actual encrypted IPA member and actual size',
            'XML logging sink; style-ingestion call recorded without executing its body',
            'stack-protector GOT slot resolved to synthetic emulated memory',
        ]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa', type=Path)
    parser.add_argument('--emulate', action='store_true', help='Execute original ARM64 code with Unicorn')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output and args.output.resolve() == args.ipa.resolve():
        parser.error('Report must not overwrite source IPA')
    report = audit(args.ipa, args.emulate)
    text = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
