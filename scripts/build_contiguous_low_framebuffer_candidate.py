#!/usr/bin/env python3
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


ROOT = Path(__file__).resolve().parents[1]
BASE_ROM = ROOT / "artifacts" / "generated" / "g1mcfix4.z64"
BASELINE_TND = ROOT / "artifacts" / "roms" / "BASELINE_TND64_Expanded_direct_from_stock.z64"
OUT_ROM = ROOT / "artifacts" / "generated" / "g1contlow1.z64"
OUT_REPORT = ROOT / "reports" / "tnd480i_g1contlow1_contiguous_low_framebuffer_20260524.json"


PATCHES = [
    # Clear one contiguous 0x12c000 block starting at 0x80400000.
    (0x003D30, 0x3C048040, "clear contiguous low fb pair: base upper 0x8040"),
    (0x003D34, 0x00000000, "clear contiguous low fb pair: no lower OR needed"),
    (0x003D38, 0x00000000, "clear contiguous low fb pair: nop"),
    (0x003D3C, 0x3C050012, "clear contiguous low fb pair: size upper 0x0012"),
    (0x003D40, 0x34A5C000, "clear contiguous low fb pair: size lower 0xC000"),
    (0x003D44, 0x0C005F10, "clear contiguous low fb pair: bzero call"),
    (0x003D48, 0x00000000, "clear contiguous low fb pair: delay-slot nop"),
    (0x003D4C, 0x8FBF0014, "clear contiguous low fb pair: restore ra"),
    (0x003D50, 0x03E00008, "clear contiguous low fb pair: return"),
    (0x003D54, 0x27BD0018, "clear contiguous low fb pair: restore sp"),
    (0x003D58, 0x00000000, "clear contiguous low fb pair: remove second clear"),
    (0x003D5C, 0x00000000, "clear contiguous low fb pair: remove second clear"),
    (0x003D60, 0x00000000, "clear contiguous low fb pair: remove second clear epilogue"),
    (0x003D64, 0x00000000, "clear contiguous low fb pair: remove second clear epilogue"),
    (0x003D68, 0x00000000, "clear contiguous low fb pair: remove second clear epilogue"),
    # Keep fb0 at current stable 0x80400000, move fb1 from 0x8076A000 to
    # 0x80496000 so the pair is contiguous with GE480i's 0x96000 stride.
    (0x00658C, 0x3C058049, "fb1 upper = 0x8049"),
    (0x006590, 0x34A56000, "fb1 lower = 0x6000"),
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
        shutil.copy2(source, target)
        payload = target.read_bytes()
        outputs.append({"target": str(target), "bytes": len(payload), "md5": md5(payload)})
    return outputs


def make_bps(target):
    patch = ROOT / "artifacts" / "generated" / "TND6480i_g1contlow1_from_baseline_tnd.bps"
    manifest = ROOT / "reports" / "tnd6480i_g1contlow1_bps_manifest.json"
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
            "TND6480i g1contlow1: contiguous low 0x80400000/0x80496000 framebuffers on g1mcfix4.",
        ],
        check=True,
        cwd=ROOT,
    )
    return {"patch": str(patch), "manifest": str(manifest), "patch_md5": md5(patch.read_bytes())}


def stage(out_rom):
    stage_dir = ROOT / "artifacts" / "analogue_test"
    release_dir = ROOT / "artifacts" / "test_release" / "TND6480i_g1contlow1_contiguous_low_framebuffer_test"
    stage_dir.mkdir(parents=True, exist_ok=True)
    release_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for suffix in (".z64", ".sav", ".eep"):
        source = out_rom.with_suffix(suffix)
        for target in (
            stage_dir / f"G1CLOW1{suffix.upper()}",
            release_dir / f"TND6480I_G1CLOW1{suffix}",
        ):
            shutil.copy2(source, target)
            payload = target.read_bytes()
            outputs.append({"target": str(target), "bytes": len(payload), "md5": md5(payload)})
    return outputs


def main():
    base = BASE_ROM.read_bytes()
    data = bytearray(base)
    applied = []
    for offset, value, note in PATCHES:
        old = word(data, offset)
        write_word(data, offset, value)
        applied.append(
            {
                "offset": f"0x{offset:06X}",
                "old": f"0x{old:08X}",
                "new": f"0x{value:08X}",
                "changed": old != value,
                "note": note,
            }
        )

    crc1, crc2 = update_n64_crc_6102(data)
    OUT_ROM.write_bytes(data)
    report = {
        "variant": "g1contlow1",
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(OUT_ROM),
        "out_md5": md5(data),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": (
            "Diagnostic for Analogue text softness: keep the stable g1mcfix4 VI "
            "selector but make fb0/fb1 contiguous at GE480i's 0x96000 stride."
        ),
        "memory_model": {
            "framebuffer_0": "0x80400000-0x80495FFF",
            "framebuffer_1": "0x80496000-0x8052BFFF",
            "tlb_cache_8mb_expected": "unchanged from g1mcfix4: 0x806B6000-0x80769FFF",
        },
        "patches": applied,
        "changed_patch_count": sum(1 for row in applied if row["changed"]),
        "save_outputs": copy_save_pair(OUT_ROM),
        "stage_outputs": stage(OUT_ROM),
        "bps": make_bps(OUT_ROM),
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("variant", "out_rom", "out_md5", "header_crc", "changed_patch_count")}, indent=2))


if __name__ == "__main__":
    main()
