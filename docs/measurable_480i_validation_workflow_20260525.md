# Measurable 480i Validation Workflow - 2026-05-25

This project should no longer advance by repeatedly uploading candidate ROMs
and asking for subjective hardware impressions. A candidate must pass objective
gates before it is worth manual testing on N64 or Analogue 3D.

2026-05-25 closeout: the `g1hiq3_gegate` line passed the hardware/Analogue
font-quality check after the measured GE480i text/HUD contract audit and
ammo-on save normalization. The same line fixed Bazaar's countdown timer
position. Use this workflow as the regression gate for future candidates.

## Reference Set

All visual metrics must use captures from the same GV-USB2/S-Video path.

Known local reference recordings:

| Label | Path | Role |
|---|---|---|
| `GE_stock` | `C:\Users\codex\Documents\Light Capture ˜^‰æƒtƒHƒ‹ƒ_\n64\1. GoldenEye 007.mpg` | 240p/stock-resolution control |
| `GE480i` | `C:\Users\codex\Documents\Light Capture ˜^‰æƒtƒHƒ‹ƒ_\n64\2. GoldenEye 480i.mpg` | target high-resolution/interlaced reference |
| `TND_stock` | `C:\Users\codex\Documents\Light Capture ˜^‰æƒtƒHƒ‹ƒ_\n64\3. Tomorrow Never DIes 64.mpg` | TND stock control |
| `TND6480i_old` | `C:\Users\codex\Documents\Light Capture ˜^‰æƒtƒHƒ‹ƒ_\n64\4. Tomorrow Never Dies 6480i.mpg` | older candidate/regression control |

## Gate 1: Binary And VI/RDP Intent

Before hardware:

- Direct VI sites around `0x19978-0x19A64` must match GE480i or be justified.
- `g_ViFrontData` / `g_ViBackData` must describe 640-wide color images and a
  480-line interlaced output path.
- Runtime display lists must contain `SetColorImage` width 640 and scissor
  640x480 for gameplay/front-end screens.
- Text render calls must use GE480i-class view bounds: `view_x=640`,
  `view_y=480` or the known GE480i front-end equivalent.
- Glyph `TextureRectangle` commands must be compared against GE480i for
  rectangle coordinates and texture steps (`dsdx`, `dtdy`). If those are still
  stock-scale, the ROM is not a valid text-quality candidate even if VI says
  480i.

## Gate 2: Capture Metrics

Use `scripts/measure_480i_text_quality.py` to compare candidate captures
against GE480i and stock controls.

Example:

```powershell
python scripts\measure_480i_text_quality.py `
  --sample GE480i="C:\path\to\ge480i_frames_or_video" `
  --sample Candidate="C:\path\to\candidate_frames_or_video" `
  --reference-label GE480i `
  --crop pause_text=120,70,600,410 `
  --out-json reports\measurement\candidate_vs_ge480i.json `
  --out-sheet diagnostics\captures\measurement\candidate_vs_ge480i.png
```

Metrics:

| Metric | Meaning |
|---|---|
| `line_pair_mad` | Odd/even adjacent-line detail. Low values usually mean line-doubled/soft output. |
| `vertical_nyquist_ratio` | Alternating-line detail energy, useful for interlace/high-resolution evidence. |
| `laplacian_var` | Edge/detail energy, useful for text sharpness in matched crops. |
| `edge_density` | Fraction of strong local gradients in the crop. |
| `temporal_mad` | Motion/change across sampled frames. Helps distinguish static/no-signal comparisons. |

The current thresholds are provisional until we collect matched GE480i/TND
frames for the same page type:

- Candidate `line_pair_mad` in text crops should be at least `0.75x` GE480i
  and clearly above the stock controls.
- Candidate `laplacian_var` in text crops should be at least `0.70x` GE480i
  and clearly above the stock controls.
- Candidate must not win only on `vertical_nyquist_ratio`; analog noise or
  flicker can inflate that number while text remains soft.
- Candidate must show a live, content-matched crop. Black/blank/transition
  frames invalidate the measurement.

## Gate 3: Content-Matched Screens

Do not compare random scenes. Use the same class of screen:

- Pause/watch text: GE480i pause/watch vs TND pause/watch.
- Mission intro/speech text: GE480i objective/briefing-style text vs TND
  mission intro/speech text.
- HUD/ammo text: GE480i HUD vs TND HUD.
- Dossier/front-end text: GE480i dossier page vs TND dossier page.

The crop boxes must isolate text or UI. Full-screen averages are allowed only
for interlace/noise detection, not for deciding text quality.

For HUD/ammo comparisons, normalize the EEPROM options first. The shared
all-missions save used during earlier testing had `OPTION_DISPLAYAMMO` disabled
(`0x001A`), which made GE480i omit the ammo HUD in direct-stage captures. Use:

```powershell
python scripts\patch_save_options.py `
  artifacts\generated\g1hiq3_gegate.sav `
  artifacts\generated\g1hiq3_gegate_ammoon.sav `
  --ammo-on `
  --fullscreen
```

The expected valid-folder option word after this patch is `0x003A`.

