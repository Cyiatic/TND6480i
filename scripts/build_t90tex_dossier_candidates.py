#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import DIRECT_PATCH_GROUPS, md5, update_n64_crc_6102


MENU_REPORT = Path("reports/tnd480i_gbslow_menu05_09_safe_20260511_report.json")
BRIEF_REPORT = Path("reports/fullrom_safe_ge480_words_missing_current_20260510.json")

MENU_PTR_OFFSETS = {0x40540, 0x40544}
MENU_HELPER_BLOB = set(range(0x42F1C, 0x42F88, 4))
BRIEF_WRAP_RANGE = (0x454E8, 0x45604)

FUNCTION_RANGES = {
    "menu05_file_select": (0x403DC, 0x41D90),
    "menu06_mode_select": (0x41D90, 0x42118),
    "menu07_mission_select": (0x42118, 0x42854),
    "menu08_difficulty": (0x432F8, 0x43E74),
    "menu09_007_options": (0x43EA4, 0x44C1C),
}

# Exclude values previously classified as cursor/tween/control thresholds.
CONTROL_OR_CURSOR_OFFSETS = {
    0x42330,
    0x42338,
    0x433FC,
    0x43400,
    0x43434,
    0x43460,
    0x438A0,
    0x438A8,
}

CANDIDATES = [
    {
        "name": "txfilefull",
        "menu_functions": ["menu05_file_select"],
        "purpose": "t90texstk plus coordinated file-select GE480i words; checks folders/icons/text as a group.",
    },
    {
        "name": "txfileplace",
        "menu_functions": ["menu05_file_select"],
        "placement_only": True,
        "purpose": "t90texstk plus file-select placement/integer words only; icons/floats stay TND.",
    },
    {
        "name": "txfileicons",
        "menu_functions": ["menu05_file_select"],
        "scale_only": True,
        "purpose": "t90texstk plus file-select float/icon words only; text placement stays TND.",
    },
    {
        "name": "txfsg0",
        "menu_functions": ["menu05_file_select"],
        "only_offsets": [0x419F0, 0x41A04, 0x41A10],
        "purpose": "t90texstk plus file-select scale group 0 only, around 0x419F0-0x41A10.",
    },
    {
        "name": "txfsg1",
        "menu_functions": ["menu05_file_select"],
        "only_offsets": [0x41B24, 0x41B2C, 0x41B30, 0x41B34],
        "purpose": "t90texstk plus file-select scale group 1 only, around 0x41B24-0x41B34.",
    },
    {
        "name": "txfsg2",
        "menu_functions": ["menu05_file_select"],
        "only_offsets": [0x41C30, 0x41C40, 0x41C48],
        "purpose": "t90texstk plus file-select scale group 2 only, around 0x41C30-0x41C48.",
    },
    {
        "name": "txfsg01",
        "menu_functions": ["menu05_file_select"],
        "only_offsets": [0x419F0, 0x41A04, 0x41A10, 0x41B24, 0x41B2C, 0x41B30, 0x41B34],
        "purpose": "t90texstk plus file-select scale groups 0 and 1, excluding group 2 which hides Select File.",
    },
    {
        "name": "txfp0g0",
        "menu_functions": ["menu05_file_select"],
        "only_offsets": [0x41644, 0x417DC, 0x41894, 0x41898, 0x41964, 0x419F0, 0x41A04, 0x41A10],
        "purpose": "t90texstk plus file-select placement words and scale group 0.",
    },
    {
        "name": "txfp0g1",
        "menu_functions": ["menu05_file_select"],
        "only_offsets": [0x41644, 0x417DC, 0x41894, 0x41898, 0x41964, 0x41B24, 0x41B2C, 0x41B30, 0x41B34],
        "purpose": "t90texstk plus file-select placement words and scale group 1.",
    },
    {
        "name": "txfp0g2",
        "menu_functions": ["menu05_file_select"],
        "only_offsets": [0x41644, 0x417DC, 0x41894, 0x41898, 0x41964, 0x41C30, 0x41C40, 0x41C48],
        "purpose": "t90texstk plus file-select placement words and scale group 2.",
    },
    {
        "name": "txfp0g01",
        "menu_functions": ["menu05_file_select"],
        "only_offsets": [0x41644, 0x417DC, 0x41894, 0x41898, 0x41964, 0x419F0, 0x41A04, 0x41A10, 0x41B24, 0x41B2C, 0x41B30, 0x41B34],
        "purpose": "t90texstk plus file-select placement words and scale groups 0 and 1, excluding group 2.",
    },
    {
        "name": "txmode06",
        "menu_functions": ["menu06_mode_select"],
        "purpose": "t90texstk plus mode-select GE480i words.",
    },
    {
        "name": "txm07draw",
        "menu_functions": ["menu07_mission_select"],
        "draw_only": True,
        "purpose": "t90texstk plus mission-select draw coordinates only; cursor/control words stay TND.",
    },
    {
        "name": "txm08draw",
        "menu_functions": ["menu08_difficulty"],
        "draw_only": True,
        "purpose": "t90texstk plus difficulty-page draw coordinates only; cursor/control words stay TND.",
    },
    {
        "name": "txmstxt",
        "direct_groups": ["J_mission_select_text_480i"],
        "purpose": "t90texstk plus the narrow mission-select text/grid direct group only.",
    },
    {
        "name": "txdossdraw",
        "menu_functions": ["menu06_mode_select", "menu07_mission_select", "menu08_difficulty"],
        "draw_only": True,
        "brief_wrap": True,
        "purpose": "t90texstk dossier draw pass: mode, mission, difficulty draw words plus briefing wraps.",
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def parse_hex(value):
    return value if isinstance(value, int) else int(value, 16)


def function_name_for_offset(offset):
    for name, (start, end) in FUNCTION_RANGES.items():
        if start <= offset < end:
            return name
    return "unclassified"


def is_float_or_scale_word(patch):
    new = patch["new"]
    return (new & 0xFFFF0000) in (0x3C010000, 0x44810000)


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
                "function": function_name_for_offset(offset),
            }
        )
    return patches


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
    by_offset = {}
    for entry in walk_json(report):
        off = entry.get("off") or entry.get("offset")
        new = entry.get("ge480") or entry.get("ge480i")
        if off is None or new is None:
            continue
        offset = parse_hex(off)
        if start <= offset < end:
            by_offset[offset] = {
                "offset": offset,
                "new": parse_hex(new),
                "source": BRIEF_REPORT.name,
                "note": "briefing/objective GE480i text wrap threshold",
                "function": "brief_wrap",
            }
    return [by_offset[offset] for offset in sorted(by_offset)]


