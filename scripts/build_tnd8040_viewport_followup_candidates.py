#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_render_state_revert_candidates import copy_save
from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/tnd8040.z64")
OUT_DIR = Path("artifacts/generated")
REPORT = Path("reports/tnd480i_tnd8040_viewport_followup_candidates_20260517.json")


PATCH_SETS = {
    "camera_ge_heights": [
        (0xBB89C, 0x240201F0, "GE 480i camera widescreen/fullscreen branch height 496"),
        (0xBB8B8, 0x2402017C, "GE 480i camera cinema/widescreen branch height 380"),
        (0xBB8C0, 0x24020260, "GE 480i camera fullscreen/cinema branch height 608"),
        (0xBB8FC, 0x24420168, "GE 480i camera animated widescreen height offset 360"),
        (0xBB944, 0x24420110, "GE 480i camera animated cinema height offset 272"),
        (0xBBA60, 0x2442003C, "GE 480i camera animated widescreen top offset 60"),
        (0xBBAA8, 0x24420068, "GE 480i camera animated cinema top offset 104"),
    ],
    "noncamera_ge_default": [
        (0xBB91C, 0x240201B8, "GE 480i non-camera default viewport height 440"),
        (0xBB954, 0x240201B8, "GE 480i non-camera fallback viewport height 440"),
        (0xBBA80, 0x24020014, "GE 480i non-camera default viewport top 20"),
    ],
}


CANDIDATES = [
    {
        "name": "t8040camge",
        "purpose": (
            "Keep the tnd8040 framebuffer/playability breakthrough, but replace only "
            "the camera/cinema viewport height and animated offset constants with "
            "GE 480i values. This tests whether short level-intro/cutscene framing "
            "comes from flattening all TND camera heights to 480."
        ),
        "sets": ["camera_ge_heights"],
    },
    {
        "name": "t8040viewge",
        "purpose": (
            "Apply GE 480i camera/cinema viewport constants plus GE non-camera "
            "default height/top. This is broader than camge and may affect normal "
            "gameplay fit, so it is emulator/direct-probe first only."
        ),
        "sets": ["camera_ge_heights", "noncamera_ge_default"],
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def iter_patches(names):
    seen = {}
    for name in names:
        for offset, value, note in PATCH_SETS[name]:
            seen[offset] = (name, value, note)
    for offset in sorted(seen):
        yield offset, *seen[offset]


def build_one(spec, base):
    rom = bytearray(base)
    patches = []
    for offset, set_name, value, note in iter_patches(spec["sets"]):
        old = word(rom, offset)
        write_word(rom, offset, value)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{value:08X}",
                "changed": old != value,
                "set": set_name,
                "note": note,
            }
        )
    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = OUT_DIR / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": patches,
        "save_outputs": copy_save(out_rom),
        "direct_probe_focus": ["Party", "Bazaar", "The End"],
    }


def main():
    base = BASE_ROM.read_bytes()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reports = [build_one(spec, base) for spec in CANDIDATES]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
