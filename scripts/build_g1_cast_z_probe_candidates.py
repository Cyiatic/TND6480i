#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


ROOT = Path(__file__).resolve().parents[1]
BASE_ROM = ROOT / "artifacts" / "generated" / "g1hlim1.z64"
OUT_DIR = ROOT / "artifacts" / "generated"
REPORT = ROOT / "reports" / "tnd480i_g1hlim1_cast_z_probe_candidates_20260519.json"

WIDTH_WORD = 0x240501B8
HEIGHT_WORD = 0x2406014A
GE_WIDTH_WORD = 0x24050280
GE_HEIGHT_WORD = 0x240601E0

VARIANTS = {
    "g1hczw1": {
        "purpose": "g1hlim1 with display-cast z-buffer width restored to stock/TND 440, height left at GE480i 480.",
        "patches": [(0x4D42C, WIDTH_WORD, "display-cast z-buffer width stock 440")],
    },
    "g1hczh1": {
        "purpose": "g1hlim1 with display-cast z-buffer height restored to stock/TND 330, width left at GE480i 640.",
        "patches": [(0x4D434, HEIGHT_WORD, "display-cast z-buffer height stock 330")],
    },
    "g1hczwh1": {
        "purpose": "g1hlim1 with both display-cast z-buffer dimensions restored to stock/TND 440x330.",
        "patches": [
            (0x4D42C, WIDTH_WORD, "display-cast z-buffer width stock 440"),
            (0x4D434, HEIGHT_WORD, "display-cast z-buffer height stock 330"),
        ],
    },
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


def build_one(name, spec, base_rom, base):
    rom = bytearray(base)
    patches = []
    for offset, new, note in spec["patches"]:
        old = word(rom, offset)
        if offset == 0x4D42C and old != GE_WIDTH_WORD:
            raise SystemExit(f"{name}: unexpected width word 0x{old:08X} at 0x{offset:X}")
        if offset == 0x4D434 and old != GE_HEIGHT_WORD:
            raise SystemExit(f"{name}: unexpected height word 0x{old:08X} at 0x{offset:X}")
        write_word(rom, offset, new)
        patches.append({
            "offset": f"0x{offset:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{new:08X}",
            "note": note,
        })

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = OUT_DIR / f"{name}.z64"
    out_rom.write_bytes(rom)
    return {
        "name": name,
        "purpose": spec["purpose"],
        "base_rom": str(base_rom),
        "base_md5": md5(base),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": patches,
        "save_outputs": copy_save_pair(base_rom, out_rom),
        "do_not_promote_until_hardware_compared": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=BASE_ROM)
    parser.add_argument("--variant", choices=sorted(VARIANTS), action="append")
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    variants = args.variant or sorted(VARIANTS)
    base = args.base_rom.read_bytes()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report = [build_one(name, VARIANTS[name], args.base_rom, base) for name in variants]
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.report), "variants": [item["name"] for item in report]}, indent=2))


if __name__ == "__main__":
    main()
