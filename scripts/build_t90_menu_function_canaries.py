#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/t90viewge.z64")
BASE_SAVE = Path("artifacts/generated/t90viewge.sav")
MENU_REPORT = Path("reports/tnd480i_gbslow_menu05_09_safe_20260511_report.json")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_t90_menu_function_canaries_20260518.json")

MENU_PTR_OFFSETS = {0x40540, 0x40544}
MENU_HELPER_BLOB = set(range(0x42F1C, 0x42F88, 4))

# TND front-end function ranges inferred from the stock ROM prologue/return map
# and the local GoldenEye front.c order. The menu05/file-select constructor is
# intentionally separated because scale-only edits there removed save-select UI.
FUNCTION_RANGES = {
    "menu05_file_select": (0x403DC, 0x41D90),
    "menu06_mode_select": (0x41D90, 0x42118),
    "menu07_mission_select": (0x42118, 0x42854),
    "menu08_difficulty": (0x432F8, 0x43E74),
    "menu09_007_options": (0x43EA4, 0x44C1C),
}

CANDIDATES = [
    {
        "name": "t90menu06",
        "groups": ["menu06_mode_select"],
        "purpose": "Apply only GE-style mode-select menu06 edits, leaving file select and later menus stock.",
    },
    {
        "name": "t90menu07",
        "groups": ["menu07_mission_select"],
        "purpose": "Apply only GE-style mission-select menu07 edits, leaving file select stock.",
    },
    {
        "name": "t90menu08",
        "groups": ["menu08_difficulty"],
        "purpose": "Apply only GE-style difficulty menu08 edits, leaving file select stock.",
    },
    {
        "name": "t90menu0608",
        "groups": ["menu06_mode_select", "menu07_mission_select", "menu08_difficulty"],
        "purpose": "Apply GE-style mode, mission, and difficulty menu edits while preserving file select.",
    },
    {
        "name": "t90menu0609",
        "groups": [
            "menu06_mode_select",
            "menu07_mission_select",
            "menu08_difficulty",
            "menu09_007_options",
        ],
        "purpose": "Apply GE-style menu06-menu09 edits while preserving file select.",
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def parse_hex(value):
    return value if isinstance(value, int) else int(value, 16)


def load_menu_patches():
    report = json.loads(MENU_REPORT.read_text(encoding="utf-8"))
    patches = []
    for entry in report["safe_direct_words_applied"]:
        offset = parse_hex(entry["offset"])
        if offset in MENU_PTR_OFFSETS or offset in MENU_HELPER_BLOB:
            continue
        patches.append(
            {
                "source": MENU_REPORT.name,
                "offset": offset,
                "new": parse_hex(entry["new"]),
                "old_reported": parse_hex(entry["old"]),
                "range": entry.get("range", ""),
            }
        )
    return patches


def function_name_for_offset(offset):
    for name, (start, end) in FUNCTION_RANGES.items():
        if start <= offset < end:
            return name
    return "unclassified"


def copy_save(out_rom):
    outputs = []
    if not BASE_SAVE.exists():
        return outputs
    save = BASE_SAVE.read_bytes()
    for suffix, payload in {
        ".sav": save,
        ".eep": save if len(save) >= 2048 else save + b"\0" * (2048 - len(save)),
    }.items():
        out = out_rom.with_suffix(suffix)
        out.write_bytes(payload)
        outputs.append({"path": str(out), "bytes": len(payload), "md5": md5(payload)})
    return outputs


def build_one(spec, all_patches, base):
    rom = bytearray(base)
    wanted = set(spec["groups"])
    selected = [
        patch
        for patch in all_patches
        if function_name_for_offset(patch["offset"]) in wanted
    ]
    applied = []
    for patch in sorted(selected, key=lambda item: item["offset"]):
        offset = patch["offset"]
        old = word(rom, offset)
        write_word(rom, offset, patch["new"])
        applied.append(
            {
                "offset": f"0x{offset:X}",
                "function": function_name_for_offset(offset),
                "old": f"0x{old:08X}",
                "new": f"0x{patch['new']:08X}",
                "changed": old != patch["new"],
                "source": patch["source"],
            }
        )

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = OUT_DIR / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "groups": spec["groups"],
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patch_count": len(applied),
        "changed_patch_count": sum(1 for patch in applied if patch["changed"]),
        "patches": applied,
        "save_outputs": copy_save(out_rom),
    }


def main():
    if not BASE_ROM.exists():
        raise SystemExit(f"missing base ROM: {BASE_ROM}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    base = BASE_ROM.read_bytes()
    all_patches = load_menu_patches()
    classification = {}
    for patch in all_patches:
        classification.setdefault(function_name_for_offset(patch["offset"]), 0)
        classification[function_name_for_offset(patch["offset"])] += 1
    results = [build_one(spec, all_patches, base) for spec in CANDIDATES]
    report = {
        "base_rom": str(BASE_ROM),
        "function_ranges": {
            name: {"start": f"0x{start:X}", "end": f"0x{end:X}"}
            for name, (start, end) in FUNCTION_RANGES.items()
        },
        "classification_counts": dict(sorted(classification.items())),
        "rejected_prior": {
            "t90menuscales": "scale-only all-menu canary removed save-select labels/icons",
            "t90menuplace": "placement-only all-menu canary pushed Copy/Erase offscreen",
        },
        "candidates": results,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
