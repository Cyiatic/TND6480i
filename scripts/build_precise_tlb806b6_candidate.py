#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/game_h460_top10_stock_dossier_tables_007label_current.z64")
OUT_ROM = Path("artifacts/generated/game_h460_top10_stock_dossier_tlb806b6_007label_current.z64")
REPORT = Path("reports/tnd480i_game_h460_top10_stock_dossier_tlb806b6_007label_current_report.json")

DIRECT_BASE = 0x802B6000
EXPANSION_DELTA = 0x00400000
EXPANDED_BASE = DIRECT_BASE + EXPANSION_DELTA
TLB_CACHE_BYTES = 90 * 0x2000
FB1_BASE = 0x8076A000
FB1_BYTES = 0x96000


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def main():
    rom = bytearray(BASE_ROM.read_bytes())
    base_md5 = md5(rom)
    patches = []

    for offset, value, note in [
        (0x241C, 0x3C080000 | ((DIRECT_BASE >> 16) & 0xFFFF), "TLB cache direct base upper 0x802B6000"),
        (0x2420, 0x25080000 | (DIRECT_BASE & 0xFFFF), "TLB cache direct base lower 0x802B6000"),
    ]:
        old = word(rom, offset)
        write_word(rom, offset, value)
        patches.append({
            "offset": f"0x{offset:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{value:08X}",
            "note": note,
            "changed": old != value,
        })

    crc1, crc2 = update_n64_crc_6102(rom)
    OUT_ROM.parent.mkdir(parents=True, exist_ok=True)
    OUT_ROM.write_bytes(rom)

    expanded_end = EXPANDED_BASE + TLB_CACHE_BYTES - 1
    fb1_end = FB1_BASE + FB1_BYTES - 1
    report = {
        "name": OUT_ROM.stem,
        "purpose": (
            "Preserve the current active 007-label in-game-480i fallback, but move the "
            "Expansion Pak TLB page cache to the highest page-aligned base that ends "
            "immediately before fb1. This avoids the old cache/fb1 overlap while taking "
            "far less stage memory than tlb8060/tlb805c."
        ),
        "base_rom": str(BASE_ROM),
        "base_md5": base_md5,
        "out_rom": str(OUT_ROM),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "framebuffer_layout": {
            "fb0": "0x80300000-0x80395FFF",
            "fb1": f"0x{FB1_BASE:08X}-0x{fb1_end:08X}",
        },
        "tlb_cache_layout": {
            "direct_base_no_expansion_delta": f"0x{DIRECT_BASE:08X}",
            "expected_expansion_base": f"0x{EXPANDED_BASE:08X}",
            "expected_expansion_range": f"0x{EXPANDED_BASE:08X}-0x{expanded_end:08X}",
            "old_expected_expansion_range": "0x806F6000-0x807A9FFF",
            "gap_to_fb1": FB1_BASE - expanded_end - 1,
            "memory_preserved_vs_tlb8060": EXPANDED_BASE - 0x80600000,
        },
        "patches": patches,
        "notes": [
            "Only the direct TLB-base upper halfword changes; 0x2420 already used the needed lower 0x6000.",
            "The 0x806B6000-0x80769FFF cache range ends exactly before fb1 starts at 0x8076A000.",
            "This should be tested against Party/City/Credits load failures, Tower/Boat intros, Hotel/Volcano prism, and good control levels.",
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
