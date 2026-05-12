# TND64 480i Next Hardware Queue

Date: 2026-05-08

## Current Hardware State

- 2026-05-11 playability reset:
  - User testing made the priorities explicit: gameplay first, pause/watch second, level intro/outro third, then dossier/mission menus, then front/title/gunbarrel/logos/demos.
  - The active console ROM is now the small in-game viewport centering canary:
    `artifacts/generated/game_h460_top10_current.z64`.
  - MD5: `892cbd5e8253e9cc3c6c4c4645bd69c0`; N64 CRC: `CD679836 961D35FD`.
  - It rolls away from the `menu_late_safe` / gunbarrel-front branch and changes only three normal gameplay viewport words on the known gameplay/watch baseline:
    `0xBB91C = 460`, `0xBB954 = 460`, `0xBBA80 = top 10`.
  - Goal: reduce in-game top/bottom flicker and CRT overscan while preserving the working 640-wide gameplay, correct reticle size, and acceptable watch scale.
  - Hardware sanity after upload: `diagnostics/captures/current/after_upload_game_h460_top10_wait10_20260511.png` shows TND credits output, so the direct upload booted.
  - Gopher evidence: `diagnostics/captures/contact_sheets/game_viewport_centering_input70_20260510.jpg` and `reports/smoke/smoke_game_viewport_centering_input70_20260510.json`.
  - Saturday/user-driven test focus for this ROM: Bazaar in-game fit, top/bottom flicker, dialogue/text boxes, countdown position, watch flicker, save/mission flow only as needed to reach gameplay, then Party crash/repro.
  - If `h460/top10` still runs too tall, the already-built `artifacts/generated/game_h440_top20_current.z64` is the next narrow crop candidate. If `h460/top10` regresses gameplay, roll back to `artifacts/generated/TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_reserve58000_core_no_menu.z64`.
  - Deprioritize gunbarrel and broad menu/front canaries until the ROM is playable beyond Bazaar.

- 2026-05-11 earlier current-best restore, now superseded by the playability reset above:
  - SC64 was back in direct-ROM mode with EEPROM 4k and the then-current best ROM restored:
    `artifacts/generated/gbslow_menu05_09_moving_post_20260511.z64`.
  - MD5: `739ae518dddfc423482a859b63e6f33e`; N64 CRC: `735E38D7 95D565A3`.
  - This supersedes `gamefulltop0_gbslow_shared_blitter_stock_texture_setup_20260511.z64` by adding the `menu05_09_safe` direct menu/front range and the post-matrix moving-barrel display-list suppression at `0x3C68C`.
  - Hardware cadence still matches the promoted slow/GE-like branch (`44.845s` first sustained red in the short capture; `44.978s` in the long no-input capture) and should be treated as the rollback target for title/front/menu canaries.
  - Evidence: `diagnostics/captures/contact_sheets/gbslow_menu05_09_moving_post_coldboot_20260511_sheet.jpg`, `diagnostics/captures/contact_sheets/gbslow_menu05_09_moving_post_gunbarrel_24_74_2fps_20260511.jpg`, `diagnostics/captures/contact_sheets/gbslow_menu05_09_moving_post_long_noinput_8s_20260511.jpg`, `diagnostics/captures/contact_sheets/gbslow_menu05_09_moving_post_long_gunbarrel_24_74_2fps_20260511.jpg`, and `reports/capture_cadence/motion_gbslow_menu05_09_moving_post_long_vs_short_20260511.json`.
  - `gamefulltop0_gbslow_texture_front_force_table0_20260511.z64` was uploaded and tested from hardware, then rejected and replaced with the current best. It forced the front/menu setup table selector to table0 but did not fix front/cast clipping and delayed/disturbed the gunbarrel (`49.449s` first sustained red).
  - `gamefulltop0_gbslow_texture_rle32_20260511.z64`, `gamefulltop0_gbslow_texture_rle48_20260511.z64`, and `gamefulltop0_gbslow_texture_rle64_20260511.z64` are Gopher/offline rejects. RLE32/48 underpower the barrel layer; RLE64 corrupts front/menu text.
  - `gamefulltop0_gbslow_texture_skip_menufb_20260511.z64`, `gamefulltop0_gbslow_texture_frontzbuf_width640_20260511.z64`, and `gamefulltop0_gbslow_texture_frontzbuf_height480_20260511.z64` are hardware rejects/non-promotes. `skip_menufb` preserved good cadence but did not improve composition; width-only zbuffer reproduced horizontal striping; height-only zbuffer preserved cadence but left the doubled aperture/front composition unchanged. The current-best ROM was restored to SC64 afterward.
  - Offline rejects after the moving-post promotion: `gbslow_menu05_09_moving_post_stock_rowcount_20260511.z64`, `gbslow_menu05_09_moving_post_stock_stride_20260511.z64`, and `gbslow_menu05_09_moving_post_stock_stripsteps_20260511.z64`. Do not upload these; stock row-count/stride reintroduce static in Gopher64, and stock strip-steps has no clear visual win.
  - Display-cast probes after the moving-post promotion are rejected/non-promoted. `gbslow_moving_post_displaycast_rects_20260511.z64` was the only hardware upload; it kept good gunbarrel cadence but blanked the no-input loop after the gunbarrel where the current-best branch continues into visible cast/credits. The text and rect+text display-cast variants are Gopher rejects because they push cast text off the right side. Evidence: `diagnostics/captures/contact_sheets/gbslow_displaycast_rects_coldboot_8s_labeled_20260511.jpg`, `diagnostics/captures/contact_sheets/gbslow_displaycast_rects_gunbarrel_24_74_2fps_20260511.jpg`, and `reports/capture_cadence/motion_gbslow_displaycast_rects_vs_moving_post_20260511.json`.
  - Current RDP/Gopher visual capture can be unreliable after the `gdigrab title=` changes; use process survival as a smoke only unless the contact sheet visibly contains real frames. Hardware GV-USB2 remains authoritative for title/front/gunbarrel visual checks.

