#!/usr/bin/env python3
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/t8040viewge.z64")
BASE_SAVE = Path("artifacts/generated/t8040viewge.sav")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_t8040viewge_front_menu_candidates_20260517.json")

SLOW_TEXTURE_REPORT = Path(
    "reports/tnd480i_gamefulltop0_gbslow_shared_blitter_stock_texture_setup_20260511_report.json"
)
MENU05_09_REPORT = Path("reports/tnd480i_gbslow_menu05_09_safe_20260511_report.json")
MOVING_POST_REPORT = Path("reports/tnd480i_gbslow_menu05_09_moving_post_20260511_report.json")


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def parse_hex(value):
    if isinstance(value, int):
        return value
    return int(value, 16)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def patch_from_direct_word(entry, source):
    return {
        "source": source,
        "offset": parse_hex(entry["offset"]),
        "new": parse_hex(entry["new"]),
        "group": entry.get("group") or entry.get("range"),
        "note": entry.get("note", ""),
    }


def gather_patches(include_menu):
    patches = []
    slow_texture = load_json(SLOW_TEXTURE_REPORT)
    for entry in slow_texture["direct_word_patches"]:
        patches.append(patch_from_direct_word(entry, SLOW_TEXTURE_REPORT.name))

    moving = load_json(MOVING_POST_REPORT)
    for entry in moving["direct_word_patches"]:
        patches.append(patch_from_direct_word(entry, MOVING_POST_REPORT.name))

    if include_menu:
        menu = load_json(MENU05_09_REPORT)
        for entry in menu["safe_direct_words_applied"]:
            patches.append(patch_from_direct_word(entry, MENU05_09_REPORT.name))

    # Last writer wins if an offset appears twice, while preserving deterministic order.
    by_offset = {}
    for patch in patches:
        by_offset[patch["offset"]] = patch
    return [by_offset[offset] for offset in sorted(by_offset)]


def copy_save(out_rom):
    outputs = []
    if BASE_SAVE.exists():
        save_bytes = BASE_SAVE.read_bytes()
        out_sav = out_rom.with_suffix(".sav")
        out_eep = out_rom.with_suffix(".eep")
        out_sav.write_bytes(save_bytes)
        out_eep.write_bytes(save_bytes if len(save_bytes) >= 2048 else save_bytes + b"\0" * (2048 - len(save_bytes)))
        outputs.extend(
            [
                {"path": str(out_sav), "bytes": out_sav.stat().st_size, "md5": md5(out_sav.read_bytes())},
                {"path": str(out_eep), "bytes": out_eep.stat().st_size, "md5": md5(out_eep.read_bytes())},
            ]
        )
    return outputs


def build_one(name, purpose, include_menu):
    base = bytearray(BASE_ROM.read_bytes())
    patches = []
    for patch in gather_patches(include_menu):
        offset = patch["offset"]
        old = word(base, offset)
        write_word(base, offset, patch["new"])
        patches.append(
            {
                "source": patch["source"],
                "group": patch["group"],
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{patch['new']:08X}",
                "changed": old != patch["new"],
                "note": patch["note"],
            }
        )

    crc1, crc2 = update_n64_crc_6102(base)
    out_rom = OUT_DIR / f"{name}.z64"
    out_rom.write_bytes(base)
    return {
        "name": name,
        "purpose": purpose,
        "base_rom": str(BASE_ROM),
        "base_md5": md5(BASE_ROM.read_bytes()),
        "out_rom": str(out_rom),
        "out_md5": md5(base),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "include_menu05_09": include_menu,
        "patches": patches,
        "changed_patch_count": sum(1 for patch in patches if patch["changed"]),
        "save_outputs": copy_save(out_rom),
        "direct_probe_focus": ["Bazaar", "Party", "Hotel", "Volcano", "The End"],
    }


def main():
    if not BASE_ROM.exists():
        raise SystemExit(f"missing base ROM: {BASE_ROM}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reports = [
        build_one(
            "t8040vfront",
            (
                "t8040viewge gameplay baseline plus the old proven slow gunbarrel/front "
                "ingredients only: 3.625 title-X cadence, stock title/sniper texture setup, "
                "and post-matrix moving-barrel suppression. Does not touch the GE-sized "
                "menu05_09 layout block."
            ),
            include_menu=False,
        ),
        build_one(
            "t8040vfrontmenu",
            (
                "t8040viewge gameplay baseline plus slow gunbarrel/front ingredients and "
                "the menu05_09 GE-sized front/menu shell. TND mission content/mission count "
                "is preserved; this is a sizing/layout shell transplant, not a mission map transplant."
            ),
            include_menu=True,
        ),
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
