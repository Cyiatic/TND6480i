#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_render_state_revert_candidates import copy_save
from build_t90_dossier_candidates import (
    load_menu_patches,
)
from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/t90viewge.z64")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_t90_menu_drawonly_candidates_20260518.json")

# Exclude values that the source audit classified as cursor/tween/control
# thresholds rather than pure draw coordinates.
CONTROL_OR_CURSOR_OFFSETS = {
    # menu07: set_cursor_to_stage_solo style cursor target/tween values
    0x42330,
    0x42338,
    # menu08: interface/set-cursor threshold and target values
    0x433FC,
    0x43400,
    0x43434,
    0x43460,
    0x438A0,
    0x438A8,
}

FUNCTION_RANGES = {
    "menu05_file_select": (0x403DC, 0x41D90),
    "menu06_mode_select": (0x41D90, 0x42118),
    "menu07_mission_select": (0x42118, 0x42854),
    "menu08_difficulty": (0x432F8, 0x43E74),
    "menu09_007_options": (0x43EA4, 0x44C1C),
}

CANDIDATES = [
    {
        "name": "t90m07draw",
        "functions": ["menu07_mission_select"],
        "purpose": "Mission-select GE480i visual draw coordinates only; cursor/control words stay TND.",
    },
    {
        "name": "t90m08draw",
        "functions": ["menu08_difficulty"],
        "purpose": "Difficulty-page GE480i visual draw coordinates only; cursor/control words stay TND.",
    },
    {
        "name": "t90dossdraw",
        "functions": ["menu07_mission_select", "menu08_difficulty"],
        "purpose": "Mission-select plus difficulty draw-only pass, excluding cursor/control thresholds.",
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def function_name_for_offset(offset):
    for name, (start, end) in FUNCTION_RANGES.items():
        if start <= offset < end:
            return name
    return "unclassified"


def selected_patches(functions):
    wanted = set(functions)
    patches = []
    for patch in load_menu_patches():
        offset = patch["offset"]
        function = function_name_for_offset(offset)
        if function not in wanted:
            continue
        if offset in CONTROL_OR_CURSOR_OFFSETS:
            continue
        patches.append({**patch, "function": function})
    return sorted(patches, key=lambda item: item["offset"])


def build_one(spec, base):
    rom = bytearray(base)
    applied = []
    for patch in selected_patches(spec["functions"]):
        offset = patch["offset"]
        old = word(rom, offset)
        write_word(rom, offset, patch["new"])
        applied.append(
            {
                "offset": f"0x{offset:X}",
                "function": patch["function"],
                "old": f"0x{old:08X}",
                "new": f"0x{patch['new']:08X}",
                "changed": old != patch["new"],
                "source": patch["source"],
                "note": patch.get("note", ""),
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
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patch_count": len(applied),
        "changed_patch_count": sum(1 for patch in applied if patch["changed"]),
        "excluded_control_or_cursor_offsets": [f"0x{offset:X}" for offset in sorted(CONTROL_OR_CURSOR_OFFSETS)],
        "patches": applied,
        "save_outputs": copy_save(out_rom),
    }


def main():
    if not BASE_ROM.exists():
        raise SystemExit(f"missing base ROM: {BASE_ROM}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    base = BASE_ROM.read_bytes()
    results = [build_one(spec, base) for spec in CANDIDATES]
    REPORT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
