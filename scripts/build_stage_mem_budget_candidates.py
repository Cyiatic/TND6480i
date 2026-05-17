#!/usr/bin/env python3
import json
from pathlib import Path

from build_tnd480i_candidate import (
    GE_1172_OFFSET,
    inflate_ge1172,
    md5,
    pack_ge1172,
    update_n64_crc_6102,
)


BASE_ROM = Path("artifacts/generated/tnd58.z64")
BASE_SAVE = Path("artifacts/generated/tnd58.sav")
OUT_DIR = Path("artifacts/generated")
REPORT_DIR = Path("reports")

STAGE_STRINGS = {
    "Party": {
        "raw_offset": 0x7D0C,
        "base": "-ml0 -me0 -mgfx70  -mvtx50 -mt900 -ma200",
    },
    "Hotel": {
        "raw_offset": 0x7D90,
        "base": "-ml0 -me0 -mgfx100 -mvtx50 -mt950 -ma220",
    },
    "City": {
        "raw_offset": 0x7E40,
        "base": "-ml0 -me0 -mgfx100 -mvtx50 -mt850 -ma200",
    },
    "Volcano": {
        "raw_offset": 0x7EC4,
        "base": "-ml0 -me0 -mgfx60  -mvtx40 -mt850 -ma300",
    },
    "The End": {
        "raw_offset": 0x7F1C,
        "base": "-ml0 -me0 -mgfx100 -mvtx50 -mt700 -ma150",
    },
}

CANDIDATES = [
    {
        "name": "tnd58mem_mtdown",
        "purpose": (
            "Reduce texture-cache pressure only on the direct-stage failure groups. "
            "This tests whether the 480i stage path is simply running out of stage "
            "bank headroom before or during world render."
        ),
        "strings": {
            "Party": "-ml0 -me0 -mgfx70  -mvtx50 -mt800 -ma200",
            "Hotel": "-ml0 -me0 -mgfx100 -mvtx50 -mt850 -ma220",
            "City": "-ml0 -me0 -mgfx100 -mvtx50 -mt750 -ma200",
            "Volcano": "-ml0 -me0 -mgfx60  -mvtx40 -mt750 -ma300",
            "The End": "-ml0 -me0 -mgfx100 -mvtx50 -mt600 -ma150",
        },
    },
    {
        "name": "tnd58mem_gfxvtx_keep",
        "purpose": (
            "Increase display-list and dynamic-vertex/matrix pools for the failure "
            "groups while leaving texture and mema budgets unchanged. This isolates "
            "gfx/vtx overflow as a possible cause, at the risk of using more stage RAM."
        ),
        "strings": {
            "Party": "-ml0 -me0 -mgfx100 -mvtx70 -mt900 -ma200",
            "Hotel": "-ml0 -me0 -mgfx130 -mvtx70 -mt950 -ma220",
            "City": "-ml0 -me0 -mgfx130 -mvtx70 -mt850 -ma200",
            "Volcano": "-ml0 -me0 -mgfx100 -mvtx70 -mt850 -ma300",
            "The End": "-ml0 -me0 -mgfx130 -mvtx70 -mt700 -ma150",
        },
    },
    {
        "name": "tnd58mem_gfxvtx_bal",
        "purpose": (
            "Increase gfx/vtx pools but pay for most or all of that increase by "
            "lowering texture-cache budgets. This keeps the total named allocations "
            "near the current tnd58 budget while checking for display-list pressure."
        ),
        "strings": {
            "Party": "-ml0 -me0 -mgfx100 -mvtx70 -mt800 -ma200",
            "Hotel": "-ml0 -me0 -mgfx130 -mvtx70 -mt850 -ma220",
            "City": "-ml0 -me0 -mgfx130 -mvtx70 -mt750 -ma200",
            "Volcano": "-ml0 -me0 -mgfx100 -mvtx70 -mt710 -ma300",
            "The End": "-ml0 -me0 -mgfx130 -mvtx70 -mt600 -ma150",
        },
    },
]


