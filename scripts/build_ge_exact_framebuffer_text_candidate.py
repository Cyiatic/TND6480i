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
GE480I = ROOT / "artifacts" / "roms" / "BASELINE_GE_480i_direct_from_stock.z64"

OUT_ROM = ROOT / "artifacts" / "generated" / "g1gefb8060.z64"
OUT_REPORT = ROOT / "reports" / "tnd480i_g1gefb8060_framebuffer_text_quality_20260524.json"


COPY_GE480I_RANGES = [
    # VI front/back data init. GE480i uses contiguous 0x96000 framebuffers.
    (0x003C60, 0x003CB0, "GE480i contiguous g_ViFrontData/g_ViBackData buffer init"),
    # GE480i clear from 0x806D4000 through 0x807FFFFF as one 0x12C000 block.
    (0x003D24, 0x003D5C, "GE480i upper framebuffer clear"),
    # VI swap/update path: physical base + g_ViBackIndex * 0x96000.
    (0x0046B4, 0x0046F4, "GE480i contiguous framebuffer VI handoff"),
    # Store framebuffer globals as GE480i's upper-RAM pair:
    # A06D4000 and A076A000.
    (0x006584, 0x0065B8, "GE480i cfb globals at 0x806D4000/0x8076A000"),
]

DIRECT_WORD_PATCHES = [
    # Keep 90 TLB pages, but move page cache to 0x80600000 on Expansion Pak:
    # 0x80200000 + 0x00400000 expansion delta.
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


def make_bps(target):
    patch = ROOT / "artifacts" / "generated" / "TND6480i_g1gefb8060_from_baseline_tnd.bps"
    manifest = ROOT / "reports" / "tnd6480i_g1gefb8060_bps_manifest.json"
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
            "TND6480i g1gefb8060: g1mcfix4 with GE480i contiguous upper framebuffers and lower TLB cache.",
        ],
        check=True,
        cwd=ROOT,
    )
    return {"patch": str(patch), "manifest": str(manifest), "patch_md5": md5(patch.read_bytes())}


def stage_short_names(out_rom):
    stage_dir = ROOT / "artifacts" / "analogue_test"
    release_dir = ROOT / "artifacts" / "test_release" / "TND6480i_g1gefb8060_ge_framebuffer_text_test"
    stage_dir.mkdir(parents=True, exist_ok=True)
    release_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for suffix in (".z64", ".sav", ".eep"):
        source = out_rom.with_suffix(suffix)
        for target in (
            stage_dir / f"G1GEFB{suffix.upper()}",
            release_dir / f"TND6480I_G1GEFB8060{suffix}",
        ):
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


def main():
    base = BASE_ROM.read_bytes()
    ge480 = GE480I.read_bytes()
    data = bytearray(base)
    patches = []

    for start, end, note in COPY_GE480I_RANGES:
        for offset in range(start, end, 4):
            old = word(data, offset)
            new = word(ge480, offset)
            if old != new:
                write_word(data, offset, new)
            patches.append(
                {
                    "offset": f"0x{offset:06X}",
                    "old": f"0x{old:08X}",
                    "new": f"0x{new:08X}",
                    "changed": old != new,
                    "note": note,
                }
            )

    for offset, new, note in DIRECT_WORD_PATCHES:
        old = word(data, offset)
        write_word(data, offset, new)
        patches.append(
            {
                "offset": f"0x{offset:06X}",
                "old": f"0x{old:08X}",
                "new": f"0x{new:08X}",
                "changed": old != new,
                "note": note,
            }
        )

    crc1, crc2 = update_n64_crc_6102(data)
    OUT_ROM.parent.mkdir(parents=True, exist_ok=True)
    OUT_ROM.write_bytes(data)

    report = {
        "variant": "g1gefb8060",
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(OUT_ROM),
        "out_md5": md5(data),
        "size": len(data),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": (
            "Hardware text-quality diagnostic: restore GE480i's contiguous upper-RAM "
            "framebuffer presentation path while moving the TND page cache below those "
            "framebuffers to preserve all-level stability."
        ),
        "memory_model": {
            "tlb_cache_8mb_expected": "0x80600000-0x806B3FFF (90 pages * 0x2000)",
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
            "Mission intro and speech text sharpness versus GE480i.",
            "All-level boot regression check, especially Party/City/The End, Hotel/Volcano, Tower/Boat.",
            "Check for return of top/bottom flicker or prism failures.",
        ],
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("variant", "out_rom", "out_md5", "header_crc", "changed_patch_count")}, indent=2))


if __name__ == "__main__":
    main()
