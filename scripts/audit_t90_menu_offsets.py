#!/usr/bin/env python3
import json
import struct
from pathlib import Path

from capstone import CS_ARCH_MIPS, CS_MODE_BIG_ENDIAN, CS_MODE_MIPS32, Cs


ROM = Path("artifacts/generated/t90viewge.z64")
MENU_REPORT = Path("reports/tnd480i_t90_menu_function_canaries_20260518.json")
OUT = Path("reports/t90_menu_offset_audit_20260518.json")

SOURCE_HINTS = {
    "menu05_file_select": {
        "source": r"C:\Users\codex\Documents\n64\007-decomp\src\game\front.c",
        "symbols": [
            "constructor_menu05_fileselect",
            "copy/erase/select label and icon placement",
        ],
        "risk": "file-select icon/text setup is coupled to folder model projection; scale-only patches already removed labels/icons",
    },
    "menu06_mode_select": {
        "source": r"C:\Users\codex\Documents\n64\007-decomp\src\game\front.c",
        "symbols": [
            "constructor_menu06_modesel",
            "mode-select wallet/Bond layout",
        ],
        "risk": "small patch count, mostly transition thresholds; no visible route win in Gopher",
    },
    "menu07_mission_select": {
        "source": r"C:\Users\codex\Documents\n64\007-decomp\src\game\front.c",
        "symbols": [
            "constructor_menu07_missionsel",
            "cursor_xpos_table_mission_select",
            "cursor_ypos_table_mission_select",
        ],
        "risk": "includes cursor/highlight state and document box coordinates; raw GE constants assume GE mission grid",
    },
    "menu08_difficulty": {
        "source": r"C:\Users\codex\Documents\n64\007-decomp\src\game\front.c",
        "symbols": [
            "constructor_menu08_difficulty",
            "print_current_solo_briefing_stage_name",
            "set_cursor_pos_difficulty",
        ],
        "risk": "mixes cursor tween thresholds, text coordinates, highlight rectangles, and checkmark placement",
    },
    "menu09_007_options": {
        "source": r"C:\Users\codex\Documents\n64\007-decomp\src\game\front.c",
        "symbols": [
            "constructor_menu09_007options",
            "007 difficulty sliders",
        ],
        "risk": "not relevant until custom 007 options screen is prioritized",
    },
}


def word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def signed16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def classify_instruction(value):
    op = value >> 26
    rt = (value >> 16) & 0x1F
    imm = signed16(value)
    if op == 0x09:
        return f"addiu immediate {imm}"
    if op == 0x0F:
        return f"lui upper 0x{value & 0xFFFF:04X}"
    if op == 0x0A:
        return f"slti threshold {imm}"
    if op == 0x0D:
        return f"ori immediate 0x{value & 0xFFFF:04X}"
    if op in {0x23, 0x2B, 0x31, 0x39}:
        return f"memory op rt={rt} offset {imm}"
    return "other"


def disasm_window(md, data, offset, radius=12):
    start = max(0, offset - radius)
    start -= start % 4
    size = radius * 2 + 4
    out = []
    for insn in md.disasm(data[start : start + size], 0x7F000000 + start):
        rom_off = insn.address - 0x7F000000
        out.append(
            {
                "offset": f"0x{rom_off:X}",
                "target": rom_off == offset,
                "mnemonic": insn.mnemonic,
                "operands": insn.op_str,
            }
        )
    return out


def candidate_patches(report):
    for candidate in report["candidates"]:
        for patch in candidate["patches"]:
            yield candidate["name"], patch


def main():
    data = ROM.read_bytes()
    report = json.loads(MENU_REPORT.read_text(encoding="utf-8"))
    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_BIG_ENDIAN)
    by_key = {}
    for candidate_name, patch in candidate_patches(report):
        function = patch.get("function") or "unclassified"
        offset = int(patch["offset"], 16)
        old = int(patch["old"], 16)
        new = int(patch["new"], 16)
        key = (function, offset, new)
        item = by_key.setdefault(
            key,
            {
                "candidates": [],
                "offset": patch["offset"],
                "rom_word_now": f"0x{word(data, offset):08X}",
                "old": patch["old"],
                "new": patch["new"],
                "old_kind": classify_instruction(old),
                "new_kind": classify_instruction(new),
                "delta_low16_signed": signed16(new) - signed16(old),
                "context": disasm_window(md, data, offset),
            }
        )
        item["candidates"].append(candidate_name)

    by_function = {}
    for (function, _offset, _new), item in sorted(by_key.items(), key=lambda entry: entry[0]):
        by_function.setdefault(function, []).append(item)

    audit = {
        "rom": str(ROM),
        "menu_report": str(MENU_REPORT),
        "summary": (
            "Raw GE menu-function constants mix visual layout with cursor/tween/control "
            "state. Future menu candidates should patch only source-classified draw "
            "coordinates after validating the corresponding TND menu path."
        ),
        "source_hints": SOURCE_HINTS,
        "functions": by_function,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: len(v) for k, v in by_function.items()}, indent=2))


if __name__ == "__main__":
    main()
