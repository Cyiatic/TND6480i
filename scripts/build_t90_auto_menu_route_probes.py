#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/t90gbtexpost.z64")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_t90_auto_menu_route_probes_20260518.json")
TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018

ROUTES = [
    ("t90auto05", 0x05, "MENU_FILE_SELECT", "File select / save folders"),
    ("t90auto06", 0x06, "MENU_MODE_SELECT", "Single-player / multiplayer / cheat select"),
    ("t90auto07", 0x07, "MENU_MISSION_SELECT", "Mission select dossier"),
    ("t90auto08", 0x08, "MENU_DIFFICULTY", "Difficulty select dossier"),
    ("t90auto0a", 0x0A, "MENU_BRIEFING", "Mission briefing dossier"),
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


def build_one(route, base_rom, base, out_dir, prefix):
    name, menu_id, symbol, purpose = route
    rom = bytearray(base)
    old = word(rom, TIMEOUT_MENU_WORD_OFFSET)
    if old != EXPECTED_TIMEOUT_WORD:
        raise SystemExit(
            f"unexpected timeout menu word at 0x{TIMEOUT_MENU_WORD_OFFSET:X}: "
            f"0x{old:08X}, expected 0x{EXPECTED_TIMEOUT_WORD:08X}"
        )

    new = 0x24040000 | menu_id
    write_word(rom, TIMEOUT_MENU_WORD_OFFSET, new)
    crc1, crc2 = update_n64_crc_6102(rom)
    out_name = name if not prefix else f"{prefix}{name[3:]}"
    out_rom = out_dir / f"{out_name}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": out_name,
        "menu_id": menu_id,
        "symbol": symbol,
        "purpose": purpose,
        "base_rom": str(base_rom),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patch": {
            "offset": f"0x{TIMEOUT_MENU_WORD_OFFSET:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{new:08X}",
            "note": f"After the TND title/logo timeout, route directly to {symbol}.",
        },
        "save_outputs": copy_save_pair(base_rom, out_rom),
        "do_not_promote": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=BASE_ROM)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument(
        "--prefix",
        default="",
        help="Optional output name prefix. Example: t90post -> t90post05/t90post06/etc.",
    )
    args = parser.parse_args()

    if not args.base_rom.exists():
        raise SystemExit(f"missing base ROM: {args.base_rom}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    base = args.base_rom.read_bytes()
    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(base),
        "purpose": "No-input hardware route probes for front/dossier pages; do not promote over gameplay baseline.",
        "routes": [build_one(route, args.base_rom, base, args.out_dir, args.prefix) for route in ROUTES],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
