# TND6480i Resume State

Last updated: 2026-05-11 after user playability-priority reset and upload of the in-game viewport centering canary.

Scope reminder: keep work limited to this N64/TND6480i project and directly related tools/devices.

## Current Console State

The SC64 is in direct-ROM mode with EEPROM 4k. The console currently has the gameplay-first playability canary loaded:

```text
artifacts/generated/game_h460_top10_current.z64
MD5: 892cbd5e8253e9cc3c6c4c4645bd69c0
N64 CRC: CD679836 961D35FD
```

This is a deliberately small playability branch. It is based on the last solid gameplay/watch fallback and reverts away from the later gunbarrel/menu experiments. It changes only normal gameplay viewport centering:

- `0xBB91C`: non-camera default viewport height `480 -> 460`
- `0xBB954`: non-camera fallback viewport height `480 -> 460`
- `0xBBA80`: non-camera default viewport top `0 -> 10`

Goal: reduce the current top/bottom in-game flicker and overscan without touching front/title, gunbarrel, dossier, or camera cutscene paths.

Evidence:

```text
diagnostics/captures/contact_sheets/game_viewport_centering_input70_20260510.jpg
reports/smoke/smoke_game_viewport_centering_input70_20260510.json
diagnostics/captures/current/after_upload_game_h460_top10_wait10_20260511.png
reports/tnd480i_game_h460_top10_current_report.json
```

If this improves fit but still shows top/bottom issues, the next tight candidate should be a nearby viewport crop/center probe, not title/menu work. If it regresses gameplay, roll back to:

```text
artifacts/generated/TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_reserve58000_core_no_menu.z64
MD5: 17d4ea3194d02d5ea121b1e42aa59469
N64 CRC: CD6799DE DAD61991
```

Nearby already-built fallback/probe:

```text
artifacts/generated/game_h440_top20_current.z64
MD5: 9eaf413cdb765a33cf164095f897fc14
N64 CRC: CD67980E 8DF351CC
```

Use `h440/top20` only if `h460/top10` still draws too far into the CRT overscan or keeps text boxes/countdown outside the visible field.

## Current Priority Reset

User testing on 2026-05-11 showed the project is not playable enough to justify spending more first-pass time on gunbarrel/front polish. New priority order:

1. In-game playability: Bazaar fit, top/bottom flicker, text boxes running offscreen, countdown placement, watch flicker.
2. Pause/watch stability and readability.
3. Level intro/outro camera rendering, currently still confined to a top rectangle.
4. Dossier/menu usability: missing/offscreen save-select and mission-select text, difficulty/objectives shifted.
5. Level progression crash: Party loads audio then crashes shortly after, so test beyond Bazaar before calling any build playable.
6. Front/title/gunbarrel/logos/opening credits/demos after gameplay is stable.

The late front/menu canaries are no longer the active line. In particular, do not keep promoting `menu_late_safe`: user testing found broad menu/front regressions, and it did not address gameplay enough to justify the extra risk.

The previous slow-gunbarrel/menu candidate remains useful reference material only:

```text
artifacts/generated/gbslow_menu05_09_moving_post_20260511.z64
MD5: 739ae518dddfc423482a859b63e6f33e
N64 CRC: 735E38D7 95D565A3
```

It was based on the best gameplay/pause fallback below, then added four narrow ingredients:

- `S_gunbarrel_case1_slow_3_625`: changes only `0x3DF04/0x3DF08` so the case-1 title X decrement is `3.625f`, matching the slower GE 480i-like gunbarrel cadence.
- `U_shared_blitter_stock_texture_setup`: restores TND's stock texture-setup words at `0x4FDEC`, `0x4FDFC`, `0x4FE34`, `0x4FE3C`, `0x4FE44`, and `0x4FF00` while retaining the GE-style step/row/stride words already present in the fallback.
- `menu05_09_safe`: applies 161 safe direct GE-enhanced-480i words in the `0x403DC:0x45138` front/menu range. Gopher64 menu-flow sheets show better document/paper menu behavior than the prior current-best branch.
- `moving_skip_post_matrix_barrel_only`: changes `0x3C68C` from `lui t7,0x0600` to `addiu t7,zero,0`, removing the late moving-barrel display-list pointer only in the post-matrix path.

Hardware evidence:

```text
diagnostics/captures/videos/gbslow_menu05_09_moving_post_coldboot_20260511.mp4
diagnostics/captures/contact_sheets/gbslow_menu05_09_moving_post_coldboot_20260511_sheet.jpg
diagnostics/captures/contact_sheets/gbslow_menu05_09_moving_post_gunbarrel_24_74_2fps_20260511.jpg
reports/capture_cadence/motion_gbslow_menu05_09_moving_post_vs_refs_20260511.json
```

Result: promote as the current best test candidate. Compared with `gamefulltop0_gbslow_shared_blitter_stock_texture_setup`, the early doubled white aperture/dot phase is reduced while preserving the slow/GE-like cadence. The first sustained red is `44.845s`, and white-to-red is `5.973s`.

A later long no-input hardware capture of the same loaded build confirmed the cadence is stable across a fresh Kasa coldboot:

