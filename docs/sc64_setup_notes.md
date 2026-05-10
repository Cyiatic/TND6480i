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

## Capture And Power Control Notes

- Current DirectShow video device name for ffmpeg is `GV-USB2, Analog Capture`.
- Kasa Smart Control plug label is `N64`.
- To power-cycle from the app, click the center of the teal square above the `N64` label, then click the shaded `Off` or `On` button on the right. Avoid the `Refresh` button.
- After `sc64deployer reset`, a Kasa off/on cycle has restored the SC64 menu and `ROM write: Enabled`.

## Upload Commands

Current rule after the late 2026-05-08 SC64 session:

- Do not use `--direct` as the first path. It queued a ROM but left the capture/menu state ambiguous, and `--direct --reboot` reported AUX halt/reboot warnings.
- Use normal `upload` from a visibly working SC64 menu, then use the real console reset/power cycle path.
- If GV-USB2 is still flat blue, stop. A passive capture on 2026-05-09 was still flat blue: `parallel_diag/capture_before_morning_handoff_20260509.png`.

Current first meaningful hardware candidate is an instrumented low-cave baseline control, not a 480i candidate:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\GitHub\TND6480i\artifacts\generated\BASELINE_TND64_Expanded_sc64isv_hvionly_lowcave.z64'
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' debug --isv 0x03FF0000 --no-writeback
```

Press the real N64 reset button after upload/listener setup. Expected marker: `TND:HVI1`.

Lowest-risk visual-only baseline control, if we want to prove the low-cave trampoline before any debug write:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\GitHub\TND6480i\artifacts\generated\BASELINE_TND64_Expanded_hvijump_lowcave.z64'
```

Expected result: normal baseline TND video after reset. This emits no debug marker.

Current best uninstrumented 480i visual candidate, only after the SC64 debug channel is validated:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\GitHub\TND6480i\artifacts\generated\TND64_480i_single8076_all_core_no_menu.z64'
```

This supersedes the earlier width/scale-only candidate for a one-shot visual test because it includes the GE 480i origin/control-flow bypass at `0x19978/0x19980` in addition to the width/vsync and scale words.

Previous width/scale-only candidate, still useful as an isolation fallback:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\GitHub\TND6480i\artifacts\generated\TND64_480i_single8076_mem_fg_h_width_scale_core_no_menu.z64'
```

## Debug Mode

`sc64deployer debug` supports UNFLoader-style debug terminal behavior.

An SC64/IS-Viewer low-cave HVI-only baseline control is ready:

```text
BASELINE_TND64_Expanded_sc64isv_hvionly_lowcave.z64
MD5: efc8c7caaa898e421f82eb42b2d62edb
N64 CRC: 5AB52A0F BAB5C1D8
```

Expected IS-Viewer markers:

```text
TND:HVI1  VI setup function returned
```

`TND:HVI1` is intentionally emitted from the VI setup return path, so it may repeat while the game is still alive. That is useful if the debug terminal connects after the earliest boot path.

Use the low-cave HVI-only baseline first when debugging a black screen:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\GitHub\TND6480i\artifacts\generated\BASELINE_TND64_Expanded_sc64isv_hvionly_lowcave.z64'
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' debug --isv 0x03FF0000 --no-writeback
```

IS-Viewer64 standalone debug command:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' debug --isv 0x03FF0000
```

The SC64 docs say `ISV_ADDRESS` enables IS-Viewer64 at a ROM-base-relative offset. For most apps this is `0x03FF0000`.

The low-cave baseline and corrected v3 diagnostic builds were emulator-smoked in Gopher64:

- `BASELINE_TND64_Expanded_hvijump_lowcave.z64`: 25 second smoke survived, no early exit
- `BASELINE_TND64_Expanded_sc64isv_hvionly_lowcave.z64`: 25 second smoke survived, no early exit
- `BASELINE_TND64_Expanded_sc64isv_noentry_v3_lowcave.z64`: 25 second smoke survived, no early exit
- `TND64_480i_single8076_all_core_no_menu_sc64isv_hvionly_lowcave.z64`: 25 second smoke survived, no early exit

## Immediate Debug Strategy

1. Use SC64 for faster and cleaner upload/run first.
2. Validate the low-cave HVI-only baseline control and capture:
   - `sc64deployer debug --isv 0x03FF0000` output
   - GV-USB2 frames at 2, 5, 10, 15, 30, 60, 90, and 120 seconds
3. If `TND:HVI1` appears on baseline, run the corrected v3 all-hook baseline control.
4. If the corrected baseline markers appear, test the HVI-only 480i debug ROM.
5. If `TND:HVI1` repeats while capture is black on the 480i build, focus on VI register values, framebuffer address/format, and output mode rather than a hard crash.
