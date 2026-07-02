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
HVI_RETURN_ROM_OFF = 0x19AC4
SC64_DATA_BUFFER_INTERNAL = 0x05000000
SC64_DATA_BUFFER_DIAG_OFFSET = 0x1000


def word(value):
    return value.to_bytes(4, "big")


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


def ensure_zero_cave(rom, off, words):
    size = len(words) * 4
    if any(rom[off:off + size]):
        raise ValueError(f"diagnostic cave is not empty at 0x{off:X} for 0x{size:X} bytes")


def make_vidiag_trampoline(restore_video_related_stack):
    # Runs at the end of a VI-related path. It unlocks SC64 register/data-buffer
    # access, then writes a compact snapshot of g_ViBackData to the SC64 data
    # buffer. The PC can read it with:
    #   sc64deployer dump 0x05001000 0x20 <path>
    words = [
        lui(R_T0, 0xBFFF),
        sw(R_ZERO, 0x0010, R_T0),
        lui(R_T1, 0x5F55),
        ori(R_T1, R_T1, 0x4E4C),
        sw(R_T1, 0x0010, R_T0),
        lui(R_T1, 0x4F43),
        ori(R_T1, R_T1, 0x4B5F),
        sw(R_T1, 0x0010, R_T0),
        lui(R_T0, 0xBFFE),
        lui(R_T1, 0x5644),
        ori(R_T1, R_T1, 0x4941),
        sw(R_T1, SC64_DATA_BUFFER_DIAG_OFFSET + 0x0000, R_T0),
        lui(R_T2, 0x8002),
        lw(R_T2, 0x32A8, R_T2),
        sw(R_T2, SC64_DATA_BUFFER_DIAG_OFFSET + 0x0004, R_T0),
        lw(R_T3, 0x0000, R_T2),
        sw(R_T3, SC64_DATA_BUFFER_DIAG_OFFSET + 0x0008, R_T0),
        lw(R_T3, 0x0004, R_T2),
        sw(R_T3, SC64_DATA_BUFFER_DIAG_OFFSET + 0x000C, R_T0),
        lw(R_T3, 0x0018, R_T2),
        sw(R_T3, SC64_DATA_BUFFER_DIAG_OFFSET + 0x0010, R_T0),
        lw(R_T3, 0x001C, R_T2),
        sw(R_T3, SC64_DATA_BUFFER_DIAG_OFFSET + 0x0014, R_T0),
        lw(R_T3, 0x0020, R_T2),
        sw(R_T3, SC64_DATA_BUFFER_DIAG_OFFSET + 0x0018, R_T0),
        lw(R_T3, 0x0028, R_T2),
        sw(R_T3, SC64_DATA_BUFFER_DIAG_OFFSET + 0x001C, R_T0),
    ]
    if restore_video_related_stack:
        words.extend([
            lw(R_RA, 0x0014, R_SP),
            addiu(R_SP, R_SP, 0x0018),
        ])
    words.extend([
        jr(R_RA),
        nop(),
    ])
    return words


def apply_vidiag(rom, hook):
    restore_video_related_stack = hook == "video-related"
    hook_offset = VIDEO_RELATED_RETURN_ROM_OFF if restore_video_related_stack else HVI_RETURN_ROM_OFF
    trampoline = make_vidiag_trampoline(restore_video_related_stack)
    ensure_zero_cave(rom, DIAG_CAVE_ROM_OFF, trampoline)
    write_words(rom, DIAG_CAVE_ROM_OFF, trampoline)
    if restore_video_related_stack:
        hook_words = [j(runtime(DIAG_CAVE_ROM_OFF)), nop()]
    else:
        hook_words = [j(runtime(DIAG_CAVE_ROM_OFF)), addiu(R_SP, R_SP, 0x0048)]
    write_words(rom, hook_offset, hook_words)
    return {
        "cave_offset": f"0x{DIAG_CAVE_ROM_OFF:X}",
        "hook": hook,
        "hook_offset": f"0x{hook_offset:X}",
        "runtime_cave": f"0x{runtime(DIAG_CAVE_ROM_OFF):08X}",
        "sc64_data_buffer_internal": f"0x{SC64_DATA_BUFFER_INTERNAL:X}",
        "sc64_data_buffer_diag_internal": f"0x{SC64_DATA_BUFFER_INTERNAL + SC64_DATA_BUFFER_DIAG_OFFSET:X}",
        "sc64_deployer_dump_command": (
            f"sc64deployer dump 0x{SC64_DATA_BUFFER_INTERNAL + SC64_DATA_BUFFER_DIAG_OFFSET:08X} 0x20 <path>"
        ),
        "snapshot_words": {
            "0x00": "marker VDIA",
            "0x04": "g_ViBackData pointer",
            "0x08": "VideoSettings word 0: mode/fields",
            "0x0C": "x/y",
            "0x10": "bufx/bufy",
            "0x14": "viewx/viewy",
            "0x18": "viewleft/viewtop",
            "0x1C": "framebuf",
        },
    }


def build(args):
    rom = bytearray(Path(args.base_rom).read_bytes())
    report = apply_vidiag(rom, args.hook)
    crc1, crc2 = update_n64_crc_6102(rom)
    Path(args.out_rom).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_rom).write_bytes(rom)
    summary = {
        "base_rom": args.base_rom,
        "out_rom": args.out_rom,
        "md5": hashlib.md5(rom).hexdigest(),
        "n64_crc": [f"0x{crc1:08X}", f"0x{crc2:08X}"],
        "diagnostic": report,
    }
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", required=True)
    parser.add_argument("--out-rom", required=True)
    parser.add_argument("--report")
    parser.add_argument("--hook", choices=["hvi", "video-related"], default="hvi")
    args = parser.parse_args()
    print(json.dumps(build(args), indent=2))


if __name__ == "__main__":
    main()
