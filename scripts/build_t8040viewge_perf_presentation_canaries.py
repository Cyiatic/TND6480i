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
REPORT = Path("reports/tnd480i_t8040viewge_perf_presentation_canaries_20260517.json")


CANDIDATES = [
    {
        "name": "t8040vbufstk",
        "pack_stem": "TNDBUF",
        "purpose": (
            "Performance canary from t8040viewge: keep the 480i VI/framebuffer "
            "and visual-fit baseline, but restore only the front/menu viSetBuf "
            "width/height constants to stock TND. If a stale front buffer size "
            "is feeding g_ViBackData->bufx/bufy into gameplay, this should reduce "
            "RDP color-image/fill workload without broadly reverting visuals."
        ),
        "groups": {
            "front_visetbuf_stock": [
                (0x4DAEC, "front viSetBuf/menu width"),
                (0x4DAF4, "front viSetBuf/menu height"),
            ],
        },
    },
    {
        "name": "t8040vblstk",
        "pack_stem": "TNDBLIT",
        "purpose": (
            "Performance canary from t8040viewge: keep the 480i VI/framebuffer "
            "and all-level gameplay baseline, but restore the shared title/sniper "
            "texture blitter geometry cluster to stock TND. This tests whether "
            "the GE-sized shared blitter workload is what makes Wreck/Printworks "
            "abnormally slow even after internal gameplay dimensions are restored."
        ),
        "groups": {
            "shared_texture_setup_stock": [
                (0x4FDEC, "shared title/sniper texture setup upper"),
                (0x4FDFC, "shared title/sniper texture rectangle target width"),
                (0x4FE34, "shared title/sniper height load upper"),
                (0x4FE3C, "shared title/sniper texture setup lower"),
                (0x4FE44, "shared title/sniper height load/use"),
                (0x4FF00, "shared title/sniper texture rectangle lower width"),
            ],
            "shared_strip_row_stride_stock": [
                (0x500EC, "shared title/sniper negative-x strip step"),
                (0x500FC, "shared title/sniper negative-x strip step"),
                (0x50148, "shared title/sniper positive-x strip step"),
                (0x50168, "shared title/sniper positive-x strip step"),
                (0x501AC, "shared title/sniper source row loop limit"),
                (0x501B4, "shared title/sniper source stride"),
            ],
        },
    },
    {
        "name": "t8040vbufblstk",
        "pack_stem": "TNDBOTH",
        "purpose": (
            "Performance canary from t8040viewge: combine the stock front viSetBuf "
            "constants with the stock shared title/sniper blitter geometry cluster. "
            "Use only after the isolated canaries are classified."
        ),
        "groups": {
            "front_visetbuf_stock": [
                (0x4DAEC, "front viSetBuf/menu width"),
                (0x4DAF4, "front viSetBuf/menu height"),
            ],
            "shared_texture_setup_stock": [
                (0x4FDEC, "shared title/sniper texture setup upper"),
                (0x4FDFC, "shared title/sniper texture rectangle target width"),
                (0x4FE34, "shared title/sniper height load upper"),
                (0x4FE3C, "shared title/sniper texture setup lower"),
                (0x4FE44, "shared title/sniper height load/use"),
                (0x4FF00, "shared title/sniper texture rectangle lower width"),
            ],
            "shared_strip_row_stride_stock": [
                (0x500EC, "shared title/sniper negative-x strip step"),
                (0x500FC, "shared title/sniper negative-x strip step"),
                (0x50148, "shared title/sniper positive-x strip step"),
                (0x50168, "shared title/sniper positive-x strip step"),
                (0x501AC, "shared title/sniper source row loop limit"),
                (0x501B4, "shared title/sniper source stride"),
            ],
        },
    },
]


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


def build_one(spec, base, stock):
    rom = bytearray(base)
    patches = []
    for group, entries in spec["groups"].items():
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
    out_rom = OUT_DIR / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)

    pack_rom = PACK_DIR / f"{spec['pack_stem']}.Z64"
    shutil.copyfile(out_rom, pack_rom)
    save_outputs = copy_saves(out_rom, spec["pack_stem"])

    bps_path = OUT_DIR / f"TND6480i_{spec['name']}_from_baseline_tnd.bps"
    bps_manifest = Path(f"reports/tnd6480i_{spec['name']}_bps_manifest.json")
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
        "stock_source_rom": str(STOCK_ROM),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "pack_rom": str(pack_rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": patches,
        "changed_patch_count": sum(1 for patch in patches if patch["changed"]),
        "save_outputs": save_outputs,
        "bps_patch": str(bps_path),
        "bps_patch_md5": bps.get("patch_md5"),
        "bps_manifest": str(bps_manifest),
        "test_note": (
            "Use direct-stage Wreck first as a performance canary. Do not promote "
            "a full ROM until Wreck speed and Bazaar/Labs visual stability are both checked."
        ),
    }


def main():
    if not BASE_ROM.exists():
        raise SystemExit(f"missing base ROM: {BASE_ROM}")
    if not STOCK_ROM.exists():
        raise SystemExit(f"missing stock ROM: {STOCK_ROM}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PACK_DIR.mkdir(parents=True, exist_ok=True)

    base = BASE_ROM.read_bytes()
    stock = STOCK_ROM.read_bytes()
    reports = [build_one(spec, base, stock) for spec in CANDIDATES]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
