#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import DIRECT_PATCH_GROUPS, md5, update_n64_crc_6102


CANDIDATES = [
    {
        "name": "txskipfb",
        "groups": ["J_front_skip_menu_framebuf_swap"],
        "purpose": "Keep t90texstk but skip the menu-framebuffer swap gate at 0x4F1C4.",
    },
    {
        "name": "txforce0",
        "groups": ["J_front_force_menu_table0_480i"],
        "purpose": "Keep t90texstk but force the front/menu VI table index to 0.",
    },
    {
        "name": "txgate",
        "groups": ["J_front_force_menu_table0_480i", "J_front_skip_menu_framebuf_swap"],
        "purpose": "Force menu table 0 and skip the menu-framebuffer swap together.",
    },
    {
        "name": "txfrontz",
        "groups": ["J_front_zbuffer_480i"],
        "purpose": "Keep t90texstk but change only the front zbuffer dimensions to 640x480.",
    },
    {
        "name": "txzgate",
        "groups": ["J_front_zbuffer_480i", "J_front_skip_menu_framebuf_swap"],
        "purpose": "Front zbuffer 640x480 plus skip-menu-framebuffer-swap gate.",
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def iter_group_patches(groups):
    patches = {}
    for group in groups:
        for offset, value, note in DIRECT_PATCH_GROUPS[group]:
            patches[offset] = {"offset": offset, "new": value, "group": group, "note": note}
    for offset in sorted(patches):
        yield patches[offset]


def copy_save_pair(base_rom, out_rom):
    outputs = []
    for suffix in (".sav", ".eep"):
        source = base_rom.with_suffix(suffix)
        target = out_rom.with_suffix(suffix)
        if not source.exists():
            outputs.append({"source": str(source), "target": str(target), "missing": True})
            continue
        shutil.copy2(source, target)
        data = target.read_bytes()
        outputs.append({"source": str(source), "target": str(target), "bytes": len(data), "md5": md5(data)})
    return outputs


def build_one(spec, base_rom, base, out_dir):
    rom = bytearray(base)
    applied = []
    for patch in iter_group_patches(spec["groups"]):
        offset = patch["offset"]
        old = word(rom, offset)
        write_word(rom, offset, patch["new"])
        applied.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{patch['new']:08X}",
                "changed": old != patch["new"],
                "group": patch["group"],
                "note": patch["note"],
            }
        )
    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = out_dir / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "groups": spec["groups"],
        "base_rom": str(base_rom),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patch_count": len(applied),
        "changed_patch_count": sum(1 for patch in applied if patch["changed"]),
        "patches": applied,
        "save_outputs": copy_save_pair(base_rom, out_rom),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/t90texstk.z64"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/generated"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/tnd480i_t90tex_front_gate_candidates_20260518.json"),
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
        "purpose": "Narrow front/menu framebuffer gate probes on stable t90texstk; capture on hardware against GE480i before promotion.",
        "candidates": [build_one(spec, args.base_rom, base, args.out_dir) for spec in CANDIDATES],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
