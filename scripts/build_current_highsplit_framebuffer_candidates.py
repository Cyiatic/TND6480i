#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


CURRENT_BEST = Path("artifacts/generated/game_h460_top10_stock_dossier_tables_current.z64")
CAMVIEW_BASE = Path("artifacts/generated/game_h460_top10_stock_dossier_camviewstock_current.z64")


FB0_CANDIDATES = [
    {
        "tag": "split803b8_8076",
        "base": 0x803B8000,
        "note": "just above the decomp-visible stack/static constants",
    },
    {
        "tag": "split8046_8076",
        "base": 0x80460000,
        "note": "above the old 0x80400000 black-screen range and below 0x80500000",
    },
    {
        "tag": "split8056_8076",
        "base": 0x80560000,
        "note": "above the isolated 0x80500000 constant and below 0x80600000",
    },
    {
        "tag": "split8066_8076",
        "base": 0x80660000,
        "note": "above the isolated 0x80600000 constant and below 0x80702520",
    },
    {
        "tag": "split806d_8076",
        "base": 0x806D4000,
        "note": "GE-style fb0 base; retained as a negative/control candidate",
    },
]


def make_out_specs():
    specs = []
    for fb0 in FB0_CANDIDATES:
        specs.append({
            "name": f"game_h460_top10_stock_dossier_{fb0['tag']}_current",
            "base": CURRENT_BEST,
            "fb0": fb0["base"],
            "fb0_tag": fb0["tag"],
            "placement_note": fb0["note"],
            "purpose": (
                "Preserve the current best split-framebuffer logic and dossier fixes, "
                f"but move fb0 from 0x80300000 to 0x{fb0['base']:08X} so it no "
                "longer overlaps the GE/TND TLB paging cache below sp_boot."
            ),
        })
    specs.append({
        "name": "game_h460_top10_stock_dossier_split806d_8076_camviewstock_current",
        "base": CAMVIEW_BASE,
        "fb0": 0x806D4000,
        "fb0_tag": "split806d_8076",
        "placement_note": "GE-style fb0 base retained for the camera-view-stock diagnostic base",
        "purpose": (
            "Same split806d/8076 framebuffer placement, starting from the "
            "camera-view-stock diagnostic base."
        ),
    })
    return specs


def fb0_patches(fb0):
    upper = (fb0 >> 16) & 0xFFFF
    lower = fb0 & 0xFFFF
    return [
        # viInitBuffers: keep the existing two-clear split-buffer path, but
        # clear fb0 at the candidate base. fb1 remains 0x8076A000.
        (0x3D30, 0x3C040000 | upper, f"clear fb0 base upper 0x{fb0:08X}"),
        (0x3D34, 0x34840000 | lower, f"clear fb0 base lower 0x{fb0:08X}"),

        # framebuffer globals: keep the existing split selector path and store
        # cfb_16[0] = fb0 | 0xA0000000, cfb_16[1] = 0xA076A000.
        (0x6584, 0x3C040000 | upper, f"fb0 base upper 0x{fb0:08X}"),
        (0x6588, 0x34840000 | lower, f"fb0 base lower 0x{fb0:08X}"),
    ]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def build_one(spec):
    base_path = spec["base"]
    rom = bytearray(base_path.read_bytes())
    patch_report = []

    for offset, new_value, note in fb0_patches(spec["fb0"]):
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
            "fb0": f"0x{spec['fb0']:08X}-0x{spec['fb0'] + 0x95FFF:08X}",
            "fb1": "0x8076A000-0x807FFFFF",
            "placement_note": spec["placement_note"],
            "tlb_cache_risk": (
                "fb0 no longer covers 0x80300000-0x80395FFF, which overlaps "
                "the decomp-inferred TLB page cache region below sp_boot."
            ),
            "selector": "unchanged split framebuffer selector at 0x46B4-0x46F0",
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
    reports = [build_one(spec) for spec in make_out_specs()]
    summary = Path("reports/tnd480i_highsplit_framebuffer_candidates_20260516.json")
    summary.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
