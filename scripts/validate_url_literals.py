"""Independently inspect shortened URL literals in a built production IPA."""
import argparse
import json
import struct
import zipfile

LOOPBACK = b'http://127.0.0.1/'


def inspect_literals(binary):
    if len(binary) < 32 or struct.unpack_from('<I', binary)[0] != 0xFEEDFACF:
        raise ValueError('Expected a 64-bit little-endian Mach-O')
    segments = []
    literal_section = None
    position = 32
    end = position + struct.unpack_from('<I', binary, 20)[0]
    if end > len(binary):
        raise ValueError('Truncated load commands')
    for _ in range(struct.unpack_from('<I', binary, 16)[0]):
        if position + 8 > end:
            raise ValueError('Truncated load command')
        command, size = struct.unpack_from('<II', binary, position)
        if size < 8 or position + size > end:
            raise ValueError('Invalid load command')
        if command == 0x19:
            if size < 72:
                raise ValueError('Truncated segment')
            segments.append(struct.unpack_from('<QQQQ', binary, position + 24))
            count = struct.unpack_from('<I', binary, position + 64)[0]
            if 72 + count * 80 > size:
                raise ValueError('Truncated sections')
            for index in range(count):
                entry = position + 72 + index * 80
                if binary[entry:entry + 16].split(b'\0')[0] == b'__cfstring':
                    literal_section = struct.unpack_from('<QQI', binary, entry + 32)
        position += size

    def read_address(address, length):
        for base, virtual_size, offset, file_size in segments:
            if base <= address and address + length <= base + file_size:
                start = offset + address - base
                if start + length <= len(binary):
                    return binary[start:start + length]
        return b''

    if literal_section is None:
        raise ValueError('No CFString section')
    _, section_size, section_offset = literal_section
    if section_size % 32 or section_offset + section_size > len(binary):
        raise ValueError('Invalid CFString section')
    results = []
    for offset in range(section_offset, section_offset + section_size, 32):
        _, flags, address, length = struct.unpack_from('<QQQQ', binary, offset)
        if read_address(address, len(LOOPBACK)) == LOOPBACK:
            logical = read_address(address, length)
            results.append({'record_offset': hex(offset), 'logical_length': length,
                            'valid': logical == LOOPBACK, 'contains_nul': b'\0' in logical})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa')
    args = parser.parse_args()
    with zipfile.ZipFile(args.ipa) as archive:
        results = inspect_literals(archive.read('Payload/RealRacing3.app/RealRacing3'))
    print(json.dumps({'ipa': args.ipa, 'literals': results}, indent=2))
    return 0 if len(results) == 5 and all(record['valid'] for record in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
