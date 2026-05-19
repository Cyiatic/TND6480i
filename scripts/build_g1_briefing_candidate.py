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
BASE_ROM = ROOT / "artifacts" / "generated" / "g1hct2.z64"
GE_STOCK = ROOT / "artifacts" / "roms" / "GoldenEye 007 (USA).z64"
GE_480I = ROOT / "artifacts" / "roms" / "BASELINE_GE_480i_direct_from_stock.z64"

BRIEF_WRAP_RANGE = (0x454E8, 0x45604)
BRIEFING_MENU0A_RANGE = (0x4A000, 0x4C500)


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
            f"TND6480i {out_stem}: g1hct2 plus GE480i briefing/objective menu0A coordinate deltas.",
        ],
        check=True,
        cwd=ROOT,
    )
    return {"patch": str(patch), "manifest": str(manifest)}


def collect_offsets(ge_stock, ge480):
    ranges = [
        ("brief_wrap_thresholds", BRIEF_WRAP_RANGE),
        ("briefing_menu0A", BRIEFING_MENU0A_RANGE),
    ]
    offsets = []
    for source, (start, end) in ranges:
        for offset in range(start, end, 4):
            ge_old = word(ge_stock, offset)
            ge_new = word(ge480, offset)
            if ge_old == ge_new:
                continue
            offsets.append((offset, source, ge_old, ge_new))
    return offsets


def build_variant(name, base_rom, ge_stock_rom, ge480_rom):
    base_bytes = base_rom.read_bytes()
    rom = bytearray(base_bytes)
    ge_stock = ge_stock_rom.read_bytes()
    ge480 = ge480_rom.read_bytes()
    patches = []
    skipped = []

    for offset, source, ge_old, ge_new in collect_offsets(ge_stock, ge480):
        old = word(rom, offset)
        if old == ge_new:
            patches.append(
                {
                    "offset": f"0x{offset:X}",
                    "source": source,
                    "old": f"0x{old:08X}",
                    "ge_stock": f"0x{ge_old:08X}",
                    "new": f"0x{ge_new:08X}",
                    "changed": False,
                    "note": "already matched GE480i",
                }
            )
            continue
        if old != ge_old:
            skipped.append(
                {
                    "offset": f"0x{offset:X}",
                    "source": source,
                    "old": f"0x{old:08X}",
                    "ge_stock": f"0x{ge_old:08X}",
                    "ge480": f"0x{ge_new:08X}",
                    "reason": "current word is TND-specific, not the GE stock baseline",
                }
            )
            continue
        write_word(rom, offset, ge_new)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "source": source,
                "old": f"0x{old:08X}",
                "ge_stock": f"0x{ge_old:08X}",
                "new": f"0x{ge_new:08X}",
                "changed": True,
                "note": "GE480i briefing/objective coordinate delta",
            }
        )

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = ROOT / "artifacts" / "generated" / f"{name}.z64"
    out_rom.write_bytes(rom)
    report = {
        "base_rom": str(base_rom),
        "base_md5": md5(base_bytes),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": "Apply only GE480i briefing/objective menu0A coordinate and wrap-threshold deltas on top of g1hct2.",
        "ranges": [
            {"name": "brief_wrap_thresholds", "start": f"0x{BRIEF_WRAP_RANGE[0]:X}", "end": f"0x{BRIEF_WRAP_RANGE[1]:X}"},
            {"name": "briefing_menu0A", "start": f"0x{BRIEFING_MENU0A_RANGE[0]:X}", "end": f"0x{BRIEFING_MENU0A_RANGE[1]:X}"},
        ],
        "patches": patches,
        "skipped": skipped,
        "changed_patch_count": sum(1 for patch in patches if patch["changed"]),
        "skipped_count": len(skipped),
        "save_outputs": copy_save_pair(base_rom, out_rom),
        "bps": make_bps(out_rom, name),
        "do_not_promote_until_hardware_compared": True,
    }
    report_path = ROOT / "reports" / f"tnd480i_{name}_briefing_candidate_20260519.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report_path, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=BASE_ROM)
    parser.add_argument("--ge-stock-rom", type=Path, default=GE_STOCK)
    parser.add_argument("--ge480-rom", type=Path, default=GE_480I)
    parser.add_argument("--variant", default="g1hbrf1")
    args = parser.parse_args()

    for path in (args.base_rom, args.ge_stock_rom, args.ge480_rom):
        if not path.exists():
            raise SystemExit(f"missing ROM: {path}")

    report_path, report = build_variant(args.variant, args.base_rom, args.ge_stock_rom, args.ge480_rom)
    print(json.dumps({"report": str(report_path), "out_rom": report["out_rom"], "out_md5": report["out_md5"]}, indent=2))


if __name__ == "__main__":
    main()
