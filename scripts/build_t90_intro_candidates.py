#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_render_state_revert_candidates import copy_save
from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/t90viewge.z64")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_t90_intro_candidates_20260518.json")

PATCH_SETS = {
    "gb_slow": [
        (0x3DF04, 0x3C014068, "gunbarrel case-1 x decrement 3.625 upper"),
        (0x3DF08, 0x44814000, "gunbarrel case-1 x decrement move to f8"),
    ],
    "gb_post_dl": [
        (0x3C68C, 0x240F0000, "disable second moving gunbarrel display-list command"),
    ],
    "tex_stock": [
        (0x4FDEC, 0x3C17070D, "stock shared title/sniper texture setup upper"),
        (0x4FDFC, 0x3C0AE46D, "stock shared title/sniper texture rectangle target width"),
        (0x4FE34, 0x3C018005, "stock shared title/sniper height load upper"),
        (0x4FE3C, 0x36F7B026, "stock shared title/sniper texture setup lower"),
        (0x4FE44, 0xC4301CF0, "stock shared title/sniper height load/use"),
        (0x4FF00, 0x3C0E006D, "stock shared title/sniper texture rectangle lower width"),
    ],
    "blitter_stock": [
        (0x4FDEC, 0x3C17070D, "stock shared title/sniper texture setup upper"),
        (0x4FDFC, 0x3C0AE46D, "stock shared title/sniper texture rectangle target width"),
        (0x4FE34, 0x3C018005, "stock shared title/sniper height load upper"),
        (0x4FE3C, 0x36F7B026, "stock shared title/sniper texture setup lower"),
        (0x4FE44, 0xC4301CF0, "stock shared title/sniper height load/use"),
        (0x4FF00, 0x3C0E006D, "stock shared title/sniper texture rectangle lower width"),
        (0x500EC, 0x25190011, "stock shared title/sniper negative-x strip step"),
        (0x500FC, 0x250E0010, "stock shared title/sniper negative-x strip step"),
        (0x50148, 0x25190011, "stock shared title/sniper positive-x strip step"),
        (0x50168, 0x25190010, "stock shared title/sniper positive-x strip step"),
        (0x501AC, 0x2921012C, "stock shared title/sniper source row loop limit"),
        (0x501B4, 0x261001B8, "stock shared title/sniper source stride"),
    ],
}

CANDIDATES = [
    {
        "name": "t90gbslow",
        "sets": ["gb_slow"],
        "purpose": "T90GE plus only the known gunbarrel case-1 slowdown timing diagnostic.",
    },
    {
        "name": "t90gbpost",
        "sets": ["gb_post_dl"],
        "purpose": "T90GE plus only the post-matrix moving-barrel display-list suppression diagnostic.",
    },
    {
        "name": "t90gbcombo",
        "sets": ["gb_slow", "gb_post_dl"],
        "purpose": "T90GE plus slowdown timing and post-matrix moving-barrel suppression.",
    },
    {
        "name": "t90texstk",
        "sets": ["tex_stock"],
        "purpose": "T90GE with only the shared title/sniper texture setup restored to stock TND.",
    },
    {
        "name": "t90gbslowtex",
        "sets": ["gb_slow", "tex_stock"],
        "purpose": "T90GE plus GE-like gunbarrel case-1 slowdown and stock shared title/sniper texture setup.",
    },
    {
        "name": "t90gbposttex",
        "sets": ["gb_post_dl", "tex_stock"],
        "purpose": "T90GE plus post-matrix moving-barrel suppression and stock shared title/sniper texture setup.",
    },
    {
        "name": "t90gbtexpost",
        "sets": ["gb_slow", "gb_post_dl", "tex_stock"],
        "purpose": "T90GE plus the earlier useful front-end trio: slowdown, post-matrix suppression, and stock texture setup.",
    },
    {
        "name": "t90blstk",
        "sets": ["blitter_stock"],
        "purpose": "T90GE with the full shared title/sniper blitter geometry cluster restored to stock TND.",
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def selected_patches(spec):
    patches = {}
    for patch_set in spec["sets"]:
        for offset, value, note in PATCH_SETS[patch_set]:
            patches[offset] = {
                "offset": offset,
                "new": value,
                "set": patch_set,
                "note": note,
            }
    return [patches[offset] for offset in sorted(patches)]


def build_one(spec, base):
    rom = bytearray(base)
    applied = []
    for patch in selected_patches(spec):
        offset = patch["offset"]
        old = word(rom, offset)
        write_word(rom, offset, patch["new"])
        applied.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{patch['new']:08X}",
                "changed": old != patch["new"],
                "set": patch["set"],
                "note": patch["note"],
            }
        )
    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = OUT_DIR / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "sets": spec["sets"],
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
