#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import DIRECT_PATCH_GROUPS, md5, update_n64_crc_6102


TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018

ROUTES = [
    ("05", 0x05, "file select / save folders"),
    ("06", 0x06, "mode select"),
    ("07", 0x07, "mission select"),
]

CANDIDATES = [
    {
        "name": "txlay43a",
        "groups": ["J_front_layout_43a_480i"],
        "purpose": "Front/menu 43a Y-layout cluster only.",
    },
    {
        "name": "txlay460",
        "groups": ["J_front_layout_460_480i"],
        "purpose": "Front/menu computed rectangle cluster only.",
    },
    {
        "name": "txlayfloat",
        "groups": ["J_front_layout_float_480i"],
        "purpose": "Front/menu float layout constants only.",
    },
    {
        "name": "txlayy",
        "groups": ["J_front_layout_y_480i"],
        "purpose": "Front/menu y-offset cluster only.",
    },
    {
        "name": "txlay4aaa",
        "groups": ["J_front_layout_4aaa_480i"],
        "purpose": "Front/menu 4aaa x/y/draw-width cluster only.",
    },
    {
        "name": "txlay43ay",
        "groups": ["J_front_layout_43a_480i", "J_front_layout_y_480i"],
        "purpose": "43a Y-layout cluster plus y-offset cluster.",
    },
    {
        "name": "txlaysafe",
        "groups": ["J_front_layout_43a_480i", "J_front_layout_4aaa_480i", "J_front_layout_gridstep_480i"],
        "purpose": "Previously labeled safe front layout cluster: 43a + 4aaa + grid steps.",
    },
    {
        "name": "txlayall",
        "groups": ["J_front_layout_no_rectloop_480i"],
        "purpose": "Full GE480i front layout cluster, excluding framebuffer/dim1 changes.",
    },
    {
        "name": "txlayallbuf",
        "groups": ["J_front_layout_no_rectloop_480i", "J_front_buffer_sizes_480i"],
        "purpose": "Full GE480i front layout cluster plus GE-sized front work buffers.",
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


def apply_groups(base, groups):
    rom = bytearray(base)
    applied = []
    for group in groups:
        for offset, value, note in DIRECT_PATCH_GROUPS[group]:
            old = word(rom, offset)
            write_word(rom, offset, value)
            applied.append(
                {
                    "group": group,
                    "offset": f"0x{offset:X}",
                    "old": f"0x{old:08X}",
                    "new": f"0x{value:08X}",
                    "changed": old != value,
                    "note": note,
                }
            )
    return rom, applied


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


def build_candidate(spec, base_rom, base, out_dir, route_dir):
    rom, applied = apply_groups(base, spec["groups"])
    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = out_dir / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)

    route_outputs = []
    for route_suffix, menu_id, route_purpose in ROUTES:
        route_rom = bytearray(rom)
        route_patch = add_direct_route(route_rom, menu_id)
        rcrc1, rcrc2 = update_n64_crc_6102(route_rom)
        route_path = route_dir / f"{spec['name']}auto{route_suffix}.z64"
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
        "name": spec["name"],
        "purpose": spec["purpose"],
        "groups": spec["groups"],
        "base_rom": str(base_rom),
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
    parser.add_argument("--route-dir", type=Path, default=Path("artifacts/generated/front_layout_routes"))
    parser.add_argument("--report", type=Path, default=Path("reports/tnd480i_t90tex_front_layout_candidates_20260518.json"))
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
        "purpose": "Isolate GE enhanced 480i front-layout spacing clusters on the stable t90texstk gameplay baseline.",
        "candidates": [build_candidate(spec, args.base_rom, base, args.out_dir, args.route_dir) for spec in CANDIDATES],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.report), "candidates": [item["name"] for item in report["candidates"]]}, indent=2))


if __name__ == "__main__":
    main()
