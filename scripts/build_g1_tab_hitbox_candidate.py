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
BASE_ROM = ROOT / "artifacts" / "generated" / "g1fsorig1.z64"
GE_STOCK = ROOT / "artifacts" / "roms" / "GoldenEye 007 (USA).z64"
GE_480I = ROOT / "artifacts" / "roms" / "BASELINE_GE_480i_direct_from_stock.z64"
OUT_ROM = ROOT / "artifacts" / "generated" / "g1tabhit1.z64"
REPORT = ROOT / "reports" / "tnd480i_g1tabhit1_tab_hitbox_20260519.json"

# GE480i rewrites frontCheckCursorOnNextTab, not just its immediates. Without
# this range, the NEXT hitbox remains at the stock 240p Y band and overlaps the
# visible START tab after 480i tab scaling.
NEXT_TAB_HITBOX_RANGE = (0x3F0A8, 0x3F114)

ROUTE_PATCHES = {
    "timeout_to_mission_select": (0x3FF34, 0x24040018, 0x24040007),
    "mission_select_force_button_accept": (0x42D98, 0x1040002A, 0x00000000),
    "difficulty_accept": (0x43554, 0x11600012, 0x00000000),
    "difficulty_route_agent_to_briefing": (0x43560, 0x24010003, 0x24010004),
    "force_background_page": (0x4A14C, 0x00002025, 0x24040001),
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
        outputs.append({"source": str(source), "target": str(target), "bytes": len(payload), "md5": md5(payload)})
    return outputs


def patch_hitbox(rom, ge_stock, ge480):
    start, end = NEXT_TAB_HITBOX_RANGE
    patches = []
    for offset in range(start, end, 4):
        old = word(rom, offset)
        stock = word(ge_stock, offset)
        new = word(ge480, offset)
        write_word(rom, offset, new)
        patches.append({
            "offset": f"0x{offset:X}",
            "old": f"0x{old:08X}",
            "ge_stock": f"0x{stock:08X}",
            "new": f"0x{new:08X}",
            "changed": old != new,
            "stock_differs_from_ge480i": stock != new,
        })
    return patches


def add_background_route(base_rom, base, out_rom):
    rom = bytearray(base)
    patches = []
    for key, (offset, expected, new) in ROUTE_PATCHES.items():
        old = word(rom, offset)
        if old != expected:
            raise ValueError(f"{key}: expected 0x{expected:08X} at 0x{offset:X}, got 0x{old:08X}")
        write_word(rom, offset, new)
        patches.append({"key": key, "offset": f"0x{offset:X}", "old": f"0x{old:08X}", "new": f"0x{new:08X}"})
    crc1, crc2 = update_n64_crc_6102(rom)
    route_rom = out_rom.with_name(out_rom.stem + "btn0cpg1.z64")
    route_rom.write_bytes(rom)
    return {
        "out_rom": str(route_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "route_patches": patches,
        "save_outputs": copy_save_pair(base_rom, route_rom),
    }


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
            f"TND6480i {out_stem}: g1fsorig1 plus GE480i NEXT tab hitbox function.",
        ],
        check=True,
        cwd=ROOT,
    )
    return {"patch": str(patch), "manifest": str(manifest), "patch_md5": md5(patch.read_bytes())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=BASE_ROM)
    parser.add_argument("--out-rom", type=Path, default=OUT_ROM)
    parser.add_argument("--ge-stock-rom", type=Path, default=GE_STOCK)
    parser.add_argument("--ge480-rom", type=Path, default=GE_480I)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    base = bytearray(args.base_rom.read_bytes())
    ge_stock = args.ge_stock_rom.read_bytes()
    ge480 = args.ge480_rom.read_bytes()
    patches = patch_hitbox(base, ge_stock, ge480)
    crc1, crc2 = update_n64_crc_6102(base)

    args.out_rom.parent.mkdir(parents=True, exist_ok=True)
    args.out_rom.write_bytes(base)

    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(args.base_rom.read_bytes()),
        "out_rom": str(args.out_rom),
        "out_md5": md5(base),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": "Move NEXT tab hit detection/highlight to the GE480i tab band so hovering START no longer highlights NEXT.",
        "patch_range": {"start": f"0x{NEXT_TAB_HITBOX_RANGE[0]:X}", "end": f"0x{NEXT_TAB_HITBOX_RANGE[1]:X}"},
        "patches": patches,
        "changed_patch_count": sum(1 for item in patches if item["changed"]),
        "save_outputs": copy_save_pair(args.base_rom, args.out_rom),
        "routes": {"background_page": add_background_route(args.base_rom, base, args.out_rom)},
        "bps": make_bps(args.out_rom, args.out_rom.stem),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out_rom": str(args.out_rom), "out_md5": report["out_md5"], "report": str(args.report)}, indent=2))


if __name__ == "__main__":
    main()
