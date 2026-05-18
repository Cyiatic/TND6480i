#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/t90viewge.z64")
BASE_SAVE = Path("artifacts/generated/t90viewge.sav")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_t90_front_menu_canaries_20260518.json")

MENU_REPORT = Path("reports/tnd480i_gbslow_menu05_09_safe_20260511_report.json")

# These were already suspect on the t8040 menu-subset line: the pointer pair can
# erase save-select content, and the helper blob is too broad for a first t90 pass.
MENU_PTR_OFFSETS = {0x40540, 0x40544}
MENU_HELPER_BLOB = set(range(0x42F1C, 0x42F88, 4))


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def parse_hex(value):
    return value if isinstance(value, int) else int(value, 16)


def load_menu_patches():
    report = json.loads(MENU_REPORT.read_text(encoding="utf-8"))
    patches = []
    for entry in report["safe_direct_words_applied"]:
        patches.append(
            {
                "source": MENU_REPORT.name,
                "offset": parse_hex(entry["offset"]),
                "new": parse_hex(entry["new"]),
                "group": entry.get("group") or entry.get("range"),
                "note": entry.get("note", ""),
            }
        )
    return patches


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


def select_patches(kind):
    patches = load_menu_patches()
    safe = [
        patch
        for patch in patches
        if patch["offset"] not in MENU_PTR_OFFSETS
        and patch["offset"] not in MENU_HELPER_BLOB
    ]
    if kind == "scale_only":
        return [patch for patch in safe if is_float_or_scale_word(patch)]
    if kind == "placement_only":
        return [patch for patch in safe if not is_float_or_scale_word(patch)]
    if kind == "minus_ptr_helper":
        return safe
    raise ValueError(kind)


def copy_save(out_rom):
    outputs = []
    if not BASE_SAVE.exists():
        return outputs
    save = BASE_SAVE.read_bytes()
    payloads = {
        ".sav": save,
        ".eep": save if len(save) >= 2048 else save + b"\0" * (2048 - len(save)),
    }
    for suffix, data in payloads.items():
        out = out_rom.with_suffix(suffix)
        out.write_bytes(data)
        outputs.append({"path": str(out), "bytes": len(data), "md5": md5(data)})
    return outputs


def build_one(name, kind, purpose):
    base = BASE_ROM.read_bytes()
    rom = bytearray(base)
    by_offset = {patch["offset"]: patch for patch in select_patches(kind)}
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
        "kind": kind,
        "purpose": purpose,
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
    results = [
        build_one(
            "t90menuscales",
            "scale_only",
            "Current fast/playable t90viewge plus only GE-style menu float/scale words.",
        ),
        build_one(
            "t90menuplace",
            "placement_only",
            "Current fast/playable t90viewge plus menu05_09 placement/integer words, excluding scale words, pointer words, and helper blob.",
        ),
        build_one(
            "t90menusafe",
            "minus_ptr_helper",
            "Current fast/playable t90viewge plus menu05_09 safe shell minus the known-suspect pointer words and helper blob.",
        ),
    ]
    REPORT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
