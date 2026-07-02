#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/game_h460_top10_stock_dossier_tlb806b6_007label_current.z64")
STOCK_ROM = Path("artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64")
SAVE_SOURCE = BASE_ROM.with_suffix(".sav")
REPORT_DIR = Path("reports")
OUT_DIR = Path("artifacts/generated")


SPECS = [
    {
        "name": "game_h460_top10_stock_dossier_tlb806b6_noresfb_007label_current",
        "purpose": (
            "Diagnostic: preserve the active 640x480 in-game/camera dimensions, but "
            "disable the cameraBufferToggle redirect that sets the VI back framebuffer "
            "to the small stage 'resolution' buffer."
        ),
        "patches": [
            {
                "offset": 0xBBB8C,
                "value": 0x00000000,
                "note": "NOP jal viSetFrameBuf2(resolution); delay-slot resolution load is left harmless",
            }
        ],
        "notes": [
            "The active camera viewport words are 640x480, while the original resolution buffer allocation is stock-sized.",
            "If the redirect fires during Party/Credits/Tower/Boat intros, a 640x480 render can overrun that temporary stage buffer.",
            "This keeps the larger dimensions but forces camera rendering to stay on the normal fixed back framebuffer.",
        ],
    },
    {
        "name": "game_h460_top10_stock_dossier_tlb806b6_camviewstock_007label_current",
        "purpose": (
            "Conservative fallback: preserve the active TLB/007/in-game branch, but "
            "restore only the cameraBufferToggle viewport width/heights to stock TND."
        ),
        "patches": [
            {"offset": 0xBB7A4, "stock": True, "note": "camera viewport width 640 -> stock"},
            {"offset": 0xBB89C, "stock": True, "note": "camera widescreen viewport height 480 -> stock"},
            {"offset": 0xBB8B8, "stock": True, "note": "camera cinema viewport height 480 -> stock"},
            {"offset": 0xBB8C0, "stock": True, "note": "camera fullscreen viewport height 480 -> stock"},
        ],
        "notes": [
            "This gives up camera/cutscene 480i geometry first, prioritizing level playability.",
            "It should reduce pressure on the stock-sized resolution buffer if the redirect is required by those scenes.",
            "Use if noresfb boots but still leaves Party/Credits/Tower/Boat broken or visibly worse.",
        ],
    },
    {
        "name": "game_h460_top10_stock_dossier_tlb806b6_camstock_noresfb_007label_current",
        "purpose": (
            "Diagnostic combination: stock camera viewport dimensions plus disabled "
            "resolution-framebuffer redirect, leaving the active in-game 480i path intact."
        ),
        "patches": [
            {"offset": 0xBB7A4, "stock": True, "note": "camera viewport width 640 -> stock"},
            {"offset": 0xBB89C, "stock": True, "note": "camera widescreen viewport height 480 -> stock"},
            {"offset": 0xBB8B8, "stock": True, "note": "camera cinema viewport height 480 -> stock"},
            {"offset": 0xBB8C0, "stock": True, "note": "camera fullscreen viewport height 480 -> stock"},
            {
                "offset": 0xBBB8C,
                "value": 0x00000000,
                "note": "NOP jal viSetFrameBuf2(resolution)",
            },
        ],
        "notes": [
            "This is a last-resort diagnostic, not the first hardware upload.",
            "It is intentionally reversible and narrowly scoped to the camera framebuffer/viewport family.",
        ],
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def build_one(base, stock, spec):
    rom = bytearray(base)
    patches = []
    for patch in spec["patches"]:
        offset = patch["offset"]
        old = word(rom, offset)
        new = word(stock, offset) if patch.get("stock") else patch["value"]
        write_word(rom, offset, new)
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{new:08X}",
                "note": patch["note"],
                "changed": old != new,
            }
        )

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = OUT_DIR / f"{spec['name']}.z64"
    out_rom.parent.mkdir(parents=True, exist_ok=True)
    out_rom.write_bytes(rom)

    if SAVE_SOURCE.exists():
        out_rom.with_suffix(".sav").write_bytes(SAVE_SOURCE.read_bytes())
        eep = SAVE_SOURCE.read_bytes()
        if len(eep) < 2048:
            eep = eep + b"\0" * (2048 - len(eep))
        out_rom.with_suffix(".eep").write_bytes(eep)

    report = {
        "name": spec["name"],
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "stock_source_rom": str(STOCK_ROM),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": spec["purpose"],
        "patches": patches,
        "notes": spec["notes"],
        "hardware_priority": (
            "Test noresfb first. If it changes Party/Credits from rectangle-lock to loadable, keep iterating there. "
            "If it regresses normal gameplay, immediately restore the active tlb806b6 ROM."
        ),
    }
    report_path = REPORT_DIR / f"tnd480i_{spec['name']}_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    base = BASE_ROM.read_bytes()
    stock = STOCK_ROM.read_bytes()
    reports = [build_one(base, stock, spec) for spec in SPECS]
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
