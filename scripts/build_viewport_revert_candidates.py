#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_render_state_revert_candidates import copy_save
from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/tnd58.z64")
STOCK_ROM = Path("artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_viewport_revert_candidates_20260517.json")

GROUPS = {
    "default_view": [
        (0xBB7C0, "non-camera widescreen viewport width"),
        (0xBB7D4, "non-camera default viewport width branch delay"),
        (0xBB7DC, "non-camera cinema viewport width"),
        (0xBB7E0, "non-camera fallback viewport width"),
        (0xBB91C, "non-camera default viewport height"),
        (0xBB954, "non-camera fallback viewport height"),
        (0xBBA80, "non-camera default viewport top"),
    ],
    "camera_view": [
        (0xBB7A4, "cameraBufferToggle viewport width"),
        (0xBB89C, "camera widescreen viewport height"),
        (0xBB8B8, "camera cinema viewport height"),
        (0xBB8C0, "camera fullscreen viewport height"),
    ],
    "other_view": [
        (0xBB790, "4-player viewport width"),
        (0xBB83C, "4-player viewport ULX"),
        (0xBB874, "4-player viewport height"),
        (0xBB8FC, "widescreen animated viewport height offset"),
        (0xBB944, "cinema animated viewport height offset"),
        (0xBB9A0, "2-player viewport ULY"),
        (0xBB9D8, "4-player viewport ULY"),
        (0xBBA60, "widescreen animated viewport ULY offset"),
        (0xBBAA8, "cinema animated viewport ULY offset"),
    ],
    "global_xy": [
        (0xBB730, "getWidth320or440 low-res return"),
        (0xBB740, "getWidth320or440 hi-res return"),
        (0xBB754, "getHeight330or240 low-res return"),
        (0xBB764, "getHeight330or240 hi-res return"),
    ],
}

CANDIDATES = [
    {
        "name": "t58rdef",
        "groups": ["default_view"],
        "purpose": "Restore only normal non-camera single-player viewport dimensions to stock TND.",
    },
    {
        "name": "t58rdefcam",
        "groups": ["default_view", "camera_view"],
        "purpose": "Restore normal plus camera viewport dimensions, while keeping global 640x480 helpers.",
    },
    {
        "name": "t58rvw",
        "groups": ["default_view", "camera_view", "other_view"],
        "purpose": "Restore all viewport return dimensions except global width/height helpers.",
    },
    {
        "name": "t58rvwxy",
        "groups": ["default_view", "camera_view", "other_view", "global_xy"],
        "purpose": "Restore the whole gameplay viewport/helper family to stock TND as a playability control.",
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def build_one(spec, base, stock):
    rom = bytearray(base)
    patches = []
    for group in spec["groups"]:
        for offset, note in GROUPS[group]:
            old = word(rom, offset)
            new = word(stock, offset)
            write_word(rom, offset, new)
            patches.append(
                {
                    "group": group,
                    "offset": f"0x{offset:X}",
                    "old": f"0x{old:08X}",
                    "new": f"0x{new:08X}",
                    "note": note,
                    "changed": old != new,
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
        "stock_source_rom": str(STOCK_ROM),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": patches,
        "save_outputs": copy_save(out_rom),
        "direct_probe_focus": ["Party", "City", "The End", "Hotel", "Volcano"],
    }


def main():
    base = BASE_ROM.read_bytes()
    stock = STOCK_ROM.read_bytes()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reports = [build_one(spec, base, stock) for spec in CANDIDATES]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
