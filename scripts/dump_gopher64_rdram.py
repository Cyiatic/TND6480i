#!/usr/bin/env python3
"""Launch Gopher64, locate the emulated RDRAM buffer, and dump it.

This is a measurement fallback for cases where emulator screenshots are not
trustworthy but the emulator's own RDRAM still contains the display lists and
framebuffer state we need to inspect.
"""

import argparse
import ctypes
import json
import subprocess
import sys
import time
from pathlib import Path

from smoke_gopher64 import foreground_for_capture, parse_input_events, tap_key, windows_for_pid


if sys.platform != "win32":
    raise SystemExit("dump_gopher64_rdram.py currently uses Win32 process APIs")


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_NOACCESS = 0x01
PAGE_GUARD = 0x100
RDRAM_SIZE = 8 * 1024 * 1024


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.c_ulong),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_ulong),
        ("Protect", ctypes.c_ulong),
        ("Type", ctypes.c_ulong),
    ]


kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
kernel32.OpenProcess.restype = ctypes.c_void_p
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
kernel32.VirtualQueryEx.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION),
    ctypes.c_size_t,
]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t
kernel32.ReadProcessMemory.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.ReadProcessMemory.restype = ctypes.c_bool


def readable_region(info):
    return (
        info.State == MEM_COMMIT
        and not (info.Protect & PAGE_NOACCESS)
        and not (info.Protect & PAGE_GUARD)
        and info.RegionSize >= 0x1000
    )


def read_memory(handle, address, size):
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t()
    ok = kernel32.ReadProcessMemory(
        handle,
        ctypes.c_void_p(address),
        buf,
        size,
        ctypes.byref(read),
    )
    if not ok or read.value != size:
        return None
    return buf.raw


def iter_regions(handle):
    addr = 0
    max_addr = 0x7FFFFFFFFFFF
    info = MEMORY_BASIC_INFORMATION()
    while addr < max_addr:
        result = kernel32.VirtualQueryEx(
            handle,
            ctypes.c_void_p(addr),
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not result:
            break
        yield info
        next_addr = int(info.BaseAddress or 0) + int(info.RegionSize)
        if next_addr <= addr:
            break
        addr = next_addr


def locate_rdram(handle, rom_bytes, report_regions=False):
    pattern = rom_bytes[0x1000:0x1100]
    candidates = []
    regions_seen = 0
    for info in iter_regions(handle):
        if not readable_region(info):
            continue
        base = int(info.BaseAddress)
        size = int(info.RegionSize)
        regions_seen += 1
        if size < 0x20000:
            continue
        blob = read_memory(handle, base, min(size, 64 * 1024 * 1024))
        if not blob:
            continue
        pos = blob.find(pattern)
        while pos != -1:
            rdram_base = base + pos - 0x400
            if rdram_base >= base and rdram_base + RDRAM_SIZE <= base + size:
                sample = read_memory(handle, rdram_base + 0x400, len(pattern))
                full = read_memory(handle, rdram_base, RDRAM_SIZE)
                if sample == pattern and full:
                    # Penalize ROM-like mappings where the same pattern is also at
                    # base + 0x1000 rather than RDRAM's base + 0x400.
                    rom_like = read_memory(handle, rdram_base + 0x1000, len(pattern)) == pattern
                    candidates.append({
                        "rdram_base": rdram_base,
                        "region_base": base,
                        "region_size": size,
                        "pattern_offset": pos,
                        "rom_like": rom_like,
                        "dump": full,
                    })
            pos = blob.find(pattern, pos + 1)
    candidates.sort(key=lambda item: (item["rom_like"], -item["region_size"]))
    return candidates, regions_seen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gopher", required=True, type=Path)
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--input-events")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    rom_bytes = args.rom.read_bytes()
    input_events = parse_input_events(args.input_events)
    proc = subprocess.Popen([str(args.gopher), str(args.rom)])
    report = {
        "rom": str(args.rom),
        "pid": proc.pid,
        "seconds": args.seconds,
        "input_events": [
            {"time": event["time"], "key": event["key"], "duration": event["duration"]}
            for event in input_events
        ],
    }
    try:
        hwnd = None
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            wins = windows_for_pid(proc.pid)
            if wins:
                hwnd = wins[0][0]
                break
            time.sleep(0.1)
        if hwnd is not None:
            foreground_for_capture(hwnd)
        start = time.monotonic()
        consumed = 0
        for event in input_events:
            target = start + event["time"]
            while time.monotonic() < target:
                time.sleep(0.01)
            tap_key(event["vk"])
            consumed += 1
            if event["duration"] > 0.035:
                time.sleep(event["duration"] - 0.035)
        while time.monotonic() - start < args.seconds:
            if proc.poll() is not None:
                break
            time.sleep(0.05)

        handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, proc.pid)
        if not handle:
            raise RuntimeError(f"OpenProcess failed: {ctypes.get_last_error()}")
        try:
            candidates, regions_seen = locate_rdram(handle, rom_bytes)
        finally:
            kernel32.CloseHandle(handle)
        if not candidates:
            raise RuntimeError("could not locate an 8 MB RDRAM candidate in gopher64 process memory")
        best = candidates[0]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(best["dump"])
        report.update({
            "window_found": hwnd is not None,
            "input_events_consumed": consumed,
            "regions_seen": regions_seen,
            "candidate_count": len(candidates),
            "selected": {
                "rdram_base": f"0x{best['rdram_base']:X}",
                "region_base": f"0x{best['region_base']:X}",
                "region_size": best["region_size"],
                "pattern_offset": best["pattern_offset"],
                "rom_like": best["rom_like"],
            },
            "out": str(args.out),
            "bytes": len(best["dump"]),
        })
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
