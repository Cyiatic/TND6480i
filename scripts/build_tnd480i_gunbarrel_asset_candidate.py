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


def make_rle_runs(raw):
    runs = []
    i = 0
    while i < len(raw):
        value = raw[i]
        run = 1
        i += 1
        while i < len(raw) and raw[i] == value and run < 255:
            run += 1
            i += 1
        runs.append((run, value))
    return runs


def encode_rle_runs(width, height, header_tail, runs):
    encoded = bytearray()
    encoded += width.to_bytes(2, "big")
    encoded += height.to_bytes(2, "big")
    encoded += header_tail
    for run, value in runs:
        encoded.extend([run, value])
    return bytes(encoded)


def encode_rle_image(image, header_tail):
    raw = image.tobytes()
    return encode_rle_runs(image.width, image.height, header_tail, make_rle_runs(raw))


def encode_split_value_runs(image, header_tail, target_len, value):
    if target_len is None:
        return None, None

    raw = image.tobytes()
    runs = make_rle_runs(raw)
    baseline = encode_rle_runs(image.width, image.height, header_tail, runs)
    if len(baseline) >= target_len:
        return baseline, {
            "target_encoded_len": f"0x{target_len:X}",
            "baseline_encoded_len": f"0x{len(baseline):X}",
            "final_encoded_len": f"0x{len(baseline):X}",
            "split_value": value,
            "runs_added": 0,
            "decoded_pixels_modified": 0,
        }

    needed_bytes = target_len - len(baseline)
    needed_runs = needed_bytes // 2
    if needed_bytes % 2:
        needed_runs += 1

    split_runs = []
    runs_added = 0
    for count, run_value in runs:
        if run_value == value and count > 1 and runs_added < needed_runs:
            singles = min(count - 1, needed_runs - runs_added)
            split_runs.extend((1, run_value) for _ in range(singles))
            split_runs.append((count - singles, run_value))
            runs_added += singles
        else:
            split_runs.append((count, run_value))

    encoded = encode_rle_runs(image.width, image.height, header_tail, split_runs)
    return encoded, {
        "target_encoded_len": f"0x{target_len:X}",
        "baseline_encoded_len": f"0x{len(baseline):X}",
        "final_encoded_len": f"0x{len(encoded):X}",
        "split_value": value,
        "runs_added": runs_added,
        "decoded_pixels_modified": 0,
    }


def cropped_source_image(source_image, args):
    crop_left = args.source_crop_left
    crop_top = args.source_crop_top
    crop_right = args.source_crop_right
    crop_bottom = args.source_crop_bottom
    if crop_left is crop_top is crop_right is crop_bottom is None:
        return source_image, None

    left = 0 if crop_left is None else crop_left
    top = 0 if crop_top is None else crop_top
    right = source_image.width if crop_right is None else crop_right
    bottom = source_image.height if crop_bottom is None else crop_bottom
    if not (0 <= left < right <= source_image.width and 0 <= top < bottom <= source_image.height):
        raise ValueError(f"invalid source crop {(left, top, right, bottom)} for {source_image.size}")
    return source_image.crop((left, top, right, bottom)), {
        "source_crop_left": left,
        "source_crop_top": top,
        "source_crop_right": right,
        "source_crop_bottom": bottom,
    }


def resampling_for_mode(asset_mode):
    if asset_mode.endswith("-nearest"):
        return Image.Resampling.NEAREST
    if asset_mode.endswith("-bilinear"):
        return Image.Resampling.BILINEAR
    if asset_mode.endswith("-lanczos"):
        return Image.Resampling.LANCZOS
    raise ValueError(f"asset mode {asset_mode} has no resampling method")


