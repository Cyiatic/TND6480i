#!/usr/bin/env python3
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = "g1casta1"
STAMP = "20260518"

OUT_DIR = ROOT / "diagnostics" / "captures" / "current" / f"preingame_issue_cards_{CANDIDATE}_{STAMP}"
ATLAS = ROOT / "diagnostics" / "captures" / "current" / f"preingame_issue_cards_{CANDIDATE}_{STAMP}.jpg"
REPORT = ROOT / "reports" / f"preingame_issue_cards_{CANDIDATE}_{STAMP}.json"

TARGET_SIZE = (720, 540)
CARD_WIDTH = 1510
CARD_HEIGHT = 770

COLORS = {
    "green": (40, 230, 80),
    "cyan": (40, 220, 255),
    "yellow": (255, 210, 30),
    "red": (255, 70, 70),
    "magenta": (255, 90, 210),
    "orange": (255, 150, 40),
    "white": (245, 245, 245),
    "gray": (170, 170, 170),
}


def font(size):
    for name in ("consola.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


FONT_TITLE = font(22)
FONT_LABEL = font(16)
FONT_SMALL = font(14)
FONT_NOTE = font(15)


def rel(path):
    return ROOT / path


def resolve_path(path):
    if not path:
        return None
    image_path = Path(path)
    if not image_path.is_absolute():
        image_path = rel(path)
    return image_path


def active_bbox(image, threshold=32):
    pixels = image.load()
    xs = []
    ys = []
    for y in range(image.height):
        for x in range(image.width):
            r, g, b = pixels[x, y]
            if max(r, g, b) > threshold and (r + g + b) > threshold * 2:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return [min(xs), min(ys), max(xs), max(ys)]


def load_panel(path, label):
    panel = Image.new("RGB", TARGET_SIZE, (10, 10, 10))
    if not path:
        draw = ImageDraw.Draw(panel)
        draw.text((24, 240), "no safe current capture yet", fill=COLORS["yellow"], font=FONT_TITLE)
        draw.rectangle((0, 0, TARGET_SIZE[0] - 1, TARGET_SIZE[1] - 1), outline=COLORS["yellow"])
        return panel, None
    image_path = resolve_path(path)
    image = Image.open(image_path).convert("RGB")
    if image.size != TARGET_SIZE:
        image = image.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    bbox = active_bbox(image)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, TARGET_SIZE[0], 30), fill=(0, 0, 0))
    draw.text((8, 5), label, fill=COLORS["white"], font=FONT_SMALL)
    return image, bbox


def draw_box(draw, box, color_name, label):
    color = COLORS[color_name]
    x1, y1, x2, y2 = box
    for inset in range(2):
        draw.rectangle((x1 + inset, y1 + inset, x2 - inset, y2 - inset), outline=color)
    if label:
        y = y1 - 18
        if y < 32:
            y = y2 + 4
        draw.text((x1 + 4, y), label, fill=color, font=FONT_SMALL)


def draw_line(draw, line, color_name, label):
    color = COLORS[color_name]
    x1, y1, x2, y2 = line
    draw.line((x1, y1, x2, y2), fill=color, width=3)
    if label:
        draw.text((min(x1, x2) + 4, max(32, min(y1, y2) - 18)), label, fill=color, font=FONT_SMALL)


def wrap_text(draw, text, width, font_obj=FONT_NOTE):
    words = text.split()
    lines = []
    line = ""
    for word in words:
        test = word if not line else f"{line} {word}"
        bbox = draw.textbbox((0, 0), test, font=font_obj)
        if bbox[2] - bbox[0] <= width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def apply_overlays(panel, spec, side):
    draw = ImageDraw.Draw(panel)
    for item in spec.get(f"{side}_boxes", []):
        draw_box(draw, item["box"], item["color"], item["label"])
    for item in spec.get(f"{side}_lines", []):
        draw_line(draw, item["line"], item["color"], item["label"])


