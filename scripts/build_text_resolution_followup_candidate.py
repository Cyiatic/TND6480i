#!/usr/bin/env python3
"""Build a narrow text-resolution follow-up candidate from g1mcfix4.

The 2026-05-24 Analogue check reported that in-game speech and watch/pause
text still look like stock resolution even though the gameplay path is stable.
This script deliberately avoids broad front/menu/framebuffer churn. It audits
the text/font paths and emits one small candidate that fills the GE480i
"other viewport" constants still absent from g1mcfix4.
"""

import json
import re
import shutil
import struct
from collections import Counter
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


ROOT = Path(__file__).resolve().parents[1]
DECOMP_ROOT = Path(r"C:\Users\codex\Documents\n64\007-decomp\src")

ROMS = {
    "ge_stock": ROOT / "artifacts" / "roms" / "GoldenEye 007 (USA).z64",
    "ge480i": ROOT / "artifacts" / "roms" / "BASELINE_GE_480i_direct_from_stock.z64",
    "tnd_base": ROOT / "artifacts" / "roms" / "BASELINE_TND64_Expanded_direct_from_stock.z64",
    "g1mcfix4": ROOT / "artifacts" / "generated" / "g1mcfix4.z64",
}

OUT_ROM = ROOT / "artifacts" / "generated" / "g1txtview1.z64"
OUT_REPORT = ROOT / "reports" / "text_resolution_followup_20260524.json"
OUT_DOC = ROOT / "docs" / "text_resolution_followup_20260524.md"

COMMENT_RE = re.compile(
    r"/\*\s*([0-9A-Fa-f]{6})\s+([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})\s*\*/\s*(.*)"
)
FUNC_RE = re.compile(r"^\s*(?:[A-Za-z_][\w\s\*\(\)]*\s+)?([A-Za-z_]\w*)\s*\([^;]*\)\s*$")

SELECTED_SOURCE_FILES = [
    "game/watch.c",
    "game/mp_watch.c",
    "game/bondview.c",
    "game/gun.c",
    "game/textrelated.c",
    "fr.c",
]

# These are the only simple GE stock -> GE480i viewport constants that
# g1mcfix4 still leaves at stock in the selected text/gameplay source audit.
# They are not the known-stable single-player default/camera constants, which
# are already GE480i in g1mcfix4.
TEXT_VIEWPORT_FOLLOWUP_PATCHES = [
    (0x0BB790, 0x2402013F, "4-player/alternate viewport width return 319"),
    (0x0BB83C, 0x24020141, "4-player/alternate viewport left return 321"),
    (0x0BB874, 0x240200E5, "4-player/alternate viewport height return 229"),
    (0x0BB9A0, 0x240200F1, "2-player/alternate viewport top return 241"),
    (0x0BB9D8, 0x240200F1, "4-player/alternate viewport top return 241"),
]


def word(data, offset):
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def signed16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def mips_lui_addiu_addr(data, lui_offset, addiu_offset):
    hi = word(data, lui_offset) & 0xFFFF
    lo = signed16(word(data, addiu_offset) & 0xFFFF)
    return (hi << 16) + lo


def parse_gothic_like_font(data, offset, size):
    rows = []
    score = 0
    char_offset = 0x2A4
    for i in range(94):
        row_offset = offset + char_offset + i * 0x18
        values = struct.unpack_from(">6I", data, row_offset)
        index, baseline, height, width, kerning_index, pixeldata = values
        signed_baseline = baseline if baseline < 0x80000000 else baseline - 0x100000000
        signed_kerning = (
            kerning_index if kerning_index < 0x80000000 else kerning_index - 0x100000000
        )
        rows.append(
            {
                "index": index,
                "baseline": signed_baseline,
                "height": height,
                "width": width,
                "kerning_index": signed_kerning,
                "pixeldata": pixeldata,
            }
        )
        if index == i:
            score += 3
        if 0 <= index < 128:
            score += 1
        if -16 <= signed_baseline <= 32:
            score += 1
        if 0 < height <= 32:
            score += 1
        if 0 < width <= 32:
            score += 1
        if -1 <= signed_kerning < 32:
            score += 1
        if 0 <= pixeldata < size:
            score += 1
    return {
        "score": score,
        "height_min": min(row["height"] for row in rows),
        "height_max": max(row["height"] for row in rows),
        "width_sum": sum(row["width"] for row in rows),
        "sample_32_45": rows[32:46],
    }


def nearest_function(lines, index):
    for pos in range(index, max(-1, index - 120), -1):
        line = lines[pos].rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "/*", "*")):
            continue
        match = FUNC_RE.match(line)
        if match:
            return match.group(1)
    return ""


def source_mapped_ge480i_diffs(roms):
    rows = []
    for rel_path in SELECTED_SOURCE_FILES:
        source_path = DECOMP_ROOT / rel_path
        lines = source_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for idx, line in enumerate(lines):
            match = COMMENT_RE.search(line)
            if not match:
                continue
            offset = int(match.group(1), 16)
            ge_word = word(roms["ge_stock"], offset)
            ge480_word = word(roms["ge480i"], offset)
            if ge_word is None or ge480_word is None or ge_word == ge480_word:
                continue
            rows.append(
                {
                    "file": rel_path,
                    "line": idx + 1,
                    "function": nearest_function(lines, idx),
                    "offset": f"0x{offset:06X}",
                    "source_word": f"0x{int(match.group(3), 16):08X}",
                    "source": match.group(4).strip(),
                    "words": {
                        "ge_stock": f"0x{ge_word:08X}",
                        "ge480i": f"0x{ge480_word:08X}",
                        "tnd_base": f"0x{word(roms['tnd_base'], offset):08X}",
                        "g1mcfix4": f"0x{word(roms['g1mcfix4'], offset):08X}",
                    },
                    "g1_matches_ge480i": word(roms["g1mcfix4"], offset) == ge480_word,
                }
            )
    return rows


