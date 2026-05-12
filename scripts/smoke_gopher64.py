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
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.MoveWindow.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.BOOL]
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint,
]
user32.keybd_event.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, wintypes.DWORD, ctypes.POINTER(ctypes.c_ulong)]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowDC.argtypes = [wintypes.HWND]
user32.GetWindowDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, ctypes.c_uint]

gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.GetDIBits.argtypes = [
    wintypes.HDC,
    wintypes.HBITMAP,
    ctypes.c_uint,
    ctypes.c_uint,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint,
]

VK_RETURN = 0x0D
VK_LSHIFT = 0xA0
VK_LCTRL = 0xA2
VK_TAB = 0x09
VK_SPACE = 0x20
VK_ESCAPE = 0x1B
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
KEYEVENTF_KEYUP = 0x0002
SW_RESTORE = 9
HWND_TOPMOST = wintypes.HWND(-1)
SWP_SHOWWINDOW = 0x0040
PW_RENDERFULLCONTENT = 0x00000002
DIB_RGB_COLORS = 0
BI_RGB = 0

VK_NAMES = {
    "ENTER": VK_RETURN,
    "RETURN": VK_RETURN,
    "START": VK_RETURN,
    "LSHIFT": VK_LSHIFT,
    "SHIFT": VK_LSHIFT,
    "A_BUTTON": VK_LSHIFT,
    "A_BTN": VK_LSHIFT,
    "LCTRL": VK_LCTRL,
    "CTRL": VK_LCTRL,
    "B_BUTTON": VK_LCTRL,
    "B_BTN": VK_LCTRL,
    "TAB": VK_TAB,
    "SPACE": VK_SPACE,
    "ESC": VK_ESCAPE,
    "ESCAPE": VK_ESCAPE,
    "LEFT": VK_LEFT,
    "RIGHT": VK_RIGHT,
    "UP": VK_UP,
    "DOWN": VK_DOWN,
}
for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
    VK_NAMES[char] = ord(char)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


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


def set_key(vk, pressed):
    flags = 0 if pressed else KEYEVENTF_KEYUP
    user32.keybd_event(vk, 0, flags, None)


def parse_input_events(value):
    if not value:
        return []
    text = value
    path = Path(value)
    if path.exists():
        text = path.read_text(encoding="utf-8")

    events = []
    for raw_part in text.replace("\n", ";").split(";"):
        part = raw_part.strip()
        if not part or part.startswith("#"):
            continue
        fields = [field.strip() for field in part.replace(",", ":").split(":") if field.strip()]
        if len(fields) not in {2, 3}:
            raise argparse.ArgumentTypeError(
                f"input event must be time:key[:duration], got {raw_part!r}"
            )
        event_time = float(fields[0])
        key_name = fields[1].upper()
        if key_name not in VK_NAMES:
            known = ", ".join(sorted(VK_NAMES))
            raise argparse.ArgumentTypeError(f"unknown key {fields[1]!r}; known keys: {known}")
        duration = float(fields[2]) if len(fields) == 3 else 0.035
        if duration < 0:
            raise argparse.ArgumentTypeError(f"duration must be non-negative, got {raw_part!r}")
        events.append({
            "time": event_time,
            "key": key_name,
            "vk": VK_NAMES[key_name],
            "duration": duration,
        })
    return sorted(events, key=lambda item: item["time"])


def foreground_for_capture(hwnd):
    hwnd = wintypes.HWND(hwnd)
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 96, 96, 656, 519, SWP_SHOWWINDOW)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)


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
        "capture_method": "ffmpeg_gdigrab_desktop",
        "stderr_tail": result.stderr.splitlines()[-8:],
    }


def capture_window_title_gdigrab(ffmpeg, out_png, title):
    out_png.parent.mkdir(parents=True, exist_ok=True)
    if not title:
        return {
            "path": str(out_png),
            "returncode": 1,
            "capture_method": "ffmpeg_gdigrab_title",
            "stderr_tail": ["window title unavailable"],
        }
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
        f"title={title}",
        "-frames:v",
        "1",
        str(out_png),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
    return {
        "path": str(out_png),
        "returncode": result.returncode,
        "capture_method": "ffmpeg_gdigrab_title",
        "stderr_tail": result.stderr.splitlines()[-8:],
    }


