#!/usr/bin/env python3
"""Static 480i contract checker for GoldenEye/TND64 candidates.

This does not prove visual taste. It answers the part that should be
measurable before hardware testing: do the relevant ROM words describe a
coherent 640x480 interlaced render path, GE480i-class text/overlay constants,
and non-overlapping 640x480 framebuffers?
"""

import argparse
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GE480I = ROOT / "artifacts" / "roms" / "BASELINE_GE_480i_direct_from_stock.z64"
SAFE_DIFF_REPORT = ROOT / "reports" / "safe_unported_ge480i_code_words_g1mcfix4_20260524.json"

EXPANSION_DELTA = 0x00400000
TLB_PAGE_COUNT = 90
TLB_PAGE_BYTES = 0x2000
FB_BYTES = 0x96000
GE_FB0 = 0x806D4000
GE_FB1 = 0x8076A000

VI_SWAP_OFFSETS = [
    0x019978,
    0x019980,
    0x019984,
    0x0199B4,
    0x0199D0,
    0x019A24,
    0x019A60,
    0x019A64,
]

DIRECT_DIM_OFFSETS = [
    0x04F354,
    0x04F35C,
]

BONDVIEW_VIEWPORT_OFFSETS = [
    0x0BB730,
    0x0BB740,
    0x0BB754,
    0x0BB764,
    0x0BB7A4,
    0x0BB7C0,
    0x0BB7D0,
    0x0BB7E0,
    0x0BB89C,
    0x0BB8B8,
    0x0BB8C0,
    0x0BB91C,
    0x0BB954,
    0x0BBA80,
]

TEXT_VIEWPORT_OFFSETS = [
    0x0BB790,
    0x0BB83C,
    0x0BB874,
    0x0BB9A0,
    0x0BB9D8,
]

HUD_NUMERIC_Y_OFFSETS = [
    0x08AE9C,
    0x08AEF0,
    0x08AF3C,
    0x08AF9C,
    0x08AFF0,
    0x08B03C,
    0x08B09C,
    0x08B0F0,
]

MENU_BUFFER_OFFSETS = [
    0x035920,
    0x035924,
    0x03592C,
    0x03FC90,
    0x03FC94,
    0x040540,
    0x040544,
]

FRAMEBUFFER_WORD_OFFSETS = [
    0x00241C,
    0x002420,
    0x003C8C,
    0x003C90,
    0x003C94,
    0x003D30,
    0x003D34,
    0x003D38,
    0x003D3C,
    0x003D40,
    0x003D44,
    0x003D48,
    0x003D4C,
    0x003D50,
    0x003D54,
    0x0046B4,
    0x0046B8,
    0x0046BC,
    0x0046C0,
    0x0046C4,
    0x0046C8,
    0x0046CC,
    0x0046D0,
    0x0046D4,
    0x0046D8,
    0x0046DC,
    0x0046E0,
    0x0046E4,
    0x0046E8,
    0x0046EC,
    0x006584,
    0x006588,
    0x00658C,
    0x006590,
    0x006594,
    0x006598,
    0x00659C,
    0x0065A0,
    0x0065A4,
    0x0065A8,
    0x0065AC,
    0x0065B0,
    0x0065B4,
]


def read_word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def fmt(value):
    return f"0x{value:08X}"


def signed16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def decode_lui_imm(word):
    return word & 0xFFFF if (word >> 26) == 0x0F else None


def decode_low_imm(word, expected_rt=None, expected_rs=None):
    opcode = word >> 26
    if opcode not in (0x09, 0x0D):  # addiu / ori
        return None
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    if expected_rt is not None and rt != expected_rt:
        return None
    if expected_rs is not None and rs != expected_rs:
        return None
    imm = word & 0xFFFF
    return imm if opcode == 0x0D else signed16(imm)