Also record the in-game anti-aliasing state for every text-quality comparison.
The user observed that AA makes a large visible difference to text appearance.
The AA save bit is not yet mapped here, so do not silently mix AA-on and AA-off
captures. If the setting must be automated, first create a clean before/after
EEPROM diff from the same folder with only AA toggled.

## Gate 4: Hardware Regression

Only after the first three gates pass:

- Upload one candidate to SC64.
- Capture a short GV-USB2 clip/frame set before asking the user to test.
- If the ROM hangs before title/menu, loses sound, or corrupts front-end boot,
  mark it rejected and restore the console to the last usable baseline.

Recent hard rejections:

| Candidate | Result |
|---|---|
| `g1hifb1` | Text still bad and rendering worse; single-buffer framebuffer diagnostic rejected. |
| `g1hqfb1` | TiJayFly/Rare-logo phase slowed/hung and no sound; GE contiguous upper-framebuffer path rejected for TND. |

## Current Technical Conclusion

Framebuffer placement is not the next productive lever. The 2026-05-25 text
pass was accepted on the `g1hiq3_gegate` line without moving to GE480i's
contiguous upper framebuffer model. If the text issue reappears, the next
technical step is runtime text/RDP measurement:

1. Capture `textRender` / `textRenderGlow` arguments for GE480i and TND6480i.
2. Capture or parse glyph `TextureRectangle` commands for the same text class.
3. Compare coordinates and texture steps.
4. Patch only the mismatched draw-path component.

No more framebuffer-layout candidates should be uploaded for text quality unless
runtime RDP evidence specifically points back to framebuffer presentation.

2026-05-25 follow-up: initial runtime instrumentation did not produce a usable
text-call trace. Gopher64 does not execute the direct-stage boot patch site in
the current launch path, SC64 data-buffer dumps return stale or unrelated data
for the text-call ring, and SC64 cannot directly dump N64 RDRAM
(`0x80000000` is outside the deployer's dumpable address range).

A working no-controller capture harness now exists:

```text
scripts/build_force_fp_watch_probe.py
scripts/build_auto_watch_text_probe.py --delay-frames ...
```

The successful route is `force_fp_watch_probe_v3`: direct-boot Wreck/Frigate,
force `CAMERAMODE_FP` from `bondviewFrozenMoveBond`, then trigger the watch from
`bondviewProcessInput`. This gives matched GE480i/TND6480i watch captures on
real hardware without asking the user to drive the console.

Current matched hardware evidence:

```text
diagnostics/captures/videos/force_fp_watch_ge480i_v3_20260525.mp4
diagnostics/captures/videos/force_fp_watch_tnd6480i_v3_20260525.mp4
reports/measurement/force_watch_text_metrics_ge_vs_tnd_v3_t50_20260525.json
diagnostics/captures/measurement/force_watch_text_metrics_ge_vs_tnd_v3_t50_20260525.png
diagnostics/captures/videos/force_fp_hud_ge480i_v2_20260525.mp4
diagnostics/captures/videos/force_fp_hud_tnd6480i_v2_20260525.mp4
reports/measurement/force_hud_text_metrics_ge_vs_tnd_v2_t38_20260525.json
diagnostics/captures/measurement/force_hud_text_metrics_ge_vs_tnd_v2_t38_20260525.png
```

The fresh GV-USB2/S-Video watch-page metrics do not show a decisive TND text
detail failure: the top watch-text crop is `0.93x` GE480i by line-pair detail
and above GE480i in Laplacian edge energy. Treat this as a regression gate only;
the user's Analogue 3D report still matters because HDMI/FPGA presentation may
expose softness that S-Video capture does not.

Until a better runtime trace exists, use fresh content-matched GV-USB2 captures
plus the metric script as the objective gate, and only upload text candidates
after they improve the measured crop or provide a clear low-level RDP/display
list reason. For current release work, package `g1hiq3_gegate` rather than
generating more text/framebuffer candidates.

## Tooling Added

Capture metric tool:

```text
scripts/measure_480i_text_quality.py
```

Initial proof report from existing GV-USB2 frame sets:

```text
reports/measurement/capture_metrics_ge480i_vs_tnd_g1hiq1_20260525.json
diagnostics/captures/measurement/capture_metrics_ge480i_vs_tnd_g1hiq1_20260525.png
```

This initial report is only a tool sanity check because the frame sets are not
content-matched tightly enough to make a final text-quality judgment.

Runtime RDP scan helper:

```text
scripts/scan_rdp_commands.py
```

Initial sanity check:

```text
reports/measurement/rdp_scan_p00bzr_state_20260525.json
```

The RDP scanner should be pointed at a known display-list range when possible.
Whole savestate/RDRAM scans contain false positives, but they are still useful
for finding candidate `SetColorImage`, `SetScissor`, and texture-rectangle
clusters to inspect more narrowly.

No-controller watch capture harness:

```text
scripts/build_force_fp_watch_probe.py
scripts/build_auto_watch_text_probe.py
scripts/patch_save_options.py
```

Use `force_fp_watch_probe_v3` as the model for future probes. The frozen-move
hook alone can force active gameplay, but the watch trigger needs the
`bondviewProcessInput` hook after the camera mode has settled.
