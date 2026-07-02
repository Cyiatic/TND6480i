#!/usr/bin/env python3
import argparse
import json
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


TND6480I_EVENTS = [
    ("00:00", "CMK board", "front"),
    ("00:04", "TiJayFly logo", "front"),
    ("00:12", "Rare logo", "front"),
    ("00:16", "Gunbarrel", "front"),
    ("00:37", "TND logo", "front"),
    ("00:41", "Opening credits", "front"),
    ("01:14", "File select dossier", "menu"),
    ("01:28", "Single/Multi/Cheats", "menu"),
    ("01:38", "Mission select", "menu"),
    ("01:46", "Difficulty select", "menu"),
    ("01:55", "Mission briefing", "menu"),
    ("02:01", "Bazaar", "level_flicker"),
    ("03:40", "Party lock", "level_lock"),
    ("04:17", "Labs pickup freeze", "level_freeze"),
    ("06:44", "Press good", "level_good"),
    ("09:50", "Hotel prism", "level_prism"),
    ("10:56", "Parkhaus good", "level_good"),
    ("13:32", "Wreck good", "level_good"),
    ("16:04", "Tower intro crash", "level_crash"),
    ("16:48", "City lock", "level_lock"),
    ("17:39", "Boat intro crash", "level_crash"),
    ("18:09", "Bridge good", "level_good"),
    ("24:25", "Volcano prism", "level_prism"),
    ("25:00", "Alaska good", "level_good"),
]

LEVEL_PROBES = [
    ("Bazaar", "02:01", [0, 4, 12, 28]),
    ("Party", "03:40", [0, 4, 12, 24]),
    ("Labs", "04:17", [0, 12, 60, 115]),
    ("Press", "06:44", [0, 8, 28, 80]),
    ("Hotel", "09:50", [0, 5, 12, 25]),
    ("Parkhaus", "10:56", [0, 8, 28, 80]),
    ("Wreck", "13:32", [0, 8, 28, 80]),
    ("Tower", "16:04", [0, 5, 12, 25]),
    ("City", "16:48", [0, 4, 12, 24]),
    ("Boat", "17:39", [0, 5, 12, 25]),
    ("Bridge", "18:09", [0, 8, 28, 80]),
    ("Volcano", "24:25", [0, 5, 12, 25]),
    ("Alaska", "25:00", [0, 8, 28, 80]),
]


