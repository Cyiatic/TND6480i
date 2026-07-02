# Text Resolution Follow-Up - 2026-05-24

User report: on Analogue 3D, character speech and the pause/watch menu still look like stock-resolution text compared with GE480i.

Final 2026-05-25 closeout: the current `g1hiq3_gegate` line, paired with the
normalized ammo-on save, passed user hardware/Analogue review for font quality.
The same line also fixed Bazaar's countdown timer position. This document is
retained as the investigation history; use
`docs/runtime_text_measurement_attempt_20260525.md` and
`docs/measurable_480i_validation_workflow_20260525.md` for the final
measurement workflow and regression gates.

## What The Audit Says

- Source-mapped GE stock -> GE480i diffs checked in the selected text/gameplay files: `592`.
- Diffs where `g1mcfix4` does not match GE480i in those files: `29`.
- `watch.c`, `mp_watch.c`, `gun.c`, and the mapped `textrelated.c` diffs already match GE480i in `g1mcfix4`.
- The active Gothic font bank used by the watch/pause menu is byte-identical across GE stock, GE480i, TND64, and `g1mcfix4`.
- The US `textRender` / `textRenderGlow` bodies are not changed by the GE480i patch in the mapped source audit.

This makes the font-bank theory unlikely for pause text. The remaining low-risk probe is the small viewport-helper family still left at stock in `g1mcfix4`; broader framebuffer selection differences remain intentional and should not be changed without a dedicated hardware comparison.

## New Diagnostic Candidate

- ROM: `C:\Users\codex\Documents\GitHub\TND6480i\artifacts\generated\g1txtview1.z64`
- MD5: `d6d591c90177db8db2a2c57518f4ca6c`
- Header CRC: `0D2B858F DDE4BF4A`
- Save mirrors: `C:\Users\codex\Documents\GitHub\TND6480i\artifacts\generated\g1txtview1.sav`, `C:\Users\codex\Documents\GitHub\TND6480i\artifacts\generated\g1txtview1.eep`
- Analogue short-name copy: `C:\Users\codex\Documents\GitHub\TND6480i\artifacts\analogue_test\G1TXTVW1.Z64`
- Gopher64 survival smoke: `reports\smoke\smoke_g1txtview1_text_followup.json`

Only these words changed from `g1mcfix4`:

| Offset | Old | New | Note |
|---:|---:|---:|---|
| `0x0BB790` | `0x2402009F` | `0x2402013F` | 4-player/alternate viewport width return 319 |
| `0x0BB83C` | `0x240200A1` | `0x24020141` | 4-player/alternate viewport left return 321 |
| `0x0BB874` | `0x2402006D` | `0x240200E5` | 4-player/alternate viewport height return 229 |
| `0x0BB9A0` | `0x24020079` | `0x240200F1` | 2-player/alternate viewport top return 241 |
| `0x0BB9D8` | `0x24020079` | `0x240200F1` | 4-player/alternate viewport top return 241 |

## Remaining Miss Summary

- `fr.c`: `27`
- `game/bondview.c`: `2`

The `fr.c` misses are the final split-framebuffer implementation, not simple missed text patches. Replacing them wholesale with GE480i's contiguous stride path would risk the all-level stability we just recovered.

## Emulator Pause-Menu Check

RetroArch/ParaLLEl N64 was configured with an explicit keyboard Start binding and framebuffer screenshots were captured from direct-stage pause/watch menus.

- GE480i reference screenshot: `diagnostics/captures/retroarch/pause_compare_20260524/p00bzr-260524-160403.png`
- TND6480i `g1mcfix4` screenshot: `diagnostics/captures/retroarch/pause_compare_20260524/p00bzr-260524-155140.png`
- Comparison sheet: `diagnostics/captures/retroarch/pause_compare_20260524/ge480i_vs_tnd6480i_pause_text_compare_20260524.png`
- Metrics/report: `reports/pause_menu_emulator_compare_20260524.json`

Current emulator-framebuffer read: the TND watch/pause text is in the same coordinate and pixel-scale class as the GE480i watch text. It does not obviously match a stock low-resolution watch-menu path in this comparison.

