#!/usr/bin/env python3
import argparse
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BACKDROP_FN_START = 0x3C6C4
TITLE_X_PLUS_OFF = 0x3C6CC
TITLE_Y_MINUS_OFF = 0x3C6DC
SCALE_X_LUI_OFF = 0x3C734
SCALE_Y_LUI_OFF = 0x3C738
SCALE_Y_ORI_OFF = 0x3C740
SCALE_X_ORI_OFF = 0x3C744


def word(data, off):
    return int.from_bytes(data[off:off + 4], "big")


def put_word(data, off, value):
    data[off:off + 4] = value.to_bytes(4, "big")


def float_bits(value):
    return struct.unpack(">I", struct.pack(">f", float(value)))[0]


def lui(reg, value):
    return 0x3C000000 | (reg << 16) | ((value >> 16) & 0xFFFF)


def ori(reg, value):
    return 0x34000000 | (reg << 21) | (reg << 16) | (value & 0xFFFF)


def patch_float_load(report, rom, off_lui, off_ori, reg, value, note):
    bits = float_bits(value)
    patches = [
        (off_lui, lui(reg, bits), f"{note} upper for {value:g}"),
        (off_ori, ori(reg, bits), f"{note} lower for {value:g}"),
    ]
    for off, new_value, patch_note in patches:
        old = word(rom, off)
        put_word(rom, off, new_value)
        report.append({
            "offset": f"0x{off:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{new_value:08X}",
            "note": patch_note,
        })


def patch_lui_float(report, rom, off, reg, value, note):
    bits = float_bits(value)
    if bits & 0xFFFF:
        raise ValueError(f"{note} value {value:g} needs non-zero lower half 0x{bits & 0xFFFF:04X}")
    new_value = lui(reg, bits)
    old = word(rom, off)
    put_word(rom, off, new_value)
    report.append({
        "offset": f"0x{off:X}",
        "old": f"0x{old:08X}",
        "new": f"0x{new_value:08X}",
        "note": f"{note} for {value:g}",
    })


def apply_variant(rom, variant):
    report = []
    if variant.get("return_immediately"):
        for off, new_value, note in [
            (BACKDROP_FN_START, 0x03E00008, "diagnostic skip insert_sight_backdrop_eye_intro: jr ra"),
            (BACKDROP_FN_START + 4, 0x00801025, "diagnostic skip insert_sight_backdrop_eye_intro: move v0,a0"),
        ]:
            old = word(rom, off)
            put_word(rom, off, new_value)
            report.append({
                "offset": f"0x{off:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{new_value:08X}",
                "note": note,
            })
        return report

    if "tx" in variant:
        patch_lui_float(report, rom, TITLE_X_PLUS_OFF, 1, variant["tx"], "backdrop translate X addend")
    if "ty" in variant:
        patch_lui_float(report, rom, TITLE_Y_MINUS_OFF, 1, variant["ty"], "backdrop translate Y subtract addend")
    if "sx" in variant:
        patch_float_load(report, rom, SCALE_X_LUI_OFF, SCALE_X_ORI_OFF, 5, variant["sx"], "backdrop scale X")
    if "sy" in variant:
        patch_float_load(report, rom, SCALE_Y_LUI_OFF, SCALE_Y_ORI_OFF, 6, variant["sy"], "backdrop scale Y")
    return report


VARIANTS = {
    "backdrop_skip": {"return_immediately": True},
    "backdrop_scale_240": {"sx": 2.4, "sy": 2.4},
    "backdrop_scale_300": {"sx": 3.0, "sy": 3.0},
    "backdrop_tx640": {"tx": 640.0},
    "backdrop_tx896": {"tx": 896.0},
    "backdrop_tx640_scale240": {"tx": 640.0, "sx": 2.4, "sy": 2.4},
    "backdrop_tx896_scale300": {"tx": 896.0, "sx": 3.0, "sy": 3.0},
    "backdrop_ty0_scale240": {"ty": 0.0, "sx": 2.4, "sy": 2.4},
    "backdrop_ty80_scale300": {"ty": 80.0, "sx": 3.0, "sy": 3.0},
}


def build(args):
    base_path = Path(args.base_rom)
    base = bytearray(base_path.read_bytes())
    out_dir = Path(args.out_dir)
    report_dir = Path(args.report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    selected = args.variant or sorted(VARIANTS)
    for name in selected:
        variant = VARIANTS[name]
        rom = bytearray(base)
        patches = apply_variant(rom, variant)
        crc1, crc2 = update_n64_crc_6102(rom)
        out_path = out_dir / f"{args.prefix}_{name}_20260510.z64"
        report_path = report_dir / f"{args.prefix}_{name}_20260510_report.json"
        out_path.write_bytes(rom)
        report = {
            "base_rom": str(base_path),
            "out_rom": str(out_path),
            "variant": name,
            "variant_config": variant,
            "patches": patches,
            "out_md5": md5(rom),
            "header_crc": f"{crc1:08X} {crc2:08X}",
            "changed_bytes_from_base": sum(a != b for a, b in zip(base, rom)),
        }
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        manifest.append({
            "variant": name,
            "out_rom": str(out_path),
            "report": str(report_path),
            "out_md5": report["out_md5"],
            "header_crc": report["header_crc"],
            "patch_count": len(patches),
        })

    print(json.dumps(manifest, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-rom",
        default="artifacts/generated/TND64_480i_gamefulltop0_ge480i_titleasset_exact_20260510.z64",
    )
    parser.add_argument("--out-dir", default="artifacts/generated")
    parser.add_argument("--report-dir", default="reports")
    parser.add_argument("--prefix", default="TND64_480i_gamefulltop0_ge480i_titleasset")
    parser.add_argument("--variant", action="append", choices=sorted(VARIANTS))
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
