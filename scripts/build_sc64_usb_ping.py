import argparse
import hashlib
import json
from pathlib import Path

from build_tnd480i_candidate import update_n64_crc_6102


R_ZERO = 0
R_T0 = 8
R_T1 = 9
R_T2 = 10
R_SP = 29
R_RA = 31

ROM_LOAD_OFFSET = 0x1000
RAM_LOAD_ADDRESS = 0x80000400

DIAG_CAVE_ROM_OFF = 0x3CB0
BCLR_RETURN_ROM_OFF = 0x3D4C
HVI_RETURN_ROM_OFF = 0x19AC4
LOW_CAVE_SIZE = 0x74

SC64_CMD_USB_WRITE = 0x4D
DATATYPE_TEXT = 0x01


def word(value):
    return value.to_bytes(4, "big")


def ascii_word(text):
    data = text.encode("ascii")
    if len(data) != 4:
        raise ValueError("marker must be exactly four ASCII bytes")
    return int.from_bytes(data, "big")


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


def jr(rs):
    return 0x00000008 | (rs << 21)


def nop():
    return 0


def runtime(rom_off):
    return RAM_LOAD_ADDRESS + (rom_off - ROM_LOAD_OFFSET)


def write_words(rom, off, words):
    for i, value in enumerate(words):
        rom[off + i * 4:off + i * 4 + 4] = word(value)


def ensure_low_cave(rom, words):
    size = len(words) * 4
    if size > LOW_CAVE_SIZE:
        raise ValueError(f"diagnostic stub is 0x{size:X}, low cave only has 0x{LOW_CAVE_SIZE:X}")
    if any(rom[DIAG_CAVE_ROM_OFF:DIAG_CAVE_ROM_OFF + size]):
        raise ValueError(f"diagnostic cave is not empty at 0x{DIAG_CAVE_ROM_OFF:X}")


def unlock_sc64_regs():
    return [
        lui(R_T0, 0xBFFF),
        sw(R_ZERO, 0x0010, R_T0),
        lui(R_T1, 0x5F55),
        ori(R_T1, R_T1, 0x4E4C),
        sw(R_T1, 0x0010, R_T0),
        lui(R_T1, 0x4F43),
        ori(R_T1, R_T1, 0x4B5F),
        sw(R_T1, 0x0010, R_T0),
    ]


def make_usb_ping():
    header = (DATATYPE_TEXT << 24) | 0x000004
    return [
        *unlock_sc64_regs(),
        lui(R_T2, 0xBFFE),
        lui(R_T1, ascii_word("PING") >> 16),
        ori(R_T1, R_T1, ascii_word("PING") & 0xFFFF),
        sw(R_T1, 0x0000, R_T2),
        lui(R_T1, 0x1FFE),
        sw(R_T1, 0x0004, R_T0),
        lui(R_T1, header >> 16),
        ori(R_T1, R_T1, header & 0xFFFF),
        sw(R_T1, 0x0008, R_T0),
        addiu(R_T1, R_ZERO, SC64_CMD_USB_WRITE),
        sw(R_T1, 0x0000, R_T0),
    ]


def apply_usb_ping(rom, hook):
    words = make_usb_ping()
    if hook == "hvi":
        words.extend([jr(R_RA), nop()])
        hook_offset = HVI_RETURN_ROM_OFF
        hook_words = [
            j(runtime(DIAG_CAVE_ROM_OFF)),
            addiu(R_SP, R_SP, 0x0048),
        ]
    elif hook == "bclr":
        words.extend([jr(R_RA), addiu(R_SP, R_SP, 0x0018)])
        hook_offset = BCLR_RETURN_ROM_OFF
        hook_words = [
            j(runtime(DIAG_CAVE_ROM_OFF)),
            lw(R_RA, 0x0014, R_SP),
        ]
    else:
        raise ValueError(f"unknown hook: {hook}")
    ensure_low_cave(rom, words)
    write_words(rom, DIAG_CAVE_ROM_OFF, words)
    write_words(rom, hook_offset, hook_words)
    return {
        "transport": "sc64 n64 usb_write",
        "hook": hook,
        "payload": "PING",
        "packet_id": "U",
        "datatype": f"0x{DATATYPE_TEXT:02X}",
        "data_buffer_pi_address": "0x1FFE0000",
        "cave_offset": f"0x{DIAG_CAVE_ROM_OFF:X}",
        "hook_offset": f"0x{hook_offset:X}",
        "runtime_cave": f"0x{runtime(DIAG_CAVE_ROM_OFF):08X}",
        "low_cave_bytes_used": f"0x{len(words) * 4:X}",
    }


def md5(data):
    return hashlib.md5(data).hexdigest()


def build(args):
    rom = bytearray(Path(args.base_rom).read_bytes())
    diagnostic = apply_usb_ping(rom, args.hook)
    crc1, crc2 = update_n64_crc_6102(rom)
    out_rom = Path(args.out_rom)
    out_rom.parent.mkdir(parents=True, exist_ok=True)
    out_rom.write_bytes(rom)
    summary = {
        "base_rom": args.base_rom,
        "out_rom": args.out_rom,
        "out_md5": md5(rom),
        "n64_crc": [f"0x{crc1:08X}", f"0x{crc2:08X}"],
        "diagnostic": diagnostic,
    }
    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", required=True)
    parser.add_argument("--out-rom", required=True)
    parser.add_argument("--report")
    parser.add_argument("--hook", choices=("hvi", "bclr"), default="bclr")
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
