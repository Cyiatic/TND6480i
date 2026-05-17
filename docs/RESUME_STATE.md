# TND6480i Resume State

Last updated: 2026-05-17 after rejecting `t8040vmenuscales` and restoring `t8040viewge`.

Scope reminder: keep work limited to this N64/TND6480i project and directly related tools/devices.

## Current Performance Finding

User Analogue 3D feedback on `t8040viewge`: gameplay is viable but performance is poor, with Printworks and Wreck reportedly running slower than expected even with Analogue overclock. Treat this as a first-class issue, not just visual polish.

Current interpretation: the active branch is probably paying for a true high-workload render path, not merely switching VI output to interlace. `t8040viewge`, `t8040camge`, `tnd8040`, and `tnd58` all share the expensive stage z-buffer path at:

```text
0x106ED4 = width 640
0x106EE4 = height 480
0x106EF0 = low-res width 640
0x106F10 = single-player height 480
0x106F24 = split height 480
```

That means UI placement or 480i capture output is not enough to prove the 3D scene is being rendered in the same way as GE's enhanced 480i patch. The next gameplay work should quantify performance against GE480i and test whether a lower-cost internal render/depth path can preserve the 480i visual target without the current slowdown.

Analogue comparison pack:

```text
artifacts/analogue_test/TNDVIABL.Z64  = t8040viewge, current viable baseline
artifacts/analogue_test/TNDCAMGE.Z64  = t8040camge, previous all-level boot baseline
artifacts/analogue_test/TND8040.Z64   = tnd8040 control before GE camera/view constants
artifacts/analogue_test/TND58.Z64     = older tlbpages58 fallback/control
```

User feedback: all four comparison ROMs are similarly slow. Treat that as confirmation that the shared 640-wide/480-high stage z/depth path is the likely cost center, not the later `t8040viewge` viewport/menu edits.

Performance canaries built from current `t8040viewge`:

```text
artifacts/analogue_test/TNDZ360.Z64 = t8040viewge with 640-wide, 360-high tested stage z/depth heights
artifacts/analogue_test/TNDZ640.Z64 = t8040viewge with 640-wide, stock-ish tested stage z/depth heights
artifacts/analogue_test/TNDZSTK.Z64 = t8040viewge with stock tested stage z/depth footprint
reports/tnd480i_t8040viewge_perf_zbuf_candidates_20260517.json
scripts/build_t8040viewge_perf_zbuf_candidates.py
```

Test order: `TNDZ360` first because it keeps 640-wide rows while lowering the worst height cost. If speed improves but visuals regress, the next engineering target is a hybrid render path: 480i VI/output and UI/view constants without full 640x480 depth allocation everywhere.

Local direct-stage Wreck smoke: `reports/smoke/smoke_t8040viewge_perf_zbuf_wreck_visual_20260517.json`. The `t8040viewge` control plus `t8040vz360`, `t8040vz640`, and `t8040vzstk` all survived about 34 seconds in Gopher64 and produced nonblack Wreck captures. This is only a boot/render sanity gate; use Analogue or real hardware for the actual speed judgment.

Motion-cadence report:

```text
reports/capture_cadence/performance_ge480i_vs_tnd6480i_wreck_20260517.json
```

## Current Console State

Promoted candidate currently loaded on the SC64 for the next manual full-romhack visual-fit test:

```text
artifacts/generated/t8040viewge.z64
content source: artifacts/generated/tnd8040.z64
MD5: 763f94bd1fb364e3d9eb8809bde4900b
N64 CRC: 84B7FA99 E50042D8
```

Paired save:

```text
artifacts/generated/t8040viewge.sav
MD5: 79ed3fe6851b080ff21de69fd12f034d
```

Purpose: keep the `t8040camge` playability/camera breakthrough, then also apply GE's normal non-camera default viewport height/top. This is the current stable gameplay baseline before further front/menu experiments.

Evidence:

```text
scripts/build_tnd8040_viewport_followup_candidates.py
reports/tnd480i_tnd8040_viewport_followup_candidates_20260517.json
reports/stage_probes/direct_stage_probes_t8040viewge_all.json
reports/smoke/smoke_t8040viewge_visual_matrix_20260517.json
reports/stage_probes/direct_stage_t8040viewge_hardware_20260517.json
reports/tnd6480i_t8040viewge_bps_manifest.json
diagnostics/captures/contact_sheets/t8040viewge_p00bzr_direct_20260517_postcycle.jpg
diagnostics/captures/contact_sheets/t8040viewge_p01pty_direct_20260517_postcycle.jpg
diagnostics/captures/contact_sheets/t8040viewge_p04hot_direct_20260517_postcycle.jpg
diagnostics/captures/contact_sheets/t8040viewge_p11vol_direct_20260517_postcycle.jpg
diagnostics/captures/contact_sheets/t8040viewge_full_startup_20260517_postcycle.jpg
```

Verified BPS patch:

```text
artifacts/generated/TND6480i_t8040viewge_from_baseline_tnd.bps
MD5: 773dedd2d931426fde77652fa07d19e5
```

Important correction: `p01pty` is Party / CMGN Launch Party. `p13end` is The End / end-credits / City of Hamburg. Do not describe `p13end` white-rectangle or black-screen behavior as Party.

User full-ROM feedback on the previous `t8040camge` baseline: all levels appear to load and boot correctly. User feedback on `t8040viewge`: Bazaar and Labs look fine, pause menu looks fine, all levels boot, and bullets UI is good. This means the work has moved from load survival back to visual correctness, especially the pre-ingame/front/menu path.

Rejected front/menu candidate: `t8040vmenuscales`

- It was uploaded after emulator/direct-stage smoke as a narrow "GE menu scales, TND placements" branch.
- User hardware feedback: save-select icons and text were missing, and everything else looked the same.
- Status: rejected/regressed. It was restored away from SC64. Do not build more menu-scale-only variants from this subset unless a specific draw call is identified.
- Evidence remains useful only as a negative result: `reports/tnd480i_t8040viewge_menu_subset_candidates_20260517.json`, `reports/smoke/smoke_t8040_menu_subsets_input_20260517.json`, `reports/smoke/smoke_t8040vmenuscales_problem_stages_20260517.json`, and `reports/tnd6480i_t8040vmenuscales_bps_manifest.json`.

Manual test focus for restored `t8040viewge`: continue from the stable gameplay baseline. For front/menu work, use the GE480i reference only as a visual target: GE-sized file/dossier shell, but preserve TND mission count and placements. Do not transplant broad `menu05_09` or scale-only subsets blindly.

Previous visual-fit gameplay baseline:

```text
artifacts/generated/t8040viewge.z64
MD5: 763f94bd1fb364e3d9eb8809bde4900b
N64 CRC: 84B7FA99 E50042D8
Patch MD5: 773dedd2d931426fde77652fa07d19e5
```

