#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/g1txmissionfull.z64")
OUT_ROM = Path("artifacts/generated/g1mlfix4.z64")
REPORT = Path("reports/tnd480i_g1mlfix4_mission_label_scaled_20260518.json")

TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018

# Keep both helpers inside the proven resident low cave at 0x3CB0-0x3D20.
HELPER1_OFF = 0x3CB0
HELPER2_OFF = 0x3CE8


def runtime_addr(offset):
    return (0x70000000 if offset < 0x40000 else 0x7F000000) + offset


HELPER1_ADDR = runtime_addr(HELPER1_OFF)
HELPER2_ADDR = runtime_addr(HELPER2_OFF)

FIRST_SITE = 0x43154
FIRST_RETURN = 0x7F043160
SECOND_SITE = 0x431E8
SECOND_RETURN = 0x7F0431F4

ORIGINAL_SECOND_CALLEE = 0x7000441C

REG = {
    "zero": 0,
    "v1": 3,
    "a1": 5,
    "a2": 6,
    "t0": 8,
    "t2": 10,
    "t9": 25,
    "sp": 29,
    "s6": 22,
}


def r_type(rs, rt, rd, shamt, funct):
    return (rs << 21) | (rt << 16) | (rd << 11) | (shamt << 6) | funct


def i_type(op, rs, rt, imm):
    return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def j_type(op, addr):
    return (op << 26) | ((addr >> 2) & 0x03FFFFFF)


def lw(rt, imm, rs):
    return i_type(0x23, rs, rt, imm)


def sw(rt, imm, rs):
    return i_type(0x2B, rs, rt, imm)


def addiu(rt, rs, imm):
    return i_type(0x09, rs, rt, imm)


def addu(rd, rs, rt):
    return r_type(rs, rt, rd, 0, 0x21)


def sll(rd, rt, shamt):
    return r_type(0, rt, rd, shamt, 0x00)


def j(addr):
    return j_type(0x02, addr)


def jal(addr):
    return j_type(0x03, addr)


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def write_words(data, offset, words):
    for index, value in enumerate(words):
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


def coordinate_adjust_words(return_addr):
    # Start from g1txmissionfull's GE480i label constants, then expand the old
    # 5x4 mission cursor table spacing into the 480i filmstrip spacing seen in
    # the GE480i reference. t1 is intentionally preserved; the original code
    # uses it as measured text width immediately after the first hook.
    return [
        lw(REG["t9"], 0xD8, REG["sp"]),      # t9 = column index
        sll(REG["t0"], REG["t9"], 5),        # x += column * 33 + 36
        addu(REG["t0"], REG["t0"], REG["t9"]),
        addu(REG["a1"], REG["a1"], REG["t0"]),
        addiu(REG["a1"], REG["a1"], 36),
        sll(REG["t0"], REG["s6"], 5),        # y += row * 32 + 32
        addu(REG["a2"], REG["a2"], REG["t0"]),
        addiu(REG["a2"], REG["a2"], 32),
        addu(REG["t2"], REG["a2"], REG["v1"]),
        sw(REG["a1"], 0x8C, REG["sp"]),
        sw(REG["t2"], 0x10, REG["sp"]),
        sw(REG["a2"], 0x88, REG["sp"]),
        j(return_addr),
        0,
    ]


def second_pass_words():
    words = coordinate_adjust_words(0)
    words = words[:8]
    return words + [
        sw(REG["a1"], 0x8C, REG["sp"]),
        jal(ORIGINAL_SECOND_CALLEE),
        sw(REG["a2"], 0x88, REG["sp"]),
        j(SECOND_RETURN),
        0,
    ]


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
    first_helper = coordinate_adjust_words(FIRST_RETURN)
    second_helper = second_pass_words()

    patches = []
    for offset, words, note in [
        (HELPER1_OFF, first_helper, "mission label first-pass coordinate scaler"),
        (HELPER2_OFF, second_helper, "mission label shadow-pass coordinate scaler"),
        (FIRST_SITE, [j(HELPER1_ADDR), 0, 0], "route first mission-label draw setup to scaler"),
        (SECOND_SITE, [j(HELPER2_ADDR), 0, 0], "route shadow mission-label draw setup to scaler"),
    ]:
        old = [word(rom, offset + index * 4) for index in range(len(words))]
        write_words(rom, offset, words)
        patches.append({
            "offset": f"0x{offset:X}",
            "words": len(words),
            "old": [f"0x{value:08X}" for value in old],
            "new": [f"0x{value:08X}" for value in words],
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
        "purpose": "Scale only the mission-select label coordinates toward the GE480i filmstrip spacing.",
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