- 2026-05-09 SC64 repo session:
  - The prior runtime-fixed no-entry baseline debug ROM black-screened on hardware and produced no ISV markers.
  - That result is now partially invalidated because the `DFB1` hook was found to overwrite original framebuffer-global setup instead of replaying it.
  - `scripts/build_sc64_isv_instrumented.py` now supports `--hooks` and uses a corrected trampoline for `DFB1`.
  - A later HVI-only baseline control also black-screened when the logger/trampoline cave was at ROM `0x331E0`.
  - Current theory: `0x331E0` is not guaranteed to be resident in RDRAM when early boot/video code runs on real hardware. The new builds use an early low cave at ROM `0x3CB0`.
  - SC64 was reset over USB and reports `Bootloader -> Menu from SD card`. Do not upload another ROM while the user is away.
  - Next hardware step is a low-cave baseline control, not a 480i candidate.
- 2026-05-09 low-cave HVI baseline follow-up:
  - From a visible SC64 menu, `BASELINE_TND64_Expanded_sc64isv_hvionly_lowcave.z64` was uploaded and launched after a real reset.
  - The ROM reached visible TND title/credits output on GV-USB2, so the low-cave HVI trampoline no longer appears to black-screen baseline TND.
  - The SC64 ISV listener still started/stopped immediately, and dumping `0x03FF0000` showed no `TND:*` marker.
  - Treat the low-cave trampoline mechanics as visually validated on baseline, but do not trust SC64 ISV marker capture yet.
  - SC64 boot configuration was reset over USB to `Bootloader -> Menu from SD card`; a real reset/power-cycle is still needed before another upload because ROM write remains disabled while the ROM is running.
- 2026-05-09 dim0 visual hardware result:
  - From a confirmed SC64 menu, `TND64_480i_single8076_all_dim0_core_no_menu.z64` was uploaded and launched after a real reset.
  - It stayed pure black through 60 seconds on GV-USB2.
  - SC64 boot configuration was reset over USB afterward, but a real reset/power-cycle is still needed before another upload because ROM write remains disabled.
  - A later user reset did not recover visible video; GV-USB2 still captured pure black and SC64 still reported `ROM write: Disabled`.
  - Do not retry `single8076_all_dim0` first. Continue offline and isolate whether the direct dimension word, the single-buffer layout, or the full H VI-register family is the hardware failure point.
- 2026-05-09 offline decomp follow-up:
  - The user-tested no-dims single-all visual candidate did not patch direct gameplay dimension words at `0x4F354` and `0x4F35C`.
  - Those words were still `320x240` and `440x330`, which matches the reported aliased Bond-hand symptom.
  - A full two-word dim-aware candidate patched both words to `640x480` and survived process smokes, but later visual capture stayed black in Gopher64.
  - One-word tests on the single-buffer full-H branch showed `0x4F354 -> 640x480` (`single8076_all_dim0`) rendered in Gopher64, while `0x4F35C -> 640x480` (`single8076_all_dim1`) stayed black.
  - Real hardware then black-screened `single8076_all_dim0`, and smaller `dim0_only` / `dim1_only` probes both stayed black in Gopher64 even without framebuffer relocation.
  - The `FGH only` probe, which keeps stock direct dimensions and framebuffer placement while applying F/G/H VI-side words, rendered in Gopher64.
  - Hardware later black-screened `FGH only` through 60 seconds, so it is no longer a candidate. Split F/G/H into smaller probes before another hardware upload.
  - Smaller `F only`, `G only`, `FG only`, `H only`, `H origin only`, `H width only`, and `H scale only` probes all rendered in Gopher64 80 second visual/input smokes.
  - Hardware black-screened `H only` through 60 seconds after a physical reset launched the queued ROM.
  - Kasa smart-plug power cycling is useful for recovery to the SC64 menu. A later clean Kasa cycle did launch a queued `Bootloader -> ROM` target, so earlier notes saying it did not launch may have been affected by Kasa UI/operator confusion.
  - `H origin only` produced unstable/noisy video through 60 seconds on hardware, not a pure black screen. This makes the H origin/control-flow bypass independently hardware-sensitive.
  - `H width only` launched from a clean Kasa power cycle and produced visible TND logo/rating/license/intro output through 60 seconds, but with severe lower-screen horizontal banding and bad vertical placement. It is not a valid 480i fix, but it is not a pure-black failure.
  - `H scale only` launched from a clean Kasa power cycle and stayed pure black through 60 seconds.
  - The SC64 menu is currently visible again after `sc64deployer reset` plus Kasa power cycle, and SC64 reports `ROM write: Enabled`.
  - The independent H subfamily checks are complete: origin destabilizes/noises video, width/vsync renders with severe corruption, and scale black-screens. Stop blind H-combination uploads until a coherent TND-specific VI/mode/framebuffer patch is derived.