Latest hardware result for `t8040viewge`:

- Full ROM uploaded successfully with EEPROM 4k save. Startup capture reaches CMK/logos/gunbarrel/TND logo/opening cast. Known front/gunbarrel/logo issues remain.
- Direct-stage `p00bzr` / Bazaar reaches gameplay with Bond's hand visible and a more conservative vertical gameplay viewport than `t8040camge`.
- Direct-stage `p01pty` / Party reaches live rendered Party scenes on real N64.
- Direct-stage `p04hot` / Hotel and `p11vol` / Volcano render live without the sampled rainbow-prism failure class.
- Gopher64 direct-stage smoke for Bazaar, Party, Hotel, City, Volcano, and The End did not produce a hard emulator black-screen.
- Active-area comparison report: `reports/video_active_area_t8040viewge_vs_camge_20260517.json`. At 240x160 analysis scale, `t8040viewge` reduces the median active height for normal gameplay/camera samples from about 153-154 px to about 147 px on Bazaar/Party/Hotel, while preserving live rendering. This is the intended visual-fit tradeoff to evaluate on CRT/capture.

Manual fallback focus for `t8040viewge`: restore this candidate if `t8040vmenuscales` regresses gameplay/level booting. It is the current stable gameplay baseline before front/menu-scale work.

Previous visual/playability candidate:

```text
artifacts/generated/t8040camge.z64
MD5: 2d4033c68b875c90dc89dd70e1484fbb
N64 CRC: 84B7FAE5 32E2DC5F
Patch MD5: 789d845c37b2a2227aa9dc993bad890a
```

Purpose: keep the `tnd8040` framebuffer/playability breakthrough, then replace only the camera/cinema viewport height and animated-offset constants with the GE 480i reference values. User full-ROM feedback: all levels appear to load and boot correctly. Treat this as the fallback if `t8040viewge`'s more conservative normal gameplay viewport is visually worse or causes route regressions.

Previous playability base:

```text
artifacts/generated/tnd8040.z64
content source: artifacts/generated/t58fb8040.z64
MD5: 4f8798f2ec6dbf94e01688a1d4352133
N64 CRC: 84B7F80D 84B524C7
```

Purpose: keep the `tlbpages58` 007-label branch, but move the low framebuffer base/clear from `0x80300000` to `0x80400000`. This was the first candidate that changed the bad level class in the right direction: direct-stage hardware probes showed Party, City, The End/end-credits, Hotel, Volcano, Tower, and Boat reaching rendered scenes instead of the earlier black/prism/freeze classes.

Latest narrow misses on top of `tnd8040`:

- `t8040nr` NOPs `0xBBB8C` (`jal viSetFrameBuf2(resolution)`) but Party and The End still keep the same short top intro/title rectangle while booting into live scenes.
- `t8040camstk` restores only cameraBufferToggle viewport width/heights to stock TND, but Party still keeps the same short top intro/title rectangle.
- `t8040p56` lowers the TLB page wrap count from 58 to 56 to leave a 16 KB guard gap before `fb1`, but hardware direct `p01pty` appears to stall in the early Party intro view while `tnd8040` progresses farther in the same capture window. Report: `reports/stage_probes/direct_stage_t8040p56_hardware_20260517.json`. Treat as a regression and do not promote.
- `t8040frstk` / `t8040frblstk` restore front/menu VI words, with and without the shared title/sniper blitter rollback. Gopher64 direct `p01pty` goes essentially black (`reports/smoke/smoke_t8040_front_reverts_p01pty_20260517.json`), so do not upload them.
- `p01pty_aux_hwvi` attempted SC64 AUX VI-register telemetry from direct Party. The ROM was uploaded, SC64 debug listened through a Kasa power cycle, but the log only contains `Started`/`Stopped` and no AUX packets (`diagnostics/aux/p01pty_aux_hwvi_debug_20260517.txt`). Full `tnd8040` was restored afterward. Do not rely on AUX telemetry yet.

Current interpretation: `t8040viewge` is the gameplay baseline; `t8040vmenuscales` is the active front/menu-scale test layered on top. If `t8040vmenuscales` regresses gameplay, restore `t8040viewge`. If the whole `t8040viewge` line regresses in a way not previously observed, fall back to `t8040camge`, then `tnd8040`.

## Fallback Console State

The normal fallback candidate remains the `tlbpages58` 007-label build with short SC64 staging names:

```text
artifacts/generated/tnd58.z64
content source: artifacts/generated/game_h460_top10_stock_dossier_tlbpages58_007label_current.z64
MD5: 25cd6b104b4cbdf3b2cdf4e1d02354da
N64 CRC: 84B7FBED 3ED1CF90
```

Paired save:

```text
artifacts/generated/tnd58.sav
content source: artifacts/generated/game_h460_top10_stock_dossier_tlbpages58_007label_current.sav
MD5: 79ed3fe6851b080ff21de69fd12f034d
```

Purpose: restore the previous `tlbpages58` branch after `zbuf640hstock` regressed Bazaar. This branch preserves the current in-game-480i/camera-480i/007-label path, keeps the stock-start/no-fb1-overlap TLB page-count fix, and uses the generated all-missions EEPROM that previously matched this candidate.

Reports/evidence:

```text
reports/tnd480i_game_h460_top10_stock_dossier_tlbpages58_007label_current_report.json
reports/tnd480i_tlb_pagecount_candidates_20260517.json
reports/save_pairing_tlb_pagecount_all_missions_20260517.json
diagnostics/captures/videos/tnd58_shortname_restore_powercycle_startup_20260517.mp4
diagnostics/captures/contact_sheets/tnd58_shortname_restore_powercycle_startup_20260517.jpg
artifacts/generated/TND6480i_game_h460_top10_stock_dossier_tlbpages58_007label_from_baseline_tnd.bps
reports/tnd6480i_game_h460_top10_stock_dossier_tlbpages58_007label_bps_manifest.json
```

Verified BPS patch MD5: `7e576a51f9467c7a29374dfb7d65221a`.

Hardware startup evidence: SC64 accepted the short-name direct ROM and EEPROM 4k save upload, then a Kasa power-cycle plus GV-USB2 capture showed live CMK/logos/gunbarrel/title/opening-cast output.

Manual test focus for this restored ROM: confirm the generated save now loads, then use it as the fallback/control for Party/Credits/City, Hotel/Volcano, Tower/Boat, Labs, and Wreck/Bridge/Press/Alaska.

Important operational note: keep SC64 upload filenames short and same-stem from now on, even when `--save` is explicit. Use `artifacts/generated/tnd58.z64` / `tnd58.sav` style staging names to avoid filename-length or save-association ambiguity.

## Direct Stage Probe Workflow

