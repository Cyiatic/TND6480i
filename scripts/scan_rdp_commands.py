#!/usr/bin/env python3
"""Scan a memory/state dump for plausible RDP commands.

This is a lightweight helper for comparing runtime display-list evidence between
GE480i and TND6480i.  It does not need symbols.  It scans big-endian 64-bit
words and decodes the RDP commands that matter for the 480i/text-quality gate:

  * SetColorImage: framebuffer format/width/address
  * SetScissor: viewport/scissor rectangle
  * TextureRectangle / TextureRectangleFlip: glyph/sprite rectangles

Because a raw RDRAM/savestate dump contains false positives, the output is a
summary plus filtered "plausible text rectangle" samples.  Use it as a
comparison aid, not as sole proof.
"""

import argparse
import json
import struct
from collections import Counter
from pathlib import Path


RDP_NAMES = {
    0xE4: "TextureRectangle",
    0xE5: "TextureRectangleFlip",
    0xED: "SetScissor",
    0xFF: "SetColorImage",
}


def be64(data, offset):
    return struct.unpack_from(">Q", data, offset)[0]


def decode_texrect(word0, word1):
    return {
        "xl": ((word0 >> 12) & 0xFFF) / 4.0,
        "yl": (word0 & 0xFFF) / 4.0,
        "tile": (word1 >> 24) & 0x7,
        "xh": ((word1 >> 12) & 0xFFF) / 4.0,
        "yh": (word1 & 0xFFF) / 4.0,
    }


def decode_setscissor(word0, word1):
    return {
        "mode": (word1 >> 24) & 0x3,
        "xh": ((word0 >> 12) & 0xFFF) / 4.0,
        "yh": (word0 & 0xFFF) / 4.0,
        "xl": ((word1 >> 12) & 0xFFF) / 4.0,
        "yl": (word1 & 0xFFF) / 4.0,
    }


def decode_setcolorimage(word0, word1):
    return {
        "fmt": (word0 >> 21) & 0x7,
        "siz": (word0 >> 19) & 0x3,
        "width": (word0 & 0xFFF) + 1,
        "addr": word1 & 0x00FFFFFF,
        "raw_addr": word1,
    }


def plausible_rect(rect, max_width=640, max_height=480):
    w = rect["xl"] - rect["xh"]
    h = rect["yl"] - rect["yh"]
    if w <= 0 or h <= 0:
        return False
    if rect["xh"] < 0 or rect["yh"] < 0 or rect["xl"] > max_width + 16 or rect["yl"] > max_height + 16:
        return False
    # Font glyph rectangles are usually small; keep sprites too, but exclude
    # full-screen fills.
    return w <= 96 and h <= 96


def scan(data, start=0, end=None, step=8):
    end = len(data) if end is None else min(end, len(data))
    commands = []
    counts = Counter()
    for offset in range(start, max(start, end - 7), step):
        raw = be64(data, offset)
        cmd = (raw >> 56) & 0xFF
        if cmd not in RDP_NAMES:
            continue
        word0 = (raw >> 32) & 0xFFFFFFFF
        word1 = raw & 0xFFFFFFFF
        entry = {
            "offset": f"0x{offset:08X}",
            "cmd": f"0x{cmd:02X}",
            "name": RDP_NAMES[cmd],
            "word0": f"0x{word0:08X}",
            "word1": f"0x{word1:08X}",
        }
        if cmd in (0xE4, 0xE5):
            entry["rect"] = decode_texrect(word0, word1)
        elif cmd == 0xED:
            entry["scissor"] = decode_setscissor(word0, word1)
        elif cmd == 0xFF:
            entry["color_image"] = decode_setcolorimage(word0, word1)
        commands.append(entry)
        counts[RDP_NAMES[cmd]] += 1
    return commands, counts


def summarize(commands, counts):
    color_images = [cmd["color_image"] for cmd in commands if "color_image" in cmd]
    scissors = [cmd["scissor"] for cmd in commands if "scissor" in cmd]
    texrects = [cmd for cmd in commands if "rect" in cmd and plausible_rect(cmd["rect"])]
    texrect_sizes = Counter()
    for cmd in texrects:
        rect = cmd["rect"]
        w = round(rect["xl"] - rect["xh"], 1)
        h = round(rect["yl"] - rect["yh"], 1)
        texrect_sizes[f"{w}x{h}"] += 1
    return {
        "command_counts": dict(counts),
        "color_image_widths": dict(Counter(str(ci["width"]) for ci in color_images)),
        "color_image_samples": color_images[:20],
        "scissor_samples": scissors[:20],
        "plausible_text_rect_count": len(texrects),
        "plausible_text_rect_size_top": texrect_sizes.most_common(30),
        "plausible_text_rect_samples": texrects[:60],
    }


def main():
    parser = argparse.ArgumentParser(description="Scan a binary memory/state dump for RDP commands.")
    parser.add_argument("dump")
    parser.add_argument("--start", default="0")
    parser.add_argument("--end")
    parser.add_argument("--step", type=int, default=8)
    parser.add_argument("--out-json", required=True)
    args = parser.parse_args()

    data = Path(args.dump).read_bytes()
    start = int(args.start, 0)
    end = int(args.end, 0) if args.end else None
    commands, counts = scan(data, start=start, end=end, step=args.step)
    report = {
        "dump": args.dump,
        "bytes": len(data),
        "scan": {"start": start, "end": end or len(data), "step": args.step},
        "summary": summarize(commands, counts),
    }
    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out_json": str(out), "commands": len(commands), **report["summary"]}, indent=2)[:4000])


if __name__ == "__main__":
    main()
