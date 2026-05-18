#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


MODE_Y_OFFSETS = [
    0x42330,
    0x42390,
    0x42458,
    0x4246C,
    0x42484,
    0x424F0,
    0x425DC,
    0x425F4,
    0x4260C,
    0x42688,
    0x42730,
    0x42748,
    0x42760,
]

TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def signed16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def with_signed16(value, imm):
    return (value & 0xFFFF0000) | (imm & 0xFFFF)


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


def add_mode_route(base_rom, rom, out_rom):
    old = word(rom, TIMEOUT_MENU_WORD_OFFSET)
    if old != EXPECTED_TIMEOUT_WORD:
        raise ValueError(f"unexpected timeout word 0x{old:08X} at 0x{TIMEOUT_MENU_WORD_OFFSET:X}")
    write_word(rom, TIMEOUT_MENU_WORD_OFFSET, 0x24040006)
    crc1, crc2 = update_n64_crc_6102(rom)
    route_rom = out_rom.with_name(out_rom.stem + "auto06.z64")
    route_rom.write_bytes(rom)
    return {
        "out_rom": str(route_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "route_patch": {
            "offset": f"0x{TIMEOUT_MENU_WORD_OFFSET:X}",
            "old": f"0x{old:08X}",
            "new": "0x24040006",
        },
        "save_outputs": copy_save_pair(base_rom, route_rom),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/t90doss1.z64"))
    parser.add_argument("--out-rom", type=Path, default=Path("artifacts/generated/t90doss1my16.z64"))
    parser.add_argument("--delta", type=int, default=-16)
    parser.add_argument("--report", type=Path, default=Path("reports/tnd480i_t90doss1_mode_y_candidate_20260518.json"))
    args = parser.parse_args()

    base = bytearray(args.base_rom.read_bytes())
    patches = []
    for offset in MODE_Y_OFFSETS:
        old = word(base, offset)
        new_imm = signed16(old) + args.delta
        new = with_signed16(old, new_imm)
        write_word(base, offset, new)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{new:08X}",
                "delta": args.delta,
            }
        )

    crc1, crc2 = update_n64_crc_6102(base)
    args.out_rom.parent.mkdir(parents=True, exist_ok=True)
    args.out_rom.write_bytes(base)
    route_rom = bytearray(base)

    report = {
        "base_rom": str(args.base_rom),
        "out_rom": str(args.out_rom),
        "out_md5": md5(base),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": "Move only the mode-select vertical constants up after t90doss1 reached the 640x480 table1 path.",
        "patches": patches,
        "save_outputs": copy_save_pair(args.base_rom, args.out_rom),
        "route_output": add_mode_route(args.base_rom, route_rom, args.out_rom),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
