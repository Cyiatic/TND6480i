#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


PATCH_SETS = {
    "post": [
    (0x3C68C, 0x3C0F0600, 0x240F0000, "suppress second moving gunbarrel display-list command"),
    ],
    "slow": [
    (0x3DF04, 0x3C018005, 0x3C014068, "gunbarrel case-1 decrement 3.625f upper"),
    (0x3DF08, 0xC428F304, 0x44814000, "gunbarrel case-1 decrement 3.625f move"),
    ],
}

PATCH_SET_ORDER = {
    "combo": ["post", "slow"],
    "slow": ["slow"],
    "post": ["post"],
}


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


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
        outputs.append({"source": str(source), "target": str(target), "bytes": len(payload), "md5": md5(payload)})
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/g1castz1.z64"))
    parser.add_argument("--out-rom", type=Path, default=Path("artifacts/generated/g1castgb1.z64"))
    parser.add_argument("--report", type=Path, default=Path("reports/tnd480i_g1castgb1_gunbarrel_cadence_20260518.json"))
    parser.add_argument("--patch-set", choices=sorted(PATCH_SET_ORDER), default="combo")
    args = parser.parse_args()

    rom = bytearray(args.base_rom.read_bytes())
    applied = []
    patches = []
    for patch_set in PATCH_SET_ORDER[args.patch_set]:
        patches.extend(PATCH_SETS[patch_set])

    for offset, expected_old, new, note in patches:
        old = word(rom, offset)
        if old not in (expected_old, new):
            raise SystemExit(
                f"unexpected word at 0x{offset:X}: 0x{old:08X}, expected 0x{expected_old:08X}"
            )
        write_word(rom, offset, new)
        applied.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{new:08X}",
                "changed": old != new,
                "note": note,
            }
        )

    crc1, crc2 = update_n64_crc_6102(rom)
    args.out_rom.parent.mkdir(parents=True, exist_ok=True)
    args.out_rom.write_bytes(rom)
    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(args.base_rom.read_bytes()),
        "out_rom": str(args.out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "purpose": "Narrow gunbarrel probe on top of g1castz1.",
        "patch_set": args.patch_set,
        "patches": applied,
        "save_outputs": copy_save_pair(args.base_rom, args.out_rom),
        "do_not_promote_until_hardware_compared": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
