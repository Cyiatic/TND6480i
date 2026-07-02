#!/usr/bin/env python3
"""Patch textRender/textRenderGlow to log call arguments into RDRAM.

Unlike the SC64 logger, this does not require USB/AUX transport.  The game
writes records into a ROM-code cave that is writable after the game is loaded.
After running in Gopher64, dump RDRAM and parse it by scanning for the TXLR
header.  This gives a deterministic comparison of GE480i vs TND6480i text draw
arguments.
"""

from __future__ import annotations

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
TEXT_RENDER_ROM_OFF = 0x0E25EC
TEXT_RENDER_FIRST_WORD = 0x27BDFF58
TEXT_RENDER_CONTINUE_ROM_OFF = TEXT_RENDER_ROM_OFF + 4
TEXT_RENDER_GLOW_ROM_OFF = 0x0E321C
TEXT_RENDER_GLOW_FIRST_WORD = 0x27BDFF68
TEXT_RENDER_GLOW_CONTINUE_ROM_OFF = TEXT_RENDER_GLOW_ROM_OFF + 4

RING_HEADER_SIZE = 0x100
RING_RECORD_SIZE = 0x80
RING_RECORD_COUNT = 32
RING_RECORD_MASK = RING_RECORD_COUNT - 1
RING_TOTAL_SIZE = RING_HEADER_SIZE + RING_RECORD_SIZE * RING_RECORD_COUNT
STUB_GLOW_DELTA = 0x300
RING_DELTA = 0x800
MIN_CAVE_SIZE = RING_DELTA + RING_TOTAL_SIZE


def word(value: int) -> bytes:
    return value.to_bytes(4, "big")


def ascii_word(text: str) -> int:
    raw = text.encode("ascii")
    if len(raw) != 4:
        raise ValueError("ASCII marker must be four bytes")
    return int.from_bytes(raw, "big")


def read_word(rom: bytes | bytearray, off: int) -> int:
    return int.from_bytes(rom[off : off + 4], "big")


def write_word(rom: bytearray, off: int, value: int) -> None:
    rom[off : off + 4] = word(value)


def write_words(rom: bytearray, off: int, words: list[int]) -> None:
    for index, value in enumerate(words):
        write_word(rom, off + index * 4, value)


def runtime(rom_off: int) -> int:
    return MAIN_VADDR_BASE + rom_off


def kseg1_for_loaded_rom_offset(rom_off: int) -> int:
    # In the Gopher64 RDRAM dumps for GE/TND, main ROM offset N appears at
    # RDRAM offset N - 0xC00.  Use KSEG1 instead of KSEG0 for the ring so the
    # diagnostic writes bypass CPU cache and are visible in a raw RDRAM dump.
    return 0xA0000000 + rom_off - 0xC00


def lui(rt: int, imm: int) -> int:
    return 0x3C000000 | (rt << 16) | (imm & 0xFFFF)


def ori(rt: int, rs: int, imm: int) -> int:
    return 0x34000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def addiu(rt: int, rs: int, imm: int) -> int:
    return 0x24000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def andi(rt: int, rs: int, imm: int) -> int:
    return 0x30000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def sll(rd: int, rt: int, shamt: int) -> int:
    return (rt << 16) | (rd << 11) | ((shamt & 0x1F) << 6)


def addu(rd: int, rs: int, rt: int) -> int:
    return (rs << 21) | (rt << 16) | (rd << 11) | 0x21


def lw(rt: int, offset: int, base: int) -> int:
    return 0x8C000000 | (base << 21) | (rt << 16) | (offset & 0xFFFF)


def sw(rt: int, offset: int, base: int) -> int:
    return 0xAC000000 | (base << 21) | (rt << 16) | (offset & 0xFFFF)


def j(addr: int) -> int:
    return 0x08000000 | ((addr >> 2) & 0x03FFFFFF)


def nop() -> int:
    return 0


def load_imm(reg: int, value: int) -> list[int]:
    return [lui(reg, value >> 16), ori(reg, reg, value & 0xFFFF)]


def find_executable_zero_cave(rom: bytes, min_size: int) -> tuple[int, int]:
    required_nibble = (runtime(TEXT_RENDER_ROM_OFF) >> 28) & 0xF
    run_start = None
    run_len = 0
    start = max(0, 0x7F000000 - MAIN_VADDR_BASE)
    for index in range(start, len(rom)):
        if rom[index] == 0:
            if run_start is None:
                run_start = index
            run_len += 1
            aligned_start = (run_start + 3) & ~3
            aligned_len = index - aligned_start + 1
            if aligned_len >= min_size:
                if ((runtime(aligned_start) >> 28) & 0xF) == required_nibble:
                    return aligned_start, aligned_len
        else:
            run_start = None
            run_len = 0
    raise ValueError(f"could not find 0x{min_size:X}-byte zero cave in 0x7F jump range")