def window_rect(hwnd):
    rect = wintypes.RECT()
    if not user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect)):
        return None
    return {
        "left": rect.left,
        "top": rect.top,
        "right": rect.right,
        "bottom": rect.bottom,
        "width": rect.right - rect.left,
        "height": rect.bottom - rect.top,
    }


def capture_window_imagegrab(hwnd, out_png, original_error=None):
    out_png.parent.mkdir(parents=True, exist_ok=True)
    rect = window_rect(hwnd)
    if not rect:
        return {
            "path": str(out_png),
            "returncode": 1,
            "capture_method": "pil_imagegrab_window",
            "stderr_tail": ["window rect unavailable"],
            "ffmpeg_error": original_error,
        }
    try:
        from PIL import ImageGrab

        image = ImageGrab.grab(
            bbox=(rect["left"], rect["top"], rect["right"], rect["bottom"]),
            all_screens=True,
        ).convert("RGB")
        image.save(out_png)
        return {
            "path": str(out_png),
            "returncode": 0,
            "capture_method": "pil_imagegrab_window",
            "stderr_tail": [],
            "desktop_window_rect": rect,
            "window_rect": {
                "left": 0,
                "top": 0,
                "right": image.width,
                "bottom": image.height,
                "width": image.width,
                "height": image.height,
            },
            "ffmpeg_error": original_error,
        }
    except Exception as exc:
        return {
            "path": str(out_png),
            "returncode": 1,
            "capture_method": "pil_imagegrab_window",
            "stderr_tail": [repr(exc)],
            "desktop_window_rect": rect,
            "ffmpeg_error": original_error,
        }


def capture_window_printwindow(hwnd, out_png, original_error=None):
    out_png.parent.mkdir(parents=True, exist_ok=True)
    rect = window_rect(hwnd)
    if not rect:
        return {
            "path": str(out_png),
            "returncode": 1,
            "capture_method": "win32_printwindow",
            "stderr_tail": ["window rect unavailable"],
            "previous_error": original_error,
        }
    width = rect["width"]
    height = rect["height"]
    if width <= 0 or height <= 0:
        return {
            "path": str(out_png),
            "returncode": 1,
            "capture_method": "win32_printwindow",
            "stderr_tail": ["empty window rect"],
            "desktop_window_rect": rect,
            "previous_error": original_error,
        }

    hwnd_obj = wintypes.HWND(hwnd)
    hwnd_dc = user32.GetWindowDC(hwnd_obj)
    mem_dc = None
    bitmap = None
    old_obj = None
    try:
        mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
        bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
        old_obj = gdi32.SelectObject(mem_dc, bitmap)
        ok = user32.PrintWindow(hwnd_obj, mem_dc, PW_RENDERFULLCONTENT)
        if not ok:
            ok = user32.PrintWindow(hwnd_obj, mem_dc, 0)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        buffer = ctypes.create_string_buffer(width * height * 4)
        got = gdi32.GetDIBits(mem_dc, bitmap, 0, height, buffer, ctypes.byref(bmi), DIB_RGB_COLORS)
        if got == 0:
            raise OSError(f"GetDIBits failed, last_error={ctypes.get_last_error()}")

        from PIL import Image

        image = Image.frombuffer("RGB", (width, height), buffer, "raw", "BGRX", 0, 1)
        image.save(out_png)
        return {
            "path": str(out_png),
            "returncode": 0 if ok else 2,
            "capture_method": "win32_printwindow",
            "stderr_tail": [] if ok else ["PrintWindow returned false; saved bitmap anyway"],
            "desktop_window_rect": rect,
            "window_rect": {
                "left": 0,
                "top": 0,
                "right": width,
                "bottom": height,
                "width": width,
                "height": height,
            },
            "previous_error": original_error,
        }
    except Exception as exc:
        return {
            "path": str(out_png),
            "returncode": 1,
            "capture_method": "win32_printwindow",
            "stderr_tail": [repr(exc)],
            "desktop_window_rect": rect,
            "previous_error": original_error,
        }
    finally:
        if old_obj:
            gdi32.SelectObject(mem_dc, old_obj)
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if mem_dc:
            gdi32.DeleteDC(mem_dc)
        if hwnd_dc:
            user32.ReleaseDC(hwnd_obj, hwnd_dc)