- 2026-05-10 split8030 dim0 success:
  - `TND64_480i_split8030_8076_all_dims_core_no_menu.z64` survived as a process but visually captured black in Gopher64, so it was rejected.
  - `TND64_480i_split8030_8076_all_dim0_core_no_menu.z64` rendered a live level scene in Gopher64 and booted on real N64 with SC64 `upload --direct` plus a Kasa power cycle.
  - Hardware output was visible over the GV-USB2 S-Video path through at least 180 seconds: Rareware logo, intro silhouettes/credits, and title branding all rendered.
  - `TND64_480i_split8030_8076_all_dim1_core_no_menu.z64` stayed black in Gopher64 visual capture and was not uploaded.
  - Current working candidate: `artifacts/generated/TND64_480i_split8030_8076_all_dim0_core_no_menu.z64`, MD5 `4fd6d3b38b50c2ec0a1bdd110598516c`, N64 CRC `25FD2E62 AF703620`.
  - Verified IPS patch: `artifacts/generated/TND6480i_split8030_8076_all_dim0_from_baseline_tnd.ips`, MD5 `d08906f5353b6b0dd2d7937f00c09e58`.
  - SC64 was restored afterward to `Bootloader -> Menu from SD card` with `ROM write: Enabled`.
- 2026-05-10 overnight SC64/Kasa follow-up:
  - Added `scripts/hardware/cycle_kasa_n64_buttons.ps1`, which uses the Kasa Smart Control WinForms On/Off button handles directly instead of mouse coordinates.
  - The helper successfully power-cycled the N64 and recovered a visible SC64 menu with `ROM write: Enabled`.
  - Hardware canary `TND64_480i_title640draw_tndstride430_nogameplay_reserve58000_core_no_menu.z64` reached the Rare splash, then stuck on a static narrow vertical-bar image for 180 seconds. Reject.
  - Hardware canary `TND64_480i_tndrect508src430_gameplayxy_tnddefaultwidthheight480i_reserve58000_core_no_menu.z64` used the corrected active TND title RLE source stride `508`, but still stuck on a static vertical-bar image for 180 seconds. Reject.
  - SC64 was restored afterward to `Bootloader -> Menu from SD card`; GV-USB2 shows the SC64 menu, and `sc64deployer info` reports `ROM write: Enabled`.
- 2026-05-10 later unattended hardware follow-up:
  - From a confirmed SC64 menu, `TND64_480i_gunbufBE200_gameplayxy_tnddefaultwidthheight_reserve58000_core_no_menu.z64` was uploaded with EEPROM 4k save type and launched by Kasa power cycle.
  - It booted and looped the title/gunbarrel/credits path for 180 seconds without the rejected vertical-bar failure, but it did not auto-enter a gameplay demo.
  - Cadence was still stock-like: high-red detector intervals were `4.771s`, `4.771s`, and `4.838s` versus GE 480i reference `7.908s`.
  - From a confirmed SC64 menu, `TND64_480i_frontbufsizes_gameplayxy_tnddefaultwidthheight_reserve58000_core_no_menu.z64` was uploaded next. It also booted and looped title/gunbarrel/credits for 165 seconds without entering gameplay.
  - Its high-red detector intervals were `4.705s` and `4.805s`, again matching the known width/height branch rather than GE 480i.
  - SC64 was restored afterward to `Bootloader -> Menu from SD card`; GV-USB2 shows the SC64 menu, and `sc64deployer info` reports `ROM write: Enabled`.
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

There is still no proven-good 480i hardware patch. The current live hardware candidate is the width+height/no-top viewport probe. It keeps the working split framebuffer package, the first direct dimension word, the title allocation/reserve experiment, the GE 480i `getWidth320or440()` / `getHeight330or240()` return values, and changes only the normal player viewport width/height path to GE-style width `640` and height `440`. It deliberately leaves camera/intro viewport tops and the normal top offset alone.

Only upload it from a visible SC64 menu or another known-good live video state, with SC64 reporting `ROM write: Enabled`, and use EEPROM 4k save type if the launcher asks.

`TND64_480i_gameplayxy_tnddefaultwidthheight480i_reserve58000_core_no_menu.z64`

- Path: `artifacts/generated/TND64_480i_gameplayxy_tnddefaultwidthheight480i_reserve58000_core_no_menu.z64`
- Profile: `split8030_8076_all_dim0_gameplayxy_tnddefaultwidthheight480i`, plus title allocation `0x96040` and intro reserve `0x58000`
- MD5: `a17be68fd0eeb2e88bfd2d316e4b40db`
- N64 CRC: `25FDE5A6 EAB65D42`
- IPS patch from clean baseline: `artifacts/generated/TND6480i_gameplayxy_tnddefaultwidthheight480i_reserve58000_from_baseline_tnd.ips`
- IPS MD5: `1839e41e019e0c25db1f6321e0867f4a`
- Verification: Gopher64 75 second input smoke survived and captured a full watch/player viewport.
- Hardware status: uploaded to SC64 and launched on real N64 on 2026-05-10. Startup/cast capture succeeded, but it did not auto-enter a level within 75 seconds; controller-side gameplay test is pending.

Why this is first in line: the previous `tndfullscreen` hardware probe fixed save-slot freezes and expanded the view out of the upper-left, but forcing raw `640x480` and camera top `0` created the blue split/camera-path corruption. The default-view-only probe still had blue split on hardware, so the current probe removes the `top 20` change and keeps only normal width/height.

Do not retest these first:

