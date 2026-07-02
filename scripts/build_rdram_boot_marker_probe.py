#!/usr/bin/env python3
"""Build a direct-stage boot marker probe visible in raw RDRAM dumps."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from build_tnd480i_candidate import update_n64_crc_6102


MAIN_VADDR_BASE = 0x7EFCB4D0
BOOT_HOOK_OFF = 0x006C94
BOOT_HOOK_EXPECTED = 0x3C018002
BOOT_CONTINUE_OFF = 0x006CDC
RING_TOTAL_SIZE = 0x100
MIN_CAVE_SIZE = 0x200 + RING_TOTAL_SIZE


def word(value: int) -> bytes:
    return value.to_bytes(4, "big")


def ascii_word(text: str) -> int:
    raw = text.encode("ascii")
    if len(raw) != 4:
        raise ValueError("marker must be four ASCII bytes")
    return int.from_bytes(raw, "big")


def read_word(rom: bytes | bytearray, off: int) -> int:
    return int.from_bytes(rom[off : off + 4], "big")


def write_word(rom: bytearray, off: int, value: int) -> None:
    rom[off : off + 4] = word(value)


def write_words(rom: bytearray, off: int, words: list[int]) -> None:
    for index, value in enumerate(words):
        write_word(rom, off + index * 4, value)


def runtime(rom_off: int) -> int:
    return MAIN_VADDR_BASE + rom_off


def kseg1_for_loaded_rom_offset(rom_off: int) -> int:
    return 0xA0000000 + rom_off - 0xC00


def lui(rt: int, imm: int) -> int:
    return 0x3C000000 | (rt << 16) | (imm & 0xFFFF)


def ori(rt: int, rs: int, imm: int) -> int:
    return 0x34000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def addiu(rt: int, rs: int, imm: int) -> int:
    return 0x24000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def sw(rt: int, offset: int, base: int) -> int:
    return 0xAC000000 | (base << 21) | (rt << 16) | (offset & 0xFFFF)


def j(addr: int) -> int:
    return 0x08000000 | ((addr >> 2) & 0x03FFFFFF)


def nop() -> int:
    return 0


def load_imm(reg: int, value: int) -> list[int]:
    return [lui(reg, value >> 16), ori(reg, reg, value & 0xFFFF)]


def find_executable_zero_cave(rom: bytes, min_size: int) -> tuple[int, int]:
    required_nibble = (runtime(BOOT_HOOK_OFF) >> 28) & 0xF
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
            if aligned_len >= min_size and ((runtime(aligned_start) >> 28) & 0xF) == required_nibble:
                return aligned_start, aligned_len
        else:
            run_start = None
            run_len = 0
    raise ValueError(f"could not find 0x{min_size:X}-byte executable cave")


def build(args: argparse.Namespace) -> None:
    base = Path(args.base_rom)
    rom = bytearray(base.read_bytes())
    old = read_word(rom, BOOT_HOOK_OFF)
    if old != BOOT_HOOK_EXPECTED:
        raise ValueError(f"expected 0x{BOOT_HOOK_EXPECTED:08X} at 0x{BOOT_HOOK_OFF:X}, got 0x{old:08X}")

    cave_off, cave_len = find_executable_zero_cave(rom, MIN_CAVE_SIZE)
    ring_off = cave_off + 0x200
    ring_addr = kseg1_for_loaded_rom_offset(ring_off)
    if any(rom[cave_off : cave_off + MIN_CAVE_SIZE]):
        raise ValueError(f"selected cave was not empty at 0x{cave_off:X}")

    # t0 = uncached ring, t1 = marker scratch.  Replay the direct-stage boot
    # patch and jump to the original branch target at 0x6CDC.
    stub: list[int] = []
    stub.extend(load_imm(8, ring_addr))
    stub.extend(load_imm(9, ascii_word("TBMK")))
    stub.append(sw(9, 0x00, 8))
    stub.extend(load_imm(9, ascii_word("BOOT")))
    stub.append(sw(9, 0x04, 8))
    stub.append(lui(1, 0x8002))
    stub.append(addiu(2, 0, args.stage))
    stub.append(sw(2, 0x41A8, 1))
    stub.append(j(runtime(BOOT_CONTINUE_OFF)))
    stub.append(nop())
    write_words(rom, cave_off, stub)
    write_words(rom, BOOT_HOOK_OFF, [j(runtime(cave_off)), nop()])

    crc1, crc2 = update_n64_crc_6102(rom)
    out = Path(args.out_rom)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(rom)
    report = {
        "base_rom": str(base),
        "base_md5": hashlib.md5(base.read_bytes()).hexdigest(),
        "out_rom": str(out),
        "out_md5": hashlib.md5(rom).hexdigest(),
        "n64_crc": [f"0x{crc1:08X}", f"0x{crc2:08X}"],
        "stage": args.stage,
        "hook_offset": f"0x{BOOT_HOOK_OFF:06X}",
        "continue_offset": f"0x{BOOT_CONTINUE_OFF:06X}",
        "cave_offset": f"0x{cave_off:06X}",
        "cave_runtime": f"0x{runtime(cave_off):08X}",
        "zero_run_bytes": cave_len,
        "ring_offset": f"0x{ring_off:06X}",
        "ring_kseg1": f"0x{ring_addr:08X}",
        "ring_rdram_offset": f"0x{ring_addr - 0xA0000000:06X}",
        "stub_words": [f"0x{item:08X}" for item in stub],
    }
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a RDRAM-visible direct-stage boot marker probe.")
    parser.add_argument("--base-rom", required=True)
    parser.add_argument("--out-rom", required=True)
    parser.add_argument("--report")
    parser.add_argument("--stage", type=lambda value: int(value, 0), default=33)
    build(parser.parse_args())


if __name__ == "__main__":
    main()
