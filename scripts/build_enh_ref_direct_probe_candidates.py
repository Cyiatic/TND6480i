#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import DIRECT_PATCH_GROUPS, md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/roms/TND64_enh480i_core_no_menu_pigz.z64")
OUT_DIR = Path("artifacts/generated")
REPORT_PATH = Path("reports/tnd480i_enh_ref_direct_probe_candidates_20260516.json")


CUSTOM_GAMEVIEW_H460_TOP10 = [
    (0xBB91C, 0x240201CC, "direct non-camera default viewport height 460"),
    (0xBB954, 0x240201CC, "direct non-camera fallback viewport height 460"),
    (0xBBA80, 0x2402000A, "direct non-camera viewport top 10"),
]


SPECS = [
    {
        "name": "TND64_enh480i_ref_direct_gameview_h460_top10_nodim_probe",
        "purpose": (
            "Start from the clean enhanced-reference visual path and add only "
            "direct gameplay viewport helpers plus the h460/top10 non-camera "
            "crop, leaving direct render dimension words and framebuffer/VI "
            "hooks stock."
        ),
        "groups": [
            "I_gameplay_xy_480i",
            "I_gameplay_tnd_default_width_480i",
        ],
        "custom": CUSTOM_GAMEVIEW_H460_TOP10,
    },
    {
        "name": "TND64_enh480i_ref_direct_dim0_probe",
        "purpose": (
            "Start from the clean enhanced-reference visual path and add only the "
            "first direct render-dimension word that previously mattered for "
            "Bond-hand/true-480i checks."
        ),
        "groups": ["E_direct_dim0"],
        "custom": [],
    },
    {
        "name": "TND64_enh480i_ref_direct_gameview_h460_top10_probe",
        "purpose": (
            "Start from the clean enhanced-reference visual path and add the "
            "direct gameplay viewport helpers plus the current h460/top10 "
            "non-camera crop, while leaving camera viewports and framebuffer/VI "
            "hooks stock."
        ),
        "groups": [
            "E_direct_dim0",
            "I_gameplay_xy_480i",
            "I_gameplay_tnd_default_width_480i",
        ],
        "custom": CUSTOM_GAMEVIEW_H460_TOP10,
    },
    {
        "name": "TND64_enh480i_ref_direct_split8030_nodim_probe",
        "purpose": (
            "Start from the clean enhanced-reference visual path and add only "
            "the split8030/8076 framebuffer family, leaving direct dimension "
            "and direct gameplay viewport words stock."
        ),
        "groups": [
            "A_split_load_two_globals",
            "B_clear_split_8030_8076",
            "C_split_select_global",
            "D_fb_split_8030_8076",
        ],
        "custom": [],
    },
    {
        "name": "TND64_enh480i_ref_direct_split8030_dim0_probe",
        "purpose": (
            "Start from the clean enhanced-reference visual path and add split "
            "framebuffers plus direct dim0, leaving direct gameplay viewport "
            "words stock."
        ),
        "groups": [
            "A_split_load_two_globals",
            "B_clear_split_8030_8076",
            "C_split_select_global",
            "D_fb_split_8030_8076",
            "E_direct_dim0",
        ],
        "custom": [],
    },
    {
        "name": "TND64_enh480i_ref_direct_split8030_gameview_h460_top10_nodim_probe",
        "purpose": (
            "Start from the clean enhanced-reference visual path and add split "
            "framebuffers plus direct gameplay viewport helpers, but no direct "
            "render dimension word."
        ),
        "groups": [
            "A_split_load_two_globals",
            "B_clear_split_8030_8076",
            "C_split_select_global",
            "D_fb_split_8030_8076",
            "I_gameplay_xy_480i",
            "I_gameplay_tnd_default_width_480i",
        ],
        "custom": CUSTOM_GAMEVIEW_H460_TOP10,
    },
    {
        "name": "TND64_enh480i_ref_direct_gameview_h460_top10_split8030_probe",
        "purpose": (
            "Higher-risk probe: clean enhanced-reference base plus direct dim0, "
            "direct gameplay viewport, and the split8030/8076 framebuffer family. "
            "This deliberately omits the GE H origin/width/scale direct VI family."
        ),
        "groups": [
            "A_split_load_two_globals",
            "B_clear_split_8030_8076",
            "C_split_select_global",
            "D_fb_split_8030_8076",
            "E_direct_dim0",
            "I_gameplay_xy_480i",
            "I_gameplay_tnd_default_width_480i",
        ],
        "custom": CUSTOM_GAMEVIEW_H460_TOP10,
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def build_one(base, spec):
    rom = bytearray(base)
    patches = []
    for group in spec["groups"]:
        for offset, value, note in DIRECT_PATCH_GROUPS[group]:
            old = word(rom, offset)
            write_word(rom, offset, value)
            patches.append(
                {
                    "group": group,
                    "offset": f"0x{offset:X}",
                    "old": f"0x{old:08X}",
                    "new": f"0x{value:08X}",
                    "note": note,
                }
            )
    for offset, value, note in spec["custom"]:
        old = word(rom, offset)
        write_word(rom, offset, value)
        patches.append(
            {
                "group": "custom_h460_top10",
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{value:08X}",
                "note": note,
            }
        )

    update_n64_crc_6102(rom)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_rom = OUT_DIR / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)

    return {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{word(rom, 0x10):08X} {word(rom, 0x14):08X}",
        "patches": patches,
        "notes": [
            "These probes are deliberately based on the clean enhanced-reference route.",
            "They should be emulator-smoked before any hardware upload.",
            "They do not include front/menu/title draw experiments or GE H-family VI hooks.",
        ],
    }


def main():
    base = BASE_ROM.read_bytes()
    reports = [build_one(base, spec) for spec in SPECS]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
