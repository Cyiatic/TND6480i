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


def lui(rt, imm):
    return 0x3C000000 | (rt << 16) | (imm & 0xFFFF)


def ori(rt, rs, imm):
    return 0x34000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def addiu(rt, rs, imm):
    return 0x24000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def addu(rd, rs, rt):
    return (rs << 21) | (rt << 16) | (rd << 11) | 0x21


def or_(rd, rs, rt):
    return (rs << 21) | (rt << 16) | (rd << 11) | 0x25


def lw(rt, offset, base):
    return 0x8C000000 | (base << 21) | (rt << 16) | (offset & 0xFFFF)


def sw(rt, offset, base):
    return 0xAC000000 | (base << 21) | (rt << 16) | (offset & 0xFFFF)


def bne(rs, rt, offset):
    return 0x14000000 | (rs << 21) | (rt << 16) | (offset & 0xFFFF)


def j(addr):
    return 0x08000000 | ((addr >> 2) & 0x03FFFFFF)


def jr(rs):
    return 0x00000008 | (rs << 21)


def nop():
    return 0


def runtime(rom_off):
    return RAM_LOAD_ADDRESS + (rom_off - ROM_LOAD_OFFSET)


def hi_lo(value):
    return (value >> 16) & 0xFFFF, value & 0xFFFF


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


def build_frameblock_stub(source_offset, words_to_copy, data_buffer_offset):
    if not (1 <= words_to_copy <= 0x7FFF):
        raise ValueError("--words must be in 1..32767 so the loop counter fits one instruction")
    if not (0 <= data_buffer_offset <= 0x7FFF):
        raise ValueError("--data-buffer-offset must fit a positive 16-bit store offset")

    off_hi, off_lo = hi_lo(source_offset)
    loop_word_index = 18
    branch_word_index = 23
    branch_delta = loop_word_index - (branch_word_index + 1)

    words = [
        *unlock_sc64_regs(),
        lui(R_T0, SC64_DATA_BUFFER_CPU_BASE >> 16),
        lui(R_T1, 0x8002),
        lw(R_T1, 0x32A8, R_T1),
        lw(R_T1, 0x0028, R_T1),
        lui(R_T2, 0xA000),
        or_(R_T1, R_T1, R_T2),
        lui(R_T2, off_hi),
        ori(R_T2, R_T2, off_lo),
        addu(R_T1, R_T1, R_T2),
        addiu(R_T3, R_ZERO, words_to_copy),
        lw(R_T2, 0x0000, R_T1),
        sw(R_T2, data_buffer_offset, R_T0),
        addiu(R_T1, R_T1, 0x0004),
        addiu(R_T0, R_T0, 0x0004),
        addiu(R_T3, R_T3, -1),
        bne(R_T3, R_ZERO, branch_delta),
        nop(),
        lw(R_RA, 0x0014, R_SP),
        addiu(R_SP, R_SP, 0x0018),
        jr(R_RA),
        nop(),
    ]
    assert len(words) == 29
    return words


def apply_frameblock_dump(rom, source_offset, words_to_copy, data_buffer_offset):
    words = build_frameblock_stub(source_offset, words_to_copy, data_buffer_offset)
    ensure_low_cave(rom, words)
    write_words(rom, DIAG_CAVE_ROM_OFF, words)
    write_words(rom, VIDEO_RELATED_RETURN_ROM_OFF, [j(runtime(DIAG_CAVE_ROM_OFF)), nop()])
    return {
        "transport": "sc64 data buffer",
        "hook": "video-related-return",
        "hook_offset": f"0x{VIDEO_RELATED_RETURN_ROM_OFF:X}",
        "cave_offset": f"0x{DIAG_CAVE_ROM_OFF:X}",
        "runtime_cave": f"0x{runtime(DIAG_CAVE_ROM_OFF):08X}",
        "source": "g_ViBackData->framebuf OR 0xA0000000 plus source_offset",
        "source_offset": f"0x{source_offset:X}",
        "words_to_copy": words_to_copy,
        "bytes_to_dump": words_to_copy * 4,
        "data_buffer_internal": f"0x{SC64_DATA_BUFFER_INTERNAL + data_buffer_offset:08X}",
        "dump_command": (
            f"sc64deployer dump 0x{SC64_DATA_BUFFER_INTERNAL + data_buffer_offset:08X} "
            f"0x{words_to_copy * 4:X} <path>"
        ),
    }


def md5(data):
    return hashlib.md5(data).hexdigest()


def build(args):
    rom = bytearray(Path(args.base_rom).read_bytes())
    diagnostic = apply_frameblock_dump(rom, args.source_offset, args.words, args.data_buffer_offset)
    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = Path(args.out_rom)
    out_rom.parent.mkdir(parents=True, exist_ok=True)
    out_rom.write_bytes(rom)
    summary = {
        "base_rom": args.base_rom,
        "base_md5": md5(Path(args.base_rom).read_bytes()),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "n64_crc": [f"0x{crc1:08X}", f"0x{crc2:08X}"],
        "diagnostic": diagnostic,
    }
    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Patch a ROM to mirror a live framebuffer block into the SC64 data buffer.")
    parser.add_argument("--base-rom", required=True)
    parser.add_argument("--out-rom", required=True)
    parser.add_argument("--report")
    parser.add_argument("--source-offset", type=lambda x: int(x, 0), default=0)
    parser.add_argument("--words", type=lambda x: int(x, 0), default=0x2000)
    parser.add_argument("--data-buffer-offset", type=lambda x: int(x, 0), default=0x1000)
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
