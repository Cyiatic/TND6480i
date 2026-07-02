#!/usr/bin/env python3
"""Patch GoldenEye/TND EEPROM save option bits and refresh CRCs.

The 480i text diagnostics need comparable HUD settings. The all-missions save
we used for hardware probes can have "ammo on screen" disabled, which prevents
GE480i from drawing the same bottom-right ammo text we want to measure.

Anti-aliasing also affects perceived text quality, but its option bit is not
mapped here yet. Do not add it without a same-folder save diff where only the
AA option was toggled.
"""

import argparse
import hashlib
import json
from pathlib import Path

import make_tnd_test_save


OPTION_DISPLAYAMMO = 0x0020
OPTION_SCREENWIDE = 0x0040
OPTION_SCREENRATIO = 0x0080
OPTION_SCREENCINEMA = 0x0800
DEFAULT_OPTIONS = 0x003A


def md5(data):
    return hashlib.md5(data).hexdigest()


def parse_int(raw):
    return int(raw, 0)


def patch_options(data, set_bits, clear_bits, force_default):
    original_len = len(data)
    if original_len < make_tnd_test_save.EEPROM_SIZE:
        data = data + b"\0" * (make_tnd_test_save.EEPROM_SIZE - original_len)

    work = bytearray(data[: make_tnd_test_save.EEPROM_SIZE])
    before = []
    after = []
    changed_slots = []

    for slot in range(make_tnd_test_save.SAVE_SLOTS):
        offset = make_tnd_test_save.save_slot_offset(slot)
        flags = work[offset + 8]
        before_options = int.from_bytes(work[offset + 0x0C : offset + 0x0E], "big")
        before.append(
            {
                "slot": slot,
                "folder": flags & 0x07,
                "reset": bool(flags & 0x80),
                "options": f"0x{before_options:04X}",
                "display_ammo": bool(before_options & OPTION_DISPLAYAMMO),
            }
        )

        if flags & 0x80:
            new_options = before_options
        elif force_default:
            new_options = DEFAULT_OPTIONS
        else:
            new_options = (before_options | set_bits) & ~clear_bits

        if new_options != before_options:
            work[offset + 0x0C : offset + 0x0E] = new_options.to_bytes(2, "big")
            make_tnd_test_save.write_crc(work, offset, make_tnd_test_save.SAVE_SIZE)
            changed_slots.append(slot)

        after.append(
            {
                "slot": slot,
                "folder": flags & 0x07,
                "reset": bool(flags & 0x80),
                "options": f"0x{new_options:04X}",
                "display_ammo": bool(new_options & OPTION_DISPLAYAMMO),
                "crc_ok": make_tnd_test_save.slot_info(work, slot)["crc_ok"],
            }
        )

    make_tnd_test_save.write_crc(work, 0, make_tnd_test_save.SMALL_SAVE_SIZE)
    patched = bytes(work)
    if original_len > make_tnd_test_save.EEPROM_SIZE:
        patched += data[make_tnd_test_save.EEPROM_SIZE :]

    return patched, {
        "input_bytes": original_len,
        "output_bytes": len(patched),
        "set_bits": f"0x{set_bits:04X}",
        "clear_bits": f"0x{clear_bits:04X}",
        "force_default": force_default,
        "changed_slots": changed_slots,
        "before": before,
        "after": after,
    }


def main():
    parser = argparse.ArgumentParser(description="Patch GE/TND EEPROM save option bits.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--set", dest="set_bits", type=parse_int, default=0)
    parser.add_argument("--clear", dest="clear_bits", type=parse_int, default=0)
    parser.add_argument("--ammo-on", action="store_true", help="Set OPTION_DISPLAYAMMO.")
    parser.add_argument("--fullscreen", action="store_true", help="Clear widescreen/cinema/16:9 bits.")
    parser.add_argument("--default-options", action="store_true", help="Set valid folders to GE default 0x003A.")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    set_bits = args.set_bits
    clear_bits = args.clear_bits
    if args.ammo_on:
        set_bits |= OPTION_DISPLAYAMMO
    if args.fullscreen:
        clear_bits |= OPTION_SCREENWIDE | OPTION_SCREENRATIO | OPTION_SCREENCINEMA

    source = args.input.read_bytes()
    patched, report = patch_options(source, set_bits, clear_bits, args.default_options)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patched)
    report.update(
        {
            "input": str(args.input),
            "output": str(args.output),
            "input_md5": md5(source),
            "output_md5": md5(patched),
        }
    )

    text = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
