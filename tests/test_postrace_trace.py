"""Execute the guarded timer instructions, including its real tail callback.

The small fixture is a single leaf routine, not a redistributed game binary.
No model of the full result screen or save pipeline is claimed by these tests.
"""
import struct
import unittest

from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X30

from build_4k_v3 import SUPPORTED_MACHO_UUID
from scripts.trace_postrace import (
    BASE, ORIGINAL_TICKS, TIMER_CALL, TIMER_CALLER, TIMER_LIMIT, TIMER_START,
    TIMEOUT_CODE, direct_branch_target, patch_timeout, trace,
)


def fixture():
    binary = bytearray(TIMER_CALLER + 4)
    command_size = 24 + 152
    struct.pack_into('<8I', binary, 0, 0xFEEDFACF, 0x100000C, 0, 2,
                     2, command_size, 0, 0)
    struct.pack_into('<II16s', binary, 32, 0x1B, 24, SUPPORTED_MACHO_UUID)
    struct.pack_into('<II16sQQQQIIII', binary, 56, 0x19, 152, b'__TEXT',
                     BASE, len(binary), 0, len(binary), 7, 5, 1, 0)
    struct.pack_into('<16s16sQQ8I', binary, 128, b'__text', b'__TEXT',
                     BASE + TIMER_CALLER, 4, TIMER_CALLER, 2, 0, 0, 0, 0, 0, 0)
    binary[TIMER_START:TIMER_START + len(TIMEOUT_CODE)] = TIMEOUT_CODE
    binary[TIMER_CALLER:TIMER_CALLER + 4] = TIMER_CALL
    return bytes(binary)


class TimerMachine:
    """Run the original machine code against a controlled helper/closure state."""
    OBJECT = 0x700000000
    CLOSURE = OBJECT + 0x1000
    VTABLE = OBJECT + 0x2000
    CALLBACK = 0x100180000
    RETURN = CALLBACK + 4

    def __init__(self, code=TIMEOUT_CODE, *, pending=1, error=0, elapsed=0, callback=True):
        self.uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self.uc.mem_map((BASE + TIMER_START) & ~4095, 4096)
        self.uc.mem_write(BASE + TIMER_START, code)
        self.uc.mem_map(self.OBJECT, 0x3000)
        self.uc.mem_map(self.CALLBACK, 4096)
        self.uc.mem_write(self.CALLBACK, bytes.fromhex('c0035fd6'))  # ret
        self.uc.mem_write(self.OBJECT + 0xFC, bytes([pending]))
        self.uc.mem_write(self.OBJECT + 0x106, bytes([error]))
        self.uc.mem_write(self.OBJECT + 0x108, struct.pack('<I', elapsed))
        self.uc.mem_write(self.OBJECT + 0x28, struct.pack('<Q', self.CLOSURE if callback else 0))
        self.uc.mem_write(self.CLOSURE, struct.pack('<Q', self.VTABLE))
        self.uc.mem_write(self.VTABLE + 0x30, struct.pack('<Q', self.CALLBACK))
        self.calls = []

        def called(machine, address, size, user):
            if address == self.CALLBACK:
                self.calls.append({'argument': machine.reg_read(UC_ARM64_REG_X0),
                                   'state': self.state()})
        self.uc.hook_add(UC_HOOK_CODE, called)

    def state(self):
        return {'pending': self.uc.mem_read(self.OBJECT + 0xFC, 1)[0],
                'error': self.uc.mem_read(self.OBJECT + 0x106, 1)[0],
                'elapsed': struct.unpack('<I', self.uc.mem_read(self.OBJECT + 0x108, 4))[0]}

    def tick(self, delta):
        self.uc.reg_write(UC_ARM64_REG_X0, self.OBJECT)
        self.uc.reg_write(UC_ARM64_REG_X1, delta)
        self.uc.reg_write(UC_ARM64_REG_X30, self.RETURN)
        self.uc.emu_start(BASE + TIMER_START, self.RETURN, count=64)
        return self.state()


class PostraceTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = fixture()
        cls.changed, cls.plan = patch_timeout(cls.binary, 1000)
        cls.code = cls.changed[TIMER_START:TIMER_START + len(TIMEOUT_CODE)]

    def test_trace_resolves_backward_caller_and_patch_changes_only_the_limit(self):
        report = trace(self.binary)
        self.assertEqual(report['direct_callers'], [hex(BASE + TIMER_CALLER)])
        self.assertEqual(direct_branch_target(0x14000000, 0), None)
        self.assertEqual(self.changed[:TIMER_LIMIT], self.binary[:TIMER_LIMIT])
        self.assertEqual(self.changed[TIMER_LIMIT + 4:], self.binary[TIMER_LIMIT + 4:])
        self.assertTrue(self.plan['experimental'])
        self.assertFalse(self.plan['device_validated'])

    def test_changed_code_uuid_or_caller_is_refused(self):
        for offset in (40, TIMER_START, TIMER_CALLER):
            with self.subTest(offset=offset):
                modified = bytearray(self.binary)
                modified[offset] ^= 1
                with self.assertRaises(ValueError):
                    patch_timeout(bytes(modified), 1000)
        for ticks in (True, 0, -1, ORIGINAL_TICKS, 65536, 1.5):
            with self.subTest(ticks=ticks), self.assertRaises(ValueError):
                patch_timeout(self.binary, ticks)

    def test_inactive_completed_and_error_states_are_preserved(self):
        for pending, error in ((0, 0), (0, 1), (1, 1)):
            for code in (TIMEOUT_CODE, self.code):
                with self.subTest(pending=pending, error=error, candidate=code is self.code):
                    machine = TimerMachine(code, pending=pending, error=error, elapsed=20)
                    self.assertEqual(machine.tick(1000), {'pending': pending, 'error': error, 'elapsed': 20})
                    self.assertEqual(machine.calls, [])

    def test_shorter_wait_uses_the_same_one_shot_error_callback(self):
        original = TimerMachine(elapsed=ORIGINAL_TICKS - 1)
        candidate = TimerMachine(self.code, elapsed=999)
        for machine, limit in ((original, ORIGINAL_TICKS), (candidate, 1000)):
            self.assertEqual(machine.tick(1), {'pending': 0, 'error': 1, 'elapsed': limit})
            self.assertEqual(len(machine.calls), 1)
            self.assertEqual(machine.calls[0]['argument'], machine.CLOSURE)
            self.assertEqual(machine.calls[0]['state'], machine.state())
            machine.tick(1000)  # A later update must not issue completion twice.
            self.assertEqual(len(machine.calls), 1)
        still_waiting = TimerMachine(elapsed=999)
        self.assertEqual(still_waiting.tick(1), {'pending': 1, 'error': 0, 'elapsed': 1000})
        self.assertEqual(still_waiting.calls, [])

    def test_missing_callback_is_safe_and_below_limit_is_unchanged(self):
        for code in (TIMEOUT_CODE, self.code):
            machine = TimerMachine(code, elapsed=0)
            self.assertEqual(machine.tick(16), {'pending': 1, 'error': 0, 'elapsed': 16})
            self.assertEqual(machine.calls, [])
        machine = TimerMachine(self.code, elapsed=999, callback=False)
        self.assertEqual(machine.tick(1), {'pending': 0, 'error': 1, 'elapsed': 1000})
        self.assertEqual(machine.calls, [])


if __name__ == '__main__':
    unittest.main()
