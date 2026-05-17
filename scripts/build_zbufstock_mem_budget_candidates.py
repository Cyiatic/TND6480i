#!/usr/bin/env python3
import json
from pathlib import Path

from build_stage_mem_budget_candidates import copy_save, patch_stage_strings, zero_pad_capacity
from build_tnd480i_candidate import (
    GE_1172_OFFSET,
    inflate_ge1172,
    md5,
    pack_ge1172,
    update_n64_crc_6102,
)


BASE_ROM = Path(
    "artifacts/generated/game_h460_top10_stock_dossier_tlbpages58_zbufstock_007label_current.z64"
)
BASE_SAVE = Path("artifacts/generated/tnd58.sav")
OUT_DIR = Path("artifacts/generated")
REPORT_DIR = Path("reports")

CANDIDATES = [
    {
        "name": "zbstkmt",
        "purpose": (
            "Keep the stock z-buffer footprint and reduce only Party/The End texture "
            "cache budgets. This tests whether their black-screen failures need the "
            "z-buffer RAM back plus a smaller per-stage texture reservation."
        ),
        "strings": {
            "Party": "-ml0 -me0 -mgfx70  -mvtx50 -mt800 -ma200",
            "The End": "-ml0 -me0 -mgfx100 -mvtx50 -mt600 -ma150",
        },
    },
    {
        "name": "zbstkgx",
        "purpose": (
            "Keep the stock z-buffer footprint, raise Party/The End display-list and "
            "vertex pools, and pay for it with smaller texture budgets."
        ),
        "strings": {
            "Party": "-ml0 -me0 -mgfx100 -mvtx70 -mt800 -ma200",
            "The End": "-ml0 -me0 -mgfx130 -mvtx70 -mt600 -ma150",
        },
    },
    {
        "name": "zbstklo",
        "purpose": (
            "Keep the stock z-buffer footprint and apply a more aggressive texture "
            "budget reduction to Party/The End while leaving gfx/vtx unchanged."
        ),
        "strings": {
            "Party": "-ml0 -me0 -mgfx70  -mvtx50 -mt700 -ma200",
            "The End": "-ml0 -me0 -mgfx100 -mvtx50 -mt500 -ma150",
        },
    },
]


def build_one(candidate):
    rom = bytearray(BASE_ROM.read_bytes())
    raw, slot_len = inflate_ge1172(rom, GE_1172_OFFSET)
    patched_raw, patches = patch_stage_strings(raw, candidate["strings"])
    packed = pack_ge1172(patched_raw)
    allowed_packed_len, zero_pad_growth = zero_pad_capacity(rom, GE_1172_OFFSET, slot_len)
    if len(packed) > allowed_packed_len:
        raise ValueError(
            f"{candidate['name']}: packed 1172 stream too large: "
            f"0x{len(packed):X} > 0x{allowed_packed_len:X}"
        )

    rom[GE_1172_OFFSET : GE_1172_OFFSET + allowed_packed_len] = b"\0" * allowed_packed_len
    rom[GE_1172_OFFSET : GE_1172_OFFSET + len(packed)] = packed
    crc1, crc2 = update_n64_crc_6102(rom)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_rom = OUT_DIR / f"{candidate['name']}.z64"
    out_rom.write_bytes(rom)
    save_outputs = copy_save(out_rom)

    verify_raw, verify_consumed = inflate_ge1172(rom, GE_1172_OFFSET)
    return {
        "name": candidate["name"],
        "purpose": candidate["purpose"],
        "base_rom": str(BASE_ROM),
        "base_md5": md5(BASE_ROM.read_bytes()),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "slot_len": f"0x{slot_len:X}",
        "allowed_packed_len": f"0x{allowed_packed_len:X}",
        "zero_pad_growth": f"0x{zero_pad_growth:X}",
        "packed_len": f"0x{len(packed):X}",
        "verify_consumed": f"0x{verify_consumed:X}",
        "main_raw_md5": md5(patched_raw),
        "verify_main_raw_md5": md5(verify_raw),
        "patches": patches,
        "save_outputs": save_outputs,
        "direct_probe_focus": ["Party", "The End", "City"],
    }


def main():
    if not BASE_ROM.exists():
        raise SystemExit(f"base ROM not found: {BASE_ROM}")

    reports = [build_one(candidate) for candidate in CANDIDATES]
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "tnd480i_zbufstock_mem_budget_candidates_20260517.json"
    report_path.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
