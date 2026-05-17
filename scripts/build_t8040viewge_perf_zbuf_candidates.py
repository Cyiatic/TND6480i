#!/usr/bin/env python3
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


OUT_DIR = Path("artifacts/generated")
PACK_DIR = Path("artifacts/analogue_test")
REPORT_DIR = Path("reports")
BASELINE_TND = Path("artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64")
BASE_ROM = Path("artifacts/generated/t8040viewge.z64")
BASE_SAVE = Path("artifacts/generated/t8040viewge.sav")

ZBUF_OFFSETS = {
    "resolution_width": 0x106ED4,
    "resolution_height": 0x106EE4,
    "lowres_width": 0x106EF0,
    "single_height": 0x106F10,
    "split_height": 0x106F24,
}

WORDS = {
    "width_640_t7": 0x240F0280,
    "height_480_t8": 0x241801E0,
    "width_640_t9": 0x24190280,
    "height_480_t0": 0x240801E0,
    "height_480_t1": 0x240901E0,
    "width_440_t7": 0x240F01B8,
    "height_330_t8": 0x2418014A,
    "width_320_t9": 0x24190140,
    "height_240_t0": 0x240800F0,
    "height_120_t1": 0x24090078,
    "height_360_t8": 0x24180168,
    "height_360_t0": 0x24080168,
    "height_360_t1": 0x24090168,
}

SPECS = [
    {
        "name": "t8040vz360",
        "pack_stem": "TNDZ360",
        "purpose": (
            "Performance canary from current t8040viewge: keep 640-wide rows, "
            "but lower all tested stage z/depth heights to 360. This saves "
            "153,600 bytes versus each 640x480 depth buffer while retaining "
            "wide rows for 480i geometry."
        ),
        "patches": {
            "resolution_width": "width_640_t7",
            "resolution_height": "height_360_t8",
            "lowres_width": "width_640_t9",
            "single_height": "height_360_t0",
            "split_height": "height_360_t1",
        },
        "priority": 1,
    },
    {
        "name": "t8040vz640",
        "pack_stem": "TNDZ640",
        "purpose": (
            "Performance canary from current t8040viewge: keep 640-wide rows, "
            "but restore stock-ish heights: resolution 330, single-player 240, "
            "split 120. This is cheaper than z360 and tests whether the current "
            "visual path actually needs full-height depth."
        ),
        "patches": {
            "resolution_width": "width_640_t7",
            "resolution_height": "height_330_t8",
            "lowres_width": "width_640_t9",
            "single_height": "height_240_t0",
            "split_height": "height_120_t1",
        },
        "priority": 2,
    },
    {
        "name": "t8040vzstk",
        "pack_stem": "TNDZSTK",
        "purpose": (
            "Performance canary from current t8040viewge: restore the stock "
            "z/depth allocation footprint, 440x330 for the resolution path and "
            "320x240/120 for low-res paths. This is not expected to be visually "
            "final, but it should reveal whether the 640-wide depth rows are the "
            "remaining performance cost."
        ),
        "patches": {
            "resolution_width": "width_440_t7",
            "resolution_height": "height_330_t8",
            "lowres_width": "width_320_t9",
            "single_height": "height_240_t0",
            "split_height": "height_120_t1",
        },
        "priority": 3,
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def copy_save_to_stems(out_rom, pack_stem):
    writes = []
    if not BASE_SAVE.exists():
        return writes

    save = BASE_SAVE.read_bytes()
    eep_512 = save[:512] if len(save) >= 512 else save + b"\0" * (512 - len(save))
    eep_2048 = save if len(save) >= 2048 else save + b"\0" * (2048 - len(save))

    outputs = [
        (out_rom.with_suffix(".sav"), save),
        (out_rom.with_suffix(".eep"), eep_2048),
        (PACK_DIR / f"{pack_stem}.SAV", save),
        (PACK_DIR / f"{pack_stem}.EEP", eep_512),
    ]
    for path, payload in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        writes.append({"path": str(path), "bytes": len(payload), "md5": md5(payload)})
    return writes


def run_python(args):
    result = subprocess.run([sys.executable, *args], text=True, capture_output=True, check=True)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"stdout": result.stdout, "stderr": result.stderr}


def build_one(base, spec):
    rom = bytearray(base)
    patches = []
    for field, word_key in spec["patches"].items():
        offset = ZBUF_OFFSETS[field]
        old = word(rom, offset)
        new = WORDS[word_key]
        write_word(rom, offset, new)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "field": field,
                "old": f"0x{old:08X}",
                "new": f"0x{new:08X}",
                "word_key": word_key,
                "changed": old != new,
            }
        )

    crc1, crc2 = update_n64_crc_6102(rom)

    out_rom = OUT_DIR / f"{spec['name']}.z64"
    out_rom.parent.mkdir(parents=True, exist_ok=True)
    out_rom.write_bytes(rom)

    pack_rom = PACK_DIR / f"{spec['pack_stem']}.Z64"
    pack_rom.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out_rom, pack_rom)

    save_outputs = copy_save_to_stems(out_rom, spec["pack_stem"])

    bps_path = OUT_DIR / f"TND6480i_{spec['name']}_from_baseline_tnd.bps"
    bps_manifest = REPORT_DIR / f"tnd6480i_{spec['name']}_bps_manifest.json"
    bps = run_python(
        [
            "scripts/make_bps_patch.py",
            str(BASELINE_TND),
            str(out_rom),
            str(bps_path),
            "--manifest",
            str(bps_manifest),
            "--metadata",
            spec["purpose"],
        ]
    )

    return {
        "name": spec["name"],
        "pack_stem": spec["pack_stem"],
        "purpose": spec["purpose"],
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "pack_rom": str(pack_rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": patches,
        "save_outputs": save_outputs,
        "bps_patch": str(bps_path),
        "bps_patch_md5": bps.get("patch_md5"),
        "bps_manifest": str(bps_manifest),
        "priority": spec["priority"],
        "test_note": (
            "Analogue/SC64 performance canary only. Compare Wreck/Printworks speed "
            "against TNDVIABL first, then spot-check Bazaar/Labs/Party/Hotel/Volcano "
            "for visual or boot regressions."
        ),
    }


def main():
    if not BASE_ROM.exists():
        raise FileNotFoundError(BASE_ROM)
    base = BASE_ROM.read_bytes()
    reports = [build_one(base, spec) for spec in SPECS]
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = REPORT_DIR / "tnd480i_t8040viewge_perf_zbuf_candidates_20260517.json"
    summary_path.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), "candidates": reports}, indent=2))


if __name__ == "__main__":
    main()
