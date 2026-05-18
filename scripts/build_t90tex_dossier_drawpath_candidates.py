#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


GE_STOCK = Path("artifacts/roms/GoldenEye 007 (USA).z64")
GE_480I = Path("artifacts/roms/BASELINE_GE_480i_direct_from_stock.z64")


RANGES = {
    "modepos": [
        (0x4232C, 0x42B24, "corrected setCursorPOSforMode + constructor_menu06_modesel GE480i constants"),
    ],
    "missionhelper": [
        (0x42F1C, 0x42F88, "GE480i helper blob before constructor_menu07_missionsel"),
    ],
    "missionlabel": [
        (0x43148, 0x43154, "mission label y/x offsets"),
        (0x431E0, 0x431E8, "mission label y/x offsets repeat"),
    ],
}


CANDIDATES = [
    {
        "name": "txmodepos2",
        "range_keys": ["modepos"],
        "purpose": "Corrected GE480i mode-select constructor coordinate constants.",
    },
    {
        "name": "txmissionhelper",
        "range_keys": ["missionhelper"],
        "purpose": "GE480i mission-select helper blob only; tests cursor/grid helper behavior.",
    },
    {
        "name": "txmissionfull",
        "range_keys": ["missionhelper", "missionlabel"],
        "purpose": "GE480i mission-select helper plus mission label offsets.",
    },
    {
        "name": "txdossierdraw2",
        "range_keys": ["modepos", "missionhelper", "missionlabel"],
        "purpose": "Corrected mode-select and mission-select dossier draw-path constants.",
    },
]


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
        outputs.append({"source": str(source), "target": str(target), "bytes": len(payload), "md5": md5(payload)})
    return outputs


def collect_patches(spec, ge_stock, ge_480i):
    patches = []
    seen = set()
    for key in spec["range_keys"]:
        for start, end, note in RANGES[key]:
            for offset in range(start, end, 4):
                old = word(ge_stock, offset)
                new = word(ge_480i, offset)
                if old == new or offset in seen:
                    continue
                seen.add(offset)
                patches.append({"offset": offset, "new": new, "source_old": old, "range": key, "note": note})
    return sorted(patches, key=lambda patch: patch["offset"])


def build_one(spec, base_rom, base, ge_stock, ge_480i, out_dir, prefix):
    rom = bytearray(base)
    applied = []
    for patch in collect_patches(spec, ge_stock, ge_480i):
        offset = patch["offset"]
        old = word(rom, offset)
        write_word(rom, offset, patch["new"])
        applied.append(
            {
                "offset": f"0x{offset:X}",
                "range": patch["range"],
                "old": f"0x{old:08X}",
                "ge_stock": f"0x{patch['source_old']:08X}",
                "new": f"0x{patch['new']:08X}",
                "changed": old != patch["new"],
                "note": patch["note"],
            }
        )
    crc1, crc2 = update_n64_crc_6102(rom)
    out_name = f"{prefix}{spec['name']}" if prefix else spec["name"]
    out_rom = out_dir / f"{out_name}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": out_name,
        "purpose": spec["purpose"],
        "base_rom": str(base_rom),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patch_count": len(applied),
        "changed_patch_count": sum(1 for patch in applied if patch["changed"]),
        "patches": applied,
        "save_outputs": copy_save_pair(base_rom, out_rom),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/t90texstk.z64"))
    parser.add_argument("--ge-stock-rom", type=Path, default=GE_STOCK)
    parser.add_argument("--ge480-rom", type=Path, default=GE_480I)
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/generated"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/tnd480i_t90tex_dossier_drawpath_candidates_20260518.json"),
    )
    parser.add_argument("--prefix", default="")
    args = parser.parse_args()

    for path in (args.base_rom, args.ge_stock_rom, args.ge480_rom):
        if not path.exists():
            raise SystemExit(f"missing ROM: {path}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    base = args.base_rom.read_bytes()
    ge_stock = args.ge_stock_rom.read_bytes()
    ge_480i = args.ge480_rom.read_bytes()
    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(base),
        "ge_stock_rom": str(args.ge_stock_rom),
        "ge480_rom": str(args.ge480_rom),
        "purpose": "Corrected front.c function-range dossier draw-path probes; every useful probe must be hardware-captured against GE480i.",
        "candidates": [
            build_one(spec, args.base_rom, base, ge_stock, ge_480i, args.out_dir, args.prefix)
            for spec in CANDIDATES
        ],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
