#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


GE_STOCK = Path("artifacts/roms/GoldenEye 007 (USA).z64")
GE_480I = Path("artifacts/roms/BASELINE_GE_480i_direct_from_stock.z64")
BASE_ROM = Path("artifacts/generated/g1gridbg1.z64")
OUT_ROM = Path("artifacts/generated/g1diff1.z64")
REPORT = Path("reports/tnd480i_g1diff1_difficulty_20260518.json")

TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018

DIFFICULTY_RANGE = (0x43300, 0x43D00)

PATCH_LIBRARY = {
    "timeout_to_mission_select": (
        0x3FF34,
        0x24040018,
        0x24040007,
        "After the TND title/logo timeout, route to MENU_MISSION_SELECT.",
    ),
    "mission_select_force_button_accept": (
        0x42D98,
        0x1040002A,
        0x00000000,
        "Force the mission-select A/Start/Z accept block so briefingpage and selected_stage are initialized.",
    ),
}


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


def collect_ge480i_difficulty_words(stock, ge480):
    patches = []
    start, end = DIFFICULTY_RANGE
    for offset in range(start, end, 4):
        old = word(stock, offset)
        new = word(ge480, offset)
        if old != new:
            patches.append((offset, old, new))
    return patches


def add_difficulty_route(base_rom, base, out_rom):
    rom = bytearray(base)
    applied = []
    for key in ("timeout_to_mission_select", "mission_select_force_button_accept"):
        offset, expected_old, new, note = PATCH_LIBRARY[key]
        old = word(rom, offset)
        if old != expected_old:
            raise ValueError(f"{key}: unexpected word 0x{old:08X} at 0x{offset:X}")
        write_word(rom, offset, new)
        applied.append({"key": key, "offset": f"0x{offset:X}", "old": f"0x{old:08X}", "new": f"0x{new:08X}", "note": note})
    crc1, crc2 = update_n64_crc_6102(rom)
    route_rom = out_rom.with_name(out_rom.stem + "btn08.z64")
    route_rom.write_bytes(rom)
    return {
        "out_rom": str(route_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": applied,
        "save_outputs": copy_save_pair(base_rom, route_rom),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=BASE_ROM)
    parser.add_argument("--out-rom", type=Path, default=OUT_ROM)
    parser.add_argument("--ge-stock-rom", type=Path, default=GE_STOCK)
    parser.add_argument("--ge480-rom", type=Path, default=GE_480I)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    base = bytearray(args.base_rom.read_bytes())
    ge_stock = args.ge_stock_rom.read_bytes()
    ge480 = args.ge480_rom.read_bytes()

    patches = []
    for offset, ge_old, ge_new in collect_ge480i_difficulty_words(ge_stock, ge480):
        old = word(base, offset)
        write_word(base, offset, ge_new)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "ge_stock": f"0x{ge_old:08X}",
                "new": f"0x{ge_new:08X}",
                "changed": old != ge_new,
            }
        )

    crc1, crc2 = update_n64_crc_6102(base)
    args.out_rom.parent.mkdir(parents=True, exist_ok=True)
    args.out_rom.write_bytes(base)

    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(args.base_rom.read_bytes()),
        "out_rom": str(args.out_rom),
        "out_md5": md5(base),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": "Apply only the GE480i difficulty select constructor/interface word deltas on top of g1gridbg1.",
        "range": [f"0x{DIFFICULTY_RANGE[0]:X}", f"0x{DIFFICULTY_RANGE[1]:X}"],
        "patches": patches,
        "changed_patch_count": sum(1 for item in patches if item["changed"]),
        "save_outputs": copy_save_pair(args.base_rom, args.out_rom),
        "routes": {
            "difficulty_select": add_difficulty_route(args.base_rom, base, args.out_rom),
        },
        "do_not_promote_until_hardware_compared": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
