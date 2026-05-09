#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

from build_tnd480i_candidate import update_n64_crc_6102


R_ZERO = 0
R_AT = 1
R_V0 = 2
R_A0 = 4
R_A1 = 5
R_T0 = 8
R_T1 = 9
R_T6 = 14
R_T7 = 15
R_T9 = 25
R_SP = 29
R_RA = 31

KSEG0_BASE = 0x80000000
ROM_LOAD_OFFSET = 0x1000
RAM_LOAD_ADDRESS = 0x80000400
LOGGER_ROM_OFF = 0x3CB0
HVI_RETURN_TRAMP_ROM_OFF = 0x3CE4
DFB_RETURN_TRAMP_ROM_OFF = 0x3CFC

HOOK_ORDER = ("BCLR", "DFB1", "HVI1")


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
    return RAM_LOAD_ADDRESS + (rom_off - ROM_LOAD_OFFSET)


def ascii_word(text):
    data = text.encode("ascii")
    if len(data) != 4:
        raise ValueError("marker text must be exactly 4 ASCII bytes")
    return int.from_bytes(data, "big")


def write_words(rom, off, words):
    for i, value in enumerate(words):
        rom[off + i * 4:off + i * 4 + 4] = word(value)


def ensure_cave(rom, off, words, label):
    size = len(words) * 4
    if any(rom[off:off + size]):
        raise ValueError(f"{label} cave is not empty at 0x{off:X}")


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


def make_aux_logger():
    # Writes the four-byte marker to the SC64 AUX register. SC64 register
    # access is locked after reset, so each log call performs the documented
    # unlock sequence before writing AUX.
    return [
        lui(R_T0, 0xBFFF),
        sw(R_ZERO, 0x0010, R_T0),
        lui(R_T1, 0x5F55),
        ori(R_T1, R_T1, 0x4E4C),
        sw(R_T1, 0x0010, R_T0),
        lui(R_T1, 0x4F43),
        ori(R_T1, R_T1, 0x4B5F),
        sw(R_T1, 0x0010, R_T0),
        jr(R_RA),
        sw(R_A0, 0x0018, R_T0),
    ]


def make_noop_logger():
    return [
        jr(R_RA),
        nop(),
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


def make_dfb_return_trampoline():
    return [
        sw(R_T6, 0x417C, R_AT),
        or_(R_T7, R_A1, R_V0),
        or_(R_T9, R_RA, R_ZERO),
        sw(R_T7, 0x4180, R_AT),
        *log_call("DFB1"),
        jr(R_T9),
        nop(),
    ]


def parse_hooks(raw):
    if raw in (None, "", "all"):
        return set(HOOK_ORDER)
    if raw == "none":
        return set()
    hooks = {part.strip().upper() for part in raw.split(",") if part.strip()}
    unknown = hooks.difference(HOOK_ORDER)
    if unknown:
        raise ValueError(f"unknown hook(s): {', '.join(sorted(unknown))}")
    return hooks


def apply_instrumentation(rom, hooks=None, transport="isv"):
    hooks = set(HOOK_ORDER if hooks is None else hooks)
    report = []
    logger = (
        make_aux_logger()
        if transport == "aux"
        else make_noop_logger()
        if transport == "none"
        else make_logger()
    )
    hvi_trampoline = make_hvi_return_trampoline()
    dfb_trampoline = make_dfb_return_trampoline()

    ensure_cave(rom, LOGGER_ROM_OFF, logger, "logger")
    if "HVI1" in hooks:
        ensure_cave(rom, HVI_RETURN_TRAMP_ROM_OFF, hvi_trampoline, "HVI trampoline")
    if "DFB1" in hooks:
        ensure_cave(rom, DFB_RETURN_TRAMP_ROM_OFF, dfb_trampoline, "DFB trampoline")

    write_words(rom, LOGGER_ROM_OFF, logger)
    report.append({"offset": f"0x{LOGGER_ROM_OFF:X}", "note": f"{transport.upper()} marker logger"})

    if "HVI1" in hooks:
        write_words(rom, HVI_RETURN_TRAMP_ROM_OFF, hvi_trampoline)
        report.append({"offset": f"0x{HVI_RETURN_TRAMP_ROM_OFF:X}", "note": "VI return breadcrumb trampoline"})

    if "DFB1" in hooks:
        write_words(rom, DFB_RETURN_TRAMP_ROM_OFF, dfb_trampoline)
        report.append({"offset": f"0x{DFB_RETURN_TRAMP_ROM_OFF:X}", "note": "framebuffer global setup breadcrumb trampoline"})

    # Framebuffer clear function return path. The original function has saved
    # RA on the stack, so this can log and then return through t9.
    if "BCLR" in hooks:
        write_words(rom, 0x3D4C, [
            lw(R_RA, 0x0014, R_SP),
            or_(R_T9, R_RA, R_ZERO),
            *log_call("BCLR"),
            jr(R_T9),
            addiu(R_SP, R_SP, 0x0018),
        ])
        report.append({"offset": "0x3D4C", "note": "log after framebuffer clear function"})

    # Framebuffer global setup return path. The original block computes and
    # stores both framebuffer globals; trampoline so those instructions remain
    # intact before logging.
    if "DFB1" in hooks:
        write_words(rom, 0x65A4, [
            j(runtime(DFB_RETURN_TRAMP_ROM_OFF)),
            lui(R_AT, 0x8002),
        ])
        report.append({"offset": "0x65A4", "note": "jump to framebuffer global setup breadcrumb"})

    # VI setup function return path. The delay slot still restores SP before
    # the trampoline logs and returns to the original caller.
    if "HVI1" in hooks:
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
    hooks = parse_hooks(args.hooks)
    report = apply_instrumentation(rom, hooks, args.transport)
    crc1, crc2 = update_n64_crc_6102(rom)
    Path(args.out_rom).write_bytes(rom)
    summary = {
        "base_rom": args.base_rom,
        "out_rom": args.out_rom,
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X}{crc2:08X}",
        "transport": args.transport,
        "debug_command": (
            "sc64deployer.exe debug --isv 0x03FF0000 --no-writeback"
            if args.transport == "isv"
            else "sc64deployer.exe debug --no-writeback"
            if args.transport == "aux"
            else None
        ),
        "hooks": [hook for hook in HOOK_ORDER if hook in hooks],
        "expected_markers": [] if args.transport == "none" else [f"TND:{hook}" for hook in HOOK_ORDER if hook in hooks],
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
    parser.add_argument("--hooks", default="all", help="Comma-separated hook list: BCLR,DFB1,HVI1; or all/none")
    parser.add_argument("--transport", choices=("isv", "aux", "none"), default="isv")
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
