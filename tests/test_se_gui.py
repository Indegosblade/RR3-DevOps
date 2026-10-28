"""ARM64 admission tests adapted from hefti's MIT-licensed test_patch.py."""
import struct
import unittest

from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X29, UC_ARM64_REG_W23, UC_ARM64_REG_W8, UC_ARM64_REG_W9

from fixtures import binary_fixture
from se_compat import patch, BASE, CAVE, SITE


def execute(data, screen, family, gui):
    machine = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    machine.mem_map(BASE, 0x10000)
    machine.mem_write(BASE + CAVE, data[CAVE:CAVE + 80])
    page = (BASE + SITE) & ~4095
    machine.mem_map(page, 4096)
    machine.mem_write(BASE + SITE, data[SITE:SITE + 64])
    machine.mem_map(0x103251000, 4096)
    machine.mem_write(0x103251F14, struct.pack('<II', *screen))
    stack = 0x700000000
    machine.mem_map(stack, 0x4000)
    frame = stack + 0x2000
    machine.reg_write(UC_ARM64_REG_X29, frame)
    machine.mem_write(frame - 0x88, struct.pack('<II', family[1], family[0]))
    machine.reg_write(UC_ARM64_REG_W23, 2 if gui else 0)
    reached = []

    def stop(uc, address, size, user):
        if address in (BASE + 0x680A78, BASE + 0x680B4C):
            reached.append(address)
            uc.emu_stop()

    machine.hook_add(UC_HOOK_CODE, stop)
    machine.emu_start(BASE + SITE, BASE + 0x680B50, count=40)
    if len(reached) != 1:
        raise AssertionError('Gate did not reach its original decision')
    return reached[0] == BASE + 0x680B4C, (machine.reg_read(UC_ARM64_REG_W8), machine.reg_read(UC_ARM64_REG_W9))


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = binary_fixture()
        cls.patched, _ = patch(cls.original)

    def test_fifty_original_and_patched_gate_cases(self):
        for screen in ((1334, 750), (750, 1334), (2048, 1536), (2796, 1290), (0, 0)):
            for family in ((480, 320), (960, 640), (2048, 1536), (4096, 3072), (1440, 900)):
                for gui in (False, True):
                    with self.subTest(screen=screen, family=family, gui=gui):
                        original, original_limits = execute(self.original, screen, family, gui)
                        changed, changed_limits = execute(self.patched, screen, family, gui)
                        if gui:
                            self.assertEqual(changed_limits, (2048, 1536))
                            self.assertEqual(changed, not (family[0] > 2048 and family[1] > 1536))
                        else:
                            self.assertEqual((changed, changed_limits), (original, original_limits))

    def test_refuses_changed_site_and_occupied_cave(self):
        changed = bytearray(self.original)
        changed[SITE] ^= 1
        with self.assertRaisesRegex(ValueError, 'instructions'):
            patch(bytes(changed))
        changed = bytearray(self.original)
        changed[CAVE] = 1
        with self.assertRaisesRegex(ValueError, 'padding'):
            patch(bytes(changed))


if __name__ == '__main__':
    unittest.main()
