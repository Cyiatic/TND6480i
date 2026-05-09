#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

from build_sc64_isv_instrumented import log_call, nop, runtime, word, write_words
from build_tnd480i_candidate import update_n64_crc_6102


ENTRY_ROM_OFF = 0x1000
ENTRY_RETURN_ROM_OFF = 0x1010
ENTRY_TRAMP_ROM_OFF = 0x33280


def j(addr):
    return 0x08000000 | ((addr >> 2) & 0x03FFFFFF)


def md5(data):
    return hashlib.md5(data).hexdigest()


def apply_entry_instrumentation(rom):
    report = []
    original_entry = [
        int.from_bytes(rom[ENTRY_ROM_OFF + i * 4:ENTRY_ROM_OFF + i * 4 + 4], "big")
        for i in range(4)
    ]

    if any(rom[ENTRY_TRAMP_ROM_OFF:ENTRY_TRAMP_ROM_OFF + 0x80]):
        raise ValueError(f"entry trampoline cave is not empty at 0x{ENTRY_TRAMP_ROM_OFF:X}")

    write_words(rom, ENTRY_TRAMP_ROM_OFF, [
        *log_call("ENTR"),
        *original_entry,
        j(runtime(ENTRY_RETURN_ROM_OFF)),
        nop(),
    ])
    report.append({
        "offset": f"0x{ENTRY_TRAMP_ROM_OFF:X}",
        "note": "entry breadcrumb trampoline; logs ENTR then replays original startup words",
        "original_entry_words": [f"0x{x:08X}" for x in original_entry],
    })

    write_words(rom, ENTRY_ROM_OFF, [
        j(runtime(ENTRY_TRAMP_ROM_OFF)),
        nop(),
        nop(),
        nop(),
    ])
    report.append({
        "offset": f"0x{ENTRY_ROM_OFF:X}",
        "note": "entry jump to SC64 IS-Viewer trampoline",
    })

    return report


def build(args):
    rom = bytearray(Path(args.base_rom).read_bytes())
    report = apply_entry_instrumentation(rom)
    crc1, crc2 = update_n64_crc_6102(rom)
    Path(args.out_rom).write_bytes(rom)
    summary = {
        "base_rom": args.base_rom,
        "out_rom": args.out_rom,
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X}{crc2:08X}",
        "isv_debug_command": "sc64deployer.exe debug --isv 0x03FF0000",
        "expected_markers": ["TND:ENTR", "TND:BCLR", "TND:DFB1", "TND:HVI1"],
        "patches": report,
    }
    if args.report:
        Path(args.report).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", required=True)
    parser.add_argument("--out-rom", required=True)
    parser.add_argument("--report", default=None)
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
