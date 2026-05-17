#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_render_state_revert_candidates import copy_save
from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/tnd8040.z64")
STOCK_ROM = Path("artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_tnd8040_camera_probe_candidates_20260517.json")

SPECS = [
    {
        "name": "t8040nr",
        "purpose": (
            "Keep the promoted tnd8040 framebuffer placement, but NOP the "
            "cameraBufferToggle viSetFrameBuf2(resolution) redirect. This retests "
            "the old noresfb idea after the low framebuffer move fixed Party/End/"
            "City/Hotel/Volcano load and render stability."
        ),
        "patches": [
            {
                "offset": 0xBBB8C,
                "value": 0x00000000,
                "note": "NOP jal viSetFrameBuf2(resolution)",
            }
        ],
        "direct_probe_focus": ["Party", "The End", "Tower", "Boat", "Hotel", "Volcano"],
    },
    {
        "name": "t8040camstk",
        "purpose": (
            "Keep tnd8040, but restore only cameraBufferToggle viewport width and "
            "height constants to stock TND. This is a playability/shape diagnostic, "
            "not a final 480i camera solution."
        ),
        "patches": [
            {"offset": 0xBB7A4, "stock": True, "note": "camera viewport width"},
            {"offset": 0xBB89C, "stock": True, "note": "camera widescreen viewport height"},
            {"offset": 0xBB8B8, "stock": True, "note": "camera cinema viewport height"},
            {"offset": 0xBB8C0, "stock": True, "note": "camera fullscreen viewport height"},
        ],
        "direct_probe_focus": ["Party", "The End", "Tower", "Boat"],
    },
    {
        "name": "t8040camnr",
        "purpose": (
            "Combine stock cameraBufferToggle viewport dimensions with the noresfb "
            "redirect NOP on top of tnd8040. This is a fallback diagnostic if "
            "noresfb alone changes cutscene shape but not enough."
        ),
        "patches": [
            {"offset": 0xBB7A4, "stock": True, "note": "camera viewport width"},
            {"offset": 0xBB89C, "stock": True, "note": "camera widescreen viewport height"},
            {"offset": 0xBB8B8, "stock": True, "note": "camera cinema viewport height"},
            {"offset": 0xBB8C0, "stock": True, "note": "camera fullscreen viewport height"},
            {
                "offset": 0xBBB8C,
                "value": 0x00000000,
                "note": "NOP jal viSetFrameBuf2(resolution)",
            },
        ],
        "direct_probe_focus": ["Party", "The End", "Tower", "Boat"],
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def build_one(spec, base, stock):
    rom = bytearray(base)
    patches = []
    for patch in spec["patches"]:
        offset = patch["offset"]
        old = word(rom, offset)
        new = word(stock, offset) if patch.get("stock") else patch["value"]
        write_word(rom, offset, new)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{new:08X}",
                "note": patch["note"],
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
        "direct_probe_focus": spec["direct_probe_focus"],
    }


def main():
    base = BASE_ROM.read_bytes()
    stock = STOCK_ROM.read_bytes()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reports = [build_one(spec, base, stock) for spec in SPECS]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
