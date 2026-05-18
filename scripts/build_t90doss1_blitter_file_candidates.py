#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018

ROUTES = [
    ("05", 0x05, "file select / save folders"),
    ("06", 0x06, "mode select"),
]

CANDIDATES = [
    {
        "name": "dmyrw1",
        "purpose": "t90doss1my16 plus only the first GE480i texture-rectangle width word.",
        "patches": [
            (0x4FDFC, 0x3C0AE49F, "GE480i texture rectangle target width"),
        ],
    },
    {
        "name": "dmyrw2",
        "purpose": "t90doss1my16 plus only the second GE480i texture-rectangle width word.",
        "patches": [
            (0x4FF00, 0x3C0E009F, "GE480i texture rectangle lower width"),
        ],
    },
    {
        "name": "dmywrect",
        "purpose": "t90doss1my16 plus only the GE480i texture-rectangle width words.",
        "patches": [
            (0x4FDFC, 0x3C0AE49F, "GE480i texture rectangle target width"),
            (0x4FF00, 0x3C0E009F, "GE480i texture rectangle lower width"),
        ],
    },
    {
        "name": "dmywtile",
        "purpose": "t90doss1my16 plus only the GE480i tile setup width words.",
        "patches": [
            (0x4FDEC, 0x3C170713, "GE480i title/menu texture setup upper"),
            (0x4FE3C, 0x36F7F006, "GE480i title/menu texture setup lower"),
        ],
    },
    {
        "name": "dmytexw",
        "purpose": "t90doss1my16 plus GE480i horizontal texture setup for the shared title/menu backdrop blitter.",
        "patches": [
            (0x4FDEC, 0x3C170713, "GE480i title/menu texture setup upper"),
            (0x4FDFC, 0x3C0AE49F, "GE480i texture rectangle target width"),
            (0x4FE3C, 0x36F7F006, "GE480i title/menu texture setup lower"),
            (0x4FF00, 0x3C0E009F, "GE480i texture rectangle lower width"),
        ],
    },
    {
        "name": "dmytex430",
        "purpose": "t90doss1my16 plus full GE480i 430-line texture setup; keeps current strip steps/row loop/stride.",
        "patches": [
            (0x4FDEC, 0x3C170713, "GE480i title/menu texture setup upper"),
            (0x4FDFC, 0x3C0AE49F, "GE480i texture rectangle target width"),
            (0x4FE34, 0x3C0143D7, "GE480i title/menu draw height float upper 430.0"),
            (0x4FE3C, 0x36F7F006, "GE480i title/menu texture setup lower"),
            (0x4FE44, 0x44818000, "GE480i title/menu draw uses immediate height float"),
            (0x4FF00, 0x3C0E009F, "GE480i texture rectangle lower width"),
        ],
    },
    {
        "name": "dmytex480",
        "purpose": "t90doss1my16 plus 480-line TND variant of the GE480i texture setup; diagnostic only.",
        "patches": [
            (0x4FDEC, 0x3C170713, "GE480i title/menu texture setup upper"),
            (0x4FDFC, 0x3C0AE49F, "GE480i texture rectangle target width"),
            (0x4FE34, 0x3C0143F0, "TND diagnostic title/menu draw height float upper 480.0"),
            (0x4FE3C, 0x36F7F006, "GE480i title/menu texture setup lower"),
            (0x4FE44, 0x44818000, "GE480i title/menu draw uses immediate height float"),
            (0x4FF00, 0x3C0E009F, "GE480i texture rectangle lower width"),
            (0x501AC, 0x292101E0, "TND diagnostic source row loop limit 480"),
        ],
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


def add_route(rom, menu_id):
    old = word(rom, TIMEOUT_MENU_WORD_OFFSET)
    if old != EXPECTED_TIMEOUT_WORD:
        raise ValueError(
            f"unexpected route word at 0x{TIMEOUT_MENU_WORD_OFFSET:X}: "
            f"0x{old:08X}, expected 0x{EXPECTED_TIMEOUT_WORD:08X}"
        )
    new = 0x24040000 | menu_id
    write_word(rom, TIMEOUT_MENU_WORD_OFFSET, new)
    return {"offset": f"0x{TIMEOUT_MENU_WORD_OFFSET:X}", "old": f"0x{old:08X}", "new": f"0x{new:08X}"}


def build_candidate(spec, base_rom, base, out_dir, route_dir):
    rom = bytearray(base)
    applied = []
    for offset, value, note in spec["patches"]:
        old = word(rom, offset)
        write_word(rom, offset, value)
        applied.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{value:08X}",
                "changed": old != value,
                "note": note,
            }
        )

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = out_dir / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)

    route_outputs = []
    for route_suffix, menu_id, route_purpose in ROUTES:
        route_rom = bytearray(rom)
        route_patch = add_route(route_rom, menu_id)
        rcrc1, rcrc2 = update_n64_crc_6102(route_rom)
        route_path = route_dir / f"{spec['name']}auto{route_suffix}.z64"
        route_path.write_bytes(route_rom)
        route_outputs.append(
            {
                "route": route_suffix,
                "purpose": route_purpose,
                "out_rom": str(route_path),
                "out_md5": md5(route_rom),
                "header_crc": f"{rcrc1:08X} {rcrc2:08X}",
                "route_patch": route_patch,
                "save_outputs": copy_save_pair(base_rom, route_path),
            }
        )

    return {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "base_rom": str(base_rom),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patch_count": len(applied),
        "changed_patch_count": sum(1 for patch in applied if patch["changed"]),
        "patches": applied,
        "save_outputs": copy_save_pair(base_rom, out_rom),
        "route_outputs": route_outputs,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/t90doss1my16.z64"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/generated"))
    parser.add_argument("--route-dir", type=Path, default=Path("artifacts/generated/t90doss1_blitter_routes"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/tnd480i_t90doss1_blitter_file_candidates_20260518.json"),
    )
    args = parser.parse_args()

    if not args.base_rom.exists():
        raise SystemExit(f"missing base ROM: {args.base_rom}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.route_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    base = args.base_rom.read_bytes()
    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(base),
        "purpose": "Probe whether the remaining t90doss1my16 file-select backdrop clipping is the shared title/menu blitter texture setup.",
        "candidates": [
            build_candidate(spec, args.base_rom, base, args.out_dir, args.route_dir) for spec in CANDIDATES
        ],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.report), "candidates": [c["name"] for c in report["candidates"]]}, indent=2))


if __name__ == "__main__":
    main()
