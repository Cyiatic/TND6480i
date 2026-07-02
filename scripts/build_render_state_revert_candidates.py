#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/tnd58.z64")
BASE_SAVE = Path("artifacts/generated/tnd58.sav")
STOCK_ROM = Path("artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_render_state_revert_candidates_20260517.json")

OFFSETS = {
    "direct_table0": [
        (0x4F354, "direct render dimensions table 0"),
    ],
    "global_xy_helpers": [
        (0xBB730, "getWidth320or440 low-res return"),
        (0xBB740, "getWidth320or440 hi-res return"),
        (0xBB754, "getHeight330or240 low-res return"),
        (0xBB764, "getHeight330or240 hi-res return"),
    ],
    "camera_view": [
        (0xBB7A4, "camera viewport width"),
        (0xBB89C, "camera widescreen viewport height"),
        (0xBB8B8, "camera cinema viewport height"),
        (0xBB8C0, "camera fullscreen viewport height"),
    ],
}

CANDIDATES = [
    {
        "name": "t58rd0",
        "groups": ["direct_table0"],
        "purpose": "Restore only direct render dimensions table 0 to stock TND to test title-card/transition ownership.",
    },
    {
        "name": "t58rxy",
        "groups": ["global_xy_helpers"],
        "purpose": "Restore only the global width/height helper returns to stock TND, while keeping framebuffer/VI and per-view viewport edits.",
    },
    {
        "name": "t58rd0xy",
        "groups": ["direct_table0", "global_xy_helpers"],
        "purpose": "Restore direct table 0 plus global width/height helpers, testing whether the failing level transitions need stock-sized setup while later viewport paths remain patched.",
    },
    {
        "name": "t58rd0cam",
        "groups": ["direct_table0", "camera_view"],
        "purpose": "Restore direct table 0 and camera viewport dimensions, keeping non-camera gameplay viewport edits.",
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def copy_save(out_rom):
    if not BASE_SAVE.exists():
        return []
    save = BASE_SAVE.read_bytes()
    eep = save if len(save) >= 2048 else save + b"\0" * (2048 - len(save))
    outputs = []
    for path, data in ((out_rom.with_suffix(".sav"), save), (out_rom.with_suffix(".eep"), eep)):
        path.write_bytes(data)
        outputs.append({"path": str(path), "bytes": len(data), "md5": md5(data)})
    return outputs


def build_one(spec, base, stock):
    rom = bytearray(base)
    patches = []
    for group in spec["groups"]:
        for offset, note in OFFSETS[group]:
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
        "direct_probe_focus": ["Party", "Hotel", "City", "Volcano", "The End"],
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
