#!/usr/bin/env python3
import json
from pathlib import Path

from build_tnd480i_candidate import (
    DIRECT_PATCH_GROUPS,
    DIRECT_PATCH_PROFILES,
    GE_1172_OFFSET,
    MAIN_RANGES,
    MAIN_RANGE_SETS,
    byte_diff_count,
    inflate_ge1172,
    md5,
)

try:
    from capstone import Cs, CS_ARCH_MIPS, CS_MODE_BIG_ENDIAN, CS_MODE_MIPS64
except Exception:
    Cs = None


REPORT_DIR = Path("reports") if Path("reports").exists() else Path("parallel_diag")
DOC_DIR = Path("docs") if Path("docs").exists() else REPORT_DIR
JSON_OUT = REPORT_DIR / "patch_site_audit.json"
MD_OUT = DOC_DIR / "patch_site_audit.md"

SEARCH_DIRS = [
    Path("."),
    Path("artifacts/roms"),
    Path("artifacts/generated"),
]

ROMS = {
    "GE stock": "GoldenEye 007 (USA).z64",
    "GE 480i": "BASELINE_GE_480i_direct_from_stock.z64",
    "TND base": "BASELINE_TND64_Expanded_direct_from_stock.z64",
    "TND tables only": "TND64_enh480i_core_no_menu_pigz.z64",
    "GE exact all": "TND64_480i_core_allnodims_candidate.z64",
    "single FG+width+scale": "TND64_480i_single8076_mem_fg_h_width_scale_core_no_menu.z64",
    "single FG+origin": "TND64_480i_single8076_mem_fg_h_origin_core_no_menu.z64",
    "single FG+origin+width": "TND64_480i_single8076_mem_fg_h_origin_width_core_no_menu.z64",
    "single FG+origin+scale": "TND64_480i_single8076_mem_fg_h_origin_scale_core_no_menu.z64",
    "single all": "TND64_480i_single8076_all_core_no_menu.z64",
    "single all dim0": "TND64_480i_single8076_all_dim0_core_no_menu.z64",
    "single all dim1": "TND64_480i_single8076_all_dim1_core_no_menu.z64",
    "single all + dims": "TND64_480i_single8076_all_dims_core_no_menu.z64",
    "dim0 only": "TND64_480i_dim0only_core_no_menu.z64",
    "dim1 only": "TND64_480i_dim1only_core_no_menu.z64",
    "FGH only": "TND64_480i_fghonly_core_no_menu.z64",
    "split8030 FG+width+scale": "TND64_480i_split8030_8076_mem_fg_h_width_scale_core_no_menu.z64",
    "split8030 all": "TND64_480i_split8030_8076_all_core_no_menu.z64",
    "split8030 all + dims": "TND64_480i_split8030_8076_all_dims_core_no_menu.z64",
}

PROFILE_HINTS = {
    "GE exact all": "all_nodims",
    "single FG+width+scale": "single8076_mem_fg_h_width_scale_nodims",
    "single FG+origin": "single8076_mem_fg_h_origin_nodims",
    "single FG+origin+width": "single8076_mem_fg_h_origin_width_nodims",
    "single FG+origin+scale": "single8076_mem_fg_h_origin_scale_nodims",
    "single all": "single8076_all_nodims",
    "single all dim0": "single8076_all_dim0",
    "single all dim1": "single8076_all_dim1",
    "single all + dims": "single8076_all_dims",
    "dim0 only": "dim0_only",
    "dim1 only": "dim1_only",
    "FGH only": "fg_h_only",
    "split8030 FG+width+scale": "split8030_8076_mem_fg_h_width_scale_nodims",
    "split8030 all": "split8030_8076_all_nodims",
    "split8030 all + dims": "split8030_8076_all_dims",
}


def read_roms():
    out = {}
    for label, name in ROMS.items():
        path = resolve_rom(name)
        if path.exists():
            out[label] = {"path": str(path), "data": path.read_bytes()}
    return out


