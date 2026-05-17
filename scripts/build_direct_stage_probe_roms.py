#!/usr/bin/env python3
import argparse
import hashlib
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import update_n64_crc_6102


DEFAULT_OUT_DIR = Path("artifacts/generated/stage_probes")
REPORT_DIR = Path("reports/stage_probes")
DEFAULT_BASE = Path("artifacts/generated/tnd58.z64")
DEFAULT_SAVE = Path("artifacts/generated/tnd58.sav")

# bossMainloop normally checks tokenFind("-level_") before entering the main
# stage loop. Replacing that tiny token parser with an unconditional store to
# g_StageNum gives us one-ROM-per-stage hardware probes without menu driving.
BOOT_STAGE_PATCH = [
    (0x6C94, 0x3C018002, "lui at, 0x8002"),
    (0x6C98, None, "addiu v0, zero, <stage>"),
    (0x6C9C, 0xAC2241A8, "sw v0, g_StageNum"),
    (0x6CA0, 0x1000000E, "b after -level_ token parser"),
    (0x6CA4, 0x00000000, "nop"),
]

LEVELS = [
    {"index": 0, "short": "bzr", "name": "Bazaar", "stage_id": 33, "ge_slot": "Dam"},
    {"index": 1, "short": "pty", "name": "Party", "stage_id": 34, "ge_slot": "Facility"},
    {"index": 2, "short": "lab", "name": "Labs", "stage_id": 35, "ge_slot": "Runway"},
    {"index": 3, "short": "prs", "name": "Press", "stage_id": 36, "ge_slot": "Surface 1"},
    {"index": 4, "short": "hot", "name": "Hotel", "stage_id": 9, "ge_slot": "Bunker 1"},
    {"index": 5, "short": "prk", "name": "Parkhaus", "stage_id": 20, "ge_slot": "Silo"},
    {"index": 6, "short": "wrk", "name": "Wreck", "stage_id": 26, "ge_slot": "Frigate"},
    {"index": 7, "short": "twr", "name": "Tower", "stage_id": 43, "ge_slot": "Surface 2"},
    {"index": 8, "short": "cty", "name": "City", "stage_id": 27, "ge_slot": "Bunker 2"},
    {"index": 9, "short": "bot", "name": "Boat", "stage_id": 22, "ge_slot": "Statue"},
    {"index": 10, "short": "brg", "name": "Bridge", "stage_id": 24, "ge_slot": "Archives"},
    {"index": 11, "short": "vol", "name": "Volcano", "stage_id": 29, "ge_slot": "Streets"},
    {"index": 12, "short": "als", "name": "Alaska", "stage_id": 30, "ge_slot": "Depot"},
    {"index": 13, "short": "end", "name": "The End", "stage_id": 25, "ge_slot": "Train"},
]


def md5_bytes(data):
    return hashlib.md5(data).hexdigest()


def read_word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def build_probe(base_path, save_path, level, out_dir):
    rom = bytearray(base_path.read_bytes())
    patches = []
    for offset, value, note in BOOT_STAGE_PATCH:
        new_value = value
        if value is None:
            new_value = 0x24020000 | level["stage_id"]
        old_value = read_word(rom, offset)
        write_word(rom, offset, new_value)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old_value:08X}",
                "new": f"0x{new_value:08X}",
                "note": note,
            }
        )

    crc1, crc2 = update_n64_crc_6102(rom)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"p{level['index']:02d}{level['short']}"
    out_rom = out_dir / f"{stem}.z64"
    out_rom.write_bytes(rom)

    save_outputs = []
    if save_path and save_path.exists():
        save_bytes = save_path.read_bytes()
        out_sav = out_dir / f"{stem}.sav"
        out_eep = out_dir / f"{stem}.eep"
        out_sav.write_bytes(save_bytes)
        out_eep.write_bytes(save_bytes if len(save_bytes) >= 2048 else save_bytes + b"\0" * (2048 - len(save_bytes)))
        save_outputs = [str(out_sav), str(out_eep)]

    return {
        "level": level,
        "rom": str(out_rom),
        "md5": md5_bytes(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "saves": save_outputs,
        "patches": patches,
    }


def select_levels(names):
    if not names:
        return LEVELS
    wanted = {name.lower() for name in names}
    selected = []
    for level in LEVELS:
        keys = {
            str(level["index"]),
            level["short"].lower(),
            f"p{level['index']:02d}{level['short']}".lower(),
            level["name"].lower(),
            level["ge_slot"].lower(),
        }
        if wanted & keys:
            selected.append(level)
    missing = sorted(wanted - {k for level in selected for k in (
        str(level["index"]),
        level["short"].lower(),
        f"p{level['index']:02d}{level['short']}".lower(),
        level["name"].lower(),
        level["ge_slot"].lower(),
    )})
    if missing:
        raise SystemExit(f"unknown level selector(s): {', '.join(missing)}")
    return selected


def main():
    parser = argparse.ArgumentParser(description="Build short direct-stage TND6480i probe ROMs.")
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--save", type=Path, default=DEFAULT_SAVE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_DIR / "direct_stage_probes_latest.json")
    parser.add_argument("levels", nargs="*", help="Optional level names, indexes, shorts, or GE slots.")
    args = parser.parse_args()

    if not args.base.exists():
        raise SystemExit(f"base ROM not found: {args.base}")

    base_bytes = args.base.read_bytes()
    outputs = [build_probe(args.base, args.save, level, args.out_dir) for level in select_levels(args.levels)]
    report = {
        "base": str(args.base),
        "base_md5": md5_bytes(base_bytes),
        "save": str(args.save) if args.save else None,
        "out_dir": str(args.out_dir),
        "purpose": "Direct-boot per-stage probes to reduce manual hardware menu testing.",
        "outputs": outputs,
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
