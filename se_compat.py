"""Exact-build GUI asset-family compatibility patch, adapted from hefti.

Copyright (c) 2026 hefti and rr3 contributors.
MIT license: third_party/hefti/LICENSE.
Upstream revision: 6ace28dc541674ac52af074a20116db69bcdfb59.

Only GUI manifest entries receive the 2048x1536 admission ceiling. The physical
framebuffer, global screen-derived values and non-GUI comparisons are preserved.
"""
import struct

UUID = bytes.fromhex('06ed5b50c44c3b69a5840701b8a88451')
BASE = 0x100000000
SITE = 0x680B24
CAVE = 0x3800
RETURN = BASE + 0x680B38


def branch(pc, target):
    delta = target - pc
    if delta % 4 or not -(1 << 27) <= delta < (1 << 27):
        raise ValueError('ARM64 branch is unaligned or out of range')
    return 0x14000000 | ((delta // 4) & 0x3FFFFFF)


def adrp(pc, target, register):
    pages = ((target & ~4095) - (pc & ~4095)) // 4096
    if not -(1 << 20) <= pages < (1 << 20):
        raise ValueError('ARM64 ADRP is out of range')
    value = pages & 0x1FFFFF
    return 0x90000000 | ((value & 3) << 29) | ((value >> 2) << 5) | register


def words(values):
    return struct.pack('<' + 'I' * len(values), *values)


def original_instructions():
    return words([adrp(BASE + SITE, 0x103251000, 8), 0xB94F1508,
                  adrp(BASE + SITE + 8, 0x103251000, 9), 0xB94F1929,
                  0x296F4FB5])


def stub():
    pc = BASE + CAVE
    code = [adrp(pc, 0x103251000, 8), 0xB94F1508,
            adrp(pc + 8, 0x103251000, 9), 0xB94F1929, 0x296F4FB5,
            0x71000AFF]  # cmp w23, #2: GUI scanf parsed two dimensions
    conditional_pc = pc + len(code) * 4
    local_exit = pc + 9 * 4
    code.append(0x54000001 | (((local_exit - conditional_pc) // 4 & 0x7FFFF) << 5))
    code.extend([0x52800000 | (2048 << 5) | 8,
                 0x52800000 | (1536 << 5) | 9])
    code.append(branch(pc + len(code) * 4, RETURN))
    return words(code)


def _uuid(binary):
    if len(binary) < 32 or struct.unpack_from('<I', binary)[0] != 0xFEEDFACF:
        raise ValueError('Not a supported 64-bit Mach-O')
    end = 32 + struct.unpack_from('<I', binary, 20)[0]
    if end > len(binary):
        raise ValueError('Truncated Mach-O load commands')
    offset = 32
    for _ in range(struct.unpack_from('<I', binary, 16)[0]):
        if offset + 8 > end:
            raise ValueError('Truncated Mach-O command')
        command, size = struct.unpack_from('<II', binary, offset)
        if size < 8 or offset + size > end:
            raise ValueError('Invalid Mach-O command size')
        if command == 0x1B and size >= 24:
            return binary[offset + 8:offset + 24]
        offset += size
    raise ValueError('No executable UUID')


def patch(binary):
    """Return a new executable and two guarded operation records."""
    if _uuid(binary) != UUID:
        raise ValueError('Unsupported executable UUID')
    expected = original_instructions()
    if binary[SITE:SITE + len(expected)] != expected:
        raise ValueError('GUI filter original instructions do not match')
    data = stub()
    if len(binary) < CAVE + len(data) or any(binary[CAVE:CAVE + len(data)]):
        raise ValueError('GUI code cave is not unused zero padding')
    header_end = 32 + struct.unpack_from('<I', binary, 20)[0]
    if header_end + 128 > CAVE:
        raise ValueError('Insufficient load-command/code separation')
    output = bytearray(binary)
    changes = []
    for offset, replacement, label in (
        (SITE, words([branch(BASE + SITE, BASE + CAVE)]), 'GUI manifest threshold detour'),
        (CAVE, data, 'GUI-only 2048x1536 ceiling; non-GUI original thresholds'),
    ):
        before = binary[offset:offset + len(replacement)]
        output[offset:offset + len(replacement)] = replacement
        changes.append({'offset': hex(offset), 'original': before.hex(),
                        'replacement': replacement.hex(), 'description': label})
    return bytes(output), changes
