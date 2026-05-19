#!/usr/bin/env python3
"""Build a visual coverage atlas for the current g1mcfix1 candidate.

This is intentionally evidence-oriented: every row points at a concrete frame
or marks the screen as needing another manual capture.  The spelling pass is a
visual/manual audit of text visible in the captured frames, not OCR.
"""

import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
STAMP = "20260519"
CANDIDATE = "g1mcfix1"

OUT_DIR = ROOT / "diagnostics" / "captures" / "current" / f"{CANDIDATE}_screen_coverage_{STAMP}"
ATLAS = ROOT / "diagnostics" / "captures" / "current" / f"{CANDIDATE}_screen_coverage_atlas_{STAMP}.jpg"
REPORT = ROOT / "reports" / f"{CANDIDATE}_screen_coverage_atlas_{STAMP}.json"

PANEL_SIZE = (520, 390)
CARD_W = 1120
CARD_H = 590
THUMB_W = 560
THUMB_H = 295

COLORS = {
    "bg": (18, 18, 18),
    "panel": (9, 9, 9),
    "white": (245, 245, 245),
    "muted": (175, 175, 175),
    "green": (60, 230, 90),
    "cyan": (55, 220, 255),
    "yellow": (255, 214, 55),
    "orange": (255, 155, 45),
    "red": (255, 72, 72),
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
FONT_NOTE = font(14)
FONT_SMALL = font(13)


def resolve(path):
    if not path:
        return None
    p = Path(path)
    if p.is_absolute():
        return p
    return ROOT / p


def rel_for_report(path):
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def normalize_panel(path, label):
    panel = Image.new("RGB", PANEL_SIZE, COLORS["panel"])
    p = resolve(path)
    draw = ImageDraw.Draw(panel)
    if not p or not p.exists():
        draw.text((22, 160), "no capture", fill=COLORS["yellow"], font=FONT_TITLE)
        draw.text((22, 190), label, fill=COLORS["muted"], font=FONT_NOTE)
        draw.rectangle((0, 0, PANEL_SIZE[0] - 1, PANEL_SIZE[1] - 1), outline=COLORS["yellow"])
        return panel

    im = Image.open(p).convert("RGB")
    im.thumbnail((PANEL_SIZE[0], PANEL_SIZE[1] - 26), Image.Resampling.LANCZOS)
    x = (PANEL_SIZE[0] - im.width) // 2
    y = 26 + (PANEL_SIZE[1] - 26 - im.height) // 2
    panel.paste(im, (x, y))
    draw = ImageDraw.Draw(panel)
    draw.rectangle((0, 0, PANEL_SIZE[0], 25), fill=(0, 0, 0))
    draw.text((7, 5), label, fill=COLORS["white"], font=FONT_SMALL)
    return panel


def wrap(draw, text, width, font_obj=FONT_NOTE):
    lines = []
    line = ""
    for word in text.split():
        trial = word if not line else f"{line} {word}"
        bbox = draw.textbbox((0, 0), trial, font=font_obj)
        if bbox[2] - bbox[0] <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_wrapped(draw, x, y, label, text, color, width, max_lines=3):
    draw.text((x, y), label, fill=COLORS[color], font=FONT_NOTE)
    prefix_w = draw.textbbox((0, 0), label, font=FONT_NOTE)[2]
    lines = wrap(draw, text, width - prefix_w, FONT_NOTE)
    for idx, line in enumerate(lines[:max_lines]):
        draw.text((x + prefix_w if idx == 0 else x, y + 18 * idx), line, fill=COLORS["white"], font=FONT_NOTE)
    return y + max(1, min(max_lines, len(lines))) * 18 + 4


def make_card(spec):
    ref = normalize_panel(spec.get("reference"), spec.get("reference_label", "reference"))
    cur = normalize_panel(spec.get("current"), spec.get("current_label", "current"))
    card = Image.new("RGB", (CARD_W, CARD_H), COLORS["bg"])
    draw = ImageDraw.Draw(card)
    status_color = spec.get("status_color", "yellow")
    draw.text((12, 10), spec["title"], fill=COLORS["white"], font=FONT_TITLE)
    draw.text((12, 38), spec["status"], fill=COLORS[status_color], font=FONT_LABEL)
    card.paste(ref, (12, 70))
    card.paste(cur, (588, 70))
    draw.rectangle((554, 70, 566, 460), fill=(35, 35, 35))

    y = 470
    y = draw_wrapped(draw, 12, y, "Text checked: ", "; ".join(spec["text_checked"]), "cyan", CARD_W - 24, 2)
    y = draw_wrapped(draw, 12, y, "Spelling: ", spec["spelling"], "green" if spec["spelling_status"] == "PASS" else "yellow", CARD_W - 24, 2)
    y = draw_wrapped(draw, 12, y, "Layout note: ", spec["layout_note"], "yellow", CARD_W - 24, 2)
    return card


def build_atlas(cards):
    rows = math.ceil(len(cards) / 2)
    atlas = Image.new("RGB", (THUMB_W * 2, THUMB_H * rows), (20, 20, 20))
    for i, card in enumerate(cards):
        thumb = card.resize((THUMB_W, THUMB_H), Image.Resampling.LANCZOS)
        atlas.paste(thumb, ((i % 2) * THUMB_W, (i // 2) * THUMB_H))
    return atlas


def copy_sources(specs):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    copied = {}
    for spec in specs:
        for key in ("reference", "current"):
            p = resolve(spec.get(key))
            if not p or not p.exists():
                continue
            dest = OUT_DIR / f"{spec['name']}_{key}{p.suffix.lower()}"
            if p.resolve() != dest.resolve():
                shutil.copy2(p, dest)
            copied[str(p)] = dest
    return copied


SPECS = [
    {
        "name": "01_classification",
        "title": "01 Classification Board",
        "status": "PASS with low-confidence fine print",
        "status_color": "green",
        "reference_label": "GE480i legal screen reference",
        "current_label": "Current g1mcfix1/g1cred1 startup",
        "reference": "diagnostics/captures/contact_sheets/ge480i_scan_20260518/frames/frame_0028_00140000.png",
        "current": "diagnostics/captures/contact_sheets/g1cred1_full_startup_1fps_20260519/frames/frame_0002_00010000.png",
        "text_checked": [
            "CMK BOARD OF GAME CLASSIFICATION",
            "Proudly presents",
            "Tomorrow Never Dies 64 - Expanded",
            "A not-for-profit fan homage to James Bond",
        ],
        "spelling_status": "PASS",
        "spelling": "No visible typo in large text. Fine-print copyright lines are capture-limited, so I am treating them as low-confidence rather than fully OCR-verified.",
        "layout_note": "Content is fully onscreen and no longer runs off to the right; it uses the TND64 legal copy rather than GE wording.",
    },
    {
        "name": "02_tijayfly",
        "title": "02 TiJayFly Logo",
        "status": "PASS visual",
        "status_color": "green",
        "reference_label": "Stock TND64 logo reference",
        "current_label": "Current g1mcfix1/g1cred1 startup",
        "reference": "diagnostics/captures/contact_sheets/stock_tnd_preingame_scan_20260518/frames/frame_0001_00005000.png",
        "current": "diagnostics/captures/contact_sheets/g1cred1_full_startup_1fps_20260519/frames/frame_0007_00015000.png",
        "text_checked": ["TIJAYFLY"],
        "spelling_status": "PASS",
        "spelling": "Stylized TiJayFly logo text is intact in sampled frames; no spelling issue spotted.",
        "layout_note": "Logo remains centered in the same family as stock TND. This is a visual still check, not a frame-by-frame animation proof.",
    },
    {
        "name": "03_rare",
        "title": "03 Rare Logo",
        "status": "PASS visual",
        "status_color": "green",
        "reference_label": "Stock TND64 Rare logo",
        "current_label": "Current g1mcfix1/g1cred1 startup",
        "reference": "diagnostics/captures/contact_sheets/stock_tnd_preingame_scan_20260518/frames/frame_0017_00085000.png",
        "current": "diagnostics/captures/contact_sheets/g1cred1_full_startup_1fps_20260519/frames/frame_0015_00023000.png",
        "text_checked": ["RAREWARE"],
        "spelling_status": "PASS",
        "spelling": "Rareware logo text is a graphic mark; no visible spelling issue.",
        "layout_note": "Logo is visible and centered. Motion cadence should only be revisited if a new patch disturbs startup timing.",
    },
    {
        "name": "04_gunbarrel_sweep",
        "title": "04 Gunbarrel Sweep",
        "status": "PASS visual / cadence still human-check",
        "status_color": "green",
        "reference_label": "GE480i gunbarrel reference",
        "current_label": "Current g1mcfix1/g1cred1 startup",
        "reference": "diagnostics/captures/contact_sheets/ge480i_gunbarrel_detail_20260518/frames/frame_0003_00022000.png",
        "current": "diagnostics/captures/contact_sheets/g1cred1_full_startup_1fps_20260519/frames/frame_0022_00030000.png",
        "text_checked": ["no text"],
        "spelling_status": "PASS",
        "spelling": "No text on this screen.",
        "layout_note": "Early white aperture sweep is back in the GE480i visual family. Cadence is still best judged from motion, not this still.",
    },
    {
        "name": "05_gunbarrel_bond",
        "title": "05 Gunbarrel With Bond",
        "status": "PASS visual / cadence still human-check",
        "status_color": "green",
        "reference_label": "GE480i gunbarrel reference",
        "current_label": "Current g1mcfix1/g1cred1 startup",
        "reference": "diagnostics/captures/contact_sheets/ge480i_gunbarrel_detail_20260518/frames/frame_0008_00032000.png",
        "current": "diagnostics/captures/contact_sheets/g1cred1_full_startup_1fps_20260519/frames/frame_0034_00042000.png",
        "text_checked": ["no text"],
        "spelling_status": "PASS",
        "spelling": "No text on this screen.",
        "layout_note": "The second/offset barrel failure is not present in the current startup sample.",
    },
    {
        "name": "06_goldeneye_logo",
        "title": "06 GoldenEye Title Logo Reference",
        "status": "REFERENCE ONLY",
        "status_color": "cyan",
        "reference_label": "GE480i title logo",
        "current_label": "TND title logo current analogue",
        "reference": "diagnostics/captures/contact_sheets/ge480i_scan_20260518/frames/frame_0010_00050000.png",
        "current": "diagnostics/captures/contact_sheets/g1cred1_full_startup_1fps_20260519/frames/frame_0049_00057000.png",
        "text_checked": ["GoldenEye", "Tomorrow Never Dies"],
        "spelling_status": "PASS",
        "spelling": "GE reference spells GoldenEye correctly; current TND title spells Tomorrow Never Dies correctly.",
        "layout_note": "This row compares high-res title-logo treatment, not identical artwork. TND uses its own logo asset.",
    },
    {
        "name": "07_tnd_logo",
        "title": "07 Tomorrow Never Dies Title Logo",
        "status": "PASS visual",
        "status_color": "green",
        "reference_label": "Stock TND64 title logo",
        "current_label": "Current g1mcfix1/g1cred1 startup",
        "reference": "diagnostics/captures/contact_sheets/stock_tnd_preingame_scan_20260518/frames/frame_0008_00040000.png",
        "current": "diagnostics/captures/contact_sheets/g1cred1_full_startup_1fps_20260519/frames/frame_0049_00057000.png",
        "text_checked": ["Tomorrow Never Dies", "007"],
        "spelling_status": "PASS",
        "spelling": "On-screen title spells Tomorrow Never Dies correctly; the mixed-case DIes typo only appears in a local reference filename, not the game screen.",
        "layout_note": "Centered, readable, and no longer interrupted by the earlier gunbarrel transition failures.",
    },
    {
        "name": "08_opening_cast",
        "title": "08 Opening Credits / Cast Models",
        "status": "PASS visual with content-specific differences",
        "status_color": "green",
        "reference_label": "GE480i cast scale reference",
        "current_label": "Current g1mcfix1/g1cred1 startup",
        "reference": "diagnostics/captures/contact_sheets/ge480i_scan_20260518/frames/frame_0012_00060000.png",
        "current": "diagnostics/captures/contact_sheets/g1cred1_full_startup_1fps_20260519/frames/frame_0052_00060000.png",
        "text_checked": ["Starring", "007", "James Bond"],
        "spelling_status": "PASS",
        "spelling": "Visible sampled cast text has no typo. Names are TND64 content, so they will not match the GE cast list.",
        "layout_note": "Character scale and text scale are now in the high-res family; no bottom transition rectangle is visible in the sampled current title/cast frames.",
    },
    {
        "name": "09_file_select",
        "title": "09 File Select Dossier",
        "status": "PASS visual",
        "status_color": "green",
        "reference_label": "GE480i file select reference",
        "current_label": "Current g1mcfix1 route",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h14m25s727.png",
        "current": "diagnostics/captures/current/g1cred1_route_frames_20260519/g1cauto05_file_select.png",
        "text_checked": ["Select File", "Copy", "Erase", "007"],
        "spelling_status": "PASS",
        "spelling": "No visible typo. The earlier Custom label is fixed to 007.",
        "layout_note": "Icons and labels are present; red/black wallpaper differs from GE green by design.",
    },
    {
        "name": "10_mode_select",
        "title": "10 Bond Dossier / Mode Select",
        "status": "PASS visual",
        "status_color": "green",
        "reference_label": "GE480i mode select reference",
        "current_label": "Current g1mcfix1 route",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h14m38s302.png",
        "current": "diagnostics/captures/current/g1cred1_route_frames_20260519/g1cauto06_mode_select.png",
        "text_checked": ["SELECT MISSION", "MULTIPLAYER", "CHEAT OPTIONS", "PREVIOUS"],
        "spelling_status": "PASS",
        "spelling": "No visible typo in the sampled menu text.",
        "layout_note": "Text, selection rows, paper, and previous tab match the GE480i envelope; TND uses red folder styling.",
    },
    {
        "name": "11_mission_select",
        "title": "11 Mission Select Dossier",
        "status": "PASS visual",
        "status_color": "green",
        "reference_label": "GE480i mission select reference",
        "current_label": "Current g1mcfix1 route",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h14m57s301.png",
        "current": "diagnostics/captures/current/g1cred1_route_frames_20260519/g1cauto07_mission_select.png",
        "text_checked": ["BAZAAR", "PARTY", "LABS", "PRESS", "HOTEL", "PARKHAUS", "WRECK", "TOWER", "CITY", "BOAT", "BRIDGE", "VOLCANO", "ALASKA", "THE END"],
        "spelling_status": "PASS",
        "spelling": "No visible typo. Parkhaus is intentional; Boat is present, not Bride.",
        "layout_note": "Mission labels and film thumbnails sit inside the dossier area. Empty space is expected because TND64 has fewer missions than GE.",
    },
    {
        "name": "12_difficulty",
        "title": "12 Difficulty Select Dossier",
        "status": "PASS visual",
        "status_color": "green",
        "reference_label": "GE480i difficulty reference",
        "current_label": "Current g1mcfix1 route",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h15m03s394.png",
        "current": "diagnostics/captures/current/g1cred1_route_frames_20260519/g1cpathbtn08_difficulty_path.png",
        "text_checked": ["DIFFICULTY", "Easy", "Normal", "Hard", "Mission 3: South China Sea", "Part i: Deep Sea Wreck"],
        "spelling_status": "PASS",
        "spelling": "No typo spotted. The lower-case roman numeral in Part i matches the inherited GE dossier style.",
        "layout_note": "Red check marks, rows, heading, and tabs are aligned in the GE480i layout family.",
    },
    {
        "name": "13_briefing",
        "title": "13 Briefing / Background Page",
        "status": "PASS visual",
        "status_color": "green",
        "reference_label": "GE480i briefing reference",
        "current_label": "Current g1mcfix1 route",
        "reference": "C:/Users/codex/Pictures/vlcsnap-2026-05-18-18h15m20s302.png",
        "current": "diagnostics/captures/current/g1cred1_route_frames_20260519/g1cpathbtn0c_briefing_path.png",
        "text_checked": ["PRIMARY OBJECTIVES", "Mission 3: South China Sea", "Part i: Deep Sea Wreck", "START", "NEXT", "PREVIOUS"],
        "spelling_status": "PASS",
        "spelling": "No visible typo in the sampled route page. Objective body text is sparse in this diagnostic route, so full per-mission wording remains a manual-content check.",
        "layout_note": "The route capture uses a diagnostic state, but page geometry, heading scale, and tab placement are now correct.",
    },
    {
        "name": "14_mission_stats",
        "title": "14 Mission Complete Statistics",
        "status": "PASS visual after g1mcfix1",
        "status_color": "green",
        "reference_label": "GE480i stats reference",
        "current_label": "Current g1mcfix1 live GV-USB2",
        "reference": "diagnostics/captures/current/mission_result_compare_sources_20260519/ge480i_stats_0706.png",
        "current": "diagnostics/captures/current/g1mcfix1_live_now_screen_probe_20260519.png",
        "text_checked": ["OHMSS", "STATISTICS", "Time", "Best Time", "Accuracy", "Weapon of choice", "Shot total", "Kill total", "Head hits", "Body hits", "Limb hits", "Others"],
        "spelling_status": "PASS",
        "spelling": "No visible typo. OHMSS is a 007 dossier header/acronym, not a misspelling.",
        "layout_note": "The old Kill total / Best Time overlap is gone. Time/Best Time spacing is tight but follows the GE480i high-res stats window.",
    },
    {
        "name": "15_end_credits",
        "title": "15 End Credits",
        "status": "PASS visual / text sampled",
        "status_color": "green",
        "reference_label": "GE480i credits sample",
        "current_label": "Current g1cred1/g1mcfix1 credits sample",
        "reference": "diagnostics/captures/current/ge480i_live_end_credits_090s_20260519.png",
        "current": "diagnostics/captures/current/live_credits_format_probe_20260519.png",
        "text_checked": ["Casey Mongillo", "Chief Modeller", "Johnny Thunder", "'Rearmed' Content", "Hypatia onthegreatsea.tumblr.com"],
        "spelling_status": "PASS",
        "spelling": "No obvious typo in sampled current credits. 'Modeller' can be valid British/Commonwealth spelling and is left unchanged.",
        "layout_note": "Credits formatting is in the same general scale family as GE480i. Full crawl remains a long-duration spot check rather than a single-frame proof.",
    },
    {
        "name": "16_gameplay_watch",
        "title": "16 Gameplay HUD / Watch Menu",
        "status": "PASS by latest user hardware test; not re-captured in this atlas",
        "status_color": "yellow",
        "reference_label": "Older verified gameplay capture",
        "current_label": "Manual coverage note",
        "reference": "diagnostics/captures/current/user_driven_ingame_latest_after_note_20260510.png",
        "current": "",
        "text_checked": ["ammo HUD", "pause/watch menu text", "mission objective text boxes"],
        "spelling_status": "PASS",
        "spelling": "No spelling issue was reported in the latest gameplay/pass-menu test; this row is not a new OCR pass.",
        "layout_note": "User reported gameplay, pause menu, bullets UI, Bazaar, and Labs look fine. This remains a manual-control area for future regression sweeps.",
    },
]


def main():
    source_map = copy_sources(SPECS)
    cards = [make_card(spec) for spec in SPECS]
    ATLAS.parent.mkdir(parents=True, exist_ok=True)
    build_atlas(cards).save(ATLAS, quality=92)

    report_rows = []
    for spec in SPECS:
        row = dict(spec)
        row["reference"] = rel_for_report(resolve(spec.get("reference")) or "")
        row["current"] = rel_for_report(resolve(spec.get("current")) or "")
        for key in ("reference", "current"):
            original = resolve(spec.get(key))
            if original and str(original) in source_map:
                row[f"{key}_source_copy"] = rel_for_report(source_map[str(original)])
        report_rows.append(row)

    report = {
        "candidate": CANDIDATE,
        "candidate_rom": "artifacts/generated/g1mcfix1.z64",
        "candidate_md5": "32b0802210e71fecdf4a0a524b705aef",
        "method": "Side-by-side atlas built from existing GE480i/stock TND references plus current g1cred1/g1mcfix1 GV-USB2 captures. Spelling is visual/manual from captured text, not OCR.",
        "atlas": rel_for_report(ATLAS),
        "source_dir": rel_for_report(OUT_DIR),
        "rows": report_rows,
        "spelling_findings": [
            "No visible spelling errors found in captured current screens.",
            "The local filename spelling 'DIes' is not present on the Tomorrow Never Dies title screen.",
            "The mission select row says BOAT, not Bride; Bride was a note typo.",
            "Parkhaus is intentional TND64 content.",
            "Part i uses the inherited GoldenEye dossier roman-numeral style.",
            "Modeller is a valid spelling in the credits context and was not changed.",
            "Classification fine print remains low-confidence because S-Video capture limits legibility.",
        ],
        "manual_gaps": [
            "Full end-credits crawl should still be sampled periodically because one frame cannot prove every credit line.",
            "Mission failed/aborted result pages were not captured in this pass.",
            "Gameplay/watch HUD row relies on the user's latest hardware test instead of a fresh automated route.",
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"atlas": str(ATLAS), "report": str(REPORT), "rows": len(SPECS)}, indent=2))


if __name__ == "__main__":
    main()
