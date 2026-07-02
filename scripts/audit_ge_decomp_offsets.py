#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from build_tnd480i_candidate import DIRECT_PATCH_GROUPS, md5

try:
    from capstone import Cs, CS_ARCH_MIPS, CS_MODE_BIG_ENDIAN, CS_MODE_MIPS64
except Exception:
    Cs = None


DEFAULT_DECOMP = Path(r"C:\Users\codex\Documents\n64\007-decomp\src")
SEARCH_DIRS = [Path("."), Path("artifacts/roms"), Path("artifacts/generated")]
ROMS = {
    "ge_stock": "GoldenEye 007 (USA).z64",
    "ge_480i": "BASELINE_GE_480i_direct_from_stock.z64",
    "tnd_base": "BASELINE_TND64_Expanded_direct_from_stock.z64",
}
COMMENT_RE = re.compile(r"/\*\s*([0-9A-Fa-f]{6})\s+([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})\s*\*/\s*(.*)")
FUNC_RE = re.compile(r"^\s*(?:[A-Za-z_][\w\s\*\(\)]*\s+)?([A-Za-z_]\w*)\s*\([^;]*\)\s*$")


def resolve_file(name):
    raw = Path(name)
    if raw.exists():
        return raw
    for base in SEARCH_DIRS:
        candidate = base / name
        if candidate.exists():
            return candidate
    return None


def read_roms():
    out = {}
    for label, name in ROMS.items():
        path = resolve_file(name)
        if path is not None:
            out[label] = {"path": str(path), "data": path.read_bytes()}
    return out


def word(data, off):
    if off < 0 or off + 4 > len(data):
        return None
    return int.from_bytes(data[off:off + 4], "big")


def word_hex(value):
    return None if value is None else f"0x{value:08X}"


def disasm_one(value, off):
    if value is None or Cs is None:
        return ""
    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS64 + CS_MODE_BIG_ENDIAN)
    insns = list(md.disasm(value.to_bytes(4, "big"), off))
    if not insns:
        return ""
    ins = insns[0]
    return f"{ins.mnemonic} {ins.op_str}".strip()


def nearest_function(lines, idx):
    for j in range(idx, max(-1, idx - 80), -1):
        line = lines[j].rstrip()
        if line.startswith("#") or line.startswith("//") or line.startswith("/*"):
            continue
        match = FUNC_RE.match(line)
        if match:
            return match.group(1)
    return ""


def scan_decomp(decomp_root):
    hits = {}
    for path in sorted(decomp_root.rglob("*")):
        if path.suffix.lower() not in {".c", ".h", ".s"}:
            continue
        try:
            lines = path.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for idx, line in enumerate(lines):
            match = COMMENT_RE.search(line)
            if not match:
                continue
            rom_off = int(match.group(1), 16)
            hits.setdefault(rom_off, []).append(
                {
                    "file": str(path),
                    "line": idx + 1,
                    "vram": f"0x{int(match.group(2), 16):08X}",
                    "word": f"0x{int(match.group(3), 16):08X}",
                    "source": match.group(4).strip(),
                    "nearest_function": nearest_function(lines, idx),
                }
            )
    return hits


def patch_offsets():
    offsets = {}
    for group, patches in DIRECT_PATCH_GROUPS.items():
        for off, value, note in patches:
            offsets.setdefault(off, []).append(
                {"group": group, "value": f"0x{value:08X}", "note": note}
            )
    return dict(sorted(offsets.items()))


def annotate_source_matches(source_matches, ge_stock_word):
    annotated = []
    for match in source_matches:
        item = dict(match)
        item["word_matches_ge_stock"] = (
            ge_stock_word is not None and item["word"].lower() == f"0x{ge_stock_word:08X}".lower()
        )
        annotated.append(item)
    return annotated


def build_report(decomp_root):
    roms = read_roms()
    source_hits = scan_decomp(decomp_root)
    rows = []
    for off, patches in patch_offsets().items():
        ge_stock_word = word(roms["ge_stock"]["data"], off) if "ge_stock" in roms else None
        row = {
            "offset": f"0x{off:06X}",
            "patches": patches,
            "source_matches": annotate_source_matches(source_hits.get(off, []), ge_stock_word),
            "rom_words": {},
        }
        for label, entry in roms.items():
            value = word(entry["data"], off)
            row["rom_words"][label] = {
                "word": word_hex(value),
                "disasm": disasm_one(value, off),
            }
        rows.append(row)
    return {
        "decomp_root": str(decomp_root),
        "roms": {
            label: {"path": entry["path"], "md5": md5(entry["data"]), "size": len(entry["data"])}
            for label, entry in roms.items()
        },
        "rows": rows,
    }


def write_markdown(report, out_path):
    lines = [
        "# GE Decomp Offset Audit",
        "",
        f"Decomp root: `{report['decomp_root']}`",
        "",
        "This maps TND6480i direct patch offsets to comments in the local GoldenEye decomp. A blank source match means the offset is not represented by a first-field ROM/source-offset comment in that checkout.",
        "",
        "## High-Risk Findings",
        "",
    ]
    invalid_context = [
        row for row in report["rows"]
        if any("gameplay_viewport" in patch["group"] for patch in row["patches"])
        and row["source_matches"]
        and not any(match["word_matches_ge_stock"] for match in row["source_matches"])
    ]
    for row in invalid_context:
        match = row["source_matches"][0]
        groups = ", ".join(sorted({p["group"] for p in row["patches"]}))
        lines.append(
            f"- `{row['offset']}` ({groups}) has a same-offset decomp comment at `{Path(match['file']).name}:{match['line']}`, but the comment word `{match['word']}` does not match the GE stock ROM word. Treat that decomp line as a version/context collision."
        )
    if not invalid_context:
        lines.append("- No gameplay viewport offset had a mismatched same-offset decomp comment.")
    lines.extend(["", "## Offset Table", ""])
    lines.append("| Offset | Groups | GE stock | GE 480i | TND base | Decomp source matches |")
    lines.append("|---:|---|---|---|---|---|")
    for row in report["rows"]:
        groups = ", ".join(sorted({p["group"] for p in row["patches"]}))
        ge_stock = row["rom_words"].get("ge_stock", {})
        ge_480i = row["rom_words"].get("ge_480i", {})
        tnd_base = row["rom_words"].get("tnd_base", {})
        matches = []
        for match in row["source_matches"][:4]:
            status = "match" if match["word_matches_ge_stock"] else "mismatch"
            matches.append(
                f"`{Path(match['file']).name}:{match['line']}` {status} {match['nearest_function']} `{match['source']}`"
            )
        if len(row["source_matches"]) > 4:
            matches.append(f"+{len(row['source_matches']) - 4} more")
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['offset']}`",
                    groups,
                    f"`{ge_stock.get('word', '')}` {ge_stock.get('disasm', '')}",
                    f"`{ge_480i.get('word', '')}` {ge_480i.get('disasm', '')}",
                    f"`{tnd_base.get('word', '')}` {tnd_base.get('disasm', '')}",
                    "<br>".join(matches) if matches else "",
                ]
            )
            + " |"
        )
    out_path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--decomp-root", type=Path, default=DEFAULT_DECOMP)
    parser.add_argument("--json", type=Path, default=Path("reports/ge_decomp_offset_audit.json"))
    parser.add_argument("--md", type=Path, default=Path("docs/ge_decomp_offset_audit.md"))
    args = parser.parse_args()

    report = build_report(args.decomp_root)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2) + "\n")
    write_markdown(report, args.md)
    print(f"wrote {args.json} and {args.md}")


if __name__ == "__main__":
    main()
