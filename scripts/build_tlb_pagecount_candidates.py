#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


OUT_DIR = Path("artifacts/generated")
REPORT_DIR = Path("reports")
STOCK_SOURCE = Path("artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64")
SAVE_SOURCE = Path("artifacts/generated/tnd_test_all_missions.sav")

FB1_BASE = 0x8076A000
PAGE_SIZE = 0x2000

TLB_BASE_UPPER_OFFSET = 0x241C
TLB_BASE_LOWER_OFFSET = 0x2420
TLB_WRAP_COUNT_OFFSET = 0x2618


SPECS = [
    {
        "name": "game_h460_top10_stock_dossier_tlbpages58_007label_current",
        "base": Path("artifacts/generated/game_h460_top10_stock_dossier_tlb806b6_007label_current.z64"),
        "page_count": 58,
        "expected_expansion_base": 0x806F6000,
        "purpose": (
            "Preserve the current in-game-480i/camera-480i/007-label branch, but restore "
            "the TLB cache start to the stock Expansion Pak base and reduce the round-robin "
            "page count so the cache ends exactly before fb1 instead of overlapping it."
        ),
    },
    {
        "name": "game_h460_top10_stock_dossier_tlbpages58_camviewstock_007label_current",
        "base": Path("artifacts/generated/game_h460_top10_stock_dossier_tlb806b6_camviewstock_007label_current.z64"),
        "page_count": 58,
        "expected_expansion_base": 0x806F6000,
        "purpose": (
            "Same exact stock-memory TLB page-count fix, starting from the loaded "
            "stock-camera fallback. This combines stock camera viewports with a cache "
            "that no longer overlaps fb1 and no longer steals the extra 0x40000 of stage memory."
        ),
    },
    {
        "name": "game_h460_top10_stock_dossier_tlbpages64_007label_current",
        "base": Path("artifacts/generated/game_h460_top10_stock_dossier_tlb806b6_007label_current.z64"),
        "page_count": 64,
        "expected_expansion_base": FB1_BASE - (64 * PAGE_SIZE),
        "purpose": (
            "Middle-ground TLB diagnostic: preserve the in-game/camera-480i path and keep "
            "64 cache pages, placed as high as possible without touching fb1. This costs "
            "0xC000 more stage memory than the stock-start pages58 candidate but keeps six "
            "additional cache pages."
        ),
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def mips_lui_addiu_for_address(address):
    # addiu sign-extends its immediate. Use the normal hi-adjusted pair so
    # addresses with low half >= 0x8000 assemble back to the requested value.
    high = ((address + 0x8000) >> 16) & 0xFFFF
    low = address & 0xFFFF
    return 0x3C080000 | high, 0x25080000 | low


def copy_save(out_rom):
    if not SAVE_SOURCE.exists():
        return []
    save = SAVE_SOURCE.read_bytes()
    eep = save if len(save) >= 2048 else save + b"\0" * (2048 - len(save))
    sav_path = out_rom.with_suffix(".sav")
    eep_path = out_rom.with_suffix(".eep")
    sav_path.write_bytes(save)
    eep_path.write_bytes(eep)
    return [
        {"path": str(sav_path), "bytes": len(save)},
        {"path": str(eep_path), "bytes": len(eep)},
    ]


def build_one(spec):
    base_path = spec["base"]
    base = base_path.read_bytes()
    rom = bytearray(base)
    page_count = spec["page_count"]
    expected_expansion_base = spec["expected_expansion_base"]
    direct_base = expected_expansion_base - 0x00400000
    expected_end = expected_expansion_base + (page_count * PAGE_SIZE) - 1
    if expected_end != FB1_BASE - 1:
        raise ValueError(
            f"{spec['name']} cache ends at 0x{expected_end:08X}, not just before fb1"
        )
    if not (1 <= page_count <= 90):
        raise ValueError(f"unexpected page count: {page_count}")

    upper, lower = mips_lui_addiu_for_address(direct_base)
    patch_plan = [
        (
            TLB_BASE_UPPER_OFFSET,
            upper,
            f"TLB cache direct base upper for 0x{direct_base:08X}",
        ),
        (
            TLB_BASE_LOWER_OFFSET,
            lower,
            f"TLB cache direct base lower for 0x{direct_base:08X}",
        ),
        (
            TLB_WRAP_COUNT_OFFSET,
            0x2C810000 | page_count,
            f"TLB round-robin wrap count 90 -> {page_count}",
        ),
    ]

    patches = []
    for offset, value, note in patch_plan:
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_rom = OUT_DIR / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)
    save_writes = copy_save(out_rom)

    report = {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "base_rom": str(base_path),
        "base_md5": md5(base),
        "stock_source_rom": str(STOCK_SOURCE),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "framebuffer_layout": {
            "fb0": "0x80300000-0x80395FFF",
            "fb1": "0x8076A000-0x807FFFFF",
            "unchanged": True,
        },
        "tlb_cache_layout": {
            "page_count": page_count,
            "page_size": f"0x{PAGE_SIZE:X}",
            "direct_base_no_expansion_delta": f"0x{direct_base:08X}",
            "expected_expansion_base": f"0x{expected_expansion_base:08X}",
            "expected_expansion_range": f"0x{expected_expansion_base:08X}-0x{expected_end:08X}",
            "stock_90_page_range_on_8mb": "0x806F6000-0x807A9FFF",
            "current_tlb806b6_90_page_range": "0x806B6000-0x80769FFF",
            "gap_to_fb1": FB1_BASE - expected_end - 1,
        },
        "patches": patches,
        "save_writes": save_writes,
        "hardware_priority": (
            "Do not upload ahead of the currently loaded camviewstock test. If camviewstock "
            "still behaves the same, test pages58_007label first to restore stock stage "
            "memory while keeping the 480i camera path. If that fails, test the "
            "pages58_camviewstock combination."
        ),
    }
    report_path = REPORT_DIR / f"tnd480i_{spec['name']}_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    reports = [build_one(spec) for spec in SPECS]
    summary = REPORT_DIR / "tnd480i_tlb_pagecount_candidates_20260517.json"
    summary.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
