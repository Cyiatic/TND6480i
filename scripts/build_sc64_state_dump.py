#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

from build_tnd480i_candidate import update_n64_crc_6102


R_ZERO = 0
R_T0 = 8
R_T1 = 9
R_T2 = 10
R_T3 = 11
R_SP = 29
R_RA = 31

ROM_LOAD_OFFSET = 0x1000
RAM_LOAD_ADDRESS = 0x80000400
DIAG_CAVE_ROM_OFF = 0x3CB0
VIDEO_RELATED_RETURN_ROM_OFF = 0x46F4
LOW_CAVE_SIZE = 0x74
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


def jr(rs):
    return 0x00000008 | (rs << 21)


def nop():
    return 0


def runtime(rom_off):
    return RAM_LOAD_ADDRESS + (rom_off - ROM_LOAD_OFFSET)


def write_words(rom, off, words):
    for i, value in enumerate(words):
        rom[off + i * 4:off + i * 4 + 4] = word(value)


def ensure_low_cave(rom, words):
    size = len(words) * 4
    if size > LOW_CAVE_SIZE:
        raise ValueError(f"diagnostic stub is 0x{size:X}, low cave only has 0x{LOW_CAVE_SIZE:X}")
    if any(rom[DIAG_CAVE_ROM_OFF:DIAG_CAVE_ROM_OFF + size]):
        raise ValueError(f"diagnostic cave is not empty at 0x{DIAG_CAVE_ROM_OFF:X}")


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


def make_state_dump_stub():
    words = [
        *unlock_sc64_regs(),
        lui(R_T0, SC64_DATA_BUFFER_CPU_BASE >> 16),
        lui(R_T1, ascii_word("VDAT") >> 16),
        ori(R_T1, R_T1, ascii_word("VDAT") & 0xFFFF),
        sw(R_T1, 0x0000, R_T0),
        lui(R_T2, 0x8002),
        lw(R_T2, 0x32A8, R_T2),
        sw(R_T2, 0x0004, R_T0),
        lw(R_T3, 0x0000, R_T2),
        sw(R_T3, 0x0008, R_T0),
        lw(R_T3, 0x0018, R_T2),
        sw(R_T3, 0x000C, R_T0),
        lw(R_T3, 0x001C, R_T2),
        sw(R_T3, 0x0010, R_T0),
        lw(R_T3, 0x0028, R_T2),
        sw(R_T3, 0x0014, R_T0),
        lw(R_RA, 0x0014, R_SP),
        addiu(R_SP, R_SP, 0x0018),
        jr(R_RA),
        nop(),
    ]
    return words


def build(args):
    rom_path = Path(args.base_rom)
    rom = bytearray(rom_path.read_bytes())
    words = make_state_dump_stub()
    ensure_low_cave(rom, words)
    write_words(rom, DIAG_CAVE_ROM_OFF, words)
    write_words(rom, VIDEO_RELATED_RETURN_ROM_OFF, [j(runtime(DIAG_CAVE_ROM_OFF)), nop()])
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
            "hook": "video-related-return",
            "dump_command": "sc64deployer dump 0x05000000 0x20 <path>",
            "words": {
                "0x00": "marker VDAT",
                "0x04": "g_ViBackData pointer",
                "0x08": "settings/mode word",
                "0x0C": "bufx/bufy",
                "0x10": "viewx/viewy",
                "0x14": "framebuf",
            },
        },
    }
    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Patch a ROM to write a compact VI backdata snapshot to SC64 data buffer.")
    parser.add_argument("--base-rom", required=True)
    parser.add_argument("--out-rom", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