- `TND64_480i_single8076_all_dim0_core_no_menu.z64` - black-screened on real hardware through 60 seconds.
- `TND64_480i_fghonly_core_no_menu.z64` - black-screened on real hardware through 60 seconds.
- `TND64_480i_dim0only_core_no_menu.z64` / `TND64_480i_dim1only_core_no_menu.z64` - both black-screened in Gopher64 visual capture.
- `TND64_480i_split8030_8076_all_dim0_gameplay480i_reserve58000_core_no_menu.z64` - booted on hardware and made progress, but save slots 1/3/4 froze, gunbarrel was still not 480i, and Bazaar/watch/report composition was badly corrupted.
- `TND64_480i_gameplayxy480i_reserve58000_core_no_menu.z64` - booted on hardware and preserved cleaner watch text, but rendered the game/watch only in the upper-left quadrant.
- `TND64_480i_gameplayxy_tndfullscreen480i_reserve58000_core_no_menu.z64` - booted on hardware; all save slots worked, but gunbarrel was not 480i and gameplay had blue/split viewport corruption.
- `TND64_480i_gameplayxy_tnddefaultgeview480i_reserve58000_core_no_menu.z64` - booted on hardware; menu/briefing composition was sane, but gameplay/demo still showed the blue split with a narrow world band.
- `TND64_480i_gameplayxy_tndgeview480i_reserve58000_core_no_menu.z64` - Gopher64 reintroduced blue split/camera-path corruption; do not upload before the default-view-only probe.
- `TND64_480i_gameplayxy_tndcamerageview480i_reserve58000_core_no_menu.z64` - Gopher64 still showed the player/watch state in the upper-left mini-frame.
- `TND64_480i_gunbufBE200_gameplayxy_tnddefaultwidthheight_reserve58000_core_no_menu.z64` - booted on hardware, but the gunbarrel cadence matched the known stock-like width/height branch.
- `TND64_480i_frontbufsizes_gameplayxy_tnddefaultwidthheight_reserve58000_core_no_menu.z64` - booted on hardware, but the gunbarrel cadence matched the known stock-like width/height branch.
- `TND64_480i_split8030_8076_all_dim0_frontgameplay480i_core_no_menu.z64` - severe striped/corrupted hardware capture.
- `TND64_480i_split8030_8076_all_dim0_frontres_gameplay480i_core_no_menu.z64` - severe striped/corrupted hardware capture.
- Broad GE safe title/front transplants - emulator smoke can pass while title/cast output corrupts.
- Any `K_rectloop_*` / `K_title_draw_*` title-blitter candidate - both wrong-stride and corrected-stride hardware canaries freeze the shared title blitter into static vertical bars before the gunbarrel.

Most informative next step:

Controller-side hardware test should return to the best non-title-blitter branch, not the rejected title/rectloop probes. If a human is available, retest or refine `TND64_480i_gameplayxy_tnddefaultwidthheight480i_reserve58000_core_no_menu.z64`: check save slots 1-4, gunbarrel cadence, level intro, Bazaar/Bond hand composition, watch/pause text, and whether normal gameplay fills the screen without the blue split. Expect gunbarrel cadence to remain a separate follow-up problem.

- Do not upload another H-family combination just because it renders in Gopher64.
- Compare TND's libultra `__osViSwapContext` and higher-level `fr.c`/`VideoSettings` flow against GoldenEye 480i and/or `n64decomp/007`.
- The H-offset code itself is aligned with GE stock, so the next target is likely coherency between mode tables, framebuffer dimensions, direct gameplay dimensions, and the GE 480i libultra behavior.
- The GE 480i `video_related_8` frame stride group around `0x46B4-0x46F0` collides with the current split-buffer selector. Do not directly transplant GE's `0x46C8` stride math; derive a split-buffer-aware equivalent that preserves `cfb_16[0] = 0x80300000` and `cfb_16[1] = 0x8076A000` while matching the GE 480i mode/framebuf handoff.
- The `menu_only` compressed-main ranges currently overflow the 1172 stream slot (`0x11BC8 > 0xFDA7`), so pause/menu text correction needs a separate space-management pass.
- Optional hardware sanity check after offline analysis: run `F only`, `G only`, or `FG only` to confirm the non-H side patches are not independently fatal, but these are not expected to prove 480i on their own.

Baseline controls already run:

- `BASELINE_TND64_Expanded_sc64isv_hvionly_lowcave.z64` reached visible TND output on hardware, but ISV marker capture was not validated.
- `BASELINE_TND64_Expanded_hvijump_lowcave.z64` remains a low-cave visual-only control if the trampoline itself needs another sanity check.

## SC64 Instrumented Debug Candidate

Use this on SummerCart64 when debug visibility matters more than keeping the ROM byte-for-byte close to the candidate above.

Deprecated dim-aware payload:

`TND64_480i_single8076_all_dim0_core_no_menu_sc64isv_hvionly_lowcave.z64`

- Base: `TND64_480i_single8076_all_dim0_core_no_menu.z64`
- MD5: `8e1c0d5b2b8b276af8558602d06a80d5`
- N64 CRC: `C6224ECF 7FEB4471`
- Debug command: `sc64deployer.exe debug --isv 0x03FF0000 --no-writeback`
- Expected markers:
  - `TND:HVI1` - VI setup function returned; may repeat while the game is alive
- Emulator status: Gopher64 25 second smoke survived and printed 737 `TND:HVI1` markers.
- Hardware status: matching visual ROM black-screened through 60 seconds. Do not upload this debug payload first.

Older no-dims debug payload, superseded for visual-quality testing:

`TND64_480i_single8076_all_core_no_menu_sc64isv_hvionly_lowcave.z64`

- Base: `TND64_480i_single8076_all_core_no_menu.z64`
- MD5: `d324a80841416d57c33e64c17923be03`
- N64 CRC: `C32248EF F42057CC`
- Emulator status: Gopher64 25 second smoke survived.

