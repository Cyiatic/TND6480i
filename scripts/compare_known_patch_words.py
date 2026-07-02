#!/usr/bin/env python3
import argparse
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import (
    DIRECT_PATCH_GROUPS,
    GE_1172_OFFSET,
    MAIN_RANGES,
    inflate_ge1172,
    md5,
)


DEFAULT_ROMS = {
    "stock_tnd": "artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64",
    "ge_480i": "artifacts/roms/BASELINE_GE_480i_direct_from_stock.z64",
    "enh480i_ref": "artifacts/roms/TND64_enh480i_core_no_menu_pigz.z64",
    "current_best": "artifacts/generated/game_h460_top10_stock_dossier_tables_current.z64",
    "camviewstock": "artifacts/generated/game_h460_top10_stock_dossier_camviewstock_current.z64",
}


def read_word(data, offset):
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from(">I", data, offset)[0]


def fmt_word(value):
    return None if value is None else f"0x{value:08X}"


def direct_offsets():
    offsets = {}
    for group, entries in DIRECT_PATCH_GROUPS.items():
        for offset, _value, note in entries:
            offsets.setdefault(offset, set()).add(f"{group}: {note}")
    return offsets


def main_offsets():
    offsets = {}
    for start, end, label in MAIN_RANGES:
        for offset in range(start, end, 4):
            offsets.setdefault(offset, set()).add(label)
    return offsets


def load_roms(paths):
    roms = {}
    for label, path in paths.items():
        data = Path(path).read_bytes()
        try:
            raw, consumed = inflate_ge1172(data, GE_1172_OFFSET)
            raw_error = None
        except Exception as exc:
            raw = b""
            consumed = 0
            raw_error = str(exc)
        roms[label] = {
            "path": path,
            "bytes": data,
            "md5": md5(data),
            "size": len(data),
            "main_raw": raw,
            "main_consumed": consumed,
            "main_error": raw_error,
        }
    return roms


def differing_rows(roms, offsets, source_key, compare_labels):
    rows = []
    for offset, notes in sorted(offsets.items()):
        values = {
            label: read_word(rom[source_key], offset)
            for label, rom in roms.items()
        }
        if len({values[label] for label in compare_labels}) <= 1:
            continue
        rows.append({
            "offset": f"0x{offset:X}",
            "notes": sorted(notes),
            "values": {label: fmt_word(values[label]) for label in compare_labels},
        })
    return rows


def summarize_relation(rows, lhs, rhs):
    same = 0
    diff = 0
    for row in rows:
        values = row["values"]
        if values.get(lhs) == values.get(rhs):
            same += 1
        else:
            diff += 1
    return {"same": same, "different": diff}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="reports/known_patch_word_delta_20260516.json")
    parser.add_argument(
        "--labels",
        nargs="*",
        default=list(DEFAULT_ROMS),
        help="Labels from the built-in ROM set to compare.",
    )
    args = parser.parse_args()

    paths = {label: DEFAULT_ROMS[label] for label in args.labels}
    roms = load_roms(paths)
    labels = list(paths)

    direct_rows = differing_rows(roms, direct_offsets(), "bytes", labels)
    main_rows = differing_rows(roms, main_offsets(), "main_raw", labels)

    report = {
        "roms": {
            label: {
                "path": rom["path"],
                "md5": rom["md5"],
                "size": rom["size"],
                "main_consumed": f"0x{rom['main_consumed']:X}",
                "main_error": rom["main_error"],
            }
            for label, rom in roms.items()
        },
        "labels": labels,
        "direct_differing_known_offsets": direct_rows,
        "main_differing_known_offsets": main_rows,
        "summary": {
            "direct_known_diff_count": len(direct_rows),
            "main_known_diff_count": len(main_rows),
            "direct_current_vs_enh480i_ref": summarize_relation(direct_rows, "current_best", "enh480i_ref"),
            "direct_camviewstock_vs_enh480i_ref": summarize_relation(direct_rows, "camviewstock", "enh480i_ref"),
            "main_current_vs_enh480i_ref": summarize_relation(main_rows, "current_best", "enh480i_ref"),
            "main_camviewstock_vs_enh480i_ref": summarize_relation(main_rows, "camviewstock", "enh480i_ref"),
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
