#!/usr/bin/env python3
import argparse
import json
import hashlib
import zlib
from pathlib import Path


GE_1172_OFFSET = 0x21990


def inflate_ge1172(rom_bytes, offset=GE_1172_OFFSET):
    if rom_bytes[offset:offset + 2] != b"\x11\x72":
        raise ValueError(f"no GE 1172 marker at 0x{offset:X}")

    payload = rom_bytes[offset + 2:]
    decomp = zlib.decompressobj(-15)
    raw = decomp.decompress(payload)
    raw += decomp.flush()
    consumed = len(payload) - len(decomp.unused_data) + 2
    return raw, consumed


def scan_ge1172_streams(rom_bytes, min_raw_size=16):
    streams = []
    pos = 0
    while True:
        off = rom_bytes.find(b"\x11\x72", pos)
        if off < 0:
            return streams
        pos = off + 1
        try:
            raw, consumed = inflate_ge1172(rom_bytes, off)
        except Exception:
            continue
        if len(raw) < min_raw_size:
            continue
        streams.append({
            "offset": off,
            "consumed": consumed,
            "raw_size": len(raw),
            "md5": hashlib.md5(raw).hexdigest(),
        })


def read_bytes(path):
    return Path(path).read_bytes()


def write_bytes(path, data):
    Path(path).write_bytes(data)


def diff_runs(a, b):
    if len(a) != len(b):
        raise ValueError(f"length mismatch: {len(a)} != {len(b)}")
    runs = []
    i = 0
    while i < len(a):
        if a[i] == b[i]:
            i += 1
            continue
        start = i
        i += 1
        while i < len(a) and a[i] != b[i]:
            i += 1
        runs.append((start, i))
    return runs


def diff_words(a, b):
    if len(a) != len(b):
        raise ValueError(f"length mismatch: {len(a)} != {len(b)}")
    words = []
    for off in range(0, len(a) - 3, 4):
        if a[off:off + 4] != b[off:off + 4]:
            words.append(off)
    return words


def group_words(words, gap):
    if not words:
        return []
    groups = []
    start = prev = words[0]
    for off in words[1:]:
        if off - prev <= gap + 4:
            prev = off
            continue
        groups.append((start, prev + 4))
        start = prev = off
    groups.append((start, prev + 4))
    return groups