Full-dims debug payload, not first choice because the matching visual ROM captures black in Gopher64:

`TND64_480i_single8076_all_dims_core_no_menu_sc64isv_hvionly_lowcave.z64`

- Base: `TND64_480i_single8076_all_dims_core_no_menu.z64`
- MD5: `05c4e67a8b293eb10208ff396afbffb2`
- N64 CRC: `C5E24FCF 6BB1D73D`
- Emulator status: Gopher64 25 second smoke survived and printed 740 `TND:HVI1` markers.

Do not use the old entry-debug ROMs first. Entry logging black-screened the baseline control, and the older no-entry build had a `DFB1` hook bug. The corrected all-hook baseline is `BASELINE_TND64_Expanded_sc64isv_noentry_v3_lowcave.z64`.

## Deprecated Dim-Aware Visual Candidate

This was the most meaningful visual candidate before hardware testing because it directly addressed the observed "boots but Bond's hand is still aliased" symptom without applying the second direct dimension word that black-screens in Gopher64. It has now failed on real hardware and should not be retried first.

`TND64_480i_single8076_all_dim0_core_no_menu.z64`

- Profile: `single8076_all_dim0`
- MD5: `ad441669291605a3fd551b51c68bb195`
- N64 CRC: `CE5E1EF0 26DDA6CD`
- Difference from `TND64_480i_single8076_all_core_no_menu.z64`: only the first direct dimension word at `0x4F354` is now `0x028001E0` (`640x480`); `0x4F35C` remains stock `0x01B8014A` (`440x330`).
- Emulator status: Gopher64 80 second input-driven visual capture rendered, with window mean luma `122.22`; ares 30 second process smoke survived. The sibling `single8076_all_dim1` and full `single8076_all_dims` builds stayed black in visual capture.
- Hardware status: black screen through 60 seconds on real N64. Do not retry first.

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

Dim-aware double-buffer fallback:

`TND64_480i_split8030_8076_all_dims_core_no_menu.z64`

- Profile: `split8030_8076_all_dims`
- MD5: `cce443d766bd681a511f7d18bb95b657`
- N64 CRC: `278D2E7E C311ADE7`
- Purpose: same split8030 memory layout as above, plus the direct `640x480` gameplay dimension words.
- Emulator status: Gopher64 input-driven smoke survived 80 seconds with 266 Start/A taps; ares process smoke survived 30 seconds and stayed responsive.
- Caution: the single-buffer full-dims visual build stayed black in Gopher64, so full-dims split builds should not jump ahead of the one-word `dim0` branch.
- Hardware status: not uploaded.

Matching HVI-only SC64 debug build:

`TND64_480i_split8030_8076_all_dims_core_no_menu_sc64isv_hvionly_lowcave.z64`

- MD5: `1d7399907d353fe12266f9120541b221`
- N64 CRC: `37FE4249 55E07F56`
- Expected marker: `TND:HVI1`
- Emulator status: Gopher64 25 second smoke survived and printed 755 `TND:HVI1` markers.
- Hardware status: not uploaded.

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

## Earlier Loaded Probe, 2026-05-10

Recent hardware feedback on the latest 2026-05-10 candidate:

- In-game rendering looks good overall and is down to flickering rather than the earlier top-rectangle rendering failure.
- Level-select text is misaligned.
- Remaining major work buckets are gunbarrel, opening credits, menu size/text/layout, intro cutscene/gameplay polish, and pause menu/watch layout.

Do not discard the current gameplay viewport work while testing front/menu fixes.

The last gameplay-oriented SC64 direct-boot candidate was:

```text
artifacts/generated/TND64_480i_frontbuf_gunbarrel_padorigin_gameplayxy_tnddefaultwidthheight480i_virtualfb_reserve58000_core_no_menu.z64
MD5: 8595e4f1416fdca1bf96ad86c8907d6f
N64 CRC: 2FB6A3F7 556AA840
```

Purpose:

- Replaces the stretched 640x430 gunbarrel source with a 640x430 padded canvas containing the original 440x299 source at origin.
- Restores the file-select backdrop call, so this should be tested specifically for the former slot 1/3/4 freeze.
- Keeps the same `frontbuf`, virtual framebuffer, and gameplay width/height patch set as the previous hardware candidate that had working reticle/HUD size.

Controller-side test order:

1. Confirm whether the folder background is visible.
2. Open save slots 1, 2, 3, and 4.
3. Watch the gunbarrel for duplicate aperture/swiss-cheese artifacts.
4. Enter a level and check the known blue skybox/world-band behavior.
5. Open pause/watch and compare text placement to enhanced480i.
6. On the mission/level select screen, compare text alignment against the prior physicalfb baseline.

## Earlier Gameplay/Pause Candidate History

The mission-text candidate below was rejected after hardware testing because it made level text alignment worse:

`TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_missiontext_reserve58000_core_no_menu.z64`

- MD5: `c4d0c2b56ae5fab0617521cb0978147e`
- N64 CRC: `CD679B28 2D5C5F47`
- Purpose: preserve the latest good in-game viewport and test only the four GE 480i mission-select text/grid offset words at ROM offsets `0x43148`, `0x43150`, `0x431E0`, and `0x431E4`.
- Gopher64 smoke: `reports/smoke/smoke_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_missiontext_input_until52_20260510.json`.
- SC64 upload: completed in direct boot mode with EEPROM 4k after a Kasa power cycle.

The current best gameplay/pause fallback is:

`TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_reserve58000_core_no_menu.z64`

