#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from build_tnd480i_candidate import (
    DIRECT_PATCH_GROUPS,
    DIRECT_PATCH_PROFILES,
    GE_1172_OFFSET,
    MAIN_RANGE_SETS,
    apply_direct_words,
    apply_main_ranges,
    byte_diff_count,
    inflate_ge1172,
    md5,
    pack_ge1172,
    read,
    update_n64_crc_6102,
)


def parse_range(text):
    parts = text.split(":")
    if len(parts) not in {2, 3}:
        raise argparse.ArgumentTypeError("range must be start:end[:label]")
    start = int(parts[0], 0)
    end = int(parts[1], 0)
    if start >= end:
        raise argparse.ArgumentTypeError("range start must be before end")
    if start % 4 or end % 4:
        raise argparse.ArgumentTypeError("range bounds must be word aligned")
    label = parts[2] if len(parts) == 3 else f"0x{start:X}-0x{end:X}"
    return start, end, label


def word(data, off):
    return int.from_bytes(data[off:off + 4], "big")


def put_word(data, off, value):
    data[off:off + 4] = value.to_bytes(4, "big")


def lui_ori_words(register, value):
    return (
        0x3C000000 | (register << 16) | ((value >> 16) & 0xFFFF),
        0x34000000 | (register << 21) | (register << 16) | (value & 0xFFFF),
    )


def profile_offsets(profile):
    offsets = set()
    for group in DIRECT_PATCH_PROFILES[profile]:
        for off, _value, _note in DIRECT_PATCH_GROUPS[group]:
            offsets.add(off)
    return offsets


def apply_safe_ranges(candidate, tnd_base, ge_stock, ge480i, ranges, direct_profile):
    direct_offsets = profile_offsets(direct_profile)
    applied = []
    already_matching = []
    conflicts = []
    unsafe = []

    limit = min(len(candidate), len(tnd_base), len(ge_stock), len(ge480i))
    for start, end, label in ranges:
        bounded_end = min(end, limit - (limit % 4))
        for off in range(start, bounded_end, 4):
            ge_word = word(ge_stock, off)
            ge480_word = word(ge480i, off)
            if ge_word == ge480_word:
                continue

            tnd_word = word(tnd_base, off)
            cur_word = word(candidate, off)

            if tnd_word != ge_word:
                unsafe.append({
                    "range": label,
                    "offset": f"0x{off:X}",
                    "ge_stock": f"0x{ge_word:08X}",
                    "ge_480i": f"0x{ge480_word:08X}",
                    "tnd_base": f"0x{tnd_word:08X}",
                    "candidate": f"0x{cur_word:08X}",
                    "reason": "tnd_base_differs_from_ge_stock",
                })
                continue

            if cur_word == ge480_word:
                already_matching.append({
                    "range": label,
                    "offset": f"0x{off:X}",
                    "ge_480i": f"0x{ge480_word:08X}",
                    "direct_profile_offset": off in direct_offsets,
                })
                continue

            if cur_word != ge_word:
                conflicts.append({
                    "range": label,
                    "offset": f"0x{off:X}",
                    "ge_stock": f"0x{ge_word:08X}",
                    "ge_480i": f"0x{ge480_word:08X}",
                    "candidate": f"0x{cur_word:08X}",
                    "direct_profile_offset": off in direct_offsets,
                    "reason": "candidate_already_changed_to_other_word",
                })
                continue

            put_word(candidate, off, ge480_word)
            applied.append({
                "range": label,
                "offset": f"0x{off:X}",
                "old": f"0x{ge_word:08X}",
                "new": f"0x{ge480_word:08X}",
            })

    return {
        "applied": applied,
        "already_matching": already_matching,
        "conflicts": conflicts,
        "unsafe": unsafe,
    }


def apply_main_safe_ranges(patched_raw, tnd_raw, ge_stock_raw, ge480i_raw, ranges):
    out = bytearray(patched_raw)
    applied = []
    already_matching = []
    conflicts = []
    unsafe = []

    limit = min(len(out), len(tnd_raw), len(ge_stock_raw), len(ge480i_raw))
    for start, end, label in ranges:
        bounded_end = min(end, limit - (limit % 4))
        for off in range(start, bounded_end, 4):
            ge_word = word(ge_stock_raw, off)
            ge480_word = word(ge480i_raw, off)
            if ge_word == ge480_word:
                continue

            tnd_word = word(tnd_raw, off)
            cur_word = word(out, off)

            if tnd_word != ge_word:
                unsafe.append({
                    "range": label,
                    "offset": f"0x{off:X}",
                    "ge_stock": f"0x{ge_word:08X}",
                    "ge_480i": f"0x{ge480_word:08X}",
                    "tnd_base": f"0x{tnd_word:08X}",
                    "candidate": f"0x{cur_word:08X}",
                    "reason": "tnd_main_raw_differs_from_ge_stock",
                })
                continue

            if cur_word == ge480_word:
                already_matching.append({
                    "range": label,
                    "offset": f"0x{off:X}",
                    "ge_480i": f"0x{ge480_word:08X}",
                })
                continue

            if cur_word != ge_word:
                conflicts.append({
                    "range": label,
                    "offset": f"0x{off:X}",
                    "ge_stock": f"0x{ge_word:08X}",
                    "ge_480i": f"0x{ge480_word:08X}",
                    "candidate": f"0x{cur_word:08X}",
                    "reason": "candidate_main_raw_already_changed_to_other_word",
                })
                continue

            put_word(out, off, ge480_word)
            applied.append({
                "range": label,
                "offset": f"0x{off:X}",
                "old": f"0x{ge_word:08X}",
                "new": f"0x{ge480_word:08X}",
            })

    return bytes(out), {
        "applied": applied,
        "already_matching": already_matching,
        "conflicts": conflicts,
        "unsafe": unsafe,
    }


