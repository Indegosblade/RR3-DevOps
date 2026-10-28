"""Guarded repair/translation only; the AppData importer remains upstream work."""
import hashlib
import json
from pathlib import Path
import re
import struct

from importer_fix.payload import ENTRY, PAYLOAD, PAYLOAD_SHA256, SOURCE_SHA256

ROOT = Path(__file__).resolve().parent
LIBRARY_PATH = 'Payload/RealRacing3.app/Frameworks/AppData.dylib'
TRAMPOLINE = 0x1100
API_TABLE = 0x1140
STRINGS = 0x1240
NATIVE = 0x2000
PADDING_END = 0x4000
API_NAMES = (
    '_NSTemporaryDirectory', '_malloc', '_free', '_fopen', '_fread', '_fclose',
    '_crc32', '_dlsym', '_unzOpen64', '_unzGoToFirstFile', '_unzGetCurrentFileInfo64',
    '_unzOpenCurrentFile', '_unzReadCurrentFile', '_unzCloseCurrentFile',
    '_unzGoToNextFile', '_unzClose', '_objc_msgSend$UTF8String',
    '_objc_msgSend$stringWithUTF8String:', '_objc_msgSend$stringByAppendingPathComponent:',
    '_objc_msgSend$defaultManager', '_objc_msgSend$fileExistsAtPath:',
    '_objc_msgSend$createDirectoryAtPath:withIntermediateDirectories:attributes:error:',
    '_objc_msgSend$copyItemAtPath:toPath:error:', '_objc_msgSend$removeItemAtPath:error:',
    '_objc_msgSend$strictExtractZipArchiveAtPath:toDestination:progressBlock:',
    'NSString class reference', 'NSFileManager class reference', 'arm64e authentication',
)
FORMATS = re.compile(r'%(?:\d+\$)?[-+ #0]*\d*(?:\.\d+)?(?:hh|ll|[hljztL])?[@diuoxXfFeEgGaAcCsSp%]')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def translations():
    result = json.loads((ROOT / 'english.json').read_text(encoding='utf-8'))
    if len(result) != 149:
        raise ValueError('Expected all 149 inherited Chinese messages')
    for old, new in result.items():
        if not new or '\0' in new or FORMATS.findall(old) != FORMATS.findall(new):
            raise ValueError('Translation changed a format argument or is empty')
        new.encode('ascii')
    return result


def slices(data):
    if data[:4] == b'\xcf\xfa\xed\xfe':
        return [(0, len(data))]
    if data[:4] != b'\xca\xfe\xba\xbe' or len(data) < 8:
        raise ValueError('Expected the supported 64-bit Mach-O library')
    count = struct.unpack_from('>I', data, 4)[0]
    if not 1 <= count <= 8 or 8 + count * 20 > len(data):
        raise ValueError('Invalid universal architecture table')
    result = []
    for index in range(count):
        cpu, _, offset, size, alignment = struct.unpack_from('>IIIII', data, 8 + index * 20)
        if cpu != 0x100000C or alignment > 24 or offset % (1 << alignment):
            raise ValueError('Unexpected architecture/alignment')
        if offset < 8 + count * 20 or size < 32 or offset + size > len(data):
            raise ValueError('Invalid architecture extent')
        if any(offset < old + length and old < offset + size for old, length in result):
            raise ValueError('Overlapping architecture extents')
        result.append((offset, size))
    return result


