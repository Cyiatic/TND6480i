#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


VCD_SOURCE = 0x01
VCD_TARGET = 0x02
VCD_ADLER32 = 0x04

XD3_NOOP = 0
XD3_ADD = 1
XD3_RUN = 2
XD3_CPY = 3


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def tell(self):
        return self.pos

    def read_u8(self):
        if self.pos >= len(self.data):
            raise EOFError("unexpected end of data")
        value = self.data[self.pos]
        self.pos += 1
        return value

    def read(self, size):
        if self.pos + size > len(self.data):
            raise EOFError("unexpected end of data")
        out = self.data[self.pos:self.pos + size]
        self.pos += size
        return out

    def read_varint(self):
        value = 0
        while True:
            b = self.read_u8()
            value = (value << 7) | (b & 0x7f)
            if not (b & 0x80):
                return value


class SliceReader(Reader):
    pass


class AddressCache:
    def __init__(self, near_modes=4, same_modes=3):
        self.near_modes = near_modes
        self.same_modes = same_modes
        self.near = [0] * near_modes
        self.same = [0] * (same_modes * 256)
        self.next_slot = 0

    def update(self, addr):
        if self.near_modes:
            self.near[self.next_slot] = addr
            self.next_slot = (self.next_slot + 1) % self.near_modes
        if self.same_modes:
            self.same[addr % (self.same_modes * 256)] = addr

    def decode(self, here, mode, addr_reader):
        same_start = 2 + self.near_modes
        if mode < same_start:
            value = addr_reader.read_varint()
            if mode == 0:
                addr = value
            elif mode == 1:
                addr = here - value
            else:
                addr = self.near[mode - 2] + value
        else:
            idx = addr_reader.read_u8()
            addr = self.same[(mode - same_start) * 256 + idx]
        self.update(addr)
        return addr


def build_code_table():
    add_sizes = 17
    near_modes = 4
    same_modes = 3
    cpy_sizes = 15
    addcopy_add_max = 4
    addcopy_near_cpy_max = 6
    addcopy_same_cpy_max = 4
    copyadd_add_max = 1
    copyadd_near_cpy_max = 4
    copyadd_same_cpy_max = 4
    min_match = 4
    cpy_modes = 2 + near_modes + same_modes

    table = []
    table.append((XD3_RUN, 0, 0, 0))
    table.append((XD3_ADD, 0, 0, 0))

    for size1 in range(1, add_sizes + 1):
        table.append((XD3_ADD, size1, 0, 0))

    for mode in range(cpy_modes):
        table.append((XD3_CPY + mode, 0, 0, 0))
        for size1 in range(min_match, min_match + cpy_sizes):
            table.append((XD3_CPY + mode, size1, 0, 0))

    for mode in range(cpy_modes):
        max_copy = addcopy_near_cpy_max if mode < 2 + near_modes else addcopy_same_cpy_max
        for size1 in range(1, addcopy_add_max + 1):
            for size2 in range(min_match, max_copy + 1):
                table.append((XD3_ADD, size1, XD3_CPY + mode, size2))

    for mode in range(cpy_modes):
        max_copy = copyadd_near_cpy_max if mode < 2 + near_modes else copyadd_same_cpy_max
        for size1 in range(min_match, max_copy + 1):
            for size2 in range(1, copyadd_add_max + 1):
                table.append((XD3_CPY + mode, size1, XD3_ADD, size2))

    if len(table) != 256:
        raise AssertionError(f"default VCDIFF table size is {len(table)}")
    return table


CODE_TABLE = build_code_table()


def parse_header(reader):
    magic = reader.read(4)
    if magic != b"\xd6\xc3\xc4\x00":
        raise ValueError(f"not a VCDIFF/xdelta stream: {magic.hex()}")
    hdr_indicator = reader.read_u8()
    secondary = None
    code_table = None
    app_header = b""
    if hdr_indicator & 0x01:
        secondary = reader.read_u8()
    if hdr_indicator & 0x02:
        size = reader.read_varint()
        code_table = reader.read(size)
        reader.read_u8()
        reader.read_u8()
    if hdr_indicator & 0x04:
        size = reader.read_varint()
        app_header = reader.read(size)
    return {
        "hdr_indicator": hdr_indicator,
        "secondary": secondary,
        "custom_code_table_len": 0 if code_table is None else len(code_table),
        "app_header": app_header.decode("latin1", errors="replace"),
        "header_size": reader.tell(),
    }


