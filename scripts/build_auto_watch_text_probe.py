#!/usr/bin/env python3
import argparse
import hashlib
import json
import shutil
import struct
from pathlib import Path

from build_tnd480i_candidate import update_n64_crc_6102


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "artifacts" / "generated" / "text_probe"
DEFAULT_REPORT = ROOT / "reports" / "measurement" / "auto_watch_text_probe_20260525.json"

BOOT_STAGE_PATCH = [
    (0x6C94, 0x3C018002, "lui at, 0x8002"),
    (0x6C98, None, "addiu v0, zero, <stage>"),
    (0x6C9C, 0xAC2241A8, "sw v0, g_StageNum"),
    (0x6CA0, 0x1000000E, "b after -level_ token parser"),
    (0x6CA4, 0x00000000, "nop"),
]

# Hook bondviewProcessInput after the stack frame and saved RA are established.
# This is less dependent on the real controller edge-detection path than the
# branch near trigger_solo_watch_menu, and can safely call another function
# because the original RA is already on the stack.
AUTO_WATCH_HOOK_OFFSET = 0x0B64C8
AUTO_WATCH_HOOK_EXPECTED_OLD = 0xAFA001BC
AUTO_WATCH_HOOK_DELAY_OFFSET = 0x0B64CC
AUTO_WATCH_HOOK_DELAY_WORD = 0xAFA001B8
AUTO_WATCH_RESUME_OFFSET = 0x0B64D0
MAIN_VADDR_BASE = 0x7EFCB4D0
TRIGGER_SOLO_WATCH_MENU_OFFSET = 0x0B43A4
AUTO_WATCH_DELAY_FRAMES = 600
AUTO_WATCH_STUB_WORDS = 20
AUTO_WATCH_FLAG_PAD_BYTES = 0x80
AUTO_WATCH_MIN_CAVE_BYTES = AUTO_WATCH_FLAG_PAD_BYTES + 4

LEVELS = {
    "dam": 33,
    "bazaar": 33,
    "facility": 34,
    "party": 34,
    "runway": 35,
    "labs": 35,
    "frigate": 26,
    "wreck": 26,
}


def md5_bytes(data):
    return hashlib.md5(data).hexdigest()