def selected_patches(spec):
    selected = []
    wanted = set(spec.get("menu_functions", []))
    only_offsets = set(spec.get("only_offsets", []))
    for patch in load_menu_patches():
        if patch["function"] not in wanted:
            continue
        if only_offsets and patch["offset"] not in only_offsets:
            continue
        if spec.get("draw_only") and patch["offset"] in CONTROL_OR_CURSOR_OFFSETS:
            continue
        if spec.get("scale_only") and not is_float_or_scale_word(patch):
            continue
        if spec.get("placement_only") and is_float_or_scale_word(patch):
            continue
        selected.append(patch)

    for group in spec.get("direct_groups", []):
        for offset, value, note in DIRECT_PATCH_GROUPS[group]:
            selected.append(
                {
                    "offset": offset,
                    "new": value,
                    "source": f"DIRECT_PATCH_GROUPS.{group}",
                    "note": note,
                    "function": group,
                }
            )

    if spec.get("brief_wrap"):
        selected.extend(load_brief_wrap_patches())

    by_offset = {patch["offset"]: patch for patch in selected}
    return [by_offset[offset] for offset in sorted(by_offset)]


def copy_save_pair(base_rom, out_rom):
    outputs = []
    for suffix in (".sav", ".eep"):
        source = base_rom.with_suffix(suffix)
        target = out_rom.with_suffix(suffix)
        if not source.exists():
            outputs.append({"source": str(source), "target": str(target), "missing": True})
            continue
        shutil.copy2(source, target)
        payload = target.read_bytes()
        outputs.append({"source": str(source), "target": str(target), "bytes": len(payload), "md5": md5(payload)})
    return outputs


def build_one(spec, base_rom, base, out_dir, prefix):
    rom = bytearray(base)
    applied = []
    for patch in selected_patches(spec):
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
    out_name = f"{prefix}{spec['name']}" if prefix else spec["name"]
    out_rom = out_dir / f"{out_name}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": out_name,
        "purpose": spec["purpose"],
        "base_rom": str(base_rom),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patch_count": len(applied),
        "changed_patch_count": sum(1 for patch in applied if patch["changed"]),
        "patches": applied,
        "save_outputs": copy_save_pair(base_rom, out_rom),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/t90texstk.z64"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/generated"))
    parser.add_argument("--report", type=Path, default=Path("reports/tnd480i_t90tex_dossier_candidates_20260518.json"))
    parser.add_argument("--prefix", default="")
    args = parser.parse_args()

    if not args.base_rom.exists():
        raise SystemExit(f"missing base ROM: {args.base_rom}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    base = args.base_rom.read_bytes()
    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(base),
        "menu_report": str(MENU_REPORT),
        "brief_report": str(BRIEF_REPORT),
        "candidates": [build_one(spec, args.base_rom, base, args.out_dir, args.prefix) for spec in CANDIDATES],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
