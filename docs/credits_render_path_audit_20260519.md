# End-Credits Render Path Audit

Date: 2026-05-19

Candidate audited:

```text
artifacts/generated/g1mcfix4.z64
MD5 FA93BE061C59EF5CABAD24FBF5F66B39
```

Question: do the end credits use a separate lower-resolution viewport/framebuffer path, or do they inherit the final 480i gameplay view?

## Short Answer

No separate lower-resolution end-credits viewport was found. The end-credits crawl is an overlay triggered by the `credits_roll` AI command and drawn through the same global VI/view state used by the active stage render path. The visual difference from GoldenEye 480i credits is most likely TND64 content/camera/lighting, not an independent stock-resolution credits framebuffer.

## Evidence

The final ROM still carries the global 480i framebuffer and dimension-table package:

| Offset | Final word | Meaning |
| --- | ---: | --- |
| `0x3D30` | `0x3C048040` | clear framebuffer 0 at `0x80400000` |
| `0x3D48` | `0x3C048076` | clear framebuffer 1 upper at `0x8076A000` |
| `0x3D4C` | `0x3484A000` | clear framebuffer 1 lower at `0x8076A000` |
| `0x6584` | `0x3C048040` | initialize framebuffer 0 at `0x80400000` |
| `0x658C` | `0x3C058076` | initialize framebuffer 1 upper at `0x8076A000` |
| `0x6590` | `0x34A5A000` | initialize framebuffer 1 lower at `0x8076A000` |
| `0x4F354` | `0x028001E0` | direct dimension slot patched to `640x480` |
| `0x4F35C` | `0x028001E0` | direct dimension slot patched to `640x480` |
| `0x4F1C4` | `0x10000003` | front-end branch behavior used by final menu path |

The end-credits crawl routine is the GoldenEye/TND function at ROM `0xBD808` / runtime `0x7F088CD8`. Decompilation references:

```text
C:\Users\codex\Documents\n64\007-decomp\src\game\bondview.c
C:\Users\codex\Documents\n64\007-decomp\src\aicommands.def
C:\Users\codex\Documents\n64\007-decomp\src\bondaicommands.h
```

Relevant behavior:

- `CreditsRoll` only sets `credits_state = TRUE`.
- The command table notes that credits text and positions are stored in the setup intro struct.
- `sub_GAME_7F088CD8` checks `credits_state` and `credits_pointer`, then draws the crawl.
- That function calls `viGetViewHeight`, `viGetViewTop`, `viGetX`, and `viGetY`.
- No direct `viSetViewSize`, `viSetViewPosition`, `viSetXY`, or `viSetBuf` call was identified inside the credits crawl routine.

The final credits-specific text fixes are deliberately narrow:

| Offset | Final word | Meaning |
| --- | ---: | --- |
| `0xBD870` | `0x24160140` | default first-column X: `320` |
| `0xBD878` | `0x24170140` | default second-column X: `320` |
| `0xBD930` | `0x24760064` | pre-scan first-column explicit X: add `+100` |
| `0xBD95C` | `0x24770064` | pre-scan second-column explicit X: add `+100` |
| `0xBDA00` | `0x24760064` | render first-column explicit X: add `+100` |
| `0xBDB80` | `0x24770064` | render second-column explicit X: add `+100` |

Comparing `g1mcfix4` to the pre-credits-layout candidate `g1tabhit1`, the credits crawl function range `0xBD808-0xBDD34` differs by exactly those six words. That means the credits fix moved the text columns to match the GE480i-style coordinate space without replacing the renderer or viewport setup.

## Stage Context

The direct-stage probe table identifies:

```text
p13end / The End / stage ID 25 / original GE slot Train
```

The probe builder only writes `g_StageNum` at startup by patching the debug-token parser at `0x6C94-0x6CA4`. It is a route harness, not a renderer patch. This supports treating The End/end credits as a normal stage path with a credits overlay rather than a standalone menu/video mode.

## Visual Evidence Captured

Reference/control captures:

```text
diagnostics/captures/videos/ge480i_credits_reference_gvusb2_20260519_172355.mkv
diagnostics/captures/videos/ge480i_credits_reference_continuation_gvusb2_20260519_173012.mkv
diagnostics/captures/videos/g1mcfix4_credits_analysis_gvusb2_20260519_174358.mkv
```

Comparison images:

```text
diagnostics/captures/current/credits_ge480i_late_vs_g1mcfix4_20260519.jpg
diagnostics/captures/current/credits_ge480i_vs_g1mcfix4_brightened_20260519.jpg
```

The TND credits crawl looks correctly high-resolution and aligned after the final fix. The 3D scene is darker and framed differently than GE480i, so visual inspection alone is less definitive for the character/model render path. The static code and binary audit did not find a separate lower-resolution credits viewport.

## Remaining Caveat

The next level of proof would be runtime instrumentation that logs the active `g_ViBackData` fields during The End/end credits:

```text
viewx, viewy, viewleft, viewtop, bufx, bufy, framebuf
```

That would prove the active view values on real hardware at the exact moment the credits scene is drawn. Without that instrumentation, the best supported conclusion is that the credits scene inherits the final gameplay 480i render path, while TND64's credits content/camera/lighting make it visually unlike GoldenEye's brighter late-credits model shots.
