#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102
from build_t90tex_dossier_candidates import FUNCTION_RANGES, MENU_REPORT


GE_OLD_480I = Path(
    r"C:\Users\codex\Documents\Codex\2026-05-06\files-mentioned-by-the-user-tnd64\GE_old_480i.z64"
)
GE_ENHANCED_480I = Path("artifacts/roms/BASELINE_GE_480i_direct_from_stock.z64")
GE_STOCK = Path("artifacts/roms/GoldenEye 007 (USA).z64")

TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018

ROUTES = [
    ("05", 0x05, "file select / save folders"),
    ("06", 0x06, "mode select"),
    ("07", 0x07, "mission select"),
    ("08", 0x08, "difficulty select"),
    ("0a", 0x0A, "briefing dossier"),
]

DOSSIER_FUNCTIONS = {
    "menu05_file_select",
    "menu06_mode_select",
    "menu07_mission_select",
    "menu08_difficulty",
}

SKIP_OFFSETS = {
    # Allocation/pointer and helper-blob rewrites are not visual coordinate
    # scaling. Earlier probes showed these can black out pages or hide labels.
    0x40540,
    0x40544,
    *range(0x42F1C, 0x42F88, 4),
}

CANDIDATES = [
    {
        "name": "txsc05i",
        "functions": {"menu05_file_select"},
        "kinds": {"int"},
        "purpose": "Scale TND file-select integer coordinates by GE enhanced/stock ratios; no GE absolute coordinate paste.",
    },
    {
        "name": "txsc05if",
        "functions": {"menu05_file_select"},
        "kinds": {"int", "float_lui"},
        "purpose": "Scale TND file-select integer coordinates plus same-shape float LUI constants.",
    },
    {
        "name": "txsc0608i",
        "functions": {"menu06_mode_select", "menu07_mission_select", "menu08_difficulty"},
        "kinds": {"int"},
        "purpose": "Scale mode/mission/difficulty integer coordinates, preserving TND mission grid and labels.",
    },
    {
        "name": "txsc0608if",
        "functions": {"menu06_mode_select", "menu07_mission_select", "menu08_difficulty"},
        "kinds": {"int", "float_lui"},
        "purpose": "Scale mode/mission/difficulty integer and same-shape float LUI constants.",
    },
    {
        "name": "txscdossi",
        "functions": DOSSIER_FUNCTIONS,
        "kinds": {"int"},
        "purpose": "Scale all dossier page integer coordinates from stable t90texstk.",
    },
    {
        "name": "txscdossif",
        "functions": DOSSIER_FUNCTIONS,
        "kinds": {"int", "float_lui"},
        "purpose": "Scale all dossier page integer and same-shape float LUI constants from stable t90texstk.",
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def s16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def u16(value):
    return value & 0xFFFF


def parse_hex(value):
    return value if isinstance(value, int) else int(value, 16)


def function_name_for_offset(offset):
    for name, (start, end) in FUNCTION_RANGES.items():
        if start <= offset < end:
            return name
    return "unclassified"


def f32_from_upper(upper):
    return struct.unpack(">f", struct.pack(">I", (upper & 0xFFFF) << 16))[0]


def upper_from_f32(value):
    bits = struct.unpack(">I", struct.pack(">f", float(value)))[0]
    return (bits >> 16) & 0xFFFF


def plausible_float_upper(upper):
    return 0x4100 <= (upper & 0xFFFF) <= 0x4500


def load_enhanced_only_menu_offsets(stock, old, enhanced):
    report = json.loads(MENU_REPORT.read_text(encoding="utf-8"))
    offsets = []
    for entry in report["safe_direct_words_applied"]:
        offset = parse_hex(entry["offset"])
        if offset in SKIP_OFFSETS:
            continue
        function = function_name_for_offset(offset)
        if function not in DOSSIER_FUNCTIONS:
            continue
        stock_word = word(stock, offset)
        old_word = word(old, offset)
        enhanced_word = word(enhanced, offset)
        if old_word != stock_word:
            continue
        if enhanced_word == stock_word:
            continue
        offsets.append(
            {
                "offset": offset,
                "function": function,
                "stock": stock_word,
                "old": old_word,
                "enhanced": enhanced_word,
                "note": entry.get("note", ""),
            }
        )
    return offsets


def scale_int_word(current, stock, enhanced):
    if (current & 0xFFFF0000) != (stock & 0xFFFF0000):
        return None
    if (enhanced & 0xFFFF0000) != (stock & 0xFFFF0000):
        return None
    base = s16(stock)
    target = s16(enhanced)
    cur = s16(current)
    if base == 0:
        return None
    # Avoid classifying tiny counters or enum values as coordinates.
    if abs(base) < 8 and abs(target) < 12:
        return None
    ratio = target / base
    if not 0.35 <= abs(ratio) <= 3.0:
        return None
    new_imm = int(round(cur * ratio))
    if not -0x8000 <= new_imm <= 0x7FFF:
        return None
    return (current & 0xFFFF0000) | u16(new_imm)


def scale_float_lui_word(current, stock, enhanced):
    if (current & 0xFFFF0000) != (stock & 0xFFFF0000):
        return None
    if (enhanced & 0xFFFF0000) != (stock & 0xFFFF0000):
        return None
    if (stock >> 26) != 0x0F:
        return None
    if not (
        plausible_float_upper(stock)
        and plausible_float_upper(enhanced)
        and plausible_float_upper(current)
    ):
        return None
    base = f32_from_upper(stock)
    target = f32_from_upper(enhanced)
    cur = f32_from_upper(current)
    if base == 0:
        return None
    ratio = target / base
    if not 0.35 <= abs(ratio) <= 3.0:
        return None
    new_upper = upper_from_f32(cur * ratio)
    return (current & 0xFFFF0000) | new_upper


def scaled_patch_for(current, item, kinds):
    stock = item["stock"]
    enhanced = item["enhanced"]
    op = stock >> 26
    if "int" in kinds and op in {0x09, 0x0A, 0x0D}:
        new = scale_int_word(current, stock, enhanced)
        if new is not None:
            return new, "int_ratio"
    if "float_lui" in kinds:
        new = scale_float_lui_word(current, stock, enhanced)
        if new is not None:
            return new, "float_lui_ratio"
    return None, "skipped_shape"


def add_direct_route(rom, menu_id):
    old = word(rom, TIMEOUT_MENU_WORD_OFFSET)
    if old != EXPECTED_TIMEOUT_WORD:
        raise ValueError(
            f"unexpected route word at 0x{TIMEOUT_MENU_WORD_OFFSET:X}: "
            f"0x{old:08X}, expected 0x{EXPECTED_TIMEOUT_WORD:08X}"
        )
    new = 0x24040000 | menu_id
    write_word(rom, TIMEOUT_MENU_WORD_OFFSET, new)
    return {"offset": f"0x{TIMEOUT_MENU_WORD_OFFSET:X}", "old": f"0x{old:08X}", "new": f"0x{new:08X}"}


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


def build_candidate(spec, base_rom, base, offsets, out_dir, route_dir):
    rom = bytearray(base)
    patches = []
    skipped = []
    functions = set(spec["functions"])
    kinds = set(spec["kinds"])

    for item in offsets:
        if item["function"] not in functions:
            continue
        offset = item["offset"]
        current = word(rom, offset)
        new, kind = scaled_patch_for(current, item, kinds)
        row = {
            "offset": f"0x{offset:X}",
            "function": item["function"],
            "current": f"0x{current:08X}",
            "ge_stock": f"0x{item['stock']:08X}",
            "ge_old_480i": f"0x{item['old']:08X}",
            "ge_enhanced_480i": f"0x{item['enhanced']:08X}",
            "kind": kind,
            "note": item.get("note", ""),
        }
        if new is None:
            skipped.append(row)
            continue
        write_word(rom, offset, new)
        row["new"] = f"0x{new:08X}"
        row["changed"] = new != current
        patches.append(row)

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = out_dir / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)

    route_outputs = []
    for route_suffix, menu_id, route_purpose in ROUTES:
        route_rom = bytearray(rom)
        route_patch = add_direct_route(route_rom, menu_id)
        rcrc1, rcrc2 = update_n64_crc_6102(route_rom)
        route_path = route_dir / f"{spec['name']}auto{route_suffix}.z64"
        route_path.write_bytes(route_rom)
        route_outputs.append(
            {
                "route": route_suffix,
                "purpose": route_purpose,
                "out_rom": str(route_path),
                "out_md5": md5(route_rom),
                "header_crc": f"{rcrc1:08X} {rcrc2:08X}",
                "route_patch": route_patch,
            }
        )

    return {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "functions": sorted(functions),
        "kinds": sorted(kinds),
        "base_rom": str(base_rom),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patch_count": len(patches),
        "changed_patch_count": sum(1 for patch in patches if patch["changed"]),
        "skipped_count": len(skipped),
        "patches": patches,
        "skipped": skipped,
        "save_outputs": copy_save_pair(base_rom, out_rom),
        "route_outputs": route_outputs,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/t90texstk.z64"))
    parser.add_argument("--ge-stock-rom", type=Path, default=GE_STOCK)
    parser.add_argument("--ge-old-rom", type=Path, default=GE_OLD_480I)
    parser.add_argument("--ge-enhanced-rom", type=Path, default=GE_ENHANCED_480I)
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/generated"))
    parser.add_argument("--route-dir", type=Path, default=Path("artifacts/generated/scaled_dossier_routes"))
    parser.add_argument("--report", type=Path, default=Path("reports/tnd480i_t90tex_scaled_dossier_candidates_20260518.json"))
    args = parser.parse_args()

    for path in (args.base_rom, args.ge_stock_rom, args.ge_old_rom, args.ge_enhanced_rom):
        if not path.exists():
            raise SystemExit(f"missing ROM: {path}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.route_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    base = args.base_rom.read_bytes()
    stock = args.ge_stock_rom.read_bytes()
    old = args.ge_old_rom.read_bytes()
    enhanced = args.ge_enhanced_rom.read_bytes()
    offsets = load_enhanced_only_menu_offsets(stock, old, enhanced)

    report = {
        "purpose": (
            "Scale TND's own dossier/front-menu coordinates using GE enhanced-only "
            "ratios. This targets the enhanced 480i menu layout without transplanting "
            "GE absolute positions over TND mission/page content."
        ),
        "base_rom": str(args.base_rom),
        "base_md5": md5(base),
        "ge_stock_rom": str(args.ge_stock_rom),
        "ge_old_rom": str(args.ge_old_rom),
        "ge_enhanced_rom": str(args.ge_enhanced_rom),
        "menu_report": str(MENU_REPORT),
        "candidate_count": len(CANDIDATES),
        "enhanced_only_offset_count": len(offsets),
        "candidates": [
            build_candidate(spec, args.base_rom, base, offsets, args.out_dir, args.route_dir)
            for spec in CANDIDATES
        ],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(args.report),
                "enhanced_only_offset_count": len(offsets),
                "candidates": [
                    {
                        "name": item["name"],
                        "patch_count": item["patch_count"],
                        "changed_patch_count": item["changed_patch_count"],
                        "skipped_count": item["skipped_count"],
                    }
                    for item in report["candidates"]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
