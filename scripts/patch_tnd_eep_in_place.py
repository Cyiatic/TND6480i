#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

import make_tnd_test_save


def patch_save(data, unlock_cheats=True):
    original_len = len(data)
    if original_len < make_tnd_test_save.EEPROM_SIZE:
        raise ValueError(f"input is too small for EEPROM 4K data: {original_len} bytes")

    work = bytearray(data[: make_tnd_test_save.EEPROM_SIZE])
    before = [make_tnd_test_save.slot_info(work, slot) for slot in range(make_tnd_test_save.SAVE_SLOTS)]
    changed_slots = []

    for slot in range(make_tnd_test_save.SAVE_SLOTS):
        offset = make_tnd_test_save.save_slot_offset(slot)
        flags = work[offset + 8]
        folder = flags & 0x07
        if flags & 0x80 or folder not in {0, 1, 2, 3}:
            continue
        work[offset + make_tnd_test_save.TIMES_OFFSET : offset + make_tnd_test_save.SAVE_SIZE] = (
            b"\xFF" * (make_tnd_test_save.SAVE_SIZE - make_tnd_test_save.TIMES_OFFSET)
        )
        if unlock_cheats:
            work[
                offset
                + make_tnd_test_save.CHEAT_UNLOCK_OFFSET : offset
                + make_tnd_test_save.CHEAT_UNLOCK_OFFSET
                + make_tnd_test_save.CHEAT_UNLOCK_SIZE
            ] = b"\xFF" * make_tnd_test_save.CHEAT_UNLOCK_SIZE
        make_tnd_test_save.write_crc(work, offset, make_tnd_test_save.SAVE_SIZE)
        changed_slots.append(slot)

    make_tnd_test_save.write_crc(work, 0, make_tnd_test_save.SMALL_SAVE_SIZE)
    patched = bytes(work) + data[make_tnd_test_save.EEPROM_SIZE :]
    assert len(patched) == original_len

    return patched, {
        "input_bytes": original_len,
        "changed_slots": changed_slots,
        "unlock_cheats": unlock_cheats,
        "before": before,
        "after": [make_tnd_test_save.slot_info(bytearray(patched[:512]), slot) for slot in range(make_tnd_test_save.SAVE_SLOTS)],
    }


def md5(data):
    return hashlib.md5(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(
        description="Patch an exact EverDrive/Gopher TND EEPROM file to all missions/all cheats while preserving file size."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--no-cheats", action="store_true")
    args = parser.parse_args()

    data = args.input.read_bytes()
    patched, report = patch_save(data, unlock_cheats=not args.no_cheats)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patched)

    report.update(
        {
            "input": str(args.input),
            "output": str(args.output),
            "input_md5": md5(data),
            "output_md5": md5(patched),
            "output_bytes": len(patched),
        }
    )
    text = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