## Hardware Correction

The user then tested the follow-up on Analogue 3D and reported that the mission intro text, ammo count, and pause menu still do not match GE480i text quality. Treat that hardware/FPGA result as authoritative. The emulator comparison is now only a layout/survival check, not proof of high-resolution text rendering.

A broader safe-word audit found GE480i code constants still left at GE-stock values in `g1mcfix4`:

- `0x08AE9C-0x08B0F0`: in-game numeric/HUD text Y-position family.
- `0x043F94-0x044B54`: in-game overlay/front text thresholds, positions, and rectangle bounds.
- `0x0BB790-0x0BB9D8`: alternate viewport helper returns.
- `0x035920-0x03592C`, `0x03FC90-0x03FC94`, `0x040540-0x040544`: riskier menu video-buffer pointer/size path.

New hardware-first candidates:

| Candidate | ROM | MD5 | Scope |
|---|---|---:|---|
| `g1hiq1` | `artifacts/generated/g1hiq1.z64` | `084bf0a440b460216cc78f555f3476ec` | Low-risk: alternate viewport, in-game HUD numeric, and overlay/front text coordinate families. Uploaded to SC64 on 2026-05-24 for first test. |
| `g1hiq2` | `artifacts/generated/g1hiq2.z64` | `61f8c1f8c86c1c5f9d92a2a656569a4d` | Riskier: `g1hiq1` plus menu video-buffer pointer and menu buffer-size constants. Use only if `g1hiq1` improves gameplay overlays but pause/watch/front text remains soft. |

Short-name Analogue/SD copies:

- `artifacts/analogue_test/G1HIQ1.Z64`
- `artifacts/analogue_test/G1HIQ2.Z64`

Reports:

- `reports/tnd480i_g1hiq1_hardware_text_quality_20260524.json`
- `reports/tnd480i_g1hiq2_hardware_text_quality_20260524.json`
- `reports/smoke/smoke_g1hiq_text_quality_20260524.json`

## Analogue 3D Follow-Up

The user reported the later high-quality candidates still look visibly pixelated on Analogue 3D compared with GE480i. At this point the simple text/font theory is weak:

- The selected GE480i source-mapped text, watch, HUD, and overlay constant families are ported in `g1hiq3_gegate`.
- `g_ViFrontData` / `g_ViBackData` and sampled display lists show 640-wide color images and 640x480 scissor in the emulator state.
- Direct VI register patch sites around `0x19978-0x19A64` already match GE480i in `g1hiq3_gegate`.
- The remaining intentional divergence is the framebuffer memory model: TND uses the stable split pair `0x80400000` / `0x8076A000`, while GE480i uses contiguous upper-RAM framebuffers.

New diagnostic:

| Candidate | ROM | MD5 | Scope |
|---|---|---:|---|
| `g1hifb1` | `artifacts/generated/g1hifb1.z64` | `1d19b712e7e8bcd0ec94a88b22ffbdf9` | Single-buffer diagnostic from `g1hiq3_gegate`; both framebuffer globals are forced to `0x8076A000`. This may flicker or tear, but it isolates whether the split low/high framebuffer handoff is what Analogue presents as soft/pixelated text. |

Short-name Analogue/SD copy:

- `artifacts/analogue_test/G1HIFB1.Z64`

Report and smoke evidence:

- `reports/tnd480i_g1hifb1_high_framebuffer_diag_20260524.json`
- `reports/smoke/smoke_g1hifb1_20260524.json`
- `diagnostics/captures/hardware/g1hifb1_boot_12s_20260524.png`
- `diagnostics/captures/hardware/g1hifb1_boot_40s_20260524.png`

Interpretation rule: if `g1hifb1` sharpens the Analogue text, keep the GE480i source/text parity work and focus on deriving a stable TND-safe framebuffer pair closer to GE's upper-RAM model. If `g1hifb1` still looks like stock/pixelated text, the defect is upstream of framebuffer placement and the next audit should target the runtime display-list/text draw commands instead of more VI table churn.