Manual full-romhack passes are no longer the preferred test method. `scripts/build_direct_stage_probe_roms.py` now builds one short probe ROM per level from the current fallback candidate:

```text
python scripts/build_direct_stage_probe_roms.py
```

Generated outputs:

```text
artifacts/generated/stage_probes/p00bzr.z64  Bazaar
artifacts/generated/stage_probes/p01pty.z64  Party
artifacts/generated/stage_probes/p02lab.z64  Labs
artifacts/generated/stage_probes/p03prs.z64  Press
artifacts/generated/stage_probes/p04hot.z64  Hotel
artifacts/generated/stage_probes/p05prk.z64  Parkhaus
artifacts/generated/stage_probes/p06wrk.z64  Wreck
artifacts/generated/stage_probes/p07twr.z64  Tower
artifacts/generated/stage_probes/p08cty.z64  City
artifacts/generated/stage_probes/p09bot.z64  Boat
artifacts/generated/stage_probes/p10brg.z64  Bridge
artifacts/generated/stage_probes/p11vol.z64  Volcano
artifacts/generated/stage_probes/p12als.z64  Alaska
artifacts/generated/stage_probes/p13end.z64  The End
```

The builder patches only the early `bossMainloop` `-level_` debug-token parser (`0x6C94-0x6CA4`) to store a fixed `g_StageNum`, so this is a test harness rather than a public patch change.

Evidence:

```text
reports/stage_probes/direct_stage_probes_latest.json
reports/smoke/smoke_direct_p06wrk_20260517.json
diagnostics/captures/videos/direct_p06wrk_hardware_20260517.mp4
diagnostics/captures/contact_sheets/direct_p06wrk_hardware_20260517.jpg
```

Hardware result: `p06wrk` booted directly into Wreck on real N64 + SC64 after Kasa power-cycle. Gopher64 also reaches live Wreck rendering. `p01pty` reproduces the black/hard-hang path without menu input in Gopher64. This confirms the direct-stage harness is good enough to replace repeated manual dossier navigation for most troubleshooting.

Follow-up hardware matrix captured with the direct probes:

```text
reports/stage_probes/direct_stage_hardware_matrix_20260517.json
```

Key results:

- Bazaar and Labs boot into live gameplay through the standard blue transition rectangle.
- Party briefly reaches a first-person render, then falls to the blue rectangle and black.
- City and The End show the blue rectangle then black with no useful world render captured.
- Tower and Boat get past the transition rectangle into rendered scenes, which suggests their manual intro freezes are tied to transition/camera flow rather than basic stage-load failure.
- Hotel and Volcano boot into gameplay but reproduce the prism/blown-out render-state corruption class.

Current implication: stop treating the problem as one uniform "stage too large" failure. The next patch pass should focus on shared render/camera/VI state transitions and framebuffer/z-buffer ownership, with City/The End and Hotel/Volcano as separate signatures.

Follow-up memory-token hardware pass:

```text
scripts/build_stage_mem_budget_candidates.py
reports/tnd480i_stage_mem_budget_candidates_20260517.json
reports/stage_probes/direct_stage_mem_budget_hardware_20260517.json
```

Generated candidate families:

- `artifacts/generated/tnd58mem_mtdown.z64`: lowers only `-mt` texture-cache budgets for Party, Hotel, City, Volcano, and The End.
- `artifacts/generated/tnd58mem_gfxvtx_keep.z64`: raises `-mgfx`/`-mvtx` on the same failure groups while leaving `-mt`/`-ma` intact.
- `artifacts/generated/tnd58mem_gfxvtx_bal.z64`: raises `-mgfx`/`-mvtx` but lowers `-mt` enough to keep total named allocations near the current budget.

Hardware result: none of the memory-token variants fixed the failure groups. `gfxvtx_bal` still leaves Party as one live first-person frame followed by blue/black, City and The End as blue/black, and Hotel/Volcano as live prism/blown-out corruption. `mtdown` regresses Party and does not cure Hotel/Volcano/City. `gfxvtx_keep` also regresses Party and does not cure Hotel/Volcano. This effectively demotes simple per-stage `-mgfx`/`-mvtx`/`-mt`/`-ma` sizing as the root fix.

Current restored console state after that pass: `artifacts/generated/tnd58.z64` with `artifacts/generated/tnd58.sav`, direct ROM mode, EEPROM 4k. SC64 upload and `sc64deployer info` succeeded after restore.

Stock TND64 direct-stage control pass:

```text
reports/stage_probes/direct_stage_probes_stock_tnd.json
reports/stage_probes/direct_stage_stock_tnd_hardware_control_20260517.json
```

Control result: stock TND64 direct probes boot Party, Hotel, City, Volcano, and The End normally on real hardware. Party reaches the CMGN Launch Party title card and live stage view; City reaches Saigon Streets; The End reaches City of Hamburg; Hotel and Volcano render without the 480i prism/blown-out corruption. This confirms the direct-stage probe harness is valid for the same levels that fail on `tnd58`, and the failures are introduced by the 480i patch stack rather than direct-stage booting, save data, or the underlying stock TND level data.

Current restored console state after the stock-control pass: `artifacts/generated/tnd58.z64` with `artifacts/generated/tnd58.sav`, direct ROM mode, EEPROM 4k. SC64 upload and `sc64deployer info` succeeded after restore.

Rejected immediate diagnostic:

```text
artifacts/generated/game_h460_top10_stock_dossier_tlbpages58_zbuf640hstock_007label_current.z64
MD5: dfd0af4e1ca054ad940d18e3ba89f713
```

User feedback: the save did not load and Bazaar had the blue issue again. Treat `zbuf640hstock` as rejected/regressed. Do not upload `zbuf640h360` or `zbufstock` next without a fresh reason; reducing z-buffer height is now suspect.

Previous loaded diagnostic:

```text
artifacts/generated/game_h460_top10_stock_dossier_tlb806b6_camviewstock_007label_current.z64
MD5: 0562389b4409e062f5c3e154d7327642
N64 CRC: 84B7F759 2827B29D
```

Purpose: preserve the current known in-game-480i, TLB, dossier, and `Custom` -> `007` label path, but restore only four camera viewport return values to stock TND dimensions:

```text
0xBB7A4: camera viewport width 640 -> stock 440
0xBB89C: camera widescreen viewport height 480 -> stock 248
0xBB8B8: camera cinema viewport height 480 -> stock 190
0xBB8C0: camera fullscreen viewport height 480 -> stock 304
```

This candidate intentionally gives up broken camera/cutscene 480i geometry first, in favor of testing whether Party/Credits/Tower/Boat/City become playable when the camera path returns to stock-sized viewport dimensions.

Reports/evidence:

