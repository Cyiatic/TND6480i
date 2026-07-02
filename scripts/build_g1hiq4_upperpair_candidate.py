#!/usr/bin/env python3
"""Build a narrow upper-pair framebuffer candidate from g1hiq3.

The rejected g1hqfb1 copied GE480i's framebuffer code blocks wholesale. This
candidate keeps the stable TND split-buffer selector/clear structure, but moves
fb0 so the two 640x480 buffers are the GE480i adjacent upper-RAM pair:

  fb0 0x806D4000-0x80769FFF
  fb1 0x8076A000-0x807FFFFF

The 90-page Expansion Pak TLB cache is moved to 0x80600000-0x806B3FFF so it
does not overlap either framebuffer.
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
OUT_ROM = ROOT / "artifacts" / "generated" / "g1hiq4_upperpair.z64"
OUT_REPORT = ROOT / "reports" / "tnd480i_g1hiq4_upperpair_20260525.json"
CONTRACT_REPORT = ROOT / "reports" / "measurement" / "render_contract_g1hiq4_upperpair_20260525.json"


PATCHES = [
    (0x00241C, 0x3C088020, "TLB/page-cache direct base upper: 0x80200000 before Expansion Pak delta"),
    (0x002420, 0x25080000, "TLB/page-cache direct base lower: 0x0000"),
    (0x003D30, 0x3C04806D, "clear fb0 base upper: 0x806D4000"),
    (0x003D34, 0x34844000, "clear fb0 base lower: 0x806D4000"),
    (0x006584, 0x3C04806D, "initialize fb0 base upper: 0x806D4000"),
    (0x006588, 0x34844000, "initialize fb0 base lower: 0x806D4000"),
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
        outputs.append({"target": str(target), "bytes": len(payload), "md5": md5(payload)})
    return outputs


def stage_short_names(out_rom):
    outputs = []
    stage_dir = ROOT / "artifacts" / "analogue_test"
    release_dir = ROOT / "artifacts" / "test_release" / "TND6480i_g1hiq4_upperpair"
    stage_dir.mkdir(parents=True, exist_ok=True)
    release_dir.mkdir(parents=True, exist_ok=True)
    for suffix in (".z64", ".sav", ".eep"):
        source = out_rom.with_suffix(suffix)
        if not source.exists():
            continue
        targets = [
            stage_dir / f"G1HIQ4{suffix.upper()}",
            release_dir / f"TND6480I_G1HIQ4{suffix}",
        ]
        for target in targets:
            shutil.copy2(source, target)
            payload = target.read_bytes()
            outputs.append({"target": str(target), "bytes": len(payload), "md5": md5(payload)})
    return outputs


def make_bps(out_rom):
    patch = ROOT / "artifacts" / "generated" / "TND6480i_g1hiq4_upperpair_from_baseline_tnd.bps"
    manifest = ROOT / "reports" / "tnd6480i_g1hiq4_upperpair_bps_manifest.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "make_bps_patch.py"),
            str(BASELINE_TND),
            str(out_rom),
            str(patch),
            "--manifest",
            str(manifest),
            "--metadata",
            "TND6480i g1hiq4: g1hiq3 with stable split-buffer code and GE480i adjacent upper framebuffers.",
        ],
        check=True,
        cwd=ROOT,
    )
    return {"patch": str(patch), "manifest": str(manifest), "patch_md5": md5(patch.read_bytes())}


def run_contract(out_rom):
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "verify_480i_render_contract.py"),
            str(BASE_ROM),
            str(out_rom),
            "--out-json",
            str(CONTRACT_REPORT),
        ],
        check=True,
        cwd=ROOT,
    )
    return str(CONTRACT_REPORT)


def main():
    base = BASE_ROM.read_bytes()
    data = bytearray(base)
    patches = []

    for offset, new_value, note in PATCHES:
        old_value = word(data, offset)
        write_word(data, offset, new_value)
        patches.append({
            "offset": f"0x{offset:06X}",
            "old": f"0x{old_value:08X}",
            "new": f"0x{new_value:08X}",
            "changed": old_value != new_value,
            "note": note,
        })

    crc1, crc2 = update_n64_crc_6102(data)
    OUT_ROM.parent.mkdir(parents=True, exist_ok=True)
    OUT_ROM.write_bytes(data)

    report = {
        "variant": "g1hiq4_upperpair",
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(OUT_ROM),
        "out_md5": md5(data),
        "size": len(data),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": (
            "Measurable text-quality candidate: keep g1hiq3's all-level stable "
            "TND split-framebuffer code and GE text/menu constants, but make the "
            "actual framebuffer placement match GE480i's adjacent upper-RAM pair."
        ),
        "memory_model": {
            "tlb_cache_8mb_expected": "0x80600000-0x806B3FFF",
            "gap_after_tlb": "0x2000 bytes before fb0",
            "framebuffer_0": "0x806D4000-0x80769FFF",
            "framebuffer_1": "0x8076A000-0x807FFFFF",
            "framebuffer_code_shape": "TND/g1hiq3 split explicit globals, not GE wholesale computed path",
        },
        "patches": patches,
        "changed_patch_count": sum(1 for patch in patches if patch["changed"]),
        "save_outputs": copy_save_pair(OUT_ROM),
        "stage_outputs": stage_short_names(OUT_ROM),
        "bps": make_bps(OUT_ROM),
        "contract_report": run_contract(OUT_ROM),
        "hardware_test_focus": [
            "Does Analogue 3D text sharpness now match GE480i while all levels still boot?",
            "Check pause/watch text, mission intro speech text, ammo/HUD, and encoder digits.",
            "Regression smoke: Bazaar/Labs, Wreck/Printworks, Party/City/The End, Hotel/Volcano, Tower/Boat.",
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
        "contract_report": report["contract_report"],
    }, indent=2))


if __name__ == "__main__":
    main()