def build_asset_image(source_image, args):
    source_image, crop_report = cropped_source_image(source_image, args)

    if args.asset_mode == "resize-nearest":
        image = source_image.resize((args.asset_width, args.asset_height), Image.Resampling.NEAREST)
        return image, {"asset_mode": args.asset_mode, **(crop_report or {})}
    if args.asset_mode == "resize-bilinear":
        image = source_image.resize((args.asset_width, args.asset_height), Image.Resampling.BILINEAR)
        return image, {"asset_mode": args.asset_mode, **(crop_report or {})}
    if args.asset_mode == "resize-lanczos":
        image = source_image.resize((args.asset_width, args.asset_height), Image.Resampling.LANCZOS)
        return image, {"asset_mode": args.asset_mode, **(crop_report or {})}

    if args.asset_mode in ("scale-paste-nearest", "scale-paste-bilinear", "scale-paste-lanczos"):
        scale_width = args.scale_width or args.asset_width
        scale_height = args.scale_height or args.asset_height
        if scale_width <= 0 or scale_height <= 0:
            raise ValueError("scaled asset dimensions must be positive")
        scaled = source_image.resize((scale_width, scale_height), resampling_for_mode(args.asset_mode))
        image = Image.new("L", (args.asset_width, args.asset_height), 0)
        image.paste(scaled, (args.paste_x, args.paste_y))
        image, mask_report = apply_asset_masks(image, args)
        return image, {
            "asset_mode": args.asset_mode,
            "paste_x": args.paste_x,
            "paste_y": args.paste_y,
            "source_width": scale_width,
            "source_height": scale_height,
            "scaled_from_width": source_image.width,
            "scaled_from_height": source_image.height,
            **mask_report,
            **(crop_report or {}),
        }

    image = Image.new("L", (args.asset_width, args.asset_height), 0)
    if args.asset_mode == "pad-origin":
        paste_x = 0
        paste_y = 0
    elif args.asset_mode == "pad-center":
        paste_x = (args.asset_width - source_image.width) // 2
        paste_y = (args.asset_height - source_image.height) // 2
    elif args.asset_mode == "pad-custom":
        paste_x = args.paste_x
        paste_y = args.paste_y
    else:
        raise ValueError(f"unknown asset mode {args.asset_mode}")

    image.paste(source_image, (paste_x, paste_y))
    image, mask_report = apply_asset_masks(image, args)
    return image, {
        "asset_mode": args.asset_mode,
        "paste_x": paste_x,
        "paste_y": paste_y,
        "source_width": source_image.width,
        "source_height": source_image.height,
        **mask_report,
        **(crop_report or {}),
    }


