#!/usr/bin/env python3
"""Extract RGBA5551 framebuffers from an 8 MiB N64 RDRAM dump.

This gives us a measurable answer to the text-sharpness question that does not
depend on emulator presentation scaling.  If GE480i and TND6480i are both
rendering text into a 640x480 buffer, the raw framebuffer should show it.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


RDRAM_SIZE = 0x800000
FRAME_BYTES_640_480_16 = 640 * 480 * 2


def parse_addr(text: str) -> tuple[str, int]:
    if "=" in text:
        label, addr_text = text.split("=", 1)
    else:
        addr_text = text
        label = f"fb_{int(addr_text, 0):08X}"
    value = int(addr_text, 0)
    if value >= 0x80000000:
        value &= 0x7FFFFF
    return label, value


def rgba5551_to_image(raw: bytes, width: int, height: int) -> Image.Image:
    pixels = bytearray(width * height * 4)
    out = 0
    for (word,) in struct.iter_unpack(">H", raw):
        r = (word >> 11) & 0x1F
        g = (word >> 6) & 0x1F
        b = (word >> 1) & 0x1F
        a = word & 1
        pixels[out] = (r << 3) | (r >> 2)
        pixels[out + 1] = (g << 3) | (g >> 2)
        pixels[out + 2] = (b << 3) | (b >> 2)
        pixels[out + 3] = 255 if a else 255
        out += 4
    return Image.frombytes("RGBA", (width, height), bytes(pixels))


def luma_metrics(img: Image.Image) -> dict:
    gray = img.convert("L")
    width, height = gray.size
    px = gray.load()

    total = 0
    total2 = 0
    count = width * height
    for y in range(height):
        for x in range(width):
            v = px[x, y]
            total += v
            total2 += v * v
    mean = total / count
    std = math.sqrt(max(0.0, total2 / count - mean * mean))

    pair_sum = 0
    pair_count = 0
    for y in range(0, height - 1, 2):
        for x in range(width):
            pair_sum += abs(px[x, y] - px[x, y + 1])
            pair_count += 1
    line_pair_mad = pair_sum / pair_count if pair_count else 0.0

    gx_sum = 0
    gy_sum = 0
    edge_count = 0
    edge_total = 0
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            gx = abs(px[x + 1, y] - px[x - 1, y])
            gy = abs(px[x, y + 1] - px[x, y - 1])
            gx_sum += gx
            gy_sum += gy
            mag = gx + gy
            edge_count += mag > 48
            edge_total += 1
    return {
        "mean_luma": mean,
        "std_luma": std,
        "line_pair_mad": line_pair_mad,
        "mean_abs_gx": gx_sum / edge_total if edge_total else 0.0,
        "mean_abs_gy": gy_sum / edge_total if edge_total else 0.0,
        "edge_density": edge_count / edge_total if edge_total else 0.0,
    }


def save_sheet(rows: list[dict], out_path: Path) -> None:
    font = ImageFont.load_default()
    thumbs = []
    for row in rows:
        img = Image.open(row["png"]).convert("RGB")
        img.thumbnail((420, 315))
        tile = Image.new("RGB", (440, 360), "black")
        tile.paste(img, ((440 - img.width) // 2, 34))
        draw = ImageDraw.Draw(tile)
        label = f"{row['label']} off={row['offset']} std={row['metrics']['std_luma']:.1f} edge={row['metrics']['edge_density']:.3f}"
        draw.text((8, 8), label, fill=(255, 255, 255), font=font)
        thumbs.append(tile)
    if not thumbs:
        return
    cols = min(2, len(thumbs))
    sheet = Image.new("RGB", (cols * 440, math.ceil(len(thumbs) / cols) * 360), "black")
    for i, tile in enumerate(thumbs):
        sheet.paste(tile, ((i % cols) * 440, (i // cols) * 360))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract 16-bit N64 RGBA5551 framebuffers from RDRAM.")
    parser.add_argument("dump")
    parser.add_argument("--fb", action="append", required=True, help="LABEL=0xADDR, virtual or physical")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-sheet")
    args = parser.parse_args()

    data = Path(args.dump).read_bytes()
    if len(data) != RDRAM_SIZE:
        raise SystemExit(f"expected 8 MiB RDRAM dump, got {len(data)} bytes")
    frame_bytes = args.width * args.height * 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for fb_text in args.fb:
        label, offset = parse_addr(fb_text)
        if offset < 0 or offset + frame_bytes > len(data):
            rows.append({"label": label, "offset": f"0x{offset:06X}", "error": "out of RDRAM range"})
            continue
        raw = data[offset : offset + frame_bytes]
        img = rgba5551_to_image(raw, args.width, args.height)
        png = out_dir / f"{label}.png"
        img.save(png)
        rows.append({
            "label": label,
            "offset": f"0x{offset:06X}",
            "png": str(png),
            "metrics": luma_metrics(img),
        })

    report = {
        "dump": args.dump,
        "width": args.width,
        "height": args.height,
        "frame_bytes": frame_bytes,
        "frames": rows,
    }
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.out_sheet:
        save_sheet([row for row in rows if "png" in row], Path(args.out_sheet))
    print(json.dumps({"out_json": str(out_json), "out_sheet": args.out_sheet, "frames": rows}, indent=2))


if __name__ == "__main__":
    main()