def make_text_stub(marker_text: str, continue_rom_off: int, stack_offsets: tuple[int, ...], ring_addr: int) -> list[int]:
    record_marker = ascii_word(marker_text)
    words: list[int] = []
    # t0 = ring base, t1 = count, t2 = record pointer
    words.extend(load_imm(R_T0, ring_addr))
    words.extend(load_imm(R_T1, ascii_word("TXLR")))
    words.extend([
        sw(R_T1, 0x0000, R_T0),
        lw(R_T1, 0x0004, R_T0),
        andi(R_T2, R_T1, RING_RECORD_MASK),
        sll(R_T2, R_T2, 7),
        addiu(R_T2, R_T2, RING_HEADER_SIZE),
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
    for index, stack_off in enumerate(stack_offsets):
        words.extend([
            lw(R_T3, stack_off, R_SP),
            sw(R_T3, 0x002C + index * 4, R_T2),
        ])
    words.extend([
        addiu(R_T1, R_T1, 1),
        sw(R_T1, 0x0004, R_T0),
        j(runtime(continue_rom_off)),
        nop(),
    ])
    return words


def patch_hook(rom: bytearray, hook_off: int, expected_first: int, stub_off: int) -> dict:
    old = read_word(rom, hook_off)
    if old != expected_first:
        raise ValueError(f"unexpected hook word at 0x{hook_off:X}: got 0x{old:08X}, want 0x{expected_first:08X}")
    write_words(rom, hook_off, [j(runtime(stub_off)), old])
    return {
        "hook_offset": f"0x{hook_off:06X}",
        "stub_offset": f"0x{stub_off:06X}",
        "old_first_word": f"0x{old:08X}",
        "new_jump": f"0x{read_word(rom, hook_off):08X}",
    }


def build(args: argparse.Namespace) -> None:
    base = Path(args.base_rom)
    rom = bytearray(base.read_bytes())
    cave_off, cave_len = find_executable_zero_cave(rom, MIN_CAVE_SIZE)
    text_stub_off = cave_off
    # Keep the two stubs comfortably separated and the ring aligned/readable.
    glow_stub_off = text_stub_off + STUB_GLOW_DELTA
    ring_off = text_stub_off + RING_DELTA
    ring_addr = kseg1_for_loaded_rom_offset(ring_off)
    if any(rom[cave_off : cave_off + MIN_CAVE_SIZE]):
        raise ValueError(f"selected cave at 0x{cave_off:X} was not fully empty")

    text_words = make_text_stub(
        "TXTR",
        TEXT_RENDER_CONTINUE_ROM_OFF,
        (0x00B8, 0x00BC, 0x00C0, 0x00C4, 0x00C8, 0x00CC, 0x00D0),
        ring_addr,
    )
    glow_words = make_text_stub(
        "TXTG",
        TEXT_RENDER_GLOW_CONTINUE_ROM_OFF,
        (0x00A8, 0x00AC, 0x00B0, 0x00B4, 0x00B8, 0x00BC, 0x00C0, 0x00C4),
        ring_addr,
    )
    write_words(rom, text_stub_off, text_words)
    write_words(rom, glow_stub_off, glow_words)
    hooks = {
        "textRender": patch_hook(rom, TEXT_RENDER_ROM_OFF, TEXT_RENDER_FIRST_WORD, text_stub_off),
        "textRenderGlow": patch_hook(rom, TEXT_RENDER_GLOW_ROM_OFF, TEXT_RENDER_GLOW_FIRST_WORD, glow_stub_off),
    }
    crc1, crc2 = update_n64_crc_6102(rom)
    out = Path(args.out_rom)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(rom)
    report = {
        "base_rom": str(base),
        "base_md5": hashlib.md5(base.read_bytes()).hexdigest(),
        "out_rom": str(out),
        "out_md5": hashlib.md5(rom).hexdigest(),
        "n64_crc": [f"0x{crc1:08X}", f"0x{crc2:08X}"],
        "cave": {
            "offset": f"0x{cave_off:06X}",
            "runtime": f"0x{runtime(cave_off):08X}",
            "zero_run_bytes": cave_len,
            "text_stub_offset": f"0x{text_stub_off:06X}",
            "glow_stub_offset": f"0x{glow_stub_off:06X}",
            "ring_offset": f"0x{ring_off:06X}",
            "ring_runtime": f"0x{runtime(ring_off):08X}",
            "ring_kseg1": f"0x{ring_addr:08X}",
            "ring_rdram_offset": f"0x{ring_addr - 0xA0000000:06X}",
            "ring_total_size": f"0x{RING_TOTAL_SIZE:X}",
        },
        "hooks": hooks,
    }
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an RDRAM text-call logger ROM.")
    parser.add_argument("--base-rom", required=True)
    parser.add_argument("--out-rom", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