def parse_mask_tuple(value, expected, name):
    parts = [part.strip() for part in value.split(",")]
    if len(parts) not in expected:
        expected_text = " or ".join(str(item) for item in expected)
        raise argparse.ArgumentTypeError(f"{name} expects {expected_text} comma-separated values")
    try:
        return tuple(int(part, 0) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{name} values must be integers") from exc


def parse_mask_box(value):
    return parse_mask_tuple(value, {4, 5}, "--mask-box")


def parse_mask_ellipse(value):
    return parse_mask_tuple(value, {4, 5}, "--mask-ellipse")


def apply_asset_masks(image, args):
    masks = []
    if args.mask_box:
        pixels = image.load()
        for mask in args.mask_box:
            left, top, right, bottom = mask[:4]
            value = mask[4] if len(mask) == 5 else args.mask_value
            if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
                raise ValueError(f"invalid mask box {(left, top, right, bottom)} for {image.size}")
            for y in range(top, bottom):
                for x in range(left, right):
                    pixels[x, y] = value
            masks.append({
                "type": "box",
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "value": value,
            })

    if args.mask_ellipse:
        pixels = image.load()
        for mask in args.mask_ellipse:
            cx, cy, rx, ry = mask[:4]
            value = mask[4] if len(mask) == 5 else args.mask_value
            if rx <= 0 or ry <= 0:
                raise ValueError(f"invalid mask ellipse radius {(rx, ry)}")
            left = max(0, cx - rx)
            top = max(0, cy - ry)
            right = min(image.width, cx + rx + 1)
            bottom = min(image.height, cy + ry + 1)
            rx2 = rx * rx
            ry2 = ry * ry
            limit = rx2 * ry2
            for y in range(top, bottom):
                dy2 = (y - cy) * (y - cy)
                for x in range(left, right):
                    dx2 = (x - cx) * (x - cx)
                    if dx2 * ry2 + dy2 * rx2 <= limit:
                        pixels[x, y] = value
            masks.append({
                "type": "ellipse",
                "cx": cx,
                "cy": cy,
                "rx": rx,
                "ry": ry,
                "value": value,
            })

    if not masks:
        return image, {}
    return image, {"masks": masks}


def outside_box(x, y, box):
    left, top, right, bottom = box
    return x < left or x >= right or y < top or y >= bottom


def workload_positions(image, protected_box, region):
    left, top, right, bottom = protected_box
    if region == "below-source":
        return [
            (x, y)
            for y in range(image.height - 1, bottom - 1, -1)
            for x in range(image.width)
        ]
    if region == "right-of-source":
        return [
            (x, y)
            for y in range(top, bottom)
            for x in range(image.width - 1, right - 1, -1)
        ]
    if region == "outside-source":
        return [
            (x, y)
            for y in range(image.height - 1, -1, -1)
            for x in range(image.width)
            if outside_box(x, y, protected_box)
        ]
    raise ValueError(f"unknown workload padding region {region}")


def add_workload_padding(image, header_tail, target_len, protected_box, value, region):
    if target_len is None:
        return image, None, None

    baseline_encoded = encode_rle_image(image, header_tail)
    if len(baseline_encoded) >= target_len:
        return image, baseline_encoded, {
            "target_encoded_len": f"0x{target_len:X}",
            "baseline_encoded_len": f"0x{len(baseline_encoded):X}",
            "pixels_modified": 0,
            "pad_value": value,
        }

    positions = workload_positions(image, protected_box, region)

    def make_candidate(count):
        candidate = image.copy()
        px = candidate.load()
        for idx, (x, y) in enumerate(positions[:count]):
            px[x, y] = value if (idx & 1) == 0 else 0
        return candidate, encode_rle_image(candidate, header_tail)

    lo = 1
    hi = len(positions)
    best_image = None
    best_encoded = None
    best_count = None
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate, encoded = make_candidate(mid)
        if len(encoded) >= target_len:
            best_image = candidate
            best_encoded = encoded
            best_count = mid
            hi = mid - 1
        else:
            lo = mid + 1

    if best_image is None:
        best_image, best_encoded = make_candidate(len(positions))
        best_count = len(positions)

    return best_image, best_encoded, {
        "target_encoded_len": f"0x{target_len:X}",
        "baseline_encoded_len": f"0x{len(baseline_encoded):X}",
        "final_encoded_len": f"0x{len(best_encoded):X}",
        "pixels_modified": best_count,
        "pad_value": value,
        "region": region,
        "protected_box": [f"0x{item:X}" for item in protected_box],
    }


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

    source_rom = read(args.source_rom) if args.source_rom else bytes(base)
    decoded = decode_rle_image(source_rom, args.source_offset)
    source_image = Image.frombytes("L", (decoded["width"], decoded["height"]), decoded["raw"])
    asset_image, asset_transform = build_asset_image(source_image, args)
    protected_box = (
        asset_transform.get("paste_x", 0),
        asset_transform.get("paste_y", 0),
        asset_transform.get("paste_x", 0) + asset_transform.get("source_width", source_image.width),
        asset_transform.get("paste_y", 0) + asset_transform.get("source_height", source_image.height),
    )
    asset_image, preencoded, workload_report = add_workload_padding(
        asset_image,
        decoded["header_tail"],
        args.workload_target_encoded_len,
        protected_box,
        args.workload_pad_value,
        args.workload_pad_region,
    )
    split_encoded, rle_split_report = encode_split_value_runs(
        asset_image,
        decoded["header_tail"],
        args.rle_split_target_encoded_len,
        args.rle_split_value,
    )
    if split_encoded is not None:
        encoded = split_encoded
    elif preencoded is not None:
        encoded = preencoded
    else:
        encoded = encode_rle_image(asset_image, decoded["header_tail"])

    if args.asset_png:
        args.asset_png.parent.mkdir(parents=True, exist_ok=True)
        asset_image.save(args.asset_png)

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
        "source_rom": str(args.source_rom) if args.source_rom else str(args.base_rom),
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
            **asset_transform,
        },
        "workload_padding": workload_report,
        "rle_split_padding": rle_split_report,
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
    parser.add_argument("--source-rom", type=Path)
    parser.add_argument("--source-offset", type=lambda x: int(x, 0), default=TND_GUNBARREL_RLE_OFFSET)
    parser.add_argument("--asset-width", type=int, default=640)
    parser.add_argument("--asset-height", type=int, default=430)
    parser.add_argument(
        "--asset-mode",
        choices=(
            "resize-nearest",
            "resize-bilinear",
            "resize-lanczos",
            "scale-paste-nearest",
            "scale-paste-bilinear",
            "scale-paste-lanczos",
            "pad-origin",
            "pad-center",
            "pad-custom",
        ),
        default="resize-nearest",
    )
    parser.add_argument("--scale-width", type=int)
    parser.add_argument("--scale-height", type=int)
    parser.add_argument("--paste-x", type=int, default=0)
    parser.add_argument("--paste-y", type=int, default=0)
    parser.add_argument("--source-crop-left", type=int)
    parser.add_argument("--source-crop-top", type=int)
    parser.add_argument("--source-crop-right", type=int)
    parser.add_argument("--source-crop-bottom", type=int)
    parser.add_argument("--mask-box", type=parse_mask_box, action="append")
    parser.add_argument("--mask-ellipse", type=parse_mask_ellipse, action="append")
    parser.add_argument("--mask-value", type=int, default=0)
    parser.add_argument("--workload-target-encoded-len", type=lambda x: int(x, 0))
    parser.add_argument("--workload-pad-value", type=int, default=1)
    parser.add_argument(
        "--workload-pad-region",
        choices=("below-source", "right-of-source", "outside-source"),
        default="below-source",
    )
    parser.add_argument("--rle-split-target-encoded-len", type=lambda x: int(x, 0))
    parser.add_argument("--rle-split-value", type=int, default=0)
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
