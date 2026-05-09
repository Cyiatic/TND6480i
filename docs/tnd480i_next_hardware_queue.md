# TND64 480i Next Hardware Queue

Date: 2026-05-08

## Current Hardware State

- 2026-05-09 SC64 repo session:
  - The prior runtime-fixed no-entry baseline debug ROM black-screened on hardware and produced no ISV markers.
  - That result is now partially invalidated because the `DFB1` hook was found to overwrite original framebuffer-global setup instead of replaying it.
  - `scripts/build_sc64_isv_instrumented.py` now supports `--hooks` and uses a corrected trampoline for `DFB1`.
  - A later HVI-only baseline control also black-screened when the logger/trampoline cave was at ROM `0x331E0`.
  - Current theory: `0x331E0` is not guaranteed to be resident in RDRAM when early boot/video code runs on real hardware. The new builds use an early low cave at ROM `0x3CB0`.
  - SC64 was reset over USB and reports `Bootloader -> Menu from SD card`. Do not upload another ROM while the user is away.
  - Next hardware step is a low-cave baseline control, not a 480i candidate.
- 2026-05-08 SC64 session:
  - SC64 detected on `COM4`; firmware `v2.20.2`; SD initialized; ROM writes enabled.
  - GV-USB2 capture showed the SC64 menu clearly.
  - Uploaded `TND64_480i_single8076_mem_fg_h_width_scale_core_no_menu_sc64isv.z64` with `sc64deployer upload --direct`.
  - Re-upload with `--direct --reboot` produced `no response for [Halt] AUX message` and `no response for [Reboot] AUX message`; capture still showed the SC64 menu.
  - SC64 then reported `Boot mode: ROM (direct)` and `ROM write: Disabled`, so the ROM was queued for direct boot on the next real console reset/power cycle.
  - `sc64deployer reset` is not a console reset; docs describe it as resetting SC64 config/options. Do not use it as a substitute for the N64 reset button.
  - This state has been superseded by the follow-up below.
- Later 2026-05-08 SC64 follow-up:
  - Reset launched out of the SC64 menu into a flat blue/no-detail capture by ~20 seconds when the direct-mode instrumented ROM was queued.
  - Normal `Bootloader -> ROM` upload of the same instrumented ROM also remained flat blue; no `TND:BCLR`, `TND:DFB1`, or `TND:HVI1` markers were printed.
  - Added and built an entry diagnostic ROM: `TND64_480i_single8076_mem_fg_h_width_scale_core_no_menu_sc64isv_entry.z64`.
    - MD5: `dc4337d4f21344110fcd69dd44484111`
    - N64 CRC: `478598B1 5F46604C`
    - Expected markers: `TND:ENTR`, `TND:BCLR`, `TND:DFB1`, `TND:HVI1`
    - Gopher64 smoke: survived 30 seconds.
  - Entry diagnostic in normal SC64 boot mode stayed flat blue and printed no `TND:ENTR` marker.
  - Control upload of known baseline `BASELINE_TND64_Expanded_direct_from_stock.z64` in normal SC64 boot mode also stayed flat blue through 80 seconds.
  - Therefore the late blue-screen captures should not be treated as ROM-specific proof. They indicate the current SC64/N64/capture state is not visibly booting queued ROMs.
  - `sc64deployer test` was started but did not return within two minutes and was stopped. Afterward, SC64 reported `Boot mode: Bootloader -> Menu from SD card`.
  - Current safe hardware state: SC64 is set back to menu mode, but GV-USB2 still captures a flat blue screen. Do not upload/test more ROMs until a real power cycle/check restores a visible SC64 menu or another known-good display.
- Treat the real N64 as unavailable unless the capture card visibly shows the SC64 menu, EverDrive menu, or another known-good live video state after a physical reset or power-cycle.
- 2026-05-09 passive GV-USB2 check before morning handoff still showed flat blue: `parallel_diag/capture_before_morning_handoff_20260509.png`.
- SummerCart64 tools are now staged in `C:\Users\codex\Documents\n64`: `sc64deployer.exe` version `2.20.2` and extracted extras at `sc64-extra-v2.20.2`. See `parallel_diag/sc64_setup_notes.md` before the next hardware session.
- A sufficiently bad ROM can lock the console hard. If a candidate black-screens or stops responding, do not attempt another upload until the user has physically power-cycled and the EverDrive menu is visible again.
- Latest hardware result: `TND64_480i_split8040_8076_mem_fg_h_width_scale_core_no_menu.z64` was uploaded once from a confirmed EverDrive menu and stayed pure black through 120 seconds of capture. Treat the console as potentially wedged again until physical power-cycle.
- Passive GV-USB2 capture after the single8076 emulator smokes was still pure black: `parallel_diag/capture_state_after_single8076_smokes.png`.
- Do not upload while the capture card shows the TND title/credits/game output.
- The validated EverDrive X7 upload path is:
  `UNFLoader.exe -b -f 3 -r <rom.z64>`
