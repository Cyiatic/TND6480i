#!/usr/bin/env python3
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "diagnostics" / "captures" / "current" / "g1hbrf1_remaining_issue_analysis_20260519.jpg"
REPORT = ROOT / "reports" / "g1hbrf1_remaining_issue_analysis_20260519.json"
TARGET = (720, 540)
CARD_W = 1510
CARD_H = 780

COLORS = {
    "white": (245, 245, 245),
    "gray": (160, 160, 160),
    "green": (35, 235, 85),
    "cyan": (30, 220, 255),
    "yellow": (255, 210, 30),
    "orange": (255, 150, 35),
    "red": (255, 70, 70),
}


def font(size):
    for name in ("consola.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


FONT_TITLE = font(22)
FONT_LABEL = font(15)
FONT_NOTE = font(16)
FONT_SMALL = font(13)


def image(path):
    img = Image.open(path).convert("RGB")
    if img.size != TARGET:
        img = img.resize(TARGET, Image.Resampling.LANCZOS)
    return img


def draw_box(draw, box, color, label=None, width=3):
    x1, y1, x2, y2 = box
    for inset in range(width):
        draw.rectangle((x1 + inset, y1 + inset, x2 - inset, y2 - inset), outline=COLORS[color])
    if label:
        y = y1 - 18 if y1 >= 52 else y2 + 4
        draw.text((x1 + 4, y), label, fill=COLORS[color], font=FONT_SMALL)


def draw_line(draw, line, color, label=None):
    x1, y1, x2, y2 = line
    draw.line((x1, y1, x2, y2), fill=COLORS[color], width=3)
    if label:
        draw.text((min(x1, x2) + 4, max(34, min(y1, y2) - 18)), label, fill=COLORS[color], font=FONT_SMALL)


def panel(path, label):
    img = image(path)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, TARGET[0], 28), fill=(0, 0, 0))
    draw.text((8, 5), label, fill=COLORS["white"], font=FONT_SMALL)
    return img


def wrap(draw, text, width):
    words = text.split()
    lines = []
    line = ""
    for word in words:
        candidate = word if not line else f"{line} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=FONT_NOTE)
        if bbox[2] - bbox[0] <= width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def make_card(spec):
    left = panel(spec["reference"], spec["reference_label"])
    right = panel(spec["current"], spec["current_label"])
    ldraw = ImageDraw.Draw(left)
    rdraw = ImageDraw.Draw(right)
    for item in spec["reference_boxes"]:
        draw_box(ldraw, item["box"], item["color"], item.get("label"))
    for item in spec.get("reference_lines", []):
        draw_line(ldraw, item["line"], item["color"], item.get("label"))
    for item in spec["current_boxes"]:
        draw_box(rdraw, item["box"], item["color"], item.get("label"))
    for item in spec.get("current_lines", []):
        draw_line(rdraw, item["line"], item["color"], item.get("label"))

    card = Image.new("RGB", (CARD_W, CARD_H), (18, 18, 18))
    draw = ImageDraw.Draw(card)
    draw.text((12, 10), spec["title"], fill=COLORS["white"], font=FONT_TITLE)
    draw.text((12, 38), spec["status"], fill=COLORS["yellow"], font=FONT_LABEL)
    card.paste(left, (12, 76))
    card.paste(right, (778, 76))
    draw.rectangle((742, 76, 768, 616), fill=(30, 30, 30))

    y = 624
    for lead, color, text in (
        ("Mismatch: ", "red", spec["mismatch"]),
        ("Patch target: ", "cyan", spec["target"]),
        ("Proceed: ", "yellow", spec["proceed"]),
    ):
        draw.text((12, y), lead, fill=COLORS[color], font=FONT_NOTE)
        prefix = draw.textbbox((0, 0), lead, font=FONT_NOTE)[2]
        lines = wrap(draw, text, CARD_W - prefix - 28)
        for idx, line in enumerate(lines[:3]):
            draw.text((12 + prefix if idx == 0 else 12, y + idx * 19), line, fill=COLORS["white"], font=FONT_NOTE)
        y += max(1, min(3, len(lines))) * 19 + 3
    return card


