#!/usr/bin/env python3
import argparse
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


ROOT = Path(__file__).resolve().parents[1]
BASE_ROM = ROOT / "artifacts" / "generated" / "g1hnext1.z64"
OUT_DIR = ROOT / "artifacts" / "generated"
REPORT = ROOT / "reports" / "tnd480i_g1_file_select_backdrop_candidates_20260519.json"

TIMEOUT_MENU_WORD_OFFSET = 0x3FF34
EXPECTED_TIMEOUT_WORD = 0x24040018
FILE_SELECT_MENU_ID = 0x05
FILE_SELECT_CALLSITE = 0x41030
ORIGINAL_FILE_SELECT_JAL = 0x0FC01F32

# Clone offsets in the already-installed file-select backdrop blitter cave.
CLONE_TEXTURE_WIDTH_UPPER = 0x4F5E8
CLONE_ROW_LOOP_LIMIT = 0x4F998
CLONE_ROW_STRIDE = 0x4F9A0

CANDIDATES = [
    {
        "name": "g1fsorig1",
        "purpose": "Use the original GE/TND file-select backdrop wrapper instead of the cloned 480i blitter; checks whether the right-side rectangular smear is clone-specific.",
        "patches": [
            (FILE_SELECT_CALLSITE, ORIGINAL_FILE_SELECT_JAL, "restore file-select backdrop callsite to original wrapper"),
        ],
    },
    {
        "name": "g1fsstride508",
        "purpose": "Keep the cloned file-select path but try a 508-byte/source-width stride, matching TND's apparent visible file-select source span more closely than 640.",
        "patches": [
            (CLONE_ROW_STRIDE, 0x261001FC, "clone backdrop row stride 508"),
        ],
    },
    {
        "name": "g1fsstride560",
        "purpose": "Keep the cloned file-select path but reduce the row stride from 640 to 560 as a midpoint probe for the right-side repeat smear.",
        "patches": [
            (CLONE_ROW_STRIDE, 0x26100230, "clone backdrop row stride 560"),
        ],
    },
    {
        "name": "g1fsrowstride508",
        "purpose": "Keep the cloned path with a 480-row loop and 508 stride; probes whether the clone is overrunning both height and row pitch.",
        "patches": [
            (CLONE_ROW_LOOP_LIMIT, 0x292101E0, "clone backdrop row loop limit 480"),
            (CLONE_ROW_STRIDE, 0x261001FC, "clone backdrop row stride 508"),
        ],
    },
    {
        "name": "g1fstexstock",
        "purpose": "Keep cloned geometry but restore the first texture-width word to stock/TND; checks whether the GE480i E49F texture width causes the file-select smear.",
        "patches": [
            (CLONE_TEXTURE_WIDTH_UPPER, 0x3C0AE46D, "clone backdrop first texture-width word back to stock"),
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


def route_to_file_select(rom):
    old = word(rom, TIMEOUT_MENU_WORD_OFFSET)
    if old != EXPECTED_TIMEOUT_WORD:
        raise ValueError(
            f"unexpected timeout menu word at 0x{TIMEOUT_MENU_WORD_OFFSET:X}: "
            f"0x{old:08X}, expected 0x{EXPECTED_TIMEOUT_WORD:08X}"
        )
    new = 0x24040000 | FILE_SELECT_MENU_ID
    write_word(rom, TIMEOUT_MENU_WORD_OFFSET, new)
    return {"offset": f"0x{TIMEOUT_MENU_WORD_OFFSET:X}", "old": f"0x{old:08X}", "new": f"0x{new:08X}"}


def build_candidate(base_rom, base, spec, out_dir):
    rom = bytearray(base)
    applied = []
    for offset, value, note in spec["patches"]:
        old = word(rom, offset)
        write_word(rom, offset, value)
        applied.append({
            "offset": f"0x{offset:X}",
            "old": f"0x{old:08X}",
            "new": f"0x{value:08X}",
            "changed": old != value,
            "note": note,
        })

    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = out_dir / f"{spec['name']}.z64"
    out_rom.write_bytes(rom)

    route_rom = bytearray(rom)
    route_patch = route_to_file_select(route_rom)
    rcrc1, rcrc2 = update_n64_crc_6102(route_rom)
    route_path = out_dir / f"{spec['name']}auto05.z64"
    route_path.write_bytes(route_rom)

    return {
        "name": spec["name"],
        "purpose": spec["purpose"],
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": applied,
        "save_outputs": copy_save_pair(base_rom, out_rom),
        "route": {
            "out_rom": str(route_path),
            "out_md5": md5(route_rom),
            "header_crc": f"{rcrc1:08X} {rcrc2:08X}",
            "route_patch": route_patch,
            "save_outputs": copy_save_pair(base_rom, route_path),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", type=Path, default=BASE_ROM)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    if not args.base_rom.exists():
        raise SystemExit(f"missing base ROM: {args.base_rom}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    base = args.base_rom.read_bytes()

    report = {
        "base_rom": str(args.base_rom),
        "base_md5": md5(base),
        "purpose": "Probe only the remaining file-select gunbarrel backdrop smear while preserving g1hnext1 tab/gameplay/dossier fixes.",
        "candidates": [build_candidate(args.base_rom, base, spec, args.out_dir) for spec in CANDIDATES],
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.report), "candidates": [c["name"] for c in report["candidates"]]}, indent=2))


if __name__ == "__main__":
    main()
