#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASELINE_SOURCES = ("GE480i_reference", "Current_t90tex_direct")

BASELINE_ALIASES = {
    "Current_t90tex_direct": ("Current_t90tex_direct", "Current_t90tex"),
}


def safe_name(value):
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")


def ffmpeg_frame(ffmpeg, video, seconds, out_png):
    out_png.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
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
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
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


def make_tile(path, label, tile_width, tile_height):
    header = 30
    image = Image.open(path).convert("RGB")
    image.thumbnail((tile_width, tile_height - header), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (tile_width, tile_height), (16, 16, 16))
    tile.paste(image, ((tile_width - image.width) // 2, header + ((tile_height - header - image.height) // 2)))
    draw = ImageDraw.Draw(tile)
    draw.rectangle([0, 0, tile_width, header], fill=(0, 0, 0))
    draw.text((7, 6), label, fill=(245, 245, 245), font=load_font(15))
    return tile


def build_sheet(rows, columns, frames, out_sheet, tile_width, tile_height):
    label_width = 150
    sheet = Image.new("RGB", (label_width + len(columns) * tile_width, len(rows) * tile_height), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    page_font = load_font(18)
    for row_index, page in enumerate(rows):
        y = row_index * tile_height
        draw.rectangle([0, y, label_width, y + tile_height], fill=(8, 8, 8))
        draw.text((10, y + 14), page, fill=(255, 255, 255), font=page_font)
        for column_index, column in enumerate(columns):
            item = frames.get((page, column))
            x = label_width + column_index * tile_width
            if item and Path(item["path"]).exists():
                tile = make_tile(item["path"], column, tile_width, tile_height)
            else:
                tile = Image.new("RGB", (tile_width, tile_height), (40, 10, 10))
                ImageDraw.Draw(tile).text((10, 10), f"missing\n{column}", fill=(255, 220, 220), font=load_font(15))
            sheet.paste(tile, (x, y))
    out_sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_sheet, quality=92)


def parse_candidate(value):
    parts = value.split("|")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("candidate must be PAGE|LABEL|VIDEO|SECONDS")
    page, label, video, seconds = parts
    return {
        "page": page,
        "label": label,
        "video": Path(video),
        "seconds": float(seconds),
    }


def find_baseline_frame(baseline_frames, page_key, source):
    for candidate_source in BASELINE_ALIASES.get(source, (source,)):
        path = baseline_frames / f"{page_key}__{candidate_source}.png"
        if path.exists():
            return path
    return baseline_frames / f"{page_key}__{source}.png"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-frames", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--sheet", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, default=Path("ffmpeg"))
    parser.add_argument("--candidate", action="append", type=parse_candidate, required=True)
    parser.add_argument("--tile-width", type=int, default=360)
    parser.add_argument("--tile-height", type=int, default=270)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = args.out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for candidate in args.candidate:
        if candidate["page"] not in rows:
            rows.append(candidate["page"])

    columns = ["GE480i reference", "Current t90tex"]
    for candidate in args.candidate:
        if candidate["label"] not in columns:
            columns.append(candidate["label"])

    frames = {}
    entries = []
    for page in rows:
        page_key = safe_name(page)
        for source, label in zip(BASELINE_SOURCES, columns[:2]):
            source_path = find_baseline_frame(args.baseline_frames, page_key, source)
            target_path = frames_dir / f"{page_key}__{safe_name(label)}.png"
            capture = {"ok": source_path.exists(), "copied": False}
            if source_path.exists():
                shutil.copy2(source_path, target_path)
                capture["copied"] = True
            entry = {
                "page": page,
                "source": label,
                "path": str(target_path),
                "capture": capture,
            }
            frames[(page, label)] = entry
            entries.append(entry)

    for candidate in args.candidate:
        page = candidate["page"]
        label = candidate["label"]
        target_path = frames_dir / f"{safe_name(page)}__{safe_name(label)}.png"
        capture = ffmpeg_frame(args.ffmpeg, candidate["video"], candidate["seconds"], target_path)
        entry = {
            "page": page,
            "source": label,
            "video": str(candidate["video"]),
            "seconds": candidate["seconds"],
            "path": str(target_path),
            "capture": capture,
        }
        frames[(page, label)] = entry
        entries.append(entry)

    build_sheet(rows, columns, frames, args.sheet, args.tile_width, args.tile_height)
    report = {
        "sheet": str(args.sheet),
        "baseline_frames": str(args.baseline_frames),
        "rows": rows,
        "columns": columns,
        "entries": entries,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sheet": str(args.sheet), "rows": rows, "columns": columns}, indent=2))


if __name__ == "__main__":
    main()