def image(data):
    if len(data) < 32 or data[:4] != b'\xcf\xfa\xed\xfe':
        raise ValueError('Expected a little-endian 64-bit Mach-O')
    cpu, subtype = struct.unpack_from('<II', data, 4)
    if cpu != 0x100000C:
        raise ValueError('Expected ARM64')
    count, commands = struct.unpack_from('<II', data, 16)
    end = 32 + commands
    if end > len(data) or count > commands // 8:
        raise ValueError('Invalid load commands')
    sections, segments, uuid, chained = {}, [], None, False
    position = 32
    for _ in range(count):
        if position + 8 > end:
            raise ValueError('Truncated load command')
        command, size = struct.unpack_from('<II', data, position)
        if size < 8 or position + size > end:
            raise ValueError('Invalid load command extent')
        if command == 0x1B:
            if size != 24:
                raise ValueError('Invalid UUID')
            uuid = data[position + 8:position + 24].hex()
        elif command == 0x80000034:
            chained = True
        elif command == 0x19:
            if size < 72:
                raise ValueError('Truncated segment')
            name = data[position + 8:position + 24].split(b'\0')[0].decode('ascii')
            vm, virtual, offset, length, _, protection, nsects = struct.unpack_from('<QQQQiiI', data, position + 24)
            if offset + length > len(data) or 72 + 80 * nsects > size:
                raise ValueError('Invalid segment/sections')
            segments.append({'name': name, 'vm': vm, 'virtual': virtual, 'offset': offset,
                             'size': length, 'protection': protection})
            for ordinal in range(nsects):
                at = position + 72 + ordinal * 80
                section_name = data[at:at + 16].split(b'\0')[0].decode('ascii')
                address, length, offset = struct.unpack_from('<QQI', data, at + 32)
                flags = struct.unpack_from('<I', data, at + 64)[0]
                if flags & 255 not in (1, 0x12) and offset + length > len(data):
                    raise ValueError('Section exceeds input')
                sections[name + ':' + section_name] = {'address': address, 'size': length,
                                                       'offset': offset, 'flags': flags}
        position += size
    if position != end or uuid is None:
        raise ValueError('Load-command size/UUID mismatch')
    return {'uuid': uuid, 'subtype': subtype, 'header_end': end,
            'segments': segments, 'sections': sections, 'chained': chained}


def vm_offset(metadata, address, size=1):
    for segment in metadata['segments']:
        if segment['vm'] <= address and address + size <= segment['vm'] + segment['size']:
            return segment['offset'] + address - segment['vm']
    raise ValueError('Unbacked virtual address')


def constant_strings(data, metadata):
    section = next((s for key, s in metadata['sections'].items() if key.endswith(':__cfstring')), None)
    if section is None or section['size'] % 32:
        raise ValueError('Invalid constant-string section')
    for at in range(section['offset'], section['offset'] + section['size'], 32):
        _, flags, pointer, count = struct.unpack_from('<QQQQ', data, at)
        target = pointer
        if metadata['chained']:
            if pointer >> 62 or ((pointer >> 43) & 255):
                raise ValueError('Unsupported authenticated/bound string-data pointer')
            target &= (1 << 43) - 1
        width = 2 if flags & 0x10 else 1
        if count > len(data) // width:
            raise ValueError('Invalid string length')
        offset = vm_offset(metadata, target, count * width)
        text = data[offset:offset + count * width].decode('utf-16le' if width == 2 else 'utf-8')
        yield at, flags, pointer, text


