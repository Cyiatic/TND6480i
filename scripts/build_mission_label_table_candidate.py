#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/g1txmissionfull.z64")
OUT_ROM = Path("artifacts/generated/g1mtabge3.z64")
REPORT = Path("reports/tnd480i_g1mtabge3_mission_label_table_20260518.json")

TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018

TABLE_OFF = 0x4F9FC
# The file-select blitter clone at ROM 0x4F498 is deliberately routed at
# runtime 0x7F01A968. Its used size is 0x564 bytes, so 0x4F9FC maps to the
# first unused word at runtime 0x7F01AECC.
TABLE_ADDR = 0x7F01AECC
X_TABLE = [90, 191, 292, 393, 494]
Y_TABLE = [78, 179, 280, 381]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def lui(rt, imm):
    return (0x0F << 26) | (rt << 16) | (imm & 0xFFFF)


def addiu(rt, rs, imm):
    return (0x09 << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def hi_lo(addr):
    lo = addr & 0xFFFF
    hi = (addr >> 16) & 0xFFFF
    if lo & 0x8000:
        hi = (hi + 1) & 0xFFFF
        lo -= 0x10000
    return hi, lo


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
    parser.add_argument("--out-rom", type=Path, default=OUT_ROM)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    rom = bytearray(args.base_rom.read_bytes())
    x_addr = TABLE_ADDR
    y_addr = TABLE_ADDR + len(X_TABLE) * 4
    x_hi, x_lo = hi_lo(x_addr)
    y_hi, y_lo = hi_lo(y_addr)

    table_words = X_TABLE + Y_TABLE
    patches = []
    old_table = [word(rom, TABLE_OFF + index * 4) for index in range(len(table_words))]
    for index, value in enumerate(table_words):
        write_word(rom, TABLE_OFF + index * 4, value)
    patches.append({
        "offset": f"0x{TABLE_OFF:X}",
        "runtime_address": f"0x{TABLE_ADDR:X}",
        "old": [f"0x{value:08X}" for value in old_table],
        "new": [value for value in table_words],
        "note": "custom mission-select label X/Y tables in cloned-blitter slack space",
    })

    pointer_words = [
        (0x4302C, lui(9, x_hi), "lui t1, custom X table high"),
        (0x43030, lui(11, y_hi), "lui t3, custom Y table high"),
        (0x43034, addiu(11, 11, y_lo), "addiu t3, t3, custom Y table low"),
        (0x43038, addiu(9, 9, x_lo), "addiu t1, t1, custom X table low"),
    ]
    for offset, value, note in pointer_words:
        old = word(rom, offset)
        write_word(rom, offset, value)
        patches.append({
            "offset": f"0x{offset:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{value:08X}",
            "note": note,
        })

    crc1, crc2 = update_n64_crc_6102(rom)
    args.out_rom.parent.mkdir(parents=True, exist_ok=True)
    args.out_rom.write_bytes(rom)
    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(args.base_rom.read_bytes()),
        "out_rom": str(args.out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": "Use a GE480i-style mission-label coordinate table without executing any new trampoline code.",
        "x_table": X_TABLE,
        "y_table": Y_TABLE,
        "patches": patches,
        "save_outputs": copy_save_pair(args.base_rom, args.out_rom),
        "routes": {
            "mission_select": add_route(args.base_rom, rom, args.out_rom, 0x07, "auto07"),
        },
        "do_not_promote_until_hardware_compared": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
