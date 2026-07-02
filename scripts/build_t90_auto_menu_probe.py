#!/usr/bin/env python3
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import md5, update_n64_crc_6102


BASE_ROM = Path("artifacts/generated/t90gbtexpost.z64")
OUT_ROM = Path("artifacts/generated/t90gbmenuauto.z64")
REPORT = Path("reports/tnd480i_t90_auto_menu_probe_20260518.json")
ANALOGUE_STEM = Path("artifacts/analogue_test/TNDGMNU")

PATCHES = [
    {
        "offset": 0x3FF34,
        "expected_old": 0x24040018,
        "new": 0x24040005,
        "note": "After the TND title/logo timeout, route to MENU_FILE_SELECT instead of MENU_DISPLAY_CAST.",
    },
]


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def copy_save_set(out_rom):
    outputs = []
    source_sav = BASE_ROM.with_suffix(".sav")
    source_eep = BASE_ROM.with_suffix(".eep")
    for source, target in (
        (source_sav, out_rom.with_suffix(".sav")),
        (source_eep, out_rom.with_suffix(".eep")),
        (source_sav, ANALOGUE_STEM.with_suffix(".SAV")),
        (source_eep, ANALOGUE_STEM.with_suffix(".EEP")),
    ):
        if not source.exists():
            outputs.append({"source": str(source), "target": str(target), "missing": True})
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        payload = target.read_bytes()
        outputs.append(
            {
                "source": str(source),
                "target": str(target),
                "bytes": len(payload),
                "md5": md5(payload),
            }
        )
    return outputs


def main():
    if not BASE_ROM.exists():
        raise SystemExit(f"missing base ROM: {BASE_ROM}")

    base = BASE_ROM.read_bytes()
    rom = bytearray(base)
    applied = []
    for patch in PATCHES:
        offset = patch["offset"]
        old = word(rom, offset)
        if old != patch["expected_old"]:
            raise SystemExit(
                f"unexpected word at 0x{offset:X}: 0x{old:08X}, expected 0x{patch['expected_old']:08X}"
            )
        write_word(rom, offset, patch["new"])
        applied.append(
            {
                "offset": f"0x{offset:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{patch['new']:08X}",
                "note": patch["note"],
            }
        )

    crc1, crc2 = update_n64_crc_6102(rom)
    OUT_ROM.parent.mkdir(parents=True, exist_ok=True)
    OUT_ROM.write_bytes(rom)
    ANALOGUE_STEM.parent.mkdir(parents=True, exist_ok=True)
    ANALOGUE_STEM.with_suffix(".Z64").write_bytes(rom)

    report = {
        "name": "t90gbmenuauto",
        "purpose": (
            "Diagnostic only: keep t90gbtexpost gameplay/front changes, but timeout directly "
            "to file select so GV-USB2 can capture dossier/menu layout without controller input."
        ),
        "base_rom": str(BASE_ROM),
        "base_md5": md5(base),
        "out_rom": str(OUT_ROM),
        "out_md5": md5(rom),
        "analogue_rom": str(ANALOGUE_STEM.with_suffix(".Z64")),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": applied,
        "save_outputs": copy_save_set(OUT_ROM),
        "do_not_promote": True,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
