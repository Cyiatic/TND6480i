#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/game_h460_top10_stock_dossier_tables_current.z64")
STOCK_ROM = Path("artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64")

OUT_SPECS = [
    {
        "name": "game_h460_top10_stock_dossier_camheightstock_current",
        "purpose": "Preserve current best gameplay/dossier work, but restore only camera viewport heights to stock.",
        "offsets": [
            (0xBB89C, "camera widescreen viewport height"),
            (0xBB8B8, "camera cinema viewport height"),
            (0xBB8C0, "camera fullscreen viewport height"),
        ],
    },
    {
        "name": "game_h460_top10_stock_dossier_camviewstock_current",
        "purpose": "Preserve current best gameplay/dossier work, but restore camera viewport width and heights to stock.",
        "offsets": [
            (0xBB7A4, "camera viewport width"),
            (0xBB89C, "camera widescreen viewport height"),
            (0xBB8B8, "camera cinema viewport height"),
            (0xBB8C0, "camera fullscreen viewport height"),
        ],
    },
    {
        "name": "game_h460_top10_stock_dossier_dim0_camviewstock_diag",
        "purpose": "Diagnostic only: additionally restore direct render dimension table 0 to stock to test whether table0 drives cutscene/playability failures.",
        "offsets": [
            (0x4F354, "direct render dimensions table 0"),
            (0xBB7A4, "camera viewport width"),
            (0xBB89C, "camera widescreen viewport height"),
            (0xBB8B8, "camera cinema viewport height"),
            (0xBB8C0, "camera fullscreen viewport height"),
        ],
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def build_one(base, stock, spec):
    rom = bytearray(base)
    patches = []
    for offset, note in spec["offsets"]:
        old = word(rom, offset)
        new = word(stock, offset)
        write_word(rom, offset, new)
        patches.append({
            "offset": f"0x{offset:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{new:08X}",
            "note": note,
        })
    update_n64_crc_6102(rom)
    out_rom = Path("artifacts/generated") / f"{spec['name']}.z64"
    out_rom.parent.mkdir(parents=True, exist_ok=True)
    out_rom.write_bytes(rom)
    header_crc = f"{word(rom, 0x10):08X} {word(rom, 0x14):08X}"
    report = {
        "base_rom": str(BASE_ROM),
        "stock_source_rom": str(STOCK_ROM),
        "out_rom": str(out_rom),
        "purpose": spec["purpose"],
        "out_md5": md5(rom),
        "header_crc": header_crc,
        "patches": patches,
        "notes": [
            "Built from the promoted current best ROM.",
            "Preserves the stock dossier table revert.",
            "Does not touch non-camera gameplay h460/top10 viewport crop words.",
            "Do not upload until emulator/offline comparison identifies a useful delta.",
        ],
    }
    report_path = Path("reports") / f"tnd480i_{spec['name']}_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    base = BASE_ROM.read_bytes()
    stock = STOCK_ROM.read_bytes()
    reports = [build_one(base, stock, spec) for spec in OUT_SPECS]
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
