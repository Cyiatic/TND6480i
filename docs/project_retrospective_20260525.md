# Project Retrospective - 2026-05-25

This note answers the handoff questions that came up after the first working
TND6480i result: what was learned, what went well, what could be improved, and
how a future N64 480i project should start.

## Final Current Line

The current best hardware/Analogue-confirmed test build is:

```text
ROM: artifacts/generated/g1hiq3_gegate.z64
Short test package: artifacts/release/TND6480i_g1hiq3_fontgood_20260525_test.zip
Short ROM name: G1HQ3AM.Z64
ROM MD5: 4063fd9968b528148a9441b11dfd0203
ROM SHA256: f359631cb63bb367e56a6c39a5f95b6fc11a3fda5b8a2c2eed87a3da5aded3d3
Save: artifacts/generated/g1hiq3_gegate_ammoon.sav
Save/EEP MD5: 50a3f7cf6e022fdec7f37f2cc8ae2e2a
Save type: EEPROM 4K
```

Confirmed user-facing improvements on this line:

- All levels boot and run.
- Gameplay, pause/watch, HUD, bullets UI, dossier pages, multiplayer screens,
  cheat menu, mission result, credits, and front-end pages are in the expected
  480i visual family.
- Font output looks good on hardware/Analogue review.
- Bazaar countdown timer position is corrected.
- The visible `Custom` label is intentionally changed to `007`.

`g1mcfix4` remains the packaged rollback release candidate because it already
has a stock-GoldenEye xdelta release bundle. `g1hiq3_gegate` is the line to
package next.

## What We Learned

480i is not a VI-register patch. The working result needed a coherent render
contract across VI, framebuffers, z-buffer dimensions, TLB/page-cache placement,
camera/viewports, front-end pages, text/HUD constants, and screen-specific
assets.

Hardware is the judge. Emulators were useful for smoke testing, but several
emulator-passing candidates black-screened, stuttered badly, corrupted levels,
or produced misleading interlace signals on real N64 hardware.

Memory placement mattered more than expected. The high framebuffer overlapped
the Expansion Pak page cache in early candidates, producing level load failures
and Hotel/Volcano prism corruption. The stable fix kept the 90-page cache for
performance, moved the page-cache base down, and kept explicit split 640x480
framebuffers.

Screen families are separate. Gameplay, watch/pause, dossier, title/gunbarrel,
display-cast, end credits, multiplayer, and mission-result pages each had
distinct layout or render-state needs. A fix that helped one family could
damage another.

Save options can invalidate visual tests. The shared all-missions save had ammo
display disabled, which made GE480i and TND HUD captures non-comparable until
`scripts/patch_save_options.py` normalized folder options and CRCs.

Anti-aliasing belongs in the capture matrix. Late testing showed that the
in-game AA option makes a big visible difference to text quality, so future
comparisons need to record AA state instead of attributing every sharpness
difference to the 480i patch.

Patch provenance matters. The safest assembly-level transplants were GE
stock-to-GE480i deltas applied only where the current TND word still matched the
old GE stock word. Same-offset source comments and raw table copies were not
enough proof.

## What Went Well

The user-driven hardware feedback loop was decisive. The SC64, GV-USB2, S-Video
capture, Analogue 3D checks, EverDrive X7, and later Kasa power switch turned a
slow manual process into a repeatable one.

Direct-stage and no-controller probes saved enormous time. Once we could boot
to a target level or force first-person/watch states, we no longer needed a full
manual route for every hypothesis.

Annotated comparisons improved judgment. Screen-by-screen comparison against
GE480i caught issues that looked "close" in isolation, especially dossier tab
placement, mission text alignment, result screens, credits, and text quality.

The repository migration helped. Named candidates, manifests, hashes, docs, and
release bundles made it possible to recover from bad branches and preserve
known-good states.

The final text pass used better gates. Instead of continuing to move
framebuffers blindly, the project measured GE/TND text captures, audited static
render contracts, fixed save options, and then asked hardware to validate a
specific candidate.

## What Could Be Improved

Start with version control and candidate discipline on day one. Early work
generated too many ROMs without enough manifests, making it harder to identify
which change caused which behavior.

Do not spend too much time polishing low-priority screens before gameplay is
stable. The gunbarrel work was interesting, but level bootability, in-game
rendering, pause/watch, and save/menu usability should always come first.

Capture references before patching deeply. A stock game clip, known-good 480i
clip, current candidate clip, and screen timestamp map should exist before the
first big patch series.

Use measurable gates sooner. Frame cadence, active-area metrics, text sharpness
crops, display-list/RDP scans, and route probes should be built before manual
testing becomes tiring.

Keep save behavior explicit. Every hardware candidate should be paired with a
matching save file, known save type, CRC status, and flashcart-specific naming
rules.

Keep display options explicit too. Ammo display, screen/aspect mode, and
anti-aliasing can all change what a capture appears to prove.