def resolve_rom(name):
    raw = Path(name)
    if raw.exists():
        return raw
    for base in SEARCH_DIRS:
        candidate = base / name
        if candidate.exists():
            return candidate
    return raw


def word(data, off):
    return int.from_bytes(data[off : off + 4], "big")


def word_hex(data, off):
    return f"{word(data, off):08X}"


def disasm_one(data, off):
    if Cs is None:
        return ""
    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS64 + CS_MODE_BIG_ENDIAN)
    insns = list(md.disasm(data[off : off + 4], off))
    if not insns:
        return ""
    ins = insns[0]
    return f"{ins.mnemonic} {ins.op_str}".strip()


def merged_runs(indices):
    if not indices:
        return []
    runs = []
    start = prev = indices[0]
    for idx in indices[1:]:
        if idx == prev + 1:
            prev = idx
            continue
        runs.append((start, prev + 1))
        start = prev = idx
    runs.append((start, prev + 1))
    return runs


def safe_byte_runs(roms):
    ge = roms["GE stock"]["data"]
    ge480 = roms["GE 480i"]["data"]
    tnd = roms["TND base"]["data"]
    indices = [
        off
        for off in range(0x1000, GE_1172_OFFSET)
        if ge[off] != ge480[off] and tnd[off] == ge[off]
    ]
    return [
        {"start": f"0x{start:06X}", "end": f"0x{end:06X}", "len": end - start}
        for start, end in merged_runs(indices)
    ]


def patch_offsets():
    offsets = {}
    for group, patches in DIRECT_PATCH_GROUPS.items():
        for off, value, note in patches:
            offsets.setdefault(off, []).append(
                {"group": group, "value": f"{value:08X}", "note": note}
            )
    return dict(sorted(offsets.items()))


def direct_audit(roms):
    offsets = patch_offsets()
    ge = roms["GE stock"]["data"]
    ge480 = roms["GE 480i"]["data"]
    tnd = roms["TND base"]["data"]
    rows = []
    for off, patches in offsets.items():
        row = {
            "offset": f"0x{off:06X}",
            "groups": sorted({p["group"] for p in patches}),
            "notes": sorted({p["note"] for p in patches}),
            "ge_stock": word_hex(ge, off),
            "ge_stock_disasm": disasm_one(ge, off),
            "ge_480i": word_hex(ge480, off),
            "ge_480i_disasm": disasm_one(ge480, off),
            "tnd_base": word_hex(tnd, off),
            "tnd_base_disasm": disasm_one(tnd, off),
            "ge_changed": word(ge, off) != word(ge480, off),
            "tnd_matches_ge_stock": word(tnd, off) == word(ge, off),
            "roms": {},
        }
        for label, entry in roms.items():
            row["roms"][label] = {
                "word": word_hex(entry["data"], off),
                "disasm": disasm_one(entry["data"], off),
            }
        rows.append(row)
    return rows


def profile_matrix(roms):
    rows = []
    for label, profile in PROFILE_HINTS.items():
        if label not in roms:
            continue
        data = roms[label]["data"]
        expected = []
        mismatches = []
        for group in DIRECT_PATCH_PROFILES[profile]:
            for off, value, note in DIRECT_PATCH_GROUPS[group]:
                actual = word(data, off)
                item = {
                    "offset": f"0x{off:06X}",
                    "group": group,
                    "expected": f"{value:08X}",
                    "actual": f"{actual:08X}",
                    "matches": actual == value,
                    "note": note,
                }
                expected.append(item)
                if actual != value:
                    mismatches.append(item)
        rows.append(
            {
                "rom": label,
                "profile": profile,
                "expected_words": len(expected),
                "mismatches": mismatches,
            }
        )
    return rows


