#!/usr/bin/env python3
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from build_tnd480i_candidate import (
    GE_1172_OFFSET,
    inflate_ge1172,
    pack_ge1172,
    update_n64_crc_6102,
)


ROOT = Path(__file__).resolve().parents[1]
LEGAL_TABLE_RAW_OFFSET = 0x9C3C
LEGAL_TABLE_RECORDS = 12
LEGAL_TABLE_RECORD_SIZE = 20


def md5(data):
    return hashlib.md5(data).hexdigest()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return Path(path).read_bytes()


def write(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        Path(path).write_text(data, encoding="utf-8")
    else:
        Path(path).write_bytes(data)


def unpack_record(raw, idx):
    off = LEGAL_TABLE_RAW_OFFSET + idx * LEGAL_TABLE_RECORD_SIZE
    chunk = raw[off:off + LEGAL_TABLE_RECORD_SIZE]
    return {
        "h_pos": int.from_bytes(chunk[0:4], "big", signed=True),
        "v_pos": int.from_bytes(chunk[4:8], "big", signed=True),
        "halign": int.from_bytes(chunk[8:12], "big", signed=True),
        "valign": int.from_bytes(chunk[12:16], "big", signed=True),
        "txtID": int.from_bytes(chunk[16:18], "big"),
        "anonymous_5": int.from_bytes(chunk[18:20], "big"),
    }


def patch_legal_table(base_raw, ge480_raw):
    out = bytearray(base_raw)
    rows = []
    for idx in range(LEGAL_TABLE_RECORDS):
        off = LEGAL_TABLE_RAW_OFFSET + idx * LEGAL_TABLE_RECORD_SIZE
        old = unpack_record(out, idx)
        ge = unpack_record(ge480_raw, idx)

        # Copy only geometry/alignment. TND64's title-bank text slots stay intact.
        out[off:off + 16] = ge480_raw[off:off + 16]
        new = unpack_record(out, idx)
        rows.append({
            "idx": idx,
            "raw_offset": f"0x{off:X}",
            "old": old,
            "ge480i": ge,
            "new": new,
            "text_id_preserved": old["txtID"] == new["txtID"],
        })
    return bytes(out), rows


def zero_pad_capacity(rom, offset, slot_len):
    end = offset + slot_len
    limit = end
    while limit < len(rom) and rom[limit] == 0:
        limit += 1
    return limit - offset, limit - end


def make_bps(source, target, patch, manifest, note):
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "make_bps_patch.py"),
        str(source),
        str(target),
        str(patch),
        "--manifest",
        str(manifest),
        "--metadata",
        note,
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)


def build(args):
    base_rom = Path(args.base_rom)
    ge480_rom = Path(args.ge480i_rom)
    out_rom = Path(args.out_rom)
    report_path = Path(args.report)

    base = bytearray(read(base_rom))
    ge480 = read(ge480_rom)

    base_raw, slot_len = inflate_ge1172(base, args.offset)
    ge480_raw, _ = inflate_ge1172(ge480, args.offset)
    patched_raw, row_report = patch_legal_table(base_raw, ge480_raw)

    packed = pack_ge1172(patched_raw, args.zopfli_iterations)
    allowed_packed_len = slot_len
    zero_pad_growth = 0
    if args.allow_zero_pad_growth:
        allowed_packed_len, zero_pad_growth = zero_pad_capacity(base, args.offset, slot_len)
    if len(packed) > allowed_packed_len:
        raise ValueError(f"packed stream too large: 0x{len(packed):X} > 0x{allowed_packed_len:X}")

    base[args.offset:args.offset + allowed_packed_len] = b"\x00" * allowed_packed_len
    base[args.offset:args.offset + len(packed)] = packed
    crc1, crc2 = update_n64_crc_6102(base)
    write(out_rom, base)

    verify_raw, verify_consumed = inflate_ge1172(base, args.offset)
    if verify_raw != patched_raw:
        raise ValueError("repacked 1172 stream did not verify")

    save_outputs = []
    for suffix in (".sav", ".eep"):
        src = base_rom.with_suffix(suffix)
        if src.exists():
            dst = out_rom.with_suffix(suffix)
            shutil.copyfile(src, dst)
            data = read(dst)
            save_outputs.append({
                "source": str(src),
                "target": str(dst),
                "bytes": len(data),
                "md5": md5(data),
            })

    bps_patch = ROOT / "artifacts" / "generated" / f"TND6480i_{out_rom.stem}_from_baseline_tnd.bps"
    bps_manifest = ROOT / "reports" / f"tnd6480i_{out_rom.stem}_bps_manifest.json"
    make_bps(
        ROOT / "artifacts" / "roms" / "BASELINE_TND64_Expanded_direct_from_stock.z64",
        out_rom,
        bps_patch,
        bps_manifest,
        f"TND6480i {out_rom.stem}: g1casta1 plus GE480i legal/classification page geometry table only.",
    )

    out_data = read(out_rom)
    report = {
        "base_rom": str(base_rom),
        "ge480i_rom": str(ge480_rom),
        "out_rom": str(out_rom),
        "out_md5": md5(out_data),
        "out_sha256": sha256(out_data),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": "Patch only the legal/classification page table at raw 0x9C3C to GE480i geometry/alignment while preserving TND text IDs.",
        "raw_offset": f"0x{LEGAL_TABLE_RAW_OFFSET:X}",
        "records": LEGAL_TABLE_RECORDS,
        "slot_len": f"0x{slot_len:X}",
        "allowed_packed_len": f"0x{allowed_packed_len:X}",
        "zero_pad_growth": f"0x{zero_pad_growth:X}",
        "packed_len": f"0x{len(packed):X}",
        "verify_consumed": f"0x{verify_consumed:X}",
        "base_raw_md5": md5(base_raw),
        "patched_raw_md5": md5(patched_raw),
        "rows": row_report,
        "save_outputs": save_outputs,
        "bps_patch": str(bps_patch),
        "bps_manifest": str(bps_manifest),
    }
    write(report_path, json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", default=str(ROOT / "artifacts" / "generated" / "g1casta1.z64"))
    parser.add_argument("--ge480i-rom", default=str(ROOT / "artifacts" / "roms" / "BASELINE_GE_480i_direct_from_stock.z64"))
    parser.add_argument("--out-rom", default=str(ROOT / "artifacts" / "generated" / "g1class1.z64"))
    parser.add_argument("--report", default=str(ROOT / "reports" / "tnd480i_g1class1_legal_classification_20260518.json"))
    parser.add_argument("--offset", type=lambda x: int(x, 0), default=GE_1172_OFFSET)
    parser.add_argument("--zopfli-iterations", type=int, default=15)
    parser.add_argument("--allow-zero-pad-growth", action="store_true", default=True)
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
