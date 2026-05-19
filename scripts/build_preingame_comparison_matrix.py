#!/usr/bin/env python3
import argparse
import json
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load_font(size, bold=False):
    names = (
        "arialbd.ttf",
        "arial.ttf",
        "consolab.ttf",
        "consola.ttf",
    ) if bold else (
        "arial.ttf",
        "consola.ttf",
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def timestamp(seconds):
    seconds = int(round(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def extract_frame(ffmpeg, video, seconds, out_png):
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
        raise RuntimeError(f"ffmpeg failed for {video} @ {seconds}: {result.stderr}")
    return out_png


def normalize_image(src, out_png, force_display_4x3=False):
    out_png.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(src).convert("RGB")
    if force_display_4x3:
        image = image.resize((720, 540), Image.Resampling.LANCZOS)
    elif image.size == (720, 480):
        image = image.resize((720, 540), Image.Resampling.LANCZOS)
    image.save(out_png)
    return out_png


def make_placeholder(text, size=(720, 540)):
    image = Image.new("RGB", size, (28, 28, 28))
    draw = ImageDraw.Draw(image)
    font = load_font(26, bold=True)
    small = load_font(19)
    y = 200
    for i, line in enumerate(textwrap.wrap(text, 34)):
        draw.text((36, y + i * 30), line, fill=(230, 230, 230), font=font if i == 0 else small)
    return image


def draw_wrapped(draw, xy, text, font, fill, width, line_height):
    x, y = xy
    for line in text.splitlines():
        wrapped = textwrap.wrap(line, width=width) or [""]
        for part in wrapped:
            draw.text((x, y), part, font=font, fill=fill)
            y += line_height
    return y


def fit_image(image, box):
    max_w, max_h = box
    copy = image.copy()
    copy.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    return copy


def make_cell(title, image, note, width, image_height):
    title_h = 30
    note_h = 82
    cell = Image.new("RGB", (width, title_h + image_height + note_h), (16, 16, 16))
    draw = ImageDraw.Draw(cell)
    title_font = load_font(17, bold=True)
    note_font = load_font(14)
    draw.rectangle([0, 0, width, title_h], fill=(0, 0, 0))
    draw.text((8, 6), title, fill=(245, 245, 245), font=title_font)
    framed = fit_image(image, (width - 12, image_height - 8))
    cell.paste(framed, ((width - framed.width) // 2, title_h + 4 + ((image_height - 8 - framed.height) // 2)))
    draw_wrapped(draw, (8, title_h + image_height + 8), note, note_font, (220, 220, 220), 47, 17)
    return cell


def build_matrix(rows, out_image):
    label_w = 210
    cell_w = 390
    image_h = 292
    cell_h = 30 + image_h + 82
    header_h = 82
    gutter = 8
    cols = ["GE480i target", "Stock TND64", "Current g1mtabge3"]
    width = label_w + len(cols) * cell_w + (len(cols) + 1) * gutter
    height = header_h + len(rows) * (cell_h + gutter) + gutter
    sheet = Image.new("RGB", (width, height), (34, 34, 34))
    draw = ImageDraw.Draw(sheet)
    header_font = load_font(21, bold=True)
    label_font = load_font(18, bold=True)
    small_font = load_font(14)
    draw.text((12, 14), "TND6480i Pre-Ingame Comparison Matrix", fill=(250, 250, 250), font=header_font)
    x = label_w + gutter
    for col in cols:
        draw.text((x + 8, 48), col, fill=(250, 250, 250), font=header_font)
        x += cell_w + gutter
    y = header_h
    for row in rows:
        draw.rectangle([0, y, label_w, y + cell_h], fill=(22, 22, 22))
        draw_wrapped(draw, (12, y + 16), row["screen"], label_font, (255, 255, 255), 17, 23)
        draw_wrapped(draw, (12, y + 96), row["finding"], small_font, row.get("finding_fill", (255, 210, 135)), 24, 17)
        x = label_w + gutter
        for key in ("ge", "stock", "current"):
            source = row[key]
            image = source["image"]
            cell = make_cell(source["title"], image, source["note"], cell_w, image_h)
            sheet.paste(cell, (x, y))
            x += cell_w + gutter
        y += cell_h + gutter
    out_image.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_image, quality=92)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-image", required=True, type=Path)
    parser.add_argument("--out-report", required=True, type=Path)
    parser.add_argument("--work-dir", default=Path("diagnostics/captures/current/preingame_matrix_frames"), type=Path)
    parser.add_argument("--ffmpeg", default=Path("ffmpeg"), type=Path)
    args = parser.parse_args()

    clip_dir = Path(r"C:\Users\codex\Documents\Light Capture ˜^‰æƒtƒHƒ‹ƒ_\n64")
    ge480i = clip_dir / "2. GoldenEye 480i.mpg"
    stock_tnd = clip_dir / "3. Tomorrow Never DIes 64.mpg"
    current_start = Path("diagnostics/captures/videos/g1mtabge3_full_front_130s_hardware_20260518.mp4")
    current_file = Path("diagnostics/captures/videos/g1tabauto05_file_hardware_20260518.mp4")
    current_mode = Path("diagnostics/captures/videos/g1tabauto06_mode_hardware_20260518.mp4")
    current_mission = Path("diagnostics/captures/videos/g1mtabge3auto07_mission_hardware_20260518.mp4")
    current_difficulty_probe = Path("diagnostics/captures/videos/g1tabauto08_difficulty_hardware_20260518.mp4")
    current_briefing_probe = Path("diagnostics/captures/videos/g1tabauto0a_briefing_hardware_20260518.mp4")

    ge_snaps = {
        "classification": Path(r"C:\Users\codex\Pictures\vlcsnap-2026-05-18-18h14m11s759.png"),
        "file": Path(r"C:\Users\codex\Pictures\vlcsnap-2026-05-18-18h14m25s727.png"),
        "mode": Path(r"C:\Users\codex\Pictures\vlcsnap-2026-05-18-18h14m38s302.png"),
        "mission": Path(r"C:\Users\codex\Pictures\vlcsnap-2026-05-18-18h14m57s301.png"),
        "difficulty": Path(r"C:\Users\codex\Pictures\vlcsnap-2026-05-18-18h15m03s394.png"),
        "briefing": Path(r"C:\Users\codex\Pictures\vlcsnap-2026-05-18-18h15m20s302.png"),
        "objectives": Path(r"C:\Users\codex\Pictures\vlcsnap-2026-05-18-18h15m43s930.png"),
    }

    def still(name, src, force=False):
        out = args.work_dir / f"{name}.png"
        return Image.open(normalize_image(src, out, force_display_4x3=force)).convert("RGB")

    def frame(name, video, seconds):
        raw = args.work_dir / "raw" / f"{name}.png"
        extract_frame(args.ffmpeg, video, seconds, raw)
        return still(name, raw, force=True)

    def blank(text):
        return make_placeholder(text)

    rows = [
        {
            "screen": "Classification / CMK board",
            "finding": "Needs explicit validation. Current capture appears delayed/looped; earlier user note said it runs off right.",
            "ge": {"title": "GE480i snapshot", "image": still("ge_classification", ge_snaps["classification"]), "note": "Reference for high-res legal text scale."},
            "stock": {"title": "Stock TND64 02:20", "image": frame("stock_cmk_140s", stock_tnd, 140), "note": "TND-specific screen; should preserve content bounds."},
            "current": {"title": "Current 01:30", "image": frame("current_cmk_90s", current_start, 90), "note": "Captured during loop, not yet a clean pass/fail frame."},
        },
        {
            "screen": "TiJayFly logo",
            "finding": "TND-only asset. Use stock TND for position/pacing; 480i should not introduce crop.",
            "ge": {"title": "GE480i n/a", "image": blank("No GE equivalent"), "note": "No matching GE screen."},
            "stock": {"title": "Stock TND64 00:05", "image": frame("stock_tijay_5s", stock_tnd, 5), "note": "Original logo timing and bounds."},
            "current": {"title": "Current 00:15", "image": frame("current_tijay_15s", current_start, 15), "note": "Visible, delayed versus stock/reference startup cadence."},
        },
        {
            "screen": "Rare logo",
            "finding": "Comparable screen. Check scale/centering and intro cadence against GE480i/stock.",
            "ge": {"title": "GE480i 00:15", "image": frame("ge_rare_15s", ge480i, 15), "note": "Target 480i logo presentation."},
            "stock": {"title": "Stock TND64 00:15", "image": frame("stock_rare_15s", stock_tnd, 15), "note": "Original TND cadence."},
            "current": {"title": "Current 00:25", "image": frame("current_rare_25s", current_start, 25), "note": "Visible; cadence is slower than stock TND."},
        },
        {
            "screen": "White circle / barrel entry",
            "finding": "Fail. Current has doubled/incorrect circle structure instead of the normal sweep.",
            "ge": {"title": "GE480i 00:20", "image": frame("ge_circle_20s", ge480i, 20), "note": "Normal 480i circle/barrel entry."},
            "stock": {"title": "Stock TND64 00:20", "image": frame("stock_circle_20s", stock_tnd, 20), "note": "Normal TND circle entry."},
            "current": {"title": "Current 00:30", "image": frame("current_circle_30s", current_start, 30), "note": "Wrong geometry; user described this as swiss-cheese/double-barrel behavior."},
        },
        {
            "screen": "Gunbarrel, Bond visible",
            "finding": "Fail. Bond/barrel cadence and apparent viewport do not match GE480i or stock TND.",
            "ge": {"title": "GE480i 00:30", "image": frame("ge_bond_30s", ge480i, 30), "note": "Bond remains synced with barrel travel."},
            "stock": {"title": "Stock TND64 00:30", "image": frame("stock_bond_30s", stock_tnd, 30), "note": "Stock TND sync/position reference."},
            "current": {"title": "Current 00:40", "image": frame("current_bond_40s", current_start, 40), "note": "Bond appears at wrong phase relative to the moving barrel."},
        },
        {
            "screen": "Gunbarrel red wipe",
            "finding": "Fail. Current phase/shape differs; keep this out of the gameplay-success path.",
            "ge": {"title": "GE480i 00:40", "image": frame("ge_red_40s", ge480i, 40), "note": "Target high-res red wipe shape."},
            "stock": {"title": "Stock TND64 00:35", "image": frame("stock_red_35s", stock_tnd, 35), "note": "Original red wipe timing."},
            "current": {"title": "Current 00:45", "image": frame("current_red_45s", current_start, 45), "note": "Still not a visual/timing match."},
        },
        {
            "screen": "Title logo",
            "finding": "Needs fix/measurement. Current title does not yet read like GE480i-style high-res presentation.",
            "ge": {"title": "GE480i title 00:50", "image": frame("ge_title_50s", ge480i, 50), "note": "Reference for sharp centered title treatment."},
            "stock": {"title": "Stock TND64 00:40", "image": frame("stock_title_40s", stock_tnd, 40), "note": "TND title asset/placement reference."},
            "current": {"title": "Current 00:55", "image": frame("current_title_55s", current_start, 55), "note": "Needs pixel-bound comparison before patching."},
        },
        {
            "screen": "Opening credits",
            "finding": "Verified fail. Character presentation is cropped/zoomed into heads or upper fragments versus GE480i/stock TND.",
            "ge": {"title": "GE480i credits 00:55", "image": frame("ge_credits_55s", ge480i, 55), "note": "Reference text scale and margins."},
            "stock": {"title": "Stock TND64 00:45", "image": frame("stock_credits_45s", stock_tnd, 45), "note": "Original TND credit placement."},
            "current": {"title": "Current 01:05", "image": frame("current_credits_65s", current_start, 65), "note": "Character crop/scale is wrong; also needs text-bound measurement."},
        },
        {
            "screen": "File select dossier",
            "finding": "Mostly close, but current wallpaper/background appears shifted left versus GE480i target.",
            "ge": {"title": "GE480i snapshot", "image": still("ge_file_select", ge_snaps["file"]), "note": "Target file icons/text/background relationship."},
            "stock": {"title": "Stock TND64 n/a", "image": blank("No clean stock menu capture in this set"), "note": "Can capture later if needed."},
            "current": {"title": "Current route 01:00", "image": frame("current_file_60s", current_file, 60), "note": "Text/icons close; red wallpaper starts too far left."},
        },
        {
            "screen": "Bond dossier / mode select",
            "finding": "Improved. Visual layout is now close; remaining issue is interactive hitbox/tab placement, not obvious in a still.",
            "ge": {"title": "GE480i snapshot", "image": still("ge_mode_select", ge_snaps["mode"]), "note": "Target for Bond photo/text/tab geometry."},
            "stock": {"title": "Stock TND64 n/a", "image": blank("No clean stock menu capture in this set"), "note": "TND uses red folders and different photo."},
            "current": {"title": "Current route 01:00", "image": frame("current_mode_60s", current_mode, 60), "note": "Photo/text visually close; verify tab/cursor hit targets separately."},
        },
        {
            "screen": "Mission select",
            "finding": "Fail. Mission label text still overflows/misaligns instead of sitting on the film strip like GE480i.",
            "ge": {"title": "GE480i snapshot", "image": still("ge_mission_select", ge_snaps["mission"]), "note": "Target label placement over photos/film."},
            "stock": {"title": "Stock TND64 n/a", "image": blank("No clean stock menu capture in this set"), "note": "Need TND-specific mission count only; layout should match GE480i style."},
            "current": {"title": "Current route 01:00", "image": frame("current_mission_60s", current_mission, 60), "note": "Labels run right/vertical alignment is off."},
        },
        {
            "screen": "Difficulty select",
            "finding": "Unknown current. Route probe currently lands on mode page, so no valid current difficulty frame yet.",
            "ge": {"title": "GE480i snapshot", "image": still("ge_difficulty", ge_snaps["difficulty"]), "note": "Target menu scale and text placement."},
            "stock": {"title": "Stock TND64 n/a", "image": blank("No clean stock difficulty capture"), "note": "Requires driven menu path or better state injection."},
            "current": {"title": "Current probe result", "image": frame("current_difficulty_probe_15s", current_difficulty_probe, 15), "note": "Probe failed semantically: shows mode page, not difficulty."},
        },
        {
            "screen": "Briefing / objectives",
            "finding": "Unknown current. Route probe currently lands on mode page, so no valid current briefing frame yet.",
            "ge": {"title": "GE480i snapshot", "image": still("ge_briefing", ge_snaps["briefing"]), "note": "Target briefing text scale."},
            "stock": {"title": "GE480i obj ref", "image": still("ge_objectives", ge_snaps["objectives"]), "note": "Extra GE480i reference for photo/objective page."},
            "current": {"title": "Current probe result", "image": frame("current_briefing_probe_15s", current_briefing_probe, 15), "note": "Probe failed semantically: shows mode page, not briefing."},
        },
    ]

    build_matrix(rows, args.out_image)
    report = {
        "output_image": str(args.out_image),
        "current_candidate": "artifacts/generated/g1mtabge3.z64",
        "notes": [
            "GV-USB2 frames were normalized from 720x480 capture to 720x540 display aspect for comparison.",
            "Difficulty and briefing current route probes do not reach the intended pages; they land on the Bond/mode dossier page.",
            "No ROM patching is performed by this script.",
        ],
        "rows": [
            {
                "screen": row["screen"],
                "finding": row["finding"],
                "ge": row["ge"]["title"],
                "stock": row["stock"]["title"],
                "current": row["current"]["title"],
            }
            for row in rows
        ],
    }
    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    args.out_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"image": str(args.out_image), "report": str(args.out_report), "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