def main_range_audit(roms):
    out = []
    ge480_raw, _ = inflate_ge1172(roms["GE 480i"]["data"])
    tnd_raw, _ = inflate_ge1172(roms["TND base"]["data"])
    ranges = MAIN_RANGES + MAIN_RANGE_SETS["menu_only"]
    seen = set()
    unique_ranges = []
    for start, end, note in ranges:
        key = (start, end)
        if key not in seen:
            unique_ranges.append((start, end, note))
            seen.add(key)
    for label, entry in roms.items():
        try:
            raw, consumed = inflate_ge1172(entry["data"])
        except Exception as exc:
            out.append({"rom": label, "error": str(exc)})
            continue
        rows = []
        for start, end, note in unique_ranges:
            chunk = raw[start:end]
            rows.append(
                {
                    "start": f"0x{start:04X}",
                    "end": f"0x{end:04X}",
                    "len": end - start,
                    "note": note,
                    "equals_ge480": chunk == ge480_raw[start:end],
                    "equals_tnd_base": chunk == tnd_raw[start:end],
                    "diff_bytes_from_tnd": byte_diff_count(tnd_raw[start:end], chunk),
                    "diff_bytes_from_ge480": byte_diff_count(ge480_raw[start:end], chunk),
                }
            )
        out.append(
            {
                "rom": label,
                "main_md5": md5(raw),
                "stream_consumed": f"0x{consumed:X}",
                "ranges": rows,
            }
        )
    return out


