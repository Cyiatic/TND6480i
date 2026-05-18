#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

from build_tnd480i_candidate import update_n64_crc_6102


MAIN_ROM_TO_RUNTIME_DELTA = 0x34B30

WRAPPER_SRC_OFF = 0x3C7F8
WRAPPER_LEN = 0xC4
WRAPPER_INNER_JAL_OFF = 0x3C8A4

BLITTER_SRC_OFF = 0x4FD70
BLITTER_LEN = 0x4A0

CLONE_CAVE_OFF = 0x4F498
CLONE_CAVE_LEN = 0x594
CLONE_WRAPPER_OFF = CLONE_CAVE_OFF
CLONE_BLITTER_OFF = CLONE_WRAPPER_OFF + WRAPPER_LEN

CALLSITES = {
    "sniper": 0x3C984,
    "file-select": 0x41030,
}

TEXTURE_SETUPS = {
    "stock": {
        0x4FDEC: 0x3C17070D,
        0x4FDFC: 0x3C0AE46D,
        0x4FE34: 0x3C018005,
        0x4FE3C: 0x36F7B026,
        0x4FE44: 0xC4301CF0,
        0x4FF00: 0x3C0E006D,
    },
    "ge480": {
        0x4FDEC: 0x3C170713,
        0x4FDFC: 0x3C0AE49F,
        0x4FE34: 0x3C0143D7,
        0x4FE3C: 0x36F7F006,
        0x4FE44: 0x44818000,
        0x4FF00: 0x3C0E009F,
    },
    "rw1": {
        # Minimal file-select backdrop coverage fix found by hardware probe dmyrw1.
        0x4FDFC: 0x3C0AE49F,
    },
}

GEOMETRY_SETUPS = {
    "inherit": {},
    "ge480": {
        0x500EC: 0x2519001D,
        0x500FC: 0x250E001C,
        0x50148: 0x2519001D,
        0x50168: 0x2519001C,
        0x501AC: 0x292101AE,
        0x501B4: 0x26100280,
    },
    "stock_strip": {
        0x500EC: 0x25190011,
        0x500FC: 0x250E0010,
        0x50148: 0x25190011,
        0x50168: 0x25190010,
    },
    "stock_row": {
        0x501AC: 0x2921012C,
    },
    "stock_stride": {
        0x501B4: 0x261001B8,
    },
    "tnd508_stride": {
        0x501B4: 0x261001FC,
    },
    "tnd508_row480_stride": {
        0x501AC: 0x292101E0,
        0x501B4: 0x261001FC,
    },
    "tnd508_row507_stride": {
        0x501AC: 0x292101FB,
        0x501B4: 0x261001FC,
    },
    "tnd508_strip20_stride": {
        0x500EC: 0x25190015,
        0x500FC: 0x250E0014,
        0x50148: 0x25190015,
        0x50168: 0x25190014,
        0x501B4: 0x261001FC,
    },
    "tnd508_strip20_row507_stride": {
        0x500EC: 0x25190015,
        0x500FC: 0x250E0014,
        0x50148: 0x25190015,
        0x50168: 0x25190014,
        0x501AC: 0x292101FB,
        0x501B4: 0x261001FC,
    },
    "stock_row_stride": {
        0x501AC: 0x2921012C,
        0x501B4: 0x261001B8,
    },
    "stock_all": {
        0x500EC: 0x25190011,
        0x500FC: 0x250E0010,
        0x50148: 0x25190011,
        0x50168: 0x25190010,
        0x501AC: 0x2921012C,
        0x501B4: 0x261001B8,
    },
}


def runtime_addr(rom_off):
    return 0x7F000000 + rom_off - MAIN_ROM_TO_RUNTIME_DELTA


def jal_word(addr):
    return 0x0C000000 | ((addr >> 2) & 0x03FFFFFF)


def md5(data):
    return hashlib.md5(data).hexdigest()


def read_word(rom, off):
    return int.from_bytes(rom[off:off + 4], "big")


def write_word(rom, off, value):
    rom[off:off + 4] = value.to_bytes(4, "big")


def ensure_zero_cave(rom):
    cave = rom[CLONE_CAVE_OFF:CLONE_CAVE_OFF + CLONE_CAVE_LEN]
    if any(cave):
        raise ValueError(f"clone cave is not zeroed at 0x{CLONE_CAVE_OFF:X}")
    end = CLONE_BLITTER_OFF + BLITTER_LEN
    if end > CLONE_CAVE_OFF + CLONE_CAVE_LEN:
        raise ValueError(
            f"clone payload ends at 0x{end:X}, beyond cave end 0x{CLONE_CAVE_OFF + CLONE_CAVE_LEN:X}"
        )


