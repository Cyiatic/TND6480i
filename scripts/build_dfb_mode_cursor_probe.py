#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018

PROBES = {
    "dfbcurx": {
        "purpose": "Restore only TND stock mode-select cursor X constant.",
        "patches": {
            0x42338: 0x3C0142FC,
        },
    },
    "dfbcury": {
        "purpose": "Restore only TND stock mode-select cursor Y base constant.",
        "patches": {
            0x42330: 0x25CF00E2,
        },
    },
    "dfbcur": {
        "purpose": "Restore TND stock mode-select cursor X and Y constants.",
        "patches": {
            0x42330: 0x25CF00E2,
            0x42338: 0x3C0142FC,
        },
    },
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


def add_mode_route(base_rom, full_rom, out_rom):
    route_rom = bytearray(full_rom)
    old = word(route_rom, TIMEOUT_MENU_WORD_OFFSET)
    if old != EXPECTED_TIMEOUT_WORD:
        raise ValueError(f"unexpected timeout word 0x{old:08X} at 0x{TIMEOUT_MENU_WORD_OFFSET:X}")
    write_word(route_rom, TIMEOUT_MENU_WORD_OFFSET, 0x24040006)
    crc1, crc2 = update_n64_crc_6102(route_rom)
    route_path = out_rom.with_name(out_rom.stem + "auto06.z64")
    route_path.write_bytes(route_rom)
    return {
        "out_rom": str(route_path),
        "out_md5": md5(route_rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patch": {
            "offset": f"0x{TIMEOUT_MENU_WORD_OFFSET:X}",
            "old": f"0x{old:08X}",
            "new": "0x24040006",
        },
        "save_outputs": copy_save_pair(base_rom, route_path),
    }


def build_one(name, spec, base_rom, base, out_dir):
    rom = bytearray(base)
    applied = []
    for offset, value in spec["patches"].items():
        old = word(rom, offset)
        write_word(rom, offset, value)
        applied.append({
            "offset": f"0x{offset:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{value:08X}",
        })
    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = out_dir / f"{name}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": name,
        "purpose": spec["purpose"],
        "base_rom": str(base_rom),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": applied,
        "save_outputs": copy_save_pair(base_rom, out_rom),
        "route_output": add_mode_route(base_rom, rom, out_rom),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/dfbmy32.z64"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/generated"))
    parser.add_argument("--report", type=Path, default=Path("reports/tnd480i_dfb_mode_cursor_probe_20260518.json"))
    args = parser.parse_args()

    base = args.base_rom.read_bytes()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(base),
        "purpose": "Focused mode-select cursor probes on top of dfbmy32; no text/background changes.",
        "candidates": [build_one(name, spec, args.base_rom, base, args.out_dir) for name, spec in PROBES.items()],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
