#!/usr/bin/env python3
import argparse
import json
import shutil
from pathlib import Path

from build_tnd480i_candidate import (
    GE_1172_OFFSET,
    apply_main_ranges,
    inflate_ge1172,
    md5,
    pack_ge1172,
    update_n64_crc_6102,
)


CANDIDATES = [
    {
        "name": "txmtabx",
        "ranges": [(0xA240, 0xA254, "GE480i mission cursor/table X coordinates")],
        "purpose": "Only the GE480i mission-select X cursor/table data from raw 1172.",
    },
    {
        "name": "txmtaby",
        "ranges": [(0xA254, 0xA264, "GE480i mission cursor/table Y coordinates")],
        "purpose": "Only the GE480i mission-select Y cursor/table data from raw 1172.",
    },
    {
        "name": "txmtabxy",
        "ranges": [(0xA240, 0xA264, "GE480i mission cursor/table X and Y coordinates")],
        "purpose": "Full GE480i mission-select cursor/table data from raw 1172.",
    },
    {
        "name": "txmrawa",
        "ranges": [(0x9C3C, 0x9D24, "GE480i menu/display table A")],
        "purpose": "The larger GE480i menu/display table A only; checks page-scale/table effect.",
    },
    {
        "name": "txmrawab",
        "ranges": [
            (0x9C3C, 0x9D24, "GE480i menu/display table A"),
            (0xA240, 0xA264, "GE480i menu/display table B"),
        ],
        "purpose": "GE480i menu/display table A plus mission cursor/table B.",
    },
]


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
        outputs.append(
            {
                "source": str(source),
                "target": str(target),
                "bytes": len(payload),
                "md5": md5(payload),
            }
        )
    return outputs


def zero_pad_capacity(rom, offset, slot_len):
    end = offset + slot_len
    limit = end
    while limit < len(rom) and rom[limit] == 0:
        limit += 1
    return limit - offset, limit - end


def insert_raw_1172(base_rom_bytes, patched_raw, slot_len, allowed_len, zopfli_iterations):
    packed = pack_ge1172(patched_raw, zopfli_iterations=zopfli_iterations)
    if len(packed) > allowed_len:
        raise ValueError(f"packed 1172 is {len(packed)} bytes, allowed slot is {allowed_len} bytes")
    out = bytearray(base_rom_bytes)
    start = GE_1172_OFFSET
    end = start + allowed_len
    out[start:end] = b"\0" * allowed_len
    out[start:start + len(packed)] = packed
    return out, packed


def build_one(
    spec,
    base_rom,
    base_rom_bytes,
    base_raw,
    ge_raw,
    slot_len,
    allowed_len,
    out_dir,
    prefix,
    zopfli_iterations,
):
    patched_raw, range_report = apply_main_ranges(base_raw, ge_raw, spec["ranges"])
    rom, packed = insert_raw_1172(base_rom_bytes, patched_raw, slot_len, allowed_len, zopfli_iterations)
    verify_raw, _ = inflate_ge1172(rom, GE_1172_OFFSET)
    if verify_raw != patched_raw:
        raise ValueError(f"{spec['name']} 1172 verify mismatch after repack")

    crc1, crc2 = update_n64_crc_6102(rom)
    out_name = f"{prefix}{spec['name']}" if prefix else spec["name"]
    out_rom = out_dir / f"{out_name}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": out_name,
        "purpose": spec["purpose"],
        "base_rom": str(base_rom),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "raw_md5": md5(patched_raw),
        "packed_1172_len": len(packed),
        "slot_1172_len": slot_len,
        "allowed_1172_len": allowed_len,
        "ranges": range_report,
        "save_outputs": copy_save_pair(base_rom, out_rom),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/t90texstk.z64"))
    parser.add_argument("--ge480-rom", type=Path, default=Path("artifacts/roms/BASELINE_GE_480i_direct_from_stock.z64"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/generated"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/tnd480i_t90tex_raw_menu_table_candidates_20260518.json"),
    )
    parser.add_argument("--prefix", default="")
    parser.add_argument("--zopfli-iterations", type=int, default=25)
    args = parser.parse_args()

    if not args.base_rom.exists():
        raise SystemExit(f"missing base ROM: {args.base_rom}")
    if not args.ge480_rom.exists():
        raise SystemExit(f"missing GE480i ROM: {args.ge480_rom}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    base_rom_bytes = args.base_rom.read_bytes()
    ge_rom_bytes = args.ge480_rom.read_bytes()
    base_raw, slot_len = inflate_ge1172(base_rom_bytes, GE_1172_OFFSET)
    ge_raw, _ = inflate_ge1172(ge_rom_bytes, GE_1172_OFFSET)
    allowed_len, zero_pad_growth = zero_pad_capacity(base_rom_bytes, GE_1172_OFFSET, slot_len)

    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(base_rom_bytes),
        "ge480_rom": str(args.ge480_rom),
        "ge480_md5": md5(ge_rom_bytes),
        "1172_offset": f"0x{GE_1172_OFFSET:X}",
        "1172_slot_len": slot_len,
        "1172_allowed_len": allowed_len,
        "1172_zero_pad_growth": zero_pad_growth,
        "purpose": "Targeted raw 1172 front-end menu-table overlays on the stable t90texstk gameplay candidate.",
        "candidates": [
            build_one(
                spec,
                args.base_rom,
                base_rom_bytes,
                base_raw,
                ge_raw,
                slot_len,
                allowed_len,
                args.out_dir,
                args.prefix,
                args.zopfli_iterations,
            )
            for spec in CANDIDATES
        ],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
