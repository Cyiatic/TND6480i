#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from PIL import Image

from build_tnd480i_candidate import (
    DIRECT_PATCH_GROUPS,
    DIRECT_PATCH_PROFILES,
    apply_direct_words,
    byte_diff_count,
    md5,
    read,
    update_n64_crc_6102,
    write,
)


TND_GUNBARREL_RLE_OFFSET = 0x29E120
TITLE_ALLOC_WORD_OFFSETS = (0x3A38C, 0x3A390)
INTRO_RESERVE_WORD_OFFSETS = (0x3D934, 0x3D938, 0x3D950, 0x3D958)
TITLE_RLE_SOURCE_WORD_OFFSETS = (0x3D928, 0x3D94C, 0x3D948, 0x3D954)


def word(data, off):
    return int.from_bytes(data[off:off + 4], "big")


def put_word(data, off, value):
    data[off:off + 4] = value.to_bytes(4, "big")


def align(value, amount):
    return (value + amount - 1) & ~(amount - 1)


def lui_ori_words(register, value):
    return (
        0x3C000000 | (register << 16) | ((value >> 16) & 0xFFFF),
        0x34000000 | (register << 21) | (register << 16) | (value & 0xFFFF),
    )


def lui_addiu_words(register, value):
    high = ((value + 0x8000) >> 16) & 0xFFFF
    low = value & 0xFFFF
    return (
        0x3C000000 | (register << 16) | high,
        0x24000000 | (register << 21) | (register << 16) | low,
    )


def decode_rle_image(rom, offset):
    width = int.from_bytes(rom[offset:offset + 2], "big")
    height = int.from_bytes(rom[offset + 2:offset + 4], "big")
    header_tail = bytes(rom[offset + 4:offset + 10])
    pos = offset + 10
    raw = bytearray()
    runs = 0
    while len(raw) < width * height:
        count = rom[pos]
        value = rom[pos + 1]
        pos += 2
        runs += 1
        raw.extend([value] * count)
    return {
        "width": width,
        "height": height,
        "header_tail": header_tail,
        "raw": bytes(raw[:width * height]),
        "rle_end": pos,
        "runs": runs,
    }


def encode_rle_image(image, header_tail):
    raw = image.tobytes()
    encoded = bytearray()
    encoded += image.width.to_bytes(2, "big")
    encoded += image.height.to_bytes(2, "big")
    encoded += header_tail

    i = 0
    while i < len(raw):
        value = raw[i]
        run = 1
        i += 1
        while i < len(raw) and raw[i] == value and run < 255:
            run += 1
            i += 1
        encoded.extend([run, value])

    return bytes(encoded)


def add_experimental_word(report, rom, off, value, note):
    old = word(rom, off)
    put_word(rom, off, value)
    report.append({
        "offset": f"0x{off:X}",
        "old": f"0x{old:08X}",
        "new": f"0x{value:08X}",
        "note": note,
    })


def apply_title_alloc_and_intro_reserve(rom, title_alloc_size, intro_reserve):
    report = []
    if title_alloc_size is not None:
        upper, lower = lui_ori_words(4, title_alloc_size)
        add_experimental_word(report, rom, TITLE_ALLOC_WORD_OFFSETS[0], upper, f"title allocation upper for 0x{title_alloc_size:X}")
        add_experimental_word(report, rom, TITLE_ALLOC_WORD_OFFSETS[1], lower, f"title allocation lower for 0x{title_alloc_size:X}")

    if intro_reserve is not None:
        down = (-intro_reserve) & 0xFFFFFFFF
        down_upper, down_lower = lui_ori_words(1, down)
        up_upper, up_lower = lui_ori_words(1, intro_reserve)
        add_experimental_word(report, rom, INTRO_RESERVE_WORD_OFFSETS[0], down_upper, f"intro reserve subtract upper for 0x{intro_reserve:X}")
        add_experimental_word(report, rom, INTRO_RESERVE_WORD_OFFSETS[1], down_lower, f"intro reserve subtract lower for 0x{intro_reserve:X}")
        add_experimental_word(report, rom, INTRO_RESERVE_WORD_OFFSETS[2], up_upper, f"intro reserve add upper for 0x{intro_reserve:X}")
        add_experimental_word(report, rom, INTRO_RESERVE_WORD_OFFSETS[3], up_lower, f"intro reserve add lower for 0x{intro_reserve:X}")

    return report