## G1HIFB1 Rejected

User hardware report: `g1hifb1` still had bad text and made the rest of the render worse. Do not continue the single-buffer branch.

Follow-up audit:

- The GE480i enhanced ROM in `artifacts/roms/BASELINE_GE_480i_direct_from_stock.z64` matches the N64-Tools `GE640x480iEnhanced[SubDragTrevorZoinkity].xdelta` output.
- `j_text_trigger` references and the `textRender`/`textRenderGlow`/`textMeasure` bodies are identical across stock GE, GE480i enhanced, baseline TND, `g1mcfix4`, and `g1hiq3_gegate`; this is not the missing enhanced-text switch.
- The rejected `g1hifb1` only changed framebuffer globals. It did not make the VI front/back buffer init or VI handoff match GE480i, so it was an incoherent framebuffer diagnostic rather than a true GE framebuffer model test.

New coherent diagnostic:

| Candidate | ROM | MD5 | Scope |
|---|---|---:|---|
| `g1hqfb1` | `artifacts/generated/g1hqfb1.z64` | `90c534abe183c175238c73abe04067fc` | `g1hiq3_gegate` plus GE480i paired upper-RAM framebuffer init, clear, VI handoff, and cfb globals. TLB cache moved to `0x80600000-0x806B3FFF` to avoid overlapping GE's `0x806D4000/0x8076A000` framebuffers. |

Evidence:

- Gopher64 smoke survived 35 seconds: `reports/smoke/smoke_g1hqfb1_20260524.json`.
- Uploaded to SC64 on 2026-05-24 with paired save.
- GV-USB2 boot captures reached visible intro/gunbarrel: `diagnostics/captures/hardware/g1hqfb1_boot_10s_20260524.png`, `diagnostics/captures/hardware/g1hqfb1_boot_30s_20260524.png`.
- Analogue short-name copy: `artifacts/analogue_test/G1HQFB1.Z64`.

Interpretation rule: if `g1hqfb1` improves Analogue text clarity, the remaining issue was the split presentation-buffer model, and the next work is an all-level stability pass under the GE-style upper framebuffer layout. If it does not improve text clarity, stop changing framebuffer placement and instrument runtime text RDP commands/texture-rectangle scale directly.

## G1HQFB1 Rejected

User hardware report on 2026-05-25: TiJayFly loads slower, the game does not progress past the TiJayFly/Rare-logo phase, and there is no sound. The console was restored to `g1hiq3_gegate` immediately afterward.

Conclusion: GE480i's coherent contiguous upper-framebuffer path is not TND64-safe when transplanted onto the current TND branch, even with the TLB cache moved lower. Together with the `g1hifb1` rejection, this closes the framebuffer-placement line of attack for the current text-quality issue.

Next work should instrument or compare runtime text display-list commands:

- `textRender` / `textRenderGlow` call arguments: x/y pointers, view bounds, font bank, line height.
- RDP `TextureRectangle` / `TextureRectangleFlip` commands emitted for font glyphs.
- Texture coordinate step values (`dsdx`, `dtdy`) and rectangle coordinates for GE480i vs TND6480i on the same pause/watch and mission-intro text classes.
- Any RDP state differences immediately before glyph rectangles, especially texture filter, tile size, and combine/render mode.

## Closeout

The runtime trace path remained useful as future instrumentation guidance, but
the accepted candidate did not require another framebuffer branch. The final
working answer was to keep `g1hiq3_gegate`'s stable split framebuffer model,
normalize save options for comparable HUD output, and validate the audited
GE480i text/HUD/front-end constant set on hardware.

Current handoff package:

```text
artifacts/release/TND6480i_g1hiq3_fontgood_20260525_test.zip
G1HQ3AM.Z64 MD5 4063fd9968b528148a9441b11dfd0203
G1HQ3AM.SAV MD5 50a3f7cf6e022fdec7f37f2cc8ae2e2a
G1HQ3AM.EEP MD5 50a3f7cf6e022fdec7f37f2cc8ae2e2a
```
