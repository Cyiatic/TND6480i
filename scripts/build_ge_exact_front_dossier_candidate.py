#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


GE_STOCK = Path("artifacts/roms/GoldenEye 007 (USA).z64")
GE_480I = Path("artifacts/roms/BASELINE_GE_480i_direct_from_stock.z64")
TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018

PATCH_RANGES = [
    (0x3EBE0, 0x3EF80, "front tab text/cursor bounds from GE480i"),
    (0x41B00, 0x42800, "mode/file front constants and mode constructor/update from GE480i"),
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


def collect_ge_diffs(stock, ge480):
    patches = []
    for start, end, note in PATCH_RANGES:
        for offset in range(start, end, 4):
            old = word(stock, offset)
            new = word(ge480, offset)
            if old == new:
                continue
            patches.append({"offset": offset, "new": new, "ge_stock": old, "note": note})
    return patches


def add_route(base_rom, base, out_rom, menu_id, suffix):
    rom = bytearray(base)
    old = word(rom, TIMEOUT_MENU_WORD_OFFSET)
    if old != EXPECTED_TIMEOUT_WORD:
        raise ValueError(f"unexpected timeout word 0x{old:08X} at 0x{TIMEOUT_MENU_WORD_OFFSET:X}")
    write_word(rom, TIMEOUT_MENU_WORD_OFFSET, 0x24040000 | menu_id)
    crc1, crc2 = update_n64_crc_6102(rom)
    route_rom = out_rom.with_name(out_rom.stem + suffix + ".z64")
    route_rom.write_bytes(rom)
    return {
        "out_rom": str(route_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "route_patch": {
            "offset": f"0x{TIMEOUT_MENU_WORD_OFFSET:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{0x24040000 | menu_id:08X}",
        },
        "save_outputs": copy_save_pair(base_rom, route_rom),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/dmyfbrw1.z64"))
    parser.add_argument("--out-rom", type=Path, default=Path("artifacts/generated/gexact1.z64"))
    parser.add_argument("--ge-stock-rom", type=Path, default=GE_STOCK)
    parser.add_argument("--ge480-rom", type=Path, default=GE_480I)
    parser.add_argument("--report", type=Path, default=Path("reports/tnd480i_gexact1_front_dossier_20260518.json"))
    args = parser.parse_args()

    base = bytearray(args.base_rom.read_bytes())
    stock = args.ge_stock_rom.read_bytes()
    ge480 = args.ge480_rom.read_bytes()

    applied = []
    for patch in collect_ge_diffs(stock, ge480):
        old = word(base, patch["offset"])
        write_word(base, patch["offset"], patch["new"])
        applied.append({
            "offset": f"0x{patch['offset']:X}",
            "old": f"0x{old:08X}",
            "ge_stock": f"0x{patch['ge_stock']:08X}",
            "new": f"0x{patch['new']:08X}",
            "changed": old != patch["new"],
            "note": patch["note"],
        })

    crc1, crc2 = update_n64_crc_6102(base)
    args.out_rom.parent.mkdir(parents=True, exist_ok=True)
    args.out_rom.write_bytes(base)

    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(args.base_rom.read_bytes()),
        "out_rom": str(args.out_rom),
        "out_md5": md5(base),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": (
            "Apply the exact GE480i front tab and mode dossier constants on top of the "
            "file-select-only cloned blitter path. This reverses manual mode-y nudges "
            "and restores GE480i tab/cursor bounds."
        ),
        "patch_ranges": [{"start": f"0x{s:X}", "end": f"0x{e:X}", "note": n} for s, e, n in PATCH_RANGES],
        "patches": applied,
        "changed_patch_count": sum(1 for item in applied if item["changed"]),
        "save_outputs": copy_save_pair(args.base_rom, args.out_rom),
        "routes": {
            "mode_select": add_route(args.base_rom, base, args.out_rom, 0x06, "auto06"),
            "file_select": add_route(args.base_rom, base, args.out_rom, 0x05, "auto05"),
            "mission_select": add_route(args.base_rom, base, args.out_rom, 0x07, "auto07"),
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
