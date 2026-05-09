# SummerCart64 Setup Notes

Date: 2026-05-08

## Local Tools

- Deployer: `C:\Users\codex\Documents\n64\sc64deployer.exe`
- Deployer version: `sc64deployer 2.20.2`
- Extras folder: `C:\Users\codex\Documents\n64\sc64-extra-v2.20.2`
- Firmware bundle: `C:\Users\codex\Documents\n64\sc64-extra-v2.20.2\sc64-firmware-v2.20.2.bin`
- Firmware metadata from bundle:
  - version: `v2.20.2`
  - created: `2024-11-18 22:10:49`
  - tag: `v2.20.2`
  - sha: `18041e25472075a166292d1195603bcefe9c9688`

Current detection result before the SC64 is physically connected:

```text
No SC64 devices found
```

## Physical Swap Checklist

Do not upload anything until the capture card visibly shows the SC64 menu or another known-good live video state.

1. Power off the N64.
2. Swap EverDrive X7 for SummerCart64.
3. Connect SummerCart64 USB-C to this PC.
4. Power on the N64.
5. Capture one GV-USB2 frame and confirm the SC64 menu is visible.
6. Run:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' list
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' info
```

## Upload Commands

Current rule after the late 2026-05-08 SC64 session:

- Do not use `--direct` as the first path. It queued a ROM but left the capture/menu state ambiguous, and `--direct --reboot` reported AUX halt/reboot warnings.
- Use normal `upload` from a visibly working SC64 menu, then use the real console reset/power cycle path.
- If GV-USB2 is still flat blue, stop. A passive capture on 2026-05-09 was still flat blue: `parallel_diag/capture_before_morning_handoff_20260509.png`.

Current first uninstrumented hardware candidate:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\Codex\2026-05-06\files-mentioned-by-the-user-tnd64\TND64_480i_single8076_all_core_no_menu.z64'
```

This supersedes the earlier width/scale-only candidate for a one-shot visual test because it includes the GE 480i origin/control-flow bypass at `0x19978/0x19980` in addition to the width/vsync and scale words.

Previous width/scale-only candidate, still useful as an isolation fallback:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\Codex\2026-05-06\files-mentioned-by-the-user-tnd64\TND64_480i_single8076_mem_fg_h_width_scale_core_no_menu.z64'
```

Experimental double-buffer fallback, only after the single-high candidate has a clear result:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\Codex\2026-05-06\files-mentioned-by-the-user-tnd64\TND64_480i_split8030_8076_all_core_no_menu.z64'
```

## Debug Mode

`sc64deployer debug` supports UNFLoader-style debug terminal behavior.

An SC64/IS-Viewer-instrumented copy of the current best candidate is ready:

```text
TND64_480i_single8076_all_core_no_menu_sc64isv_entry.z64
MD5: 76071b20801ad798fa47233e95daf27f
N64 CRC: 5BC25FC8 8378A8B1
```

Expected IS-Viewer markers:

```text
TND:ENTR  entry trampoline ran
TND:BCLR  framebuffer clear function returned
TND:DFB1  framebuffer globals were written
TND:HVI1  VI setup function returned
```

`TND:HVI1` is intentionally emitted from the VI setup return path, so it may repeat while the game is still alive. That is useful if the debug terminal connects after the earliest boot path.

Use the instrumented ROM when debugging a black screen:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\Codex\2026-05-06\files-mentioned-by-the-user-tnd64\TND64_480i_single8076_all_core_no_menu_sc64isv_entry.z64'
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' debug --isv 0x03FF0000
```

IS-Viewer64 standalone debug command:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' debug --isv 0x03FF0000
```

The SC64 docs say `ISV_ADDRESS` enables IS-Viewer64 at a ROM-base-relative offset. For most apps this is `0x03FF0000`.

The instrumented candidate was emulator-smoked in Gopher64:

- visible 30 second smoke: survived, no early exit
- input-driven 65 second smoke: survived, no early exit

## Immediate Debug Strategy

1. Use SC64 for faster and cleaner upload/run first.
2. If the current best candidate still black-screens, run the SC64 ISV instrumented candidate and capture:
   - `sc64deployer debug --isv 0x03FF0000` output
   - GV-USB2 frames at 2, 5, 10, 15, 30, 60, 90, and 120 seconds
3. If `TND:BCLR` appears but `TND:DFB1` does not, focus on framebuffer-global setup.
4. If `TND:DFB1` appears but `TND:HVI1` does not, focus on the VI setup function or an earlier crash before video registers finish.
5. If `TND:HVI1` repeats while capture is black, focus on VI register values, framebuffer address/format, and output mode rather than a hard crash.