```text
reports/tnd480i_game_h460_top10_stock_dossier_tlb806b6_camviewstock_007label_current_report.json
reports/smoke/smoke_tlb806b6_camviewstock_007label_input30_20260517.json
reports/save_pairing_camera_guard_20260516.json
diagnostics/captures/videos/tlb806b6_camviewstock_007label_powercycle_startup_20260517.mp4
diagnostics/captures/contact_sheets/tlb806b6_camviewstock_007label_powercycle_startup_20260517.jpg
artifacts/generated/TND6480i_game_h460_top10_stock_dossier_tlb806b6_camviewstock_007label_from_baseline_tnd.bps
reports/tnd6480i_game_h460_top10_stock_dossier_tlb806b6_camviewstock_007label_bps_manifest.json
```

If retesting this previous `camviewstock` ROM later: Party and Credits first, because both showed the same top-rectangle flash before lock on `tlb806b6`/`noresfb`. Then test City, Tower intro, Boat intro, Hotel/Volcano prism, Labs encoder/door, and control stages. Expected tradeoff: level intro/camera cutscenes may be stock-sized/not 480i, but this is acceptable for that pass if it restores playability.

Previous diagnostic ROM:

```text
artifacts/generated/game_h460_top10_stock_dossier_tlb806b6_noresfb_007label_current.z64
MD5: d2f7ae37494601121deed50d50c6deb1
N64 CRC: 84B7E78B 4366546B
```

Purpose: preserve the previous known in-game-480i, TLB, and `Custom` -> `007` label path, but NOP only the `viSetFrameBuf2(resolution)` call in the `cameraBufferToggle` path at ROM offset `0xBBB8C`. The working theory is that the active camera viewport words are 640x480 while the original temporary `resolution` stage buffer is stock-sized; if the redirect fires during Party/Credits/Tower/Boat intros, a high-res render can overrun that small temporary buffer and corrupt level/cutscene memory.

Reports/evidence:

```text
reports/tnd480i_game_h460_top10_stock_dossier_tlb806b6_noresfb_007label_current_report.json
reports/smoke/smoke_tlb806b6_noresfb_007label_input30_20260516.json
reports/save_pairing_camera_guard_20260516.json
diagnostics/captures/videos/tlb806b6_noresfb_007label_powercycle_startup_20260516.mp4
diagnostics/captures/contact_sheets/tlb806b6_noresfb_007label_powercycle_startup_20260516.jpg
diagnostics/captures/videos/tlb806b6_noresfb_007label_noinput_followup_20260516.mp4
diagnostics/captures/contact_sheets/tlb806b6_noresfb_007label_noinput_followup_20260516.jpg
artifacts/generated/TND6480i_game_h460_top10_stock_dossier_tlb806b6_noresfb_007label_from_baseline_tnd.bps
reports/tnd6480i_game_h460_top10_stock_dossier_tlb806b6_noresfb_007label_bps_manifest.json
```

User hardware feedback: `noresfb` behaves the same as the previous `tlb806b6` candidate. Treat it as an informative miss: disabling only the `viSetFrameBuf2(resolution)` redirect did not resolve Party/Credits rectangle-locks or the broader cutscene/load failures, but no explicit regression was reported.

Previous active ROM:

```text
artifacts/generated/game_h460_top10_stock_dossier_tlb806b6_007label_current.z64
MD5: dabab8bad8b5ebee0f58f384102af658
N64 CRC: 84B7F875 89A76790
```

Purpose: preserve the previous known in-game-480i path and the `Custom` -> `007` label fix, while moving the Expansion Pak TLB page cache to `0x806B6000-0x80769FFF`. That range ends exactly before `fb1 = 0x8076A000-0x807FFFFF`, avoiding the old TLB/fb1 overlap while preserving `0xB6000` more stage memory than the earlier `tlb8060` canary.

SC64 upload and Kasa launch completed on 2026-05-16. A GV-USB2 S-video cold-boot capture shows the candidate alive through the early front/title path:

```text
diagnostics/captures/videos/tlb806b6_007label_powercycle_startup_20260516.mp4
diagnostics/captures/contact_sheets/tlb806b6_007label_powercycle_startup_20260516.jpg
reports/tnd480i_game_h460_top10_stock_dossier_tlb806b6_007label_current_report.json
reports/save_pairing_tlb806b6_007label_20260516.json
artifacts/generated/TND6480i_game_h460_top10_stock_dossier_tlb806b6_007label_from_baseline_tnd.bps
reports/tnd6480i_game_h460_top10_stock_dossier_tlb806b6_007label_bps_manifest.json
```

Paired all-missions save:

```text
artifacts/generated/game_h460_top10_stock_dossier_tlb806b6_007label_current.sav
MD5: 79ed3fe6851b080ff21de69fd12f034d
```

Immediate smoke on the previous active ROM: Gopher64 survived 75 seconds with the all-missions save and short input route (`reports/smoke/smoke_tlb806b6_007label_input30_20260516.json`). Hardware startup reaches CMK, TiJayFly, gunbarrel/title, and opening credits.

Latest user hardware feedback on this loaded ROM: Party now flashes a white rectangle shaped like the same too-short cutscene render area in the upper portion of the screen, then does not load. Credits behaves the same way as Party. Everything else appears to behave the same as the previous label-fixed in-game-480i fallback. This is a useful delta: the failure is now visibly touching the shared cutscene/camera render rectangle before locking, so prioritize the level-intro/camera framebuffer path over another broad memory-relocation attempt.

Next hardware test focus for this loaded ROM: Party/Credits rectangle-lock and City load failure first; then Tower/Boat intro freezes; then Hotel/Volcano prism; then Labs encoder/door freeze; finally Parkhaus/Wreck/Bridge/Alaska as controls. If this behaves worse than the previous fallback, restore `artifacts/generated/game_h460_top10_stock_dossier_tables_007label_current.z64`.

Latest hardware feedback on the previous restored fallback:

- Overall: font appears to render at the correct resolution, though it may sit slightly close to the upper-left corner.
- Bazaar: top and bottom flashing persists.
- Party: still refuses to load.
- Labs: freeze point is inconsistent; one run froze after picking up the encoder and trying the closed door, another froze immediately on grabbing the encoder. Top/bottom flicker appears reduced.
- Printworks: intro cutscene appears to take up more vertical screen space than before.
- Hotel: rainbow/prism issue persists.
- Parkhaus: appears fine.
- Wreck: appears fine.
- Tower: still freezes during the intro cutscene.
- City: still refuses to load.
- Boat: still freezes at intro cutscene.
- Bridge: fine.
- Volcano: rainbow/prism issue persists.
- Alaska: fine.
- Credits: does not load.

Current implication: keep this as the active in-game-480i fallback, but the next technical pass should target level-load/cutscene/framebuffer memory behavior. The pattern is not a simple menu-font issue: several ordinary gameplay stages are fine, while large/problem stages and intro/camera-heavy paths still fail or corrupt.

