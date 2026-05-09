#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

if sys.platform != "win32":
    raise SystemExit("smoke_gopher64.py currently uses Win32 window/input APIs")

import ctypes
from ctypes import wintypes


user32 = ctypes.WinDLL("user32", use_last_error=True)

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.keybd_event.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, wintypes.DWORD, ctypes.POINTER(ctypes.c_ulong)]

VK_RETURN = 0x0D
VK_LSHIFT = 0xA0
KEYEVENTF_KEYUP = 0x0002


def window_title(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def windows_for_pid(pid):
    found = []

    @EnumWindowsProc
    def enum_proc(hwnd, _lparam):
        proc_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if proc_id.value == pid and user32.IsWindowVisible(hwnd):
            found.append((hwnd, window_title(hwnd)))
        return True

    user32.EnumWindows(enum_proc, 0)
    return found


def tap_key(vk):
    user32.keybd_event(vk, 0, 0, None)
    time.sleep(0.035)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, None)


def capture_desktop(ffmpeg, out_png):
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "gdigrab",
        "-framerate",
        "1",
        "-i",
        "desktop",
        "-frames:v",
        "1",
        str(out_png),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
    return {
        "path": str(out_png),
        "returncode": result.returncode,
        "stderr_tail": result.stderr.splitlines()[-8:],
    }


def run_one(args, rom):
    stdout_path = args.report.parent / f"{Path(rom).stem}.stdout.txt"
    stderr_path = args.report.parent / f"{Path(rom).stem}.stderr.txt"
    env = os.environ.copy()
    env["SDL_AUDIODRIVER"] = "dummy"
    with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout, stderr_path.open(
        "w", encoding="utf-8", errors="replace"
    ) as stderr:
        proc = subprocess.Popen(
            [str(args.gopher), str(rom)],
            cwd=args.cwd,
            env=env,
            stdout=stdout,
            stderr=stderr,
        )
        start = time.monotonic()
        main_window = None
        key_taps = 0
        last_tap = 0.0
        try:
            while time.monotonic() - start < args.seconds:
                windows = windows_for_pid(proc.pid)
                if windows and main_window is None:
                    main_window = {"hwnd": int(windows[0][0]), "title": windows[0][1]}
                if args.input and main_window is not None and time.monotonic() - last_tap >= args.tap_interval:
                    user32.SetForegroundWindow(wintypes.HWND(main_window["hwnd"]))
                    tap_key(VK_RETURN)
                    tap_key(VK_LSHIFT)
                    key_taps += 2
                    last_tap = time.monotonic()
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
        finally:
            elapsed = time.monotonic() - start
            exited_before_timeout = proc.poll() is not None
            exit_code_before_timeout = proc.poll()
            if not exited_before_timeout:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)

    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    marker_counts = Counter(line.strip() for line in stdout_text.splitlines() if line.startswith("TND:"))
    capture = None
    if args.ffmpeg and args.capture_dir:
        capture = capture_desktop(args.ffmpeg, args.capture_dir / f"{Path(rom).stem}.png")
    return {
        "rom": str(rom),
        "elapsed": round(elapsed, 2),
        "main_window_seen": main_window is not None,
        "main_window": main_window,
        "key_taps": key_taps,
        "exited_before_timeout": exited_before_timeout,
        "exit_code_before_timeout": exit_code_before_timeout,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "stdout_bytes": len(stdout_text.encode("utf-8", errors="replace")),
        "stderr_bytes": len(stderr_text.encode("utf-8", errors="replace")),
        "marker_counts": dict(sorted(marker_counts.items())),
        "stderr_tail": stderr_text.splitlines()[-8:],
        "capture": capture,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("roms", nargs="+")
    parser.add_argument("--gopher", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--seconds", type=float, default=25.0)
    parser.add_argument("--input", action="store_true")
    parser.add_argument("--tap-interval", type=float, default=0.6)
    parser.add_argument("--ffmpeg", type=Path, default=None)
    parser.add_argument("--capture-dir", type=Path, default=None)
    parser.add_argument("--cwd", default=str(Path.cwd()))
    args = parser.parse_args()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    results = [run_one(args, rom) for rom in args.roms]
    args.report.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
