#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


CURRENT_BEST = Path("artifacts/generated/game_h460_top10_stock_dossier_tables_current.z64")
CAMVIEW_BASE = Path("artifacts/generated/game_h460_top10_stock_dossier_camviewstock_current.z64")


TLB_BASES = [
    {
        "tag": "tlb8060",
        # Direct code adds the Expansion Pak delta at 0x8000050C. With 8 MB
        # RDRAM, 0x80200000 becomes 0x80600000.
        "direct_base": 0x80200000,
        "expanded_base": 0x80600000,
        "note": "moves TLB page cache below fb1 while leaving framebuffers untouched",
    },
    {
        "tag": "tlb805c",
        "direct_base": 0x801C0000,
        "expanded_base": 0x805C0000,
        "note": "lower cache placement with more gap below fb1",
    },
]


def out_specs():
    specs = []
    for tlb in TLB_BASES:
        specs.append({
            "name": f"game_h460_top10_stock_dossier_{tlb['tag']}_current",
            "base": CURRENT_BEST,
            **tlb,
            "purpose": (
                "Preserve current best framebuffers and gameplay/dossier fixes, "
                "but relocate the Expansion Pak TLB page cache away from fb1."
            ),
        })
    specs.append({
        "name": "game_h460_top10_stock_dossier_tlb8060_camviewstock_current",
        "base": CAMVIEW_BASE,
        "tag": "tlb8060",
        "direct_base": 0x80200000,
        "expanded_base": 0x80600000,
        "note": "camera-view-stock diagnostic with TLB cache below fb1",
        "purpose": (
            "Same TLB cache relocation, starting from the camera-view-stock "
            "diagnostic base."
        ),
    })
    return specs


def tlb_patches(direct_base):
    upper = (direct_base >> 16) & 0xFFFF
    lower = direct_base & 0xFFFF
    return [
        # tlbmanageEstablishManagementTable:
        # g_tlbmanageTlbAllocatedBlock = direct_base + expansion_delta.
        (0x241C, 0x3C080000 | upper, f"TLB cache direct base upper 0x{direct_base:08X}"),
        (0x2420, 0x25080000 | lower, f"TLB cache direct base lower 0x{direct_base:08X}"),
    ]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def build_one(spec):
    base_path = spec["base"]
    rom = bytearray(base_path.read_bytes())
    patch_report = []

    for offset, new_value, note in tlb_patches(spec["direct_base"]):
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

    expanded_end = spec["expanded_base"] + (90 * 0x2000) - 1
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
            "fb1": "0x8076A000-0x807FFFFF",
            "unchanged": True,
        },
        "tlb_cache_layout": {
            "direct_base_no_expansion_delta": f"0x{spec['direct_base']:08X}",
            "expected_expansion_base": f"0x{spec['expanded_base']:08X}",
            "expected_expansion_range": f"0x{spec['expanded_base']:08X}-0x{expanded_end:08X}",
            "old_expected_expansion_range": "0x806F6000-0x807A9FFF",
            "note": spec["note"],
        },
        "patches": patch_report,
    }
    out_report = Path("reports") / f"tnd480i_{spec['name']}_report.json"
    out_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "out_rom": str(out_rom),
        "out_md5": report["out_md5"],
        "header_crc": report["header_crc"],
        "expected_expansion_range": report["tlb_cache_layout"]["expected_expansion_range"],
    }, indent=2))
    return report


def main():
    reports = [build_one(spec) for spec in out_specs()]
    summary = Path("reports/tnd480i_tlb_cache_candidates_20260516.json")
    summary.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