def parse_time(value):
    parts = [int(part) for part in value.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(f"Unsupported timestamp: {value}")


def format_time(seconds):
    seconds = int(round(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def discover_clip_dir():
    docs = Path.home() / "Documents"
    for candidate in docs.iterdir():
        if candidate.is_dir() and candidate.name.startswith("Light Capture"):
            n64 = candidate / "n64"
            if n64.exists():
                return n64
    raise FileNotFoundError("Could not find Documents/Light Capture*/n64")


def find_tnd6480i_video(clip_dir):
    matches = sorted(clip_dir.glob("*6480i*.mpg"))
    if not matches:
        raise FileNotFoundError(f"No *6480i*.mpg file in {clip_dir}")
    return matches[0]


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
    if result.returncode != 0 or not out_png.exists():
        return {
            "ok": False,
            "returncode": result.returncode,
            "stderr_tail": result.stderr.splitlines()[-8:],
        }
    return {"ok": True, "returncode": result.returncode, "stderr_tail": []}


def bbox(mask):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return {
        "left": int(xs.min()),
        "top": int(ys.min()),
        "right": int(xs.max()) + 1,
        "bottom": int(ys.max()) + 1,
        "width": int(xs.max() - xs.min() + 1),
        "height": int(ys.max() - ys.min() + 1),
    }


def frame_metrics(path):
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img, dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    maxc = np.max(arr, axis=2)
    minc = np.min(arr, axis=2)
    nonblack = luma > 16
    bright = luma > 64
    saturated = (maxc > 85) & ((maxc - minc) > 55)
    hot_prism = saturated & (luma > 42)
    active_bbox = bbox(nonblack)
    bright_bbox = bbox(bright)
    return {
        "mean_luma": round(float(np.mean(luma)), 3),
        "nonblack_ratio": round(float(np.mean(nonblack)), 6),
        "bright_ratio": round(float(np.mean(bright)), 6),
        "saturated_ratio": round(float(np.mean(saturated)), 6),
        "prism_ratio": round(float(np.mean(hot_prism)), 6),
        "active_bbox": active_bbox,
        "bright_bbox": bright_bbox,
    }


def load_font(size):
    for name in ("arial.ttf", "consola.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def make_tile(path, title, subtitle, width, height):
    src = Image.open(path).convert("RGB")
    src.thumbnail((width, height - 40), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (width, height), (16, 16, 16))
    x = (width - src.width) // 2
    tile.paste(src, (x, 40))
    draw = ImageDraw.Draw(tile)
    title_font = load_font(15)
    sub_font = load_font(12)
    draw.rectangle([0, 0, width, 40], fill=(0, 0, 0))
    draw.text((6, 4), title[:42], fill=(255, 230, 90), font=title_font)
    draw.text((6, 22), subtitle[:52], fill=(210, 210, 210), font=sub_font)
    return tile


def make_sheet(items, out_path, columns=4, tile_width=360, tile_height=280):
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGB", (columns * tile_width, rows * tile_height), (24, 24, 24))
    for index, item in enumerate(items):
        tile = make_tile(item["path"], item["title"], item["subtitle"], tile_width, tile_height)
        x = (index % columns) * tile_width
        y = (index // columns) * tile_height
        sheet.paste(tile, (x, y))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=92)


def build_atlas(args):
    clip_dir = args.clip_dir or discover_clip_dir()
    video = args.video or find_tnd6480i_video(clip_dir)
    frame_dir = args.out_dir / "frames"
    report = {
        "video": str(video),
        "clip_dir": str(clip_dir),
        "screen_atlas": [],
        "level_probes": [],
    }

    screen_tiles = []
    for index, (stamp, label, family) in enumerate(TND6480I_EVENTS):
        seconds = parse_time(stamp)
        out_png = frame_dir / "screen_atlas" / f"{index:02d}_{stamp.replace(':', '')}_{label.replace('/', '_').replace(' ', '_')}.png"
        capture = run_ffmpeg_frame(args.ffmpeg, video, seconds, out_png)
        if not capture["ok"]:
            report["screen_atlas"].append({
                "timestamp": stamp,
                "seconds": seconds,
                "label": label,
                "family": family,
                "path": str(out_png),
                "capture": capture,
                "skipped": True,
            })
            continue
        metrics = frame_metrics(out_png)
        entry = {
            "timestamp": stamp,
            "seconds": seconds,
            "label": label,
            "family": family,
            "path": str(out_png),
            "metrics": metrics,
        }
        report["screen_atlas"].append(entry)
        screen_tiles.append({
            "path": out_png,
            "title": f"{stamp} {label}",
            "subtitle": f"{family} prism={metrics['prism_ratio']} active_h={metrics['active_bbox']['height'] if metrics['active_bbox'] else 'n/a'}",
        })

    probe_tiles = []
    for level, start, offsets in LEVEL_PROBES:
        base = parse_time(start)
        for offset in offsets:
            seconds = base + offset
            stamp = format_time(seconds)
            out_png = frame_dir / "level_probes" / f"{level}_{stamp.replace(':', '')}_p{offset:03d}.png"
            capture = run_ffmpeg_frame(args.ffmpeg, video, seconds, out_png)
            if not capture["ok"]:
                report["level_probes"].append({
                    "level": level,
                    "timestamp": stamp,
                    "seconds": seconds,
                    "offset_from_level_start": offset,
                    "path": str(out_png),
                    "capture": capture,
                    "skipped": True,
                })
                continue
            metrics = frame_metrics(out_png)
            entry = {
                "level": level,
                "timestamp": stamp,
                "seconds": seconds,
                "offset_from_level_start": offset,
                "path": str(out_png),
                "metrics": metrics,
            }
            report["level_probes"].append(entry)
            probe_tiles.append({
                "path": out_png,
                "title": f"{level} +{offset}s ({stamp})",
                "subtitle": f"prism={metrics['prism_ratio']} active_h={metrics['active_bbox']['height'] if metrics['active_bbox'] else 'n/a'}",
            })

    screen_sheet = args.out_dir / "tnd6480i_screen_atlas_20260516.jpg"
    level_sheet = args.out_dir / "tnd6480i_level_probe_20260516.jpg"
    make_sheet(screen_tiles, screen_sheet, columns=4)
    make_sheet(probe_tiles, level_sheet, columns=4)
    report["outputs"] = {
        "screen_sheet": str(screen_sheet),
        "level_sheet": str(level_sheet),
        "json": str(args.report),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["outputs"], indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", type=Path, default=Path("ffmpeg"))
    parser.add_argument("--clip-dir", type=Path)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("diagnostics/captures/contact_sheets/lightcapture_20260516"))
    parser.add_argument("--report", type=Path, default=Path("reports/video_atlas/tnd6480i_lightcapture_atlas_20260516.json"))
    args = parser.parse_args()
    build_atlas(args)


if __name__ == "__main__":
    main()