```text
diagnostics/captures/videos/gbslow_menu05_09_moving_post_long_noinput_20260511.mp4
diagnostics/captures/contact_sheets/gbslow_menu05_09_moving_post_long_noinput_8s_20260511.jpg
diagnostics/captures/contact_sheets/gbslow_menu05_09_moving_post_long_gunbarrel_24_74_2fps_20260511.jpg
reports/capture_cadence/motion_gbslow_menu05_09_moving_post_long_vs_short_20260511.json
```

Long-capture result: first sustained red `44.978s`, white-to-red `5.972s`. The no-input loop still does not reach gameplay/demo, so hardware coverage for intro/gameplay still requires controller driving. Remaining visual problems on the promoted build: title/credits/cast composition is clipped or mirrored in places, menu/level-select alignment is not final, and the intro/gameplay path still needs user-driven or emulator-assisted verification. Gopher64 source-vs-current startup and menu-flow comparisons show no obvious front-end regression, but current RDP capture is intermittent, so hardware GV-USB2 is authoritative for title/front visuals:

```text
diagnostics/captures/contact_sheets/gopher_startup_source_vs_current_best_20260511.jpg
diagnostics/captures/contact_sheets/gopher_gbslow_texture_setup_inputflow_20260511.jpg
diagnostics/captures/contact_sheets/source_vs_gbslow_texture_inputmenu_dense_20260511.jpg
reports/smoke/smoke_startup_source_vs_current_best_20260511.json
diagnostics/captures/contact_sheets/gopher_menu_safe_matrix_20260511.jpg
diagnostics/captures/contact_sheets/gopher_gbslow_menu05_09_moving_post_input_20260511.jpg
reports/smoke/smoke_gbslow_menu05_09_moving_post_input_20260511.json
```

The previous gameplay/pause fallback remains the rollback target:

```text
artifacts/generated/TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_reserve58000_core_no_menu.z64
MD5: 17d4ea3194d02d5ea121b1e42aa59469
N64 CRC: CD6799DE DAD61991
```

User feedback on this fallback: pause/watch is good, all save slots work, and in-game is slightly more stable than the prior `camfullheight` build. It still has top/bottom flicker and the remaining problem areas are opening credits, menu size/text/layout, intro cutscene framing, level-select text alignment, and any gunbarrel polish left after the promoted slow/texture-setup candidate.

After the user returned on 2026-05-10, the live in-game capture was intentionally user-driven rather than a no-input cold boot. Use it as gameplay flicker evidence, not title/gunbarrel timing evidence:

```text
diagnostics/captures/current_state_user_back_20260510_1838.png
```

A later Kasa power-cycle/no-input capture is the clean neutral-start reference for this same fallback:

```text
diagnostics/captures/videos/gamefulltop0_neutral_start_recheck_20260510_1840.mkv
diagnostics/captures/contact_sheets/gamefulltop0_neutral_start_recheck_labeled_20260510_1840.jpg
reports/capture_cadence/motion_gamefulltop0_neutral_recheck_20260510_1840.json
```

That neutral-start reference loops the front end and confirms the fallback gunbarrel cadence is still stock/TND-like, not GE 480i-like. The earlier `gamefulltop0_coldboot_reference_20260510.mkv` includes user-driven progress and should not be used as a pure no-input timing reference.

Restore evidence:

```text
diagnostics/captures/after_restore_gamefulltop0_return_wait8_20260510.png
diagnostics/captures/videos/gamefulltop0_restored_reference_startup_20260510.mkv
diagnostics/captures/contact_sheets/gamefulltop0_restored_reference_startup_20260510_sheet.jpg
diagnostics/captures/current/after_restore_gamefulltop0_after_frontzbuf_reject_wait8_20260510.png
diagnostics/captures/current/after_restore_gamefulltop0_after_flbox_reject_20260510.png
diagnostics/captures/current/after_restore_fallback_from_sc64usb_diag_20260510.png
diagnostics/captures/current/after_restore_fallback_from_gunbarrel_slow_tests_20260510.png
diagnostics/captures/current/after_restore_fallback_from_alt640_blitter_20260511.png
```

Recent rejected/superseded title/gunbarrel probes:

- `gunsplit259f4` was previously loaded and may affect cadence, but it was superseded when later title-asset testing required restoring the fallback.
- `TND64_480i_gamefulltop0_ge480i_titleasset_exact_20260510.z64` booted, but the later live capture showed persistent hardware gameplay corruption. Reject as a gameplay-safe baseline.
- The `backdrop_*` matrix generated by `scripts/build_tnd480i_backdrop_matrix.py` survived Gopher64 but looked worse than the exact-asset baseline in `diagnostics/captures/contact_sheets/backdrop_matrix_gopher36_20260510.jpg`; do not upload.
- `TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_frontzbuf_reserve58000_core_no_menu.z64` booted but made the title/credits path visibly worse with heavy horizontal striping and did not improve gunbarrel cadence. It has been rejected and the fallback above was restored afterward.
- `flbox.z64` / `TND64_480i_gamefulltop0_frontbox_cluster_safe_20260510.z64` booted and looped on hardware, but the title/credits/gunbarrel looked essentially unchanged and still stock-like. It has been rejected as non-improving and the fallback above was restored afterward.
- `gamefulltop0_gunbarrel_case1_slow3625_20260510.z64` is useful but not final. It proves the state-machine case-1 `g_TitleX` decrement can create a GE-like slow Bond-on-screen phase (`45.078s` first sustained red vs fallback `40.340s`), but it does not fix the doubled RLE barrel.
- `gamefulltop0_gunbarrel_slow3625_endcolor64_20260510.z64` and `gamefulltop0_gunbarrel_slow3625_endcolor96_20260510.z64` are rejected as final candidates. Both preserve slow timing, but color gating only dims/underpowers the barrel art and does not cleanly solve duplicate aperture/rifling composition.
- `gamefulltop0_sniper_call_alt640_blitter_20260511.z64` is rejected as a patch. It redirects only the sniper wrapper's inner call from `sub_GAME_7F01B240` to adjacent `sub_GAME_7F01B6E0`; hardware survives and reaches credits, but the gunbarrel gains a large magenta/pink miscomposited barrel layer and stock-like/early red timing.
- `gamefulltop0_gbslow_shared_blitter_stock_row_stride_20260511.z64` and `gamefulltop0_gbslow_shared_blitter_stock_all_20260511.z64` remain offline/rejected. Restoring row/stride/full stock behavior brings back horizontal garbage/static in Gopher64. Texture setup only is the useful rollback.
- `gamefulltop0_gbslow_texture_rle32_20260511.z64`, `gamefulltop0_gbslow_texture_rle48_20260511.z64`, and `gamefulltop0_gbslow_texture_rle64_20260511.z64` are rejected/offline. In current-best context the RLE32/48 caps hide some duplicate layer pixels but underpower the barrel/red art; RLE64 corrupts front/menu text in Gopher64.
- `gamefulltop0_gbslow_texture_front_force_table0_20260511.z64` is hardware-rejected. It forces the front/menu VI table selector at `0x4F1B8` to use table0, but the cold-boot capture did not fix front/cast clipping and perturbed gunbarrel progression (`49.449s` first sustained red versus current best `45.045-45.145s`). The current-best ROM was restored to SC64 afterward.
- `gamefulltop0_gbslow_texture_skip_menufb_20260511.z64` is hardware-rejected/non-promoted. It bypasses the menu framebuffer swap branch at `0x4F1C4`; hardware cadence stayed in the good slow range (`45.012s` first sustained red), but the front/title composition and cast clipping were not improved.
- `gamefulltop0_gbslow_texture_frontzbuf_width640_20260511.z64` is hardware-rejected. It changes only the front zbuffer width word at `0x4D42C` from `440` to `640`; it reproduced horizontal title/cast striping like the older broad `frontzbuf` branch.
- `gamefulltop0_gbslow_texture_frontzbuf_height480_20260511.z64` is hardware-rejected/non-promoted. It changes only the front zbuffer height word at `0x4D434` from `330` to `480`; cadence remained good (`44.978s` first sustained red), but the doubled aperture and front/title composition remained materially unchanged. The current-best ROM was restored to SC64 afterward.
- `gbslow_menu05_09_layout_only_20260511.z64` is superseded. Skipping the suspect words at `0x40540/0x40544` did not show a visual improvement over the full `menu05_09_safe` range.
- `gbslow_menu05_09_moving_pre_20260511.z64` and `gbslow_menu05_09_moving_both_20260511.z64` are offline/superseded. The post-only moving display-list suppression keeps the useful aperture cleanup without stripping too much of the moving barrel art.
- `gbslow_menu05_09_moving_post_stock_stripsteps_20260511.z64`, `gbslow_menu05_09_moving_post_stock_rowcount_20260511.z64`, and `gbslow_menu05_09_moving_post_stock_stride_20260511.z64` are offline rejects. Gopher64 shows stock row-count and stock stride reintroduce static/garbage; stock strip-steps has no clear visual win.
- `gbslow_moving_post_front_textwork_20260511.z64` is hardware-safe but rejected/non-promoted. It keeps the same slow cadence (`44.811s` first sustained red, white-to-red `5.972s`) but the active-area comparison and visual sheets show no material improvement over the previous moving-post branch. Evidence: `diagnostics/captures/contact_sheets/compare_moving_post_vs_front_textwork_8s_20260511.jpg`, `reports/capture_active_area/active_gbslow_front_textwork_vs_moving_post_cast_20260511.json`.
- `gbslow_moving_post_sniper_clone_tnd508_stride_20260511.z64`, `gbslow_moving_post_sniper_clone_tnd508_row480_stride_20260511.z64`, `gbslow_moving_post_sniper_clone_tnd508_row507_stride_20260511.z64`, `gbslow_moving_post_sniper_clone_tnd508_strip20_stride_20260511.z64`, and `gbslow_moving_post_sniper_clone_tnd508_strip20_row507_stride_20260511.z64` are Gopher rejects. They route only the sniper callsite through a clone using TND-source stride/row geometry, but all introduce horizontal static/garbage by the Bond/aperture frame. Do not upload. Evidence: `diagnostics/captures/contact_sheets/gopher_moving_post_sniper_tnd508_geometry_20260511.jpg`.
- `gbslow_moving_post_gunbufBE200_20260511.z64` is an offline reject. It applies only `0x3FC90/0x3FC94` on top of the moving-post baseline; Gopher survives, but the aperture/dot is fatter and the doubled composition remains. Evidence: `diagnostics/captures/contact_sheets/gopher_moving_post_gunbufBE200_20260511.jpg`.