Avoid "one more ROM" loops. If several candidates fail without a new
measurement, stop and improve the probe or comparison method.

Assistant-side improvements:

- Preserve a single "current known good" pointer after every successful hardware
  test.
- Ask for or generate reference captures before spending many cycles on a
  visually complex screen.
- Treat user fatigue as a hard engineering constraint and reduce manual
  controller routes with probes.
- Avoid declaring a candidate good until it has screen-family evidence, not just
  a successful boot or one fixed page.
- Update docs immediately when a candidate is promoted, rejected, or superseded.

User/project-side improvements:

- Provide stock, known-good 480i, and current-candidate recordings as early as
  possible.
- Record timestamps for key screens, as was eventually done for the TND clips.
- Provide complete saves and known save-type settings early.
- Keep the flashcart, capture-card, and power-control setup stable during a
  hardware test pass.
- Push back when a candidate is only "less wrong" rather than actually matching
  the reference; that feedback materially improved this project.

## How To Start Better From Scratch

Use this opening prompt shape for a future N64 480i project:

```text
Create a repo and work only from named candidates with manifests.
Do not start by brute-forcing resolution constants.

First document:
- stock ROM hash and region
- source/reference ROM hashes
- flashcart and save type
- emulator setup
- capture path and reference clips
- memory map, framebuffer locations, VI setup, z-buffer allocation, page cache,
  camera viewport functions, front-end/menu viewport functions, and text/HUD
  draw paths

Then build:
- one emulator smoke harness
- one hardware capture command
- one direct-stage or direct-screen probe harness
- one screen-comparison/contact-sheet workflow

Only after that, create the first minimal candidate with a falsifiable
hypothesis and a patch-site manifest.
```

For a new GoldenEye-engine project, start by reading these files:

- `docs/N64_480i_porting_playbook.md`
- `docs/reverse_engineering_technical_findings.md`
- `docs/measurable_480i_validation_workflow_20260525.md`
- `docs/runtime_text_measurement_attempt_20260525.md`
- `docs/direct_stage_probe_workflow.md`
- `docs/ge_decomp_offset_audit.md`
- `docs/current_candidate_status_20260519.md`

## Better Prompt For A Future Fresh Thread

```text
Please continue from the TND6480i workflow, but do not assume offsets transfer.

Read:
C:\Users\codex\Documents\GitHub\TND6480i\docs\N64_480i_porting_playbook.md
C:\Users\codex\Documents\GitHub\TND6480i\docs\project_retrospective_20260525.md
C:\Users\codex\Documents\GitHub\TND6480i\docs\reverse_engineering_technical_findings.md
C:\Users\codex\Documents\GitHub\TND6480i\docs\measurable_480i_validation_workflow_20260525.md
C:\Users\codex\Documents\GitHub\TND6480i\docs\runtime_text_measurement_attempt_20260525.md

Work only on the N64 project. Use Git from the beginning. Keep commercial ROMs,
generated ROMs, saves, and raw captures out of normal commits. Build named
candidates with hashes and manifests. Use emulator smoke tests for quick
rejects, then hardware captures before promotion. Prefer direct-stage,
direct-screen, or no-controller probes over repeated manual playthroughs.

Before patching, map the target game's framebuffer, VI, z-buffer, TLB/page
cache, viewport, menu/front-end, text/HUD, and save paths. The first candidate
must test one clear hypothesis.
```

## Useful Statistics

Local repo snapshot after the 2026-05-25 font-good pass:

| Item | Count |
|---|---:|
| Git commits on `main` | 91 |
| `.z64` files | 135 |
| `.sav` files | 738 |
| `.eep` files | 766 |
| BPS patches | 78 |
| xdelta patches | 2 |
| IPS patches | 12 |
| JSON reports/manifests | 1,820 |
| PNG captures | 9,568 |
| JPG/contact sheets | 999 |
| MP4 clips | 384 |
| MKV clips | 19 |
| Files in `artifacts/generated` | 1,559 |
| Files in `artifacts/release` | 82 |
| Files in `reports` | 2,896 |
| Files in `diagnostics/captures` | 10,925 |
| Scripts | 181 |
| Docs | 23 |

These numbers are useful mostly as a caution. The successful workflow is not
"generate thousands of ROMs"; it is "make a falsifiable candidate, capture the
right screen, compare it to the right reference, then document promotion or
rejection."

## Suggested Cleanup Before Public Release

Before a public release or handoff:

1. Generate a stock-GoldenEye-USA-to-`g1hiq3_gegate` xdelta package.
2. Include the short-name `G1HQ3AM` test package only as local hardware
   convenience, not as a public ROM distribution.
3. Keep `g1mcfix4` documented as rollback, not current best.
4. Add one final full-playthrough note after a normal controller route.
5. Add final hashes for patch, target ROM, and save.
6. Commit only scripts, docs, manifests, and patch metadata allowed by the repo
   policy.