def make_card(spec):
    left, left_bbox = load_panel(spec.get("reference"), spec["reference_label"])
    right, right_bbox = load_panel(spec.get("current"), spec["current_label"])
    apply_overlays(left, spec, "reference")
    apply_overlays(right, spec, "current")

    card = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), (18, 18, 18))
    draw = ImageDraw.Draw(card)
    severity_color = COLORS[spec.get("severity_color", "yellow")]
    draw.text((12, 10), spec["title"], fill=COLORS["white"], font=FONT_TITLE)
    draw.text((12, 38), spec["status"], fill=severity_color, font=FONT_LABEL)
    card.paste(left, (12, 80))
    card.paste(right, (778, 80))
    draw.rectangle((742, 80, 768, 620), fill=(30, 30, 30))

    measure = spec.get("measurement", "")
    if spec.get("show_active_bbox", False):
        measure = f"{measure} Active bbox ref={left_bbox}, current={right_bbox}."

    y = 628
    for label, text, color in (
        ("Mismatch: ", spec["mismatch"], "red"),
        ("Target: ", spec["target"], "cyan"),
        ("Measurement: ", measure, "yellow"),
    ):
        if not text:
            continue
        draw.text((12, y), label, fill=COLORS[color], font=FONT_NOTE)
        prefix_w = draw.textbbox((0, 0), label, font=FONT_NOTE)[2]
        lines = wrap_text(draw, text, CARD_WIDTH - prefix_w - 28)
        for idx, line in enumerate(lines[:2]):
            draw.text((12 + prefix_w if idx == 0 else 12, y + idx * 18), line, fill=COLORS["white"], font=FONT_NOTE)
        y += max(1, min(2, len(lines))) * 18 + 4

    return card, {"reference_active_bbox": left_bbox, "current_active_bbox": right_bbox}


