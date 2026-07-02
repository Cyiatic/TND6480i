#!/usr/bin/env python3
"""Parse TXLR text-call rings from a raw RDRAM dump."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


HEADER = b"TXLR"
RECORD_BASE = 0x100
RECORD_SIZE = 0x80
RECORD_COUNT = 32
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
    ("stack_arg11", 0x48),
]


def u32(data: bytes, off: int) -> int | None:
    if off + 4 > len(data):
        return None
    return int.from_bytes(data[off : off + 4], "big")


def maybe_ascii(value: int | None) -> str | None:
    if value is None:
        return None
    raw = value.to_bytes(4, "big")
    if all(32 <= b < 127 for b in raw):
        return raw.decode("ascii")
    return None


def parse_ring(data: bytes, header_off: int) -> dict:
    count = u32(data, header_off + 4)
    records = []
    for index in range(RECORD_COUNT):
        off = header_off + RECORD_BASE + index * RECORD_SIZE
        if off + RECORD_SIZE > len(data):
            break
        marker = data[off : off + 4]
        if marker not in MARKERS:
            continue
        record = {
            "ring_index": index,
            "function": MARKERS[marker],
        }
        for name, field_off in FIELDS:
            value = u32(data, off + field_off)
            if name == "marker":
                record[name] = marker.decode("ascii")
            else:
                record[name] = value
                record[f"{name}_hex"] = f"0x{value:08X}" if value is not None else None
        text_ascii = maybe_ascii(record.get("text_first_word"))
        if text_ascii:
            record["text_first_word_ascii"] = text_ascii
        records.append(record)
    records.sort(key=lambda item: item.get("sequence") if item.get("sequence") is not None else -1)
    callsites = {}
    view_bounds = {}
    for record in records:
        key = f"{record['function']}@{record['ra_hex']}"
        callsites[key] = callsites.get(key, 0) + 1
        vb = (record.get("stack_arg4"), record.get("stack_arg5"))
        view_bounds[str(vb)] = view_bounds.get(str(vb), 0) + 1
    return {
        "header_offset": f"0x{header_off:06X}",
        "count": count,
        "count_hex": f"0x{count:08X}" if count is not None else None,
        "records_found": len(records),
        "callsites": dict(sorted(callsites.items())),
        "view_bounds_top": sorted(view_bounds.items(), key=lambda item: item[1], reverse=True)[:20],
        "records": records,
    }


def parse_dump(path: Path) -> dict:
    data = path.read_bytes()
    rings = []
    start = 0
    while True:
        off = data.find(HEADER, start)
        if off < 0:
            break
        ring = parse_ring(data, off)
        if ring["records_found"]:
            rings.append(ring)
        start = off + 1
    return {
        "dump": str(path),
        "bytes": len(data),
        "ring_count": len(rings),
        "rings": rings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse RDRAM TXLR text-call ring buffers.")
    parser.add_argument("dump")
    parser.add_argument("--out-json")
    args = parser.parse_args()
    result = parse_dump(Path(args.dump))
    if args.out_json:
        out = Path(args.out_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "dump": result["dump"],
        "ring_count": result["ring_count"],
        "rings": [
            {
                "header_offset": ring["header_offset"],
                "count": ring["count"],
                "records_found": ring["records_found"],
                "callsites": ring["callsites"],
                "view_bounds_top": ring["view_bounds_top"],
            }
            for ring in result["rings"]
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
