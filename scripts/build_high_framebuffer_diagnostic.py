#!/usr/bin/env python3
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
OUT_ROM = ROOT / "artifacts" / "generated" / "g1hifb1.z64"
OUT_REPORT = ROOT / "reports" / "tnd480i_g1hifb1_high_framebuffer_diag_20260524.json"


PATCHES = [
    (0x006584, 0x3C048076, "framebuffer global fb0 upper -> 0x8076A000"),
    (0x006588, 0x3484A000, "framebuffer global fb0 lower -> 0x8076A000"),
    (0x00658C, 0x00802825, "fb1 = fb0 for single high-buffer diagnostic"),
    (0x006590, 0x3C02A000, "uncached segment upper"),
    (0x006594, 0x00827025, "fb0 uncached pointer"),
    (0x006598, 0x3C018002, "global pointer base"),
    (0x00659C, 0xAC2E417C, "store cfb_16[0]"),
    (0x0065A0, 0x00A27825, "fb1 uncached pointer"),
    (0x0065A4, 0x03E00008, "return"),
    (0x0065A8, 0xAC2F4180, "store cfb_16[1] in delay slot"),
    (0x0065AC, 0x00000000, "clear old fb1 calculation"),
    (0x0065B0, 0x00000000, "clear old return"),
    (0x0065B4, 0x00000000, "clear old delay slot"),
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
        if not source.exists():
            outputs.append({"source": str(source), "target": str(target), "missing": True})
            continue
        shutil.copy2(source, target)
        payload = target.read_bytes()
        outputs.append({
            "source": str(source),
            "target": str(target),
            "bytes": len(payload),
            "md5": md5(payload),
        })
    return outputs


def stage_outputs(out_rom):
    stage_dir = ROOT / "artifacts" / "analogue_test"
    release_dir = ROOT / "artifacts" / "test_release" / "TND6480i_g1hifb1_high_framebuffer_diag"
    stage_dir.mkdir(parents=True, exist_ok=True)
    release_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for suffix in (".z64", ".sav", ".eep"):
        source = out_rom.with_suffix(suffix)
        for target in (
            stage_dir / f"G1HIFB1{suffix.upper()}",
            release_dir / f"TND6480I_G1HIFB1{suffix}",
        ):
            if not source.exists():
                outputs.append({"source": str(source), "target": str(target), "missing": True})
                continue
            shutil.copy2(source, target)
            payload = target.read_bytes()
            outputs.append({
                "source": str(source),
                "target": str(target),
                "bytes": len(payload),
                "md5": md5(payload),
            })
    return outputs


def make_bps(target):
    patch = ROOT / "artifacts" / "generated" / "TND6480i_g1hifb1_from_baseline_tnd.bps"
    manifest = ROOT / "reports" / "tnd6480i_g1hifb1_bps_manifest.json"
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
            "TND6480i g1hifb1: g1hiq3 with both cfb globals forced to 0x8076A000 for Analogue text-quality diagnosis.",
        ],
        check=True,
        cwd=ROOT,
    )
    return {"patch": str(patch), "manifest": str(manifest), "patch_md5": md5(patch.read_bytes())}


def main():
    for path in (BASE_ROM, BASELINE_TND):
        if not path.exists():
            raise SystemExit(f"missing input: {path}")

    base = BASE_ROM.read_bytes()
    data = bytearray(base)
    applied = []

    for offset, new, note in PATCHES:
        old = word(data, offset)
        write_word(data, offset, new)
        applied.append({
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
        "variant": "g1hifb1",
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(OUT_ROM),
        "out_md5": md5(data),
        "size": len(data),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": (
            "Narrow Analogue 3D diagnostic: keep the latest GE480i text/menu parity candidate, "
            "but force both framebuffer globals to the high 0x8076A000 buffer. If text becomes "
            "GE480i-sharp, the remaining defect is the split low/high framebuffer handoff. If it "
            "stays soft, the problem is upstream of framebuffer placement."
        ),
        "expected_tradeoffs": [
            "This is single-buffered and may tear or flicker; that is acceptable for this diagnostic.",
            "Do not promote as final unless it also survives an all-level stability pass.",
        ],
        "patches": applied,
        "changed_patch_count": sum(1 for item in applied if item["changed"]),
        "save_outputs": copy_save_pair(OUT_ROM),
        "stage_outputs": stage_outputs(OUT_ROM),
        "bps": make_bps(OUT_ROM),
        "hardware_test_focus": [
            "Analogue 3D: compare pause/watch text against GE480i.",
            "Analogue 3D: compare mission intro text and ammo/HUD numerals against GE480i.",
            "N64/SC64 smoke only: confirm it reaches gameplay before any deeper test.",
        ],
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "variant": report["variant"],
        "out_rom": report["out_rom"],
        "out_md5": report["out_md5"],
        "header_crc": report["header_crc"],
        "changed_patch_count": report["changed_patch_count"],
        "stage_short_rom": str(ROOT / "artifacts" / "analogue_test" / "G1HIFB1.Z64"),
        "report": str(OUT_REPORT),
    }, indent=2))


if __name__ == "__main__":
    main()