def write_markdown(report):
    direct_columns = [
        ("single FG+width+scale", "Current single W/S"),
        ("single all", "Single all"),
        ("single all dim0", "Single all dim0"),
        ("single all dim1", "Single all dim1"),
        ("single all + dims", "Single all + dims"),
        ("dim0 only", "Dim0 only"),
        ("dim1 only", "Dim1 only"),
        ("FGH only", "FGH only"),
        ("split8030 all", "Split8030 all"),
        ("split8030 all + dims", "Split8030 all + dims"),
    ]
    direct_columns = [col for col in direct_columns if col[0] in report["roms"]]
    lines = []
    lines.append("# TND64 480i Patch-Site Audit")
    lines.append("")
    lines.append("Generated from local ROMs only. No hardware upload was performed.")
    lines.append("")
    lines.append("## Conclusions")
    lines.append("")
    lines.append(
        "- `TND64_enh480i_core_no_menu_pigz.z64` contains the compressed-main core table changes, but it leaves the direct VI/framebuffer boot-code sites at TND stock values. That matches the observed behavior: it can boot without proving true 480i output."
    )
    lines.append(
        "- `single FG+width+scale` has the single-high framebuffer layout plus GE 480i width/vsync and scale writes, but omits the origin/control-flow bypass at `0x19978/0x19980`."
    )
    lines.append(
        "- `single all` and the new `single FG+origin*` builds add that origin branch family while keeping the safer `0x8076A000` single-buffer memory placement."
    )
    lines.append(
        "- The direct gameplay dimension words at `0x4F354` and `0x4F35C` explain why the no-dims single-all hardware test could still show an aliased Bond hand, but the latest isolation results make those words dangerous to patch first."
    )
    lines.append(
        "- `dim0 only` and `dim1 only` both stayed black in Gopher64 visual capture, and the combined `single all dim0` build black-screened on real hardware. Treat direct dimension patches as a research branch, not the next hardware-first branch."
    )
    lines.append(
        "- `FGH only` keeps framebuffer placement and direct dimensions stock while applying the GE 480i F/G/H VI-side word family. It rendered in Gopher64 visual capture, but later black-screened on real hardware, so the F/G/H family now needs smaller hardware probes before any 480i payload is retried."
    )
    lines.append(
        "- `split8030 all + dims` is the double-buffer fallback that avoids both the earlier `0x80400000` real-hardware failure point and the known `0x8070xxxx` TND references while also applying the direct dimension words."
    )
    lines.append("")
    lines.append("## ROM Inventory")
    lines.append("")
    lines.append("| Label | File | MD5 |")
    lines.append("|---|---|---|")
    for label, entry in report["roms"].items():
        lines.append(f"| {label} | `{entry['path']}` | `{entry['md5']}` |")
    lines.append("")
    safe = report["safe_byte_runs"]
    lines.append("## Portable GE 480i Byte Runs")
    lines.append("")
    lines.append(
        f"`GE stock != GE 480i` and `TND base == GE stock` before the compressed main: {len(safe)} runs, {sum(r['len'] for r in safe)} bytes."
    )
    lines.append("")
    lines.append("| Start | End | Bytes |")
    lines.append("|---:|---:|---:|")
    for row in safe:
        lines.append(f"| `{row['start']}` | `{row['end']}` | {row['len']} |")
    lines.append("")
    lines.append("## Direct Word Sites")
    lines.append("")
    headers = ["Offset", "Groups", "TND base", "GE 480i"] + [name for _, name in direct_columns]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---:"] + ["---"] * (len(headers) - 1)) + "|")
    for row in report["direct_word_sites"]:
        rom_words = row["roms"]
        cols = [
            f"`{row['offset']}`",
            ", ".join(row["groups"]),
            f"`{row['tnd_base']}` {row['tnd_base_disasm']}",
            f"`{row['ge_480i']}` {row['ge_480i_disasm']}",
        ]
        for label, _name in direct_columns:
            cols.append(
                f"`{rom_words.get(label, {}).get('word', 'missing')}` "
                f"{rom_words.get(label, {}).get('disasm', '')}"
            )
        lines.append(
            "| "
            + " | ".join(cols)
            + " |"
        )
    lines.append("")
    lines.append("## Profile Checks")
    lines.append("")
    lines.append("| ROM | Profile | Expected words | Mismatches |")
    lines.append("|---|---|---:|---:|")
    for row in report["profile_matrix"]:
        lines.append(
            f"| {row['rom']} | `{row['profile']}` | {row['expected_words']} | {len(row['mismatches'])} |"
        )
    lines.append("")
    lines.append("## Main Table Ranges")
    lines.append("")
    lines.append("| ROM | Main MD5 | Core ranges equal GE 480i | Menu ranges equal GE 480i |")
    lines.append("|---|---|---:|---:|")
    core_keys = {(s, e) for s, e, _ in MAIN_RANGE_SETS["core_no_menu"]}
    menu_keys = {(s, e) for s, e, _ in MAIN_RANGE_SETS["menu_only"]}
    for row in report["main_ranges"]:
        if "error" in row:
            lines.append(f"| {row['rom']} | error: {row['error']} | 0 | 0 |")
            continue
        core_eq = 0
        menu_eq = 0
        for r in row["ranges"]:
            key = (int(r["start"], 16), int(r["end"], 16))
            if key in core_keys and r["equals_ge480"]:
                core_eq += 1
            if key in menu_keys and r["equals_ge480"]:
                menu_eq += 1
        lines.append(f"| {row['rom']} | `{row['main_md5']}` | {core_eq}/4 | {menu_eq}/2 |")
    lines.append("")
    lines.append(f"Full machine-readable details are in `{JSON_OUT}`.")
    MD_OUT.write_text("\n".join(lines) + "\n")


def main():
    REPORT_DIR.mkdir(exist_ok=True)
    DOC_DIR.mkdir(exist_ok=True)
    roms = read_roms()
    missing = sorted(set(ROMS) - set(roms))
    report_roms = {
        label: {"path": entry["path"], "md5": md5(entry["data"]), "size": len(entry["data"])}
        for label, entry in roms.items()
    }
    report = {
        "missing_rom_labels": missing,
        "roms": report_roms,
        "safe_byte_runs": safe_byte_runs(roms),
        "direct_word_sites": direct_audit(roms),
        "profile_matrix": profile_matrix(roms),
        "main_ranges": main_range_audit(roms),
    }
    JSON_OUT.write_text(json.dumps(report, indent=2) + "\n")
    write_markdown(report)
    print(f"wrote {JSON_OUT} and {MD_OUT}")


if __name__ == "__main__":
    main()
