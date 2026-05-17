#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102
from build_t8040viewge_menu_subset_candidates import (
    BASE_ROM,
    BASE_SAVE,
    OUT_DIR,
    menu_patches,
)


REPORT = Path("reports/tnd480i_t8040viewge_menu_scale_bisect_20260517.json")

GROUPS = [
    ("t8040ms00_02", range(0, 3), "First scale-load triplet around 0x419F0-0x41A10."),
    ("t8040ms03_06", range(3, 7), "Second/third scale-load pair around 0x41B24-0x41B34."),
    ("t8040ms07_09", range(7, 10), "Scale-load triplet around 0x41C30-0x41C48."),
    ("t8040ms10_13", range(10, 14), "Late 0x41F54-0x42338 menu constants."),
    ("t8040ms14_18", range(14, 19), "0x433FC-0x438A8 menu constants."),
    ("t8040ms19_25", range(19, 26), "Repeated lower menu constants from 0x43D0C-0x44A08."),
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


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


def build_one(name, indexes, purpose, all_patches):
    rom = bytearray(BASE_ROM.read_bytes())
    selected = [all_patches[index] for index in indexes]
    applied = []
    for index, patch in zip(indexes, selected):
        offset = patch["offset"]
        old = word(rom, offset)
        write_word(rom, offset, patch["new"])
        applied.append(
            {
                "index": index,
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{patch['new']:08X}",
                "changed": old != patch["new"],
                "source": patch["source"],
                "group": patch["group"],
            }
        )

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = OUT_DIR / f"{name}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": name,
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_patches = menu_patches("scale_only")
    results = [build_one(name, indexes, purpose, all_patches) for name, indexes, purpose in GROUPS]
    REPORT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
