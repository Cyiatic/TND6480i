#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_render_state_revert_candidates import copy_save
from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/game_h460_top10_stock_dossier_tlb806b6_007label_current.z64")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_tlb90_fb8040_candidate_20260517.json")


FB8040_PATCHES = [
    (0x3D30, 0x3C048040, "clear fb0 base upper 0x80400000"),
    (0x6584, 0x3C048040, "fb0 global base upper 0x80400000"),
]

VIEWGE_PATCHES = [
    (0xBB89C, 0x240201F0, "GE 480i camera widescreen/fullscreen branch height 496"),
    (0xBB8B8, 0x2402017C, "GE 480i camera cinema/widescreen branch height 380"),
    (0xBB8C0, 0x24020260, "GE 480i camera fullscreen/cinema branch height 608"),
    (0xBB8FC, 0x24420168, "GE 480i camera animated widescreen height offset 360"),
    (0xBB91C, 0x240201B8, "GE 480i non-camera default viewport height 440"),
    (0xBB944, 0x24420110, "GE 480i camera animated cinema height offset 272"),
    (0xBB954, 0x240201B8, "GE 480i non-camera fallback viewport height 440"),
    (0xBBA60, 0x2442003C, "GE 480i camera animated widescreen top offset 60"),
    (0xBBA80, 0x24020014, "GE 480i non-camera default viewport top 20"),
    (0xBBAA8, 0x24420068, "GE 480i camera animated cinema top offset 104"),
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def build_one(name, extra_patches, purpose_suffix):
    base = BASE_ROM.read_bytes()
    rom = bytearray(base)
    patches = []
    for offset, new_value, note in FB8040_PATCHES + extra_patches:
        old_value = word(rom, offset)
        write_word(rom, offset, new_value)
        patches.append({
            "offset": f"0x{offset:X}",
            "old": f"0x{old_value:08X}",
            "new": f"0x{new_value:08X}",
            "changed": old_value != new_value,
            "note": note,
        })

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = OUT_DIR / f"{name}.z64"
    out_rom.write_bytes(rom)
    report = {
        "name": name,
        "purpose": (
            "Keep the 90-page TLB cache from the tlb806b6 branch, relocated below "
            "fb1, and add the fb0=0x80400000 level-boot fix. This is a performance "
            "canary intended to avoid the 58-page page-cache slowdown while keeping "
            "the all-level boot improvement from the tnd8040 line. " + purpose_suffix
        ),
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "tlb_cache_layout": {
            "page_count": 90,
            "page_size": "0x2000",
            "expected_expansion_range": "0x806B6000-0x80769FFF",
            "gap_to_fb1": 0,
        },
        "framebuffer_layout": {
            "fb0": "0x80400000-0x80495FFF",
            "fb1": "0x8076A000-0x807FFFFF",
        },
        "patches": patches,
        "save_outputs": copy_save(out_rom),
    }
    return report


def build():
    reports = [
        build_one(
            "t90fb8040",
            [],
            "This minimal canary leaves the camera/viewport constants as they were in the tlb806b6 branch.",
        ),
        build_one(
            "t90viewge",
            VIEWGE_PATCHES,
            "This full candidate also applies the later GE 480i camera and normal-viewport fit constants from t8040viewge.",
        ),
    ]
    REPORT.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    build()
