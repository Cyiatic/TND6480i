#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


IPS_MAX_OFFSET = 0xFFFFFF
IPS_MAX_RECORD = 0xFFFF


def md5(data):
    return hashlib.md5(data).hexdigest()


def changed_ranges(base, target):
    if len(base) != len(target):
        raise ValueError(f"length mismatch: {len(base)} != {len(target)}")

    ranges = []
    i = 0
    while i < len(base):
        if base[i] == target[i]:
            i += 1
            continue
        start = i
        while i < len(base) and base[i] != target[i]:
            i += 1
        ranges.append((start, target[start:i]))
    return ranges


def write_ips(path, ranges):
    with path.open("wb") as f:
        f.write(b"PATCH")
        for start, data in ranges:
            pos = start
            while data:
                chunk, data = data[:IPS_MAX_RECORD], data[IPS_MAX_RECORD:]
                if pos > IPS_MAX_OFFSET:
                    raise ValueError(f"IPS offset out of range: 0x{pos:X}")
                f.write(pos.to_bytes(3, "big"))
                f.write(len(chunk).to_bytes(2, "big"))
                f.write(chunk)
                pos += len(chunk)
        f.write(b"EOF")


def apply_ips(base, patch):
    if not patch.startswith(b"PATCH"):
        raise ValueError("missing IPS header")

    out = bytearray(base)
    i = 5
    while patch[i:i + 3] != b"EOF":
        offset = int.from_bytes(patch[i:i + 3], "big")
        size = int.from_bytes(patch[i + 3:i + 5], "big")
        i += 5
        if size == 0:
            rle_size = int.from_bytes(patch[i:i + 2], "big")
            value = patch[i + 2]
            i += 3
            out[offset:offset + rle_size] = bytes([value]) * rle_size
        else:
            out[offset:offset + size] = patch[i:i + size]
            i += size
    return bytes(out)


def main():
    parser = argparse.ArgumentParser(description="Create a simple IPS patch and JSON manifest.")
    parser.add_argument("base_rom")
    parser.add_argument("target_rom")
    parser.add_argument("out_patch")
    parser.add_argument("--manifest")
    args = parser.parse_args()

    base_path = Path(args.base_rom)
    target_path = Path(args.target_rom)
    out_path = Path(args.out_patch)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    base = base_path.read_bytes()
    target = target_path.read_bytes()
    ranges = changed_ranges(base, target)
    write_ips(out_path, ranges)
    patch = out_path.read_bytes()
    verified = apply_ips(base, patch) == target

    manifest = {
        "format": "IPS",
        "base_rom": str(base_path),
        "target_rom": str(target_path),
        "patch": str(out_path),
        "base_md5": md5(base),
        "target_md5": md5(target),
        "patch_md5": md5(patch),
        "verified": verified,
        "base_size": len(base),
        "target_size": len(target),
        "changed_bytes": sum(len(data) for _, data in ranges),
        "record_count": len(ranges),
        "changed_ranges": [
            {"offset": f"0x{start:X}", "length": len(data)}
            for start, data in ranges
        ],
    }

    if args.manifest:
        manifest_path = Path(args.manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
