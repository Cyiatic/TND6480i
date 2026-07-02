#!/usr/bin/env python3
import argparse
import glob
import json
from pathlib import Path


FIELDS = [
    ("marker", "ascii"),
    ("g_ViBackData", "hex"),
    ("video_settings_word0", "hex"),
    ("xy", "pair"),
    ("bufxy", "pair"),
    ("viewxy", "pair"),
    ("viewlefttop", "pair_signed"),
    ("framebuf", "hex"),
]


def u16(value):
    return value & 0xFFFF


def s16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def parse_one(path):
    data = Path(path).read_bytes()
    if len(data) < 0x20:
        raise ValueError(f"{path} is too short: {len(data)} bytes")
    words = [int.from_bytes(data[i:i + 4], "big") for i in range(0, 0x20, 4)]
    out = {"path": str(path), "raw_words": [f"0x{word:08X}" for word in words]}
    for (name, kind), value in zip(FIELDS, words):
        if kind == "ascii":
            out[name] = value.to_bytes(4, "big").decode("ascii", errors="replace")
        elif kind == "hex":
            out[name] = f"0x{value:08X}"
        elif kind == "pair":
            out[name] = {"hi": u16(value >> 16), "lo": u16(value)}
        elif kind == "pair_signed":
            out[name] = {"hi": s16(value >> 16), "lo": s16(value)}
        else:
            raise AssertionError(kind)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dumps", nargs="+")
    parser.add_argument("--out")
    args = parser.parse_args()
    dump_paths = []
    for pattern in args.dumps:
        matches = sorted(glob.glob(pattern))
        dump_paths.extend(matches if matches else [pattern])
    parsed = [parse_one(path) for path in dump_paths]
    text = json.dumps(parsed, indent=2) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
