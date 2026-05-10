#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np


def stream_frames(ffmpeg, video, width, height, scale_width, scale_height):
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video),
        "-vf",
        f"scale={scale_width}:{scale_height}",
        "-pix_fmt",
        "rgb24",
        "-f",
        "rawvideo",
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    frame_size = scale_width * scale_height * 3
    index = 0
    try:
        while True:
            raw = proc.stdout.read(frame_size)
            if len(raw) != frame_size:
                break
            frame = np.frombuffer(raw, dtype=np.uint8).reshape((scale_height, scale_width, 3))
            yield index, frame
            index += 1
    finally:
        proc.stdout.close()
        proc.wait(timeout=10)


def sustained_start(rows, key, threshold, fps, after=0.0, seconds=0.5, greater=True):
    run = int(max(1, round(seconds * fps)))
    start_frame = int(round(after * fps))
    values = [row[key] for row in rows]
    for i in range(start_frame, max(0, len(values) - run + 1)):
        window = values[i:i + run]
        ok = all(v >= threshold for v in window) if greater else all(v <= threshold for v in window)
        if ok:
            return rows[i]["t"]
    return None


def local_max_time(rows, key, after=0.0, before=None):
    candidates = [row for row in rows if row["t"] >= after and (before is None or row["t"] <= before)]
    if not candidates:
        return None
    row = max(candidates, key=lambda item: item[key])
    return {"t": row["t"], "value": row[key]}


def analyze(args, video):
    fps = args.fps
    rows = []
    prev_luma = None
    for index, frame in stream_frames(args.ffmpeg, video, args.width, args.height, args.scale_width, args.scale_height):
        arr = frame.astype(np.float32)
        r = arr[:, :, 0]
        g = arr[:, :, 1]
        b = arr[:, :, 2]
        luma = 0.299 * r + 0.587 * g + 0.114 * b
        white = (luma > 170) & (np.abs(r - g) < 25) & (np.abs(g - b) < 25)
        red = (r > 70) & (r > g * 1.45) & (r > b * 1.45)
        bright = luma > 48
        motion = 0.0 if prev_luma is None else float(np.mean(np.abs(luma - prev_luma)))
        prev_luma = luma
        rows.append({
            "frame": index,
            "t": round(index / fps, 3),
            "mean_luma": round(float(np.mean(luma)), 3),
            "white_ratio": round(float(np.mean(white)), 5),
            "red_ratio": round(float(np.mean(red)), 5),
            "bright_ratio": round(float(np.mean(bright)), 5),
            "motion": round(motion, 3),
        })

    events = {
        "first_sustained_bright_after_5s": sustained_start(rows, "bright_ratio", args.bright_threshold, fps, after=5.0),
        "first_sustained_white_after_5s": sustained_start(rows, "white_ratio", args.white_threshold, fps, after=5.0),
        "first_sustained_red_after_5s": sustained_start(rows, "red_ratio", args.red_threshold, fps, after=5.0),
        "peak_white_after_5s": local_max_time(rows, "white_ratio", after=5.0, before=45.0),
        "peak_red_after_5s": local_max_time(rows, "red_ratio", after=5.0, before=45.0),
        "peak_motion_after_5s": local_max_time(rows, "motion", after=5.0, before=45.0),
    }
    white_start = events["first_sustained_white_after_5s"]
    red_start = events["first_sustained_red_after_5s"]
    if white_start is not None and red_start is not None:
        events["white_to_red_seconds"] = round(red_start - white_start, 3)

    samples = [row for row in rows if 5.0 <= row["t"] <= 45.0 and row["frame"] % int(round(fps)) == 0]
    return {
        "video": str(video),
        "fps": fps,
        "frames": len(rows),
        "duration_seconds": round(len(rows) / fps, 3),
        "scale": [args.scale_width, args.scale_height],
        "thresholds": {
            "white": args.white_threshold,
            "red": args.red_threshold,
            "bright": args.bright_threshold,
        },
        "events": events,
        "one_second_samples_5_to_45": samples,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("videos", nargs="+", type=Path)
    parser.add_argument("--ffmpeg", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--fps", type=float, default=29.97)
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--scale-width", type=int, default=180)
    parser.add_argument("--scale-height", type=int, default=120)
    parser.add_argument("--white-threshold", type=float, default=0.035)
    parser.add_argument("--red-threshold", type=float, default=0.035)
    parser.add_argument("--bright-threshold", type=float, default=0.05)
    args = parser.parse_args()
    result = [analyze(args, video) for video in args.videos]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