- MD5: `17d4ea3194d02d5ea121b1e42aa59469`
- N64 CRC: `CD6799DE DAD61991`
- Purpose: preserve the best current camera-height-only gameplay baseline and test whether the remaining top/bottom gameplay flicker is caused by the non-camera default view still being `640x440` at top `20`.
- Direct overlay from the previous `camfullheight` baseline: `gameplayxy_tnddefaultwidthheight480fulltopzero480i_only`, effectively changing only `0xBB91C`, `0xBB954`, and `0xBBA80` from that baseline.
- Gopher64 smoke: `reports/smoke/smoke_physicalfb_camfullheight_gamefulltop0_input_until52_20260510.json`.
- SC64 upload: completed in direct boot mode with EEPROM 4k after a Kasa power cycle. It was restored to the console again after two rejected gunbarrel workload probes.
- Hardware result: promoted. The user verified the pause menu is good, and in-game appears slightly more stable than `camfullheight`.
- Hardware test focus: keep this loaded as the current best gameplay/pause baseline. Remaining work should target gunbarrel/opening credits/menu/intro without regressing this viewport behavior.

Rejected 2026-05-10 gunbarrel workload probes from this baseline:

- `TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_gunwork259f4_reserve58000_core_no_menu.z64`, MD5 `119710751ac49ec46e95949001fe3fd0`. Booted, but bottom/source workload padding caused obvious title/gunbarrel artifacts.
- `TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_gunwork259f4right_reserve58000_core_no_menu.z64`, MD5 `ce7d9e8415b36c56d2d1585db418cb79`. Booted, but right-side workload padding still produced stray top-row garbage and a misframed gunbarrel.

The N64 previously had this SC64 direct-boot candidate loaded:

`TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_gunsplit259f4_reserve58000_core_no_menu.z64`

- MD5: `3f70b554d8363112d1cc03e7cf53a62c`
- N64 CRC: `CD6790DE 0FA4B3BD`
- Purpose: preserve the exact decoded pad-origin gunbarrel bitmap and inflate only the encoded RLE run structure to test whether the GE-like cadence can be recovered without visible pixel padding.
- Gopher64 smoke: `reports/smoke/smoke_gunsplit259f4_input_until52_20260510.json`.
- Hardware capture: `diagnostics/captures/videos/gunsplit259f4_powercycle_startup_20260510.mp4`, contact sheet `diagnostics/captures/contact_sheets/gunsplit259f4_powercycle_startup_20260510_sheet.jpg`.
- Hardware status: superseded. Later title-asset testing left the console in a bad gameplay state, so the N64 was recovered to the `gamefulltop0` fallback.

Earlier 2026-05-11 gunbarrel/menu branch:

`gbslow_menu05_09_moving_post_20260511.z64`

- MD5: `739ae518dddfc423482a859b63e6f33e`
- N64 CRC: `735E38D7 95D565A3`
- SC64 state: direct boot, EEPROM 4k.
- Base: the `gamefulltop0` gameplay/pause fallback below.
- Added direct ingredients: case-1 gunbarrel X decrement `3.625f` at `0x3DF04/0x3DF08`, stock TND title/sniper texture setup at `0x4FDEC`, `0x4FDFC`, `0x4FE34`, `0x4FE3C`, `0x4FE44`, and `0x4FF00`, the safe `0x403DC:0x45138` menu/front direct range, and post-matrix moving-barrel display-list suppression at `0x3C68C`.
- Hardware result at the time: promoted for gunbarrel cadence. It was later superseded by the 2026-05-11 playability reset because user testing showed broad menu/front regressions and the gameplay path still needed priority attention.
- Evidence: `diagnostics/captures/contact_sheets/gbslow_menu05_09_moving_post_gunbarrel_24_74_2fps_20260511.jpg`, `diagnostics/captures/contact_sheets/gbslow_menu05_09_moving_post_long_noinput_8s_20260511.jpg`, `diagnostics/captures/contact_sheets/gopher_gbslow_menu05_09_moving_post_input_20260511.jpg`, and `reports/capture_cadence/motion_gbslow_menu05_09_moving_post_long_vs_short_20260511.json`.

Do not keep this candidate loaded for current gameplay work. It is reference material for later title/front research only. For the active hardware line, use the `h460/top10` playability canary at the top of this document, then roll back to the previous gameplay/pause fallback if a new gameplay probe corrupts the in-game path:

`TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_reserve58000_core_no_menu.z64`

- MD5: `17d4ea3194d02d5ea121b1e42aa59469`
- N64 CRC: `CD6799DE DAD61991`
- SC64 state: direct boot, EEPROM 4k when it was the active fallback.
- Restore capture: `diagnostics/captures/after_restore_gamefulltop0_return_wait8_20260510.png`.
- Fresh hardware reference clip: `diagnostics/captures/videos/gamefulltop0_restored_reference_startup_20260510.mkv`, contact sheet `diagnostics/captures/contact_sheets/gamefulltop0_restored_reference_startup_20260510_sheet.jpg`.
- User-driven in-game flicker evidence after return: `diagnostics/captures/current_state_user_back_20260510_1838.png`.
- Clean neutral-start title/gunbarrel reference after Kasa power cycle: `diagnostics/captures/videos/gamefulltop0_neutral_start_recheck_20260510_1840.mkv`, contact sheet `diagnostics/captures/contact_sheets/gamefulltop0_neutral_start_recheck_labeled_20260510_1840.jpg`, cadence report `reports/capture_cadence/motion_gamefulltop0_neutral_recheck_20260510_1840.json`.
- Restored again after rejecting `frontzbuf`: `diagnostics/captures/current/after_restore_gamefulltop0_after_frontzbuf_reject_wait8_20260510.png`.
- Restored again after rejecting `flbox`: `diagnostics/captures/current/after_restore_gamefulltop0_after_flbox_reject_20260510.png`.
- Restored again after the gunbarrel slow-timing/color canaries: `diagnostics/captures/current/after_restore_fallback_from_gunbarrel_slow_tests_20260510.png`.
- Restored again after the alt-640 sniper blitter canary: `diagnostics/captures/current/after_restore_fallback_from_alt640_blitter_20260511.png`.
- Do not treat `gamefulltop0_coldboot_reference_20260510.mkv` as pure no-input timing evidence; it includes user-driven progress to gameplay.

