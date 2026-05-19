# Current Candidate Status - 2026-05-19

Current best hardware candidate:

- ROM: `artifacts/generated/g1mcfix1.z64`
- Save: `artifacts/generated/g1mcfix1.sav`
- EEPROM mirror: `artifacts/generated/g1mcfix1.eep`
- BPS: `artifacts/generated/TND6480i_g1mcfix1_from_baseline_tnd.bps`
- ROM MD5: `32b0802210e71fecdf4a0a524b705aef`
- Patch MD5: `407738ef49c3227ab9dafb50aac5f348`

Convenience copies:

- `artifacts/generated/TND6480i_current_g1mcfix1.z64`
- `artifacts/generated/TND6480i_current_g1mcfix1.sav`
- `artifacts/generated/TND6480i_current_g1mcfix1.eep`
- `artifacts/generated/TND6480i_current_g1mcfix1_from_baseline_tnd.bps`

`g1mcfix1` is `g1cred1` plus the GE480i mission-complete statistics spacing deltas:

- `0x4C564: 240C0037 -> 240C0050`
- `0x4C56C: 25AE00F4 -> 25AE0140`
- `0x4C5EC: 240B0082 -> 240B009B`
- `0x4C5F4: 258D00F4 -> 258D0140`

The binary diff from `g1cred1` is only those four words plus the N64 header CRC words.

## Hardware Evidence

Current screen coverage atlas and spelling pass:

- `diagnostics/captures/current/g1mcfix1_screen_coverage_atlas_20260519.jpg`
- `reports/g1mcfix1_screen_coverage_atlas_20260519.json`

Mission-complete statistics comparison:

- `diagnostics/captures/current/g1mcfix1_mission_result_stats_comparison_20260519.jpg`
- `reports/g1mcfix1_mission_result_stats_comparison_20260519.json`
- Live probe: `diagnostics/captures/current/g1mcfix1_live_now_screen_probe_20260519.png`

Startup and dossier route evidence inherited from `g1cred1` because `g1mcfix1` only touches mission-complete statistics:

- Startup sheet: `diagnostics/captures/contact_sheets/g1cred1_full_startup_1fps_20260519.jpg`
- Route frames: `diagnostics/captures/current/g1cred1_route_frames_20260519/`

## Current Read

Pass or likely-pass:

- Gameplay, pause/watch menu, bullets UI, Bazaar, Labs, and all level boot stability remain inherited from the latest user-verified good build.
- File select, mode select, mission select, difficulty, and briefing/background dossier pages match the GE480i layout family in the current route captures.
- The opening title/logo/gunbarrel/cast screens have current evidence in the new atlas.
- The mission-complete statistics overlap is fixed live on GV-USB2.
- Visual spelling pass found no visible current-screen typos. The `DIes` typo is only in a local capture filename, not on the Tomorrow Never Dies title screen.

Still needs manual proof:

- Full end-credits crawl, because one sampled frame cannot prove every credit line.
- Mission failed/aborted result pages, which were not captured in this pass.
- Final normal-controller walkthrough through dossier -> mission -> gameplay -> completion on real hardware before release tagging.

## Rejected Or Diagnostic

- `g1hbrf1`: superseded by `g1cred1` and `g1mcfix1`.
- `g1hlegal1`: rebuilt the legal/classification stream but did not improve behavior.
- `g1hnext1`, `g1tabhit1`, `g1cred1`: important intermediate fixes now included in `g1mcfix1`.
- Route helper ROMs such as `brfauto*`, `brfbtn*`, and `g1mcfix1auto0d` are diagnostic-only and should not be release candidates.

## Next Work Order

1. Treat `g1mcfix1` as the active candidate.
2. Use the new coverage atlas as the checklist for any final visual review.
3. Capture missing manual-only screens if they appear during play: failed mission, aborted mission, and more end-credit lines.
4. If no new issue appears in a full walkthrough, generate the final release patch from `TND6480i_g1mcfix1_from_baseline_tnd.bps`.