def analyze_capture(capture_path, rect):
    if not rect:
        return None
    try:
        from PIL import Image, ImageStat
    except Exception as exc:
        return {"error": f"Pillow unavailable: {exc}"}
    image = Image.open(capture_path).convert("RGB")
    left = max(0, min(image.width, rect["left"]))
    top = max(0, min(image.height, rect["top"]))
    right = max(0, min(image.width, rect["right"]))
    bottom = max(0, min(image.height, rect["bottom"]))
    if right <= left or bottom <= top:
        return {"error": "window rect outside capture"}
    crop = image.crop((left, top, right, bottom)).convert("L")
    stat = ImageStat.Stat(crop)
    pixels = crop.width * crop.height
    hist = crop.histogram()
    nonblack = sum(hist[9:])
    bright = sum(hist[48:])
    return {
        "crop_box": [left, top, right, bottom],
        "mean_luma": round(stat.mean[0], 2),
        "stddev_luma": round(stat.stddev[0], 2),
        "nonblack_ratio": round(nonblack / pixels, 4),
        "bright_ratio": round(bright / pixels, 4),
    }


def capture_looks_blank(capture_path):
    try:
        from PIL import Image, ImageStat

        image = Image.open(capture_path).convert("L")
        hist = image.histogram()
        pixels = image.width * image.height
        if pixels <= 0:
            return True
        nonblack_ratio = sum(hist[9:]) / pixels
        stat = ImageStat.Stat(image)
        # gdigrab-by-title can return a mostly black swapchain with a few stale white bars.
        # Treat that as blank so we fall back to desktop/window capture.
        return nonblack_ratio < 0.001 or (stat.mean[0] < 8.0 and nonblack_ratio < 0.03)
    except Exception:
        return False


def parse_capture_times(value):
    if not value:
        return []
    times = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        times.append(float(part))
    return sorted(set(times))