Do not upload these newly rejected title/gunbarrel probes:

- `TND64_480i_gamefulltop0_ge480i_titleasset_exact_20260510.z64`, MD5 `c48310588beb3ac33373ca378c27e902`. It boots, but hardware gameplay later showed persistent split/corrupt display state.
- `TND64_480i_gamefulltop0_ge480i_titleasset_backdrop_*_20260510.z64`. Gopher64 36-second visual comparison rejected the backdrop skip/scale/translate family; the sheet is `diagnostics/captures/contact_sheets/backdrop_matrix_gopher36_20260510.jpg`.
- `TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_frontzbuf_reserve58000_core_no_menu.z64`. It boots, but GV-USB2 hardware retest showed heavy horizontal striping in the title/credits path and no useful gunbarrel cadence improvement. Evidence: `diagnostics/captures/contact_sheets/frontzbuf_retest_powercycle_labeled_20260510.jpg` and `reports/capture_cadence/motion_frontzbuf_retest_vs_refs_20260510.json`.
- `flbox.z64` / `TND64_480i_gamefulltop0_frontbox_cluster_safe_20260510.z64`. It changes only five safe front text-box constants and booted on hardware, but the credits/gunbarrel/front text remained materially unchanged. Evidence: `diagnostics/captures/contact_sheets/frontbox_noinput_gopher_20260510.jpg`, `diagnostics/captures/contact_sheets/flbox_powercycle_startup_20260510_sheet.jpg`, and `diagnostics/captures/contact_sheets/flbox_live_followup_20260510_sheet.jpg`.

Do not upload the new front-layout split candidates yet:

- `fl43a.z64`, `fl460.z64`, `flflt.z64`, `fly.z64`, `fl4aaa.z64`, `flgrid.z64`, `fl43a460.z64`, `flsafe.z64`.
- They all survived Gopher64 no-input startup, but none clearly fixed front text/layout. `flgrid` is the weakest from input-smoke behavior and should not be a first hardware candidate.
- Evidence: `diagnostics/captures/contact_sheets/layout_subclusters_gopher_20260510.jpg`, `diagnostics/captures/contact_sheets/layout_flsafe_input_gopher_20260510.jpg`, `diagnostics/captures/contact_sheets/layout_individual_input_gopher_20260510.jpg`.

SC64 diagnostic caution:

- The current HVI diagnostic ROM booted visually, but SC64 data-buffer dumps did not contain the expected words. Do not rely on the direct-store SC64 diagnostic path until it is reworked around a DMA/USB-style write.
- The USB-C cable is not the current blocker: SC64 upload, `info`, and raw `CMDv` serial probing all work. Replacing the cable is only worth revisiting if uploads or `sc64deployer info` become intermittent.
- `gamefulltop0_hlimit_current_20260510.z64` is now hardware-rejected as a gunbarrel/title fix. It changes only the title/menu height limit at `0x46F18`; it booted and looped, but the double aperture remained and red timing stayed stock-like (`40.307s` vs fallback `40.340s`). Evidence: `diagnostics/captures/contact_sheets/hlimit_current_gunbarrel_24_60_2fps_20260510.jpg` and `reports/capture_cadence/motion_hlimit_current_vs_helper_fallback_20260510.json`.
- Early title-layer skip canaries now exist and process-smoke in Gopher64. Do not upload them as a batch. The narrow `gamefulltop0_skip_case1_backdrop_20260510.z64` hardware canary booted and looped but did not show a compelling improvement. The wider `gamefulltop0_skip_cases1_3_backdrop_20260510.z64` coldboot canary also left the double white aperture / stock-like gunbarrel behavior visible. The complementary `gamefulltop0_skip_cases1_3_sniper_20260510.z64` canary is rejected as a functional patch because it strands the intro on a white crescent and never reaches the red/title progression. The current fallback has been restored.
- Sniper/RLE final-argument canaries have now been tested and rejected as fixes. Divisor probes (`gamefulltop0_sniper_div640_20260510.z64`, `gamefulltop0_sniper_div960_20260510.z64`, `gamefulltop0_sniper_div2560_20260510.z64`) preserved the paired aperture and stock-like timing. Constant-x probes (`gamefulltop0_sniper_x0_20260510.z64`, `gamefulltop0_sniper_xleft160_20260510.z64`, `gamefulltop0_sniper_xright160_20260510.z64`) visibly separated the RLE slice from the moving gunbarrel layer, proving this is a two-layer composition issue. Do not keep testing simple final-x shifts; target draw order/state/source selection around `insert_sniper_sight_eye_intro`.
- Internal RLE / moving-barrel display-list canaries were also tested. `gamefulltop0_sniper_internal_rle_skip_20260510.z64` bypasses the inner `sub_GAME_7F007CC8` call and largely removes the doubled RLE barrel, but removes too much art and shifts red early (`38.172s` vs fallback `40.340s`). `gamefulltop0_moving_skip_prebarrel_20260510.z64`, `gamefulltop0_moving_skip_postbarrel_20260510.z64`, and `gamefulltop0_moving_skip_bothbarrels_20260510.z64` trim early paired-dot clutter but keep stock-like red timing (`40.440s`, `40.474s`, `40.407s`). Next candidates should rewrite/mask/retime the RLE blit path, not globally skip either layer.
- Additional sniper/RLE canaries are now rejected as final candidates. `gamefulltop0_skip_case1_sniper_20260510.z64` also strands the intro on a small crescent and never reaches sustained red. RLE end-color canaries (`gamefulltop0_sniper_rle_endcolor0_20260510.z64`, `gamefulltop0_sniper_rle_endcolor32_20260510.z64`, `gamefulltop0_sniper_rle_endcolor128_20260510.z64`) show that dimming the RLE ramp can hide the doubled rifling, but it strips too much art at low values and does not alter stock-like red timing (`40.307s`, `40.474s`, `40.507s` vs fallback `40.340s`). Use color gating only as part of a more selective/per-state fix.
- Gunbarrel case-1 timing canaries are tested. `gamefulltop0_gunbarrel_case1_slow3625_20260510.z64` proves the GE-like slowdown can be mimicked by changing the case-1 `g_TitleX` decrement from the stock `5.8183274f` load to `3.625f` (`45.078s` first sustained red), but the double RLE barrel remains. `gamefulltop0_gunbarrel_slow3625_endcolor64_20260510.z64` and `gamefulltop0_gunbarrel_slow3625_endcolor96_20260510.z64` preserve slow timing (`45.045s` and `44.745s`) but only underpower/dim the miscomposited barrel. Keep the timing patch as a possible later ingredient; do not keep testing color-only variants as final candidates.
- `gamefulltop0_sniper_call_alt640_blitter_20260511.z64` is hardware-rejected as a final patch. It changes only `0x3C8A4` from the active sniper wrapper's call to `sub_GAME_7F01B240` into a call to adjacent `sub_GAME_7F01B6E0`. It boots and loops, proving a callsite-specific blitter path can be explored without the old global title-blitter vertical-bar freeze, but the raw sibling routine produces a large magenta/pink duplicate barrel and stock-like/early red timing (`39.873s`). Evidence: `diagnostics/captures/contact_sheets/sniper_call_alt640_blitter_gunbarrel_24_74_2fps_20260511.jpg` and `reports/capture_cadence/motion_sniper_call_alt640_blitter_vs_refs_20260511.json`.
- Shared-blitter rollback matrix: keep only `gamefulltop0_gbslow_shared_blitter_stock_texture_setup_20260511.z64` as promoted. The row/stride/full-stock variants are emulator-rejected because they reintroduce horizontal garbage/static. The no-op menu-1172 overlay showed the current branch already matches GE enhanced 480i for the compressed-main menu ranges; remaining menu/front issues are in direct/full-ROM state and layout callsites.
- Front-layout 2026-05-11 matrix: do not upload `fl43a`, `fl460`, `fly`, `fl4aaa`, `fl43a_460`, `flsafe_cluster`, or `front_height_limit` from the `gbslow_texture` branch. Gopher64 sheets show no clear winner; `fl460`, `fl4aaa`, and combined clusters tend to stay boxed/top-left or otherwise worsen intro/gameplay framing. Evidence: `diagnostics/captures/contact_sheets/gopher_gbslow_texture_frontlayout_matrix_20260511.jpg`.
- Front microprobe 2026-05-11 results: do not promote `gamefulltop0_gbslow_texture_skip_menufb_20260511.z64`, `gamefulltop0_gbslow_texture_frontzbuf_width640_20260511.z64`, or `gamefulltop0_gbslow_texture_frontzbuf_height480_20260511.z64`. Evidence: `diagnostics/captures/contact_sheets/gbslow_texture_skip_menufb_coldboot_20260511_sheet.jpg`, `diagnostics/captures/contact_sheets/gbslow_texture_frontzbuf_width640_coldboot_20260511_sheet.jpg`, `diagnostics/captures/contact_sheets/gbslow_texture_frontzbuf_height480_coldboot_20260511_sheet.jpg`, and the matching `reports/capture_cadence/motion_gbslow_texture_*_vs_refs_20260511.json` reports.
- Display-cast 2026-05-11 results: do not upload `gbslow_moving_post_displaycast_iface_20260511.z64`, `gbslow_moving_post_displaycast_rects_20260511.z64`, `gbslow_moving_post_displaycast_text_20260511.z64`, `gbslow_moving_post_displaycast_rects_text_20260511.z64`, or `gbslow_moving_post_displaycast_iface_rects_text_20260511.z64` as next canaries. `displaycast_rects` was hardware-rejected because it blanked after the gunbarrel despite preserving slow cadence; text variants are offline rejects.

The previous `camfulltop0` probe was rejected after hardware feedback: it made the level intro move more than it should and did not fix the smaller-rectangle render.

The previous `camfullheight` probe is the best gameplay baseline so far: the user reported that in-game rendering looked better, with flicker limited to the top and bottom. Other sections still require more work.

Do not upload the `physicalfb_dim1*` table-1 probes yet. They target `0x4F35C`, where table 1 remains stock `440x330`, but Gopher64 input smoke left the full, width-only, and height-only variants stuck on the TND logo after 85 seconds. These are useful clues for the boxed intro but not hardware-safe candidates.

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
