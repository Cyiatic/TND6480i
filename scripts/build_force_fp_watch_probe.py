#!/usr/bin/env python3
"""Build no-controller direct-stage watch probes for hardware text captures.

The earlier auto-watch probe hooked bondviewProcessInput, which only runs once
the direct-stage route has reached the normal player-input path. Some direct
stage probes can sit in the intro/cinema camera path indefinitely with no
controller attached, so this probe hooks bondviewFrozenMoveBond instead. That
function runs during camera/frozen movement, after the player state exists.
"""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from build_tnd480i_candidate import update_n64_crc_6102


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "artifacts" / "generated" / "force_fp_watch_probe"
DEFAULT_REPORT = ROOT / "reports" / "measurement" / "force_fp_watch_probe_20260525.json"

MAIN_VADDR_BASE = 0x7EFCB4D0

BOOT_STAGE_PATCH = [
    (0x6C94, 0x3C018002, "lui at, 0x8002"),
    (0x6C98, None, "addiu v0, zero, <stage>"),
    (0x6C9C, 0xAC2241A8, "sw v0, g_StageNum"),
    (0x6CA0, 0x1000000E, "b after -level_ token parser"),
    (0x6CA4, 0x00000000, "nop"),
]

# Hook just before bondviewFrozenMoveBond calls bondviewProcessInput(0,0,0,0).
# At this point the function stack frame exists, RA is saved, and the original
# a0-a3 arguments have already been stored to the stack.
FROZEN_WATCH_HOOK_OFFSET = 0x0BB574
FROZEN_WATCH_HOOK_EXPECTED = (0x00002025, 0x00002825)  # move a0,zero; move a1,zero
FROZEN_WATCH_RESUME_OFFSET = 0x0BB57C

BONDVIEW_SET_CAMERA_MODE_OFFSET = 0x0AF4E8
TRIGGER_SOLO_WATCH_MENU_OFFSET = 0x0B43A4
CAMERAMODE_FP = 4

STUB_MIN_BYTES = 0x180
FLAG_PAD_BYTES = 0x100

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


R_ZERO = 0
R_A0 = 4
R_A1 = 5
R_T0 = 8
R_T1 = 9
R_T2 = 10


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


def j(addr):
    return 0x08000000 | ((addr >> 2) & 0x03FFFFFF)


def jal(addr):
    return 0x0C000000 | ((addr >> 2) & 0x03FFFFFF)


def nop():
    return 0


def move(rd, rs):
    return (rs << 21) | (R_ZERO << 16) | (rd << 11) | 0x25


def beq(rs, rt, offset):
    return 0x10000000 | (rs << 21) | (rt << 16) | (offset & 0xFFFF)


def bne(rs, rt, offset):
    return 0x14000000 | (rs << 21) | (rt << 16) | (offset & 0xFFFF)


class Asm:
    def __init__(self):
        self.words = []
        self.labels = {}
        self.branches = []

    def emit(self, word):
        self.words.append(word)

    def label(self, name):
        if name in self.labels:
            raise ValueError(f"duplicate label: {name}")
        self.labels[name] = len(self.words)

    def beq(self, rs, rt, label):
        self.branches.append((len(self.words), "beq", rs, rt, label))
        self.words.append(0)

    def bne(self, rs, rt, label):
        self.branches.append((len(self.words), "bne", rs, rt, label))
        self.words.append(0)

    def resolve(self):
        for index, kind, rs, rt, label in self.branches:
            if label not in self.labels:
                raise ValueError(f"unknown branch label: {label}")
            offset = self.labels[label] - (index + 1)
            if offset < -0x8000 or offset > 0x7FFF:
                raise ValueError(f"branch to {label} out of range: {offset}")
            self.words[index] = beq(rs, rt, offset) if kind == "beq" else bne(rs, rt, offset)
        return self.words


def write_words(data, offset, words):
    for index, value in enumerate(words):
        write_word(data, offset + index * 4, value)