def byte_diff_count(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def apply_word_safe(stock, hi, target):
    out = bytearray(target)
    words = diff_words(stock, hi)
    applied = []
    conflicts = []
    for off in words:
        old = stock[off:off + 4]
        new = hi[off:off + 4]
        cur = target[off:off + 4]
        if cur == old:
            out[off:off + 4] = new
            applied.append(off)
        else:
            conflicts.append(off)
    return bytes(out), {
        "mode": "word-safe",
        "diff_words": len(words),
        "applied_words": len(applied),
        "conflict_words": len(conflicts),
        "applied_bytes": len(applied) * 4,
        "conflict_bytes": len(conflicts) * 4,
    }


def apply_hunk_safe(stock, hi, target, gap):
    out = bytearray(target)
    words = diff_words(stock, hi)
    groups = group_words(words, gap)
    applied = []
    conflicts = []
    for start, end in groups:
        if target[start:end] == stock[start:end]:
            out[start:end] = hi[start:end]
            applied.append((start, end))
        else:
            conflicts.append((start, end))
    return bytes(out), {
        "mode": f"hunk-safe-gap{gap}",
        "groups": len(groups),
        "applied_groups": len(applied),
        "conflict_groups": len(conflicts),
        "applied_bytes": sum(e - s for s, e in applied),
        "conflict_bytes": sum(e - s for s, e in conflicts),
    }


def find_all(haystack, needle):
    hits = []
    pos = 0
    while True:
        idx = haystack.find(needle, pos)
        if idx < 0:
            return hits
        hits.append(idx)
        pos = idx + 1


def apply_context_hunks(stock, hi, target, gap, context):
    out = bytearray(target)
    words = diff_words(stock, hi)
    groups = group_words(words, gap)
    applied_same = []
    applied_moved = []
    conflicts = []
    ambiguous = []
    missing = []

    for start, end in groups:
        left = max(0, start - context)
        right = min(len(stock), end + context)
        pattern = stock[left:right]
        hits = find_all(target, pattern)
        if len(hits) == 1:
            dest = hits[0] + (start - left)
            out[dest:dest + (end - start)] = hi[start:end]
            if dest == start:
                applied_same.append((start, end, dest))
            else:
                applied_moved.append((start, end, dest))
        elif len(hits) > 1:
            ambiguous.append((start, end, len(hits)))
        else:
            if target[start:end] == stock[start:end]:
                out[start:end] = hi[start:end]
                applied_same.append((start, end, start))
            else:
                missing.append((start, end))
                conflicts.append((start, end))

    return bytes(out), {
        "mode": f"context-gap{gap}-ctx{context}",
        "groups": len(groups),
        "applied_same_groups": len(applied_same),
        "applied_moved_groups": len(applied_moved),
        "missing_groups": len(missing),
        "ambiguous_groups": len(ambiguous),
        "conflict_groups": len(conflicts),
        "applied_bytes": sum(e - s for s, e, _ in applied_same + applied_moved),
        "moved_examples": [
            {"source": f"0x{s:X}-0x{e:X}", "dest": f"0x{d:X}"}
            for s, e, d in applied_moved[:20]
        ],
    }


def summarize(stock, hi, tnd):
    runs = diff_runs(stock, hi)
    words = diff_words(stock, hi)
    tnd_words = diff_words(stock, tnd)
    conflict_words = [off for off in words if tnd[off:off + 4] != stock[off:off + 4]]
    gap16_groups = []
    for start, end in group_words(words, 16):
        same = tnd[start:end] == stock[start:end]
        changed_bytes = byte_diff_count(stock[start:end], hi[start:end])
        tnd_conflict_bytes = byte_diff_count(stock[start:end], tnd[start:end])
        gap16_groups.append({
            "start": f"0x{start:X}",
            "end": f"0x{end:X}",
            "len": end - start,
            "same_in_tnd": same,
            "changed_bytes": changed_bytes,
            "tnd_conflict_bytes": tnd_conflict_bytes,
            "stock_first16": stock[start:min(end, start + 16)].hex(),
            "hi_first16": hi[start:min(end, start + 16)].hex(),
            "tnd_first16": tnd[start:min(end, start + 16)].hex(),
        })
    return {
        "raw_size": len(stock),
        "byte_diffs_stock_to_480i": byte_diff_count(stock, hi),
        "byte_diffs_stock_to_tnd": byte_diff_count(stock, tnd),
        "byte_diff_runs_stock_to_480i": len(runs),
        "word_diffs_stock_to_480i": len(words),
        "word_diffs_stock_to_tnd": len(tnd_words),
        "word_conflicts_480i_vs_tnd": len(conflict_words),
        "gap16_groups": gap16_groups,
        "first_40_480i_runs": [
            {
                "start": f"0x{s:X}",
                "end": f"0x{e:X}",
                "len": e - s,
                "stock": stock[s:min(e, s + 16)].hex(),
                "hi": hi[s:min(e, s + 16)].hex(),
                "tnd": tnd[s:min(e, s + 16)].hex(),
            }
            for s, e in runs[:40]
        ],
    }


def cmd_extract(args):
    raw, consumed = inflate_ge1172(read_bytes(args.rom), args.offset)
    write_bytes(args.out, raw)
    print(json.dumps({
        "rom": args.rom,
        "out": args.out,
        "offset": f"0x{args.offset:X}",
        "raw_size": len(raw),
        "consumed": f"0x{consumed:X}",
    }, indent=2))


def cmd_analyze(args):
    stock = read_bytes(args.stock_raw)
    hi = read_bytes(args.hi_raw)
    tnd = read_bytes(args.tnd_raw)
    print(json.dumps(summarize(stock, hi, tnd), indent=2))


def cmd_scanrom(args):
    reports = []
    for rom in args.roms:
        data = read_bytes(rom)
        streams = scan_ge1172_streams(data, args.min_raw_size)
        reports.append({
            "rom": rom,
            "size": len(data),
            "stream_count": len(streams),
            "streams": [
                {
                    "offset": f"0x{s['offset']:X}",
                    "consumed": f"0x{s['consumed']:X}",
                    "raw_size": s["raw_size"],
                    "md5": s["md5"],
                }
                for s in streams
            ],
        })
    print(json.dumps(reports, indent=2))


def cmd_make(args):
    stock = read_bytes(args.stock_raw)
    hi = read_bytes(args.hi_raw)
    tnd = read_bytes(args.tnd_raw)
    reports = []

    variants = []
    variants.append((args.out_prefix + "_word_safe.bin",) + apply_word_safe(stock, hi, tnd))
    for gap in args.gaps:
        variants.append((args.out_prefix + f"_hunk_gap{gap}.bin",) + apply_hunk_safe(stock, hi, tnd, gap))
    for gap in args.gaps:
        variants.append((args.out_prefix + f"_context_gap{gap}_ctx{args.context}.bin",) + apply_context_hunks(stock, hi, tnd, gap, args.context))

    for path, raw, report in variants:
        write_bytes(path, raw)
        report["out"] = path
        report["byte_diffs_from_tnd"] = byte_diff_count(tnd, raw)
        reports.append(report)

    Path(args.report).write_text(json.dumps(reports, indent=2) + "\n")
    print(json.dumps(reports, indent=2))


def cmd_surgical(args):
    hi = read_bytes(args.hi_raw)
    tnd = bytearray(read_bytes(args.tnd_raw))
    range_sets = {
        "all": [
            (0x24B8, 0x2500, "display table A"),
            (0x5CD4, 0x5D10, "VI/display command table A"),
            (0x7594, 0x75D0, "VI/display command table B"),
            (0x76F0, 0x7700, "dimension table header only"),
            (0x9C3C, 0x9D24, "enhanced menu/display table A"),
            (0xA240, 0xA264, "enhanced menu/display table B"),
        ],
        "core_no_menu": [
            (0x24B8, 0x2500, "display table A"),
            (0x5CD4, 0x5D10, "VI/display command table A"),
            (0x7594, 0x75D0, "VI/display command table B"),
            (0x76F0, 0x7700, "dimension table header only"),
        ],
        "core_no_dim": [
            (0x24B8, 0x2500, "display table A"),
            (0x5CD4, 0x5D10, "VI/display command table A"),
            (0x7594, 0x75D0, "VI/display command table B"),
            (0x9C3C, 0x9D24, "enhanced menu/display table A"),
            (0xA240, 0xA264, "enhanced menu/display table B"),
        ],
        "core_only": [
            (0x24B8, 0x2500, "display table A"),
            (0x5CD4, 0x5D10, "VI/display command table A"),
            (0x7594, 0x75D0, "VI/display command table B"),
        ],
        "menu_only": [
            (0x9C3C, 0x9D24, "enhanced menu/display table A"),
            (0xA240, 0xA264, "enhanced menu/display table B"),
        ],
    }
    ranges = range_sets[args.variant]
    # A quick reminder for future-us: the large conflicting groups are mostly
    # TND resource/name/pointer tables and must not be copied wholesale.
    base_ranges = [
        (0x24B8, 0x2500, "display table A"),
        (0x5CD4, 0x5D10, "VI/display command table A"),
        (0x7594, 0x75D0, "VI/display command table B"),
        (0x76F0, 0x7700, "dimension table header only"),
        (0x9C3C, 0x9D24, "enhanced menu/display table A"),
        (0xA240, 0xA264, "enhanced menu/display table B"),
    ]
    report = []
    for start, end, note in ranges:
        before = bytes(tnd[start:end])
        tnd[start:end] = hi[start:end]
        report.append({
            "start": f"0x{start:X}",
            "end": f"0x{end:X}",
            "len": end - start,
            "note": note,
            "changed_bytes_from_tnd": byte_diff_count(before, hi[start:end]),
        })

    write_bytes(args.out, bytes(tnd))
    Path(args.report).write_text(json.dumps({
        "variant": args.variant,
        "applied": report,
        "available_ranges": [
            {"start": f"0x{s:X}", "end": f"0x{e:X}", "note": note}
            for s, e, note in base_ranges
        ],
    }, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("extract")
    p.add_argument("rom")
    p.add_argument("out")
    p.add_argument("--offset", type=lambda x: int(x, 0), default=GE_1172_OFFSET)
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("analyze")
    p.add_argument("stock_raw")
    p.add_argument("hi_raw")
    p.add_argument("tnd_raw")
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("make")
    p.add_argument("stock_raw")
    p.add_argument("hi_raw")
    p.add_argument("tnd_raw")
    p.add_argument("out_prefix")
    p.add_argument("--report", default="port_480i_report.json")
    p.add_argument("--context", type=int, default=32)
    p.add_argument("--gaps", type=int, nargs="+", default=[0, 16, 64])
    p.set_defaults(func=cmd_make)

    p = sub.add_parser("scanrom")
    p.add_argument("roms", nargs="+")
    p.add_argument("--min-raw-size", type=int, default=64)
    p.set_defaults(func=cmd_scanrom)

    p = sub.add_parser("surgical")
    p.add_argument("hi_raw")
    p.add_argument("tnd_raw")
    p.add_argument("out")
    p.add_argument("--report", default="port_480i_surgical_report.json")
    p.add_argument(
        "--variant",
        choices=["all", "core_no_menu", "core_no_dim", "core_only", "menu_only"],
        default="all",
    )
    p.set_defaults(func=cmd_surgical)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