def apply_experimental_words(candidate, args):
    report = []

    if args.title_alloc_size is not None:
        upper, lower = lui_ori_words(4, args.title_alloc_size)
        for off, value, note in [
            (0x3A38C, upper, f"title allocation upper for 0x{args.title_alloc_size:X}"),
            (0x3A390, lower, f"title allocation lower for 0x{args.title_alloc_size:X}"),
        ]:
            old = word(candidate, off)
            put_word(candidate, off, value)
            report.append({
                "offset": f"0x{off:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{value:08X}",
                "note": note,
            })

    if args.intro_reserve is not None:
        down = (-args.intro_reserve) & 0xFFFFFFFF
        down_upper, down_lower = lui_ori_words(1, down)
        up_upper, up_lower = lui_ori_words(1, args.intro_reserve)
        for off, value, note in [
            (0x3D934, down_upper, f"intro reserve subtract upper for 0x{args.intro_reserve:X}"),
            (0x3D938, down_lower, f"intro reserve subtract lower for 0x{args.intro_reserve:X}"),
            (0x3D950, up_upper, f"intro reserve add upper for 0x{args.intro_reserve:X}"),
            (0x3D958, up_lower, f"intro reserve add lower for 0x{args.intro_reserve:X}"),
        ]:
            old = word(candidate, off)
            put_word(candidate, off, value)
            report.append({
                "offset": f"0x{off:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{value:08X}",
                "note": note,
            })

    return report


def zero_pad_capacity(rom, offset, slot_len):
    end = offset + slot_len
    limit = end
    while limit < len(rom) and rom[limit] == 0:
        limit += 1
    return limit - offset, limit - end


