#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


PATCHES = [
    (0x4D42C, 0x240501B8, 0x24050280, "display-cast z-buffer width 640"),
    (0x4D434, 0x2406014A, 0x240601E0, "display-cast z-buffer height 480"),
]


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
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/g1mtabge4.z64"))
    parser.add_argument("--out-rom", type=Path, default=Path("artifacts/generated/g1castz1.z64"))
    parser.add_argument("--report", type=Path, default=Path("reports/tnd480i_g1castz1_cast_zbuffer_20260518.json"))
    args = parser.parse_args()

    rom = bytearray(args.base_rom.read_bytes())
    applied = []
    for offset, expected_old, new, note in PATCHES:
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
        "purpose": (
            "Narrow opening-credits/display-cast probe: keep g1mtabge4 gameplay and dossier work, "
            "but make the cast z-buffer dimensions match the already-applied GE480i view size."
        ),
        "patches": applied,
        "save_outputs": copy_save_pair(args.base_rom, args.out_rom),
        "do_not_promote_until_hardware_compared": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
