#!/usr/bin/env python3
import argparse
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def run_ffmpeg_frame(ffmpeg, video, seconds, out_png):
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


def load_font(size):
    for name in ("consola.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def tile_for(path, label, tile_width, tile_height):
    header = 30
    image = Image.open(path).convert("RGB")
    image.thumbnail((tile_width, tile_height - header), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (tile_width, tile_height), (12, 12, 12))
    x = (tile_width - image.width) // 2
    y = header + ((tile_height - header - image.height) // 2)
    tile.paste(image, (x, y))
    draw = ImageDraw.Draw(tile)
    draw.rectangle([0, 0, tile_width, header], fill=(0, 0, 0))
    draw.text((6, 6), label, fill=(245, 245, 245), font=load_font(14))
    return tile


def build_sheet(frame_entries, sheet_path, columns, tile_width, tile_height):
    rows = math.ceil(len(frame_entries) / columns)
    sheet = Image.new("RGB", (columns * tile_width, rows * tile_height), (24, 24, 24))
    for index, entry in enumerate(frame_entries):
        tile = tile_for(Path(entry["path"]), entry["label"], tile_width, tile_height)
        sheet.paste(tile, ((index % columns) * tile_width, (index // columns) * tile_height))
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(sheet_path, quality=92)


def parse_source(raw):
    parts = raw.split("|", 2)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("--source must be LABEL|VIDEO|START_SECONDS")
    label, video, start = parts
    return {"label": label, "video": Path(video), "start": float(start)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", type=parse_source, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--sheet", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, default=Path("ffmpeg"))
    parser.add_argument("--relative", type=float, nargs="+", required=True)
    parser.add_argument("--columns", type=int, default=13)
    parser.add_argument("--tile-width", type=int, default=270)
    parser.add_argument("--tile-height", type=int, default=210)
    args = parser.parse_args()

    entries = []
    for source in args.source:
        safe_label = "".join(c if c.isalnum() else "_" for c in source["label"]).strip("_")
        for rel in args.relative:
            seconds = source["start"] + rel
            out_png = args.out_dir / "frames" / f"{safe_label}_{int(round(rel * 1000)):08d}.png"
            capture = run_ffmpeg_frame(args.ffmpeg, source["video"], seconds, out_png)
            entry = {
                "source": source["label"],
                "relative": rel,
                "seconds": round(seconds, 3),
                "path": str(out_png),
                "capture": capture,
            }
            if capture["ok"]:
                entry["label"] = f"{source['label']} +{rel:g}s"
                entries.append(entry)

    build_sheet(entries, args.sheet, args.columns, args.tile_width, args.tile_height)
    report = {
        "sheet": str(args.sheet),
        "sources": [
            {"label": s["label"], "video": str(s["video"]), "start": s["start"]}
            for s in args.source
        ],
        "relative": args.relative,
        "frames": entries,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sheet": str(args.sheet), "frames": len(entries)}, indent=2))


if __name__ == "__main__":
    main()
