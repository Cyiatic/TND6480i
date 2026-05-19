#!/usr/bin/env python3
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = "g1casta1"
OUT_DIR = ROOT / "diagnostics" / "captures" / "current" / f"preingame_annotations_{CANDIDATE}_20260518"
REPORT = ROOT / "reports" / f"preingame_annotations_{CANDIDATE}_20260518.json"
ATLAS = ROOT / "diagnostics" / "captures" / "current" / f"preingame_annotations_{CANDIDATE}_20260518.jpg"

TARGET_SIZE = (720, 540)
CARD_WIDTH = 1510
CARD_HEIGHT = 660

COLORS = {
    "green": (40, 230, 80),
    "cyan": (40, 220, 255),
    "yellow": (255, 210, 30),
    "red": (255, 70, 70),
    "magenta": (255, 90, 210),
    "white": (245, 245, 245),
}


def font(size):
    for name in ("consola.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


FONT_TITLE = font(21)
FONT_LABEL = font(16)
FONT_SMALL = font(14)
FONT_NOTE = font(15)


def rel(path):
    return ROOT / path


def load_panel(path, label):
    panel = Image.new("RGB", TARGET_SIZE, (12, 12, 12))
    if not path:
        draw = ImageDraw.Draw(panel)
        draw.text((24, 240), "no safe capture yet", fill=COLORS["yellow"], font=FONT_TITLE)
        return panel
    image_path = Path(path)
    if not image_path.is_absolute():
        image_path = rel(path)
    image = Image.open(image_path).convert("RGB")
    image = image.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, TARGET_SIZE[0], 30), fill=(0, 0, 0))
    draw.text((8, 5), label, fill=COLORS["white"], font=FONT_SMALL)
    return image


def draw_box(draw, box, color_name, label):
    color = COLORS[color_name]
    x1, y1, x2, y2 = box
    for inset in range(2):
        draw.rectangle((x1 + inset, y1 + inset, x2 - inset, y2 - inset), outline=color)
    if label:
        draw.text((x1 + 4, max(32, y1 - 18)), label, fill=color, font=FONT_SMALL)


def wrap_text(draw, text, width):
    words = text.split()
    lines = []
    line = ""
    for word in words:
        test = word if not line else f"{line} {word}"
        bbox = draw.textbbox((0, 0), test, font=FONT_NOTE)
        if bbox[2] - bbox[0] <= width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def make_card(spec):
    left = load_panel(spec.get("reference"), spec["reference_label"])
    right = load_panel(spec.get("current"), spec["current_label"])
    draw_left = ImageDraw.Draw(left)
    draw_right = ImageDraw.Draw(right)

    for item in spec.get("reference_boxes", []):
        draw_box(draw_left, item["box"], item["color"], item["label"])
    for item in spec.get("current_boxes", []):
        draw_box(draw_right, item["box"], item["color"], item["label"])

    card = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), (18, 18, 18))
    draw = ImageDraw.Draw(card)
    draw.text((12, 10), spec["title"], fill=COLORS["white"], font=FONT_TITLE)
    draw.text((12, 38), spec["verdict"], fill=COLORS[spec.get("verdict_color", "yellow")], font=FONT_LABEL)
    card.paste(left, (12, 76))
    card.paste(right, (778, 76))
    draw.rectangle((742, 76, 768, 616), fill=(30, 30, 30))

    notes_x = 12
    notes_y = 620
    draw.text((notes_x, notes_y), "Fix note: ", fill=COLORS["cyan"], font=FONT_NOTE)
    prefix_w = draw.textbbox((0, 0), "Fix note: ", font=FONT_NOTE)[2]
    lines = wrap_text(draw, spec["note"], CARD_WIDTH - prefix_w - 28)
    for idx, line in enumerate(lines[:2]):
        draw.text((notes_x + prefix_w if idx == 0 else notes_x, notes_y + idx * 18), line, fill=COLORS["white"], font=FONT_NOTE)
    return card


