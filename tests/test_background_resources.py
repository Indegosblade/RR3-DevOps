import hashlib
import struct
import unittest
from unittest.mock import patch

from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import (UC_ARM64_REG_PC, UC_ARM64_REG_LR, UC_ARM64_REG_SP,
    UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_S0,
    UC_ARM64_REG_S1, UC_ARM64_REG_S2, UC_ARM64_REG_S3)

from scripts import trace_background_resources as trace


def adrp(pc, target, register=8):
    immediate = ((target & ~4095) - (pc & ~4095)) // 4096
    value = immediate & 0x1FFFFF
    return 0x90000000 | ((value & 3) << 29) | ((value >> 2) << 5) | register


def draw_calls(flags=8, mode=9, override=-1, gui_present=True):
    """Execute the guarded original callback, mocking only external draw calls."""
    machine = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    entry = trace.BASE + trace.DRAW
    machine.mem_map(entry & ~4095, 4096)
    machine.mem_write(entry, trace.DRAW_CODE)
    data = 0x700000000
    task, gui, view, context, renderer, vtable = [data + index * 4096 for index in range(6)]
    machine.mem_map(data, 6 * 4096)
    machine.mem_write(task + 8, struct.pack('<QQ', view, gui if gui_present else 0))
    machine.mem_write(context + 0x690, struct.pack('<i', mode))
    machine.mem_write(context + 0x698, struct.pack('<i', override))
    global_page = 0x103255000
    machine.mem_map(global_page, 4096)
    machine.mem_write(global_page + 0xE30, struct.pack('<Q', renderer))
    machine.mem_write(renderer, struct.pack('<Q', vtable))
    tint, stop = 0x600000000, 0x600001000
    machine.mem_map(tint, 8192)
    machine.mem_write(vtable + 0x80, struct.pack('<Q', tint))
    machine.mem_map(0x10070D000, 4096)
    machine.mem_map(0x100501000, 4096)
    stack = 0x710000000
    machine.mem_map(stack, 16384)
    machine.reg_write(UC_ARM64_REG_SP, stack + 8192)
    machine.reg_write(UC_ARM64_REG_LR, stop)
    machine.reg_write(UC_ARM64_REG_X0, task)
    machine.reg_write(UC_ARM64_REG_X1, context)
    machine.reg_write(UC_ARM64_REG_X2, flags)
    functions = {tint: 'four_float_draw_state', 0x10070DD40: 'view_begin',
                 0x10050127C: 'gui_draw', 0x10070DD68: 'view_end'}
    calls = []

    def hook(uc, address, size, user):
        if address not in functions:
            return
        call = {'name': functions[address], 'argument': uc.reg_read(UC_ARM64_REG_X0)}
        if address == tint:
            call['floats'] = [struct.unpack('<f', struct.pack('<I', uc.reg_read(register)))[0]
                              for register in (UC_ARM64_REG_S0, UC_ARM64_REG_S1,
                                               UC_ARM64_REG_S2, UC_ARM64_REG_S3)]
        calls.append(call)
        uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))

    machine.hook_add(UC_HOOK_CODE, hook)
    machine.emu_start(entry, stop, count=120)
    return calls, (renderer, view, gui)


class BackgroundTraceTests(unittest.TestCase):
    def test_adjacent_address_decode_resolves_signed_pages_and_rejects_other_registers(self):
        pc = 0x100020008
        for target in (0x100010456, 0x100050ABC):
            first = adrp(pc, target, 8)
            second = 0x91000000 | ((target & 4095) << 10) | (8 << 5) | 1
            self.assertEqual(trace.adrp_add_target(first, second, pc), target)
            self.assertIsNone(trace.adrp_add_target(first, second ^ (1 << 5), pc))
        self.assertIsNone(trace.adrp_add_target(0xD65F03C0, 0x91000000, pc))

    def test_code_guard_detects_changed_instruction_and_uuid(self):
        data = bytearray(trace.DRAW + len(trace.DRAW_CODE))
        struct.pack_into('<8I', data, 0, 0xFEEDFACF, 0x100000C, 0, 2, 1, 24, 0, 0)
        struct.pack_into('<II16s', data, 32, 0x1B, 24, trace.SUPPORTED_MACHO_UUID)
        data[trace.DRAW:trace.DRAW + len(trace.DRAW_CODE)] = trace.DRAW_CODE
        self.assertEqual(hashlib.sha256(trace.DRAW_CODE).hexdigest(), trace.REGIONS['draw'][2])
        with patch.object(trace, 'REGIONS', {'draw': trace.REGIONS['draw']}):
            trace.validate_regions(data)
            data[trace.DRAW] ^= 1
            with self.assertRaisesRegex(ValueError, 'draw'):
                trace.validate_regions(data)
            data[trace.DRAW] ^= 1
            data[40] ^= 1
            with self.assertRaisesRegex(ValueError, 'UUID'):
                trace.validate_regions(data)

    def test_original_draw_callback_obeys_presence_flags_and_context_selector(self):
        for values in ({'flags': 0}, {'gui_present': False}, {'mode': 0},
                       {'mode': 9, 'override': 0}):
            with self.subTest(values=values):
                calls, _ = draw_calls(**values)
                self.assertEqual(calls, [])
        for values in ({}, {'mode': 0, 'override': 9}, {'flags': 0x108}):
            with self.subTest(values=values):
                calls, (renderer, view, gui) = draw_calls(**values)
                self.assertEqual([call['name'] for call in calls],
                                 ['four_float_draw_state', 'view_begin', 'gui_draw', 'view_end'])
                self.assertEqual([call['argument'] for call in calls], [renderer, view, gui, view])
                self.assertEqual(calls[0]['floats'], [1.0, 1.0, 1.0, 1.0])

    def test_same_basename_is_not_a_safe_resource_replacement(self):
        references = [
            {'image': 'ltd_timed_series/missing/lts_bg.png', 'status': 'unresolved',
             'uses': [{'layout': 'event.gui'}],
             'matching_absent_atlas_declarations': [{'path': 'missing/sprites.ios.atlas'}]},
            {'image': 'car_sales/cars/car_sales_car_174.png', 'status': 'unresolved',
             'uses': [{'layout': 'sale.gui'}], 'matching_absent_atlas_declarations': []},
        ]
        result = trace.classify_references(references, {
            'ltd_timed_series/other/lts_bg.png': {'2048x1536'},
            'car_sales/cars/build_310/car_sales_car_174.png': {'2048x1536'},
        })
        first, second = result['references']
        self.assertEqual(first['category'], 'absent_manifest_collection_candidate')
        self.assertFalse(first['automatic_replacement_justified'])
        self.assertEqual(second['category'], 'runtime_car_sale_path_candidates_available')
        self.assertEqual(second['available_car_sale_candidates'], ['car_sales/cars/build_310/car_sales_car_174.png'])
        self.assertFalse(second['automatic_replacement_justified'])
        self.assertEqual(result['same_basename_other_collection_reference_count'], 2)
        self.assertEqual(result['same_basename_limited_time_series_reference_count'], 1)
        self.assertEqual(result['case_only_sprite_reference_count'], 0)


if __name__ == '__main__':
    unittest.main()
