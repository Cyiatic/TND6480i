#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


ROOT = Path(__file__).resolve().parents[1]
BASE_ROM = ROOT / "artifacts" / "generated" / "g1mcfix4.z64"
GE_STOCK = ROOT / "artifacts" / "roms" / "GoldenEye 007 (USA).z64"
GE_480I = ROOT / "artifacts" / "roms" / "BASELINE_GE_480i_direct_from_stock.z64"
SAFE_DIFF_REPORT = ROOT / "reports" / "safe_unported_ge480i_code_words_g1mcfix4_20260524.json"


TEXT_VIEWPORT_FOLLOWUP_PATCHES = [
    (0x0BB790, "alternate viewport width return"),
    (0x0BB83C, "alternate viewport left return"),
    (0x0BB874, "alternate viewport height return"),
    (0x0BB9A0, "alternate viewport top return"),
    (0x0BB9D8, "alternate viewport top return"),
]

HUD_NUMERIC_Y_PATCHES = [
    (0x08AE9C, "in-game numeric/HUD text row 0 Y"),
    (0x08AEF0, "in-game numeric/HUD text row 1 Y"),
    (0x08AF3C, "in-game numeric/HUD text label row 0 Y"),
    (0x08AF9C, "in-game numeric/HUD text row 2 Y"),
    (0x08AFF0, "in-game numeric/HUD text row 3 Y"),
    (0x08B03C, "in-game numeric/HUD text label row 1 Y"),
    (0x08B09C, "in-game numeric/HUD text row 4 Y"),
    (0x08B0F0, "in-game numeric/HUD text row 5 Y"),
]

# GE480i changes this block as a family. The constants are primarily
# thresholds, text positions, scissor/rectangle dimensions, and menu-related
# overlay bounds used by the in-game overlay/front route. The user-visible
# symptom is that mission intro/speech text and some overlays still look like
# stock-res output on Analogue 3D even when emulator framebuffers look fine.
INGAME_OVERLAY_RANGE = (0x043F94, 0x044B54)

MENU_VIDEO_BUFFER_PATCHES = [
    (0x035920, "force menu video-buffer pointer upper to 0x8076"),
    (0x035924, "force menu video-buffer pointer lower to 0xA000"),
    (0x03592C, "skip stock 64-byte aligned allocation mask"),
]

MENU_BUFFER_SIZE_PATCHES = [
    (0x03FC90, "front/menu allocation size upper"),
    (0x03FC94, "front/menu allocation size lower"),
    (0x040540, "front/menu reset size upper"),
    (0x040544, "front/menu reset size lower"),
]

VARIANTS = {
    "g1hiq1": {
        "short_name": "G1HIQ1",
        "purpose": (
            "Hardware text-quality candidate: port the untouched GE480i "
            "in-game overlay and HUD numeric coordinate families, without "
            "changing the menu video-buffer allocator."
        ),
        "groups": ["viewport", "hud_numeric_y", "ingame_overlay"],
    },
    "g1hiq2": {
        "short_name": "G1HIQ2",
        "purpose": (
            "Riskier hardware text-quality diagnostic: g1hiq1 plus the "
            "GE480i menu video-buffer pointer and menu buffer-size constants. "
            "Use only if g1hiq1 keeps pause/watch or front text visibly soft."
        ),
        "groups": [
            "viewport",
            "hud_numeric_y",
            "ingame_overlay",
            "menu_video_buffer",
            "menu_buffer_size",
        ],
    },
}


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def copy_save_pair(base_rom, out_rom):
    outputs = []
    for suffix in (".sav", ".eep"):
        source = base_rom.with_suffix(suffix)
        target = out_rom.with_suffix(suffix)
        if not source.exists():
            outputs.append({"source": str(source), "target": str(target), "missing": True})
            continue
        shutil.copy2(source, target)
        payload = target.read_bytes()
        outputs.append(
            {
                "source": str(source),
                "target": str(target),
                "bytes": len(payload),
                "md5": md5(payload),
            }
        )
    return outputs


def make_bps(target, out_stem):
    patch = ROOT / "artifacts" / "generated" / f"TND6480i_{out_stem}_from_baseline_tnd.bps"
    manifest = ROOT / "reports" / f"tnd6480i_{out_stem}_bps_manifest.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "make_bps_patch.py"),
            str(ROOT / "artifacts" / "roms" / "BASELINE_TND64_Expanded_direct_from_stock.z64"),
            str(target),
            str(patch),
            "--manifest",
            str(manifest),
            "--metadata",
            f"TND6480i {out_stem}: hardware text-quality follow-up on g1mcfix4.",
        ],
        check=True,
        cwd=ROOT,
    )
    return {"patch": str(patch), "manifest": str(manifest), "patch_md5": md5(patch.read_bytes())}


def load_safe_diff_rows():
    report = json.loads(SAFE_DIFF_REPORT.read_text(encoding="utf-8"))
    rows = {}
    for row in report["rows"]:
        rows[int(row["offset"], 16)] = row
    return rows


def collect_group_offsets(group, safe_rows):
    if group == "viewport":
        return TEXT_VIEWPORT_FOLLOWUP_PATCHES
    if group == "hud_numeric_y":
        return HUD_NUMERIC_Y_PATCHES
    if group == "menu_video_buffer":
        return MENU_VIDEO_BUFFER_PATCHES
    if group == "menu_buffer_size":
        return MENU_BUFFER_SIZE_PATCHES
    if group == "ingame_overlay":
        start, end = INGAME_OVERLAY_RANGE
        offsets = []
        for offset in sorted(safe_rows):
            if start <= offset <= end:
                offsets.append((offset, "GE480i in-game overlay/front text coordinate family"))
        return offsets
    raise ValueError(f"unknown group {group}")