def read_word(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def write_word(data, offset, value):
    struct.pack_into(">I", data, offset, value)


def runtime(offset):
    return MAIN_VADDR_BASE + offset


def lui(rt, imm):
    return 0x3C000000 | (rt << 16) | (imm & 0xFFFF)


def ori(rt, rs, imm):
    return 0x34000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def addiu(rt, rs, imm):
    return 0x24000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def lw(rt, offset, base):
    return 0x8C000000 | (base << 21) | (rt << 16) | (offset & 0xFFFF)


def sw(rt, offset, base):
    return 0xAC000000 | (base << 21) | (rt << 16) | (offset & 0xFFFF)


def bnez(rs, offset):
    return 0x14000000 | (rs << 21) | (offset & 0xFFFF)


def beq(rs, rt, offset):
    return 0x10000000 | (rs << 21) | (rt << 16) | (offset & 0xFFFF)


def j(addr):
    return 0x08000000 | ((addr >> 2) & 0x03FFFFFF)


def jal(addr):
    return 0x0C000000 | ((addr >> 2) & 0x03FFFFFF)


def nop():
    return 0


def write_words(data, offset, words):
    for index, value in enumerate(words):
        write_word(data, offset + index * 4, value)


def high_nibble(addr):
    return (addr >> 28) & 0xF


def find_executable_cave(rom, min_size=AUTO_WATCH_MIN_CAVE_BYTES):
    required_region = high_nibble(runtime(AUTO_WATCH_HOOK_OFFSET))
    start = max(0, 0x7F000000 - MAIN_VADDR_BASE)
    run_start = None
    run_len = 0

    for index in range(start, len(rom)):
        if rom[index] == 0:
            if run_start is None:
                run_start = index
            run_len += 1
            if run_len >= min_size and run_start % 4 == 0:
                cave_addr = runtime(run_start)
                if high_nibble(cave_addr) == required_region:
                    return run_start, run_len
        else:
            run_start = None
            run_len = 0

    raise ValueError(f"could not find a {min_size}-byte zero cave in the 0x7F jump region")


def build_auto_watch_stub(rom, cave_offset, delay_frames):
    if any(rom[cave_offset:cave_offset + AUTO_WATCH_MIN_CAVE_BYTES]):
        raise ValueError(f"auto-watch cave is not empty at 0x{cave_offset:X}")
    flag_offset = cave_offset + AUTO_WATCH_FLAG_PAD_BYTES
    flag_addr = runtime(flag_offset)
    # Registers: t8=24 counter/flag, t9=25 flag pointer, t0=8 temp.
    trigger_index = 14
    words = [
        AUTO_WATCH_HOOK_EXPECTED_OLD,
        lui(25, flag_addr >> 16),
        ori(25, 25, flag_addr & 0xFFFF),
        lw(24, 0, 25),
        addiu(8, 0, -1),
        beq(24, 8, 6),
        nop(),
        addiu(8, 0, delay_frames),
        beq(24, 8, trigger_index - 9),
        nop(),
        addiu(24, 24, 1),
        sw(24, 0, 25),
        j(runtime(AUTO_WATCH_RESUME_OFFSET)),
        nop(),
        addiu(24, 0, -1),
        sw(24, 0, 25),
        jal(runtime(TRIGGER_SOLO_WATCH_MENU_OFFSET)),
        0x00002025,  # move a0, zero
        j(runtime(AUTO_WATCH_RESUME_OFFSET)),
        nop(),
    ]
    if len(words) != AUTO_WATCH_STUB_WORDS:
        raise AssertionError(f"auto-watch stub length changed: {len(words)} words")
    write_words(rom, cave_offset, words)
    return {
        "cave_offset": f"0x{cave_offset:06X}",
        "cave_vaddr": f"0x{runtime(cave_offset):08X}",
        "flag_offset": f"0x{flag_offset:06X}",
        "flag_vaddr": f"0x{flag_addr:08X}",
        "delay_frames": delay_frames,
        "hook_offset": f"0x{AUTO_WATCH_HOOK_OFFSET:06X}",
        "resume_offset": f"0x{AUTO_WATCH_RESUME_OFFSET:06X}",
        "trigger_solo_watch_menu_offset": f"0x{TRIGGER_SOLO_WATCH_MENU_OFFSET:06X}",
        "words": [f"0x{word:08X}" for word in words],
    }


def copy_save(save_path, out_rom):
    outputs = []
    if not save_path:
        return outputs
    save_path = Path(save_path)
    if not save_path.exists():
        return [{"source": str(save_path), "missing": True}]
    raw = save_path.read_bytes()
    for suffix in (".sav", ".eep"):
        target = out_rom.with_suffix(suffix)
        if suffix == ".eep" and len(raw) < 2048:
            payload = raw + b"\0" * (2048 - len(raw))
        else:
            payload = raw
        target.write_bytes(payload)
        outputs.append({"target": str(target), "bytes": len(payload), "md5": md5_bytes(payload)})
    return outputs


def build_one(label, base_rom, save_path, stage_id, delay_frames, out_dir):
    rom = bytearray(Path(base_rom).read_bytes())
    patches = []

    for offset, value, note in BOOT_STAGE_PATCH:
        new_value = value if value is not None else 0x24020000 | stage_id
        old_value = read_word(rom, offset)
        write_word(rom, offset, new_value)
        patches.append({
            "offset": f"0x{offset:06X}",
            "old": f"0x{old_value:08X}",
            "new": f"0x{new_value:08X}",
            "note": note,
        })

    old_branch = read_word(rom, AUTO_WATCH_HOOK_OFFSET)
    if old_branch != AUTO_WATCH_HOOK_EXPECTED_OLD:
        raise ValueError(
            f"{label}: expected hook word 0x{AUTO_WATCH_HOOK_EXPECTED_OLD:08X} "
            f"at 0x{AUTO_WATCH_HOOK_OFFSET:X}, found 0x{old_branch:08X}"
        )
    old_delay = read_word(rom, AUTO_WATCH_HOOK_DELAY_OFFSET)
    if old_delay != AUTO_WATCH_HOOK_DELAY_WORD:
        raise ValueError(
            f"{label}: expected hook delay 0x{AUTO_WATCH_HOOK_DELAY_WORD:08X} "
            f"at 0x{AUTO_WATCH_HOOK_DELAY_OFFSET:X}, found 0x{old_delay:08X}"
        )
    cave_offset, cave_len = find_executable_cave(rom)
    stub = build_auto_watch_stub(rom, cave_offset, delay_frames)
    stub["zero_run_bytes"] = cave_len
    write_word(rom, AUTO_WATCH_HOOK_OFFSET, j(runtime(cave_offset)))
    write_word(rom, AUTO_WATCH_HOOK_DELAY_OFFSET, AUTO_WATCH_HOOK_DELAY_WORD)
    patches.append({
        "offset": f"0x{AUTO_WATCH_HOOK_OFFSET:06X}",
        "old": f"0x{old_branch:08X}",
        "new": f"0x{read_word(rom, AUTO_WATCH_HOOK_OFFSET):08X}",
        "note": "jump from bondviewProcessInput prologue to one-shot auto-watch trampoline",
    })

    crc1, crc2 = update_n64_crc_6102(rom)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_rom = out_dir / f"{label}.z64"
    out_rom.write_bytes(rom)
    return {
        "label": label,
        "base_rom": str(base_rom),
        "base_md5": md5_bytes(Path(base_rom).read_bytes()),
        "out_rom": str(out_rom),
        "out_md5": md5_bytes(rom),
        "stage_id": stage_id,
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": patches,
        "auto_watch_stub": stub,
        "save_outputs": copy_save(save_path, out_rom),
    }


def parse_sample(raw):
    parts = raw.split("=", 1)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("sample must be LABEL=ROM")
    return parts[0], Path(parts[1])


def main():
    parser = argparse.ArgumentParser(description="Build direct-stage auto-watch ROMs for hardware text-quality captures.")
    parser.add_argument("--sample", action="append", type=parse_sample, required=True, help="LABEL=ROM; repeat for GE/TND")
    parser.add_argument("--save", action="append", default=[], help="Optional LABEL=SAVE pairing")
    parser.add_argument("--stage", default="dam", help="Stage key or integer stage id; dam/bazaar default to 33")
    parser.add_argument("--delay-frames", type=int, default=AUTO_WATCH_DELAY_FRAMES, help="bondviewProcessInput frame to trigger the watch")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    save_map = {}
    for item in args.save:
        label, path = parse_sample(item)
        save_map[label] = path

    stage_id = LEVELS.get(str(args.stage).lower(), None)
    if stage_id is None:
        stage_id = int(args.stage, 0)

    outputs = [
        build_one(label, rom, save_map.get(label), stage_id, args.delay_frames, args.out_dir)
        for label, rom in args.sample
    ]
    report = {
        "purpose": (
            "No-controller hardware diagnostic: direct-boot a stage and auto-open "
            "the watch once so GE480i and TND6480i pause text can be captured and "
            "measured on the same GV-USB2 path."
        ),
        "stage_id": stage_id,
        "delay_frames": args.delay_frames,
        "outputs": outputs,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