def build(args):
    base_path = Path(args.base_rom)
    ge_stock_path = Path(args.ge_stock_rom)
    ge480i_path = Path(args.ge480i_rom)
    out_path = Path(args.out_rom)

    tnd_base = bytearray(read(base_path))
    candidate = bytearray(tnd_base)
    ge_stock = read(ge_stock_path)
    ge480i = read(ge480i_path)

    _base_raw, slot_len = inflate_ge1172(candidate, args.offset)
    ge_raw, _ = inflate_ge1172(ge480i, args.offset)
    ge_stock_raw, _ = inflate_ge1172(ge_stock, args.offset)
    tnd_raw, _ = inflate_ge1172(candidate, args.offset)

    ranges = MAIN_RANGE_SETS[args.variant]
    patched_raw, main_report = apply_main_ranges(tnd_raw, ge_raw, ranges)
    patched_raw, main_safe_report = apply_main_safe_ranges(
        patched_raw,
        tnd_raw,
        ge_stock_raw,
        ge_raw,
        args.main_safe_range,
    )
    packed_len = 0
    allowed_packed_len = slot_len
    zero_pad_growth = 0
    if args.allow_zero_pad_growth:
        allowed_packed_len, zero_pad_growth = zero_pad_capacity(candidate, args.offset, slot_len)

    if ranges or args.main_safe_range:
        packed = pack_ge1172(patched_raw)
        if len(packed) > allowed_packed_len:
            raise ValueError(f"packed stream too large: 0x{len(packed):X} > 0x{allowed_packed_len:X}")
        candidate[args.offset:args.offset + allowed_packed_len] = b"\x00" * allowed_packed_len
        candidate[args.offset:args.offset + len(packed)] = packed
        packed_len = len(packed)

    direct_report = apply_direct_words(candidate, args.direct_profile)
    safe_report = apply_safe_ranges(
        candidate,
        tnd_base,
        ge_stock,
        ge480i,
        args.safe_range,
        args.direct_profile,
    )
    experimental_report = apply_experimental_words(candidate, args)

    crc1, crc2 = update_n64_crc_6102(candidate)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(candidate)

    verify_raw, verify_consumed = inflate_ge1172(candidate, args.offset)
    report = {
        "base_rom": str(base_path),
        "ge_stock_rom": str(ge_stock_path),
        "ge480i_rom": str(ge480i_path),
        "out_rom": str(out_path),
        "variant": args.variant,
        "direct_profile": args.direct_profile,
        "safe_ranges": [
            {"start": f"0x{start:X}", "end": f"0x{end:X}", "label": label}
            for start, end, label in args.safe_range
        ],
        "out_md5": md5(candidate),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "main_raw_md5": md5(patched_raw),
        "verify_main_raw_md5": md5(verify_raw),
        "slot_len": f"0x{slot_len:X}",
        "allowed_packed_len": f"0x{allowed_packed_len:X}",
        "zero_pad_growth": f"0x{zero_pad_growth:X}",
        "packed_len": f"0x{packed_len:X}",
        "verify_consumed": f"0x{verify_consumed:X}",
        "main_changed_bytes_from_tnd": byte_diff_count(tnd_raw, patched_raw),
        "fullrom_changed_bytes_from_tnd": byte_diff_count(tnd_base, candidate),
        "main_ranges": main_report,
        "main_safe_ranges": [
            {"start": f"0x{start:X}", "end": f"0x{end:X}", "label": label}
            for start, end, label in args.main_safe_range
        ],
        "main_safe_words_applied": main_safe_report["applied"],
        "main_safe_words_already_matching": main_safe_report["already_matching"],
        "main_safe_word_conflicts": main_safe_report["conflicts"],
        "main_safe_words_skipped_unsafe": main_safe_report["unsafe"],
        "direct_word_patches": direct_report,
        "safe_direct_words_applied": safe_report["applied"],
        "safe_direct_words_already_matching": safe_report["already_matching"],
        "safe_direct_word_conflicts": safe_report["conflicts"],
        "safe_direct_words_skipped_unsafe": safe_report["unsafe"],
        "experimental_direct_words": experimental_report,
        "counts": {
            "main_ranges": len(main_report),
            "direct_word_patches": len(direct_report),
            "safe_direct_words_applied": len(safe_report["applied"]),
            "safe_direct_words_already_matching": len(safe_report["already_matching"]),
            "safe_direct_word_conflicts": len(safe_report["conflicts"]),
            "safe_direct_words_skipped_unsafe": len(safe_report["unsafe"]),
            "main_safe_words_applied": len(main_safe_report["applied"]),
            "main_safe_words_already_matching": len(main_safe_report["already_matching"]),
            "main_safe_word_conflicts": len(main_safe_report["conflicts"]),
            "main_safe_words_skipped_unsafe": len(main_safe_report["unsafe"]),
            "experimental_direct_words": len(experimental_report),
        },
    }

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", default="artifacts/roms/TND64_enh480i_core_no_menu_pigz.z64")
    parser.add_argument("--ge-stock-rom", default="artifacts/roms/GoldenEye 007 (USA).z64")
    parser.add_argument("--ge480i-rom", default="artifacts/roms/BASELINE_GE_480i_direct_from_stock.z64")
    parser.add_argument(
        "--out-rom",
        default="artifacts/generated/TND64_480i_split8030_8076_all_dim0_gameplay480i_safe_titlefront_core_no_menu.z64",
    )
    parser.add_argument(
        "--report",
        default="reports/tnd480i_split8030_8076_all_dim0_gameplay480i_safe_titlefront_core_no_menu_report.json",
    )
    parser.add_argument("--offset", type=lambda x: int(x, 0), default=GE_1172_OFFSET)
    parser.add_argument("--variant", choices=sorted(MAIN_RANGE_SETS), default="direct_only")
    parser.add_argument(
        "--direct-profile",
        choices=sorted(DIRECT_PATCH_PROFILES),
        default="split8030_8076_all_dim0_gameplay480i",
    )
    parser.add_argument(
        "--safe-range",
        action="append",
        type=parse_range,
        default=None,
        help="Apply GE 480i full-ROM word diffs only where TND base matches GE stock; format start:end[:label].",
    )
    parser.add_argument(
        "--main-safe-range",
        action="append",
        type=parse_range,
        default=[],
        help="Apply GE 480i 1172-main raw word diffs only where TND main raw matches GE stock; format start:end[:label].",
    )
    parser.add_argument("--no-default-safe-ranges", action="store_true")
    parser.add_argument(
        "--title-alloc-size",
        type=lambda x: int(x, 0),
        default=None,
        help="Experimental override for the title allocation immediate at 0x3A38C/0x3A390.",
    )
    parser.add_argument(
        "--intro-reserve",
        type=lambda x: int(x, 0),
        default=None,
        help="Experimental override for the intro buffer reserve immediate at 0x3D934/0x3D950.",
    )
    parser.add_argument(
        "--allow-zero-pad-growth",
        action="store_true",
        help="Allow a repacked 1172 stream to extend into zero padding immediately following the original stream.",
    )
    args = parser.parse_args()
    if args.safe_range is None and args.no_default_safe_ranges:
        args.safe_range = []
    elif args.safe_range is None:
        args.safe_range = [
            parse_range("0x3A000:0x50200:title_front_code"),
            parse_range("0x106ED4:0x106F28:expanded_menu_resolution"),
        ]
    build(args)


if __name__ == "__main__":
    main()
