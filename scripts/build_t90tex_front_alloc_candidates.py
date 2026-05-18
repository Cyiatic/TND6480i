#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


CANDIDATES = [
    {
        "name": "txfrontalloc",
        "purpose": "Apply only the GE480i front-end heap reservation at 0x3FC90/0x3FC94.",
        "patches": [
            (0x3FC90, 0x3C05000B, "front heap reservation upper, GE480i 0xBE200"),
            (0x3FC94, 0x34A5E200, "front heap reservation lower, GE480i 0xBE200"),
        ],
    },
    {
        "name": "txfilealloc",
        "purpose": "Apply only the GE480i file-select/menu allocation at 0x40540/0x40544.",
        "patches": [
            (0x40540, 0x3C0E000B, "file/menu allocation upper, GE480i 0xB4200"),
            (0x40544, 0x35CE4200, "file/menu allocation lower, GE480i 0xB4200"),
        ],
    },
    {
        "name": "txallocboth",
        "purpose": "Apply both GE480i front heap and file/menu allocation reservations.",
        "patches": [
            (0x3FC90, 0x3C05000B, "front heap reservation upper, GE480i 0xBE200"),
            (0x3FC94, 0x34A5E200, "front heap reservation lower, GE480i 0xBE200"),
            (0x40540, 0x3C0E000B, "file/menu allocation upper, GE480i 0xB4200"),
            (0x40544, 0x35CE4200, "file/menu allocation lower, GE480i 0xB4200"),
        ],
    },
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


def build_one(spec, base_rom, base, out_dir):
    rom = bytearray(base)
    applied = []
    for offset, value, note in spec["patches"]:
        old = word(rom, offset)
        write_word(rom, offset, value)
        applied.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{value:08X}",
                "changed": old != value,
                "note": note,
            }
        )
    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = out_dir / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "base_rom": str(base_rom),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": applied,
        "save_outputs": copy_save_pair(base_rom, out_rom),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=Path("artifacts/generated/t90texstk.z64"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/generated"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/tnd480i_t90tex_front_alloc_candidates_20260518.json"),
    )
    args = parser.parse_args()

    if not args.base_rom.exists():
        raise SystemExit(f"missing base ROM: {args.base_rom}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    base = args.base_rom.read_bytes()
    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(base),
        "purpose": "Narrow GE480i front/menu allocation probes on stable t90texstk; candidates must be console-captured and compared to GE480i before promotion.",
        "candidates": [build_one(spec, args.base_rom, base, args.out_dir) for spec in CANDIDATES],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