- `split8040_8076_all` black-screened on real N64 using the validated forced EverDrive path.
- `split8040_8076_mem_fg_h_width_scale` also black-screened on real N64 using the validated forced EverDrive path.
- Baseline TND booted normally using the same path, so the upload path is good.
- After the second split-layout black screen, deprioritize split `0x80400000/0x8076A000` hardware tests. The current safer branch is the single-high-framebuffer layout that keeps both framebuffer globals at `0x8076A000` and avoids clearing or drawing into `0x80400000`.

## Emulator Notes

- Gopher64 runs reliably over RDP when launched with:
  `SDL_AUDIODRIVER=dummy`
- Default Gopher64 keys used:
  - Start: Enter
  - A: Left Shift
  - B: Left Control
  - Analog: arrow keys
  - C-buttons: I/J/K/L
  - D-pad: W/A/S/D
  - Z/L/R: Z/X/C
- Automated Start/A input reaches gameplay on `split8040_8076_memonly`.
- `core_no_menu_base`, `split8040_8076_memonly`, `split8040_8076_fg`, and `split8040_8076_all` all reached or survived into live first-person/menu scenes in Gopher64.
- `split8040_8076_mem_fg_h_width_scale` reached the watch/gameplay path in Gopher64 with repeated Start/A input and did not exit before the 85 second timeout.
- `split8040_8076_mem_fg_h_origin_width` and `split8040_8076_mem_fg_h_origin_scale` survived 28 second no-input Gopher64 process smokes.
- `single8076_mem_fg`, `single8076_mem_fg_h_width`, `single8076_mem_fg_h_scale`, and `single8076_mem_fg_h_width_scale` all opened a visible Gopher64 main window and survived a 30 second visible process smoke on 2026-05-08.
- `single8076_mem_fg_h_width_scale` also survived an 84 second Gopher64 run with repeated Start/A input on 2026-05-08. Desktop capture failed in the current RDP/session state, and PrintWindow was proven unusable by producing the same black/white artifact for known-good baseline TND.
- Therefore the real-hardware black screen on `split8040_8076_all` is likely hardware-sensitive VI/register/cache behavior, not ROM packing or a general boot failure.

## Static Memory Notes

- TND's decompressed main has real-looking `0x8070xxxx` code/data references around `0x80700100` and `0x80702000`. Avoid framebuffer layouts that cover `0x80700000-0x8076A000`.
- The split layout leaves that area clear: fb0 is `0x80400000-0x80495FFF`; fb1 is `0x8076A000-0x807FFFFF`.
- The single-high layout uses only `0x8076A000-0x807FFFFF` and points both framebuffer globals at the same buffer. This avoids the suspected `0x80400000` collision, but it is a diagnostic single-buffer layout and may tear or flicker even if it boots.
- A static full-word scan of TND's decompressed main shows constants around `0x803AB400-0x803B4950`, plus isolated constants at `0x80500000`, `0x80600000`, `0x80702520`, and `0x80787000`. A `0x80300000` 640x480x16 framebuffer ends around `0x80396000`, below the `0x803Axxxx` constants, so `split8030_8076` exists as an experimental double-buffer fallback.
- `split8060_8076` failed in Gopher64 and should not be used as a first hardware fallback.

## Existing Known Hardware Result

### Do Not Re-test First

`TND64_480i_split8040_8076_core_no_menu.z64`

- Profile: `split8040_8076_all_nodims`
- MD5: `482a19f86b022531cdef49382b5c540a`
- N64 CRC: `257D2EA2 01491962`
- Result: black screen on real N64.

`TND64_480i_split8040_8076_mem_fg_h_width_scale_core_no_menu.z64`

- Profile: `split8040_8076_mem_fg_h_width_scale_nodims`
- MD5: `865157b56f1e3a384888c909520f2740`
- N64 CRC: `3D4A29A2 1F98FEB5`
- Result: black screen on real N64 from a confirmed EverDrive menu, pure black at 2, 5, 10, 15, 30, 45, 60, 90, and 120 seconds.

## Current Safest Hardware Candidate

Only use this if the capture card visibly shows the SC64 menu, EverDrive menu, or another known-good live video state after a physical reset or power-cycle. If it black-screens or locks, stop immediately and continue offline.

`BASELINE_TND64_Expanded_sc64isv_hvionly_lowcave.z64`

- Base: known-good baseline TND expanded ROM.
- MD5: `efc8c7caaa898e421f82eb42b2d62edb`
- N64 CRC: `5AB52A0F BAB5C1D8`
- Expected marker: `TND:HVI1`
- Purpose: validate SC64/IS-Viewer logging from the least invasive late video hook, with the logger/trampoline in known early-code padding, before testing any 480i payload.
- Emulator status: Gopher64 25 second smoke survived.