Rejected immediately prior probe:

```text
artifacts/generated/TND64_enh480i_ref_direct_split8030_dim0_007label_probe.z64
MD5: 513f2109d90a50f6f5092ae99475ddb5
SHA256: FF9F8A3F72EC71EDCB420468731D7E75325FCC12F369A7AA2A40918E3769FB9E
N64 CRC: B2E39E87 B1CE26F6
diagnostics/captures/videos/split8030_dim0_007label_powercycle_startup_20260516.mp4
diagnostics/captures/contact_sheets/split8030_dim0_007label_powercycle_startup_20260516.jpg
diagnostics/captures/current/after_split8030_dim0_007label_noinput_20260516.png
reports/title_custom_to_007_TND64_enh480i_ref_direct_split8030_dim0_007label_probe_20260516.json
reports/save_pairing_enh_ref_direct_007label_probes_20260516.json
artifacts/generated/TND6480i_enh_ref_split8030_dim0_007label_from_baseline_tnd.bps
reports/tnd6480i_enh_ref_split8030_dim0_007label_bps_manifest.json
```

The label fix worked on that enhanced-reference probe: a full scan of the ROM plus all `0x1172` compressed streams found `Custom` count `0`, and the user confirmed it showed `007`. However, the user also confirmed in-game was no longer 480i on hardware, so this branch is rejected for gameplay despite its clean emulator render.

The previously loaded narrow 007-label `tlb805c` canary is now a fallback/non-promoted branch:

```text
artifacts/generated/game_h460_top10_stock_dossier_tlb805c_007label_current.z64
MD5: a6a511de202b999c6d231f4b1efc3b66
N64 CRC: 84B77BB3 D6366555
```

Immediate hardware feedback before that label-only `tlb805c` change: `tlb805c` did not fix the broader playability issues. Labs showed the same top/bottom flicker pattern as Bazaar, and otherwise the user reported behavior was essentially the same. Treat `tlb805c` as a non-promoted canary for stability work unless a later test proves otherwise.

Prior TLB-cache relocation context, preserved for follow-up:

Key finding: the older "fb0 overlaps TLB cache" theory was incomplete. Direct ROM code initializes the page-cache base as `0x802F6000 + *(0x8000050C)`, and `0x8000050C` is `osMemSize - 0x400000`. On an 8 MB Expansion Pak console, that puts the 90-page TLB cache around `0x806F6000-0x807A9FFF`, overlapping the high framebuffer at `0x8076A000-0x807FFFFF`. The `tlb8060` canary changes that base math to `0x80200000 + expansion_delta`, moving the expected 8 MB cache range to `0x80600000-0x806B3FFF`, below the high framebuffer.

Direct instruction edits in this canary:

```text
ROM 0x241C: 3C08802F -> 3C088020
ROM 0x2420: 25086000 -> 25080000
```

Hardware evidence:

```text
diagnostics/captures/current/after_tlb8060_upload_boot_wait12_20260516.png
diagnostics/captures/current/after_tlb8060_upload_boot_wait32_20260516.png
diagnostics/captures/videos/tlb8060_noinput_boot_20260516.mp4
diagnostics/captures/contact_sheets/tlb8060_noinput_boot_20260516.jpg
diagnostics/captures/current/post_reboot_tlb8060_state_20260516.png
reports/smoke/smoke_tlb8060_current_process_input45_20260516.json
reports/tnd480i_tlb_cache_candidates_20260516.json
reports/save_pairing_tlb_candidates_20260516.json
reports/smoke/smoke_tlb8060_savebacked_input30_20260516.json
reports/smoke/smoke_tlb805c_savebacked_input30_20260516.json
diagnostics/captures/contact_sheets/tlb8060_savebacked_input30_20260516.jpg
diagnostics/captures/contact_sheets/tlb805c_savebacked_input30_20260516.jpg
artifacts/generated/TND6480i_game_h460_top10_stock_dossier_tlb8060_from_baseline_tnd.bps
reports/tnd6480i_game_h460_top10_stock_dossier_tlb8060_bps_manifest.json
artifacts/generated/TND6480i_game_h460_top10_stock_dossier_tlb805c_from_baseline_tnd.bps
reports/tnd6480i_game_h460_top10_stock_dossier_tlb805c_bps_manifest.json
```

Post-reboot capture still shows live first-person/demo gameplay, so the PC reboot did not clear the running direct ROM. Known visual issues remain: top-band/prism-like corruption is still visible, and this canary was not intended to fix front/menu/gunbarrel/cutscene scaling. User later played Bazaar through to Party on hardware; Party still black-screened/locked, so `tlb8060` did not resolve that level load failure.

User observation to preserve: emulator timing can be a clue even when the visual layout is not fixed. If TiJayFly/logo/front sequences run slower than stock, that can indicate the interlaced path is active, because emulators often expect the game's internal timing/resolution to remain stock. Do not classify a candidate as "not 480i" solely from ugly front composition if cadence/timing has shifted.

Save handling is now explicit. `scripts/prepare_save_for_rom.py` pairs the complete EEPROM save with candidate ROMs by writing same-stem `.sav` and padded `.eep` files beside the ROM, by writing Gopher64's hashed `GOLDENEYE-<ROM_SHA256>.eep` save file, and optionally by writing Parallel Launcher's same-stem `.srm` file into its RetroArch save directory when given `--parallel-srm-template`. The source save remains:

```text
C:\Users\codex\Documents\007 - Tomorrow Never Dies (USA).sav
size: 512 bytes
MD5: f02bb8224a4dc25079721d7a3f0d38e0
```

The current `split8030_dim0_007label` probe and prior `tlb8060`/`tlb805c` candidates all have paired saves. For future SC64 uploads, include an explicit same-stem `.sav` and `--save-type eeprom4k`; do not rely on SC64 save autodetection for this project.

Parallel Launcher save placement for the current pair:

```text
C:\Users\codex\AppData\Local\parallel-launcher\data\retro-data\saves\game_h460_top10_stock_dossier_tlb8060_current.srm
C:\Users\codex\AppData\Local\parallel-launcher\data\retro-data\saves\game_h460_top10_stock_dossier_tlb805c_current.srm
reports/save_pairing_all_targets_refresh_20260516.json
```

Kasa note: avoid using `KasaCmd.exe` unless explicitly needed. Its help/error path opened the vendor's Ko-fi page in Vivaldi, so stick to SC64/Gopher/files for routine work.

Emulator tooling is restored at:

```text
tools/emulators/gopher64.exe
gopher64 v1.1.20
SHA256: D006DBC6DA39E9DA28C21024360256D6ED8109956994BDAAA62A18E551D9CE8F
```

