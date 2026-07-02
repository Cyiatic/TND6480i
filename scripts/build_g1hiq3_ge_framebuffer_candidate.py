#!/usr/bin/env python3
"""Build a coherent GE480i framebuffer-path diagnostic from g1hiq3.

This differs from g1hifb1.  g1hifb1 only forced both framebuffer globals to a
single high buffer, which intentionally broke normal double-buffer behavior.
This candidate keeps the current text/menu parity work from g1hiq3 and copies
GE480i's paired upper-RAM framebuffer init/swap/global path as a coherent unit.
The TLB page cache is moved below those framebuffers to avoid overlap.
"""

import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


ROOT = Path(__file__).resolve().parents[1]
BASE_ROM = ROOT / "artifacts" / "generated" / "g1hiq3_gegate.z64"
BASELINE_TND = ROOT / "artifacts" / "roms" / "BASELINE_TND64_Expanded_direct_from_stock.z64"
GE480I = ROOT / "artifacts" / "roms" / "BASELINE_GE_480i_direct_from_stock.z64"

OUT_ROM = ROOT / "artifacts" / "generated" / "g1hqfb1.z64"
OUT_REPORT = ROOT / "reports" / "tnd480i_g1hqfb1_ge_framebuffer_text_quality_20260524.json"

COPY_GE480I_RANGES = [
    (0x003C60, 0x003CB0, "GE480i paired front/back VI buffer init"),
    (0x003D24, 0x003D5C, "GE480i upper-framebuffer clear range"),
    (0x0046B4, 0x0046F4, "GE480i contiguous framebuffer VI handoff"),
    (0x006584, 0x0065B8, "GE480i cfb globals at 0x806D4000/0x8076A000"),
]

DIRECT_WORD_PATCHES = [
    (0x00241C, 0x3C088020, "TLB/page-cache base upper: 0x80200000 before expansion delta"),
    (0x002420, 0x25080000, "TLB/page-cache base lower: 0x0000"),
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def copy_save_pair(out_rom):
    outputs = []
    for suffix in (".sav", ".eep"):
        source = BASE_ROM.with_suffix(suffix)
        target = out_rom.with_suffix(suffix)
        if source.exists():
            shutil.copy2(source, target)
            payload = target.read_bytes()
            outputs.append({"target": str(target), "bytes": len(payload), "md5": md5(payload)})
    return outputs


def stage_short_names(out_rom):
    stage_dir = ROOT / "artifacts" / "analogue_test"
    release_dir = ROOT / "artifacts" / "test_release" / "TND6480i_g1hqfb1_ge_framebuffer_text_test"
    stage_dir.mkdir(parents=True, exist_ok=True)
    release_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for suffix in (".z64", ".sav", ".eep"):
        source = out_rom.with_suffix(suffix)
        if not source.exists():
            continue
        for target in (
            stage_dir / f"G1HQFB1{suffix.upper()}",
            release_dir / f"TND6480I_G1HQFB1{suffix}",
        ):
            shutil.copy2(source, target)
            payload = target.read_bytes()
            outputs.append({"target": str(target), "bytes": len(payload), "md5": md5(payload)})
    return outputs


def make_bps(target):
    patch = ROOT / "artifacts" / "generated" / "TND6480i_g1hqfb1_from_baseline_tnd.bps"
    manifest = ROOT / "reports" / "tnd6480i_g1hqfb1_bps_manifest.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "make_bps_patch.py"),
            str(BASELINE_TND),
            str(target),
            str(patch),
            "--manifest",
            str(manifest),
            "--metadata",
            "TND6480i g1hqfb1: g1hiq3 with coherent GE480i upper framebuffer path and lowered TLB cache.",
        ],
        check=True,
        cwd=ROOT,
    )
    return {"patch": str(patch), "manifest": str(manifest), "patch_md5": md5(patch.read_bytes())}


def main():
    base = BASE_ROM.read_bytes()
    ge480 = GE480I.read_bytes()
    data = bytearray(base)
    patches = []

    for start, end, note in COPY_GE480I_RANGES:
        for offset in range(start, end, 4):
            old = word(data, offset)
            new = word(ge480, offset)
            write_word(data, offset, new)
            patches.append({
                "offset": f"0x{offset:06X}",
                "old": f"0x{old:08X}",
                "new": f"0x{new:08X}",
                "changed": old != new,
                "note": note,
            })

    for offset, new, note in DIRECT_WORD_PATCHES:
        old = word(data, offset)
        write_word(data, offset, new)
        patches.append({
            "offset": f"0x{offset:06X}",
            "old": f"0x{old:08X}",
            "new": f"0x{new:08X}",
            "changed": old != new,
            "note": note,
        })

    crc1, crc2 = update_n64_crc_6102(data)
    OUT_ROM.parent.mkdir(parents=True, exist_ok=True)
    OUT_ROM.write_bytes(data)

    report = {
        "variant": "g1hqfb1",
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(OUT_ROM),
        "out_md5": md5(data),
        "size": len(data),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": (
            "Current text-quality diagnostic: preserve g1hiq3's source-mapped "
            "GE480i text/menu parity, but make the framebuffer presentation model "
            "match GE480i coherently instead of using the stable split-buffer model."
        ),
        "memory_model": {
            "tlb_cache_8mb_expected": "0x80600000-0x806B3FFF",
            "framebuffer_0": "0x806D4000-0x80769FFF",
            "framebuffer_1": "0x8076A000-0x807FFFFF",
        },
        "patches": patches,
        "changed_patch_count": sum(1 for patch in patches if patch["changed"]),
        "save_outputs": copy_save_pair(OUT_ROM),
        "stage_outputs": stage_short_names(OUT_ROM),
        "bps": make_bps(OUT_ROM),
        "hardware_test_focus": [
            "Analogue 3D pause/watch text sharpness versus GE480i.",
            "Mission intro/speech text and ammo text sharpness versus GE480i.",
            "Regression check for level boot/stability and front-end corruption.",
        ],
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "variant": report["variant"],
        "out_rom": report["out_rom"],
        "out_md5": report["out_md5"],
        "header_crc": report["header_crc"],
        "changed_patch_count": report["changed_patch_count"],
    }, indent=2))


if __name__ == "__main__":
    main()