Recent reject evidence:

```text
diagnostics/captures/contact_sheets/gopher_gbslow_texture_rle_caps_20260511.jpg
diagnostics/captures/contact_sheets/gopher_gbslow_texture_rle_caps_cropped_20260511.jpg
reports/smoke/smoke_gbslow_texture_rle_caps_20260511.json
diagnostics/captures/videos/gbslow_texture_front_force_table0_coldboot_20260511.mp4
diagnostics/captures/contact_sheets/gbslow_texture_front_force_table0_coldboot_20260511_sheet.jpg
diagnostics/captures/contact_sheets/gbslow_texture_front_force_table0_gunbarrel_24_74_2fps_20260511.jpg
reports/capture_cadence/motion_gbslow_texture_front_force_table0_vs_refs_20260511.json
diagnostics/captures/videos/gbslow_texture_skip_menufb_coldboot_20260511.mp4
diagnostics/captures/contact_sheets/gbslow_texture_skip_menufb_coldboot_20260511_sheet.jpg
diagnostics/captures/contact_sheets/gbslow_texture_skip_menufb_gunbarrel_24_74_2fps_20260511.jpg
reports/capture_cadence/motion_gbslow_texture_skip_menufb_vs_refs_20260511.json
diagnostics/captures/videos/gbslow_texture_frontzbuf_width640_coldboot_20260511.mp4
diagnostics/captures/contact_sheets/gbslow_texture_frontzbuf_width640_coldboot_20260511_sheet.jpg
diagnostics/captures/contact_sheets/gbslow_texture_frontzbuf_width640_gunbarrel_24_74_2fps_20260511.jpg
reports/capture_cadence/motion_gbslow_texture_frontzbuf_width640_vs_refs_20260511.json
diagnostics/captures/videos/gbslow_texture_frontzbuf_height480_coldboot_20260511.mp4
diagnostics/captures/contact_sheets/gbslow_texture_frontzbuf_height480_coldboot_20260511_sheet.jpg
diagnostics/captures/contact_sheets/gbslow_texture_frontzbuf_height480_gunbarrel_24_74_2fps_20260511.jpg
reports/capture_cadence/motion_gbslow_texture_frontzbuf_height480_vs_refs_20260511.json
diagnostics/captures/contact_sheets/gopher_moving_slow_menu_matrix_20260511.jpg
diagnostics/captures/contact_sheets/gopher_gbslow_moving_post_blitter_micro_20260511.jpg
reports/smoke/smoke_gbslow_moving_post_blitter_micro_20260511.json
```

Gopher64 tooling note: `scripts/smoke_gopher64.py` now supports `--input-events`, a semicolon/newline list or file path of `time:key[:duration]` events. Existing `--input` Start/A mashing still works, and scheduled events can be layered on top for pause/watch checks, for example `--input --input-until 52 --input-events "61:ENTER"`.

The exact GE title-asset report is `reports/tnd480i_gamefulltop0_ge480i_titleasset_exact_20260510_report.json`. The backdrop matrix smoke report is `reports/smoke/smoke_ge480i_titleasset_backdrop_matrix_36s_20260510.json`.

Recent fallback restore captures:

```text
diagnostics/captures/after_restore_gamefulltop0_wait5_20260510.png
diagnostics/captures/after_restore_gamefulltop0_wait15_20260510.png
```

## Hardware Commands

Check SC64:

```powershell
& C:\Users\codex\Documents\n64\sc64deployer.exe info
```

Recover to SC64 menu if ROM writes are disabled:

```powershell
& C:\Users\codex\Documents\n64\sc64deployer.exe reset
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\hardware\cycle_kasa_n64_buttons.ps1 -OffOnly -OffSeconds 4
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\hardware\cycle_kasa_n64_buttons.ps1 -OnOnly -OnSeconds 12
& C:\Users\codex\Documents\n64\sc64deployer.exe info
```

Upload a candidate:

```powershell
& C:\Users\codex\Documents\n64\sc64deployer.exe upload --direct --save-type eeprom4k <rom.z64>
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\hardware\cycle_kasa_n64_buttons.ps1 -OffOnly -OffSeconds 4
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\hardware\cycle_kasa_n64_buttons.ps1 -OnOnly -OnSeconds 12
```

Capture one GV-USB2 S-video frame:

```powershell
ffmpeg -hide_banner -loglevel error -y -f dshow -video_size 720x480 -framerate 29.97 -i "video=GV-USB2, Analog Capture" -frames:v 1 <out.png>
```