Use short input bursts for emulator smoke tests. Long Start/A mashing continues into gameplay and pollutes the visual evidence by opening/closing the watch/pause screen, which makes Bond appear to nod. Current clean smoke route:

```powershell
python scripts\smoke_gopher64.py <rom.z64> --gopher tools\emulators\gopher64.exe --seconds 75 --input --input-until 30 --tap-interval 0.55 --ffmpeg C:\Users\codex\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe --capture-times 20,35,50,65
```

Highest-value manual test pass for the currently loaded ROM:

1. Party, City, and The End: do they load now, or still hard-lock?
2. Tower and Boat: do intro crashes change?
3. Labs: does recorder pickup still freeze?
4. Hotel and Volcano: does the prism/rainbow corruption change?
5. Press, Parkhaus, Wreck, Bridge, Alaska: confirm they still play as controls.

If the current `split8030_dim0_007label` probe still shows the same level-specific hard locks, keep the following prior `tlb805c` build as a fallback/reference, not as the next likely fix:

```text
artifacts/generated/game_h460_top10_stock_dossier_tlb805c_current.z64
MD5: 11a3594b1c27e96c4b6fd976a3c21080
N64 CRC: 84B77BB3 D6366555
```

Do not return first to framebuffer relocation variants. `game_h460_top10_stock_dossier_fb1_8066_current.z64` black-screened on real N64, and later Gopher visual captures became unreliable; the better current theory is to leave the fragile framebuffers in place and move the TLB cache away from them.

Patch artifact status: classic IPS is not suitable for these current expanded targets because the target ROM is `0x101A680` bytes, beyond the simple 16 MiB baseline and IPS's normal 24-bit offset range. `scripts/make_bps_patch.py` now creates and verifies BPS patches. Current verified BPS artifacts:

```text
artifacts/generated/TND6480i_game_h460_top10_stock_dossier_tlb8060_from_baseline_tnd.bps
MD5: d7b00e9f4ea8b0cb43452cc85d6c0aa8
SHA256: 12e73f78c61f7fc26087be85e5035198286606d745d5d91fa0345d24b49ef4bc

artifacts/generated/TND6480i_game_h460_top10_stock_dossier_tlb805c_from_baseline_tnd.bps
MD5: 3e2b918632b019d67383d068d2821378
SHA256: 54b440fd16c80e128c97c51520078a95fd994af73724021436001b4eb4cd1f3f
```

Both are generated from `artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64` (`MD5 1ee22dd1d70443f5e4766d4238756949`) and self-verified by applying back to the target bytes.

### Historical 2026-05-11 h460/top10 State

At that point, SC64 was in direct-ROM mode with EEPROM 4k and had the gameplay-first playability canary loaded:

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

Hardware feedback on this canary:

- Bazaar vertical fit is somewhat better; the character dialogue box at the top fits better.
- Top/bottom flicker did not noticeably improve.
- Pause/watch is usable and appears correctly formatted, but still flickers.
- Countdown timer is misaligned left instead of centered at the bottom.
- Party still does not load; it reaches audio and then fails/crashes on hardware.

Broader user level test matrix on the same active canary:

- Overall: all level intro/outro cutscenes render at a proportionally too-small height; text is not at the same clean resolution/scale as the stock 480i patch, especially on hardware. The intro character/credits cards also run offscreen.
- Current emulator route probes into non-Bazaar missions show the same camera/cutscene top-rectangle failure and partial/missing world geometry. Treat "objects not rendering" as part of the camera/cutscene render-path bug until proven otherwise.
- Bazaar: top/bottom flicker remains and appears to be Bazaar-specific.
- Party: does not load.
- Labs: playable until grabbing the encoder, then appears to freeze.
- Press: most playable level so far; no obvious first-glance issue.
- Hotel: severe flashing/rainbow prism effect that is painful to view; dossier text misalignment makes selection impossible.
- Parkhaus: similar to Press; playable.
- Wreck: playable.
- Tower: crashes during the intro cutscene.
- City: crashes before the cutscene loads, similar to Party.
- Stealth Ship: same selection issue as Hotel; because City is not playable, it is effectively blocked.
- Bridge: appears to run fine.
- Volcano: prism issue similar to Hotel but slightly less severe.
- Alaska / Shadow Moses Island: appears to run fine.
- The End: does not load, similar to Party and City.

Implication: do not spend the next pass on another tiny Bazaar viewport crop. The highest-value next comparison is to test the same save/levels against the stable rollback ROM and then the unpatched/enhanced TND base. If the same levels fail only on the 480i branch, isolate load/freezes around the framebuffer/VI allocation and camera/cutscene viewport patch stack. If they fail on base TND64, separate romhack bugs from 480i bugs before patching.

Credit-aware test plan:

1. Use the imported complete save to run short emulator probes first, not fresh hardware uploads.
2. Compare only three reference ROMs at first: current canary, stable gameplay/pause rollback, and base/enhanced TND.
3. Prioritize representative levels rather than every level immediately:
   - Press/Bridge/Alaska as good controls.
   - Bazaar for flicker/fit.
   - Party/City/The End for load failure.
   - Tower for intro crash.
   - Labs for encoder freeze.
   - Hotel/Volcano for prism corruption.
4. Use hardware only after emulator says which failures are unique to the 480i branch.

## 2026-05-12 Emulator A/B Cutscene Finding

Short save-backed Gopher64 route probes compared the current canary, the stable rollback, and the base/enhanced TND reference on the same early mission route.

Result:

- `game_h460_top10_current.z64` and the stable gameplay/pause rollback both show the cutscene/camera path rendered as a top rectangle with missing/partial world geometry.
- `artifacts/roms/TND64_enh480i_core_no_menu_pigz.z64` renders the same scene across the normal frame in emulator.
- Therefore the cutscene/object issue is not caused by the tiny `h460/top10` gameplay crop. It is inherited from the older 480i framebuffer/camera/viewport stack.

Evidence:

```text
diagnostics/captures/gopher64/route_s1_h460_20260512/game_h460_top10_current_t048p0s.png
diagnostics/captures/gopher64/ab_route_TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_reserve58000_core_no_menu_20260512/TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_reserve58000_core_no_menu_t048p0s.png
diagnostics/captures/gopher64/ab_route_TND64_enh480i_core_no_menu_pigz_20260512/TND64_enh480i_core_no_menu_pigz_t048p0s.png
```

Generated but do not promote/upload yet:

```text
artifacts/generated/game_h460_top10_camheightstock_current.z64
MD5: 1ffb6619346bfb709bbe51fd8cfd9dd0
N64 CRC: CD67966A 710E39F3
```

This candidate changes only the three camera viewport-height words (`0xBB89C`, `0xBB8B8`, `0xBB8C0`) back to stock TND values. The Gopher64 route did not produce a clean comparable cutscene; a confirm-spam retry produced black/invalid captures while the process stayed alive. Treat it as inconclusive/offline, not a hardware candidate.

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