def parse_lui_low(data, upper_off, lower_off, reg):
    upper_word = read_word(data, upper_off)
    lower_word = read_word(data, lower_off)
    upper = decode_lui_imm(upper_word)
    lower = decode_low_imm(lower_word, expected_rt=reg, expected_rs=reg)
    if upper is None or lower is None:
        return None
    return ((upper << 16) + lower) & 0xFFFFFFFF


def overlap(a_start, a_len, b_start, b_len):
    a_end = a_start + a_len - 1
    b_end = b_start + b_len - 1
    return max(a_start, b_start) <= min(a_end, b_end)


def load_overlay_offsets():
    if not SAFE_DIFF_REPORT.exists():
        return []
    data = json.loads(SAFE_DIFF_REPORT.read_text(encoding="utf-8"))
    offsets = []
    for row in data.get("rows", []):
        offset = int(row["offset"], 16)
        if 0x043F94 <= offset <= 0x044B54:
            offsets.append(offset)
    return sorted(set(offsets))


def compare_offsets(data, ge, offsets):
    rows = []
    matches = 0
    for offset in offsets:
        got = read_word(data, offset)
        want = read_word(ge, offset)
        match = got == want
        matches += int(match)
        rows.append({
            "offset": f"0x{offset:06X}",
            "candidate": fmt(got),
            "ge480i": fmt(want),
            "match": match,
        })
    total = len(offsets)
    return {
        "matches": matches,
        "total": total,
        "ratio": (matches / total) if total else 1.0,
        "mismatches": [row for row in rows if not row["match"]],
    }


def infer_framebuffer_model(data):
    tlb_direct = parse_lui_low(data, 0x00241C, 0x002420, 8)
    tlb_expanded = tlb_direct + EXPANSION_DELTA if tlb_direct is not None else None
    tlb_range = None
    if tlb_expanded is not None:
        tlb_range = [tlb_expanded, tlb_expanded + TLB_PAGE_COUNT * TLB_PAGE_BYTES - 1]

    split_fb0 = parse_lui_low(data, 0x006584, 0x006588, 4)
    split_fb1 = parse_lui_low(data, 0x00658C, 0x006590, 5)
    clear_fb0 = parse_lui_low(data, 0x003D30, 0x003D34, 4)
    clear_fb1 = parse_lui_low(data, 0x003D48, 0x003D4C, 4)

    fb0 = split_fb0
    fb1 = split_fb1
    model = "split_explicit"
    if fb0 is None or fb1 is None:
        # GE480i contiguous form computes fb1 = 0x80800000 - 0x96000 and
        # fb0 = fb1 - 0x96000 in the global initializer.
        if (
            read_word(data, 0x006584) == 0x3C048080
            and read_word(data, 0x00658C) == 0x3C020009
            and read_word(data, 0x006590) == 0x24426000
        ):
            fb0 = GE_FB0
            fb1 = GE_FB1
            model = "ge_contiguous_computed"
        else:
            model = "unknown"

    fb_ranges = []
    if fb0 is not None:
        fb_ranges.append({"name": "fb0", "start": fb0, "end": fb0 + FB_BYTES - 1})
    if fb1 is not None:
        fb_ranges.append({"name": "fb1", "start": fb1, "end": fb1 + FB_BYTES - 1})

    overlaps = []
    if tlb_expanded is not None:
        for fb in fb_ranges:
            if overlap(tlb_expanded, TLB_PAGE_COUNT * TLB_PAGE_BYTES, fb["start"], FB_BYTES):
                overlaps.append(fb["name"])

    upper_pair = fb0 == GE_FB0 and fb1 == GE_FB1
    adjacent_pair = fb0 is not None and fb1 is not None and fb0 + FB_BYTES == fb1

    return {
        "model": model,
        "tlb_direct_base": None if tlb_direct is None else fmt(tlb_direct),
        "tlb_expanded_range": None if tlb_range is None else [fmt(tlb_range[0]), fmt(tlb_range[1])],
        "framebuffers": [
            {"name": item["name"], "range": [fmt(item["start"]), fmt(item["end"])]}
            for item in fb_ranges
        ],
        "clear_targets": {
            "fb0": None if clear_fb0 is None else fmt(clear_fb0),
            "fb1": None if clear_fb1 is None else fmt(clear_fb1),
        },
        "ge_upper_pair": upper_pair,
        "adjacent_pair": adjacent_pair,
        "tlb_overlaps": overlaps,
        "passes": {
            "two_buffers": fb0 is not None and fb1 is not None and fb0 != fb1,
            "both_640x480": fb0 is not None and fb1 is not None,
            "no_tlb_overlap": not overlaps,
            "ge_upper_adjacent_pair": upper_pair and adjacent_pair,
        },
    }