Record a compressed GV-USB2 clip while power-cycling with Kasa:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\hardware\record_gvusb2_kasa_cycle.ps1 -Output <out.mp4> -Seconds 90 -PreRollSeconds 2 -OffSeconds 5 -OnSeconds 12
```

The helper was added after a failed `Start-Process ffmpeg ...` attempt exposed quoting trouble with the GV-USB2 device name. A no-cycle smoke succeeded and produced `diagnostics/captures/videos/record_helper_nocycle_test_20260510.mp4`; a real Kasa-cycle fallback reference also succeeded:

```text
diagnostics/captures/videos/gamefulltop0_helper_coldboot_reference_20260510.mp4
diagnostics/captures/contact_sheets/gamefulltop0_helper_coldboot_reference_20260510_sheet.jpg
```

## Recent Rejected Probes

`camfulltop0`: rejected. It made the level intro move more than it should and did not fix the smaller-rectangle render.

`missiontext`: rejected. It made level-select text alignment worse.

`physicalfb_dim1*`: do not upload first. They survived Gopher64 but got stuck on the TND logo.

`gunwork259f4`: rejected. Matching the stretched asset's RLE encoded length by padding below the source booted but caused obvious gunbarrel/title artifacts.

`gunwork259f4right`: rejected. Padding the right-of-source strip booted but still showed stray top-row garbage and a misframed gunbarrel.

`gunsplit259f4`: superseded/restored away from console. It appeared cleaner than pixel-padding workload probes and may affect cadence, but the automated segment alignment was not definitive.

`ge480i_titleasset_exact`: rejected as a gameplay-safe branch after live GV-USB2 showed persistent split/corrupt gameplay state.

`backdrop_*`: emulator-rejected. Skip/scale/translate variants did not improve the sampled gunbarrel frame.

`frontzbuf` on top of the current fallback: hardware-rejected. It booted and looped, but title/credits frames showed heavy striping and cadence analysis did not show the GE 480i-style slowdown.

`flbox` / front text-box first cluster: hardware-rejected as non-improving. It changed only five safe GE 480i words at `0x3EC18`, `0x3EC1C`, `0x3EC44`, `0x3EC5C`, and `0x3EC78`; Gopher64 and hardware both survived, but the front text/credits/gunbarrel behavior did not materially improve. Evidence:

```text
diagnostics/captures/contact_sheets/frontbox_noinput_gopher_20260510.jpg
diagnostics/captures/videos/flbox_powercycle_startup_20260510.mp4
diagnostics/captures/contact_sheets/flbox_powercycle_startup_20260510_sheet.jpg
diagnostics/captures/videos/flbox_live_followup_20260510.mp4
diagnostics/captures/contact_sheets/flbox_live_followup_20260510_sheet.jpg
diagnostics/captures/current/after_restore_gamefulltop0_after_flbox_reject_20260510.png
```

Front/menu layout subcluster smokes: keep offline for now. `scripts/build_tnd480i_candidate.py` now has split groups for `0x43Axx`, `0x460xx`, float bounds, Y offsets, `0x4AAAxx`, and grid-step constants. Short candidates `fl43a`, `fl460`, `flflt`, `fly`, `fl4aaa`, `flgrid`, `fl43a460`, and `flsafe` all survived Gopher64 no-input startup, but none clearly fixed the front text/layout. `flgrid` was the weakest input-smoke result and should not be uploaded first. Evidence:

```text
diagnostics/captures/contact_sheets/layout_subclusters_gopher_20260510.jpg
diagnostics/captures/contact_sheets/layout_flsafe_input_gopher_20260510.jpg
diagnostics/captures/contact_sheets/layout_individual_input_gopher_20260510.jpg
reports/smoke/smoke_layout_subclusters_a_20260510.json
reports/smoke/smoke_layout_subclusters_b_20260510.json
reports/smoke/smoke_layout_flsafe_input_20260510.json
reports/smoke/smoke_layout_individual_input_20260510.json
```

SC64 VI/USB telemetry probes: currently unreliable and not worth repeating blindly. AUX, IS-Viewer, and a direct N64-side SC64 `USB_WRITE` ping all confirmed the PC/COM path works (`CMDv` returns `SCv2`) but produced no `PKT` payloads during boot. The no-wait BCLR/HVI USB ping probes booted or partially booted but still stayed silent; the HVI variant visibly perturbed the gunbarrel. Evidence:

```text
scripts/build_sc64_aux_vidstate.py
scripts/build_sc64_isv_vidstate.py
scripts/build_sc64_usb_ping.py
scripts/sc64_listen_aux.py
reports/hardware/sc64isv_bclr_ping_waitpi_packets_bootlisten_20260510.json
reports/hardware/sc64usb_bclr_ping_nowait_packets_bootlisten_20260510.json
reports/hardware/sc64usb_hvi_ping_nowait_packets_bootlisten_20260510.json
diagnostics/captures/current/after_sc64usb_bclr_ping_nowait_bootlisten_20260510.png
diagnostics/captures/current/after_sc64usb_hvi_ping_nowait_bootlisten_20260510.png
```

Conclusion: the USB-C cable and SC64 serial link are not the blocker because uploads, `info`, and raw `CMDv` work. Prefer capture/emulator-driven visual patch iteration unless there is a new SC64-side protocol insight.

GE decomp refresh: a current local checkout now exists at `C:\Users\codex\Documents\GitHub\007`. The most relevant files for the next title/gunbarrel pass are:

```text
C:\Users\codex\Documents\GitHub\007\src\fr.c
C:\Users\codex\Documents\GitHub\007\src\fr.h
C:\Users\codex\Documents\GitHub\007\src\game\title.c
C:\Users\codex\Documents\GitHub\007\src\game\blood_animation.c
C:\Users\codex\Documents\GitHub\007\src\game\bondview.c
C:\Users\codex\Documents\GitHub\007\src\game\lvl.c
```

Useful decomp clues:

- `viSetVideoMode(MD_MAXIMUM)` selects the 480i-style mode, but title/front code still builds geometry from `viGetX()` and `viGetY()`.
- `lvlStageLoad` returns non-title stages to `MD_NORMAL`, so gameplay fixes and title fixes can diverge.
- The title path layers `manipulateGunbarrelAndLogoMatrices`, `insert_sniper_sight_eye_intro`, `insert_sight_backdrop_eye_intro`, and the blood overlay around the shared `gunbarrelgfxListPointer`.
- The current fallback contact sheet shows a double aperture before the full gunbarrel, so the next title probes should be callsite-specific layer isolation, not more global bitmap or blitter swaps.

Offline hlimit-only canary:

```text
artifacts/generated/gamefulltop0_hlimit_current_20260510.z64
MD5: b68122a8982d25305046caef3398f207
N64 CRC: CD6799C2 7544831F
Only patch: 0x46F18, title/menu height limit 0x14A -> 0x1E0
```

It survived a Gopher64 process smoke, but emulator visual capture is currently not trustworthy in this RDP/desktop state: `gdigrab` returns Windows error 5, Pillow `ImageGrab` fails, and the Win32 `PrintWindow` fallback captures only the window frame/black client. Keep this hlimit ROM offline unless a better visual route or a deliberate hardware canary slot is available.

Later deliberate hardware canary result: reject as a gunbarrel/title fix. The one-word hlimit ROM booted, reached the title/credits loop, and looked materially like fallback. The double aperture remains and cadence is unchanged (`40.307s` first sustained red vs fallback `40.340s`):

```text
diagnostics/captures/videos/hlimit_current_coldboot_20260510.mp4
diagnostics/captures/contact_sheets/hlimit_current_coldboot_20260510_sheet.jpg
diagnostics/captures/contact_sheets/hlimit_current_gunbarrel_24_60_2fps_20260510.jpg
reports/capture_cadence/motion_hlimit_current_vs_helper_fallback_20260510.json
diagnostics/captures/current/after_restore_fallback_from_hlimit_20260510.png
```

Title layer isolation canaries:

```text
artifacts/generated/gamefulltop0_skip_case1_sniper_20260510.z64
artifacts/generated/gamefulltop0_skip_case1_backdrop_20260510.z64
artifacts/generated/gamefulltop0_skip_case1_layers_20260510.z64
artifacts/generated/gamefulltop0_skip_cases1_3_sniper_20260510.z64
artifacts/generated/gamefulltop0_skip_cases1_3_backdrop_20260510.z64
```

These were generated from the current fallback after adding early intro callsite groups for `insert_sniper_sight_eye_intro` and `insert_sight_backdrop_eye_intro` to `scripts/build_tnd480i_candidate.py`. All five survived Gopher64 process smokes through the title/gunbarrel window:

```text
reports/smoke/smoke_title_layer_skips_case1_20260510.json
reports/smoke/smoke_title_layer_skips_cases1_3_20260510.json
```

Hardware canary tested: `gamefulltop0_skip_case1_backdrop_20260510.z64`, MD5 `ca5ea150976e2c4665f369dc01d13113`, N64 CRC `F367A45E 3082C162`. It booted and produced a title/gunbarrel/credits clip, but the recording was not a clean cold boot because capture started after the Rare logo. Evidence:

```text
diagnostics/captures/current/after_skip_case1_backdrop_upload_boot_20260510.png
diagnostics/captures/videos/skip_case1_backdrop_powercycle_startup_20260510.mp4
diagnostics/captures/contact_sheets/skip_case1_backdrop_powercycle_startup_20260510_sheet.jpg
reports/capture_cadence/motion_skip_case1_backdrop_vs_fallback_20260510.json
```

Conclusion: do not promote `skip_case1_backdrop`. It did not show a convincing improvement over the current fallback, and a later attempt to record a true coldboot clip with background ffmpeg failed and left a black post-check frame. The console was recovered to the SC64 menu and restored to the current fallback afterward:

```text
diagnostics/captures/current/after_recover_menu_from_skip_case1_backdrop_20260510.png
diagnostics/captures/current/after_restore_fallback_from_skip_case1_backdrop_wait8_20260510.png
```

After the recorder helper was fixed, `gamefulltop0_skip_cases1_3_backdrop_20260510.z64` was tested as a controlled coldboot canary:

```text
diagnostics/captures/videos/skip_cases1_3_backdrop_coldboot_20260510.mp4
diagnostics/captures/contact_sheets/skip_cases1_3_backdrop_coldboot_20260510_sheet.jpg
reports/capture_cadence/motion_skip_cases1_3_backdrop_vs_helper_fallback_20260510.json
diagnostics/captures/current/after_restore_fallback_from_skip_cases1_3_backdrop_wait8_20260510.png
```

It also showed the same double white aperture / stock-like gunbarrel cadence. The analyzer put fallback first sustained red at `40.340s` and the backdrop-skip canary at `40.174s` on the same helper workflow, so there is no GE 480i-like slowdown. The pre-blood `insert_sight_backdrop_eye_intro` calls are not the main fix by themselves. The fallback was restored again afterward.

Complementary sniper/RLE-layer canary:

```text
diagnostics/captures/videos/skip_cases1_3_sniper_coldboot_20260510.mp4
diagnostics/captures/contact_sheets/skip_cases1_3_sniper_coldboot_20260510_sheet.jpg
reports/capture_cadence/motion_skip_cases1_3_sniper_20260510.json
diagnostics/captures/current/after_restore_fallback_from_skip_cases1_3_sniper_wait8_20260510.png
```

Result: reject as a functional patch. Skipping `insert_sniper_sight_eye_intro` in states 1-3 removes the normal gunbarrel/title progression and strands the intro on a small white crescent. The analyzer found no sustained red phase in the 82-second clip. This confirms the sniper/RLE layer is essential state-machine work, not a layer that can simply be removed.

Sniper/RLE argument canaries after that:

```text
artifacts/generated/gamefulltop0_sniper_div640_20260510.z64
artifacts/generated/gamefulltop0_sniper_div960_20260510.z64
artifacts/generated/gamefulltop0_sniper_div2560_20260510.z64
artifacts/generated/gamefulltop0_sniper_x0_20260510.z64
artifacts/generated/gamefulltop0_sniper_xleft160_20260510.z64
artifacts/generated/gamefulltop0_sniper_xright160_20260510.z64
reports/smoke/smoke_sniper_divisors_20260510.json
reports/smoke/smoke_sniper_xargs_20260510.json
```

All six survived Gopher64 process smokes and were hardware-tested with the capture-then-Kasa-cycle helper. Divisor patches at `0x3C95C` (`640.0`, `960.0`, `2560.0`) did not remove the paired aperture or materially change red-phase timing. Constant-x patches at `0x3C980` (`0`, `-160`, `+160`) are also rejects, but they visibly separated the RLE slice from the moving gunbarrel image:

```text
diagnostics/captures/contact_sheets/sniper_x0_coldboot_20260510_sheet.jpg
diagnostics/captures/contact_sheets/sniper_xleft160_coldboot_20260510_sheet.jpg
diagnostics/captures/contact_sheets/sniper_xright160_coldboot_20260510_sheet.jpg
```

Takeaway: the double-barrel problem is a two-layer composition issue, not just the final x divisor/argument. The current fallback was restored again afterward:

```text
diagnostics/captures/current/after_restore_fallback_from_sniper_x_tests_20260510.png
```

Internal RLE and moving-barrel display-list canaries:

```text
artifacts/generated/gamefulltop0_sniper_internal_rle_skip_20260510.z64
artifacts/generated/gamefulltop0_moving_skip_prebarrel_20260510.z64
artifacts/generated/gamefulltop0_moving_skip_postbarrel_20260510.z64
artifacts/generated/gamefulltop0_moving_skip_bothbarrels_20260510.z64
reports/smoke/smoke_internal_rle_and_moving_barrel_skips_20260510.json
```

All four survived Gopher64 process smokes and were hardware-tested. `sniper_internal_rle_skip` is the most informative diagnostic: bypassing the inner `sub_GAME_7F007CC8` call at `0x3C984` largely removes the doubled rifled-barrel/RLE layer, but it strips too much art and shifts red timing early (`38.172s` vs fallback `40.340s`). The moving display-list suppressions (`pre`, `post`, and `both`) reduce some early paired-dot clutter while preserving more art, but all remain stock-like in cadence (`40.440s`, `40.474s`, `40.407s`). These are rejects as final ROMs, but they narrow the next work to the RLE blitter/source/destination state rather than simple final-x/divisor shifts or whole-layer skips.

Single-state sniper and RLE color canaries:

```text
artifacts/generated/gamefulltop0_skip_case1_sniper_20260510.z64
artifacts/generated/gamefulltop0_sniper_rle_endcolor0_20260510.z64
artifacts/generated/gamefulltop0_sniper_rle_endcolor32_20260510.z64
artifacts/generated/gamefulltop0_sniper_rle_endcolor128_20260510.z64
reports/smoke/smoke_sniper_rle_endcolors_20260510.json
```

`skip_case1_sniper` is rejected for the same functional reason as the wider sniper skip: it strands the intro on a small crescent and never reaches sustained red (`reports/capture_cadence/motion_skip_case1_sniper_vs_helper_fallback_20260510.json`).

The RLE end-color probes changed only the three end-color values loaded into the `sub_GAME_7F007CC8` call. `endcolor0` and `endcolor32` largely remove the doubled RLE/rifling layer while preserving title progression, but they strip too much barrel art. `endcolor128` keeps the doubled layer. None produce the GE 480i-style slowdown: fallback first sustained red is `40.340s`; the three probes are `40.307s`, `40.474s`, and `40.507s` respectively (`reports/capture_cadence/motion_sniper_rle_endcolors_vs_helper_fallback_20260510.json`).

The current fallback was restored again afterward:

```text
diagnostics/captures/current/after_restore_fallback_from_skip_case1_sniper_20260510.png
diagnostics/captures/current/after_restore_fallback_from_rle_endcolor_tests_20260510.png
```

Gunbarrel case-1 timing/color canaries:

```text
artifacts/generated/gamefulltop0_gunbarrel_case1_slow3625_20260510.z64
artifacts/generated/gamefulltop0_gunbarrel_slow3625_endcolor64_20260510.z64
artifacts/generated/gamefulltop0_gunbarrel_slow3625_endcolor96_20260510.z64
diagnostics/captures/contact_sheets/gunbarrel_case1_slow3625_gunbarrel_24_74_2fps_20260510.jpg
diagnostics/captures/contact_sheets/gunbarrel_slow3625_endcolor64_gunbarrel_24_74_2fps_20260510.jpg
diagnostics/captures/contact_sheets/gunbarrel_slow3625_endcolor96_gunbarrel_24_74_2fps_20260510.jpg
reports/capture_cadence/motion_gunbarrel_slow3625_endcolor96_vs_refs_20260510.json
diagnostics/captures/current/after_restore_fallback_from_gunbarrel_slow_tests_20260510.png
```

Result: the timing-only patch is a strong diagnostic and a possible later ingredient; it changes the case-1 title X decrement from the stock `5.8183274f` load to `3.625f`, delaying red/title timing into a GE-like range. It does not fix the doubled RLE layer. Combining that timing patch with RLE end-color `0x40` or `0x60` keeps the slow timing but leaves the barrel too dark/miscomposited. Do not spend more hardware cycles on color-only ramps unless they are part of a targeted per-state RLE/blitter fix.

Sniper wrapper alt-640 blitter canary:

```text
artifacts/generated/gamefulltop0_sniper_call_alt640_blitter_20260511.z64
MD5: 5633d9bf60a79da22cdd2aa5b1085306
N64 CRC: CD679BDE 85B1D274
reports/smoke/smoke_sniper_call_alt640_blitter_20260511.json
diagnostics/captures/contact_sheets/sniper_call_alt640_blitter_gunbarrel_24_74_2fps_20260511.jpg
reports/capture_cadence/motion_sniper_call_alt640_blitter_vs_refs_20260511.json
diagnostics/captures/current/after_restore_fallback_from_alt640_blitter_20260511.png
```

Result: reject as final. The canary changes only `0x3C8A4` from `jal sub_GAME_7F01B240` to `jal sub_GAME_7F01B6E0`. It proves the adjacent 640-stride blitter can be reached from the sniper wrapper without causing the old global vertical-bar title freeze, but the raw call is visually wrong: it creates a large magenta/pink duplicate barrel and does not improve cadence. Next static work should compare `sub_GAME_7F01B240` against `sub_GAME_7F01B6E0` and borrow individual texture/stride/row-loop behaviors into a proper callsite-specific path rather than redirecting blindly.

Display-cast rect/text canaries:

```text
artifacts/generated/gbslow_moving_post_displaycast_iface_20260511.z64
artifacts/generated/gbslow_moving_post_displaycast_rects_20260511.z64
artifacts/generated/gbslow_moving_post_displaycast_text_20260511.z64
artifacts/generated/gbslow_moving_post_displaycast_rects_text_20260511.z64
artifacts/generated/gbslow_moving_post_displaycast_iface_rects_text_20260511.z64
reports/smoke/smoke_moving_post_displaycast_matrix_20260511.json
diagnostics/captures/contact_sheets/gopher_moving_post_displaycast_matrix_20260511.jpg
diagnostics/captures/videos/gbslow_displaycast_rects_coldboot_20260511.mp4
diagnostics/captures/contact_sheets/gbslow_displaycast_rects_coldboot_8s_labeled_20260511.jpg
reports/capture_cadence/motion_gbslow_displaycast_rects_vs_moving_post_20260511.json
```

Result: reject/non-promote. `displaycast_rects` was hardware-tested and kept the slow gunbarrel cadence, but it blanked the no-input loop after the gunbarrel where the promoted baseline shows cast/credits. The text-bearing display-cast variants are Gopher rejects because they shove cast text off the right edge. Current-best `gbslow_menu05_09_moving_post_20260511.z64` was restored afterward.

## Useful Next Steps

1. Preserve `gamefulltop0` as the gameplay/pause fallback.
2. For gunbarrel, do not continue blind RLE bitmap swaps, simple final-x shifts, whole-layer skips, plain color-ramp-only probes, raw alt-blitter redirects, or the one-word hlimit path. The exact GE source asset alone did not fix the issue, backdrop transform constants were not promising, x-argument canaries prove the RLE slice is a separate composited layer, the inner-RLE skip proves that layer is the duplicated barrel, color dimming can hide it without fixing composition, hlimit has no useful effect, the `3.625f` timing canary only mimics the slowdown, and the alt-640 sibling blitter has an incompatible visual/argument contract. Investigate `sub_GAME_7F007CC8` / `sub_GAME_7F01B240` source and destination state, clipping, per-state draw gating, or a callsite-specific partial transplant from `sub_GAME_7F01B6E0`.
3. For intro cutscene framing, investigate callsite-specific use of the second direct render dimension word (`0x4F35C`) rather than static global table-1 patches.
4. For menus/level select, compare GE enhanced480i text/grid callsites before another blind coordinate overlay.
5. Keep updating this file and `docs/decomp_480i_findings.md` after each hardware result.
