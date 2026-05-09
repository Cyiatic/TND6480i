#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

from build_tnd480i_candidate import update_n64_crc_6102


R_ZERO = 0
R_AT = 1
R_A0 = 4
R_T0 = 8
R_T1 = 9
R_T7 = 15
R_T9 = 25
R_SP = 29
R_RA = 31

KSEG0_BASE = 0x80000000
LOGGER_ROM_OFF = 0x331E0
HVI_RETURN_TRAMP_ROM_OFF = 0x33240


def word(value):
    return value.to_bytes(4, "big")


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


def or_(rd, rs, rt):
    return 0x00000025 | (rs << 21) | (rt << 16) | (rd << 11)


def jr(rs):
    return 0x00000008 | (rs << 21)


def jal(addr):
    return 0x0C000000 | ((addr >> 2) & 0x03FFFFFF)


def j(addr):
    return 0x08000000 | ((addr >> 2) & 0x03FFFFFF)


def nop():
    return 0


def runtime(rom_off):
    return KSEG0_BASE + rom_off


def ascii_word(text):
    data = text.encode("ascii")
    if len(data) != 4:
        raise ValueError("marker text must be exactly 4 ASCII bytes")
    return int.from_bytes(data, "big")


def write_words(rom, off, words):
    for i, value in enumerate(words):
        rom[off + i * 4:off + i * 4 + 4] = word(value)


def make_logger():
    # Writes "TND:" + marker + "\n" to the IS-Viewer buffer at cart offset
    # 0x03FF0000. SC64 should be started with: sc64deployer debug --isv 0x03FF0000
    return [
        lui(R_T0, 0xB3FF),
        ori(R_T0, R_T0, 0x0020),
        lui(R_T1, 0x544E),
        ori(R_T1, R_T1, 0x443A),
        sw(R_T1, 0x0000, R_T0),
        sw(R_A0, 0x0004, R_T0),
        lui(R_T1, 0x0A00),
        sw(R_T1, 0x0008, R_T0),
        lui(R_T0, 0xB3FF),
        ori(R_T0, R_T0, 0x0014),
        addiu(R_T1, R_ZERO, 9),
        jr(R_RA),
        sw(R_T1, 0x0000, R_T0),
    ]


def log_call(marker):
    marker_word = ascii_word(marker)
    return [
        lui(R_A0, marker_word >> 16),
        jal(runtime(LOGGER_ROM_OFF)),
        ori(R_A0, R_A0, marker_word & 0xFFFF),
    ]


def make_hvi_return_trampoline():
    return [
        or_(R_T9, R_RA, R_ZERO),
        *log_call("HVI1"),
        jr(R_T9),
        nop(),
    ]


def apply_instrumentation(rom):
    report = []

    if any(rom[LOGGER_ROM_OFF:LOGGER_ROM_OFF + 0x80]):
        raise ValueError(f"logger cave is not empty at 0x{LOGGER_ROM_OFF:X}")
    if any(rom[HVI_RETURN_TRAMP_ROM_OFF:HVI_RETURN_TRAMP_ROM_OFF + 0x40]):
        raise ValueError(f"HVI trampoline cave is not empty at 0x{HVI_RETURN_TRAMP_ROM_OFF:X}")

    write_words(rom, LOGGER_ROM_OFF, make_logger())
    report.append({"offset": f"0x{LOGGER_ROM_OFF:X}", "note": "IS-Viewer marker logger"})

    write_words(rom, HVI_RETURN_TRAMP_ROM_OFF, make_hvi_return_trampoline())
    report.append({"offset": f"0x{HVI_RETURN_TRAMP_ROM_OFF:X}", "note": "VI return breadcrumb trampoline"})

    # Framebuffer clear function return path. The original function has saved
    # RA on the stack, so this can log and then return through t9.
    write_words(rom, 0x3D4C, [
        lw(R_RA, 0x0014, R_SP),
        or_(R_T9, R_RA, R_ZERO),
        *log_call("BCLR"),
        jr(R_T9),
        addiu(R_SP, R_SP, 0x0018),
    ])
    report.append({"offset": "0x3D4C", "note": "log after framebuffer clear function"})

    # Framebuffer global setup return path. Preserve original RA in t9, keep the
    # original fb1 global store, log, then return.
    write_words(rom, 0x65A4, [
        or_(R_T9, R_RA, R_ZERO),
        sw(R_T7, 0x4180, R_AT),
        *log_call("DFB1"),
        jr(R_T9),
        nop(),
    ])
    report.append({"offset": "0x65A4", "note": "log after framebuffer globals are written"})

    # VI setup function return path. The delay slot still restores SP before
    # the trampoline logs and returns to the original caller.
    write_words(rom, 0x19AC4, [
        j(runtime(HVI_RETURN_TRAMP_ROM_OFF)),
        addiu(R_SP, R_SP, 0x0048),
    ])
    report.append({"offset": "0x19AC4", "note": "log after VI setup function returns"})

    return report


def md5(data):
    return hashlib.md5(data).hexdigest()


def build(args):
    rom = bytearray(Path(args.base_rom).read_bytes())
    report = apply_instrumentation(rom)
    crc1, crc2 = update_n64_crc_6102(rom)
    Path(args.out_rom).write_bytes(rom)
    summary = {
        "base_rom": args.base_rom,
        "out_rom": args.out_rom,
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X}{crc2:08X}",
        "isv_debug_command": "sc64deployer.exe debug --isv 0x03FF0000",
        "expected_markers": ["TND:BCLR", "TND:DFB1", "TND:HVI1"],
        "patches": report,
    }
    if args.report:
        Path(args.report).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", required=True)
    parser.add_argument("--out-rom", required=True)
    parser.add_argument("--report", default=None)
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
