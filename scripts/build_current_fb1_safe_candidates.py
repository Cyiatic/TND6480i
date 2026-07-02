#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


CURRENT_BEST = Path("artifacts/generated/game_h460_top10_stock_dossier_tables_current.z64")
CAMVIEW_BASE = Path("artifacts/generated/game_h460_top10_stock_dossier_camviewstock_current.z64")


FB1_CANDIDATES = [
    {
        "tag": "fb1_8060",
        "base": 0x80600000,
        "note": "below expansion TLB cache; conservative distance from 0x8070xxxx",
    },
    {
        "tag": "fb1_8066",
        "base": 0x80660000,
        "note": "highest aligned 0x96000 buffer ending exactly before 0x806F6000",
    },
    {
        "tag": "fb1_8056",
        "base": 0x80560000,
        "note": "below isolated 0x80600000 constant and expansion TLB cache",
    },
]


def out_specs():
    specs = []
    for fb1 in FB1_CANDIDATES:
        specs.append({
            "name": f"game_h460_top10_stock_dossier_{fb1['tag']}_current",
            "base": CURRENT_BEST,
            "fb1": fb1["base"],
            "placement_note": fb1["note"],
            "purpose": (
                "Preserve current best gameplay/dossier work and fb0 at "
                "0x80300000, but move fb1 from 0x8076A000 below the Expansion "
                "Pak TLB cache allocated at about 0x806F6000-0x807A9FFF."
            ),
        })
    specs.append({
        "name": "game_h460_top10_stock_dossier_fb1_8066_camviewstock_current",
        "base": CAMVIEW_BASE,
        "fb1": 0x80660000,
        "placement_note": "camera-view-stock diagnostic with fb1 below expansion TLB cache",
        "purpose": (
            "Same fb1-safe placement, starting from the camera-view-stock "
            "diagnostic base."
        ),
    })
    return specs


def fb1_patches(fb1):
    upper = (fb1 >> 16) & 0xFFFF
    lower = fb1 & 0xFFFF
    return [
        # viInitBuffers second clear.
        (0x3D48, 0x3C040000 | upper, f"clear fb1 base upper 0x{fb1:08X}"),
        (0x3D4C, 0x34840000 | lower, f"clear fb1 base lower 0x{fb1:08X}"),

        # framebuffer global setup: cfb_16[1].
        (0x658C, 0x3C050000 | upper, f"fb1 base upper 0x{fb1:08X}"),
        (0x6590, 0x34A50000 | lower, f"fb1 base lower 0x{fb1:08X}"),
    ]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def build_one(spec):
    base_path = spec["base"]
    rom = bytearray(base_path.read_bytes())
    patch_report = []

    for offset, new_value, note in fb1_patches(spec["fb1"]):
        old_value = word(rom, offset)
        write_word(rom, offset, new_value)
        patch_report.append({
            "offset": f"0x{offset:X}",
            "old": f"0x{old_value:08X}",
            "new": f"0x{new_value:08X}",
            "note": note,
        })

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = Path("artifacts/generated") / f"{spec['name']}.z64"
    out_rom.parent.mkdir(parents=True, exist_ok=True)
    out_rom.write_bytes(rom)

    report = {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "base_rom": str(base_path),
        "base_md5": md5(base_path.read_bytes()),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "framebuffer_layout": {
            "fb0": "0x80300000-0x80395FFF",
            "fb1": f"0x{spec['fb1']:08X}-0x{spec['fb1'] + 0x95FFF:08X}",
            "placement_note": spec["placement_note"],
            "tlb_cache_reasoning": (
                "direct code at 0x241C-0x2430 stores g_tlbmanageTlbAllocatedBlock "
                "as 0x802F6000 plus the Expansion Pak delta at 0x8000050C; on "
                "8 MB systems that puts the page cache at about 0x806F6000-0x807A9FFF."
            ),
        },
        "patches": patch_report,
    }
    out_report = Path("reports") / f"tnd480i_{spec['name']}_report.json"
    out_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "out_rom": str(out_rom),
        "out_md5": report["out_md5"],
        "header_crc": report["header_crc"],
    }, indent=2))
    return report


def main():
    reports = [build_one(spec) for spec in out_specs()]
    summary = Path("reports/tnd480i_fb1_safe_candidates_20260516.json")
    summary.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
