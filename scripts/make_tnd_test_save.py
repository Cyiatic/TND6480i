#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


MASK64 = (1 << 64) - 1
SAVE_SIZE = 0x60
SMALL_SAVE_SIZE = 0x20
SAVE_SLOTS = 5
SAVE_BASE = 0x20
TIMES_OFFSET = 0x12
CHEAT_UNLOCK_OFFSET = 0x0E
CHEAT_UNLOCK_SIZE = 3
EEPROM_SIZE = 512


def random_get_next_from(seed):
    seed &= MASK64
    mixed = (((seed << 63) & MASK64) >> 31) | (((seed << 31) & MASK64) >> 32)
    mixed ^= ((seed << 44) & MASK64) >> 32
    seed = (((mixed >> 20) & 0xFFF) ^ mixed) & MASK64
    return seed, seed & 0xFFFFFFFF


def generate_crc(data):
    seed = 0x8F809F473108B3C1
    checksum1 = 0
    checksum2 = 0
    shift = 0

    for byte in data:
        seed = (seed + ((byte & 0xFF) << (shift & 0xF))) & MASK64
        seed, value = random_get_next_from(seed)
        checksum1 = (checksum1 ^ value) & 0xFFFFFFFF
        shift += 7

    for byte in reversed(data):
        seed = (seed + ((byte & 0xFF) << (shift & 0xF))) & MASK64
        seed, value = random_get_next_from(seed)
        checksum2 = (checksum2 ^ value) & 0xFFFFFFFF
        shift += 3

    return checksum1, checksum2


def write_crc(buf, offset, size):
    checksum1, checksum2 = generate_crc(buf[offset + 8 : offset + size])
    buf[offset : offset + 4] = checksum1.to_bytes(4, "big")
    buf[offset + 4 : offset + 8] = checksum2.to_bytes(4, "big")
    return checksum1, checksum2


def save_slot_offset(slot):
    return SAVE_BASE + slot * SAVE_SIZE


def slot_info(buf, slot):
    offset = save_slot_offset(slot)
    flags = buf[offset + 8]
    stored = (
        int.from_bytes(buf[offset : offset + 4], "big"),
        int.from_bytes(buf[offset + 4 : offset + 8], "big"),
    )
    calc = generate_crc(buf[offset + 8 : offset + SAVE_SIZE])
    return {
        "slot": slot,
        "offset": f"0x{offset:03X}",
        "flags": f"0x{flags:02X}",
        "folder": flags & 0x07,
        "wear_slot": (flags & 0x18) >> 3,
        "bond": (flags & 0x60) >> 5,
        "reset": bool(flags & 0x80),
        "stored_crc": [f"0x{stored[0]:08X}", f"0x{stored[1]:08X}"],
        "calculated_crc": [f"0x{calc[0]:08X}", f"0x{calc[1]:08X}"],
        "crc_ok": stored == calc,
        "cheat_bytes": [
            f"0x{byte:02X}"
            for byte in buf[
                offset + CHEAT_UNLOCK_OFFSET : offset + CHEAT_UNLOCK_OFFSET + CHEAT_UNLOCK_SIZE
            ]
        ],
        "nonzero_time_bytes": sum(1 for b in buf[offset + TIMES_OFFSET : offset + SAVE_SIZE] if b),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Create a TND/GoldenEye EEPROM test save with all mission time bits set."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(r"C:\Users\codex\Documents\007 - Tomorrow Never Dies (USA).sav"),
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--folders",
        default="0,1,2,3",
        help="Comma-separated folder numbers to mark complete. Default: 0,1,2,3.",
    )
    parser.add_argument(
        "--unlock-cheats",
        action="store_true",
        help="Set all persisted cheat unlock bits in every selected folder.",
    )
    args = parser.parse_args()

    data = bytearray(args.input.read_bytes())
    if len(data) < EEPROM_SIZE:
        data.extend(b"\x00" * (EEPROM_SIZE - len(data)))
    data = data[:EEPROM_SIZE]

    before = [slot_info(data, slot) for slot in range(SAVE_SLOTS)]
    folders = {int(part.strip()) for part in args.folders.split(",") if part.strip()}

    # The original game treats any nonzero packed mission time as a completed mission.
    # Fill the mission-time region for valid, non-reset folders only; leave the spare
    # wear-level slot alone so the game can continue to rotate saves normally.
    changed_slots = []
    for slot in range(SAVE_SLOTS):
        offset = save_slot_offset(slot)
        flags = data[offset + 8]
        folder = flags & 0x07
        if flags & 0x80 or folder not in folders:
            continue
        data[offset + TIMES_OFFSET : offset + SAVE_SIZE] = b"\xFF" * (SAVE_SIZE - TIMES_OFFSET)
        if args.unlock_cheats:
            data[
                offset + CHEAT_UNLOCK_OFFSET : offset + CHEAT_UNLOCK_OFFSET + CHEAT_UNLOCK_SIZE
            ] = b"\xFF" * CHEAT_UNLOCK_SIZE
        write_crc(data, offset, SAVE_SIZE)
        changed_slots.append(slot)

    write_crc(data, 0, SMALL_SAVE_SIZE)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)

    report = {
        "input": str(args.input),
        "input_md5": hashlib.md5(args.input.read_bytes()).hexdigest(),
        "output": str(args.output),
        "output_md5": hashlib.md5(data).hexdigest(),
        "changed_slots": changed_slots,
        "unlock_cheats": args.unlock_cheats,
        "before": before,
        "after": [slot_info(data, slot) for slot in range(SAVE_SLOTS)],
    }
    text = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
