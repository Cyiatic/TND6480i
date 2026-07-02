#!/usr/bin/env python3
"""Measure 480i/text-quality evidence from GV-USB2 captures.

This is not a perceptual oracle.  It is a regression gate.  The intended use is
to compare a candidate against known hardware references captured through the
same GV-USB2/S-Video path:

  * stock GE/TND: expected low-resolution or non-480i controls
  * GE480i enhanced: expected 480i/text-sharpness reference
  * TND6480i candidate: must move toward GE480i, not merely "look okay"

Metrics are intentionally simple and auditable:

  * line_pair_mad: odd/even adjacent-line difference.  Line-doubled 240p-like
    output tends to be lower; real 480i/high-detail output tends to be higher.
  * vertical_nyquist_ratio: energy at alternating-line frequency divided by
    total vertical energy.  This catches interlaced/high-resolution line detail.
  * laplacian_var: edge/detail energy, useful for text sharpness in matched
    crops.
  * edge_density: fraction of strong local gradients.
  * temporal_mad: mean frame-to-frame luma difference in a sampled segment.

The script can read still images, directories of frames, or video files.  For
videos it asks ffmpeg for evenly-spaced sample frames from a timestamp window.
"""

import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


DEFAULT_CROPS = {
    "full_active": [0, 0, 720, 480],
    "center_ui": [120, 70, 600, 410],
    "upper_text": [100, 40, 620, 170],
    "lower_text": [100, 300, 620, 455],
}


def parse_label_path(text):
    if "=" not in text:
        path = Path(text)
        return path.stem, path
    label, path = text.split("=", 1)
    return label, Path(path)


def parse_crop(text):
    name, coords = text.split("=", 1)
    values = [int(part) for part in coords.split(",")]
    if len(values) != 4:
        raise ValueError(f"crop needs x1,y1,x2,y2: {text}")
    return name, values


def load_luma(path):
    img = Image.open(path).convert("L")
    return np.asarray(img, dtype=np.float32)


