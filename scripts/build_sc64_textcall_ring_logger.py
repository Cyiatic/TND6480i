#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

from build_tnd480i_candidate import update_n64_crc_6102


R_ZERO = 0
R_A0 = 4
R_A1 = 5
R_A2 = 6
R_A3 = 7
R_T0 = 8
R_T1 = 9
R_T2 = 10
R_T3 = 11
R_T4 = 12
R_SP = 29
R_RA = 31

MAIN_VADDR_BASE = 0x7EFCB4D0
DIAG_CAVE_SIZE = 0x1F00

TEXT_RENDER_ROM_OFF = 0x0E25EC
TEXT_RENDER_FIRST_WORD = 0x27BDFF58
TEXT_RENDER_CONTINUE_ROM_OFF = TEXT_RENDER_ROM_OFF + 4

TEXT_RENDER_GLOW_ROM_OFF = 0x0E321C
TEXT_RENDER_GLOW_FIRST_WORD = 0x27BDFF68
TEXT_RENDER_GLOW_CONTINUE_ROM_OFF = TEXT_RENDER_GLOW_ROM_OFF + 4

SC64_DATA_BUFFER_INTERNAL = 0x05000000
SC64_DATA_BUFFER_CPU_BASE = 0xBFFE0000
RING_RECORD_BASE = 0x0100
RING_RECORD_SIZE = 0x0080
RING_RECORD_MASK = 0x003F
J_TEXT_TRIGGER_ADDR = 0x800584D0


def word(value):
    return value.to_bytes(4, "big")


def ascii_word(text):
    data = text.encode("ascii")
    if len(data) != 4:
        raise ValueError("marker must be exactly four ASCII bytes")
    return int.from_bytes(data, "big")


def lui(rt, imm):
    return 0x3C000000 | (rt << 16) | (imm & 0xFFFF)


def ori(rt, rs, imm):
    return 0x34000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def addiu(rt, rs, imm):
    return 0x24000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def andi(rt, rs, imm):
    return 0x30000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def sll(rd, rt, shamt):
    return (rt << 16) | (rd << 11) | ((shamt & 0x1F) << 6)


def addu(rd, rs, rt):
    return (rs << 21) | (rt << 16) | (rd << 11) | 0x21


def lw(rt, offset, base):
    return 0x8C000000 | (base << 21) | (rt << 16) | (offset & 0xFFFF)


def sw(rt, offset, base):
    return 0xAC000000 | (base << 21) | (rt << 16) | (offset & 0xFFFF)


def j(addr):
    return 0x08000000 | ((addr >> 2) & 0x03FFFFFF)


def nop():
    return 0


def runtime(rom_off):
    return MAIN_VADDR_BASE + rom_off


def write_words(rom, off, words):
    for i, value in enumerate(words):
        rom[off + i * 4:off + i * 4 + 4] = word(value)


def unlock_sc64_regs():
    return [
        lui(R_T0, 0xBFFF),
        sw(R_ZERO, 0x0010, R_T0),
        lui(R_T1, 0x5F55),
        ori(R_T1, R_T1, 0x4E4C),
        sw(R_T1, 0x0010, R_T0),
        lui(R_T1, 0x4F43),
        ori(R_T1, R_T1, 0x4B5F),
        sw(R_T1, 0x0010, R_T0),
    ]


def load_imm(reg, value):
    return [
        lui(reg, value >> 16),
        ori(reg, reg, value & 0xFFFF),
    ]


def make_text_stub(marker_text, continue_rom_off, stack_offsets):
    header_marker = ascii_word("TXLG")
    record_marker = ascii_word(marker_text)
    words = []
    words.extend(unlock_sc64_regs())
    words.extend(load_imm(R_T0, SC64_DATA_BUFFER_CPU_BASE))
    words.extend(load_imm(R_T1, header_marker))
    words.extend([
        sw(R_T1, 0x0000, R_T0),
        lw(R_T1, 0x0004, R_T0),
        andi(R_T2, R_T1, RING_RECORD_MASK),
        sll(R_T2, R_T2, 7),
        addiu(R_T2, R_T2, RING_RECORD_BASE),
        addu(R_T2, R_T2, R_T0),
    ])
    words.extend(load_imm(R_T3, record_marker))
    words.extend([
        sw(R_T3, 0x0000, R_T2),
        sw(R_T1, 0x0004, R_T2),
        sw(R_RA, 0x0008, R_T2),
        sw(R_SP, 0x000C, R_T2),
        sw(R_A0, 0x0010, R_T2),
        sw(R_A1, 0x0014, R_T2),
        lw(R_T3, 0x0000, R_A1),
        sw(R_T3, 0x0018, R_T2),
        sw(R_A2, 0x001C, R_T2),
        lw(R_T3, 0x0000, R_A2),
        sw(R_T3, 0x0020, R_T2),
        sw(R_A3, 0x0024, R_T2),
        lw(R_T3, 0x0000, R_A3),
        sw(R_T3, 0x0028, R_T2),
    ])
    for i, stack_off in enumerate(stack_offsets):
        words.extend([
            lw(R_T3, stack_off, R_SP),
            sw(R_T3, 0x002C + i * 4, R_T2),
        ])
    words.extend(load_imm(R_T3, J_TEXT_TRIGGER_ADDR))
    words.extend([
        lw(R_T4, 0x0000, R_T3),
        sw(R_T4, 0x0048, R_T2),
        addiu(R_T1, R_T1, 1),
        sw(R_T1, 0x0004, R_T0),
        j(runtime(continue_rom_off)),
        nop(),
    ])
    if len(words) * 4 > RING_RECORD_SIZE * 2:
        raise ValueError("unexpectedly large text logging stub")
    return words


