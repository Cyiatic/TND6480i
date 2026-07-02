#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


ASSET_START = 0x1000000
ASSET_END = 0x1025A00
POINTER_PATCHES = [
    (0x3D928, 0x3C030100, 0x3C030100, "title RLE source upper"),
    (0x3D94C, 0x24630000, 0x24630000, "title RLE source lower"),
    (0x3D948, 0x3C0B0102, 0x3C0B0102, "title RLE source end upper"),
    (0x3D954, 0x256BA680, 0x256B5A00, "title RLE source end lower for scaled 640x430 asset"),
]
DRAW_PATCHES = [
    (0x4FDEC, 0x3C17070D, 0x3C170713, "title/gunbarrel texture setup upper"),
    (0x4FDFC, 0x3C0AE46D, 0x3C0AE49F, "title/gunbarrel texture rectangle target width"),
    (0x4FE34, 0x3C018005, 0x3C0143D7, "title/gunbarrel draw height float upper 430.0"),
    (0x4FE3C, 0x36F7B026, 0x36F7F006, "title/gunbarrel texture setup lower"),
    (0x4FE44, 0xC4301CF0, 0x44818000, "title/gunbarrel draw uses immediate height float"),
    (0x4FF00, 0x3C0E006D, 0x3C0E009F, "title/gunbarrel texture rectangle lower width"),
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def copy_save_pair(base_rom, out_rom):
    outputs = []
    for suffix in (".sav", ".eep"):
        source = base_rom.with_suffix(suffix)
        target = out_rom.with_suffix(suffix)
        if not source.exists():
            outputs.append({"source": str(source), "target": str(target), "missing": True})
            continue
        shutil.copy2(source, target)
        payload = target.read_bytes()
        outputs.append({"source": str(source), "target": str(target), "bytes": len(payload), "md5": md5(payload)})
    return outputs


def apply_words(rom, patches):
    applied = []
    for offset, expected_old, new, note in patches:
        old = word(rom, offset)
        if old not in (expected_old, new):
            raise SystemExit(
                f"unexpected word at 0x{offset:X}: 0x{old:08X}, expected 0x{expected_old:08X}"
            )
        write_word(rom, offset, new)
        applied.append({
            "offset": f"0x{offset:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{new:08X}",
            "changed": old != new,
            "note": note,
        })
    return applied


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/g1castz1.z64"))
    parser.add_argument(
        "--asset-source-rom",
        type=Path,
        default=Path(
            "artifacts/generated/"
            "TND64_480i_frontbuf_gunbarrel_asset640_skipfileselect_gameplayxy_"
            "tnddefaultwidthheight480i_virtualfb_reserve58000_core_no_menu.z64"
        ),
    )
    parser.add_argument("--out-rom", type=Path, default=Path("artifacts/generated/g1casta1.z64"))
    parser.add_argument("--report", type=Path, default=Path("reports/tnd480i_g1casta1_gunbarrel_asset_transplant_20260518.json"))
    args = parser.parse_args()

    base = bytearray(args.base_rom.read_bytes())
    asset_source = args.asset_source_rom.read_bytes()
    if len(asset_source) < ASSET_END:
        raise SystemExit(f"asset source too small: 0x{len(asset_source):X}, need 0x{ASSET_END:X}")
    if len(base) < ASSET_START:
        raise SystemExit(f"base ROM too small: 0x{len(base):X}")

    transplanted = asset_source[ASSET_START:ASSET_END]
    rom = base[:ASSET_START] + bytearray(transplanted)
    applied = apply_words(rom, POINTER_PATCHES + DRAW_PATCHES)

    crc1, crc2 = update_n64_crc_6102(rom)
    args.out_rom.parent.mkdir(parents=True, exist_ok=True)
    args.out_rom.write_bytes(rom)
    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(args.base_rom.read_bytes()),
        "asset_source_rom": str(args.asset_source_rom),
        "asset_source_md5": md5(asset_source),
        "out_rom": str(args.out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "asset_range": {
            "start": f"0x{ASSET_START:X}",
            "end": f"0x{ASSET_END:X}",
            "bytes": len(transplanted),
        },
        "purpose": (
            "Transplant the known scaled 640x430 gunbarrel RLE asset onto g1castz1, "
            "then pair it with the matching title/gunbarrel draw-target word family. "
            "No gameplay or dossier tables are changed."
        ),
        "patches": applied,
        "save_outputs": copy_save_pair(args.base_rom, args.out_rom),
        "do_not_promote_until_hardware_compared": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
