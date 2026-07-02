#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np


def read_frames(ffmpeg, video, start, duration, width, height, fps):
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(video),
        "-t",
        f"{duration:.3f}",
        "-vf",
        f"fps={fps},scale={width}:{height}",
        "-pix_fmt",
        "rgb24",
        "-f",
        "rawvideo",
        "-",
    ]
    proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE)
    frame_size = width * height * 3
    data = proc.stdout
    for offset in range(0, len(data) - frame_size + 1, frame_size):
        yield np.frombuffer(data[offset:offset + frame_size], dtype=np.uint8).reshape((height, width, 3))


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


def percentile(values, pct):
    if not values:
        return None
    return round(float(np.percentile(np.array(values, dtype=np.float32), pct)), 4)


def summarize_rows(rows):
    if not rows:
        return {"frames": 0}
    keys = [
        "mean_luma",
        "bright_ratio",
        "red_ratio",
        "white_ratio",
        "motion",
        "active_width",
        "active_height",
        "active_area_ratio",
    ]
    summary = {"frames": len(rows)}
    for key in keys:
        vals = [row[key] for row in rows if row.get(key) is not None]
        summary[key] = {
            "median": percentile(vals, 50),
            "p10": percentile(vals, 10),
            "p90": percentile(vals, 90),
            "max": round(max(vals), 4) if vals else None,
        }
    largest = max(rows, key=lambda row: row.get("active_area_ratio") or 0)
    summary["largest_active_bbox"] = largest.get("active_bbox")
    summary["largest_active_frame"] = largest.get("frame")
    return summary


def analyze_segment(args, label, video, start, duration):
    rows = []
    prev_luma = None
    for index, frame in enumerate(read_frames(args.ffmpeg, video, start, duration, args.width, args.height, args.fps)):
        arr = frame.astype(np.float32)
        r = arr[:, :, 0]
        g = arr[:, :, 1]
        b = arr[:, :, 2]
        luma = 0.299 * r + 0.587 * g + 0.114 * b
        bright = luma >= args.bright_luma
        red = (r > args.red_floor) & (r > g * args.red_ratio) & (r > b * args.red_ratio)
        white = (luma > args.white_luma) & (np.abs(r - g) < args.white_delta) & (np.abs(g - b) < args.white_delta)
        active = bright | red | white
        active_bbox = bbox(active)
        motion = 0.0 if prev_luma is None else float(np.mean(np.abs(luma - prev_luma)))
        prev_luma = luma
        active_area = 0 if active_bbox is None else active_bbox["width"] * active_bbox["height"]
        rows.append({
            "frame": index,
            "t": round(start + index / args.fps, 3),
            "mean_luma": round(float(np.mean(luma)), 4),
            "bright_ratio": round(float(np.mean(bright)), 6),
            "red_ratio": round(float(np.mean(red)), 6),
            "white_ratio": round(float(np.mean(white)), 6),
            "motion": round(motion, 4),
            "active_bbox": active_bbox,
            "active_width": active_bbox["width"] if active_bbox else None,
            "active_height": active_bbox["height"] if active_bbox else None,
            "active_area_ratio": round(active_area / (args.width * args.height), 6),
        })
    sample_every = max(1, int(round(args.fps * args.sample_seconds)))
    return {
        "label": label,
        "video": str(video),
        "start": start,
        "duration": duration,
        "scale": [args.width, args.height],
        "summary": summarize_rows(rows),
        "samples": rows[::sample_every],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--width", type=int, default=180)
    parser.add_argument("--height", type=int, default=120)
    parser.add_argument("--fps", type=float, default=10.0)
    parser.add_argument("--sample-seconds", type=float, default=1.0)
    parser.add_argument("--bright-luma", type=float, default=32.0)
    parser.add_argument("--white-luma", type=float, default=145.0)
    parser.add_argument("--white-delta", type=float, default=28.0)
    parser.add_argument("--red-floor", type=float, default=55.0)
    parser.add_argument("--red-ratio", type=float, default=1.35)
    parser.add_argument(
        "--segment",
        action="append",
        nargs=4,
        metavar=("LABEL", "VIDEO", "START", "DURATION"),
        required=True,
    )
    args = parser.parse_args()
    reports = [
        analyze_segment(args, label, Path(video), float(start), float(duration))
        for label, video, start, duration in args.segment
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(reports, indent=2) + "\n")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
