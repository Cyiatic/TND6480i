#!/usr/bin/env python3
import argparse
import hashlib
import json
import zlib
from pathlib import Path

from build_tnd480i_candidate import pack_ge1172, update_n64_crc_6102


TITLE_BANK_ANCHOR = b"Easy\x00\x00\x00\x00Normal\x00\x00Hard\x00\x00\x00\x00Custom"


def inflate_1172(rom, offset):
    if rom[offset : offset + 2] != b"\x11\x72":
        raise ValueError(f"no 1172 marker at 0x{offset:X}")
    decomp = zlib.decompressobj(-15)
    raw = decomp.decompress(rom[offset + 2 :])
    raw += decomp.flush()
    consumed = len(rom[offset + 2 :]) - len(decomp.unused_data) + 2
    return raw, consumed


def find_title_bank(rom):
    pos = 0
    candidates = []
    while True:
        offset = rom.find(b"\x11\x72", pos)
        if offset < 0:
            break
        pos = offset + 1
        try:
            raw, consumed = inflate_1172(rom, offset)
        except Exception:
            continue
        if TITLE_BANK_ANCHOR in raw:
            candidates.append((offset, consumed, raw))

    if len(candidates) != 1:
        raise ValueError(f"expected one title text bank, found {len(candidates)}")
    return candidates[0]


def patch_custom_labels(raw):
    out = bytearray(raw)
    replacements = []

    for old, new in [
        (b"Custom\x00", b"007\x00\x00\x00\x00"),
        (b"Custom\n\x00", b"007\n\x00\x00\x00\x00"),
    ]:
        positions = []
        start = 0
        while True:
            idx = raw.find(old, start)
            if idx < 0:
                break
            positions.append(idx)
            start = idx + 1

        if len(positions) != 1:
            raise ValueError(f"expected one occurrence of {old!r}, found {len(positions)}")

        idx = positions[0]
        out[idx : idx + len(old)] = new
        replacements.append(
            {
                "offset_in_uncompressed_title_bank": f"0x{idx:X}",
                "old": old.hex(),
                "new": new.hex(),
            }
        )

    return bytes(out), replacements


def main():
    parser = argparse.ArgumentParser(
        description="Patch TND64 title text difficulty labels from Custom back to 007."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    rom = bytearray(args.input.read_bytes())
    original_md5 = hashlib.md5(rom).hexdigest()

    stream_offset, consumed, raw = find_title_bank(rom)
    patched_raw, replacements = patch_custom_labels(raw)
    packed = pack_ge1172(patched_raw)

    if len(packed) > consumed:
        raise ValueError(
            f"patched title bank grew past original slot: 0x{len(packed):X} > 0x{consumed:X}"
        )

    rom[stream_offset : stream_offset + len(packed)] = packed
    rom[stream_offset + len(packed) : stream_offset + consumed] = b"\x00" * (
        consumed - len(packed)
    )
    crc1, crc2 = update_n64_crc_6102(rom)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(rom)

    report = {
        "input": str(args.input),
        "input_md5": original_md5,
        "output": str(args.output),
        "output_md5": hashlib.md5(rom).hexdigest(),
        "title_bank_rom_offset": f"0x{stream_offset:X}",
        "title_bank_original_compressed_size": f"0x{consumed:X}",
        "title_bank_patched_compressed_size": f"0x{len(packed):X}",
        "title_bank_uncompressed_size": len(raw),
        "replacements": replacements,
        "header_crc": f"{crc1:08X} {crc2:08X}",
    }

    text = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
