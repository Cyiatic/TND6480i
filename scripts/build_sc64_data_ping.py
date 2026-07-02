#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

from build_tnd480i_candidate import update_n64_crc_6102


R_ZERO = 0
R_T0 = 8
R_T1 = 9
R_SP = 29
R_RA = 31

ROM_LOAD_OFFSET = 0x1000
RAM_LOAD_ADDRESS = 0x80000400
DIAG_CAVE_ROM_OFF = 0x3CB0
BCLR_RETURN_ROM_OFF = 0x3D4C
VIDEO_RELATED_RETURN_ROM_OFF = 0x46F4
LOW_CAVE_SIZE = 0x74


def word(value):
    return value.to_bytes(4, "big")


def ascii_word(text):
    data = text.encode("ascii")
    if len(data) != 4:
        raise ValueError("marker must be four ASCII bytes")
    return int.from_bytes(data, "big")


def lui(rt, imm):
    return 0x3C000000 | (rt << 16) | (imm & 0xFFFF)


def ori(rt, rs, imm):
    return 0x34000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def addiu(rt, rs, imm):
    return 0x24000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def sw(rt, offset, base):
    return 0xAC000000 | (base << 21) | (rt << 16) | (offset & 0xFFFF)


def lw(rt, offset, base):
    return 0x8C000000 | (base << 21) | (rt << 16) | (offset & 0xFFFF)


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
        rom[off + i * 4 : off + i * 4 + 4] = word(value)


def ensure_cave(rom, words):
    size = len(words) * 4
    if size > LOW_CAVE_SIZE:
        raise ValueError(f"stub is 0x{size:X}, cave is only 0x{LOW_CAVE_SIZE:X}")
    if any(rom[DIAG_CAVE_ROM_OFF : DIAG_CAVE_ROM_OFF + size]):
        raise ValueError(f"diagnostic cave is not empty at 0x{DIAG_CAVE_ROM_OFF:X}")


def unlock_sc64_regs():
    return [
        lui(R_T0, 0xBFFF),
        lui(R_T1, 0x5F55),
        ori(R_T1, R_T1, 0x4E4C),
        sw(R_T1, 0x0010, R_T0),
        lui(R_T1, 0x4F43),
        ori(R_T1, R_T1, 0x4B5F),
        sw(R_T1, 0x0010, R_T0),
    ]


def marker_words(marker):
    value = ascii_word(marker)
    return [
        lui(R_T0, 0xBFFE),
        lui(R_T1, value >> 16),
        ori(R_T1, R_T1, value & 0xFFFF),
        sw(R_T1, 0x0000, R_T0),
        lui(R_T1, 0x1234),
        ori(R_T1, R_T1, 0x5678),
        sw(R_T1, 0x0004, R_T0),
    ]


def build_stub(marker, hook):
    words = [*unlock_sc64_regs(), *marker_words(marker)]
    if hook == "bclr":
        words.extend([jr(R_RA), addiu(R_SP, R_SP, 0x0018)])
    elif hook == "video":
        words.extend([lw(R_RA, 0x0014, R_SP), addiu(R_SP, R_SP, 0x0018), jr(R_RA), nop()])
    else:
        raise ValueError(hook)
    return words


def build(args):
    rom = bytearray(Path(args.base_rom).read_bytes())
    words = build_stub(args.marker, args.hook)
    ensure_cave(rom, words)
    write_words(rom, DIAG_CAVE_ROM_OFF, words)

    if args.hook == "bclr":
        write_words(rom, BCLR_RETURN_ROM_OFF, [j(runtime(DIAG_CAVE_ROM_OFF)), lw(R_RA, 0x0014, R_SP)])
        hook_offset = BCLR_RETURN_ROM_OFF
    else:
        write_words(rom, VIDEO_RELATED_RETURN_ROM_OFF, [j(runtime(DIAG_CAVE_ROM_OFF)), nop()])
        hook_offset = VIDEO_RELATED_RETURN_ROM_OFF

    crc1, crc2 = update_n64_crc_6102(rom)
    out = Path(args.out_rom)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(rom)
    report = {
        "base_rom": args.base_rom,
        "out_rom": args.out_rom,
        "out_md5": hashlib.md5(rom).hexdigest(),
        "n64_crc": [f"0x{crc1:08X}", f"0x{crc2:08X}"],
        "hook": args.hook,
        "hook_offset": f"0x{hook_offset:X}",
        "marker": args.marker,
        "dump_command": "sc64deployer.exe dump 0x05000000 0x20 <out.bin>",
    }
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", required=True)
    parser.add_argument("--out-rom", required=True)
    parser.add_argument("--report")
    parser.add_argument("--marker", default="PING")
    parser.add_argument("--hook", choices=("bclr", "video"), default="bclr")
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
