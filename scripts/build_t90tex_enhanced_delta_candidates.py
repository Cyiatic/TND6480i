#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import DIRECT_PATCH_GROUPS, md5, update_n64_crc_6102
from build_t90tex_dossier_candidates import FUNCTION_RANGES, MENU_REPORT


TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018

ROUTES = [
    ("05", 0x05, "file select / save folders"),
    ("06", 0x06, "mode select"),
    ("07", 0x07, "mission select"),
    ("08", 0x08, "difficulty select"),
    ("0a", 0x0A, "briefing dossier"),
]

MENU_FUNCTIONS = {
    "menu05_file_select",
    "menu06_mode_select",
    "menu07_mission_select",
    "menu08_difficulty",
    "menu09_007_options",
}

CANDIDATES = [
    {
        "name": "txedfront",
        "kind": "front",
        "purpose": "GE enhanced same-opcode deltas for front layout clusters only.",
    },
    {
        "name": "txedmenu",
        "kind": "menu",
        "purpose": "GE enhanced same-opcode deltas for menu05-09 constants only.",
    },
    {
        "name": "txeddossier",
        "kind": "dossier",
        "purpose": "GE enhanced same-opcode deltas for menu05-08 dossier pages only.",
    },
    {
        "name": "txedfrontdoss",
        "kind": "front_dossier",
        "purpose": "Front layout deltas plus dossier menu05-08 deltas.",
    },
    {
        "name": "txedfrontmenu",
        "kind": "front_menu",
        "purpose": "Front layout deltas plus menu05-09 deltas.",
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def s16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def same_opcode_delta(cur, ge_stock, ge_480):
    if ge_stock == ge_480:
        return None
    stock_op = ge_stock >> 26
    ge_480_op = ge_480 >> 26
    cur_op = cur >> 26
    if stock_op != ge_480_op or cur_op != stock_op:
        return None

    # Preserve the current instruction/register fields and move only the immediate
    # by the same signed low-16 delta used by the GE enhanced patch.
    if (cur & 0xFFFF0000) != (ge_stock & 0xFFFF0000):
        return None
    delta = s16(ge_480) - s16(ge_stock)
    new_imm = (s16(cur) + delta) & 0xFFFF
    return (cur & 0xFFFF0000) | new_imm


def function_name_for_offset(offset):
    for name, (start, end) in FUNCTION_RANGES.items():
        if start <= offset < end:
            return name
    return "unclassified"


def parse_hex(value):
    return value if isinstance(value, int) else int(value, 16)


def menu_offsets():
    report = json.loads(MENU_REPORT.read_text(encoding="utf-8"))
    offsets = []
    for entry in report["safe_direct_words_applied"]:
        offset = parse_hex(entry["offset"])
        function = function_name_for_offset(offset)
        if function in MENU_FUNCTIONS:
            offsets.append((offset, function, entry.get("note", "")))
    return sorted(set(offsets))


def front_offsets():
    groups = [
        "J_front_layout_no_rectloop_480i",
        "J_front_height_limit_480i",
        "J_front_layout_gridstep_480i",
    ]
    out = []
    for group in groups:
        for offset, _value, note in DIRECT_PATCH_GROUPS[group]:
            out.append((offset, group, note))
    return sorted({(offset, source, note) for offset, source, note in out})


def selected_offsets(kind):
    front = front_offsets()
    menu = menu_offsets()
    dossier_menu = [item for item in menu if item[1] != "menu09_007_options"]
    if kind == "front":
        return front
    if kind == "menu":
        return menu
    if kind == "dossier":
        return dossier_menu
    if kind == "front_dossier":
        return front + dossier_menu
    if kind == "front_menu":
        return front + menu
    raise ValueError(kind)


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


def build_candidate(spec, base_rom, base, ge_stock, ge_480, out_dir, route_dir):
    rom = bytearray(base)
    patches = []
    skipped = []
    for offset, source, note in selected_offsets(spec["kind"]):
        cur = word(rom, offset)
        stock = word(ge_stock, offset)
        enhanced = word(ge_480, offset)
        new = same_opcode_delta(cur, stock, enhanced)
        if new is None:
            skipped.append(
                {
                    "offset": f"0x{offset:X}",
                    "source": source,
                    "current": f"0x{cur:08X}",
                    "ge_stock": f"0x{stock:08X}",
                    "ge_480i": f"0x{enhanced:08X}",
                    "reason": "not same-opcode/immediate-compatible",
                    "note": note,
                }
            )
            continue
        write_word(rom, offset, new)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "source": source,
                "current": f"0x{cur:08X}",
                "ge_stock": f"0x{stock:08X}",
                "ge_480i": f"0x{enhanced:08X}",
                "new": f"0x{new:08X}",
                "changed": cur != new,
                "note": note,
            }
        )

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
        "kind": spec["kind"],
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
    parser.add_argument("--ge-stock-rom", type=Path, default=Path("artifacts/roms/GoldenEye 007 (USA).z64"))
    parser.add_argument("--ge-480i-rom", type=Path, default=Path("artifacts/roms/BASELINE_GE_480i_direct_from_stock.z64"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/generated"))
    parser.add_argument("--route-dir", type=Path, default=Path("artifacts/generated/enhanced_delta_routes"))
    parser.add_argument("--report", type=Path, default=Path("reports/tnd480i_t90tex_enhanced_delta_candidates_20260518.json"))
    args = parser.parse_args()

    for path in (args.base_rom, args.ge_stock_rom, args.ge_480i_rom):
        if not path.exists():
            raise SystemExit(f"missing ROM: {path}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.route_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    base = args.base_rom.read_bytes()
    ge_stock = args.ge_stock_rom.read_bytes()
    ge_480 = args.ge_480i_rom.read_bytes()
    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(base),
        "ge_stock_rom": str(args.ge_stock_rom),
        "ge_stock_md5": md5(ge_stock),
        "ge_480i_rom": str(args.ge_480i_rom),
        "ge_480i_md5": md5(ge_480),
        "purpose": "Apply GE stock-to-enhanced480i same-opcode coordinate deltas to the stable TND t90texstk baseline, preserving TND-specific placements where possible.",
        "candidates": [
            build_candidate(spec, args.base_rom, base, ge_stock, ge_480, args.out_dir, args.route_dir)
            for spec in CANDIDATES
        ],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.report), "candidates": [item["name"] for item in report["candidates"]]}, indent=2))


if __name__ == "__main__":
    main()
