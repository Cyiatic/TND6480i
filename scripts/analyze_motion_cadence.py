#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path


def read_gray_frames(video, ffmpeg, start, duration, width, height):
    cmd = [
        ffmpeg,
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
        f"fps=29.97,scale={width}:{height},format=gray",
        "-f",
        "rawvideo",
        "-",
    ]
    proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE)
    frame_size = width * height
    data = proc.stdout
    return [memoryview(data)[i:i + frame_size] for i in range(0, len(data) - frame_size + 1, frame_size)]


def mean_abs_diff(a, b):
    total = 0
    for x, y in zip(a, b):
        total += abs(x - y)
    return total / len(a)


def summarize_diffs(diffs):
    if not diffs:
        return {
            "frames": 0,
            "mean_diff": 0.0,
            "median_diff": 0.0,
            "p90_diff": 0.0,
            "near_duplicate_ratio": 0.0,
            "active_ratio": 0.0,
            "estimated_updates_per_second": 0.0,
        }
    ordered = sorted(diffs)
    n = len(ordered)
    median = ordered[n // 2]
    p90 = ordered[min(n - 1, int(n * 0.90))]
    near_duplicate = sum(1 for x in diffs if x < 0.8)
    active = sum(1 for x in diffs if x >= 1.8)
    return {
        "frames": n + 1,
        "frame_diffs": n,
        "mean_diff": round(sum(diffs) / n, 4),
        "median_diff": round(median, 4),
        "p90_diff": round(p90, 4),
        "near_duplicate_ratio": round(near_duplicate / n, 4),
        "active_ratio": round(active / n, 4),
        "estimated_updates_per_second": round(active * 29.97 / n, 3),
    }


def analyze_segment(video, ffmpeg, segment, width, height):
    frames = read_gray_frames(video, ffmpeg, segment["start"], segment["duration"], width, height)
    diffs = [mean_abs_diff(frames[i - 1], frames[i]) for i in range(1, len(frames))]
    summary = summarize_diffs(diffs)
    summary.update({
        "label": segment["label"],
        "start": segment["start"],
        "duration": segment["duration"],
        "scale": [width, height],
    })
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--width", type=int, default=180)
    parser.add_argument("--height", type=int, default=120)
    parser.add_argument(
        "--segment",
        action="append",
        nargs=4,
        metavar=("LABEL", "VIDEO", "START", "DURATION"),
        required=True,
        help="Analyze one segment, e.g. --segment ge480 video.mkv 19.0 17.0",
    )
    args = parser.parse_args()

    reports = []
    for label, video, start, duration in args.segment:
        reports.append({
            "video": video,
            **analyze_segment(
                Path(video),
                args.ffmpeg,
                {"label": label, "start": float(start), "duration": float(duration)},
                args.width,
                args.height,
            ),
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(reports, indent=2) + "\n")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
