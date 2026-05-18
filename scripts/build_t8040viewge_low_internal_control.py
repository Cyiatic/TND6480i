#!/usr/bin/env python3
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/t8040viewge.z64")
BASE_SAVE = Path("artifacts/generated/t8040viewge.sav")
STOCK_ROM = Path("artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64")
BASELINE_TND = Path("artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64")
OUT_DIR = Path("artifacts/generated")
PACK_DIR = Path("artifacts/analogue_test")
REPORT = Path("reports/tnd480i_t8040viewge_low_internal_control_20260517.json")

SPEC = {
    "name": "t8040vlowint",
    "pack_stem": "TNDLOWI",
    "purpose": (
        "Diagnostic only: keep the current t8040viewge all-level-boot base and "
        "its 480i VI/framebuffer plumbing, but restore the gameplay internal "
        "render, viewport, and z/depth dimensions as a coherent stock-sized set. "
        "If this is faster, the slowdown is the true high internal render path. "
        "If it is still slow, look below gameplay dimensions at VI/framebuffer/RDP "
        "state. This is not expected to be a final 480i visual candidate."
    ),
    "groups": {
        "direct_render": [
            (0x4F354, "direct render dimensions table 0"),
        ],
        "global_xy_helpers": [
            (0xBB730, "getWidth320or440 low-res return"),
            (0xBB740, "getWidth320or440 hi-res return"),
            (0xBB754, "getHeight330or240 low-res return"),
            (0xBB764, "getHeight330or240 hi-res return"),
        ],
        "camera_viewports": [
            (0xBB7A4, "cameraBufferToggle viewport width"),
            (0xBB89C, "camera widescreen viewport height"),
            (0xBB8B8, "camera cinema viewport height"),
            (0xBB8C0, "camera fullscreen viewport height"),
            (0xBB8FC, "widescreen animated viewport height offset"),
            (0xBB944, "cinema animated viewport height offset"),
            (0xBBA60, "widescreen animated viewport top offset"),
            (0xBBAA8, "cinema animated viewport top offset"),
        ],
        "normal_viewports": [
            (0xBB7C0, "non-camera widescreen viewport width"),
            (0xBB7D4, "non-camera default viewport width branch delay"),
            (0xBB7DC, "non-camera cinema viewport width"),
            (0xBB7E0, "non-camera fallback viewport width"),
            (0xBB91C, "non-camera default viewport height"),
            (0xBB954, "non-camera fallback viewport height"),
            (0xBBA80, "non-camera default viewport top"),
        ],
        "stage_z_depth": [
            (0x106ED4, "stage z/depth resolution width"),
            (0x106EE4, "stage z/depth resolution height"),
            (0x106EF0, "stage z/depth low-res width"),
            (0x106F10, "stage z/depth single-player height"),
            (0x106F24, "stage z/depth split/multiplayer height"),
        ],
    },
}


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def run_python(args):
    result = subprocess.run([sys.executable, *args], text=True, capture_output=True, check=True)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"stdout": result.stdout, "stderr": result.stderr}


def copy_saves(out_rom, pack_stem):
    if not BASE_SAVE.exists():
        return []
    save = BASE_SAVE.read_bytes()
    eep_512 = save[:512] if len(save) >= 512 else save + b"\0" * (512 - len(save))
    eep_2048 = save if len(save) >= 2048 else save + b"\0" * (2048 - len(save))
    outputs = [
        (out_rom.with_suffix(".sav"), save),
        (out_rom.with_suffix(".eep"), eep_2048),
        (PACK_DIR / f"{pack_stem}.SAV", save),
        (PACK_DIR / f"{pack_stem}.EEP", eep_512),
    ]
    writes = []
    for path, data in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        writes.append({"path": str(path), "bytes": len(data), "md5": md5(data)})
    return writes


def main():
    base = BASE_ROM.read_bytes()
    stock = STOCK_ROM.read_bytes()
    rom = bytearray(base)
    patches = []

    for group, entries in SPEC["groups"].items():
        for offset, note in entries:
            old = word(rom, offset)
            new = word(stock, offset)
            write_word(rom, offset, new)
            patches.append(
                {
                    "group": group,
                    "offset": f"0x{offset:X}",
                    "old": f"0x{old:08X}",
                    "new": f"0x{new:08X}",
                    "note": note,
                    "changed": old != new,
                }
            )

    crc1, crc2 = update_n64_crc_6102(rom)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_rom = OUT_DIR / f"{SPEC['name']}.z64"
    out_rom.write_bytes(rom)

    PACK_DIR.mkdir(parents=True, exist_ok=True)
    pack_rom = PACK_DIR / f"{SPEC['pack_stem']}.Z64"
    shutil.copyfile(out_rom, pack_rom)
    save_outputs = copy_saves(out_rom, SPEC["pack_stem"])

    bps_path = OUT_DIR / f"TND6480i_{SPEC['name']}_from_baseline_tnd.bps"
    bps_manifest = Path(f"reports/tnd6480i_{SPEC['name']}_bps_manifest.json")
    bps = run_python(
        [
            "scripts/make_bps_patch.py",
            str(BASELINE_TND),
            str(out_rom),
            str(bps_path),
            "--manifest",
            str(bps_manifest),
            "--metadata",
            SPEC["purpose"],
        ]
    )

    report = {
        "name": SPEC["name"],
        "pack_stem": SPEC["pack_stem"],
        "purpose": SPEC["purpose"],
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "stock_source_rom": str(STOCK_ROM),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "pack_rom": str(pack_rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": patches,
        "save_outputs": save_outputs,
        "bps_patch": str(bps_path),
        "bps_patch_md5": bps.get("patch_md5"),
        "bps_manifest": str(bps_manifest),
        "test_note": (
            "Performance diagnostic only. Compare Wreck/Printworks speed to TNDVIABL. "
            "Expected visual result is stock-ish or not-true-480i; the useful signal is "
            "whether speed recovers without blue rendering."
        ),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
