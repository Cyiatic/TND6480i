#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_render_state_revert_candidates import copy_save
from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/tnd58.z64")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_framebuffer_base_probe_candidates_20260517.json")

CANDIDATES = [
    {
        "name": "t58fb8040",
        "purpose": (
            "Move only the low framebuffer base from 0x80300000 to 0x80400000 on "
            "the current tlbpages58 base. This retests the earlier split8040 idea "
            "after the high-framebuffer/TLB overlap was removed."
        ),
        "patches": [
            (0x3D30, 0x3C048040, "clear fb0 base upper 0x80400000"),
            (0x6584, 0x3C048040, "fb0 global base upper 0x80400000"),
        ],
    },
    {
        "name": "t58fb8020",
        "purpose": (
            "Move only the low framebuffer base from 0x80300000 down to 0x80200000. "
            "This is a collision probe for Party/End, not a likely final layout."
        ),
        "patches": [
            (0x3D30, 0x3C048020, "clear fb0 base upper 0x80200000"),
            (0x6584, 0x3C048020, "fb0 global base upper 0x80200000"),
        ],
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def build_one(spec, base):
    rom = bytearray(base)
    patches = []
    for offset, value, note in spec["patches"]:
        old = word(rom, offset)
        write_word(rom, offset, value)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{value:08X}",
                "note": note,
                "changed": old != value,
            }
        )
    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = OUT_DIR / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": patches,
        "save_outputs": copy_save(out_rom),
        "direct_probe_focus": ["Party", "The End", "City", "Hotel"],
    }


def main():
    base = BASE_ROM.read_bytes()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reports = [build_one(spec, base) for spec in CANDIDATES]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
