# Runtime Text Measurement Attempt - 2026-05-25

Purpose: build an objective test for the Analogue 3D report that TND6480i
mission text, HUD numbers, and pause/watch text still look stock-resolution
compared with the GE480i enhanced patch.

Final 2026-05-25 status: the current `g1hiq3_gegate` line passed user
hardware/Analogue review for font quality when paired with the normalized
ammo-on save. The same line also corrected the Bazaar countdown timer position.
Keep this document as the measurement history and regression-gate reference.

## Stable Baseline

- Current stable/playable ROM: `artifacts/generated/g1hiq3_gegate.z64`
- Paired save: `artifacts/generated/g1hiq3_gegate.sav`
- Text/HUD comparison save with ammo display enabled:
  `artifacts/generated/g1hiq3_gegate_ammoon.sav`
- Font-good short-name test bundle:
  `artifacts/release/TND6480i_g1hiq3_fontgood_20260525_test.zip`
- Console was restored to this ROM after the diagnostic attempts.

## What Was Tried

### Gopher64 RDRAM Text-Call Logger

New tooling:

- `scripts/build_rdram_textcall_logger.py`
- `scripts/parse_rdram_textcall_ring.py`
- `scripts/build_rdram_boot_marker_probe.py`

Findings:

- The first RDRAM logger build wrote to a stale/non-writable `0x7F...` target.
- The logger was corrected to write to uncached `KSEG1` RDRAM (`0xA0...`), so
  cache writeback should not hide the marker from raw dumps.
- Direct-stage Gopher launches did not execute the direct-stage boot patch site.
  The boot marker probe produced no `TBMK/BOOT` marker in RDRAM.
- Because Gopher is not reaching the direct-stage route, these dumps cannot be
  used to judge pause/watch text calls.

Useful artifacts:

- `artifacts/generated/text_probe_v7/ge480i_txlr_kseg1.z64`
- `artifacts/generated/text_probe_v7/tnd_g1hiq3_txlr_kseg1.z64`
- `artifacts/generated/text_probe_v7/ge480i_bootmarker.z64`
- `artifacts/generated/text_probe_v7/tnd_g1hiq3_bootmarker.z64`
- `diagnostics/rdram/ge480i_txlr_kseg1_35s.rdram.bin`
- `diagnostics/rdram/ge480i_bootmarker_10s.rdram.bin`

### SC64 Text-Call Ring

New/updated tooling:

- `scripts/build_sc64_textcall_ring_logger.py`
- `scripts/parse_sc64_textcall_ring.py`

Findings:

- The SC64 logger now supports dynamic executable caves, so GE480i and TND can
  be instrumented with the same hook structure.
- `sc64deployer dump 0x05000000 0x3000` is rejected by the deployer; `0x800`
  bytes succeeds.
- The successful `0x800` dumps show stale/unrelated data, not the `TXLG` text
  ring header. This matches older notes that direct CPU stores to the SC64 data
  buffer are not a reliable telemetry path for this project.
- Direct-stage hardware probes did launch, but the no-controller Wreck/Alaska
  routes sat in level intro/camera scenes and did not reach pause/watch text.

Useful artifacts:

- `artifacts/generated/diag_ge480i_autowatch_textcall_ring_sc64.z64`
- `artifacts/generated/diag_tnd_g1hiq3_autowatch_textcall_ring_sc64.z64`
- `artifacts/generated/diag_tnd_g1hiq3_wreck_autowatch_textcall_ring_sc64.z64`
- `diagnostics/sc64/diag_tnd_g1hiq3_wreck_autowatch_textcall_ring_0800_20260525.bin`
- `diagnostics/captures/current/tnd_wreck_textcall_diag_live_20260525.png`
- `diagnostics/captures/current/tnd_wreck_textcall_diag_live_120s_20260525.png`
- `diagnostics/captures/current/restored_g1hiq3_after_textdiag_20260525.png`

### Force-FP Watch Capture Harness

New/updated tooling:

- `scripts/build_force_fp_watch_probe.py`
- `scripts/build_auto_watch_text_probe.py` now accepts `--delay-frames`

Findings:

- Hooking `bondviewProcessInput` alone was too early for no-controller direct
  stage tests: the watch trigger fired while the level was still in an intro or
  frozen-camera state.
