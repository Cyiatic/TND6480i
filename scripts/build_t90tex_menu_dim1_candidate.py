#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import DIRECT_PATCH_GROUPS, md5, update_n64_crc_6102


TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018
MENU_DIM1_OFFSET = 0x4F35C
MENU_DIM1_640_480 = 0x028001E0

ROUTES = [
    ("05", 0x05, "file select / save folders"),
    ("06", 0x06, "mode select"),
    ("07", 0x07, "mission select"),
    ("08", 0x08, "difficulty select"),
    ("0a", 0x0A, "briefing dossier"),
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
        outputs.append(
            {
                "source": str(source),
                "target": str(target),
                "bytes": len(payload),
                "md5": md5(payload),
            }
        )
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


def iter_extra_group_patches(groups):
    patches = {}
    for group in groups:
        for offset, value, note in DIRECT_PATCH_GROUPS[group]:
            patches[offset] = {"offset": offset, "new": value, "group": group, "note": note}
    for offset in sorted(patches):
        yield patches[offset]


def build_candidate(base_rom, base, out_dir, route_dir, name, extra_groups=None):
    extra_groups = extra_groups or []
    rom = bytearray(base)
    patches = []

    old = word(rom, MENU_DIM1_OFFSET)
    write_word(rom, MENU_DIM1_OFFSET, MENU_DIM1_640_480)
    patches.append(
        {
            "offset": f"0x{MENU_DIM1_OFFSET:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{MENU_DIM1_640_480:08X}",
            "changed": old != MENU_DIM1_640_480,
            "group": "menu_dim1",
            "note": "front/menu dimension table entry 1 width/height 640x480",
        }
    )

    for patch in iter_extra_group_patches(extra_groups):
        offset = patch["offset"]
        old = word(rom, offset)
        write_word(rom, offset, patch["new"])
        patches.append(
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
    out_rom = out_dir / f"{name}.z64"
    out_rom.write_bytes(rom)

    route_outputs = []
    for route_suffix, menu_id, route_purpose in ROUTES:
        route_rom = bytearray(rom)
        route_patch = add_direct_route(route_rom, menu_id)
        rcrc1, rcrc2 = update_n64_crc_6102(route_rom)
        route_path = route_dir / f"{name}auto{route_suffix}.z64"
        route_path.write_bytes(route_rom)
        route_outputs.append(
            {
                "route": route_suffix,
                "purpose": route_purpose,
                "out_rom": str(route_path),
                "out_md5": md5(route_rom),
                "header_crc": f"{rcrc1:08X} {rcrc2:08X}",
                "route_patch": route_patch,
            }
        )

    return {
        "name": name,
        "purpose": (
            "Patch only the second front/menu dimension table entry at 0x4F35C "
            "from 440x330 to 640x480. GE old/enhanced 480i both use this value; "
            "t90texstk only had the first entry widened."
        ),
        "base_rom": str(base_rom),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "extra_groups": extra_groups,
        "patch_count": len(patches),
        "changed_patch_count": sum(1 for patch in patches if patch["changed"]),
        "patches": patches,
        "save_outputs": copy_save_pair(base_rom, out_rom),
        "route_outputs": route_outputs,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/t90texstk.z64"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/generated"))
    parser.add_argument("--route-dir", type=Path, default=Path("artifacts/generated/menu_dim1_routes"))
    parser.add_argument("--name", default=None)
    parser.add_argument(
        "--include-buffer-sizes",
        action="store_true",
        help="Also apply the GE enhanced front/gunbarrel work-buffer size constants.",
    )
    parser.add_argument(
        "--include-skip-menu-fb",
        action="store_true",
        help="Also skip the menu framebuffer swap before applying the selected menu dimension table entry.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/tnd480i_t90tex_menu_dim1_candidate_20260518.json"),
    )
    args = parser.parse_args()

    if not args.base_rom.exists():
        raise SystemExit(f"missing base ROM: {args.base_rom}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.route_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    base = args.base_rom.read_bytes()
    specs = []
    if args.name:
        specs.append(
            {
                "name": args.name,
                "extra_groups": (
                    (["J_front_buffer_sizes_480i"] if args.include_buffer_sizes else [])
                    + (["J_front_skip_menu_framebuf_swap"] if args.include_skip_menu_fb else [])
                ),
            }
        )
    else:
        specs = [
            {"name": "txdim1", "extra_groups": []},
            {"name": "txdim1buf", "extra_groups": ["J_front_buffer_sizes_480i"]},
        ]

    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(base),
        "candidates": [
            build_candidate(
                args.base_rom,
                base,
                args.out_dir,
                args.route_dir,
                spec["name"],
                spec["extra_groups"],
            )
            for spec in specs
        ],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