def apply_title_rle_pointer(rom, start, end):
    report = []
    source_upper, source_lower = lui_addiu_words(3, start)
    end_upper, end_lower = lui_addiu_words(11, end)
    for off, value, note in [
        (TITLE_RLE_SOURCE_WORD_OFFSETS[0], source_upper, f"title RLE source upper for 0x{start:X}"),
        (TITLE_RLE_SOURCE_WORD_OFFSETS[1], source_lower, f"title RLE source lower for 0x{start:X}"),
        (TITLE_RLE_SOURCE_WORD_OFFSETS[2], end_upper, f"title RLE source end upper for 0x{end:X}"),
        (TITLE_RLE_SOURCE_WORD_OFFSETS[3], end_lower, f"title RLE source end lower for 0x{end:X}"),
    ]:
        add_experimental_word(report, rom, off, value, note)
    return report


def build(args):
    base = bytearray(read(args.base_rom))
    original_len = len(base)

    decoded = decode_rle_image(base, args.source_offset)
    source_image = Image.frombytes("L", (decoded["width"], decoded["height"]), decoded["raw"])
    resized = source_image.resize((args.asset_width, args.asset_height), Image.Resampling.NEAREST)
    encoded = encode_rle_image(resized, decoded["header_tail"])

    if args.asset_png:
        args.asset_png.parent.mkdir(parents=True, exist_ok=True)
        resized.save(args.asset_png)

    direct_report = apply_direct_words(base, args.direct_profile)
    experimental_report = apply_title_alloc_and_intro_reserve(base, args.title_alloc_size, args.intro_reserve)

    append_start = align(len(base), args.append_align)
    append_end = align(append_start + len(encoded), 0x40)
    if len(base) < append_start:
        base.extend(b"\x00" * (append_start - len(base)))
    base.extend(encoded)
    if len(base) < append_end:
        base.extend(b"\x00" * (append_end - len(base)))

    pointer_report = apply_title_rle_pointer(base, append_start, append_end)
    crc1, crc2 = update_n64_crc_6102(base)
    write(args.out_rom, base)

    report = {
        "base_rom": str(args.base_rom),
        "out_rom": str(args.out_rom),
        "direct_profile": args.direct_profile,
        "out_md5": md5(base),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "original_rom_len": f"0x{original_len:X}",
        "new_rom_len": f"0x{len(base):X}",
        "fullrom_changed_bytes_from_tnd_prefix": byte_diff_count(read(args.base_rom), bytes(base[:original_len])),
        "source_rle": {
            "offset": f"0x{args.source_offset:X}",
            "width": decoded["width"],
            "height": decoded["height"],
            "rle_end": f"0x{decoded['rle_end']:X}",
            "runs": decoded["runs"],
        },
        "appended_rle": {
            "start": f"0x{append_start:X}",
            "end": f"0x{append_end:X}",
            "encoded_len": f"0x{len(encoded):X}",
            "padded_len": f"0x{append_end - append_start:X}",
            "width": args.asset_width,
            "height": args.asset_height,
        },
        "direct_word_patches": direct_report,
        "experimental_direct_words": experimental_report,
        "title_rle_pointer_words": pointer_report,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/roms/TND64_enh480i_core_no_menu_pigz.z64"))
    parser.add_argument("--out-rom", type=Path, default=Path("artifacts/generated/TND64_480i_gunbarrel_asset640_core_no_menu.z64"))
    parser.add_argument("--report", type=Path, default=Path("reports/tnd480i_gunbarrel_asset640_core_no_menu_report.json"))
    parser.add_argument("--asset-png", type=Path, default=Path("diagnostics/captures/tnd_gunbarrel_asset640x430_source_20260510.png"))
    parser.add_argument("--source-offset", type=lambda x: int(x, 0), default=TND_GUNBARREL_RLE_OFFSET)
    parser.add_argument("--asset-width", type=int, default=640)
    parser.add_argument("--asset-height", type=int, default=430)
    parser.add_argument("--append-align", type=lambda x: int(x, 0), default=0x1000)
    parser.add_argument("--title-alloc-size", type=lambda x: int(x, 0), default=0x96040)
    parser.add_argument("--intro-reserve", type=lambda x: int(x, 0), default=0x58000)
    parser.add_argument(
        "--direct-profile",
        choices=sorted(DIRECT_PATCH_PROFILES),
        default="split8030_8076_all_dim0_title640asset_gameplayxy_tnddefaultwidthheight480i_virtualfb",
    )
    args = parser.parse_args()
    if "K_title_draw_ge480_target_asset640_height430" not in DIRECT_PATCH_GROUPS:
        raise SystemExit("asset title-draw patch group is not available")
    build(args)


if __name__ == "__main__":
    main()