- Hooking `bondviewFrozenMoveBond` at `0x0BB574` proved useful because that path
  runs during the intro/cinema player tick after player state exists. The first
  probe successfully forced Wreck/Frigate out of the intro route into
  first-person rendering.
- The working harness combines both hooks:
  - `bondviewFrozenMoveBond` forces `CAMERAMODE_FP` at frame 180.
  - `bondviewProcessInput` triggers `trigger_solo_watch_menu(0)` at frame 260.
- This produced no-controller watch/pause captures on real N64 + SC64 + GV-USB2
  for both GE480i and TND6480i.
- SC64 still cannot directly dump N64 RDRAM. `sc64deployer dump 0x80000000 ...`
  is rejected because the command is limited to SC64 memory space, so live
  display-list/RDRAM inspection still requires an emulator, a game-side
  telemetry path, or a different debug transport.

Useful artifacts:

- `artifacts/generated/force_fp_watch_probe_v3/GE480i.z64`
- `artifacts/generated/force_fp_watch_probe_v3/TND6480i.z64`
- `reports/measurement/force_fp_watch_probe_v3_20260525.json`
- `diagnostics/captures/videos/force_fp_watch_ge480i_v3_20260525.mp4`
- `diagnostics/captures/videos/force_fp_watch_tnd6480i_v3_20260525.mp4`
- `diagnostics/captures/contact_sheets/force_fp_watch_ge480i_v3_20260525.jpg`
- `diagnostics/captures/contact_sheets/force_fp_watch_tnd6480i_v3_20260525.jpg`
- `reports/measurement/force_watch_text_metrics_ge_vs_tnd_v3_t50_20260525.json`
- `diagnostics/captures/measurement/force_watch_text_metrics_ge_vs_tnd_v3_t50_20260525.png`
- `diagnostics/captures/current/restored_g1hiq3_after_force_watch_probe_20260525.png`

Metric snapshot from the matched watch page capture, using GE480i as the
reference:

| Crop | TND line-pair ratio | TND Laplacian ratio | Notes |
|---|---:|---:|---|
| `watch_top_text` | `0.93x` | `3.68x` | Top watch labels are in the same detail class through S-Video. |
| `watch_lower_left` | `0.77x` | `3.11x` | Different text color/content makes this useful but not conclusive. |
| `watch_lower_right` | `0.70x` | `1.42x` | Ammo/count crop is smaller and noisier. |

Interpretation:

- The fresh GV-USB2/S-Video watch capture does not reproduce a decisive
  low-resolution-text failure for `g1hiq3_gegate`. The top text crop is close to
  GE480i by line-pair detail and has higher edge energy.
- The user's Analogue 3D observation should still be treated as authoritative
  for perceived HDMI sharpness. The current capture metric is a regression gate,
  not proof that the Analogue issue is solved.
- The next genuinely technical step is still runtime glyph/RDP evidence:
  compare the text rectangle coordinates and texture steps emitted by GE480i
  and TND6480i for the same watch/HUD/mission text class.

### HUD Save-Option Correction

The first GE480i HUD/no-watch probe did not show bottom-right ammo digits in the
active gameplay frames. The cause was not a render-path difference: the shared
all-missions save had `OPTION_DISPLAYAMMO` clear in valid folders.

New tooling:

- `scripts/patch_save_options.py`

Findings:

- The probe save option word was `0x001A`.
- GE default full-screen/ammo-on settings for this save class are `0x003A`.
- Patching `OPTION_DISPLAYAMMO` and refreshing the per-slot CRCs made GE480i
  draw the ammo HUD in the no-controller hardware capture.

Useful artifacts:

- `artifacts/generated/force_fp_hud_probe_v2/GE480i.z64`
- `artifacts/generated/force_fp_hud_probe_v2/GE480i.sav`
- `artifacts/generated/force_fp_hud_probe_v2/TND6480i.z64`
- `artifacts/generated/force_fp_hud_probe_v2/TND6480i.sav`
- `diagnostics/captures/videos/force_fp_hud_ge480i_v2_20260525.mp4`
- `diagnostics/captures/videos/force_fp_hud_tnd6480i_v2_20260525.mp4`
- `diagnostics/captures/measurement/force_hud_text_metrics_ge_vs_tnd_v2_t38_20260525.png`
- `reports/measurement/force_hud_text_metrics_ge_vs_tnd_v2_t38_20260525.json`
- Stable candidate save with ammo display enabled:
  `artifacts/generated/g1hiq3_gegate_ammoon.sav`
