#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_render_state_revert_candidates import copy_save
from build_tnd480i_candidate import DIRECT_PATCH_GROUPS, md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/t90viewge.z64")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_t90_front_resolution_canaries_20260518.json")

CANDIDATES = [
    {
        "name": "t90frontxy",
        "groups": ["J_front_visetxy_480i"],
        "purpose": "T90GE plus only front/menu viSetXY width/height 640x480.",
    },
    {
        "name": "t90frontbuf",
        "groups": ["J_front_visetbuf_480i"],
        "purpose": "T90GE plus only front/menu viSetBuf width/height 640x480.",
    },
    {
        "name": "t90frontxybuf",
        "groups": ["J_front_visetxybuf_480i"],
        "purpose": "T90GE plus front/menu viSetXY and viSetBuf width/height 640x480.",
    },
    {
        "name": "t90frontres",
        "groups": ["J_front_resolution_480i"],
        "purpose": "T90GE plus front/menu zbuffer, viSetXY, and viSetBuf width/height 640x480.",
    },
    {
        "name": "t90frontxybuf_mstxt",
        "groups": ["J_front_visetxybuf_480i", "J_mission_select_text_480i"],
        "purpose": "T90GE front/menu viSetXY+viSetBuf 640x480 plus the narrow mission-select text offsets.",
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def iter_group_patches(groups):
    by_offset = {}
    for group in groups:
        for offset, value, note in DIRECT_PATCH_GROUPS[group]:
            by_offset[offset] = {"group": group, "offset": offset, "new": value, "note": note}
    for offset in sorted(by_offset):
        yield by_offset[offset]


def build_one(spec, base):
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
    out_rom = OUT_DIR / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "groups": spec["groups"],
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patch_count": len(applied),
        "changed_patch_count": sum(1 for patch in applied if patch["changed"]),
        "patches": applied,
        "save_outputs": copy_save(out_rom),
    }


def main():
    if not BASE_ROM.exists():
        raise SystemExit(f"missing base ROM: {BASE_ROM}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    base = BASE_ROM.read_bytes()
    results = [build_one(spec, base) for spec in CANDIDATES]
    REPORT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
