#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


CURRENT_BEST = Path("artifacts/generated/game_h460_top10_stock_dossier_tables_current.z64")
CAMVIEW_BASE = Path("artifacts/generated/game_h460_top10_stock_dossier_camviewstock_current.z64")


OUT_SPECS = [
    {
        "name": "game_h460_top10_stock_dossier_gefb_current",
        "base": CURRENT_BEST,
        "purpose": (
            "Preserve current best gameplay/dossier work, but replace the split "
            "0x80300000/0x8076A000 framebuffer package with GE-style contiguous "
            "top-of-RDRAM framebuffers."
        ),
    },
    {
        "name": "game_h460_top10_stock_dossier_gefb_camviewstock_current",
        "base": CAMVIEW_BASE,
        "purpose": (
            "Same safe framebuffer package, starting from the camera-view-stock "
            "diagnostic base."
        ),
    },
]


PATCHES = [
    # viInitVideoSettings: make g_ViBackData->framebuf = fb0 + 0x96000
    # again, instead of loading the second split framebuffer global.
    (0x3C8C, 0x3C010009, "init stride upper 0x96000"),
    (0x3C90, 0x24216000, "init stride lower 0x96000"),
    (0x3C94, 0x01214821, "init add stride to fb0"),

    # viInitBuffers: GE clears one contiguous 0x12C000 region from
    # 0x806D4000 through 0x807FFFFF. This avoids current fb0 overlap with
    # the TLB paging cache around 0x802F6000-0x803AA000.
    (0x3D30, 0x3C048080, "clear base upper 0x80800000"),
    (0x3D34, 0x00000000, "clear old osMemSize load"),
    (0x3D38, 0x00000000, "clear old K0 conversion"),
    (0x3D3C, 0x3C050012, "clear size upper 0x12C000"),
    (0x3D40, 0x34A5C000, "clear size lower 0x12C000"),
    (0x3D44, 0x0C005F10, "clear contiguous framebuffer range"),
    (0x3D48, 0x00852023, "clear start = 0x80800000 - 0x12C000"),
    (0x3D4C, 0x8FBF0014, "restore ra"),
    (0x3D50, 0x03E00008, "return"),
    (0x3D54, 0x27BD0018, "restore stack in delay slot"),
    (0x3D58, 0x00000000, "clear split second-clear code"),
    (0x3D5C, 0x00000000, "clear split second-clear code"),
    (0x3D60, 0x00000000, "clear split second-clear code"),
    (0x3D64, 0x00000000, "clear split second-clear code"),
    (0x3D68, 0x00000000, "clear split second-clear code"),

    # video_related_8: restore the stock/GE global0 + index*stride structure,
    # with GE's 0x96000 stride.
    (0x46B4, 0x3C048002, "load framebuffer global0 upper"),
    (0x46B8, 0x0C00012B, "osVirtualToPhysical selected base"),
    (0x46BC, 0x8C84417C, "load framebuffer global0"),
    (0x46C0, 0x3C038006, "load g_ViBackIndex upper"),
    (0x46C4, 0x90780879, "load g_ViBackIndex"),
    (0x46C8, 0x3C0F0009, "stride upper 0x96000"),
    (0x46CC, 0x35EF6000, "stride lower 0x96000"),
    (0x46D0, 0x030F0018, "index * stride"),
    (0x46D4, 0x00000000, "stride calc delay/nop"),
    (0x46D8, 0x00007812, "stride calc mflo"),
    (0x46DC, 0x00000000, "clear old split selector"),
    (0x46E0, 0x3C188002, "load g_ViBackData upper"),
    (0x46E4, 0x8F1832A8, "load g_ViBackData"),
    (0x46E8, 0x00000000, "clear old split selector"),
    (0x46EC, 0x01E2C821, "framebuf = base + index*stride"),
    (0x46F0, 0xAF190028, "store framebuf"),

    # framebuffer globals: GE high contiguous framebuffers.
    (0x6584, 0x3C048080, "fb allocation top upper 0x80800000"),
    (0x6588, 0x00000000, "clear old osMemSize load"),
    (0x658C, 0x3C020009, "fb size upper 0x96000"),
    (0x6590, 0x24426000, "fb size lower 0x96000"),
    (0x6594, 0x00822823, "fb1 = top - size"),
    (0x6598, 0x00A22023, "fb0 = fb1 - size"),
    (0x659C, 0x3C02A000, "uncached segment upper"),
    (0x65A0, 0x00827025, "fb0 uncached"),
    (0x65A4, 0x3C018002, "global pointer base"),
    (0x65A8, 0xAC2E417C, "store fb0 global"),
    (0x65AC, 0x00A27825, "fb1 uncached"),
    (0x65B0, 0x03E00008, "return"),
    (0x65B4, 0xAC2F4180, "store fb1 global in delay slot"),
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def build_one(spec):
    base_path = spec["base"]
    rom = bytearray(base_path.read_bytes())
    patch_report = []

    for offset, new_value, note in PATCHES:
        old_value = word(rom, offset)
        write_word(rom, offset, new_value)
        patch_report.append({
            "offset": f"0x{offset:X}",
            "old": f"0x{old_value:08X}",
            "new": f"0x{new_value:08X}",
            "note": note,
        })

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = Path("artifacts/generated") / f"{spec['name']}.z64"
    out_rom.parent.mkdir(parents=True, exist_ok=True)
    out_rom.write_bytes(rom)

    report = {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "base_rom": str(base_path),
        "base_md5": md5(base_path.read_bytes()),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "framebuffer_layout": {
            "fb0": "0x806D4000-0x80769FFF",
            "fb1": "0x8076A000-0x807FFFFF",
            "reason": "avoid current fb0 overlap with GE/TND TLB page cache near 0x80300000",
        },
        "patches": patch_report,
    }
    out_report = Path("reports") / f"tnd480i_{spec['name']}_report.json"
    out_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "out_rom": str(out_rom),
        "out_md5": report["out_md5"],
        "header_crc": report["header_crc"],
    }, indent=2))
    return report


def main():
    reports = [build_one(spec) for spec in OUT_SPECS]
    summary = Path("reports/tnd480i_safe_framebuffer_candidates_20260516.json")
    summary.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
