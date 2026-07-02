#!/usr/bin/env python3
import argparse
import hashlib
import json
import zlib
from pathlib import Path


SOURCE_READ = 0
TARGET_READ = 1
FOOTER_SIZE = 12


def md5(data):
    return hashlib.md5(data).hexdigest()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def crc32(data):
    return zlib.crc32(data) & 0xFFFFFFFF


def encode_number(value):
    if value < 0:
        raise ValueError(f"BPS numbers cannot be negative: {value}")
    out = bytearray()
    while True:
        x = value & 0x7F
        value >>= 7
        if value == 0:
            out.append(0x80 | x)
            break
        out.append(x)
        value -= 1
    return bytes(out)


def decode_number(data, offset):
    value = 0
    shift = 1
    while True:
        x = data[offset]
        offset += 1
        value += (x & 0x7F) * shift
        if x & 0x80:
            return value, offset
        shift <<= 7
        value += shift


def encode_action(action, length):
    if length <= 0:
        raise ValueError("BPS command length must be positive")
    return encode_number(((length - 1) << 2) | action)


def append_source_read(out, length):
    out.extend(encode_action(SOURCE_READ, length))


def append_target_read(out, payload):
    out.extend(encode_action(TARGET_READ, len(payload)))
    out.extend(payload)


def same_run(source, target, offset):
    end = min(len(source), len(target))
    i = offset
    while i < end and source[i] == target[i]:
        i += 1
    return i - offset


def build_linear_bps(source, target, metadata=b"", min_same_run=8):
    patch = bytearray(b"BPS1")
    patch.extend(encode_number(len(source)))
    patch.extend(encode_number(len(target)))
    patch.extend(encode_number(len(metadata)))
    patch.extend(metadata)

    actions = []
    i = 0
    while i < len(target):
        run = same_run(source, target, i)
        if run:
            append_source_read(patch, run)
            actions.append({"type": "SourceRead", "offset": i, "length": run})
            i += run
            continue

        start = i
        i += 1
        while i < len(target):
            run = same_run(source, target, i)
            if run >= min_same_run:
                break
            i += max(1, run)
        payload = target[start:i]
        append_target_read(patch, payload)
        actions.append({"type": "TargetRead", "offset": start, "length": len(payload)})

    patch.extend(crc32(source).to_bytes(4, "little"))
    patch.extend(crc32(target).to_bytes(4, "little"))
    patch_crc = crc32(patch)
    patch.extend(patch_crc.to_bytes(4, "little"))
    return bytes(patch), actions


def apply_bps(source, patch):
    if not patch.startswith(b"BPS1"):
        raise ValueError("not a BPS patch")
    expected_patch_crc = int.from_bytes(patch[-4:], "little")
    actual_patch_crc = crc32(patch[:-4])
    if expected_patch_crc != actual_patch_crc:
        raise ValueError(f"patch CRC mismatch: {actual_patch_crc:08X} != {expected_patch_crc:08X}")

    offset = 4
    source_size, offset = decode_number(patch, offset)
    target_size, offset = decode_number(patch, offset)
    metadata_size, offset = decode_number(patch, offset)
    offset += metadata_size
    if len(source) != source_size:
        raise ValueError(f"source size mismatch: {len(source)} != {source_size}")
    source_crc = int.from_bytes(patch[-12:-8], "little")
    if crc32(source) != source_crc:
        raise ValueError("source CRC mismatch")

    target = bytearray()
    source_relative_offset = 0
    target_relative_offset = 0
    while offset < len(patch) - FOOTER_SIZE:
        data, offset = decode_number(patch, offset)
        action = data & 3
        length = (data >> 2) + 1
        if action == SOURCE_READ:
            start = len(target)
            target.extend(source[start:start + length])
        elif action == TARGET_READ:
            target.extend(patch[offset:offset + length])
            offset += length
        elif action == 2:
            data, offset = decode_number(patch, offset)
            delta = data >> 1
            source_relative_offset += -delta if data & 1 else delta
            target.extend(source[source_relative_offset:source_relative_offset + length])
            source_relative_offset += length
        elif action == 3:
            data, offset = decode_number(patch, offset)
            delta = data >> 1
            target_relative_offset += -delta if data & 1 else delta
            for _ in range(length):
                target.append(target[target_relative_offset])
                target_relative_offset += 1
        else:
            raise ValueError(f"unknown action {action}")

    if len(target) != target_size:
        raise ValueError(f"target size mismatch: {len(target)} != {target_size}")
    target_crc = int.from_bytes(patch[-8:-4], "little")
    if crc32(target) != target_crc:
        raise ValueError("target CRC mismatch")
    return bytes(target)


def main():
    parser = argparse.ArgumentParser(description="Create a BPS patch and verify it locally.")
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("out_patch", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--metadata", default="")
    args = parser.parse_args()

    source = args.source.read_bytes()
    target = args.target.read_bytes()
    metadata_obj = {
        "source": str(args.source),
        "target": str(args.target),
        "source_md5": md5(source),
        "target_md5": md5(target),
        "source_sha256": sha256(source),
        "target_sha256": sha256(target),
        "note": args.metadata,
    }
    metadata = json.dumps(metadata_obj, separators=(",", ":")).encode("utf-8")
    patch, actions = build_linear_bps(source, target, metadata)
    verified = apply_bps(source, patch) == target
    if not verified:
        raise SystemExit("BPS verification failed")

    args.out_patch.parent.mkdir(parents=True, exist_ok=True)
    args.out_patch.write_bytes(patch)
    manifest = {
        **metadata_obj,
        "patch": str(args.out_patch),
        "patch_bytes": len(patch),
        "patch_md5": md5(patch),
        "patch_sha256": sha256(patch),
        "source_bytes": len(source),
        "target_bytes": len(target),
        "source_crc32": f"{crc32(source):08X}",
        "target_crc32": f"{crc32(target):08X}",
        "patch_crc32": f"{crc32(patch[:-4]):08X}",
        "verified": verified,
        "action_count": len(actions),
        "source_read_bytes": sum(a["length"] for a in actions if a["type"] == "SourceRead"),
        "target_read_bytes": sum(a["length"] for a in actions if a["type"] == "TargetRead"),
        "actions_preview": actions[:20],
    }
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
