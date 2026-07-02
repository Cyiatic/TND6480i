#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


RECORD_BASE = 0x0100
RECORD_SIZE = 0x0080
RECORD_COUNT = 64
MARKERS = {b"TXTR": "textRender", b"TXTG": "textRenderGlow"}

FIELDS = [
    ("marker", 0x00),
    ("sequence", 0x04),
    ("ra", 0x08),
    ("sp", 0x0C),
    ("gdl", 0x10),
    ("x_ptr", 0x14),
    ("x", 0x18),
    ("y_ptr", 0x1C),
    ("y", 0x20),
    ("text_ptr", 0x24),
    ("text_first_word", 0x28),
    ("stack_arg4", 0x2C),
    ("stack_arg5", 0x30),
    ("stack_arg6", 0x34),
    ("stack_arg7", 0x38),
    ("stack_arg8", 0x3C),
    ("stack_arg9", 0x40),
    ("stack_arg10", 0x44),
    ("j_text_trigger", 0x48),
]


def u32(data, off):
    if off + 4 > len(data):
        return None
    return int.from_bytes(data[off:off + 4], "big")


def marker_text(data, off):
    raw = data[off:off + 4]
    try:
        return raw.decode("ascii")
    except UnicodeDecodeError:
        return raw.hex()


def maybe_ascii_word(value):
    raw = value.to_bytes(4, "big")
    if all(32 <= b < 127 for b in raw):
        return raw.decode("ascii")
    return None


def parse_dump(path):
    data = Path(path).read_bytes()
    header_marker = data[0:4].decode("ascii", errors="replace") if len(data) >= 4 else ""
    header_count = u32(data, 0x04)
    records = []
    for index in range(RECORD_COUNT):
        off = RECORD_BASE + index * RECORD_SIZE
        if off + RECORD_SIZE > len(data):
            break
        marker = data[off:off + 4]
        if marker not in MARKERS:
            continue
        record = {"ring_index": index, "function": MARKERS[marker]}
        for name, field_off in FIELDS:
            value = u32(data, off + field_off)
            if name == "marker":
                record[name] = marker_text(data, off + field_off)
            elif value is None:
                record[name] = None
            else:
                record[name] = value
                record[f"{name}_hex"] = f"0x{value:08X}"
        text_ascii = maybe_ascii_word(record["text_first_word"])
        if text_ascii:
            record["text_first_word_ascii"] = text_ascii
        records.append(record)
    records.sort(key=lambda item: item["sequence"])
    callsites = {}
    for record in records:
        key = f"{record['function']}@{record['ra_hex']}"
        callsites.setdefault(key, 0)
        callsites[key] += 1
    return {
        "dump": str(path),
        "bytes": len(data),
        "header": {
            "marker": header_marker,
            "count": header_count,
            "count_hex": f"0x{header_count:08X}" if header_count is not None else None,
        },
        "records_found": len(records),
        "callsites": dict(sorted(callsites.items())),
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description="Parse an SC64 textRender/textRenderGlow ring-buffer dump.")
    parser.add_argument("dump")
    parser.add_argument("--out-json")
    args = parser.parse_args()
    result = parse_dump(args.dump)
    if args.out_json:
        out = Path(args.out_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
