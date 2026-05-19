#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import (
    GE_1172_OFFSET,
    inflate_ge1172,
    md5,
    pack_ge1172,
    update_n64_crc_6102,
)


BASE_ROM = Path("artifacts/generated/g1class1.z64")
GE_480I_ROM = Path("artifacts/roms/BASELINE_GE_480i_direct_from_stock.z64")
OUT_ROM = Path("artifacts/generated/g1gridb1.z64")
REPORT = Path("reports/tnd480i_g1gridb1_mission_grid_20260518.json")

TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018

RAW_MISSION_TABLE_B_OFF = 0xA240
RAW_MISSION_TABLE_B_WORDS = 9

# Existing custom mission-label table cave used by g1mtabge4/g1class1.
LABEL_TABLE_OFF = 0x4F9FC
LABEL_TABLE_WORDS = 9


def zero_pad_capacity(data, offset, slot_len):
    end = offset + slot_len
    while end < len(data) and data[end] == 0:
        end += 1
    return end - offset


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def read_words(data, offset, count):
    return [word(data, offset + index * 4) for index in range(count)]


def write_words(data, offset, values):
    for index, value in enumerate(values):
        write_word(data, offset + index * 4, value)


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
    parser.add_argument("--base-rom", type=Path, default=BASE_ROM)
    parser.add_argument("--ge480-rom", type=Path, default=GE_480I_ROM)
    parser.add_argument("--out-rom", type=Path, default=OUT_ROM)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument(
        "--label-table",
        choices=("keep", "ge"),
        default="keep",
        help="Whether to leave the g1mtabge4 custom mission label table as-is or copy GE480i table B into it too.",
    )
    parser.add_argument("--zopfli-iterations", type=int, default=200)
    args = parser.parse_args()

    base_rom = bytearray(args.base_rom.read_bytes())
    ge_rom = args.ge480_rom.read_bytes()
    raw, consumed = inflate_ge1172(base_rom, GE_1172_OFFSET)
    ge_raw, _ = inflate_ge1172(ge_rom, GE_1172_OFFSET)
    raw = bytearray(raw)

    ge_table = read_words(ge_raw, RAW_MISSION_TABLE_B_OFF, RAW_MISSION_TABLE_B_WORDS)
    old_raw_table = read_words(raw, RAW_MISSION_TABLE_B_OFF, RAW_MISSION_TABLE_B_WORDS)
    write_words(raw, RAW_MISSION_TABLE_B_OFF, ge_table)

    patches = [
        {
            "space": "1172 raw",
            "offset": f"0x{RAW_MISSION_TABLE_B_OFF:X}",
            "old": old_raw_table,
            "new": ge_table,
            "note": "mission-select cursor/grid table B copied from GE480i",
        }
    ]

    old_label_table = read_words(base_rom, LABEL_TABLE_OFF, LABEL_TABLE_WORDS)
    if args.label_table == "ge":
        write_words(base_rom, LABEL_TABLE_OFF, ge_table)
        patches.append(
            {
                "space": "ROM",
                "offset": f"0x{LABEL_TABLE_OFF:X}",
                "old": old_label_table,
                "new": ge_table,
                "note": "custom mission-label table also copied from GE480i table B",
            }
        )

    packed = pack_ge1172(bytes(raw), args.zopfli_iterations)
    allowed_packed_len = zero_pad_capacity(base_rom, GE_1172_OFFSET, consumed)
    if len(packed) > allowed_packed_len:
        raise ValueError(f"packed stream too large: 0x{len(packed):X} > 0x{allowed_packed_len:X}")
    base_rom[GE_1172_OFFSET : GE_1172_OFFSET + allowed_packed_len] = b"\x00" * allowed_packed_len
    base_rom[GE_1172_OFFSET : GE_1172_OFFSET + len(packed)] = packed

    crc1, crc2 = update_n64_crc_6102(base_rom)
    args.out_rom.parent.mkdir(parents=True, exist_ok=True)
    args.out_rom.write_bytes(base_rom)

    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(args.base_rom.read_bytes()),
        "ge480_rom": str(args.ge480_rom),
        "out_rom": str(args.out_rom),
        "out_md5": md5(base_rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "label_table_mode": args.label_table,
        "slot_len": f"0x{consumed:X}",
        "allowed_packed_len": f"0x{allowed_packed_len:X}",
        "packed_len": f"0x{len(packed):X}",
        "patches": patches,
        "save_outputs": copy_save_pair(args.base_rom, args.out_rom),
        "routes": {
            "mission_select": add_route(args.base_rom, base_rom, args.out_rom, 0x07, "auto07"),
        },
        "do_not_promote_until_hardware_compared": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
