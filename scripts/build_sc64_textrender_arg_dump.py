#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

from build_tnd480i_candidate import update_n64_crc_6102


R_A0 = 4
R_A1 = 5
R_A2 = 6
R_A3 = 7
R_T0 = 8
R_T1 = 9
R_SP = 29

MAIN_VADDR_BASE = 0x7EFCB4D0
DIAG_CAVE_ROM_OFF = 0x1158B0
TEXT_RENDER_ROM_OFF = 0x0E25EC
TEXT_RENDER_CONTINUE_ROM_OFF = TEXT_RENDER_ROM_OFF + 4
MAIN_CAVE_SIZE = 0x100
SC64_DATA_BUFFER_INTERNAL = 0x05000000
SC64_DATA_BUFFER_CPU_BASE = 0xBFFE0000


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


def ensure_main_cave(rom, words):
    size = len(words) * 4
    if size > MAIN_CAVE_SIZE:
        raise ValueError(f"diagnostic stub is 0x{size:X}, main cave budget is 0x{MAIN_CAVE_SIZE:X}")
    if any(rom[DIAG_CAVE_ROM_OFF:DIAG_CAVE_ROM_OFF + size]):
        raise ValueError(f"diagnostic cave is not empty at 0x{DIAG_CAVE_ROM_OFF:X}")


def unlock_sc64_regs():
    return [
        lui(R_T0, 0xBFFF),
        sw(0, 0x0010, R_T0),
        lui(R_T1, 0x5F55),
        ori(R_T1, R_T1, 0x4E4C),
        sw(R_T1, 0x0010, R_T0),
        lui(R_T1, 0x4F43),
        ori(R_T1, R_T1, 0x4B5F),
        sw(R_T1, 0x0010, R_T0),
    ]


def make_textrender_stub():
    marker = ascii_word("TXTR")
    words = [
        *unlock_sc64_regs(),
        lui(R_T0, SC64_DATA_BUFFER_CPU_BASE >> 16),
        lui(R_T1, marker >> 16),
        ori(R_T1, R_T1, marker & 0xFFFF),
        sw(R_T1, 0x0000, R_T0),
        sw(R_A0, 0x0004, R_T0),
        sw(R_A1, 0x0008, R_T0),
        sw(R_A2, 0x000C, R_T0),
        sw(R_A3, 0x0010, R_T0),
    ]
    for i, stack_off in enumerate((0x00B8, 0x00BC, 0x00C0, 0x00C4, 0x00C8)):
        words.extend([
            lw(R_T1, stack_off, R_SP),
            sw(R_T1, 0x0014 + i * 4, R_T0),
        ])
    words.extend([j(runtime(TEXT_RENDER_CONTINUE_ROM_OFF)), nop()])
    return words


def build(args):
    rom_path = Path(args.base_rom)
    rom = bytearray(rom_path.read_bytes())
    words = make_textrender_stub()
    ensure_main_cave(rom, words)
    write_words(rom, DIAG_CAVE_ROM_OFF, words)
    original_first_word = int.from_bytes(rom[TEXT_RENDER_ROM_OFF:TEXT_RENDER_ROM_OFF + 4], "big")
    if original_first_word != 0x27BDFF58:
        raise ValueError(f"unexpected textRender prologue at 0x{TEXT_RENDER_ROM_OFF:X}: 0x{original_first_word:08X}")
    write_words(rom, TEXT_RENDER_ROM_OFF, [
        j(runtime(DIAG_CAVE_ROM_OFF)),
        original_first_word,
    ])
    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = Path(args.out_rom)
    out_rom.parent.mkdir(parents=True, exist_ok=True)
    out_rom.write_bytes(rom)
    summary = {
        "base_rom": str(rom_path),
        "base_md5": hashlib.md5(rom_path.read_bytes()).hexdigest(),
        "out_rom": str(out_rom),
        "out_md5": hashlib.md5(rom).hexdigest(),
        "n64_crc": [f"0x{crc1:08X}", f"0x{crc2:08X}"],
        "diagnostic": {
            "transport": "sc64 data buffer",
            "hook": "textRender entry",
            "dump_command": "sc64deployer dump 0x05000000 0x30 <path>",
            "words": {
                "0x00": "marker TXTR",
                "0x04": "arg0 gdl",
                "0x08": "arg1 x pointer",
                "0x0C": "arg2 y pointer",
                "0x10": "arg3 text pointer",
                "0x14": "stack arg4 font chars",
                "0x18": "stack arg5 font file",
                "0x1C": "stack arg6 color",
                "0x20": "stack arg7 view_x",
                "0x24": "stack arg8 view_y",
            },
        },
    }
    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Patch textRender to dump its latest arguments to the SC64 data buffer.")
    parser.add_argument("--base-rom", required=True)
    parser.add_argument("--out-rom", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