def ensure_cave(rom, offset, size):
    if any(rom[offset:offset + size]):
        raise ValueError(f"diagnostic cave is not empty at 0x{offset:X} for 0x{size:X} bytes")


def find_executable_zero_cave(rom, min_size):
    required_nibble = (runtime(TEXT_RENDER_ROM_OFF) >> 28) & 0xF
    start = max(0, 0x7F000000 - MAIN_VADDR_BASE)
    run_start = None
    run_len = 0
    for index in range(start, len(rom)):
        if rom[index] == 0:
            if run_start is None:
                run_start = index
            run_len += 1
            aligned_start = (run_start + 3) & ~3
            aligned_len = index - aligned_start + 1
            if aligned_len >= min_size and ((runtime(aligned_start) >> 28) & 0xF) == required_nibble:
                return aligned_start, aligned_len
        else:
            run_start = None
            run_len = 0
    raise ValueError(f"could not find 0x{min_size:X}-byte zero cave in textRender jump range")


def patch_hook(rom, hook_off, expected_first, stub_off):
    original = int.from_bytes(rom[hook_off:hook_off + 4], "big")
    if original != expected_first:
        raise ValueError(f"unexpected prologue at 0x{hook_off:X}: 0x{original:08X}")
    write_words(rom, hook_off, [
        j(runtime(stub_off)),
        original,
    ])


def build(args):
    base_rom = Path(args.base_rom)
    rom = bytearray(base_rom.read_bytes())

    text_words = make_text_stub(
        "TXTR",
        TEXT_RENDER_CONTINUE_ROM_OFF,
        (0x00B8, 0x00BC, 0x00C0, 0x00C4, 0x00C8, 0x00CC, 0x00D0),
    )
    total_size = (len(text_words) + len(make_text_stub(
        "TXTG",
        TEXT_RENDER_GLOW_CONTINUE_ROM_OFF,
        (0x00A8, 0x00AC, 0x00B0, 0x00B4, 0x00B8, 0x00BC, 0x00C0, 0x00C4),
    ))) * 4
    if total_size > DIAG_CAVE_SIZE:
        raise ValueError(f"diagnostic stubs use 0x{total_size:X}, cave budget is 0x{DIAG_CAVE_SIZE:X}")
    if args.cave_offset is not None:
        diag_cave_rom_off = int(args.cave_offset, 0)
        cave_len = DIAG_CAVE_SIZE
        ensure_cave(rom, diag_cave_rom_off, total_size)
    else:
        diag_cave_rom_off, cave_len = find_executable_zero_cave(rom, total_size)

    text_glow_stub_off = diag_cave_rom_off + len(text_words) * 4
    if text_glow_stub_off & 3:
        raise ValueError("unaligned glow stub")
    glow_words = make_text_stub(
        "TXTG",
        TEXT_RENDER_GLOW_CONTINUE_ROM_OFF,
        (0x00A8, 0x00AC, 0x00B0, 0x00B4, 0x00B8, 0x00BC, 0x00C0, 0x00C4),
    )
    write_words(rom, diag_cave_rom_off, text_words)
    write_words(rom, text_glow_stub_off, glow_words)
    patch_hook(rom, TEXT_RENDER_ROM_OFF, TEXT_RENDER_FIRST_WORD, diag_cave_rom_off)
    patch_hook(rom, TEXT_RENDER_GLOW_ROM_OFF, TEXT_RENDER_GLOW_FIRST_WORD, text_glow_stub_off)
    crc1, crc2 = update_n64_crc_6102(rom)

    out_rom = Path(args.out_rom)
    out_rom.parent.mkdir(parents=True, exist_ok=True)
    out_rom.write_bytes(rom)

    summary = {
        "base_rom": str(base_rom),
        "base_md5": hashlib.md5(base_rom.read_bytes()).hexdigest(),
        "out_rom": str(out_rom),
        "out_md5": hashlib.md5(rom).hexdigest(),
        "n64_crc": [f"0x{crc1:08X}", f"0x{crc2:08X}"],
        "hooks": {
            "textRender": {
                "rom_offset": f"0x{TEXT_RENDER_ROM_OFF:06X}",
                "stub_rom_offset": f"0x{diag_cave_rom_off:06X}",
                "continue_rom_offset": f"0x{TEXT_RENDER_CONTINUE_ROM_OFF:06X}",
                "record_marker": "TXTR",
            },
            "textRenderGlow": {
                "rom_offset": f"0x{TEXT_RENDER_GLOW_ROM_OFF:06X}",
                "stub_rom_offset": f"0x{text_glow_stub_off:06X}",
                "continue_rom_offset": f"0x{TEXT_RENDER_GLOW_CONTINUE_ROM_OFF:06X}",
                "record_marker": "TXTG",
            },
        },
        "cave": {
            "offset": f"0x{diag_cave_rom_off:06X}",
            "runtime": f"0x{runtime(diag_cave_rom_off):08X}",
            "zero_run_bytes": cave_len,
            "total_size": f"0x{total_size:X}",
        },
        "sc64_dump": {
            "address": f"0x{SC64_DATA_BUFFER_INTERNAL:08X}",
            "size": "0x3000",
            "command": f"sc64deployer dump 0x{SC64_DATA_BUFFER_INTERNAL:08X} 0x3000 <path>",
            "parser": "python scripts/parse_sc64_textcall_ring.py <dump> --out-json <report>",
        },
    }
    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Patch textRender/textRenderGlow to write a call ring to the SC64 data buffer.")
    parser.add_argument("--base-rom", required=True)
    parser.add_argument("--out-rom", required=True)
    parser.add_argument("--report")
    parser.add_argument("--cave-offset")
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
