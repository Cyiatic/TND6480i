# N64 480i Porting Playbook

This note distills reusable lessons from the TND6480i project into a
project-neutral workflow for future N64 480i / hi-res patch work.

## Core Principle

Treat 480i as a coordinated render-system port, not a resolution-constant
patch.

The TND6480i breakthrough came from handling these together:

- framebuffer size and placement
- VI mode and dimension tables
- viewport setup and camera path dimensions
- z-buffer ownership
- TLB/page-cache placement
- front-end/menu render paths
- text/layout coordinate systems
- save options that affect visible HUD/UI output
- anti-aliasing/display options that affect perceived text quality
- hardware capture verification

Any one of these can appear to work alone in an emulator while failing on real
hardware.

## Recommended Repo Structure

```text
README.md
docs/
  current_candidate_status_YYYYMMDD.md
  reverse_engineering_technical_findings.md
  project_retrospective_YYYYMMDD.md
  verification_matrix.md
  release_checklist.md
  direct_probe_workflow.md
reports/
  candidate_manifests.json
  patch_site_audit.json
scripts/
  build_candidate.py
  build_direct_probe_roms.py
  smoke_emulator.py
  build_video_contact_sheet.py
artifacts/
  generated/
  release/
  roms/          local only; do not commit commercial ROMs
diagnostics/
  captures/      local only unless intentionally publishing derived stills
```

Keep generated ROMs, huge captures, and proprietary assets out of Git unless
the repo is intentionally private and licensed to hold them.

## Candidate Discipline

Every candidate should have:

- a short stable name
- source ROM hash
- target ROM hash
- exact patch-site list
- reason for the change
- expected behavior
- paired save file and save type
- rejection or promotion notes

Avoid changing multiple unrelated systems in one candidate. If a candidate
touches framebuffer placement, do not also change menu text unless there is a
specific dependency.

## Reverse Engineering Checklist

Find and document:

- boot/video init path
- framebuffer allocation and clear routines
- active framebuffer pointer selection
- VI width/height/interlace settings
- resolution and viewport tables
- camera viewport setup
- menu/front-end viewport setup
- z-buffer dimensions and allocation
- memory heap/page-cache/TLB boundaries
- text rendering coordinate space
- stage/level boot path
- save type and per-folder option layout
- debug or command-line hooks useful for direct probes

For each patch site, record the ROM offset, old word, new word, and a
plain-English reason.

## Hardware Workflow

Use emulators for fast iteration, but promote only with hardware evidence.

Recommended hardware loop:

1. Build candidate and manifest.
2. Run emulator smoke test.
3. Build direct-stage or direct-screen probes where possible.
4. Upload one candidate/probe to flashcart.
5. Capture through GV-USB2 or equivalent.
6. Build contact sheet.
7. Compare against stock and known 480i reference.
8. Promote, reject, or narrow the next hypothesis.

Manual playthroughs are expensive. Use them only after direct probes and
captures suggest a candidate is promising.

## Visual Comparison Workflow

For each important screen, keep:

- stock game reference
- known-good 480i reference if available
- current candidate capture
- annotated comparison image

Compare:

- active image area
- text size and sharpness
- cursor/highlight alignment
- menu hitbox alignment
- sprite/background origin
- viewport height and width
- flicker/strobe artifacts
- performance/cadence

Do not rely only on "it boots." Incorrect 480i often boots and looks
superficially close.

## Lessons From TND6480i

- The final working path needed two 640x480x16 framebuffers placed safely in
  Expansion Pak RAM.
- Framebuffer placement had to be coordinated with the page-cache/TLB region.
- Reducing memory ranges could make levels boot but cause severe performance
  regressions.
- Some screens used separate front-end/menu paths that required layout-specific
  fixes after the core 480i render path worked.
- Direct-stage and no-controller probes saved enormous manual testing time.
- Real hardware exposed issues that emulators either missed or made ambiguous.
- Screen-by-screen annotated comparisons prevented false "close enough"
  promotions.
- Save options can make visual comparisons invalid. Confirm that HUD,
  widescreen, ammo display, anti-aliasing, and folder settings match before
  comparing two ROMs.
- The final text-quality pass was solved by auditing GE480i render-contract
  constants and validating with matched capture metrics plus hardware/Analogue
  review, not by moving framebuffers again.
- UI overlay fixes can have collateral benefits. In TND6480i, the same
  text/HUD/front-end constant line that fixed perceived font quality also fixed
  Bazaar's countdown timer placement.
- The next public-facing step after a confirmed local ROM is packaging the exact
  stock-ROM-to-target patch and recording target hashes.

## When Starting A New Game

Do not assume GoldenEye/TND offsets transfer. Assume only the investigation
pattern transfers.

Start by proving:

- stock ROM hash and region
- bootability on emulator and hardware
- Expansion Pak behavior
- existing hi-res or letterbox modes, if any
- framebuffer locations in stock
- VI setup routines
- menu and gameplay render paths
- text/HUD render path
- save type and option layout
- anti-aliasing/display-option state
- a way to direct-load levels or test screens

Then build the smallest possible proof candidate that changes one render-system
layer at a time.

## Better First-Week Checklist

Use this order before attempting a public-facing candidate:

1. Create the repo and ignore generated ROMs, saves, captures, and proprietary
   assets.
2. Record stock ROM hashes and any known reference patch hashes.
3. Capture stock hardware boot/gameplay/menu footage.
4. Capture a known-good 480i reference when one exists.
5. Map framebuffer, VI, z-buffer, heap/page-cache, camera viewport, front-end
   viewport, text/HUD, and save paths.
6. Build an emulator smoke harness.
7. Build a hardware capture command and contact-sheet workflow.
8. Build direct-stage/direct-screen probes before relying on repeated manual
   playthroughs.
9. Promote only named candidates with manifests, hashes, and explicit
   pass/fail notes.
10. When manual testing gets tiring, stop and improve the probe.

## Prompt Template

```text
Work only on this N64 480i project. Use Git from the start. Do not commit ROMs,
saves, or raw captures. Before patching, document stock hashes, capture setup,
framebuffer/VI/z-buffer/memory/viewports/text paths, and the first falsifiable
hypothesis. Build named candidates with manifests and hashes. Use emulator
smoke tests for fast rejection, then hardware capture before promotion. Prefer
direct-stage, direct-screen, and no-controller probes over repeated manual
controller routes.
```