def save_frame_sheet(samples, crops, out_path):
    thumbs = []
    font = ImageFont.load_default()
    for label, frame_path in samples:
        img = Image.open(frame_path).convert("RGB")
        for crop_name, box in crops.items():
            crop = img.crop(tuple(box))
            crop.thumbnail((300, 200))
            tile = Image.new("RGB", (320, 240), "black")
            tile.paste(crop, ((320 - crop.width) // 2, 28))
            draw = ImageDraw.Draw(tile)
            draw.text((8, 6), f"{label} / {crop_name}", fill=(255, 255, 255), font=font)
            thumbs.append(tile)
    if not thumbs:
        return
    cols = min(3, len(thumbs))
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * 320, rows * 240), "black")
    for idx, tile in enumerate(thumbs):
        sheet.paste(tile, ((idx % cols) * 320, (idx // cols) * 240))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def ffmpeg_extract(video, out_dir, start, duration, samples, ffmpeg="ffmpeg"):
    out_dir.mkdir(parents=True, exist_ok=True)
    if samples <= 1:
        times = [start]
    else:
        span = max(0.0, duration)
        times = [start + (span * i / (samples - 1)) for i in range(samples)]
    paths = []
    for idx, ts in enumerate(times):
        out_path = out_dir / f"frame_{idx:03d}_{ts:.3f}.png"
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{ts:.3f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                str(out_path),
            ],
            check=True,
        )
        paths.append(out_path)
    return paths


def collect_frames(label, path, work_dir, start, duration, samples, ffmpeg):
    suffix = path.suffix.lower()
    if path.is_dir():
        images = sorted(
            p for p in path.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}
        )
        frame_like = [p for p in images if p.stem.lower().startswith("frame_")]
        frames = frame_like or images
    elif suffix in {".png", ".jpg", ".jpeg", ".bmp"}:
        frames = [path]
    else:
        frames = ffmpeg_extract(path, work_dir / label, start, duration, samples, ffmpeg)
    if not frames:
        raise ValueError(f"no frames for {label}: {path}")
    return frames


def crop_array(arr, box):
    x1, y1, x2, y2 = box
    return arr[y1:y2, x1:x2]


def metrics_for_frames(frames, crop_box):
    arrays = [crop_array(load_luma(path), crop_box) for path in frames]
    stack = np.stack(arrays, axis=0)
    avg = stack.mean(axis=0)

    if avg.shape[0] >= 2:
        pair_count = min(avg[0::2, :].shape[0], avg[1::2, :].shape[0])
        line_pair_mad = float(np.mean(np.abs(avg[0 : pair_count * 2 : 2, :] - avg[1 : pair_count * 2 : 2, :])))
    else:
        line_pair_mad = 0.0

    centered = avg - avg.mean(axis=0, keepdims=True)
    fft = np.fft.rfft(centered, axis=0)
    power = np.abs(fft) ** 2
    total_power = float(power[1:, :].sum()) if power.shape[0] > 1 else 0.0
    nyquist_power = float(power[-1, :].sum()) if power.shape[0] > 1 else 0.0
    vertical_nyquist_ratio = nyquist_power / total_power if total_power else 0.0

    gx = np.zeros_like(avg)
    gy = np.zeros_like(avg)
    gx[:, 1:-1] = avg[:, 2:] - avg[:, :-2]
    gy[1:-1, :] = avg[2:, :] - avg[:-2, :]
    grad = np.sqrt(gx * gx + gy * gy)
    edge_density = float(np.mean(grad > max(12.0, np.percentile(grad, 90))))

    lap = np.zeros_like(avg)
    lap[1:-1, 1:-1] = (
        -4.0 * avg[1:-1, 1:-1]
        + avg[:-2, 1:-1]
        + avg[2:, 1:-1]
        + avg[1:-1, :-2]
        + avg[1:-1, 2:]
    )
    laplacian_var = float(np.var(lap))

    if len(arrays) > 1:
        temporal_mad = float(np.mean([np.mean(np.abs(arrays[i + 1] - arrays[i])) for i in range(len(arrays) - 1)]))
    else:
        temporal_mad = 0.0

    return {
        "frames": len(frames),
        "mean_luma": float(avg.mean()),
        "std_luma": float(avg.std()),
        "line_pair_mad": line_pair_mad,
        "vertical_nyquist_ratio": vertical_nyquist_ratio,
        "laplacian_var": laplacian_var,
        "edge_density": edge_density,
        "temporal_mad": temporal_mad,
    }


def ratio(value, ref):
    return value / ref if ref else None


def main():
    parser = argparse.ArgumentParser(description="Measure 480i/text-quality metrics from GV-USB2 captures.")
    parser.add_argument("--sample", action="append", required=True, help="LABEL=path to image, frame dir, or video")
    parser.add_argument("--reference-label", default=None, help="Label to use for ratio comparisons, typically GE480i")
    parser.add_argument("--crop", action="append", default=[], help="NAME=x1,y1,x2,y2")
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--frames", type=int, default=9)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-sheet")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()

    crops = dict(DEFAULT_CROPS)
    for crop in args.crop:
        name, box = parse_crop(crop)
        crops[name] = box

    out_json = Path(args.out_json)
    work_dir = out_json.parent / f"{out_json.stem}_frames"
    work_dir.mkdir(parents=True, exist_ok=True)

    samples = []
    frame_lookup = {}
    for sample_text in args.sample:
        label, path = parse_label_path(sample_text)
        frames = collect_frames(label, path, work_dir, args.start, args.duration, args.frames, args.ffmpeg)
        samples.append({"label": label, "path": str(path), "frames": [str(p) for p in frames]})
        frame_lookup[label] = frames

    results = {"samples": samples, "crops": crops, "metrics": {}, "ratios_to_reference": {}}
    for sample in samples:
        label = sample["label"]
        results["metrics"][label] = {}
        for crop_name, box in crops.items():
            results["metrics"][label][crop_name] = metrics_for_frames(frame_lookup[label], box)

    ref = args.reference_label
    if ref and ref in results["metrics"]:
        for label, by_crop in results["metrics"].items():
            if label == ref:
                continue
            results["ratios_to_reference"][label] = {}
            for crop_name, metrics in by_crop.items():
                ref_metrics = results["metrics"][ref][crop_name]
                results["ratios_to_reference"][label][crop_name] = {
                    key: ratio(metrics[key], ref_metrics[key])
                    for key in ("line_pair_mad", "vertical_nyquist_ratio", "laplacian_var", "edge_density")
                }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    if args.out_sheet:
        first_frames = [(sample["label"], Path(sample["frames"][0])) for sample in samples]
        save_frame_sheet(first_frames, crops, Path(args.out_sheet))

    print(json.dumps({
        "out_json": str(out_json),
        "out_sheet": args.out_sheet,
        "labels": [sample["label"] for sample in samples],
        "crops": list(crops),
    }, indent=2))


if __name__ == "__main__":
    main()