## Clean Handoff ROMs

Most relevant current test ROM:

```text
artifacts/generated/game_h460_top10_current.z64
MD5: 892cbd5e8253e9cc3c6c4c4645bd69c0
N64 CRC: CD679836 961D35FD
```

Most stable gameplay/pause rollback ROM:

```text
artifacts/generated/TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_reserve58000_core_no_menu.z64
MD5: 17d4ea3194d02d5ea121b1e42aa59469
N64 CRC: CD6799DE DAD61991
```

Use the rollback ROM if the next experiment makes gameplay, saves, or pause/watch worse. Do not use the later gunbarrel/menu branches as gameplay baselines.

## Save State

The complete EEPROM save supplied by the user is:

```text
C:\Users\codex\Documents\007 - Tomorrow Never Dies (USA).sav
size: 512 bytes
MD5: f02bb8224a4dc25079721d7a3f0d38e0
```

It was imported into Gopher64 by padding it to 2048 bytes and writing it to the per-ROM `.eep` files for `game_h460_top10_current`, the stable rollback ROM, `TND64_enh480i_core_no_menu_pigz`, and `BASELINE_TND64_Expanded_direct_from_stock`. Existing Gopher saves were backed up with a timestamp suffix before overwrite.

Current emulator route status: Start/A automation with the imported save reliably reaches Bazaar, but has not yet found a reliable Party selection route. `reports/smoke/smoke_party_route_probe2_h460_downspam_20260511.json` survived 95 seconds but still landed in Bazaar.

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

Historical result at the time: promoted for gunbarrel/front cadence only. Compared with `gamefulltop0_gbslow_shared_blitter_stock_texture_setup`, the early doubled white aperture/dot phase is reduced while preserving the slow/GE-like cadence. Later gameplay testing superseded this branch; do not use it as the gameplay baseline.

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
python scripts\prepare_save_for_rom.py <rom.z64> --manifest reports\save_pairing_<candidate>.json
& C:\Users\codex\Documents\n64\sc64deployer.exe upload --direct --save-type eeprom4k --save "C:\Users\codex\Documents\007 - Tomorrow Never Dies (USA).sav" <rom.z64>
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

## 2026-05-12 Dossier Stock-Revert Probes

User feedback: `game_h460_top10_current.z64` is still the best overall candidate, but the mission-select dossier remains badly aligned. The requested low-cost direction is to leave gameplay alone and revert the broken dossier/front text toward stock rather than keep chasing full 480i menu polish.

Built on `artifacts/generated/game_h460_top10_current.z64`:

```text
artifacts/generated/game_h460_top10_stock_dossier_tables_current.z64
MD5: f8d146a4a9edd57a2dd2169a4aa9bd21
N64 CRC: 84B7F86D A3B63A65
```

This is the first hardware test candidate. It reverts only the compressed front/menu display tables at raw main offsets `0x9C3C-0x9D24` and `0xA240-0xA264` to stock TND values. The current gameplay crop words at `0xBB91C`, `0xBB954`, and `0xBBA80` are unchanged, as are the direct front 480i words, watch/pause/HUD text work, and the already-rejected `J_mission_select_text_480i` offsets. Gopher no-input capture was inconclusive because the unmodified `game_h460_top10_current.z64` produced the same black capture behavior in the current RDP/Gopher capture path.

Hardware result: promote as current best. User reported the mission text misalignment appears resolved, and the ROM appears to keep the same level stability as the previous h460/top10 baseline. Hotel still has the rainbow/prism flashing issue, and Stealth Boat freezes during the intro cutscene. The file-select screen background remains misaligned and does not match stock TND64 or the stock 480i patch; fix that next as a narrow file-select/background pass.

Fallback only if the table-only candidate still has unusable dossier/classification layout:

```text
artifacts/generated/game_h460_top10_stock_front_dossier_current.z64
MD5: b712eee26aca645d225b7cbf3d449cc3
N64 CRC: 84B7F529 15121F51
```

This broader fallback also restores direct front/menu sizing words at `0x4DAE0`, `0x4DAE8`, `0x4DAEC`, `0x4DAF4`, `0x106ED4`, `0x106EE4`, `0x106EF0`, `0x106F10`, and `0x106F24` to stock. It is more likely to make front screens stock-looking, but it changes more of the front path, so do not test it before `stock_dossier_tables`.

Hardware result: reject. User reported it regressed too hard and made the Bazaar-style blue outline render issue appear on Wreck, which previously worked. Do not use this as a base.

Current screen taxonomy to keep in mind for future context gathering: Board classification, TJ logo, Rare logo, right-moving white circle effect, left-moving gunbarrel, intro character credits, dossier/file select, singleplayer/multiplayer/cheats screen, mission-select dossier, difficulty select, briefing/objectives, level intro, in-game, pause/watch, level outro, and mission-complete dossier.

## 2026-05-12 LightCapture Reference Videos

User recorded four hardware reference clips in the LightCapture output folder under `Documents`:

```text
1. GoldenEye 007.mpg
2. GoldenEye 480i.mpg
3. Tomorrow Never DIes 64.mpg
4. Tomorrow Never Dies 6480i.mpg
```

All are MPEG2 `720x480`, `29.97fps`, top-field-first interlaced captures from GV-USB2/S-video. The TND6480i clip is confirmed to be `game_h460_top10_stock_dossier_tables_current.z64`, now the current best base.

TND6480i timestamp index:

```text
00:00 CMK Board Game of Classification - unsure
00:04 TiJayFly Logo - unsure
00:12 Rare Logo - unsure
00:16 Gunbarrel - not 480i
00:37 TND Logo - not 480i
00:41 Opening Credits - not scaled right / runs offscreen compared to regular
01:14 File Select Dossier Screen - not 480i
01:28 Single/Multiplayer/Cheat Select - not 480i
01:38 Mission Select - not 480i
01:46 Difficulty Select - not 480i
01:55 Mission Briefing - not 480i
02:01 Bazaar - 480i with top/bottom flickering
03:40 Party - does not load; appears to hard-lock console and requires power cycle
04:17 Labs - crashes/freezes upon recorder pickup; item-get sound can be heard; reset is enough to recover
06:44 Press - seems to work fine
09:50 Hotel - rainbow/prism flashing corruption
10:56 Parkhaus - seems to work fine
13:32 Wreck - seems to work fine
16:04 Tower - crashes during level intro; reset is enough to recover
16:48 City - does not load; appears to lock up and requires power cycle
17:39 Boat - crashes during level intro
18:09 Bridge - seems to work fine
24:25 Volcano - rainbow/prism flashing corruption
25:00 Alaska - seems to work fine
```