def font_audit(roms):
    rows = {}
    for label, data in roms.items():
        gothic = mips_lui_addiu_addr(data, 0x0E1768, 0x0E1780)
        zurich = mips_lui_addiu_addr(data, 0x0E17F4, 0x0E180C)
        rows[label] = {
            "gothic": {
                "rom_offset": f"0x{gothic:06X}",
                "size": "0x24B0",
                "md5": md5(data[gothic : gothic + 0x24B0]),
                "metrics": parse_gothic_like_font(data, gothic, 0x24B0),
            },
            "zurich": {
                "rom_offset": f"0x{zurich:06X}",
                "size": "0x3540",
                "md5": md5(data[zurich : zurich + 0x3540]),
                "metrics": parse_gothic_like_font(data, zurich, 0x3540),
            },
        }
    return rows


def build_candidate(base_rom):
    data = bytearray(base_rom)
    patches = []
    for offset, new_value, note in TEXT_VIEWPORT_FOLLOWUP_PATCHES:
        old_value = word(data, offset)
        write_word(data, offset, new_value)
        patches.append(
            {
                "offset": f"0x{offset:06X}",
                "old": f"0x{old_value:08X}",
                "new": f"0x{new_value:08X}",
                "note": note,
            }
        )
    crc1, crc2 = update_n64_crc_6102(data)
    OUT_ROM.parent.mkdir(parents=True, exist_ok=True)
    OUT_ROM.write_bytes(data)

    for suffix in (".sav", ".eep"):
        src = ROOT / "artifacts" / "generated" / f"g1mcfix4{suffix}"
        if src.exists():
            shutil.copy2(src, OUT_ROM.with_suffix(suffix))

    return {
        "rom": str(OUT_ROM),
        "md5": md5(data),
        "size": len(data),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": patches,
        "paired_saves": [
            str(OUT_ROM.with_suffix(".sav")),
            str(OUT_ROM.with_suffix(".eep")),
        ],
    }


def write_markdown(report):
    rows = report["source_mapped_ge480i_diffs"]
    misses = [row for row in rows if not row["g1_matches_ge480i"]]
    miss_counts = Counter(row["file"] for row in misses)

    lines = [
        "# Text Resolution Follow-Up - 2026-05-24",
        "",
        "User report: on Analogue 3D, character speech and the pause/watch menu still look like stock-resolution text compared with GE480i.",
        "",
        "## What The Audit Says",
        "",
        f"- Source-mapped GE stock -> GE480i diffs checked in the selected text/gameplay files: `{len(rows)}`.",
        f"- Diffs where `g1mcfix4` does not match GE480i in those files: `{len(misses)}`.",
        "- `watch.c`, `mp_watch.c`, `gun.c`, and the mapped `textrelated.c` diffs already match GE480i in `g1mcfix4`.",
        "- The active Gothic font bank used by the watch/pause menu is byte-identical across GE stock, GE480i, TND64, and `g1mcfix4`.",
        "- The US `textRender` / `textRenderGlow` bodies are not changed by the GE480i patch in the mapped source audit.",
        "",
        "This makes the font-bank theory unlikely for pause text. The remaining low-risk probe is the small viewport-helper family still left at stock in `g1mcfix4`; broader framebuffer selection differences remain intentional and should not be changed without a dedicated hardware comparison.",
        "",
        "## New Diagnostic Candidate",
        "",
        f"- ROM: `{report['candidate']['rom']}`",
        f"- MD5: `{report['candidate']['md5']}`",
        f"- Header CRC: `{report['candidate']['header_crc']}`",
        f"- Save mirrors: `{report['candidate']['paired_saves'][0]}`, `{report['candidate']['paired_saves'][1]}`",
        "",
        "Only these words changed from `g1mcfix4`:",
        "",
        "| Offset | Old | New | Note |",
        "|---:|---:|---:|---|",
    ]
    for patch in report["candidate"]["patches"]:
        lines.append(f"| `{patch['offset']}` | `{patch['old']}` | `{patch['new']}` | {patch['note']} |")

    lines.extend(
        [
            "",
            "## Remaining Miss Summary",
            "",
        ]
    )
    for file_name, count in sorted(miss_counts.items()):
        lines.append(f"- `{file_name}`: `{count}`")
    lines.extend(
        [
            "",
            "The `fr.c` misses are the final split-framebuffer implementation, not simple missed text patches. Replacing them wholesale with GE480i's contiguous stride path would risk the all-level stability we just recovered.",
        ]
    )
    OUT_DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    roms = {label: path.read_bytes() for label, path in ROMS.items()}
    source_rows = source_mapped_ge480i_diffs(roms)
    candidate = build_candidate(roms["g1mcfix4"])
    report = {
        "input_roms": {
            label: {"path": str(path), "md5": md5(roms[label]), "size": len(roms[label])}
            for label, path in ROMS.items()
        },
        "font_audit": font_audit(roms),
        "source_mapped_ge480i_diffs": source_rows,
        "candidate": candidate,
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_DOC.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report)
    print(json.dumps({"candidate": candidate, "report": str(OUT_REPORT), "doc": str(OUT_DOC)}, indent=2))


if __name__ == "__main__":
    main()
