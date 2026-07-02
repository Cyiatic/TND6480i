#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_render_state_revert_candidates import copy_save
from build_tnd480i_candidate import DIRECT_PATCH_GROUPS, md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/t90viewge.z64")
MENU_REPORT = Path("reports/tnd480i_gbslow_menu05_09_safe_20260511_report.json")
BRIEF_REPORT = Path("reports/fullrom_safe_ge480_words_missing_current_20260510.json")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_t90_dossier_candidates_20260518.json")

MENU_PTR_OFFSETS = {0x40540, 0x40544}
MENU_HELPER_BLOB = set(range(0x42F1C, 0x42F88, 4))

FUNCTION_RANGES = {
    "menu05_file_select": (0x403DC, 0x41D90),
    "menu06_mode_select": (0x41D90, 0x42118),
    "menu08_difficulty": (0x432F8, 0x43E74),
}

BRIEF_WRAP_RANGE = (0x454E8, 0x45604)

CANDIDATES = [
    {
        "name": "t90mstxt",
        "menu_functions": [],
        "direct_groups": ["J_mission_select_text_480i"],
        "brief_wrap": False,
        "purpose": "T90GE plus only the narrow mission-select text/grid offsets.",
    },
    {
        "name": "t90briefwrap",
        "menu_functions": [],
        "direct_groups": [],
        "brief_wrap": True,
        "purpose": "T90GE plus only GE480i briefing/objective text wrap thresholds.",
    },
    {
        "name": "t90dossiercore",
        "menu_functions": ["menu06_mode_select", "menu08_difficulty"],
        "menu_scale_only": False,
        "direct_groups": ["J_mission_select_text_480i"],
        "brief_wrap": True,
        "purpose": "T90GE dossier text pass: mode/difficulty text scale, mission label offsets, and briefing wrap thresholds; file-select and mission grid geometry stay stock TND.",
    },
    {
        "name": "t90modescale",
        "menu_functions": ["menu06_mode_select"],
        "menu_scale_only": True,
        "direct_groups": [],
        "brief_wrap": False,
        "purpose": "T90GE plus only mode-select GE480i scale/float words; file select and coordinates stay stock TND.",
    },
    {
        "name": "t90diffscale",
        "menu_functions": ["menu08_difficulty"],
        "menu_scale_only": True,
        "direct_groups": [],
        "brief_wrap": False,
        "purpose": "T90GE plus only difficulty-page GE480i scale/float words; placement stays stock TND.",
    },
    {
        "name": "t90dossci",
        "menu_functions": ["menu06_mode_select", "menu08_difficulty"],
        "menu_scale_only": True,
        "direct_groups": ["J_mission_select_text_480i"],
        "brief_wrap": True,
        "purpose": "T90GE dossier-scale candidate: mode/difficulty scale-only, narrow mission text offsets, and briefing wraps without file-select or coordinate transplants.",
    },
    {
        "name": "t90filefull",
        "menu_functions": ["menu05_file_select"],
        "direct_groups": [],
        "brief_wrap": False,
        "purpose": "T90GE plus only the coordinated file-select menu05 GE480i edits; tests whether icon/text pairs work when moved together.",
    },
    {
        "name": "t90filetext",
        "menu_functions": ["menu05_file_select"],
        "menu_placement_only": True,
        "direct_groups": [],
        "brief_wrap": False,
        "purpose": "T90GE plus only file-select menu05 non-float/text placement words; diagnostic for labels without moving image floats.",
    },
    {
        "name": "t90fileicons",
        "menu_functions": ["menu05_file_select"],
        "menu_scale_only": True,
        "direct_groups": [],
        "brief_wrap": False,
        "purpose": "T90GE plus only file-select menu05 float/icon position words; diagnostic for icon coordinates without label placements.",
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
                "offset": offset,
                "new": parse_hex(entry["new"]),
                "source": MENU_REPORT.name,
                "note": entry.get("note", ""),
            }
        )
    return patches


def function_name_for_offset(offset):
    for name, (start, end) in FUNCTION_RANGES.items():
        if start <= offset < end:
            return name
    return None


def is_float_or_scale_word(patch):
    new = patch["new"]
    return (new & 0xFFFF0000) in (0x3C010000, 0x44810000)


def iter_direct_group_patches(groups):
    by_offset = {}
    for group in groups:
        for offset, value, note in DIRECT_PATCH_GROUPS[group]:
            by_offset[offset] = {
                "offset": offset,
                "new": value,
                "source": f"DIRECT_PATCH_GROUPS.{group}",
                "note": note,
            }
    for offset in sorted(by_offset):
        yield by_offset[offset]


def walk_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def load_brief_wrap_patches():
    report = json.loads(BRIEF_REPORT.read_text(encoding="utf-8"))
    start, end = BRIEF_WRAP_RANGE
    patches = {}
    for entry in walk_json(report):
        off = entry.get("off") or entry.get("offset")
        new = entry.get("ge480") or entry.get("ge480i")
        if off is None or new is None:
            continue
        offset = parse_hex(off)
        if start <= offset < end:
            patches[offset] = {
                "offset": offset,
                "new": parse_hex(new),
                "source": BRIEF_REPORT.name,
                "note": "briefing/objective GE480i text wrap threshold",
            }
    return [patches[offset] for offset in sorted(patches)]


def select_patches(spec):
    selected = []
    wanted_functions = set(spec["menu_functions"])
    for patch in load_menu_patches():
        function = function_name_for_offset(patch["offset"])
        if function in wanted_functions:
            if spec.get("menu_scale_only") and not is_float_or_scale_word(patch):
                continue
            if spec.get("menu_placement_only") and is_float_or_scale_word(patch):
                continue
            patch = dict(patch)
            patch["function"] = function
            selected.append(patch)

    selected.extend(iter_direct_group_patches(spec["direct_groups"]))

    if spec["brief_wrap"]:
        selected.extend(load_brief_wrap_patches())

    by_offset = {patch["offset"]: patch for patch in selected}
    return [by_offset[offset] for offset in sorted(by_offset)]


def build_one(spec, base):
    rom = bytearray(base)
    applied = []
    for patch in select_patches(spec):
        offset = patch["offset"]
        old = word(rom, offset)
        write_word(rom, offset, patch["new"])
        applied.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{patch['new']:08X}",
                "changed": old != patch["new"],
                "source": patch["source"],
                "function": patch.get("function"),
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
