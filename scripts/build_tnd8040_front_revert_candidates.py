#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_render_state_revert_candidates import copy_save
from build_tnd480i_candidate import DIRECT_PATCH_GROUPS, md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/tnd8040.z64")
REFERENCE_ROM = Path("artifacts/roms/TND64_enh480i_core_no_menu_pigz.z64")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_tnd8040_front_revert_candidates_20260517.json")


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def offsets_for_groups(groups):
    offsets = {}
    for group in groups:
        for offset, _value, note in DIRECT_PATCH_GROUPS[group]:
            offsets.setdefault(offset, []).append({"group": group, "note": note})
    return offsets


CANDIDATES = [
    {
        "name": "t8040frstk",
        "purpose": (
            "Keep the tnd8040 gameplay/framebuffer core, but restore only the raw "
            "front-end viSetXY/viSetBuf and expanded-menu dimension words to the "
            "enhanced-reference/stock direct values. This tests whether the short "
            "level-title/cutscene rectangle is front display-state leakage."
        ),
        "groups": [
            "J_front_visetxybuf_480i",
            "J_expanded_menu_resolution_480i",
        ],
    },
    {
        "name": "t8040frblstk",
        "purpose": (
            "Keep the tnd8040 gameplay/framebuffer core, restore front/menu VI words, "
            "and also restore the shared title/sniper blitter geometry cluster to "
            "the enhanced-reference/stock direct values. This combines the previous "
            "blitter rollback with a front display-state rollback."
        ),
        "groups": [
            "J_front_visetxybuf_480i",
            "J_expanded_menu_resolution_480i",
            "K_title_draw_ge480_target_asset640_height430",
        ],
    },
    {
        "name": "t8040uistk",
        "purpose": (
            "Broader UI/front rollback on top of tnd8040: restore every direct word "
            "covered by J_front_title_480i plus the shared title/sniper blitter words. "
            "This is a playability diagnostic and may intentionally return front/menu "
            "screens to stock-scaled behavior."
        ),
        "groups": [
            "J_front_title_480i",
            "K_title_draw_ge480_target_asset640_height430",
        ],
    },
]


def build_one(spec, base, reference):
    rom = bytearray(base)
    patches = []
    for offset, refs in sorted(offsets_for_groups(spec["groups"]).items()):
        old = word(rom, offset)
        new = word(reference, offset)
        write_word(rom, offset, new)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{new:08X}",
                "changed": old != new,
                "refs": refs,
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
        "reference_rom": str(REFERENCE_ROM),
        "reference_md5": md5(reference),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": patches,
        "changed_patch_count": sum(1 for patch in patches if patch["changed"]),
        "save_outputs": copy_save(out_rom),
        "direct_probe_focus": ["Party", "The End", "Bazaar"],
    }


def main():
    base = BASE_ROM.read_bytes()
    reference = REFERENCE_ROM.read_bytes()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reports = [build_one(spec, base, reference) for spec in CANDIDATES]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