def decode_windows(patch_bytes, target_bytes=None):
    reader = Reader(patch_bytes)
    header = parse_header(reader)
    target_pos = 0
    windows = []
    source_copies = []
    target_writes = []

    while reader.tell() < len(patch_bytes):
        window_start = reader.tell()
        win_indicator = reader.read_u8()
        copy_len = 0
        copy_pos = 0
        if win_indicator & (VCD_SOURCE | VCD_TARGET):
            copy_len = reader.read_varint()
            copy_pos = reader.read_varint()
        delta_len = reader.read_varint()
        delta_start = reader.tell()
        target_len = reader.read_varint()
        delta_indicator = reader.read_u8()
        if delta_indicator:
            raise ValueError(f"compressed delta sections are not supported: {delta_indicator:#x}")
        data_len = reader.read_varint()
        inst_len = reader.read_varint()
        addr_len = reader.read_varint()
        checksum = None
        if win_indicator & VCD_ADLER32:
            checksum = int.from_bytes(reader.read(4), "big")
        data_sec = reader.read(data_len)
        inst_sec = reader.read(inst_len)
        addr_sec = reader.read(addr_len)
        expected_delta_end = delta_start + delta_len
        if reader.tell() != expected_delta_end:
            raise ValueError(
                f"delta length mismatch at patch offset {window_start:#x}: "
                f"reader {reader.tell():#x}, expected {expected_delta_end:#x}"
            )

        data_reader = SliceReader(data_sec)
        inst_reader = SliceReader(inst_sec)
        addr_reader = SliceReader(addr_sec)
        cache = AddressCache()
        out_pos = 0
        counts = {"RUN": 0, "ADD": 0, "COPY_SOURCE": 0, "COPY_TARGET": 0}

        while inst_reader.tell() < len(inst_sec):
            opcode = inst_reader.read_u8()
            entry = CODE_TABLE[opcode]
            halves = [(entry[0], entry[1]), (entry[2], entry[3])]
            for inst_type, size in halves:
                if inst_type == XD3_NOOP:
                    continue
                if size == 0:
                    size = inst_reader.read_varint()
                target_abs = target_pos + out_pos
                here = copy_len + out_pos
                if inst_type == XD3_RUN:
                    data_reader.read_u8()
                    target_writes.append({
                        "type": "RUN",
                        "target_start": target_abs,
                        "target_end": target_abs + size,
                    })
                    counts["RUN"] += 1
                elif inst_type == XD3_ADD:
                    data_reader.read(size)
                    target_writes.append({
                        "type": "ADD",
                        "target_start": target_abs,
                        "target_end": target_abs + size,
                    })
                    counts["ADD"] += 1
                elif inst_type >= XD3_CPY:
                    mode = inst_type - XD3_CPY
                    addr = cache.decode(here, mode, addr_reader)
                    if addr < copy_len:
                        source_abs = copy_pos + addr
                        source_copies.append({
                            "target_start": target_abs,
                            "target_end": target_abs + size,
                            "source_start": source_abs,
                            "source_end": source_abs + size,
                            "window_target_start": target_pos,
                        })
                        counts["COPY_SOURCE"] += 1
                    else:
                        target_src = target_pos + (addr - copy_len)
                        counts["COPY_TARGET"] += 1
                        target_writes.append({
                            "type": "COPY_TARGET",
                            "target_start": target_abs,
                            "target_end": target_abs + size,
                            "copy_from": target_src,
                        })
                else:
                    raise ValueError(f"unknown instruction type: {inst_type}")
                out_pos += size

        if out_pos != target_len:
            raise ValueError(f"target window length mismatch: {out_pos} != {target_len}")
        if data_reader.tell() != len(data_sec):
            raise ValueError("data section under-consumed")
        if addr_reader.tell() != len(addr_sec):
            raise ValueError("address section under-consumed")

        windows.append({
            "patch_offset": window_start,
            "win_indicator": win_indicator,
            "copy_len": copy_len,
            "copy_pos": copy_pos,
            "target_start": target_pos,
            "target_end": target_pos + target_len,
            "target_len": target_len,
            "delta_len": delta_len,
            "checksum": checksum,
            "counts": counts,
        })
        target_pos += target_len

    return {
        "header": header,
        "target_size": target_pos,
        "windows": windows,
        "source_copies": source_copies,
        "target_writes": target_writes,
    }


