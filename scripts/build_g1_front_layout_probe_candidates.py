#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from build_tnd480i_candidate import DIRECT_PATCH_GROUPS, md5, update_n64_crc_6102


ROOT = Path(__file__).resolve().parents[1]
BASE_ROM = ROOT / "artifacts" / "generated" / "g1diff3.z64"
OUT_DIR = ROOT / "artifacts" / "generated"
REPORT = ROOT / "reports" / "tnd480i_g1_front_layout_probe_candidates_20260518.json"

VARIANTS = {
    "g1hlim1": {
        "groups": ["J_front_height_limit_480i"],
        "purpose": "Only raise the title/menu height limit from stock 330 to 480.",
    },
    "g1frontfloat1": {
        "groups": ["J_front_layout_float_480i"],
        "purpose": "Only apply the GE480i title/menu float constants near the front layout path.",
    },
    "g1fronty1": {
        "groups": ["J_front_layout_y_480i"],
        "purpose": "Only apply the GE480i front layout Y offsets following the height limit.",
    },
    "g1front460a1": {
        "groups": ["J_front_layout_460_480i"],
        "purpose": "Only apply the GE480i computed front-layout block at 0x460A8-0x460E0.",
    },
    "g1front4aaa1": {
        "groups": ["J_front_layout_4aaa_480i"],
        "purpose": "Only apply the GE480i title/menu layout constants at 0x4AAAC-0x4AAC4.",
    },
    "g1hlimfy1": {
        "groups": ["J_front_height_limit_480i", "J_front_layout_float_480i", "J_front_layout_y_480i"],
        "purpose": "Apply the height-limit, float, and immediate Y-offset constants together.",
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


def iter_group_patches(groups):
    by_offset = {}
    for group in groups:
        for offset, value, note in DIRECT_PATCH_GROUPS[group]:
            by_offset[offset] = {"offset": offset, "new": value, "group": group, "note": note}
    for offset in sorted(by_offset):
        yield by_offset[offset]


def make_bps(target, out_stem):
    patch = ROOT / "artifacts" / "generated" / f"TND6480i_{out_stem}_from_baseline_tnd.bps"
    manifest = ROOT / "reports" / f"tnd6480i_{out_stem}_bps_manifest.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "make_bps_patch.py"),
        str(ROOT / "artifacts" / "roms" / "BASELINE_TND64_Expanded_direct_from_stock.z64"),
        str(target),
        str(patch),
        "--manifest",
        str(manifest),
        "--metadata",
        f"TND6480i {out_stem}: g1diff3 front-layout probe.",
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)
    return {"patch": str(patch), "manifest": str(manifest)}


def build_one(name, spec, base_rom, base):
    rom = bytearray(base)
    patches = []
    for patch in iter_group_patches(spec["groups"]):
        offset = patch["offset"]
        old = word(rom, offset)
        write_word(rom, offset, patch["new"])
        patches.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{patch['new']:08X}",
                "changed": old != patch["new"],
                "group": patch["group"],
                "note": patch["note"],
            }
        )

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
        "patch_count": len(patches),
        "changed_patch_count": sum(1 for patch in patches if patch["changed"]),
        "patches": patches,
        "save_outputs": copy_save_pair(base_rom, out_rom),
        "bps": make_bps(out_rom, name),
        "do_not_promote_until_hardware_compared": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=BASE_ROM)
    parser.add_argument("--variant", action="append", choices=sorted(VARIANTS))
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    variants = args.variant or sorted(VARIANTS)
    base = args.base_rom.read_bytes()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report = [build_one(name, VARIANTS[name], args.base_rom, base) for name in variants]
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