- Short-name Analogue pair:
  `artifacts/analogue_test/G1HQ3AM.Z64`,
  `artifacts/analogue_test/G1HQ3AM.SAV`,
  `artifacts/analogue_test/G1HQ3AM.EEP`

Metric snapshot from the matched HUD capture, using GE480i as the reference:

| Crop | TND line-pair ratio | TND Laplacian ratio | Notes |
|---|---:|---:|---|
| `ammo_hud` | `0.78x` | `3.78x` | Both samples now draw ammo; backgrounds differ heavily. |
| `lower_right_digits` | `2.06x` | `3.75x` | Digit crop shows TND detail energy above GE through GV-USB2. |

Interpretation:

- Save options can invalidate HUD comparisons. Always use an ammo-on save for
  HUD text tests.
- The corrected GV-USB2/S-Video HUD probe again does not reproduce a decisive
  low-resolution TND text failure. Analogue HDMI/perceptual validation remains a
  separate gate.
- This closes the "missing ammo HUD" probe issue; it does not by itself prove
  the Analogue text-quality concern is solved.

### Anti-Aliasing Option Observation

After the font-good `g1hiq3_gegate` confirmation, the user noticed that the
in-game anti-aliasing option makes a large visible difference to text quality.
That means AA state is part of the text-measurement contract, not just a player
preference.

Current status:

- `scripts/patch_save_options.py` can normalize ammo display and screen/aspect
  bits, but it does not yet map the anti-aliasing bit.
- Future watch/HUD/mission-intro comparisons must record whether AA is on or
  off before judging text detail.
- If possible, capture matched AA-on and AA-off pairs for GE480i and TND6480i.
  Until the save bit is mapped, avoid treating AA-on versus AA-off differences
  as evidence of a bad 480i render path.

## Existing Capture Metrics

The existing GV-USB2 clips still provide the most useful objective signal today:

- GE480i reference: `C:\Users\codex\Documents\Light Capture ˜^‰æƒtƒHƒ‹ƒ_\n64\2. GoldenEye 480i.mpg`
- TND6480i old/current-reference clip: `C:\Users\codex\Documents\Light Capture ˜^‰æƒtƒHƒ‹ƒ_\n64\4. Tomorrow Never Dies 6480i.mpg`
- Matched frame sheet: `diagnostics/captures/lightcapture_existing/matched_text_frames/existing_capture_text_quality_ge480i_vs_tnd6480i_20260525.png`
- Metrics: `reports/measurement/existing_capture_text_quality_ge480i_vs_tnd6480i_20260525.json`

Those metrics are useful as a regression gate but not final proof for the latest
ROM unless a fresh matched capture is recorded from that same ROM.

## Next Viable Measurement Paths

1. Reuse the force-FP/watch harness for repeatable no-controller watch captures
   whenever a new text-quality candidate is built.
2. Use `scripts/patch_save_options.py --ammo-on --fullscreen` before any HUD
   comparison so GE480i and TND draw the same HUD class.
3. Build a similar no-controller speech/mission-intro route if the Analogue
   issue is more visible in mission intro text or character speech than in the
   watch/HUD pages.
4. Keep trying for runtime glyph/RDP evidence: text rectangle coordinates,
   texture steps (`dsdx`, `dtdy`), and RDP state before glyph rectangles.
5. Do not continue framebuffer-placement candidates for this issue. `g1hifb1`,
   `g1hqfb1`, and `g1hiq4_upperpair` were rejected, while `g1hiq3_gegate`
   already matches the audited GE480i VI/text/HUD constants except for its
   intentional split framebuffer model.

## Hardware Closeout

After the save-option correction and `g1hiq3_gegate` restore, the user reported
that the font looks good. The user also reported that the Bazaar countdown timer
position is fixed on the same build. This is the current human/hardware
acceptance signal for the text pass.

Do not reopen the text issue by moving framebuffers unless a future measurement
shows a concrete runtime display-list or glyph-rectangle mismatch. The next
release-oriented task is packaging a stock-GoldenEye-USA-to-`g1hiq3_gegate`
patch and recording its hashes.
