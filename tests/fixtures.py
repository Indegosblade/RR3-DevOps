"""Synthetic Mach-O fixtures; no game executable or device data is included."""
import struct

import build_4k_v3 as builder
import se_compat


def binary_fixture():
    size = 0x2D61200
    data = bytearray(size)
    section_offset = 0x2D50000
    section_size = 0x11140
    segment_size = 152
    commands_size = segment_size + 24
    struct.pack_into('<8I', data, 0, 0xFEEDFACF, 0x100000C, 0, 2, 2, commands_size, 0, 0)
    struct.pack_into('<II16sQQQQIIII', data, 32, 0x19, segment_size, b'__TEXT',
                     se_compat.BASE, size, 0, size, 7, 5, 1, 0)
    struct.pack_into('<16s16sQQ8I', data, 104, b'__cfstring', b'__TEXT',
                     se_compat.BASE + section_offset, section_size, section_offset,
                     3, 0, 0, 0, 0, 0, 0)
    struct.pack_into('<II16s', data, 32 + segment_size, 0x1B, 24, builder.SUPPORTED_MACHO_UUID)
    for offset, expected, replacement, description in builder.PATCHES:
        data[offset:offset + len(expected)] = expected
    literal_pairs = [(0x2D51360, 0x26CB1A2), (0x2D56880, 0x26E787D),
                     (0x2D610E0, 0x26F5B86), (0x2D61100, 0x26F5BAB),
                     (0x2D61120, 0x26F5BD2)]
    for record, text in literal_pairs:
        length = next(len(expected) for offset, expected, _, _ in builder.PATCHES if offset == text)
        struct.pack_into('<QQQQ', data, record, 0, 0x7C8, se_compat.BASE + text, length)
    original = se_compat.original_instructions()
    data[se_compat.SITE:se_compat.SITE + len(original)] = original
    # The untouched five-instruction threshold decision after the detour site.
    # Kept in the synthetic fixture so tests execute the original comparison.
    decision = bytes.fromhex('1f05007128a9417a64a2487aa4c2497a8cf9ff54')
    data[0x680B38:0x680B4C] = decision
    return bytes(data)