def analyze_rom(path, ge, overlay_offsets):
    data = path.read_bytes()
    categories = {
        "vi_swap": compare_offsets(data, ge, VI_SWAP_OFFSETS),
        "direct_dimensions": compare_offsets(data, ge, DIRECT_DIM_OFFSETS),
        "bondview_viewports": compare_offsets(data, ge, BONDVIEW_VIEWPORT_OFFSETS),
        "text_viewports": compare_offsets(data, ge, TEXT_VIEWPORT_OFFSETS),
        "hud_numeric_y": compare_offsets(data, ge, HUD_NUMERIC_Y_OFFSETS),
        "menu_buffer": compare_offsets(data, ge, MENU_BUFFER_OFFSETS),
        "ingame_overlay_family": compare_offsets(data, ge, overlay_offsets),
    }
    framebuffer = infer_framebuffer_model(data)
    word_matrix = {
        f"0x{offset:06X}": fmt(read_word(data, offset))
        for offset in FRAMEBUFFER_WORD_OFFSETS
    }
    passes = {
        "framebuffer_contract": all(framebuffer["passes"].values()),
        "vi_swap_exact": categories["vi_swap"]["ratio"] == 1.0,
        "direct_dimensions_exact": categories["direct_dimensions"]["ratio"] == 1.0,
        "bondview_viewports_exact": categories["bondview_viewports"]["ratio"] == 1.0,
        "text_related_exact": all(
            categories[name]["ratio"] == 1.0
            for name in ("text_viewports", "hud_numeric_y", "menu_buffer", "ingame_overlay_family")
        ),
    }
    return {
        "path": str(path),
        "md5": md5(data),
        "size": len(data),
        "framebuffer": framebuffer,
        "categories": categories,
        "framebuffer_word_matrix": word_matrix,
        "passes": passes,
        "overall_static_pass": all(passes.values()),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("roms", nargs="+", type=Path)
    parser.add_argument("--ge480i", type=Path, default=DEFAULT_GE480I)
    parser.add_argument("--out-json", type=Path)
    args = parser.parse_args()

    ge = args.ge480i.read_bytes()
    overlay_offsets = load_overlay_offsets()
    report = {
        "ge480i_reference": str(args.ge480i),
        "checks": {
            "tlb_page_count": TLB_PAGE_COUNT,
            "tlb_page_bytes": f"0x{TLB_PAGE_BYTES:X}",
            "framebuffer_bytes": f"0x{FB_BYTES:X}",
            "target_framebuffers": {
                "fb0": [fmt(GE_FB0), fmt(GE_FB0 + FB_BYTES - 1)],
                "fb1": [fmt(GE_FB1), fmt(GE_FB1 + FB_BYTES - 1)],
            },
            "ingame_overlay_offsets": len(overlay_offsets),
        },
        "roms": [analyze_rom(path, ge, overlay_offsets) for path in args.roms],
    }

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for item in report["roms"]:
        fb = item["framebuffer"]
        print(Path(item["path"]).name)
        print(f"  overall_static_pass: {item['overall_static_pass']}")
        print(f"  framebuffer: {fb['model']} {fb['framebuffers']} tlb={fb['tlb_expanded_range']} overlaps={fb['tlb_overlaps']}")
        for name, category in item["categories"].items():
            print(f"  {name}: {category['matches']}/{category['total']}")


if __name__ == "__main__":
    main()
