#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/tnd8040.z64")
BASE_SAVE = Path("artifacts/generated/tnd8040.sav")
STOCK_ROM = Path("artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_tnd8040_blitter_rollback_candidates_20260517.json")

GROUPS = {
    "shared_texture_setup": [
        (0x4FDEC, "shared title/sniper texture setup upper"),
        (0x4FDFC, "shared title/sniper texture rectangle target width"),
        (0x4FE34, "shared title/sniper height load upper"),
        (0x4FE3C, "shared title/sniper texture setup lower"),
        (0x4FE44, "shared title/sniper height load/use"),
        (0x4FF00, "shared title/sniper texture rectangle lower width"),
    ],
    "shared_strip_steps": [
        (0x500EC, "shared title/sniper negative-x strip step"),
        (0x500FC, "shared title/sniper negative-x strip step"),
        (0x50148, "shared title/sniper positive-x strip step"),
        (0x50168, "shared title/sniper positive-x strip step"),
    ],
    "shared_row_stride": [
        (0x501AC, "shared title/sniper source row loop limit"),
        (0x501B4, "shared title/sniper source stride"),
    ],
}

CANDIDATES = [
    {
        "name": "t8040texstk",
        "groups": ["shared_texture_setup"],
        "purpose": (
            "Keep tnd8040's gameplay/framebuffer fixes, but restore only the "
            "shared title/sniper texture-setup words to stock TND. This tests "
            "whether the short top intro/title rectangle is caused by the "
            "target-size part of the GE-style blitter transplant."
        ),
        "direct_probe_focus": ["Party", "The End"],
    },
    {
        "name": "t8040blstk",
        "groups": ["shared_texture_setup", "shared_strip_steps", "shared_row_stride"],
        "purpose": (
            "Keep tnd8040's gameplay/framebuffer fixes, but restore the whole "
            "shared title/sniper blitter geometry cluster to stock TND. This is "
            "a conservative playability probe: front/title scenes may stop "
            "being 480i-polished, but they should avoid broken GE/TND mixed "
            "blitter state if that is what makes title cards collapse into a "
            "short strip."
        ),
        "direct_probe_focus": ["Party", "The End", "City"],
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
        "direct_probe_focus": spec["direct_probe_focus"],
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