def merge_ranges(ranges):
    if not ranges:
        return []
    ranges = sorted(ranges)
    merged = [list(ranges[0])]
    for start, end in ranges[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


def reconstruct_source(pairs):
    max_source = 0
    for parsed, _target in pairs:
        for win in parsed["windows"]:
            if win["win_indicator"] & VCD_SOURCE:
                max_source = max(max_source, win["copy_pos"] + win["copy_len"])
    source = bytearray([0x00] * max_source)
    known = bytearray(max_source)
    conflicts = []
    assignments = 0
    for parsed, target_bytes in pairs:
        for op in parsed["source_copies"]:
            chunk = target_bytes[op["target_start"]:op["target_end"]]
            if len(chunk) != op["source_end"] - op["source_start"]:
                raise ValueError("target is shorter than the patch describes")
            for idx, value in enumerate(chunk):
                pos = op["source_start"] + idx
                if known[pos] and source[pos] != value:
                    conflicts.append({
                        "source": pos,
                        "old": source[pos],
                        "new": value,
                        "target_start": op["target_start"],
                    })
                else:
                    if not known[pos]:
                        assignments += 1
                    source[pos] = value
                    known[pos] = 1
    holes = []
    i = 0
    while i < len(known):
        if known[i]:
            i += 1
            continue
        start = i
        while i < len(known) and not known[i]:
            i += 1
        holes.append((start, i))
    return bytes(source), bytes(known), {
        "source_size": len(source),
        "known_bytes": sum(known),
        "unknown_bytes": len(source) - sum(known),
        "hole_count": len(holes),
        "first_40_holes": [[hex(s), hex(e), e - s] for s, e in holes[:40]],
        "conflict_count": len(conflicts),
        "first_20_conflicts": conflicts[:20],
        "assignments": assignments,
    }


def diff_known(source, known, target):
    limit = min(len(source), len(target))
    diff_ranges = []
    unknown_in_target = []
    i = 0
    while i < limit:
        if not known[i]:
            start = i
            while i < limit and not known[i]:
                i += 1
            unknown_in_target.append((start, i))
            continue
        if source[i] == target[i]:
            i += 1
            continue
        start = i
        while i < limit and known[i] and source[i] != target[i]:
            i += 1
        diff_ranges.append((start, i))
    if len(target) > len(source):
        diff_ranges.append((len(source), len(target)))
    return diff_ranges, unknown_in_target


def cmd_summary(args):
    patch = Path(args.patch).read_bytes()
    parsed = decode_windows(patch)
    report = {
        "patch": args.patch,
        "target_size": parsed["target_size"],
        "header": parsed["header"],
        "window_count": len(parsed["windows"]),
        "windows": parsed["windows"],
        "source_copy_ops": len(parsed["source_copies"]),
        "source_copy_bytes": sum(op["source_end"] - op["source_start"] for op in parsed["source_copies"]),
        "write_ops": len(parsed["target_writes"]),
        "write_bytes": sum(op["target_end"] - op["target_start"] for op in parsed["target_writes"]),
    }
    print(json.dumps(report, indent=2))


def cmd_reconstruct(args):
    pairs = []
    parsed_summaries = []
    for item in args.pair:
        patch_path, target_path = item.split("=", 1)
        patch = Path(patch_path).read_bytes()
        target = Path(target_path).read_bytes()
        parsed = decode_windows(patch, target)
        pairs.append((parsed, target))
        parsed_summaries.append({
            "patch": patch_path,
            "target": target_path,
            "target_size": parsed["target_size"],
            "window_count": len(parsed["windows"]),
            "source_copy_ops": len(parsed["source_copies"]),
            "source_copy_bytes": sum(op["source_end"] - op["source_start"] for op in parsed["source_copies"]),
            "header": parsed["header"],
        })
    source, known, recon_report = reconstruct_source(pairs)
    report = {
        "inputs": parsed_summaries,
        "reconstruction": recon_report,
    }
    if args.out_source:
        Path(args.out_source).write_bytes(source)
        report["out_source"] = args.out_source
    if args.out_mask:
        Path(args.out_mask).write_bytes(known)
        report["out_mask"] = args.out_mask
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def cmd_diff(args):
    source = Path(args.source).read_bytes()
    known = Path(args.mask).read_bytes()
    target = Path(args.target).read_bytes()
    diff_ranges, unknown_ranges = diff_known(source, known, target)
    report = {
        "source": args.source,
        "target": args.target,
        "target_size": len(target),
        "known_source_size": len(source),
        "diff_range_count": len(diff_ranges),
        "diff_bytes": sum(e - s for s, e in diff_ranges),
        "unknown_range_count_within_overlap": len(unknown_ranges),
        "unknown_bytes_within_overlap": sum(e - s for s, e in unknown_ranges),
        "first_120_diff_ranges": [[hex(s), hex(e), e - s] for s, e in diff_ranges[:120]],
        "first_40_unknown_ranges": [[hex(s), hex(e), e - s] for s, e in unknown_ranges[:40]],
    }
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("summary")
    p.add_argument("patch")
    p.set_defaults(func=cmd_summary)

    p = sub.add_parser("reconstruct")
    p.add_argument("--pair", action="append", required=True, help="patch=target")
    p.add_argument("--out-source")
    p.add_argument("--out-mask")
    p.add_argument("--report")
    p.set_defaults(func=cmd_reconstruct)

    p = sub.add_parser("diff")
    p.add_argument("source")
    p.add_argument("mask")
    p.add_argument("target")
    p.add_argument("--report")
    p.set_defaults(func=cmd_diff)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
