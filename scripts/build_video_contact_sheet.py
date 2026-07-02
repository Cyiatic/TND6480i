#!/usr/bin/env python3
import argparse
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def ffmpeg_frame(ffmpeg, video, seconds, out_png):
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{seconds:.3f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        str(out_png),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return {
        "ok": result.returncode == 0 and out_png.exists(),
        "returncode": result.returncode,
        "stderr_tail": result.stderr.splitlines()[-8:],
    }


def duration_seconds(ffprobe, video):
    cmd = [
        str(ffprobe),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return float(result.stdout.strip())


def timestamp(seconds):
    seconds = int(round(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def load_font(size):
    for name in ("consola.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def make_tile(path, label, tile_width, tile_height):
    header = 28
    image = Image.open(path).convert("RGB")
    image.thumbnail((tile_width, tile_height - header), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (tile_width, tile_height), (12, 12, 12))
    tile.paste(image, ((tile_width - image.width) // 2, header + ((tile_height - header - image.height) // 2)))
    draw = ImageDraw.Draw(tile)
    draw.rectangle([0, 0, tile_width, header], fill=(0, 0, 0))
    draw.text((6, 5), label, fill=(245, 245, 245), font=load_font(15))
    return tile


def build_sheet(frames, out_sheet, columns, tile_width, tile_height):
    rows = math.ceil(len(frames) / columns)
    sheet = Image.new("RGB", (columns * tile_width, rows * tile_height), (24, 24, 24))
    for index, item in enumerate(frames):
        tile = make_tile(item["path"], item["label"], tile_width, tile_height)
        sheet.paste(tile, ((index % columns) * tile_width, (index // columns) * tile_height))
    out_sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_sheet, quality=92)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--sheet", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--ffmpeg", type=Path, default=Path("ffmpeg"))
    parser.add_argument("--ffprobe", type=Path, default=Path("ffprobe"))
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--end", type=float, default=None)
    parser.add_argument("--step", type=float, default=1.0)
    parser.add_argument("--columns", type=int, default=8)
    parser.add_argument("--tile-width", type=int, default=300)
    parser.add_argument("--tile-height", type=int, default=230)
    args = parser.parse_args()

    end = args.end if args.end is not None else duration_seconds(args.ffprobe, args.video)
    if args.step <= 0:
        raise SystemExit("--step must be positive")

    frames = []
    seconds = args.start
    index = 0
    while seconds <= end + 0.001:
        out_png = args.out_dir / "frames" / f"frame_{index:04d}_{int(round(seconds * 1000)):08d}.png"
        capture = ffmpeg_frame(args.ffmpeg, args.video, seconds, out_png)
        entry = {
            "index": index,
            "seconds": round(seconds, 3),
            "timestamp": timestamp(seconds),
            "path": str(out_png),
            "capture": capture,
        }
        if capture["ok"]:
            entry["label"] = timestamp(seconds)
            frames.append(entry)
        index += 1
        seconds += args.step

    build_sheet(frames, args.sheet, args.columns, args.tile_width, args.tile_height)
    report = {
        "video": str(args.video),
        "sheet": str(args.sheet),
        "start": args.start,
        "end": end,
        "step": args.step,
        "frames": frames,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sheet": str(args.sheet), "frames": len(frames)}, indent=2))


if __name__ == "__main__":
    main()