def apply_variant(data, ge_stock, ge480, variant, safe_rows):
    patches = []
    for group in VARIANTS[variant]["groups"]:
        for offset, note in collect_group_offsets(group, safe_rows):
            old = word(data, offset)
            ge_old = word(ge_stock, offset)
            ge_new = word(ge480, offset)
            if ge_old == ge_new:
                raise ValueError(f"GE stock and GE480i unexpectedly match at 0x{offset:X}")
            if old == ge_new:
                patches.append(
                    {
                        "offset": f"0x{offset:06X}",
                        "group": group,
                        "note": note,
                        "old": f"0x{old:08X}",
                        "ge_stock": f"0x{ge_old:08X}",
                        "new": f"0x{ge_new:08X}",
                        "changed": False,
                    }
                )
                continue
            if old != ge_old:
                raise ValueError(
                    f"current word at 0x{offset:X} is neither GE stock nor GE480i: "
                    f"current=0x{old:08X} ge_stock=0x{ge_old:08X} ge480i=0x{ge_new:08X}"
                )
            write_word(data, offset, ge_new)
            patches.append(
                {
                    "offset": f"0x{offset:06X}",
                    "group": group,
                    "note": note,
                    "old": f"0x{old:08X}",
                    "ge_stock": f"0x{ge_old:08X}",
                    "new": f"0x{ge_new:08X}",
                    "changed": True,
                    "ge480i_disasm": safe_rows.get(offset, {}).get("ge480i_disasm"),
                }
            )
    return patches


def stage_short_name(out_rom, short_name):
    stage_dir = ROOT / "artifacts" / "analogue_test"
    stage_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for suffix in (".Z64", ".sav", ".eep"):
        source = out_rom.with_suffix(suffix.lower() if suffix != ".Z64" else ".z64")
        target = stage_dir / f"{short_name}{suffix}"
        if not source.exists():
            outputs.append({"source": str(source), "target": str(target), "missing": True})
            continue
        shutil.copy2(source, target)
        payload = target.read_bytes()
        outputs.append({"source": str(source), "target": str(target), "bytes": len(payload), "md5": md5(payload)})
    return outputs


def build_variant(name, args, safe_rows):
    base_bytes = args.base_rom.read_bytes()
    data = bytearray(base_bytes)
    ge_stock = args.ge_stock_rom.read_bytes()
    ge480 = args.ge480_rom.read_bytes()

    patches = apply_variant(data, ge_stock, ge480, name, safe_rows)
    crc1, crc2 = update_n64_crc_6102(data)

    out_rom = ROOT / "artifacts" / "generated" / f"{name}.z64"
    out_rom.parent.mkdir(parents=True, exist_ok=True)
    out_rom.write_bytes(data)
    save_outputs = copy_save_pair(args.base_rom, out_rom)

    report = {
        "variant": name,
        "short_name": VARIANTS[name]["short_name"],
        "base_rom": str(args.base_rom),
        "base_md5": md5(base_bytes),
        "out_rom": str(out_rom),
        "out_md5": md5(data),
        "size": len(data),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": VARIANTS[name]["purpose"],
        "groups": VARIANTS[name]["groups"],
        "patches": patches,
        "changed_patch_count": sum(1 for patch in patches if patch["changed"]),
        "save_outputs": save_outputs,
        "analogue_stage_outputs": stage_short_name(out_rom, VARIANTS[name]["short_name"]),
        "bps": make_bps(out_rom, name),
        "hardware_test_focus": [
            "Compare mission intro text and in-game speech text sharpness against GE480i on Analogue 3D.",
            "Compare ammo/numeric HUD sharpness and placement against GE480i.",
            "Open the pause/watch menu and compare small text sharpness against GE480i.",
            "Smoke Bazaar, Labs, Wreck/Printworks, and one previously stable level for regression.",
        ],
        "emulator_limit": (
            "Do not accept emulator framebuffer screenshots as proof of text sharpness; "
            "the 2026-05-24 Analogue result contradicted emulator pause comparisons."
        ),
    }
    report_path = ROOT / "reports" / f"tnd480i_{name}_hardware_text_quality_20260524.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report_path, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=BASE_ROM)
    parser.add_argument("--ge-stock-rom", type=Path, default=GE_STOCK)
    parser.add_argument("--ge480-rom", type=Path, default=GE_480I)
    parser.add_argument("--variants", nargs="*", default=list(VARIANTS))
    args = parser.parse_args()

    for path in (args.base_rom, args.ge_stock_rom, args.ge480_rom, SAFE_DIFF_REPORT):
        if not path.exists():
            raise SystemExit(f"missing input: {path}")

    safe_rows = load_safe_diff_rows()
    reports = []
    for name in args.variants:
        if name not in VARIANTS:
            raise SystemExit(f"unknown variant: {name}")
        report_path, report = build_variant(name, args, safe_rows)
        reports.append(
            {
                "variant": name,
                "out_rom": report["out_rom"],
                "out_md5": report["out_md5"],
                "header_crc": report["header_crc"],
                "report": str(report_path),
                "changed_patch_count": report["changed_patch_count"],
                "short_name": report["short_name"],
            }
        )
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