def high_nibble(addr):
    return (addr >> 28) & 0xF


def find_executable_cave(rom, min_size):
    required_region = high_nibble(runtime(FROZEN_WATCH_HOOK_OFFSET))
    start = max(0, 0x7F000000 - MAIN_VADDR_BASE)
    run_start = None
    run_len = 0

    for index in range(start, len(rom)):
        if rom[index] == 0:
            if run_start is None:
                run_start = index
            run_len += 1
            aligned_start = (run_start + 3) & ~3
            aligned_len = index - aligned_start + 1
            if aligned_len >= min_size and high_nibble(runtime(aligned_start)) == required_region:
                return aligned_start, aligned_len
        else:
            run_start = None
            run_len = 0

    raise ValueError(f"could not find a {min_size}-byte zero cave in the 0x7F jump region")


def build_force_fp_watch_stub(force_frame, watch_frame, cave_offset):
    flag_offset = cave_offset + FLAG_PAD_BYTES
    flag_addr = runtime(flag_offset)

    asm = Asm()
    asm.emit(lui(R_T1, flag_addr >> 16))
    asm.emit(ori(R_T1, R_T1, flag_addr & 0xFFFF))
    asm.emit(lw(R_T0, 0, R_T1))
    asm.emit(addiu(R_T2, R_ZERO, -1))
    asm.beq(R_T0, R_T2, "done")
    asm.emit(nop())
    asm.emit(addiu(R_T0, R_T0, 1))
    asm.emit(sw(R_T0, 0, R_T1))
    asm.emit(addiu(R_T2, R_ZERO, force_frame))
    asm.bne(R_T0, R_T2, "check_watch")
    asm.emit(nop())
    asm.emit(addiu(R_A0, R_ZERO, CAMERAMODE_FP))
    asm.emit(jal(runtime(BONDVIEW_SET_CAMERA_MODE_OFFSET)))
    asm.emit(nop())
    asm.beq(R_ZERO, R_ZERO, "done")
    asm.emit(nop())

    asm.label("check_watch")
    if watch_frame > 0:
        asm.emit(addiu(R_T2, R_ZERO, watch_frame))
        asm.bne(R_T0, R_T2, "done")
        asm.emit(nop())
        asm.emit(addiu(R_T0, R_ZERO, -1))
        asm.emit(sw(R_T0, 0, R_T1))
        asm.emit(jal(runtime(TRIGGER_SOLO_WATCH_MENU_OFFSET)))
        asm.emit(move(R_A0, R_ZERO))

    asm.label("done")
    asm.emit(move(R_A0, R_ZERO))
    asm.emit(move(R_A1, R_ZERO))
    asm.emit(j(runtime(FROZEN_WATCH_RESUME_OFFSET)))
    asm.emit(nop())

    words = asm.resolve()
    return words, {
        "cave_offset": f"0x{cave_offset:06X}",
        "cave_vaddr": f"0x{runtime(cave_offset):08X}",
        "flag_offset": f"0x{flag_offset:06X}",
        "flag_vaddr": f"0x{flag_addr:08X}",
        "force_frame": force_frame,
        "watch_frame": watch_frame,
        "hook_offset": f"0x{FROZEN_WATCH_HOOK_OFFSET:06X}",
        "resume_offset": f"0x{FROZEN_WATCH_RESUME_OFFSET:06X}",
        "bondview_set_camera_mode_offset": f"0x{BONDVIEW_SET_CAMERA_MODE_OFFSET:06X}",
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


def patch_boot_stage(rom, stage_id):
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
    return patches


def build_one(label, base_rom, save_path, stage_id, force_frame, watch_frame, out_dir):
    base_path = Path(base_rom)
    base_bytes = base_path.read_bytes()
    rom = bytearray(base_bytes)
    patches = patch_boot_stage(rom, stage_id)

    old0 = read_word(rom, FROZEN_WATCH_HOOK_OFFSET)
    old1 = read_word(rom, FROZEN_WATCH_HOOK_OFFSET + 4)
    if (old0, old1) != FROZEN_WATCH_HOOK_EXPECTED:
        raise ValueError(
            f"{label}: expected hook words "
            f"{' '.join(f'0x{x:08X}' for x in FROZEN_WATCH_HOOK_EXPECTED)} at "
            f"0x{FROZEN_WATCH_HOOK_OFFSET:X}, found 0x{old0:08X} 0x{old1:08X}"
        )

    cave_offset, cave_len = find_executable_cave(rom, STUB_MIN_BYTES)
    if any(rom[cave_offset:cave_offset + STUB_MIN_BYTES]):
        raise ValueError(f"force-FP/watch cave is not empty at 0x{cave_offset:X}")
    words, stub = build_force_fp_watch_stub(force_frame, watch_frame, cave_offset)
    write_words(rom, cave_offset, words)
    write_word(rom, FROZEN_WATCH_HOOK_OFFSET, j(runtime(cave_offset)))
    write_word(rom, FROZEN_WATCH_HOOK_OFFSET + 4, nop())
    stub["zero_run_bytes"] = cave_len
    patches.append({
        "offset": f"0x{FROZEN_WATCH_HOOK_OFFSET:06X}",
        "old": f"0x{old0:08X} 0x{old1:08X}",
        "new": f"0x{read_word(rom, FROZEN_WATCH_HOOK_OFFSET):08X} 0x{read_word(rom, FROZEN_WATCH_HOOK_OFFSET + 4):08X}",
        "note": "jump from bondviewFrozenMoveBond pre-input path to force-FP/watch trampoline",
    })

    crc1, crc2 = update_n64_crc_6102(rom)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_rom = out_dir / f"{label}.z64"
    out_rom.write_bytes(rom)
    return {
        "label": label,
        "base_rom": str(base_path),
        "base_md5": md5_bytes(base_bytes),
        "out_rom": str(out_rom),
        "out_md5": md5_bytes(rom),
        "stage_id": stage_id,
        "header_crc": f"{crc1:08X} {crc2:08X}",
        "patches": patches,
        "force_fp_watch_stub": stub,
        "save_outputs": copy_save(save_path, out_rom),
    }


def parse_sample(raw):
    parts = raw.split("=", 1)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("sample must be LABEL=ROM")
    return parts[0], Path(parts[1])


def main():
    parser = argparse.ArgumentParser(description="Build direct-stage force-FP/watch ROMs for hardware text captures.")
    parser.add_argument("--sample", action="append", type=parse_sample, required=True, help="LABEL=ROM; repeat for GE/TND")
    parser.add_argument("--save", action="append", default=[], help="Optional LABEL=SAVE pairing")
    parser.add_argument("--stage", default="wreck", help="Stage key or integer stage id; wreck/frigate default to 26")
    parser.add_argument("--force-frame", type=int, default=180, help="FrozenMoveBond frame to force first-person mode")
    parser.add_argument("--watch-frame", type=int, default=240, help="FrozenMoveBond frame to open the watch after first-person mode settles; use 0 to leave gameplay/HUD visible")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    save_map = {}
    for item in args.save:
        label, path = parse_sample(item)
        save_map[label] = path

    stage_id = LEVELS.get(str(args.stage).lower())
    if stage_id is None:
        stage_id = int(args.stage, 0)

    outputs = [
        build_one(label, rom, save_map.get(label), stage_id, args.force_frame, args.watch_frame, args.out_dir)
        for label, rom in args.sample
    ]
    report = {
        "purpose": (
            "No-controller hardware diagnostic: direct-boot a stage, force "
            "CAMERAMODE_FP from the frozen/cinema player path, then open the "
            "watch so GE480i and TND6480i text can be captured through GV-USB2."
        ),
        "stage_id": stage_id,
        "force_frame": args.force_frame,
        "watch_frame": args.watch_frame,
        "outputs": outputs,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
