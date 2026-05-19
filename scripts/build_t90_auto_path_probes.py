#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/t90gbtexpost.z64")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_t90_auto_path_probes_20260518.json")

PATCH_LIBRARY = {
    "timeout_to_mission_select": (
        0x3FF34,
        0x24040018,
        0x24040007,
        "After the TND title/logo timeout, route to MENU_MISSION_SELECT.",
    ),
    "mission_select_accept": (
        0x42E88,
        0x13200010,
        0x00000000,
        "Force mission-select accept path by removing the branch that skips MENU_DIFFICULTY.",
    ),
    "mission_select_force_button_accept": (
        0x42D98,
        0x1040002A,
        0x00000000,
        "Force the mission-select A/Start/Z accept block so briefingpage and selected_stage are initialized.",
    ),
    "difficulty_accept": (
        0x43554,
        0x11600012,
        0x00000000,
        "Force difficulty accept path by removing the branch that skips MENU_BRIEFING.",
    ),
    "difficulty_force_button_accept": (
        0x43518,
        0x10400008,
        0x00000000,
        "Force the difficulty A/Start/Z accept block before the page-transition branch.",
    ),
    "difficulty_route_007_to_briefing": (
        0x43560,
        0x24010003,
        0x24010004,
        "Diagnostic-only route patch: with an all-missions save, do not treat the default 007 row as MENU_007_OPTIONS; let it fall through to MENU_BRIEFING.",
    ),
}

PROBES = [
    {
        "name": "t90path08",
        "purpose": "No-input probe: title/logo -> mission select -> forced accept -> difficulty.",
        "patches": ["timeout_to_mission_select", "mission_select_accept"],
    },
    {
        "name": "t90path0a",
        "purpose": "No-input probe: title/logo -> mission select -> forced accept -> difficulty -> forced accept -> briefing.",
        "patches": ["timeout_to_mission_select", "mission_select_accept", "difficulty_accept"],
    },
    {
        "name": "t90btn08",
        "purpose": "No-input probe: title/logo -> mission select -> forced mission accept block -> difficulty.",
        "patches": ["timeout_to_mission_select", "mission_select_force_button_accept"],
    },
    {
        "name": "t90btn0a",
        "purpose": "No-input probe: title/logo -> mission select -> forced mission accept block -> difficulty -> forced difficulty accept block -> briefing.",
        "patches": ["timeout_to_mission_select", "mission_select_force_button_accept", "difficulty_force_button_accept"],
    },
    {
        "name": "t90btn0b",
        "purpose": "No-input diagnostic: force mission and difficulty accept, then route the all-missions-save default 007 row to briefing instead of 007 options.",
        "patches": [
            "timeout_to_mission_select",
            "mission_select_force_button_accept",
            "difficulty_force_button_accept",
            "difficulty_route_007_to_briefing",
        ],
    },
    {
        "name": "t90btn0c",
        "purpose": "No-input diagnostic: force mission-state setup, then force the difficulty page-transition branch to briefing without depending on difficulty cursor hit testing.",
        "patches": [
            "timeout_to_mission_select",
            "mission_select_force_button_accept",
            "difficulty_accept",
            "difficulty_route_007_to_briefing",
        ],
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


def build_one(spec, base_rom, base, out_dir, prefix):
    rom = bytearray(base)
    applied = []
    for key in spec["patches"]:
        offset, expected_old, new, note = PATCH_LIBRARY[key]
        old = word(rom, offset)
        if old != expected_old:
            raise SystemExit(
                f"{spec['name']}: unexpected word at 0x{offset:X}: 0x{old:08X}, expected 0x{expected_old:08X}"
            )
        write_word(rom, offset, new)
        applied.append(
            {
                "key": key,
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{new:08X}",
                "note": note,
            }
        )
    crc1, crc2 = update_n64_crc_6102(rom)
    out_name = f"{prefix}{spec['name'][3:]}" if prefix and spec["name"].startswith("t90") else f"{prefix}{spec['name']}"
    out_rom = out_dir / f"{out_name}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": out_name,
        "purpose": spec["purpose"],
        "base_rom": str(base_rom),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": applied,
        "save_outputs": copy_save_pair(base_rom, out_rom),
        "do_not_promote": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=BASE_ROM)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--prefix", default="")
    args = parser.parse_args()

    if not args.base_rom.exists():
        raise SystemExit(f"missing base ROM: {args.base_rom}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    base = args.base_rom.read_bytes()
    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(base),
        "purpose": "No-controller route probes that preserve upstream menu initialization before later dossier pages.",
        "probes": [build_one(spec, args.base_rom, base, args.out_dir, args.prefix) for spec in PROBES],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