SPECS = [
    {
        "name": "01_classification",
        "title": "01 Classification Board",
        "status": "FAIL: vertical layout is compressed/upshifted versus GE480i",
        "severity_color": "red",
        "reference_label": "GE480i classification reference",
        "current_label": "Current g1casta1 hardware capture",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h14m11s759.png",
        "current": "diagnostics/captures/contact_sheets/g1casta1_full_front_hardware_cycled_20260518/frames/frame_0002_00010000.png",
        "show_active_bbox": True,
        "reference_boxes": [
            {"box": [55, 55, 660, 450], "color": "green", "label": "GE480i legal-page envelope"},
            {"box": [435, 125, 655, 212], "color": "cyan", "label": "right legal block"},
            {"box": [55, 236, 655, 242], "color": "yellow", "label": "divider"},
            {"box": [220, 405, 520, 455], "color": "magenta", "label": "bottom legal text"},
        ],
        "current_boxes": [
            {"box": [40, 22, 660, 365], "color": "red", "label": "current active area ends too high"},
            {"box": [255, 75, 460, 143], "color": "cyan", "label": "right block too high"},
            {"box": [55, 210, 660, 216], "color": "yellow", "label": "divider too high"},
            {"box": [95, 250, 405, 292], "color": "magenta", "label": "bottom text too high"},
        ],
        "mismatch": "The content is squeezed into the top two-thirds of the screen. The GE480i reference spreads the legal block, divider, signatures, rating, and bottom copyright line down to the lower safe area.",
        "target": "Use GE480i classification as the high-res layout reference, while preserving TND64-specific wording/logos.",
        "measurement": "Current bottom legal text is around y=250-292; GE480i bottom legal text is around y=405-455.",
    },
    {
        "name": "02_tijayfly_logo",
        "title": "02 TiJayFly Logo",
        "status": "UNCERTAIN: needs dynamic verification, not a still-frame promotion",
        "severity_color": "yellow",
        "reference_label": "Stock TND64 content reference",
        "current_label": "Current g1casta1 hardware capture",
        "reference": "diagnostics/captures/contact_sheets/stock_tnd_preingame_scan_20260518/frames/frame_0015_00075000.png",
        "current": "diagnostics/captures/contact_sheets/g1casta1_full_front_hardware_cycled_20260518/frames/frame_0003_00015000.png",
        "reference_boxes": [
            {"box": [90, 215, 560, 270], "color": "green", "label": "stock logo band"},
        ],
        "current_boxes": [
            {"box": [120, 205, 590, 276], "color": "yellow", "label": "current logo band"},
        ],
        "mismatch": "Single stills do not prove whether the logo animation is scaled or timed correctly. Current logo is visible, but the capture frames vary in brightness and direction during the loop.",
        "target": "Verify against a short stock TND64 and g1casta1 motion strip with matched timestamps before changing logo code.",
        "measurement": "Logo still-frame bounds are broadly centered; dynamic cadence remains unknown.",
    },
    {
        "name": "03_rare_logo",
        "title": "03 Rare Logo",
        "status": "UNCERTAIN: needs stock-motion comparison",
        "severity_color": "yellow",
        "reference_label": "Stock/TND content reference",
        "current_label": "Current g1casta1 hardware capture",
        "reference": "diagnostics/captures/contact_sheets/stock_tnd_preingame_scan_20260518/frames/frame_0017_00085000.png",
        "current": "diagnostics/captures/contact_sheets/g1casta1_full_front_hardware_cycled_20260518/frames/frame_0020_00100000.png",
        "reference_boxes": [
            {"box": [300, 150, 420, 340], "color": "green", "label": "Rare logo"},
        ],
        "current_boxes": [
            {"box": [305, 145, 425, 345], "color": "yellow", "label": "Rare logo"},
        ],
        "mismatch": "No obvious single-frame placement failure, but this logo needs a motion/timing check like TiJayFly.",
        "target": "Leave untouched unless the motion strip shows a scale or field cadence mismatch.",
        "measurement": "Still-frame center and approximate size are close enough for now.",
    },
    {
        "name": "04_gunbarrel",
        "title": "04 Gunbarrel",
        "status": "LIKELY PASS: composition now matches the GE480i family",
        "severity_color": "green",
        "reference_label": "GE480i gunbarrel reference",
        "current_label": "Current g1casta1 hardware capture",
        "reference": "diagnostics/captures/contact_sheets/ge480i_gunbarrel_detail_20260518/frames/frame_0008_00032000.png",
        "current": "diagnostics/captures/contact_sheets/g1casta1_full_front_hardware_cycled_20260518/frames/frame_0008_00040000.png",
        "reference_boxes": [
            {"box": [315, 130, 650, 430], "color": "green", "label": "barrel field"},
            {"box": [455, 245, 560, 390], "color": "cyan", "label": "Bond"},
        ],
        "current_boxes": [
            {"box": [300, 130, 665, 430], "color": "green", "label": "barrel field"},
            {"box": [455, 245, 560, 390], "color": "cyan", "label": "Bond"},
        ],
        "mismatch": "No large visual mismatch remaining in this still. Cadence still needs a final CRT/hardware timing check.",
        "target": "Do not spend the next pass here unless cadence is proven wrong.",
        "measurement": "The previous extra aperture/second barrel is gone in g1casta1.",
    },
    {
        "name": "05_title_logo",
        "title": "05 TND Title Logo",
        "status": "NEEDS CHECK: title scale should be judged against GE480i title behavior",
        "severity_color": "yellow",
        "reference_label": "Stock TND64 content reference",
        "current_label": "Current g1casta1 title capture",
        "reference": "diagnostics/captures/contact_sheets/stock_tnd_preingame_scan_20260518/frames/frame_0008_00040000.png",
        "current": "diagnostics/captures/contact_sheets/g1casta1_title_transition_20260518/frames/frame_0007_00057000.png",
        "reference_boxes": [
            {"box": [300, 255, 505, 315], "color": "green", "label": "stock title bounds"},
        ],
        "current_boxes": [
            {"box": [270, 255, 492, 315], "color": "yellow", "label": "current bounds"},
        ],
        "mismatch": "The title is visible, but it has not been proven to use the same high-res presentation/cadence as GE480i's title path.",
        "target": "Compare a GE480i title transition strip and current TND title transition strip, then adjust only if bounds/timing differ.",
        "measurement": "Current still is centered; dynamic behavior is the missing proof.",
    },
    {
        "name": "06_opening_credits",
        "title": "06 Opening Credits / Cast Transitions",
        "status": "FAIL: text/fade layer is not scaled/cleared like the model layer",
        "severity_color": "red",
        "reference_label": "GE480i credits text-scale reference",
        "current_label": "Current g1casta1 transition artifact",
        "reference": "diagnostics/captures/contact_sheets/verify_opening_credits_ge480i_20260518/frames/frame_0004_00058000.png",
        "current": "diagnostics/captures/contact_sheets/g1casta1_full_front_hardware_cycled_20260518/frames/frame_0016_00080000.png",
        "reference_boxes": [
            {"box": [360, 110, 615, 180], "color": "cyan", "label": "credit text scale"},
            {"box": [0, 430, 720, 535], "color": "green", "label": "clean lower field"},
        ],
        "current_boxes": [
            {"box": [300, 105, 560, 190], "color": "yellow", "label": "text layer looks stock-sized/soft"},
            {"box": [0, 327, 505, 385], "color": "red", "label": "bad fade/clear rectangle"},
        ],
        "mismatch": "Models are no longer badly cropped, but the text/fade layer still leaves a visible rectangular transition artifact near the lower screen.",
        "target": "Find the cast-credit text/fade clear rectangle path and scale/clear it consistently with the 480i presentation.",
        "measurement": "Visible lower artifact around y=327-385 in current transition frame.",
    },
    {
        "name": "07_file_select",
        "title": "07 File Select Dossier",
        "status": "FAIL: right-side gunbarrel/background bleed and folder bounds mismatch",
        "severity_color": "red",
        "reference_label": "GE480i file select reference",
        "current_label": "Current inherited dossier capture",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h14m25s727.png",
        "current": "diagnostics/captures/current/g1mtabge4_file_hw_norm_20260518.png",
        "show_active_bbox": True,
        "reference_boxes": [
            {"box": [58, 72, 660, 512], "color": "green", "label": "GE file group envelope"},
            {"box": [245, 430, 545, 475], "color": "cyan", "label": "bottom labels/icons"},
            {"box": [650, 60, 672, 512], "color": "yellow", "label": "right edge target"},
        ],
        "current_boxes": [
            {"box": [65, 80, 690, 512], "color": "red", "label": "current extends too far right"},
            {"box": [250, 430, 560, 475], "color": "cyan", "label": "labels/icons"},
            {"box": [690, 60, 715, 512], "color": "yellow", "label": "gunbarrel bleed"},
        ],
        "mismatch": "The file labels/icons are present, but the background/folder presentation bleeds too far right compared with GE480i.",
        "target": "Preserve visible labels/icons, but bring the dossier background/folder envelope back inside the GE480i right-edge behavior.",
        "measurement": "Active bbox current reaches x=707; GE480i file select reaches about x=660.",
    },
    {
        "name": "08_mode_select",
        "title": "08 Bond Dossier / Mode Select",
        "status": "FAIL: row/cursor/previous tab still do not match GE480i",
        "severity_color": "red",
        "reference_label": "GE480i mode select reference",
        "current_label": "Current inherited dossier capture",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h14m38s302.png",
        "current": "diagnostics/captures/current/g1mtabge4_mode_hw_norm_20260518.png",
        "reference_boxes": [
            {"box": [184, 356, 404, 383], "color": "green", "label": "cursor + highlight share row"},
            {"box": [638, 384, 670, 510], "color": "cyan", "label": "PREVIOUS on tab"},
        ],
        "current_boxes": [
            {"box": [120, 337, 165, 382], "color": "red", "label": "cursor not on selected row"},
            {"box": [240, 354, 405, 383], "color": "yellow", "label": "highlight/text row shifted"},
            {"box": [565, 250, 600, 365], "color": "yellow", "label": "PREVIOUS inside page"},
            {"box": [640, 385, 670, 510], "color": "cyan", "label": "tab target area"},
        ],
        "mismatch": "This is close visually, but the cursor, highlight/text row, and PREVIOUS label are not sharing the same geometry as GE480i.",
        "target": "Match GE480i row/cursor/tab relationships while retaining TND red folder art and TND menu text.",
        "measurement": "GE selected row begins near x=184; current cursor is near x=120 while row text/highlight starts near x=240.",
    },
    {
        "name": "09_mission_select",
        "title": "09 Mission Select",
        "status": "FAIL: mission captions do not sit in the GE480i film caption bands",
        "severity_color": "red",
        "reference_label": "GE480i mission select reference",
        "current_label": "Current inherited mission capture",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h14m57s301.png",
        "current": "diagnostics/captures/current/g1mtabge4_mission_hw_norm_20260518.png",
        "reference_boxes": [
            {"box": [62, 68, 641, 422], "color": "green", "label": "GE filmstrip grid"},
            {"box": [65, 143, 640, 163], "color": "cyan", "label": "row 1 caption band"},
            {"box": [65, 265, 640, 285], "color": "cyan", "label": "row 2 caption band"},
            {"box": [65, 388, 640, 408], "color": "cyan", "label": "row 3 caption band"},
        ],
        "current_boxes": [
            {"box": [62, 58, 640, 380], "color": "yellow", "label": "TND filmstrip envelope"},
            {"box": [48, 135, 650, 160], "color": "red", "label": "row labels off-band"},
            {"box": [48, 255, 650, 283], "color": "red", "label": "row labels off-band"},
            {"box": [48, 374, 650, 405], "color": "red", "label": "row labels off-band"},
        ],
        "mismatch": "The TND mission count differs, but labels still need the GE480i caption-band relationship. Several names sit too close to perforations or images.",
        "target": "Keep TND's 5/5/4 mission layout but center labels within each film caption band like GE480i.",
        "measurement": "Previous global table probes helped some rows and harmed others; likely needs page-specific caption geometry, not a blind X/Y shove.",
    },
    {
        "name": "10_difficulty",
        "title": "10 Difficulty Select",
        "status": "FAIL: paper and difficulty rows are shifted versus GE480i",
        "severity_color": "red",
        "reference_label": "GE480i difficulty reference",
        "current_label": "Current inherited difficulty capture",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h15m03s394.png",
        "current": "diagnostics/captures/current/g1mtabge4_difficulty_hw_norm_20260518.png",
        "reference_boxes": [
            {"box": [80, 70, 660, 510], "color": "green", "label": "GE paper bounds"},
            {"box": [95, 240, 285, 365], "color": "cyan", "label": "difficulty rows"},
        ],
        "current_boxes": [
            {"box": [62, 48, 668, 508], "color": "yellow", "label": "current paper bounds"},
            {"box": [112, 200, 330, 322], "color": "red", "label": "rows too high/right"},
        ],
        "mismatch": "The page is usable, but it is not GE480i-aligned: the paper starts higher/left and the difficulty block sits too high.",
        "target": "Align paper bounds and difficulty row block to the GE480i page geometry while preserving TND labels.",
        "measurement": "GE difficulty row block y=240-365; current y=200-322.",
    },
    {
        "name": "11_briefing",
        "title": "11 Briefing / Background",
        "status": "BLOCKED: no safe current capture after strobe-route rejection",
        "severity_color": "yellow",
        "reference_label": "GE480i briefing reference",
        "current_label": "No safe current capture",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h15m11s715.png",
        "current": None,
        "reference_boxes": [
            {"box": [70, 70, 660, 510], "color": "green", "label": "paper bounds"},
            {"box": [95, 170, 525, 330], "color": "cyan", "label": "briefing text block"},
            {"box": [640, 115, 670, 505], "color": "yellow", "label": "tabs"},
        ],
        "current_boxes": [],
        "mismatch": "The forced briefing route produced strobing, so there is no trustworthy current image for this page.",
        "target": "Get this through normal navigation or a safer direct route before patching any briefing constants.",
        "measurement": "No current measurement; strobe route is rejected.",
    },
    {
        "name": "12_moneypenny",
        "title": "12 Moneypenny",
        "status": "BLOCKED: reference exists, current capture still required",
        "severity_color": "yellow",
        "reference_label": "GE480i Moneypenny reference",
        "current_label": "No safe current capture",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h15m20s302.png",
        "current": None,
        "reference_boxes": [
            {"box": [70, 70, 660, 510], "color": "green", "label": "paper bounds"},
            {"box": [95, 185, 535, 255], "color": "cyan", "label": "Moneypenny text block"},
            {"box": [640, 115, 670, 505], "color": "yellow", "label": "tabs"},
        ],
        "current_boxes": [],
        "mismatch": "No safe current capture means this page cannot be honestly marked fixed.",
        "target": "Capture through a safe route, then compare text block, tabs, and paper bounds.",
        "measurement": "No current measurement yet.",
    },
    {
        "name": "13_objectives",
        "title": "13 Primary Objectives",
        "status": "BLOCKED: reference exists, current capture still required",
        "severity_color": "yellow",
        "reference_label": "GE480i objectives reference",
        "current_label": "No safe current capture",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h15m43s930.png",
        "current": None,
        "reference_boxes": [
            {"box": [70, 70, 660, 510], "color": "green", "label": "paper bounds"},
            {"box": [420, 70, 625, 230], "color": "cyan", "label": "mission photo"},
            {"box": [95, 265, 400, 335], "color": "yellow", "label": "objective text"},
            {"box": [640, 115, 670, 505], "color": "magenta", "label": "tabs"},
        ],
        "current_boxes": [],
        "mismatch": "No safe current capture means this page cannot be honestly marked fixed.",
        "target": "Capture through a safe route, then compare mission photo, objective text block, tabs, and paper bounds.",
        "measurement": "No current measurement yet.",
    },
]


