#!/usr/bin/env python3
import json
import struct
import subprocess
import sys
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


OUT_DIR = Path("artifacts/generated")
REPORT_DIR = Path("reports")
BASELINE_TND = Path("artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64")
BASE_ROM = Path("artifacts/generated/game_h460_top10_stock_dossier_tlbpages58_007label_current.z64")
SAVE_SOURCE = Path(r"C:\Users\codex\Documents\007 - Tomorrow Never Dies (USA).sav")

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
    "height_330_t0": 0x2408014A,
    "height_360_t8": 0x24180168,
    "height_360_t0": 0x24080168,
    "height_360_t1": 0x24090168,
    "height_240_t8": 0x241800F0,
    "height_240_t1": 0x240900F0,
}

SPECS = [
    {
        "name": "game_h460_top10_stock_dossier_tlbpages58_zbuf640hstock_007label_current",
        "purpose": (
            "Keep 640-wide z-buffer rows, but restore stock z-buffer heights. This "
            "tests whether the current full 640x480 stage z-buffer is starving or "
            "colliding with stage memory while preserving horizontal 480i depth layout."
        ),
        "patches": {
            "resolution_width": "width_640_t7",
            "resolution_height": "height_330_t8",
            "lowres_width": "width_640_t9",
            "single_height": "height_240_t0",
            "split_height": "height_120_t1",
        },
        "expected_allocations": {
            "resolution": "640x330 -> 422,400 bytes + 64",
            "single_player_lowres": "640x240 -> 307,200 bytes + 64",
            "current_full_reference": "640x480 -> 614,400 bytes + 64",
        },
        "hardware_priority": 1,
    },
    {
        "name": "game_h460_top10_stock_dossier_tlbpages58_zbuf640h360_007label_current",
        "purpose": (
            "Middle-ground z-buffer footprint: keep 640-wide rows and use 360-high "
            "buffers. This saves 153,600 bytes versus full 640x480 while avoiding "
            "the very short 240/330 bottom-depth cutoff."
        ),
        "patches": {
            "resolution_width": "width_640_t7",
            "resolution_height": "height_360_t8",
            "lowres_width": "width_640_t9",
            "single_height": "height_360_t0",
            "split_height": "height_360_t1",
        },
        "expected_allocations": {
            "all_paths": "640x360 -> 460,800 bytes + 64",
            "current_full_reference": "640x480 -> 614,400 bytes + 64",
        },
        "hardware_priority": 2,
    },
    {
        "name": "game_h460_top10_stock_dossier_tlbpages58_zbufstock_007label_current",
        "purpose": (
            "Most conservative memory reclamation: restore all z-buffer allocation "
            "dimensions to stock. This may regress 480i depth composition, but it "
            "is useful if the 640-wide candidates still leave Party/City/Credits dead."
        ),
        "patches": {
            "resolution_width": "width_440_t7",
            "resolution_height": "height_330_t8",
            "lowres_width": "width_320_t9",
            "single_height": "height_240_t0",
            "split_height": "height_120_t1",
        },
        "expected_allocations": {
            "resolution": "440x330 -> 290,400 bytes + 64",
            "single_player_lowres": "320x240 -> 153,600 bytes + 64",
            "current_full_reference": "640x480 -> 614,400 bytes + 64",
        },
        "hardware_priority": 3,
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def copy_save(out_rom):
    if not SAVE_SOURCE.exists():
        return []
    save = SAVE_SOURCE.read_bytes()
    eep = save if len(save) >= 2048 else save + b"\0" * (2048 - len(save))
    writes = []
    for path, payload in [(out_rom.with_suffix(".sav"), save), (out_rom.with_suffix(".eep"), eep)]:
        path.write_bytes(payload)
        writes.append({"path": str(path), "bytes": len(payload), "md5": md5(payload)})
    return writes


def run_python(args):
    result = subprocess.run([sys.executable, *args], text=True, capture_output=True, check=True)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"stdout": result.stdout, "stderr": result.stderr}


def build_one(spec):
    base = BASE_ROM.read_bytes()
    rom = bytearray(base)
    patches = []
    for key, word_key in spec["patches"].items():
        offset = ZBUF_OFFSETS[key]
        old = word(rom, offset)
        new = WORDS[word_key]
        write_word(rom, offset, new)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "field": key,
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
    save_writes = copy_save(out_rom)

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

    report = {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": patches,
        "expected_allocations": spec["expected_allocations"],
        "save_writes": save_writes,
        "bps_patch": str(bps_path),
        "bps_patch_md5": bps.get("patch_md5"),
        "bps_manifest": str(bps_manifest),
        "hardware_priority": spec["hardware_priority"],
        "test_note": (
            "Upload only one z-buffer candidate at a time. Test Party/Credits/City "
            "load, Hotel/Volcano prism, Tower/Boat intros, Labs encoder/door, then "
            "Wreck/Bridge/Press/Alaska controls."
        ),
    }
    report_path = REPORT_DIR / f"tnd480i_{spec['name']}_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    reports = [build_one(spec) for spec in SPECS]
    summary = REPORT_DIR / "tnd480i_stage_zbuf_candidates_20260517.json"
    summary.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