def main():
    specs = [
        {
            "title": "01 File Select: Folder Gunbarrel Background",
            "status": "ISSUE: TND file-select backdrop/folder envelope is stretched wider than the GE480i family",
            "reference_label": "GE480i reference, aspect-normalized",
            "current_label": "Current g1hbrf1 route, aspect-normalized",
            "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h14m25s727.png",
            "current": str(ROOT / "diagnostics" / "captures" / "contact_sheets" / "brfauto05_hardware_cycled_20260519" / "frames" / "frame_0002_00061000.png"),
            "reference_boxes": [
                {"box": [55, 67, 655, 510], "color": "green", "label": "GE folder/backdrop envelope"},
                {"box": [0, 60, 720, 505], "color": "cyan", "label": "gunbarrel backdrop fills but stays soft"},
                {"box": [640, 76, 665, 505], "color": "yellow", "label": "right edge target"},
                {"box": [105, 418, 610, 486], "color": "green", "label": "bottom labels/icons stable band"},
            ],
            "current_boxes": [
                {"box": [52, 61, 691, 509], "color": "red", "label": "current folder group too wide/right"},
                {"box": [662, 78, 718, 511], "color": "orange", "label": "right-edge bleed/stretch"},
                {"box": [0, 64, 720, 504], "color": "cyan", "label": "gunbarrel backdrop visibly stretched"},
                {"box": [108, 424, 610, 486], "color": "green", "label": "labels/icons mostly correct"},
            ],
            "mismatch": "Save folders and icon labels are readable, but the shared dark gunbarrel backdrop/folder envelope runs farther right than GE480i and looks horizontally stretched.",
            "target": "Keep the folder sprites and labels; fix the file-select backdrop/envelope source or destination width/origin so the right edge lands like the GE480i file-select page.",
            "proceed": "Audit the MENU_FILE_SELECT backdrop blitter and any file-select folder-envelope constants before changing unrelated dossier text rows.",
        },
        {
            "title": "02 Briefing Background: NEXT Tab Label",
            "status": "ISSUE: cursor/hitbox is on the right tab, but the NEXT label is drawn inside the page",
            "reference_label": "GE480i background reference, aspect-normalized",
            "current_label": "Current g1hbrf1 background route, aspect-normalized",
            "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h15m11s715.png",
            "current": str(ROOT / "diagnostics" / "captures" / "contact_sheets" / "brfbtn0cpg1_hardware_cycled_20260519" / "frames" / "frame_0002_00061000.png"),
            "reference_boxes": [
                {"box": [62, 54, 628, 523], "color": "green", "label": "paper bounds"},
                {"box": [635, 226, 665, 348], "color": "cyan", "label": "NEXT on tab"},
                {"box": [628, 214, 670, 260], "color": "green", "label": "cursor shares tab target"},
                {"box": [634, 366, 668, 506], "color": "yellow", "label": "PREVIOUS on tab"},
            ],
            "current_boxes": [
                {"box": [62, 54, 664, 523], "color": "green", "label": "paper bounds OK"},
                {"box": [432, 160, 461, 232], "color": "red", "label": "NEXT printed inside page"},
                {"box": [635, 188, 670, 329], "color": "cyan", "label": "actual tab target area"},
                {"box": [628, 210, 670, 256], "color": "green", "label": "cursor/hitbox is right"},
                {"box": [635, 372, 670, 514], "color": "yellow", "label": "PREVIOUS on tab"},
            ],
            "current_lines": [
                {"line": [461, 196, 638, 232], "color": "red", "label": "move label to tab"},
            ],
            "mismatch": "The page geometry and cursor target are good, but the NEXT label X position is using an interior-page coordinate while START and PREVIOUS are on the tab stack.",
            "target": "Patch only the briefing tab-label coordinate for NEXT so the printed text lands on the right-side middle tab, matching GE480i.",
            "proceed": "Search the MENU_BRIEFING/tab-label draw constants near the briefing constructor; avoid touching briefing text wrapping, which now looks correct.",
        },
    ]

    cards = [make_card(spec) for spec in specs]
    atlas = Image.new("RGB", (CARD_W, CARD_H * len(cards)), (20, 20, 20))
    for index, card in enumerate(cards):
        atlas.paste(card, (0, index * CARD_H))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(OUT, quality=92)
    REPORT.write_text(json.dumps({"out": str(OUT), "cards": specs}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "report": str(REPORT), "cards": len(cards)}, indent=2))


if __name__ == "__main__":
    main()
