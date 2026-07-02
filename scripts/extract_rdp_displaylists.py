#!/usr/bin/env python3
"""Extract likely live display lists from a raw N64 RDRAM dump.

The first whole-RDRAM RDP scanner was useful but noisy: any 8-byte value whose
top byte looked like an RDP opcode became a false positive.  This tool is more
deliberate.  It tries two independent routes:

1. Scan for GoldenEye's OSScTask/GfxInfo_s structures and read OSTask.data_ptr
   plus OSTask.data_size.
2. Scan RDRAM for dense GBI/RDP command clusters ending in SPEndDisplayList.

The output is intended to compare GE480i and TND6480i runtime display-list
state: color-image width/address, scissors, texture rectangles, and the RDPHalf
words that carry texture-rectangle source/step values.
"""

from __future__ import annotations

import argparse
import json
import struct
from collections import Counter
from pathlib import Path


RDRAM_SIZE = 0x800000

# RSP/GBI and RDP opcodes that commonly appear in GoldenEye display lists.
VALID_OPS = {
    0x01: "Matrix",
    0x03: "MoveMem",
    0x04: "Vertex",
    0x06: "DisplayList",
    0xB1: "Tri2",
    0xB6: "ClearGeometryMode",
    0xB7: "SetGeometryMode",
    0xB8: "EndDisplayList",
    0xB9: "SetOtherModeL",
    0xBA: "SetOtherModeH",
    0xBB: "Texture",
    0xBC: "MoveWord",
    0xBD: "PopMatrix",
    0xBF: "Tri1",
    0xE1: "RDPHalf1",
    0xE2: "SetOtherModeL/RDP",
    0xE3: "SetOtherModeH/RDP",
    0xE4: "TextureRectangle",
    0xE5: "TextureRectangleFlip",
    0xE6: "RDPFullSync",
    0xE7: "RDPPipeSync",
    0xE8: "RDPTileSync",
    0xE9: "RDPLoadSync",
    0xEA: "SetKeyGB",
    0xEB: "SetKeyR",
    0xEC: "SetConvert",
    0xED: "SetScissor",
    0xEE: "SetPrimDepth",
    0xEF: "SetRDPOtherMode",
    0xF0: "LoadTLut",
    0xF2: "SetTileSize",
    0xF3: "LoadBlock",
    0xF4: "LoadTile",
    0xF5: "SetTile",
    0xF6: "FillRectangle",
    0xF7: "SetFillColor",
    0xF8: "SetFogColor",
    0xF9: "SetBlendColor",
    0xFA: "SetPrimColor",
    0xFB: "SetEnvColor",
    0xFC: "SetCombineMode",
    0xFD: "SetTextureImage",
    0xFE: "SetDepthImage",
    0xFF: "SetColorImage",
}

RDP_INTEREST = {0xE1, 0xE4, 0xE5, 0xED, 0xF2, 0xF3, 0xF5, 0xFD, 0xFF}