def clone_wrapper_and_blitter(rom, texture_setup, geometry_setup):
    report = []
    ensure_zero_cave(rom)

    wrapper = bytes(rom[WRAPPER_SRC_OFF:WRAPPER_SRC_OFF + WRAPPER_LEN])
    blitter = bytearray(rom[BLITTER_SRC_OFF:BLITTER_SRC_OFF + BLITTER_LEN])

    rom[CLONE_WRAPPER_OFF:CLONE_WRAPPER_OFF + WRAPPER_LEN] = wrapper
    rom[CLONE_BLITTER_OFF:CLONE_BLITTER_OFF + BLITTER_LEN] = blitter

    inner_clone_jal_off = CLONE_WRAPPER_OFF + (WRAPPER_INNER_JAL_OFF - WRAPPER_SRC_OFF)
    old_inner = read_word(rom, inner_clone_jal_off)
    new_inner = jal_word(runtime_addr(CLONE_BLITTER_OFF))
    write_word(rom, inner_clone_jal_off, new_inner)
    report.append({
        "offset": f"0x{inner_clone_jal_off:X}",
        "old": f"0x{old_inner:08X}",
        "new": f"0x{new_inner:08X}",
        "note": "clone wrapper inner call routed to cloned blitter",
    })

    for source_off, value in TEXTURE_SETUPS[texture_setup].items():
        clone_off = CLONE_BLITTER_OFF + (source_off - BLITTER_SRC_OFF)
        old = read_word(rom, clone_off)
        write_word(rom, clone_off, value)
        report.append({
            "offset": f"0x{clone_off:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{value:08X}",
            "note": f"cloned blitter {texture_setup} texture setup from source 0x{source_off:X}",
        })

    for source_off, value in GEOMETRY_SETUPS[geometry_setup].items():
        clone_off = CLONE_BLITTER_OFF + (source_off - BLITTER_SRC_OFF)
        old = read_word(rom, clone_off)
        write_word(rom, clone_off, value)
        report.append({
            "offset": f"0x{clone_off:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{value:08X}",
            "note": f"cloned blitter {geometry_setup} geometry from source 0x{source_off:X}",
        })

    return report


def route_callsites(rom, routes):
    report = []
    for name in routes:
        off = CALLSITES[name]
        old = read_word(rom, off)
        new = jal_word(runtime_addr(CLONE_WRAPPER_OFF))
        write_word(rom, off, new)
        report.append({
            "offset": f"0x{off:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{new:08X}",
            "note": f"route {name} wrapper call to cloned wrapper at 0x{CLONE_WRAPPER_OFF:X}",
        })
    return report


def build(args):
    rom = bytearray(Path(args.base_rom).read_bytes())
    patches = clone_wrapper_and_blitter(rom, args.texture_setup, args.geometry_setup)
    patches.extend(route_callsites(rom, args.route))
    crc1, crc2 = update_n64_crc_6102(rom)
    Path(args.out_rom).write_bytes(rom)
    summary = {
        "base_rom": args.base_rom,
        "out_rom": args.out_rom,
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X}{crc2:08X}",
        "texture_setup": args.texture_setup,
        "geometry_setup": args.geometry_setup,
        "routes": args.route,
        "clone_cave": {
            "rom_offset": f"0x{CLONE_CAVE_OFF:X}",
            "runtime_wrapper": f"0x{runtime_addr(CLONE_WRAPPER_OFF):08X}",
            "runtime_blitter": f"0x{runtime_addr(CLONE_BLITTER_OFF):08X}",
            "bytes_used": f"0x{CLONE_BLITTER_OFF + BLITTER_LEN - CLONE_CAVE_OFF:X}",
            "bytes_available": f"0x{CLONE_CAVE_LEN:X}",
        },
        "patches": patches,
    }
    if args.report:
        Path(args.report).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", required=True)
    parser.add_argument("--out-rom", required=True)
    parser.add_argument("--report")
    parser.add_argument("--texture-setup", choices=sorted(TEXTURE_SETUPS), required=True)
    parser.add_argument("--geometry-setup", choices=sorted(GEOMETRY_SETUPS), default="inherit")
    parser.add_argument("--route", choices=sorted(CALLSITES), nargs="+", required=True)
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
