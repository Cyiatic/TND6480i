#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018

# The GE 480i menu-init rewrite embeds two aspect/dimension table entries:
#   0x4F350: aspect 4:3
#   0x4F354: entry 0 dimensions
#   0x4F358: aspect 4:3
#   0x4F35C: entry 1 dimensions
#
# t90texstk already has entry 0 at 640x480, but entry 1 is still 440x330.
# If the dossier is selecting entry 1, it will look like the older 480i layout
# even though the surrounding VI and framebuffer code is high-res.
MENU_DIM_ENTRY1_OFFSET = 0x4F35C
DIM_440_330 = 0x01B8014A
DIM_640_480 = 0x028001E0

ROUTES = [
    ("05", 0x05, "file select / save folders"),
    ("06", 0x06, "mode select"),
    ("07", 0x07, "mission select"),
    ("08", 0x08, "difficulty select"),
    ("0a", 0x0A, "briefing dossier"),
]

CANDIDATES = [
    {
        "name": "txmtab1",
        "purpose": "t90texstk with only embedded menu dimension table entry 1 changed from 440x330 to 640x480.",
        "patches": [(MENU_DIM_ENTRY1_OFFSET, DIM_640_480, "menu-init entry 1 dimensions 640x480")],
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


def add_direct_route(rom, menu_id):
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
        route_patch = add_direct_route(route_rom, menu_id)
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
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/t90texstk.z64"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/generated"))
    parser.add_argument("--route-dir", type=Path, default=Path("artifacts/generated/menu_table_routes"))
    parser.add_argument("--report", type=Path, default=Path("reports/tnd480i_t90tex_menu_table_candidates_20260518.json"))
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
        "purpose": "Isolate the remaining stock-sized embedded menu dimension table entry in the GE 480i menu-init rewrite.",
        "candidates": [build_candidate(spec, args.base_rom, base, args.out_dir, args.route_dir) for spec in CANDIDATES],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.report), "candidates": [item["name"] for item in report["candidates"]]}, indent=2))


if __name__ == "__main__":
    main()