def be32(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def be64(data: bytes, offset: int) -> int:
    return struct.unpack_from(">Q", data, offset)[0]


def fmt(value: int, width: int = 8) -> str:
    return f"0x{value:0{width}X}"


def ptr_to_rdram_offset(ptr: int) -> int | None:
    """Map a virtual or physical RDRAM pointer to a raw dump offset."""
    if 0 <= ptr < RDRAM_SIZE:
        return ptr
    if 0x80000000 <= ptr < 0x80800000:
        return ptr - 0x80000000
    if 0xA0000000 <= ptr < 0xA0800000:
        return ptr - 0xA0000000
    return None


def decode_setcolorimage(word0: int, word1: int) -> dict:
    return {
        "fmt": (word0 >> 21) & 0x7,
        "siz": (word0 >> 19) & 0x3,
        "width": (word0 & 0xFFF) + 1,
        "addr": word1 & 0x00FFFFFF,
        "raw_addr": fmt(word1),
    }


def decode_setscissor(word0: int, word1: int) -> dict:
    return {
        "mode": (word1 >> 24) & 0x3,
        "xh": ((word0 >> 12) & 0xFFF) / 4.0,
        "yh": (word0 & 0xFFF) / 4.0,
        "xl": ((word1 >> 12) & 0xFFF) / 4.0,
        "yl": (word1 & 0xFFF) / 4.0,
    }


def decode_texrect(word0: int, word1: int) -> dict:
    return {
        "xl": ((word0 >> 12) & 0xFFF) / 4.0,
        "yl": (word0 & 0xFFF) / 4.0,
        "tile": (word1 >> 24) & 0x7,
        "xh": ((word1 >> 12) & 0xFFF) / 4.0,
        "yh": (word1 & 0xFFF) / 4.0,
    }


def decode_settile_size(word0: int, word1: int) -> dict:
    return {
        "xl": ((word0 >> 12) & 0xFFF) / 4.0,
        "yl": (word0 & 0xFFF) / 4.0,
        "tile": (word1 >> 24) & 0x7,
        "xh": ((word1 >> 12) & 0xFFF) / 4.0,
        "yh": (word1 & 0xFFF) / 4.0,
    }


def decode_loadblock(word0: int, word1: int) -> dict:
    return {
        "sl": ((word0 >> 12) & 0xFFF) / 4.0,
        "tl": (word0 & 0xFFF) / 4.0,
        "tile": (word1 >> 24) & 0x7,
        "sh": ((word1 >> 12) & 0xFFF) / 4.0,
        "dxt": word1 & 0xFFF,
    }


def signed16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def decode_rdp_half(word1: int) -> dict:
    return {
        "raw": fmt(word1),
        "s_or_dsdx_s16": signed16(word1 >> 16),
        "t_or_dtdy_s16": signed16(word1),
        "s_or_dsdx_fixed": signed16(word1 >> 16) / 1024.0,
        "t_or_dtdy_fixed": signed16(word1) / 1024.0,
    }


def plausible_decoded(entry: dict) -> bool:
    op = int(entry["op"], 16)
    if op in (0x01, 0x03, 0x04, 0x06, 0xB1, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD, 0xBF):
        return True
    if op == 0xFF:
        ci = entry["color_image"]
        return ci["fmt"] <= 4 and ci["siz"] <= 3 and 1 <= ci["width"] <= 2048 and ci["addr"] < RDRAM_SIZE
    if op == 0xFD:
        ti = entry["texture_image"]
        return ti["fmt"] <= 4 and ti["siz"] <= 3 and 1 <= ti["width"] <= 2048 and ti["addr"] < RDRAM_SIZE
    if op == 0xED:
        sc = entry["scissor"]
        return 0 <= sc["xh"] <= sc["xl"] <= 1024 and 0 <= sc["yh"] <= sc["yl"] <= 1024
    if op in (0xE4, 0xE5):
        rect = entry["texture_rectangle"]
        return 0 <= rect["xh"] <= rect["xl"] <= 1024 and 0 <= rect["yh"] <= rect["yl"] <= 1024
    if op == 0xF2:
        tile = entry["tile_size"]
        return 0 <= tile["xh"] <= 2048 and 0 <= tile["yh"] <= 2048
    if op == 0xF3:
        block = entry["load_block"]
        return 0 <= block["sh"] <= 2048 and 0 <= block["dxt"] <= 0xFFF
    if op in (0xE1, 0xE2, 0xE3, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xEB, 0xEC, 0xEE, 0xEF, 0xF0, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFE):
        return True
    return False


def decode_command(data: bytes, offset: int) -> dict:
    raw = be64(data, offset)
    op = (raw >> 56) & 0xFF
    word0 = (raw >> 32) & 0xFFFFFFFF
    word1 = raw & 0xFFFFFFFF
    entry = {
        "offset": fmt(offset),
        "op": fmt(op, 2),
        "name": VALID_OPS.get(op, "Unknown"),
        "word0": fmt(word0),
        "word1": fmt(word1),
    }
    if op == 0xFF:
        entry["color_image"] = decode_setcolorimage(word0, word1)
    elif op == 0xED:
        entry["scissor"] = decode_setscissor(word0, word1)
    elif op in (0xE4, 0xE5):
        entry["texture_rectangle"] = decode_texrect(word0, word1)
    elif op == 0xE1:
        entry["rdp_half"] = decode_rdp_half(word1)
    elif op == 0xF2:
        entry["tile_size"] = decode_settile_size(word0, word1)
    elif op == 0xF3:
        entry["load_block"] = decode_loadblock(word0, word1)
    elif op == 0xFD:
        entry["texture_image"] = {
            "fmt": (word0 >> 21) & 0x7,
            "siz": (word0 >> 19) & 0x3,
            "width": (word0 & 0xFFF) + 1,
            "addr": word1 & 0x00FFFFFF,
            "raw_addr": fmt(word1),
        }
    return entry


def command_score(entry: dict | None) -> int:
    if entry is None:
        return -5
    op = int(entry["op"], 16)
    if not plausible_decoded(entry):
        return -6
    if op in (0xE4, 0xE5, 0xED, 0xFF):
        return 4
    if op in RDP_INTEREST:
        return 3
    if op in VALID_OPS:
        return 1
    return -5


def summarize_commands(commands: list[dict]) -> dict:
    counts = Counter(cmd["name"] for cmd in commands)
    color_images = [cmd["color_image"] for cmd in commands if "color_image" in cmd]
    scissors = [cmd["scissor"] for cmd in commands if "scissor" in cmd]
    texrects = [cmd for cmd in commands if "texture_rectangle" in cmd]
    texture_images = [cmd["texture_image"] for cmd in commands if "texture_image" in cmd]
    tile_sizes = [cmd["tile_size"] for cmd in commands if "tile_size" in cmd]

    rect_sizes = Counter()
    rect_bounds = []
    for cmd in texrects:
        rect = cmd["texture_rectangle"]
        w = rect["xl"] - rect["xh"]
        h = rect["yl"] - rect["yh"]
        if 0 < w <= 1024 and 0 < h <= 1024:
            rect_sizes[f"{w:.1f}x{h:.1f}"] += 1
            rect_bounds.append([rect["xh"], rect["yh"], rect["xl"], rect["yl"]])

    samples = []
    for index, cmd in enumerate(commands):
        op = int(cmd["op"], 16)
        if op in RDP_INTEREST:
            samples.append(cmd)
        if len(samples) >= 120:
            break

    return {
        "command_counts": dict(counts),
        "color_image_widths": dict(Counter(str(ci["width"]) for ci in color_images)),
        "color_image_samples": color_images[:20],
        "scissor_samples": scissors[:20],
        "texture_image_widths": dict(Counter(str(ti["width"]) for ti in texture_images)),
        "texture_image_samples": texture_images[:20],
        "tile_size_samples": tile_sizes[:20],
        "texture_rectangle_count": len(texrects),
        "texture_rectangle_size_top": rect_sizes.most_common(40),
        "texture_rectangle_bounds_samples": rect_bounds[:40],
        "interesting_samples": samples,
    }


def extract_range(data: bytes, start: int, size: int, max_bytes: int) -> dict:
    end = min(len(data), start + min(size, max_bytes))
    commands = []
    unknown = 0
    valid = 0
    score = 0
    for offset in range(start, end - 7, 8):
        op = data[offset]
        entry = None
        if op in VALID_OPS:
            entry = decode_command(data, offset)
            if plausible_decoded(entry):
                valid += 1
                commands.append(entry)
            else:
                unknown += 1
        else:
            unknown += 1
        score += command_score(entry)
    summary = summarize_commands(commands)
    summary.update({
        "start": fmt(start),
        "end": fmt(end),
        "bytes": end - start,
        "valid_command_slots": valid,
        "unknown_slots": unknown,
        "score": score,
        "valid_ratio": valid / max(1, (end - start) // 8),
    })
    return summary


def find_task_candidates(data: bytes, max_task_bytes: int) -> list[dict]:
    candidates = []
    for offset in range(0, len(data) - 0x60, 4):
        task_type = be32(data, offset + 0x10)
        os_flags = be32(data, offset + 0x08)
        task_flags = be32(data, offset + 0x14)
        ucode_boot = be32(data, offset + 0x18)
        ucode_boot_size = be32(data, offset + 0x1C)
        ucode = be32(data, offset + 0x20)
        ucode_size = be32(data, offset + 0x24)
        ucode_data = be32(data, offset + 0x28)
        ucode_data_size = be32(data, offset + 0x2C)
        data_ptr = be32(data, offset + 0x40)
        data_size = be32(data, offset + 0x44)
        cfb = be32(data, offset + 0x58)
        dl_off = ptr_to_rdram_offset(data_ptr)
        cfb_off = ptr_to_rdram_offset(cfb)
        if task_type != 1:
            continue
        if task_flags & ~0xFF:
            continue
        if task_flags not in (0, 2, 0x12, 0x22, 0x42, 0x62):
            continue
        if os_flags and os_flags & ~0x77:
            continue
        if ptr_to_rdram_offset(ucode_boot) is None or ptr_to_rdram_offset(ucode) is None or ptr_to_rdram_offset(ucode_data) is None:
            continue
        if not (0 < ucode_boot_size <= 0x1000 and 0 < ucode_size <= 0x4000 and 0 < ucode_data_size <= 0x4000):
            continue
        if data_size == 0 or data_size > max_task_bytes or data_size % 8:
            continue
        if dl_off is None or dl_off + data_size > len(data):
            continue
        if cfb and cfb_off is None:
            continue
        extracted = extract_range(data, dl_off, data_size, max_task_bytes)
        if extracted["valid_command_slots"] < 12:
            continue
        candidates.append({
            "method": "OSScTask",
            "gfxinfo_offset": fmt(offset),
            "gfxinfo_vaddr_guess": fmt(0x80000000 + offset),
            "os_flags": fmt(os_flags),
            "task_flags": fmt(task_flags),
            "ucode_boot": fmt(ucode_boot),
            "ucode_boot_size": ucode_boot_size,
            "ucode": fmt(ucode),
            "ucode_size": ucode_size,
            "ucode_data": fmt(ucode_data),
            "ucode_data_size": ucode_data_size,
            "data_ptr": fmt(data_ptr),
            "data_offset": fmt(dl_off),
            "data_size": data_size,
            "cfb": fmt(cfb),
            "cfb_offset": fmt(cfb_off) if cfb_off is not None else None,
            "summary": extracted,
        })
    candidates.sort(
        key=lambda item: (
            item["summary"]["score"],
            item["summary"]["valid_command_slots"],
            item["summary"]["texture_rectangle_count"],
        ),
        reverse=True,
    )
    return candidates


def find_command_clusters(
    data: bytes,
    window_bytes: int,
    min_score: int,
    max_extract_bytes: int,
) -> list[dict]:
    candidates = []
    end = len(data) - window_bytes
    for start in range(0, max(0, end), 8):
        window = data[start : start + window_bytes]
        ops = window[0::8]
        decoded = [decode_command(data, start + i * 8) if op in VALID_OPS else None for i, op in enumerate(ops)]
        valid = sum(1 for entry in decoded if entry is not None and plausible_decoded(entry))
        if valid < len(ops) * 0.55:
            continue
        score = sum(command_score(entry) for entry in decoded)
        if score < min_score:
            continue
        # Walk backward to a sync-ish boundary and forward to SPEndDisplayList or
        # until validity collapses.
        cluster_start = start
        while cluster_start >= 8 and data[cluster_start - 8] in VALID_OPS:
            prev = decode_command(data, cluster_start - 8)
            if not plausible_decoded(prev):
                break
            cluster_start -= 8
        cluster_end = start + window_bytes
        limit = min(len(data) - 8, cluster_start + max_extract_bytes)
        seen_end = False
        while cluster_end <= limit:
            op = data[cluster_end]
            if op not in VALID_OPS:
                break
            entry = decode_command(data, cluster_end)
            if not plausible_decoded(entry):
                break
            cluster_end += 8
            if op == 0xB8:
                seen_end = True
                break
        size = cluster_end - cluster_start
        if size < window_bytes:
            continue
        extracted = extract_range(data, cluster_start, size, max_extract_bytes)
        if extracted["valid_command_slots"] < 20:
            continue
        candidates.append({
            "method": "cluster",
            "data_offset": fmt(cluster_start),
            "data_size": size,
            "ends_with_speenddisplaylist": seen_end,
            "summary": extracted,
        })
    # De-duplicate overlapping clusters by start offset, then keep best.
    by_start = {}
    for cand in candidates:
        key = cand["data_offset"]
        old = by_start.get(key)
        if old is None or cand["summary"]["score"] > old["summary"]["score"]:
            by_start[key] = cand
    deduped = list(by_start.values())
    deduped.sort(
        key=lambda item: (
            item["summary"]["score"],
            item["summary"]["valid_command_slots"],
            item["summary"]["texture_rectangle_count"],
        ),
        reverse=True,
    )
    return deduped


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract likely display lists from an N64 RDRAM dump.")
    parser.add_argument("dump")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--max-task-bytes", type=lambda text: int(text, 0), default=0x40000)
    parser.add_argument("--max-extract-bytes", type=lambda text: int(text, 0), default=0x20000)
    parser.add_argument("--window-bytes", type=lambda text: int(text, 0), default=0x100)
    parser.add_argument("--min-cluster-score", type=int, default=35)
    parser.add_argument("--top", type=int, default=12)
    args = parser.parse_args()

    data = Path(args.dump).read_bytes()
    if len(data) != RDRAM_SIZE:
        raise SystemExit(f"expected 8 MiB RDRAM dump, got {len(data)} bytes")

    task_candidates = find_task_candidates(data, args.max_task_bytes)
    cluster_candidates = find_command_clusters(
        data,
        window_bytes=args.window_bytes,
        min_score=args.min_cluster_score,
        max_extract_bytes=args.max_extract_bytes,
    )
    report = {
        "dump": args.dump,
        "bytes": len(data),
        "task_candidate_count": len(task_candidates),
        "cluster_candidate_count": len(cluster_candidates),
        "task_candidates": task_candidates[: args.top],
        "cluster_candidates": cluster_candidates[: args.top],
    }
    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "out_json": str(out),
        "task_candidates": len(task_candidates),
        "cluster_candidates": len(cluster_candidates),
        "top_task": task_candidates[0] if task_candidates else None,
        "top_cluster": cluster_candidates[0] if cluster_candidates else None,
    }, indent=2)[:5000])


if __name__ == "__main__":
    main()
