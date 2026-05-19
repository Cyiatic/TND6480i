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
BASE_ROM = ROOT / "artifacts" / "generated" / "g1diff3.z64"
GE_STOCK = ROOT / "artifacts" / "roms" / "GoldenEye 007 (USA).z64"
GE_480I = ROOT / "artifacts" / "roms" / "BASELINE_GE_480i_direct_from_stock.z64"
OUT_ROM = ROOT / "artifacts" / "generated" / "g1castrect1.z64"
REPORT = ROOT / "reports" / "tnd480i_g1castrect1_displaycast_rects_20260518.json"

# GE480i changes the display-cast scissor/fade-fill rectangles from the
# stock 440x330 front buffer to the 640x480 front buffer. g1diff3 already
# has the nearby cast z-buffer size words, but not these two fade rectangles.
PATCH_OFFSETS = (
    (0x4E914, "displaycast scissor packed upper"),
    (0x4E918, "displaycast scissor packed lower"),
    (0x4EA44, "displaycast fade-fill packed upper"),
    (0x4EA48, "displaycast fade-fill packed lower"),
)


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
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "make_bps_patch.py"),
        str(ROOT / "artifacts" / "roms" / "BASELINE_TND64_Expanded_direct_from_stock.z64"),
        str(target),
        str(patch),
        "--manifest",
        str(manifest),
        "--metadata",
        f"TND6480i {out_stem}: g1diff3 plus display-cast fade/scissor rectangles at 640x480.",
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)
    return {"patch": str(patch), "manifest": str(manifest)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=BASE_ROM)
    parser.add_argument("--ge-stock-rom", type=Path, default=GE_STOCK)
    parser.add_argument("--ge480-rom", type=Path, default=GE_480I)
    parser.add_argument("--out-rom", type=Path, default=OUT_ROM)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    base = bytearray(args.base_rom.read_bytes())
    ge_stock = args.ge_stock_rom.read_bytes()
    ge480 = args.ge480_rom.read_bytes()
    patches = []

    for offset, note in PATCH_OFFSETS:
        ge_old = word(ge_stock, offset)
        ge_new = word(ge480, offset)
        old = word(base, offset)
        if ge_old == ge_new:
            raise SystemExit(f"GE reference has no delta at 0x{offset:X}")
        if old not in (ge_old, ge_new):
            raise SystemExit(
                f"unexpected current word at 0x{offset:X}: 0x{old:08X}, "
                f"expected 0x{ge_old:08X} or 0x{ge_new:08X}"
            )
        write_word(base, offset, ge_new)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "ge_stock": f"0x{ge_old:08X}",
                "new": f"0x{ge_new:08X}",
                "changed": old != ge_new,
                "note": note,
            }
        )

    crc1, crc2 = update_n64_crc_6102(base)
    args.out_rom.parent.mkdir(parents=True, exist_ok=True)
    args.out_rom.write_bytes(base)
    bps = make_bps(args.out_rom, args.out_rom.stem)

    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(args.base_rom.read_bytes()),
        "out_rom": str(args.out_rom),
        "out_md5": md5(base),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": "Patch only the display-cast scissor/fade-fill rectangle packed dimensions to the GE480i 640x480 values.",
        "patches": patches,
        "save_outputs": copy_save_pair(args.base_rom, args.out_rom),
        "bps": bps,
        "do_not_promote_until_hardware_compared": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