def timed_capture(args, rom, hwnd, elapsed, suffix):
    if not args.ffmpeg or not args.capture_dir:
        return None
    if hwnd is not None:
        foreground_for_capture(hwnd)
    stem = Path(rom).stem
    safe_suffix = suffix.replace(".", "p")
    out_png = args.capture_dir / f"{stem}_{safe_suffix}.png"
    title = window_title(wintypes.HWND(hwnd)) if hwnd is not None else ""
    capture = capture_window_title_gdigrab(args.ffmpeg, out_png, title)
    if capture["returncode"] == 0 and capture_looks_blank(capture["path"]):
        title_capture = capture
        capture = capture_desktop(args.ffmpeg, out_png)
        capture["previous_error"] = title_capture
    if capture["returncode"] != 0:
        capture = capture_desktop(args.ffmpeg, out_png)
    if hwnd is not None:
        rect = window_rect(hwnd)
        if capture["returncode"] == 0 and capture.get("capture_method") == "ffmpeg_gdigrab_title":
            try:
                from PIL import Image

                with Image.open(capture["path"]) as image:
                    rect = {
                        "left": 0,
                        "top": 0,
                        "right": image.width,
                        "bottom": image.height,
                        "width": image.width,
                        "height": image.height,
                    }
            except Exception:
                pass
        elif capture["returncode"] != 0:
            capture = capture_window_imagegrab(
                hwnd,
                args.capture_dir / f"{stem}_{safe_suffix}.png",
                original_error=capture,
            )
        if capture["returncode"] != 0:
            capture = capture_window_printwindow(
                hwnd,
                args.capture_dir / f"{stem}_{safe_suffix}.png",
                original_error=capture,
            )
            rect = capture.get("window_rect") or rect
        else:
            capture["window_rect"] = rect
        if capture["returncode"] == 0:
            capture["window_stats"] = analyze_capture(capture["path"], rect)
    capture["elapsed"] = round(elapsed, 2)
    return capture


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
        capture = None
        timed_captures = []
        next_capture_index = 0
        input_events = list(args.input_events)
        next_input_event = 0
        pending_keyups = []
        scripted_key_events = 0
        try:
            while time.monotonic() - start < args.seconds:
                windows = windows_for_pid(proc.pid)
                if windows and main_window is None:
                    main_window = {"hwnd": int(windows[0][0]), "title": windows[0][1]}
                elapsed_now = time.monotonic() - start
                if main_window is not None:
                    hwnd_obj = wintypes.HWND(main_window["hwnd"])
                    user32.SetForegroundWindow(hwnd_obj)
                    while pending_keyups and elapsed_now >= pending_keyups[0]["time"]:
                        item = pending_keyups.pop(0)
                        set_key(item["vk"], False)
                    while next_input_event < len(input_events) and elapsed_now >= input_events[next_input_event]["time"]:
                        event = input_events[next_input_event]
                        if event["duration"] == 0:
                            tap_key(event["vk"])
                            scripted_key_events += 2
                        else:
                            set_key(event["vk"], True)
                            scripted_key_events += 1
                            pending_keyups.append({
                                "time": elapsed_now + event["duration"],
                                "key": event["key"],
                                "vk": event["vk"],
                            })
                            pending_keyups.sort(key=lambda item: item["time"])
                        next_input_event += 1
                input_allowed = args.input and (args.input_until <= 0 or elapsed_now <= args.input_until)
                if input_allowed and main_window is not None and time.monotonic() - last_tap >= args.tap_interval:
                    user32.SetForegroundWindow(wintypes.HWND(main_window["hwnd"]))
                    tap_key(VK_RETURN)
                    tap_key(VK_LSHIFT)
                    key_taps += 2
                    last_tap = time.monotonic()
                if (
                    main_window is not None
                    and next_capture_index < len(args.capture_times)
                    and elapsed_now >= args.capture_times[next_capture_index]
                ):
                    hwnd = main_window["hwnd"]
                    suffix = f"t{args.capture_times[next_capture_index]:05.1f}s"
                    capture_item = timed_capture(args, rom, hwnd, elapsed_now, suffix)
                    if capture_item:
                        timed_captures.append(capture_item)
                    next_capture_index += 1
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
        finally:
            elapsed = time.monotonic() - start
            for item in pending_keyups:
                set_key(item["vk"], False)
            exited_before_timeout = proc.poll() is not None
            exit_code_before_timeout = proc.poll()
            if not exited_before_timeout and args.ffmpeg and args.capture_dir:
                hwnd = main_window["hwnd"] if main_window is not None else None
                capture = timed_capture(args, rom, hwnd, elapsed, "final")
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
    return {
        "rom": str(rom),
        "elapsed": round(elapsed, 2),
        "main_window_seen": main_window is not None,
        "main_window": main_window,
        "key_taps": key_taps,
        "scripted_key_events": scripted_key_events,
        "input_events_total": len(input_events),
        "input_events_consumed": next_input_event,
        "exited_before_timeout": exited_before_timeout,
        "exit_code_before_timeout": exit_code_before_timeout,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "stdout_bytes": len(stdout_text.encode("utf-8", errors="replace")),
        "stderr_bytes": len(stderr_text.encode("utf-8", errors="replace")),
        "marker_counts": dict(sorted(marker_counts.items())),
        "stderr_tail": stderr_text.splitlines()[-8:],
        "captures": timed_captures,
        "capture": capture,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("roms", nargs="+")
    parser.add_argument("--gopher", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--seconds", type=float, default=25.0)
    parser.add_argument("--input", action="store_true")
    parser.add_argument("--input-until", type=float, default=0.0, help="Stop automated Start/A taps after this many seconds; 0 means tap for the full run.")
    parser.add_argument("--tap-interval", type=float, default=0.6)
    parser.add_argument(
        "--input-events",
        type=parse_input_events,
        default=[],
        help="Semicolon/newline list or file path of scheduled key events: time:key[:duration].",
    )
    parser.add_argument("--ffmpeg", type=Path, default=None)
    parser.add_argument("--capture-dir", type=Path, default=None)
    parser.add_argument("--capture-times", type=parse_capture_times, default=[])
    parser.add_argument("--cwd", default=str(Path.cwd()))
    args = parser.parse_args()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    results = [run_one(args, rom) for rom in args.roms]
    args.report.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