def build_atlas(cards):
    thumb_w = 755
    thumb_h = 385
    cols = 2
    rows = math.ceil(len(cards) / cols)
    atlas = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (20, 20, 20))
    for index, card in enumerate(cards):
        thumb = card.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        atlas.paste(thumb, ((index % cols) * thumb_w, (index // cols) * thumb_h))
    return atlas


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    cards = []
    manifest = []
    for spec in SPECS:
        card, measurements = make_card(spec)
        out_path = OUT_DIR / f"{spec['name']}.jpg"
        card.save(out_path, quality=92)
        cards.append(card)
        manifest.append({
            "name": spec["name"],
            "title": spec["title"],
            "status": spec["status"],
            "reference": spec.get("reference"),
            "current": spec.get("current"),
            "out": str(out_path.relative_to(ROOT)),
            "mismatch": spec["mismatch"],
            "target": spec["target"],
            "measurement": spec.get("measurement"),
            **measurements,
        })

    atlas = build_atlas(cards)
    atlas.save(ATLAS, quality=90)
    REPORT.write_text(json.dumps({
        "candidate": CANDIDATE,
        "purpose": "Strict per-screen issue atlas. Red/yellow cards are not fixed until a new hardware capture matches the annotated reference geometry.",
        "atlas": str(ATLAS.relative_to(ROOT)),
        "cards": manifest,
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"atlas": str(ATLAS), "cards": len(cards), "report": str(REPORT)}, indent=2))


if __name__ == "__main__":
    main()