def branch(source, target, link=False):
    delta = target - source
    if delta % 4 or not -(1 << 27) <= delta < (1 << 27):
        raise ValueError('Branch range/alignment')
    return (0x94000000 if link else 0x14000000) | ((delta // 4) & 0x3FFFFFF)


def adrp(register, source, target):
    pages = (target >> 12) - (source >> 12)
    if not -(1 << 20) <= pages < (1 << 20):
        raise ValueError('ADRP range')
    return 0x90000000 | ((pages & 3) << 29) | (((pages >> 2) & 0x7FFFF) << 5) | register


def trampoline(resume):
    return struct.pack('<7I',
        0xF94007E0,  # LDR x0, [sp,#8]: original captured block
        adrp(1, TRAMPOLINE + 4, API_TABLE),
        0x91000021 | ((API_TABLE & 4095) << 10),
        adrp(2, TRAMPOLINE + 12, 0),  # live module base; table values are offsets
        branch(TRAMPOLINE + 16, NATIVE + ENTRY, True),
        0x381EF3A0,  # STURB w0,[x29,#-17]: original failure result slot
        branch(TRAMPOLINE + 24, resume))


def validate_config(info):
    if (info.get('AppDataSavePath') != '/Documents' or info.get('AppDataDataPath') != '/Library'
            or info.get('AppDataFileTypes') != ['dat']):
        raise ValueError('Expected the inherited RR3 Documents-save/Library-cache configuration')


def patch_dylib(original):
    if sha256(PAYLOAD) != PAYLOAD_SHA256 or sha256((ROOT / 'native.c').read_text(encoding='utf-8').encode()) != SOURCE_SHA256:
        raise ValueError('Native payload/source identity mismatch; regenerate payload')
    if NATIVE + len(PAYLOAD) > PADDING_END:
        raise ValueError('Native payload exceeds guarded padding')
    english = translations()
    layouts = json.loads((ROOT / 'layouts.json').read_text())
    output = bytearray(original)
    records = []
    for offset, size in slices(original):
        before = original[offset:offset + size]
        metadata = image(before)
        layout = layouts.get(metadata['uuid'])
        if layout is None or metadata['subtype'] != layout['subtype']:
            raise ValueError('Unsupported AppData build/architecture')
        for guard in layout['guards']:
            key, expected = guard['section'], guard['sha256']
            section = metadata['sections'].get(key)
            if section is None or sha256(before[section['offset']:section['offset'] + section['size']]) != expected:
                raise ValueError('Changed original AppData section: ' + key)
        text = next((s for s in metadata['segments'] if s['name'] == '__TEXT'), None)
        first = min(s['offset'] for s in metadata['sections'].values() if s['offset'])
        if (metadata['header_end'] > TRAMPOLINE or first != PADDING_END or text is None
                or text['vm'] != 0 or text['offset'] != 0 or not text['protection'] & 4
                or text['size'] < PADDING_END or any(before[TRAMPOLINE:PADDING_END])):
            raise ValueError('Header padding is occupied or lacks the expected executable mapping')
        if len(layout['api']) != len(API_NAMES) or API_TABLE + 8 * len(API_NAMES) > STRINGS:
            raise ValueError('Native API table shape changed')
        after = bytearray(before)
        after[TRAMPOLINE:TRAMPOLINE + 28] = trampoline(layout['failure_resume'])
        struct.pack_into('<' + 'Q' * len(API_NAMES), after, API_TABLE, *layout['api'])
        after[NATIVE:NATIVE + len(PAYLOAD)] = PAYLOAD
        queue = layout['queue_site']
        slot = layout['main_queue_slot']
        struct.pack_into('<II', after, queue, adrp(0, queue, slot), 0xF9400000 | ((slot & 4095) // 8 << 10))
        struct.pack_into('<I', after, layout['worker_site'], branch(layout['worker_site'], TRAMPOLINE))
        position, translated = STRINGS, []
        for at, flags, pointer, text in constant_strings(before, metadata):
            if text not in english:
                if any('\u4e00' <= ch <= '\u9fff' for ch in text):
                    raise ValueError('Untranslated inherited message')
                continue
            encoded = english[text].encode('ascii') + b'\0'
            if position + len(encoded) > NATIVE:
                raise ValueError('English messages exceed guarded string padding')
            after[position:position + len(encoded)] = encoded
            changed_pointer = ((pointer & ~((1 << 43) - 1)) | position) if metadata['chained'] else position
            struct.pack_into('<QQQ', after, at + 8, (flags & ~0x18) | 8, changed_pointer, len(encoded)-1)
            translated.append(text)
            position += len(encoded)
        if set(translated) != set(english) or len(translated) != 149:
            raise ValueError('Unexpected inherited message coverage')
        if any(any('\u4e00' <= ch <= '\u9fff' for ch in text) for _, _, _, text in constant_strings(after, metadata)):
            raise ValueError('Chinese logical constant strings remain')
        output[offset:offset + size] = after
        records.append({'uuid': metadata['uuid'], 'arm64e': bool(layout['api'][-1]),
                        'translated_messages': len(translated), 'native_payload_sha256': PAYLOAD_SHA256,
                        'main_queue_save_application': True, 'cache_worker_changed': False})
    return bytes(output), records