If this prints `TND:HVI1`, test `BASELINE_TND64_Expanded_sc64isv_noentry_v3_lowcave.z64` next to validate the corrected multi-hook logger. Only then use the HVI-only 480i debug ROM or return to visual 480i candidates.

Lowest-risk visual-only control:

`BASELINE_TND64_Expanded_hvijump_lowcave.z64`

- MD5: `e12d5f83eadd9ad4ae3f5427c3648e02`
- N64 CRC: `E21F057C 49DC630F`
- Purpose: proves the low-cave HVI trampoline itself does not break baseline TND. It emits no debug marker.
- Emulator status: Gopher64 25 second smoke survived.

## SC64 Instrumented Debug Candidate

Use this on SummerCart64 when debug visibility matters more than keeping the ROM byte-for-byte close to the candidate above.

`TND64_480i_single8076_all_core_no_menu_sc64isv_hvionly_lowcave.z64`

- Base: `TND64_480i_single8076_all_core_no_menu.z64`
- MD5: `d324a80841416d57c33e64c17923be03`
- N64 CRC: `C32248EF F42057CC`
- Debug command: `sc64deployer.exe debug --isv 0x03FF0000 --no-writeback`
- Expected markers:
  - `TND:HVI1` - VI setup function returned; may repeat while the game is alive
- Emulator status: Gopher64 25 second smoke survived.

Do not use the old entry-debug ROMs first. Entry logging black-screened the baseline control, and the older no-entry build had a `DFB1` hook bug. The corrected all-hook baseline is `BASELINE_TND64_Expanded_sc64isv_noentry_v3_lowcave.z64`.

## Single-High Diagnostic Fallbacks

Use these only after the one-shot candidate has a clear result and a physical reset/power-cycle is available if the console wedged.

### A. Single + F/G, No H

`TND64_480i_single8076_mem_fg_core_no_menu.z64`

- Profile: `single8076_mem_fg_nodims`
- MD5: `2a89ae6923f51bf90233a3f8eeba303b`
- N64 CRC: `465E916B 18BA8FFB`
- Purpose: tests single-high framebuffer placement plus the two side words without the larger H VI-register rewrite.

### B. Single + F/G + H Width/Vsync

`TND64_480i_single8076_mem_fg_h_width_core_no_menu.z64`

- Profile: `single8076_mem_fg_h_width_nodims`
- MD5: `7a823ac83b4565636bbac08ee4350c8f`
- N64 CRC: `27D6916B 03F6FAD1`
- Purpose: isolates H words at `0x199B4`, `0x199D0` under the safer single-high framebuffer layout.

### C. Single + F/G + H Scale

`TND64_480i_single8076_mem_fg_h_scale_core_no_menu.z64`

- Profile: `single8076_mem_fg_h_scale_nodims`
- MD5: `741b19514189c642847d03336713a57d`
- N64 CRC: `275EA16F 8FF11505`
- Purpose: isolates H words at `0x19A24`, `0x19A60`, `0x19A64` under the safer single-high framebuffer layout.

### D. Single + F/G + H Origin

`TND64_480i_single8076_mem_fg_h_origin_core_no_menu.z64`

- Profile: `single8076_mem_fg_h_origin_nodims`
- MD5: `913e7ba3cff9a9e904fdc9dd0adef3f9`
- N64 CRC: `461F9710 4BA15C2E`
- Purpose: isolates H words at `0x19978`, `0x19980`, `0x19984`.
- Emulator status: Gopher64 visible smoke passed for 30 seconds.

### E. Single + F/G + H Origin + Width/Vsync

`TND64_480i_single8076_mem_fg_h_origin_width_core_no_menu.z64`

- Profile: `single8076_mem_fg_h_origin_width_nodims`
- MD5: `abe8ece07e0fc48000bd058c6ebd2c8a`
- N64 CRC: `3BDE9710 3B526C17`
- Purpose: isolates origin plus width/vsync without the H scale words.
- Emulator status: Gopher64 visible smoke passed for 30 seconds.

### F. Single + F/G + H Origin + Scale

`TND64_480i_single8076_mem_fg_h_origin_scale_core_no_menu.z64`

- Profile: `single8076_mem_fg_h_origin_scale_nodims`
- MD5: `c8e04cc802ff804376199fa9793f6acf`
- N64 CRC: `3E9EA710 19BEFF21`
- Purpose: isolates origin plus scale without the H width/vsync words.
- Emulator status: Gopher64 visible smoke passed for 30 seconds.

## Experimental Double-Buffer Fallback

Use this only after the single-high candidate has a clear result. It may be useful if the single-buffer candidate boots but flickers, tears, or still fails to show convincing 480i behavior.