def copy_save(out_rom):
    if not BASE_SAVE.exists():
        return []
    save = BASE_SAVE.read_bytes()
    eep = save if len(save) >= 2048 else save + b"\0" * (2048 - len(save))
    outputs = []
    for path, data in ((out_rom.with_suffix(".sav"), save), (out_rom.with_suffix(".eep"), eep)):
        path.write_bytes(data)
        outputs.append({"path": str(path), "bytes": len(data), "md5": md5(data)})
    return outputs


def zero_pad_capacity(rom, offset, slot_len):
    end = offset + slot_len
    cursor = end
    while cursor < len(rom) and rom[cursor] == 0:
        cursor += 1
    return cursor - offset, cursor - end


def patch_stage_strings(raw, replacements):
    out = bytearray(raw)
    patches = []
    for stage, new_text in replacements.items():
        spec = STAGE_STRINGS[stage]
        offset = spec["raw_offset"]
        old = spec["base"].encode("ascii")
        new = new_text.encode("ascii")
        if len(old) != len(new):
            raise ValueError(f"{stage}: replacement length changed: {len(old)} -> {len(new)}")
        current = bytes(out[offset : offset + len(old)])
        if current != old:
            raise ValueError(
                f"{stage}: expected {old!r} at raw 0x{offset:X}, found {current!r}"
            )
        out[offset : offset + len(old)] = new
        patches.append(
            {
                "stage": stage,
                "raw_offset": f"0x{offset:X}",
                "old": spec["base"],
                "new": new_text,
            }
        )
    return bytes(out), patches


def build_one(candidate):
    rom = bytearray(BASE_ROM.read_bytes())
    raw, slot_len = inflate_ge1172(rom, GE_1172_OFFSET)
    patched_raw, patches = patch_stage_strings(raw, candidate["strings"])
    packed = pack_ge1172(patched_raw)
    allowed_packed_len, zero_pad_growth = zero_pad_capacity(rom, GE_1172_OFFSET, slot_len)
    if len(packed) > allowed_packed_len:
        raise ValueError(
            f"{candidate['name']}: packed 1172 stream too large: "
            f"0x{len(packed):X} > 0x{allowed_packed_len:X}"
        )

    rom[GE_1172_OFFSET : GE_1172_OFFSET + allowed_packed_len] = b"\0" * allowed_packed_len
    rom[GE_1172_OFFSET : GE_1172_OFFSET + len(packed)] = packed
    crc1, crc2 = update_n64_crc_6102(rom)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_rom = OUT_DIR / f"{candidate['name']}.z64"
    out_rom.write_bytes(rom)
    save_outputs = copy_save(out_rom)

    verify_raw, verify_consumed = inflate_ge1172(rom, GE_1172_OFFSET)
    return {
        "name": candidate["name"],
        "purpose": candidate["purpose"],
        "base_rom": str(BASE_ROM),
        "base_md5": md5(BASE_ROM.read_bytes()),
        "out_rom": str(out_rom),
        "out_md5": md5(rom),
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "slot_len": f"0x{slot_len:X}",
        "allowed_packed_len": f"0x{allowed_packed_len:X}",
        "zero_pad_growth": f"0x{zero_pad_growth:X}",
        "packed_len": f"0x{len(packed):X}",
        "verify_consumed": f"0x{verify_consumed:X}",
        "main_raw_md5": md5(patched_raw),
        "verify_main_raw_md5": md5(verify_raw),
        "patches": patches,
        "save_outputs": save_outputs,
        "direct_probe_focus": ["Party", "Hotel", "City", "Volcano", "The End"],
    }


def main():
    if not BASE_ROM.exists():
        raise SystemExit(f"base ROM not found: {BASE_ROM}")

    reports = [build_one(candidate) for candidate in CANDIDATES]
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "tnd480i_stage_mem_budget_candidates_20260517.json"
    report_path.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