Use this clip as an atlas for screen-family analysis and avoid brute-force hardware uploads. The user's highest priority is now making the rest of the romhack playable. The only front-end/menu fix to preserve is the already-promoted dossier table stock revert; other non-pause menu scaling can wait. All level cutscenes are still vertically too short / compressed, so cutscene framing remains part of the active playability problem rather than postponed front-end polish. Next analysis should compare working levels (`Press`, `Parkhaus`, `Wreck`, `Bridge`, `Alaska`) against failing/corrupt levels (`Party`, `Labs recorder pickup`, `Hotel`, `Tower intro`, `City`, `Boat intro`, `Volcano`) and identify whether the breakage is tied to level intro/camera paths, framebuffer selection, or level-specific assets/effects.

## 2026-05-16 Cooldown Resume

Hardware is reconnected and live. GV-USB2 capture succeeds from `GV-USB2, Analog Capture`, and the fresh resume frame shows the SummerCart64 menu rather than a blue/no-signal state:

```text
diagnostics/captures/current/resume_live_gvusb2_20260516_2.png
```

Current best ROM remains:

```text
artifacts/generated/game_h460_top10_stock_dossier_tables_current.z64
MD5: f8d146a4a9edd57a2dd2169a4aa9bd21
N64 CRC: 84B7F86D A3B63A65
```

Added a reusable LightCapture atlas builder:

```text
scripts/build_lightcapture_atlas.py
reports/video_atlas/tnd6480i_lightcapture_atlas_20260516.json
diagnostics/captures/contact_sheets/lightcapture_20260516/tnd6480i_screen_atlas_20260516.jpg
diagnostics/captures/contact_sheets/lightcapture_20260516/tnd6480i_level_probe_20260516.jpg
```

First atlas read:

- The dossier/menu table revert should stay: file/mission text alignment is visibly better than the rejected broader front revert path.
- The level intro/cutscene problem is still distinct from ordinary gameplay. Several level-start frames show the briefing/dossier, while early cutscene frames show a short active render strip before gameplay fills roughly the 460-line active area.
- Party, City, and Boat frames in the recorded clip fall back to SC64/menu/file-select shortly after their start points, matching user reports that those paths crash or lock.
- Hotel and Volcano show the most obvious severe color/prism corruption in the level probe sheet.
- Resume direction: do not upload a new ROM until an offline/emulator delta points at a small change. Work from `game_h460_top10_stock_dossier_tables_current.z64`, preserve the dossier table stock revert, and isolate level/cutscene/framebuffer state before revisiting gunbarrel/front-end polish.

## 2026-05-16 Camera View Stock Hardware Candidate

Built three narrow current-best derivatives with:

```text
scripts/build_current_camera_revert_candidates.py
```

Current hardware-loaded candidate:

```text
artifacts/generated/game_h460_top10_stock_dossier_camviewstock_current.z64
MD5: c36342a91e41edf2efa0f8df0c7c24c5
N64 CRC: 84B7F741 9A97BB46
Report: reports/tnd480i_game_h460_top10_stock_dossier_camviewstock_current_report.json
```

This ROM is based on the promoted `game_h460_top10_stock_dossier_tables_current.z64` and changes only four camera-mode viewport words back to stock TND values:

```text
0xBB7A4: camera viewport width 640 -> stock 440
0xBB89C: camera widescreen viewport height 480 -> stock 248
0xBB8B8: camera cinema viewport height 480 -> stock 190
0xBB8C0: camera fullscreen viewport height 480 -> stock 304
```

It deliberately preserves the current dossier table revert and the non-camera gameplay `h460/top10` crop words.

Hardware actions completed:

- Confirmed SC64 menu and GV-USB2 were live after reboot: `diagnostics/captures/current/resume_sc64_menu_check_20260516_after_reboot.png`.
- Uploaded `game_h460_top10_stock_dossier_camviewstock_current.z64` with SC64 direct boot / EEPROM 4k.
- Kasa GUI automation successfully power-cycled the N64 through the installed Kasa app.
- Boot capture after power cycle reached the title/opening path: `diagnostics/captures/current/after_kasa_cycle_camviewstock_wait12_20260516.png`.
- A 75s no-input GV-USB2 clip showed the ROM continuing through/looping front/title screens without immediate boot crash:
  - `diagnostics/captures/videos/camviewstock_noinput_boot_20260516.mp4`
  - `diagnostics/captures/contact_sheets/camviewstock_noinput_boot_20260516.jpg`

Manual hardware test priority for this loaded ROM:

1. Bazaar: confirm normal gameplay still has the same or better viewport/pause/watch behavior as current best.
2. Level intro/cutscene height: check whether the top-rectangle/compressed cutscene issue changes.
3. Party, City, Boat: check whether load/crash behavior changes.
4. Hotel and Volcano: check whether the rainbow/prism corruption changes.
5. Labs: check whether recorder pickup still freezes.

Do not promote yet. This is a focused camera-path diagnostic candidate, not a finished patch.

## 2026-05-16 Save / Party Follow-Up

The user reported that a physical power cycle recovered the console, but the save did not appear to load as expected and Party still froze. SC64 EEPROM dumping showed the uploaded save image was reaching the cart, but the source save in Documents was effectively blank: valid checksums, valid folders, but zero mission-time bytes. That made it poor for direct later-level testing.

Added a deterministic test-save builder:

```text
scripts/make_tnd_test_save.py
artifacts/generated/tnd_test_all_missions.sav
reports/tnd_test_all_missions_save_20260516.json
```

The generated save preserves the four valid folders and spare wear-level slot, fills each active folder's mission-time region with nonzero values, and recomputes the GoldenEye/TND EEPROM CRCs. Gopher64 confirms it is visible at file select as completed folders.

Staged this save beside the active baseline and TLB canaries:

```text
reports/save_pairing_all_missions_20260516.json
artifacts/generated/game_h460_top10_stock_dossier_tables_current.sav
artifacts/generated/game_h460_top10_stock_dossier_tlb805c_current.sav
artifacts/generated/game_h460_top10_stock_dossier_tlb8060_current.sav
```

Uploaded the next narrow hardware candidate:

```text
artifacts/generated/game_h460_top10_stock_dossier_tlb805c_current.z64
MD5: 11a3594b1c27e96c4b6fd976a3c21080
N64 CRC: 84B77BB3 D6366555
Paired save: artifacts/generated/game_h460_top10_stock_dossier_tlb805c_current.sav
```

SC64 accepted the upload and save, but the N64 was still black/locked from the previous Party freeze. `sc64deployer reset` only changed SC64 back to menu boot mode internally; GV-USB2 remained black. The candidate was re-uploaded after that reset, and `sc64deployer info` again shows `ROM (direct)` plus `EEPROM 4k`. The next physical action needed is a real N64 reset or power cycle; after that, test whether file select shows completed folders and launch Party from the completed save.