def build_atlas(cards):
    thumb_w = 755
    thumb_h = 330
    cols = 2
    rows = math.ceil(len(cards) / cols)
    atlas = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (20, 20, 20))
    for index, card in enumerate(cards):
        thumb = card.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        atlas.paste(thumb, ((index % cols) * thumb_w, (index // cols) * thumb_h))
    return atlas


SPECS = [
    {
        "name": "01_classification",
        "title": "01 CMK Board Of Classification",
        "reference_label": "Stock TND64 reference",
        "current_label": "Current g1casta1 hardware capture",
        "reference": "diagnostics/captures/contact_sheets/stock_tnd_preingame_scan_20260518/frames/frame_0028_00140000.png",
        "current": "diagnostics/captures/contact_sheets/g1casta1_full_front_hardware_cycled_20260518/frames/frame_0002_00010000.png",
        "verdict": "Needs safe-area validation",
        "verdict_color": "yellow",
        "reference_boxes": [
            {"box": [110, 85, 615, 455], "color": "green", "label": "legal-screen safe area"},
        ],
        "current_boxes": [
            {"box": [265, 70, 520, 160], "color": "yellow", "label": "right text cluster"},
            {"box": [70, 385, 500, 430], "color": "cyan", "label": "bottom legal text"},
        ],
        "note": "The current page is readable but still needs a bounded safe-area check; do not spend patch work here until dossier and gunbarrel are settled.",
    },
    {
        "name": "02_tijayfly_logo",
        "title": "02 TiJayFly Logo",
        "reference_label": "Stock TND64 reference",
        "current_label": "Current g1casta1 hardware capture",
        "reference": "diagnostics/captures/contact_sheets/stock_tnd_preingame_scan_20260518/frames/frame_0001_00005000.png",
        "current": "diagnostics/captures/contact_sheets/g1casta1_full_front_hardware_cycled_20260518/frames/frame_0003_00015000.png",
        "verdict": "Low priority, visually usable",
        "verdict_color": "green",
        "reference_boxes": [
            {"box": [160, 210, 570, 292], "color": "green", "label": "logo band"},
        ],
        "current_boxes": [
            {"box": [170, 220, 560, 300], "color": "green", "label": "logo band"},
        ],
        "note": "Logo framing is not a current blocker; keep as a timing signal only unless later patches disturb it.",
    },
    {
        "name": "03_gunbarrel_entry",
        "title": "03 Gunbarrel Entry Sweep",
        "reference_label": "GE480i reference",
        "current_label": "Current g1casta1 hardware capture",
        "reference": "diagnostics/captures/contact_sheets/ge480i_gunbarrel_detail_20260518/frames/frame_0003_00022000.png",
        "current": "diagnostics/captures/contact_sheets/g1casta1_full_front_hardware_cycled_20260518/frames/frame_0006_00030000.png",
        "verdict": "Improved: paired circles now match the GE480i family",
        "verdict_color": "green",
        "reference_boxes": [
            {"box": [300, 250, 395, 310], "color": "green", "label": "paired aperture"},
        ],
        "current_boxes": [
            {"box": [300, 250, 395, 310], "color": "green", "label": "paired aperture"},
        ],
        "note": "The scaled 640x430 RLE asset fixes the early sweep family; cadence still needs a final human timing check.",
    },
    {
        "name": "04_gunbarrel_bond",
        "title": "04 Gunbarrel With Bond",
        "reference_label": "GE480i reference",
        "current_label": "Current g1casta1 hardware capture",
        "reference": "diagnostics/captures/contact_sheets/ge480i_gunbarrel_detail_20260518/frames/frame_0008_00032000.png",
        "current": "diagnostics/captures/contact_sheets/g1casta1_full_front_hardware_cycled_20260518/frames/frame_0008_00040000.png",
        "verdict": "Improved: offset aperture removed",
        "verdict_color": "green",
        "reference_boxes": [
            {"box": [315, 130, 650, 430], "color": "green", "label": "single centered barrel field"},
            {"box": [455, 245, 560, 390], "color": "cyan", "label": "Bond inside aperture"},
        ],
        "current_boxes": [
            {"box": [300, 130, 665, 430], "color": "green", "label": "single centered barrel field"},
            {"box": [455, 245, 560, 390], "color": "cyan", "label": "Bond inside aperture"},
        ],
        "note": "The large extra oval is gone in g1casta1; this should be checked on CRT for cadence, but visually it is now in the GE480i family.",
    },
    {
        "name": "05_title_logo",
        "title": "05 Tomorrow Never Dies Title Logo",
        "reference_label": "Stock TND64 reference",
        "current_label": "Current g1casta1 hardware capture",
        "reference": "diagnostics/captures/contact_sheets/stock_tnd_preingame_scan_20260518/frames/frame_0008_00040000.png",
        "current": "diagnostics/captures/contact_sheets/g1casta1_title_transition_20260518/frames/frame_0007_00057000.png",
        "verdict": "Visible and centered after gunbarrel asset transplant",
        "verdict_color": "green",
        "reference_boxes": [
            {"box": [300, 255, 500, 315], "color": "green", "label": "stock logo bounds"},
        ],
        "current_boxes": [
            {"box": [275, 255, 485, 315], "color": "yellow", "label": "current logo bounds"},
        ],
        "note": "The title logo remains present after the scaled asset transplant and no longer looks like a skipped transition.",
    },
    {
        "name": "06_opening_credits",
        "title": "06 Opening Credits / Cast Models",
        "reference_label": "Stock TND64 reference",
        "current_label": "Current g1casta1 hardware capture",
        "reference": "diagnostics/captures/contact_sheets/stock_tnd_preingame_scan_20260518/frames/frame_0010_00050000.png",
        "current": "diagnostics/captures/contact_sheets/g1casta1_full_front_hardware_cycled_20260518/frames/frame_0012_00060000.png",
        "verdict": "Improved by g1castz1, still verify text safe area",
        "verdict_color": "green",
        "reference_boxes": [
            {"box": [55, 160, 210, 430], "color": "green", "label": "full character"},
            {"box": [380, 220, 650, 300], "color": "cyan", "label": "credit text"},
        ],
        "current_boxes": [
            {"box": [70, 145, 250, 430], "color": "green", "label": "full character restored"},
            {"box": [360, 215, 660, 300], "color": "cyan", "label": "text readable"},
        ],
        "note": "The z-buffer dimension fix restored full bodies compared with the earlier cropped candidate; keep monitoring right-edge credit text.",
    },
    {
        "name": "07_file_select",
        "title": "07 File Select Dossier",
        "reference_label": "GE480i reference (VLC snap)",
        "current_label": "Current dossier path, inherited by g1casta1",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h14m25s727.png",
        "current": "diagnostics/captures/current/g1mtabge4_file_hw_norm_20260518.png",
        "verdict": "Mostly acceptable; background origin still a watch item",
        "verdict_color": "green",
        "reference_boxes": [
            {"box": [60, 70, 670, 510], "color": "green", "label": "folder group"},
            {"box": [245, 430, 545, 475], "color": "cyan", "label": "bottom labels/icons"},
        ],
        "current_boxes": [
            {"box": [65, 80, 675, 505], "color": "green", "label": "folder group"},
            {"box": [250, 430, 555, 475], "color": "cyan", "label": "labels/icons present"},
        ],
        "note": "This page no longer has missing labels/icons; only revisit if the wallpaper shift becomes obvious in live navigation.",
    },
    {
        "name": "08_mode_select",
        "title": "08 Single/Multiplayer/Cheats Dossier",
        "reference_label": "GE480i reference (VLC snap)",
        "current_label": "Current dossier path, inherited by g1casta1",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h14m38s302.png",
        "current": "diagnostics/captures/current/g1mtabge4_mode_hw_norm_20260518.png",
        "verdict": "Visually close; cursor route still needs live-input proof",
        "verdict_color": "green",
        "reference_boxes": [
            {"box": [185, 356, 404, 382], "color": "green", "label": "selected row"},
            {"box": [638, 384, 670, 510], "color": "cyan", "label": "PREVIOUS tab"},
        ],
        "current_boxes": [
            {"box": [240, 355, 405, 382], "color": "green", "label": "selected row"},
            {"box": [640, 385, 670, 510], "color": "cyan", "label": "PREVIOUS tab"},
        ],
        "note": "The earlier PREVIOUS-tab problem is fixed in this capture; normal-controller cursor/hitbox still needs one live confirmation.",
    },
    {
        "name": "09_mission_select",
        "title": "09 Mission Select Dossier",
        "reference_label": "GE480i reference (VLC snap)",
        "current_label": "Current dossier path, inherited by g1casta1",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h14m57s301.png",
        "current": "diagnostics/captures/current/g1mtabge4_mission_hw_norm_20260518.png",
        "verdict": "Needs another label-alignment pass",
        "verdict_color": "yellow",
        "reference_boxes": [
            {"box": [64, 70, 640, 420], "color": "green", "label": "filmstrip grid"},
            {"box": [65, 145, 640, 395], "color": "cyan", "label": "caption bands"},
        ],
        "current_boxes": [
            {"box": [63, 58, 640, 380], "color": "green", "label": "TND filmstrip grid"},
            {"box": [48, 142, 650, 402], "color": "yellow", "label": "mission labels still need centering"},
        ],
        "note": "Keep the TND mission count/layout, but align each label to the same film-caption band behavior as GE480i.",
    },
    {
        "name": "10_difficulty",
        "title": "10 Difficulty Dossier",
        "reference_label": "GE480i reference (VLC snap)",
        "current_label": "Current dossier path, inherited by g1casta1",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h15m03s394.png",
        "current": "diagnostics/captures/current/g1mtabge4_difficulty_hw_norm_20260518.png",
        "verdict": "Visually close; keep unless live input says otherwise",
        "verdict_color": "green",
        "reference_boxes": [
            {"box": [80, 70, 660, 510], "color": "green", "label": "paper bounds"},
            {"box": [95, 240, 285, 365], "color": "cyan", "label": "difficulty rows"},
        ],
        "current_boxes": [
            {"box": [62, 48, 668, 508], "color": "green", "label": "paper bounds"},
            {"box": [112, 200, 330, 322], "color": "cyan", "label": "difficulty rows"},
        ],
        "note": "The page is usable and high-res-looking; avoid broad changes here while mission labels and gunbarrel remain unresolved.",
    },
    {
        "name": "11_briefing",
        "title": "11 Briefing / Objectives Dossier",
        "reference_label": "GE480i reference (VLC snap)",
        "current_label": "No safe current route",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h15m11s715.png",
        "current": None,
        "verdict": "Blocked: safe capture route needed",
        "verdict_color": "yellow",
        "reference_boxes": [
            {"box": [70, 70, 660, 510], "color": "green", "label": "paper bounds"},
            {"box": [95, 170, 525, 330], "color": "cyan", "label": "briefing text block"},
        ],
        "current_boxes": [],
        "note": "The forced briefing route produced the rejected strobe behavior, so briefing should be captured through a safer live/manual route before patching.",
    },
    {
        "name": "12_moneypenny",
        "title": "12 Moneypenny Dossier Page",
        "reference_label": "GE480i reference (VLC snap)",
        "current_label": "No safe current route",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h15m20s302.png",
        "current": None,
        "verdict": "Capture required before patching",
        "verdict_color": "yellow",
        "reference_boxes": [
            {"box": [70, 70, 660, 510], "color": "green", "label": "paper bounds"},
            {"box": [95, 185, 535, 255], "color": "cyan", "label": "Moneypenny text block"},
            {"box": [640, 115, 670, 505], "color": "yellow", "label": "tabs"},
        ],
        "current_boxes": [],
        "note": "This is part of the pre-ingame acceptance set. Do not assume it passes until captured through a non-strobing route.",
    },
    {
        "name": "13_objectives",
        "title": "13 Primary Objectives Dossier Page",
        "reference_label": "GE480i reference (VLC snap)",
        "current_label": "No safe current route",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h15m43s930.png",
        "current": None,
        "verdict": "Capture required before patching",
        "verdict_color": "yellow",
        "reference_boxes": [
            {"box": [70, 70, 660, 510], "color": "green", "label": "paper bounds"},
            {"box": [420, 70, 625, 230], "color": "cyan", "label": "mission photo"},
            {"box": [95, 265, 400, 335], "color": "yellow", "label": "objective text"},
            {"box": [640, 115, 670, 505], "color": "magenta", "label": "tabs"},
        ],
        "current_boxes": [],
        "note": "This page must be checked after a safe briefing/objectives route exists, because the rejected forced route caused strobing.",
    },
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    cards = []
    manifest = []
    for spec in SPECS:
        card = make_card(spec)
        out_path = OUT_DIR / f"{spec['name']}.jpg"
        card.save(out_path, quality=92)
        cards.append(card)
        manifest.append({
            "name": spec["name"],
            "title": spec["title"],
            "reference": spec.get("reference"),
            "current": spec.get("current"),
            "out": str(out_path.relative_to(ROOT)),
            "verdict": spec["verdict"],
            "note": spec["note"],
        })

    atlas = build_atlas(cards)
    atlas.save(ATLAS, quality=90)
    REPORT.write_text(json.dumps({
        "candidate": CANDIDATE,
        "atlas": str(ATLAS.relative_to(ROOT)),
        "cards": manifest,
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"atlas": str(ATLAS), "cards": len(cards), "report": str(REPORT)}, indent=2))


if __name__ == "__main__":
    main()
