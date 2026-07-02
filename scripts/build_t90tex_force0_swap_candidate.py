#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018

ROUTES = [
    ("05", 0x05, "file select / save folders"),
    ("06", 0x06, "mode select"),
    ("07", 0x07, "mission select"),
]

CANDIDATES = [
    {
        "name": "txf0swap",
        "purpose": (
            "Force the front/menu VI table index to 0, but NOP the immediate "
            "beqz so the normal menu-framebuffer swap path can still run."
        ),
        "patches": [
            (0x4F1B8, 0x00008025, "force s0/table index to 0"),
            (0x4F1BC, 0x00000000, "do not branch around the menu-framebuffer swap path"),
        ],
    },
    {
        "name": "txf0swapbuf",
        "purpose": (
            "Force table 0 with the swap path intact, plus GE-sized front work buffers."
        ),
        "patches": [
            (0x4F1B8, 0x00008025, "force s0/table index to 0"),
            (0x4F1BC, 0x00000000, "do not branch around the menu-framebuffer swap path"),
            (0x3FC90, 0x3C05000B, "front/gunbarrel work buffer size upper for 0xBE200"),
            (0x3FC94, 0x34A5E200, "front/gunbarrel work buffer size lower for 0xBE200"),
            (0x40540, 0x3C0E000B, "front state/work buffer size upper for 0xB4200"),
            (0x40544, 0x35CE4200, "front state/work buffer size lower for 0xB4200"),
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


def add_direct_route(rom, menu_id):
    old = word(rom, TIMEOUT_MENU_WORD_OFFSET)
    if old != EXPECTED_TIMEOUT_WORD:
        raise ValueError(
            f"unexpected route word at 0x{TIMEOUT_MENU_WORD_OFFSET:X}: "
            f"0x{old:08X}, expected 0x{EXPECTED_TIMEOUT_WORD:08X}"
        )
    new = 0x24040000 | menu_id
    write_word(rom, TIMEOUT_MENU_WORD_OFFSET, new)
    return {"offset": f"0x{TIMEOUT_MENU_WORD_OFFSET:X}", "old": f"0x{old:08X}", "new": f"0x{new:08X}"}


def build_one(spec, base_rom, base, out_dir, route_dir):
    rom = bytearray(base)
    applied = []
    for offset, value, note in spec["patches"]:
        old = word(rom, offset)
        write_word(rom, offset, value)
        applied.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{value:08X}",
                "changed": old != value,
                "note": note,
            }
        )

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = out_dir / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)

    route_outputs = []
    for suffix, menu_id, purpose in ROUTES:
        route_rom = bytearray(rom)
        route_patch = add_direct_route(route_rom, menu_id)
        rcrc1, rcrc2 = update_n64_crc_6102(route_rom)
        route_path = route_dir / f"{spec['name']}auto{suffix}.z64"
        route_path.write_bytes(route_rom)
        route_outputs.append(
            {
                "route": suffix,
                "purpose": purpose,
                "out_rom": str(route_path),
                "out_md5": md5(route_rom),
                "header_crc": f"{rcrc1:08X} {rcrc2:08X}",
                "route_patch": route_patch,
            }
        )

    return {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "base_rom": str(base_rom),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patch_count": len(applied),
        "changed_patch_count": sum(1 for patch in applied if patch["changed"]),
        "patches": applied,
        "save_outputs": copy_save_pair(base_rom, out_rom),
        "route_outputs": route_outputs,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/t90texstk.z64"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/generated"))
    parser.add_argument("--route-dir", type=Path, default=Path("artifacts/generated/force0_swap_routes"))
    parser.add_argument("--report", type=Path, default=Path("reports/tnd480i_t90tex_force0_swap_candidates_20260518.json"))
    args = parser.parse_args()

    if not args.base_rom.exists():
        raise SystemExit(f"missing base ROM: {args.base_rom}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.route_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    base = args.base_rom.read_bytes()
    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(base),
        "candidates": [build_one(spec, args.base_rom, base, args.out_dir, args.route_dir) for spec in CANDIDATES],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
