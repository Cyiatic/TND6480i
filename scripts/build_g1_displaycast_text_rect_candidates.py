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
BASE_ROM = ROOT / "artifacts" / "generated" / "g1hlim1.z64"
GE_STOCK = ROOT / "artifacts" / "roms" / "GoldenEye 007 (USA).z64"
GE_480I = ROOT / "artifacts" / "roms" / "BASELINE_GE_480i_direct_from_stock.z64"

PATCH_SETS = {
    "g1hct2": {
        "purpose": "Apply the remaining GE480i display-cast second/third credit-row text constants on top of g1hiftr1.",
        "offsets": (
            (0x4ED24, "display-cast second-row credit text center X"),
            (0x4ED3C, "display-cast second-row credit text Y"),
            (0x4ED44, "display-cast second-row credit text clip bottom offset"),
            (0x4ED5C, "display-cast second-row credit text render Y"),
            (0x4EE14, "display-cast third-row credit text center X"),
            (0x4EE2C, "display-cast third-row credit text Y"),
            (0x4EE34, "display-cast third-row credit text clip bottom offset"),
            (0x4EE4C, "display-cast third-row credit text render Y"),
        ),
    },
    "g1hift1": {
        "purpose": "Apply GE480i display-cast model/interface centering plus credit text constants on top of g1hlim1.",
        "offsets": (
            (0x4D040, "display-cast center X for first overlay"),
            (0x4D044, "display-cast center Y for first overlay"),
            (0x4D11C, "display-cast center X for second overlay"),
            (0x4D120, "display-cast center Y for second overlay"),
            (0x4EB20, "display-cast credit text center X"),
            (0x4EB38, "display-cast credit text first row Y"),
            (0x4EB40, "display-cast credit text clip bottom offset"),
            (0x4EB58, "display-cast credit text first render Y"),
        ),
    },
    "g1hiftr1": {
        "purpose": "Apply all remaining GE480i display-cast center, text, and fade/scissor rectangle words on top of g1hlim1.",
        "offsets": (
            (0x4D040, "display-cast center X for first overlay"),
            (0x4D044, "display-cast center Y for first overlay"),
            (0x4D11C, "display-cast center X for second overlay"),
            (0x4D120, "display-cast center Y for second overlay"),
            (0x4E914, "display-cast scissor packed upper"),
            (0x4E918, "display-cast scissor packed lower"),
            (0x4EA44, "display-cast fade-fill packed upper"),
            (0x4EA48, "display-cast fade-fill packed lower"),
            (0x4EB20, "display-cast credit text center X"),
            (0x4EB38, "display-cast credit text first row Y"),
            (0x4EB40, "display-cast credit text clip bottom offset"),
            (0x4EB58, "display-cast credit text first render Y"),
        ),
    },
    "g1hrect1": {
        "purpose": "Apply only the GE480i display-cast fade/scissor rectangles on top of g1hlim1.",
        "offsets": (
            (0x4E914, "display-cast scissor packed upper"),
            (0x4E918, "display-cast scissor packed lower"),
            (0x4EA44, "display-cast fade-fill packed upper"),
            (0x4EA48, "display-cast fade-fill packed lower"),
        ),
    },
    "g1htxt1": {
        "purpose": "Apply only the GE480i display-cast credit text center/Y constants on top of g1hlim1.",
        "offsets": (
            (0x4EB20, "display-cast credit text center X"),
            (0x4EB38, "display-cast credit text first row Y"),
            (0x4EB40, "display-cast credit text clip bottom offset"),
            (0x4EB58, "display-cast credit text first render Y"),
        ),
    },
    "g1htxr1": {
        "purpose": "Apply GE480i display-cast credit text constants plus fade/scissor rectangles on top of g1hlim1.",
        "offsets": (
            (0x4E914, "display-cast scissor packed upper"),
            (0x4E918, "display-cast scissor packed lower"),
            (0x4EA44, "display-cast fade-fill packed upper"),
            (0x4EA48, "display-cast fade-fill packed lower"),
            (0x4EB20, "display-cast credit text center X"),
            (0x4EB38, "display-cast credit text first row Y"),
            (0x4EB40, "display-cast credit text clip bottom offset"),
            (0x4EB58, "display-cast credit text first render Y"),
        ),
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
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "make_bps_patch.py"),
        str(ROOT / "artifacts" / "roms" / "BASELINE_TND64_Expanded_direct_from_stock.z64"),
        str(target),
        str(patch),
        "--manifest",
        str(manifest),
        "--metadata",
        f"TND6480i {out_stem}: g1hlim1 display-cast text/rectangle probe.",
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)
    return {"patch": str(patch), "manifest": str(manifest)}


def build_variant(name, base_rom, ge_stock_rom, ge480_rom):
    spec = PATCH_SETS[name]
    base_bytes = base_rom.read_bytes()
    rom = bytearray(base_bytes)
    ge_stock = ge_stock_rom.read_bytes()
    ge480 = ge480_rom.read_bytes()
    patches = []

    for offset, note in spec["offsets"]:
        ge_old = word(ge_stock, offset)
        ge_new = word(ge480, offset)
        old = word(rom, offset)
        if ge_old == ge_new:
            raise SystemExit(f"GE reference has no delta at 0x{offset:X}")
        if old not in (ge_old, ge_new):
            raise SystemExit(
                f"{name}: unexpected current word at 0x{offset:X}: 0x{old:08X}, "
                f"expected 0x{ge_old:08X} or 0x{ge_new:08X}"
            )
        write_word(rom, offset, ge_new)
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

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = ROOT / "artifacts" / "generated" / f"{name}.z64"
    out_rom.write_bytes(rom)
    report = {
        "base_rom": str(base_rom),
        "base_md5": md5(base_bytes),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": spec["purpose"],
        "patches": patches,
        "changed_patch_count": sum(1 for patch in patches if patch["changed"]),
        "save_outputs": copy_save_pair(base_rom, out_rom),
        "bps": make_bps(out_rom, name),
        "do_not_promote_until_hardware_compared": True,
    }
    report_path = ROOT / "reports" / f"tnd480i_{name}_displaycast_text_rect_20260519.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report_path, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=BASE_ROM)
    parser.add_argument("--ge-stock-rom", type=Path, default=GE_STOCK)
    parser.add_argument("--ge480-rom", type=Path, default=GE_480I)
    parser.add_argument("--variant", choices=sorted(PATCH_SETS), action="append")
    args = parser.parse_args()

    variants = args.variant or sorted(PATCH_SETS)
    output = {}
    for name in variants:
        report_path, report = build_variant(name, args.base_rom, args.ge_stock_rom, args.ge480_rom)
        output[name] = {
            "report": str(report_path),
            "out_rom": report["out_rom"],
            "out_md5": report["out_md5"],
        }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
