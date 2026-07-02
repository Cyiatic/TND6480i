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
BCLR_RETURN_ROM_OFF = 0x3D4C
HVI_RETURN_ROM_OFF = 0x19AC4
LOW_CAVE_SIZE = 0x74


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


def andi(rt, rs, imm):
    return 0x30000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


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


def write_words(rom, off, words):
    for i, value in enumerate(words):
        rom[off + i * 4:off + i * 4 + 4] = word(value)


def ensure_low_cave(rom, words):
    size = len(words) * 4
    if size > LOW_CAVE_SIZE:
        raise ValueError(f"diagnostic stub is 0x{size:X}, low cave only has 0x{LOW_CAVE_SIZE:X}")
    if any(rom[DIAG_CAVE_ROM_OFF:DIAG_CAVE_ROM_OFF + size]):
        raise ValueError(f"diagnostic cave is not empty at 0x{DIAG_CAVE_ROM_OFF:X}")


def emit_isv_const(value, offset):
    return [
        lui(R_T1, value >> 16),
        ori(R_T1, R_T1, value & 0xFFFF),
        sw(R_T1, offset, R_T0),
    ]


def trigger_isv(length):
    return [
        lui(R_T2, 0xA460),
        lw(R_T1, 0x0010, R_T2),
        andi(R_T1, R_T1, 0x0003),
        bne(R_T1, R_ZERO, -3),
        nop(),
        addiu(R_T1, R_ZERO, length),
        sw(R_T1, -0x000C, R_T0),
    ]


def pi_wait():
    return [
        lui(R_T2, 0xA460),
        lw(R_T1, 0x0010, R_T2),
        andi(R_T1, R_T1, 0x0003),
        bne(R_T1, R_ZERO, -3),
        nop(),
    ]


def make_backdata_snapshot():
    # ISV payload:
    #   VDBA, g_ViBackData, settings0, x/y, bufx/bufy,
    #   viewx/viewy, viewleft/viewtop, framebuf
    words = [
        lui(R_T0, 0xB3FF),
        ori(R_T0, R_T0, 0x0020),
        *emit_isv_const(ascii_word("VDBA"), 0x0000),
        lui(R_T2, 0x8002),
        lw(R_T2, 0x32A8, R_T2),
        sw(R_T2, 0x0004, R_T0),
    ]
    out_off = 0x0008
    for src_off in (0x0000, 0x0004, 0x0018, 0x001C, 0x0020, 0x0028):
        words.extend([
            lw(R_T3, src_off, R_T2),
            sw(R_T3, out_off, R_T0),
        ])
        out_off += 4
    words.extend(trigger_isv(0x20))
    return words


def make_ping_snapshot():
    return [
        lui(R_T0, 0xB3FF),
        ori(R_T0, R_T0, 0x0020),
        *pi_wait(),
        *emit_isv_const(ascii_word("PING"), 0x0000),
        *trigger_isv(0x04),
    ]


def make_hwvi_snapshot():
    # ISV payload:
    #   VHWV, VI_STATUS, VI_ORIGIN, VI_WIDTH, VI_H_START,
    #   VI_V_START, VI_X_SCALE, VI_Y_SCALE
    words = [
        lui(R_T0, 0xB3FF),
        ori(R_T0, R_T0, 0x0020),
        *emit_isv_const(ascii_word("VHWV"), 0x0000),
        lui(R_T2, 0xA440),
    ]
    out_off = 0x0004
    for src_off in (0x0000, 0x0004, 0x0008, 0x0024, 0x0028, 0x0030, 0x0034):
        words.extend([
            lw(R_T3, src_off, R_T2),
            sw(R_T3, out_off, R_T0),
        ])
        out_off += 4
    words.extend(trigger_isv(0x20))
    return words


SNAPSHOTS = {
    "ping": {
        "builder": make_ping_snapshot,
        "words": [
            "marker PING",
        ],
    },
    "backdata": {
        "builder": make_backdata_snapshot,
        "words": [
            "marker VDBA",
            "g_ViBackData pointer",
            "VideoSettings word 0",
            "x/y",
            "bufx/bufy",
            "viewx/viewy",
            "viewleft/viewtop",
            "framebuf",
        ],
    },
    "hwvi": {
        "builder": make_hwvi_snapshot,
        "words": [
            "marker VHWV",
            "VI_STATUS",
            "VI_ORIGIN",
            "VI_WIDTH",
            "VI_H_START",
            "VI_V_START",
            "VI_X_SCALE",
            "VI_Y_SCALE",
        ],
    },
}


def apply_isv_vidstate(rom, snapshot, hook):
    info = SNAPSHOTS[snapshot]
    words = info["builder"]()
    if hook == "hvi":
        words.extend([jr(R_RA), nop()])
        hook_offset = HVI_RETURN_ROM_OFF
        hook_words = [
            j(runtime(DIAG_CAVE_ROM_OFF)),
            addiu(R_SP, R_SP, 0x0048),
        ]
    elif hook == "bclr":
        words.extend([jr(R_RA), addiu(R_SP, R_SP, 0x0018)])
        hook_offset = BCLR_RETURN_ROM_OFF
        hook_words = [
            j(runtime(DIAG_CAVE_ROM_OFF)),
            lw(R_RA, 0x0014, R_SP),
        ]
    else:
        raise ValueError(f"unknown hook: {hook}")
    ensure_low_cave(rom, words)
    write_words(rom, DIAG_CAVE_ROM_OFF, words)
    write_words(rom, hook_offset, hook_words)
    return {
        "transport": "sc64 isv binary",
        "isv_offset": "0x03FF0000",
        "payload_length": "0x20",
        "snapshot": snapshot,
        "hook": hook,
        "cave_offset": f"0x{DIAG_CAVE_ROM_OFF:X}",
        "hook_offset": f"0x{hook_offset:X}",
        "runtime_cave": f"0x{runtime(DIAG_CAVE_ROM_OFF):08X}",
        "low_cave_bytes_used": f"0x{len(words) * 4:X}",
        "expected_isv_payload": info["words"],
    }


def md5(data):
    return hashlib.md5(data).hexdigest()


def build(args):
    rom = bytearray(Path(args.base_rom).read_bytes())
    diagnostic = apply_isv_vidstate(rom, args.snapshot, args.hook)
    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = Path(args.out_rom)
    out_rom.parent.mkdir(parents=True, exist_ok=True)
    out_rom.write_bytes(rom)
    summary = {
        "base_rom": args.base_rom,
        "out_rom": args.out_rom,
        "out_md5": md5(rom),
        "n64_crc": [f"0x{crc1:08X}", f"0x{crc2:08X}"],
        "diagnostic": diagnostic,
    }
    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", required=True)
    parser.add_argument("--out-rom", required=True)
    parser.add_argument("--report")
    parser.add_argument("--snapshot", choices=sorted(SNAPSHOTS), required=True)
    parser.add_argument("--hook", choices=("hvi", "bclr"), default="bclr")
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
