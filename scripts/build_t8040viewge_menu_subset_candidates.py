#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/t8040viewge.z64")
BASE_SAVE = Path("artifacts/generated/t8040viewge.sav")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_t8040viewge_menu_subset_candidates_20260517.json")

FRONT_REPORTS = [
    Path("reports/tnd480i_gamefulltop0_gbslow_shared_blitter_stock_texture_setup_20260511_report.json"),
    Path("reports/tnd480i_gbslow_menu05_09_moving_post_20260511_report.json"),
]
MENU_REPORT = Path("reports/tnd480i_gbslow_menu05_09_safe_20260511_report.json")

MENU_PTR_OFFSETS = {0x40540, 0x40544}
MENU_HELPER_BLOB = range(0x42F1C, 0x42F88, 4)


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def parse_hex(value):
    return value if isinstance(value, int) else int(value, 16)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def as_patch(entry, source):
    return {
        "source": source.name,
        "offset": parse_hex(entry["offset"]),
        "new": parse_hex(entry["new"]),
        "group": entry.get("group") or entry.get("range"),
        "note": entry.get("note", ""),
    }


def is_float_or_scale_word(patch):
    new = patch["new"]
    off = patch["offset"]
    if off in MENU_PTR_OFFSETS or off in MENU_HELPER_BLOB:
        return False
    if (new & 0xFFFF0000) == 0x3C010000:
        return True
    if (new & 0xFFFF0000) == 0x44810000:
        return True
    return False


def front_patches():
    patches = []
    for report in FRONT_REPORTS:
        data = load_json(report)
        for entry in data.get("direct_word_patches", []):
            patches.append(as_patch(entry, report))
    by_offset = {}
    for patch in patches:
        by_offset[patch["offset"]] = patch
    return [by_offset[offset] for offset in sorted(by_offset)]


def menu_patches(filter_name):
    report = load_json(MENU_REPORT)
    patches = [as_patch(entry, MENU_REPORT) for entry in report["safe_direct_words_applied"]]

    if filter_name == "minus_ptr":
        return [patch for patch in patches if patch["offset"] not in MENU_PTR_OFFSETS]
    if filter_name == "minus_helper":
        return [patch for patch in patches if patch["offset"] not in MENU_HELPER_BLOB]
    if filter_name == "minus_ptr_helper":
        return [
            patch
            for patch in patches
            if patch["offset"] not in MENU_PTR_OFFSETS and patch["offset"] not in MENU_HELPER_BLOB
        ]
    if filter_name == "scale_only":
        return [patch for patch in patches if is_float_or_scale_word(patch)]
    raise ValueError(filter_name)


def copy_save(out_rom):
    outputs = []
    if BASE_SAVE.exists():
        save = BASE_SAVE.read_bytes()
        for suffix, data in {
            ".sav": save,
            ".eep": save if len(save) >= 2048 else save + b"\0" * (2048 - len(save)),
        }.items():
            out = out_rom.with_suffix(suffix)
            out.write_bytes(data)
            outputs.append({"path": str(out), "bytes": out.stat().st_size, "md5": md5(data)})
    return outputs


def build_one(name, filter_name, purpose):
    rom = bytearray(BASE_ROM.read_bytes())
    patches = front_patches() + menu_patches(filter_name)
    by_offset = {}
    for patch in patches:
        by_offset[patch["offset"]] = patch
    applied = []
    for offset in sorted(by_offset):
        patch = by_offset[offset]
        old = word(rom, offset)
        write_word(rom, offset, patch["new"])
        applied.append(
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

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = OUT_DIR / f"{name}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": name,
        "filter": filter_name,
        "purpose": purpose,
        "base_rom": str(BASE_ROM),
        "base_md5": md5(BASE_ROM.read_bytes()),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patch_count": len(applied),
        "changed_patch_count": sum(1 for patch in applied if patch["changed"]),
        "patches": applied,
        "save_outputs": copy_save(out_rom),
    }


def main():
    variants = [
        (
            "t8040vmenusansptr",
            "minus_ptr",
            "Full GE-sized menu shell minus the two menu05_09 object/data pointer words at 0x40540/0x40544.",
        ),
        (
            "t8040vmenusanshelper",
            "minus_helper",
            "Full GE-sized menu shell minus the injected helper-code blob at 0x42F1C-0x42F84.",
        ),
        (
            "t8040vmenusafe",
            "minus_ptr_helper",
            "GE-sized menu shell minus both the suspect pointer words and helper-code blob.",
        ),
        (
            "t8040vmenuscales",
            "scale_only",
            "Only GE-style menu float/scale constants, preserving TND integer/object placements.",
        ),
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = [build_one(*variant) for variant in variants]
    REPORT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
