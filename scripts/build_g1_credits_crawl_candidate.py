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
BASE_ROM = ROOT / "artifacts" / "generated" / "g1tabhit1.z64"
GE_STOCK = ROOT / "artifacts" / "roms" / "GoldenEye 007 (USA).z64"
GE_480I = ROOT / "artifacts" / "roms" / "BASELINE_GE_480i_direct_from_stock.z64"
OUT_ROM = ROOT / "artifacts" / "generated" / "g1cred1.z64"
REPORT = ROOT / "reports" / "tnd480i_g1cred1_credits_crawl_20260519.json"

# GE480i credits crawl deltas from bondview.c:sub_GAME_7F088CD8. These are
# separate from the intro display-cast credits; they affect the Cuba/The End
# rolling credits crawl text columns.
CREDITS_CRAWL_OFFSETS = [
    (0xBD870, "default first-column x: 220 -> 320"),
    (0xBD878, "default second-column x: 220 -> 320"),
    (0xBD930, "pre-scan explicit first-column x: x -> x + 100"),
    (0xBD95C, "pre-scan explicit second-column x: x -> x + 100"),
    (0xBDA00, "render explicit first-column x: x -> x + 100"),
    (0xBDB80, "render explicit second-column x: x -> x + 100"),
]


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
            f"TND6480i {out_stem}: g1tabhit1 plus GE480i rolling credits crawl column deltas.",
        ],
        check=True,
        cwd=ROOT,
    )
    return {"patch": str(patch), "manifest": str(manifest), "patch_md5": md5(patch.read_bytes())}


def apply_credits_crawl_patch(rom, ge_stock, ge480):
    patches = []
    for offset, note in CREDITS_CRAWL_OFFSETS:
        old = word(rom, offset)
        ge_old = word(ge_stock, offset)
        ge_new = word(ge480, offset)
        if ge_old == ge_new:
            raise ValueError(f"GE stock and GE480i unexpectedly match at 0x{offset:X}")
        if old not in (ge_old, ge_new):
            raise ValueError(
                f"current word at 0x{offset:X} is neither GE stock nor GE480i: "
                f"current=0x{old:08X} ge_stock=0x{ge_old:08X} ge480=0x{ge_new:08X}"
            )
        write_word(rom, offset, ge_new)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "note": note,
                "old": f"0x{old:08X}",
                "ge_stock": f"0x{ge_old:08X}",
                "new": f"0x{ge_new:08X}",
                "changed": old != ge_new,
            }
        )
    return patches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=BASE_ROM)
    parser.add_argument("--out-rom", type=Path, default=OUT_ROM)
    parser.add_argument("--ge-stock-rom", type=Path, default=GE_STOCK)
    parser.add_argument("--ge480-rom", type=Path, default=GE_480I)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    for path in (args.base_rom, args.ge_stock_rom, args.ge480_rom):
        if not path.exists():
            raise SystemExit(f"missing ROM: {path}")

    base_bytes = args.base_rom.read_bytes()
    rom = bytearray(base_bytes)
    patches = apply_credits_crawl_patch(rom, args.ge_stock_rom.read_bytes(), args.ge480_rom.read_bytes())
    crc1, crc2 = update_n64_crc_6102(rom)

    args.out_rom.parent.mkdir(parents=True, exist_ok=True)
    args.out_rom.write_bytes(rom)

    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(base_bytes),
        "out_rom": str(args.out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": "Apply the GE480i rolling end-credits crawl x-coordinate deltas missing from g1tabhit1.",
        "scope": "Only the credits crawl function words at 0xBD870-0xBDB80 are changed; gameplay/dossier code is untouched.",
        "patches": patches,
        "changed_patch_count": sum(1 for item in patches if item["changed"]),
        "save_outputs": copy_save_pair(args.base_rom, args.out_rom),
        "bps": make_bps(args.out_rom, args.out_rom.stem),
        "do_not_promote_until_hardware_compared": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out_rom": str(args.out_rom), "out_md5": report["out_md5"], "report": str(args.report)}, indent=2))


if __name__ == "__main__":
    main()