`TND64_480i_split8030_8076_all_core_no_menu.z64`

- Profile: `split8030_8076_all_nodims`
- MD5: `6464d1b85aa7fc60d5a6fbf36fa71bf7`
- N64 CRC: `257D2E42 BCCC76EB`
- Purpose: tests a double-buffer layout with fb0 at `0x80300000-0x80395FFF` and fb1 at `0x8076A000-0x807FFFFF`, avoiding both the suspected `0x80400000` collision and the known `0x8070xxxx` constant area while keeping the full GE 480i H branch family.
- Emulator status: Gopher64 visible smoke passed for 30 seconds; Gopher64 input-driven smoke survived 76 seconds with 158 Start/A key taps; ares process smoke survived 30 seconds and stayed responsive.

The older width/scale-only split8030 fallback remains available as `TND64_480i_split8030_8076_mem_fg_h_width_scale_core_no_menu.z64` with MD5 `bd9f43cf6e42b4ee98bc519522d7c515`, but the full-H version above is now the better comparison if the single-buffer build boots but does not look right.

## Older Split Diagnostic Queue, Deprioritized

Only start this queue from a known-good EverDrive menu. If any step black-screens or locks, stop the hardware queue immediately and continue offline until a physical power-cycle is available.

### 1. Framebuffer Split Only

`TND64_480i_split8040_8076_core_no_menu_memonly.z64`

- Profile: `split8040_8076_mem_nodims`
- MD5: `37a44e96411ea6ffc8b9cc074acf0844`
- N64 CRC: `B0639EA7 853D10AA`
- Purpose: answers whether the split 0x80400000/0x8076A000 framebuffer relocation works on real hardware before adding donor VI side patches.

### 2. Split + F/G, No H

`TND64_480i_split8040_8076_mem_fg_core_no_menu.z64`

- Profile: `split8040_8076_mem_fg_nodims`
- MD5: `efc66caf4ae72c7b0922554fa2b5f4e2`
- N64 CRC: `B06381A7 853211F8`
- Purpose: tests the two single-word side patches without the larger H VI-register rewrite.

## Diagnostic Follow-ups

Use these only after the earlier steps have a clear result. If any candidate black-screens or locks, stop until a physical power-cycle is available.

### A. F/G + H Origin Bypass

`TND64_480i_split8040_8076_mem_fg_h_origin_core_no_menu.z64`

- Profile: `split8040_8076_mem_fg_h_origin_nodims`
- MD5: `cea03d3ec0fd3d1b065f9f32e6712178`
- N64 CRC: `AC63865E 97E831AA`
- Purpose: isolates H words at `0x19978`, `0x19980`, `0x19984`.

### B. F/G + H Width/Vsync

`TND64_480i_split8040_8076_mem_fg_h_width_core_no_menu.z64`

- Profile: `split8040_8076_mem_fg_h_width_nodims`
- MD5: `fab4087b34f8531c624263bcad1dbb34`
- N64 CRC: `4D4A99A6 B10F1ECD`
- Purpose: isolates H words at `0x199B4`, `0x199D0`.

### C. F/G + H Scale

`TND64_480i_split8040_8076_mem_fg_h_scale_core_no_menu.z64`

- Profile: `split8040_8076_mem_fg_h_scale_nodims`
- MD5: `39f88aab5bee95e1ad20a5412b852ebe`
- N64 CRC: `40E2A9A2 51BCDBA0`
- Purpose: isolates H words at `0x19A24`, `0x19A60`, `0x19A64`.

### D. F/G + H Origin + Width

`TND64_480i_split8040_8076_mem_fg_h_origin_width_core_no_menu.z64`

- Profile: `split8040_8076_mem_fg_h_origin_width_nodims`
- MD5: `1c096fa19b3cf9ee18584ad5b64f4c3d`
- N64 CRC: `5D439E5E 87FBFCBA`
- Purpose: combination diagnostic if origin plus width/vsync is suspected.

### E. F/G + H Origin + Scale

`TND64_480i_split8040_8076_mem_fg_h_origin_scale_core_no_menu.z64`

- Profile: `split8040_8076_mem_fg_h_origin_scale_nodims`
- MD5: `d8eb9d4a10fa007039a479511f66fa3d`
- N64 CRC: `5CE5AEA2 A517B0C0`
- Purpose: combination diagnostic if origin plus scale is suspected.

## If Step 1 Fails

If `split8040_8076_memonly` black-screens on real hardware, do not test side-patch variants yet. Treat the framebuffer placement or split-buffer code as the primary failure and move to a different memory layout. Also assume the console may be wedged until a physical power-cycle.

## If Step 1 Boots

If `split8040_8076_memonly` boots, use Step 2 next. If Step 2 boots but still does not look like 480i, continue through the H subchunk variants.
