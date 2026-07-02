# TND6480i

Tomorrow Never Dies 64 480i reverse-engineering workspace.

This repository tracks the scripts, notes, diagnostics, and release metadata used
to adapt the GoldenEye 007 based Tomorrow Never Dies 64 romhack toward the
GoldenEye 007 Enhanced 480i behavior: higher-resolution/interlaced rendering,
GE480i-style front-end layout, stable gameplay, and hardware-tested N64 output.

ROM images, generated candidate ROMs, save files, video captures, and binary
patch blobs are intentionally local/untracked. Distribute patches and manifests,
not ROMs.

## Base Romhack Provenance

This work is based on the **Tomorrow Never Dies 64 11-24 Extended Edition**
romhack. Any public repo, release notes, or patch package should state that
clearly.

As of 2026-07-02, TiJay indicated that publishing this repository is okay as
long as the 11-24 Extended Edition basis is made clear, and may speak with Wreck
about including the patch in a future Vault bundle. Treat Vault inclusion as an
upstream packaging possibility, not as something this repo can promise.

## AI Assistance Disclosure

This project was developed with AI assistance from OpenAI Codex for reverse
engineering support, scripting, documentation, visual comparison workflows, and
candidate iteration. Hardware setup, real-console testing, subjective visual
review, and final project direction were provided by the human project owner.

## Current Result

Current best hardware/Analogue-confirmed test candidate:

- Candidate: `g1hiq3_gegate` / short flashcart name `G1HQ3AM`
- Local ROM: `artifacts/generated/g1hiq3_gegate.z64`
- Local ROM MD5: `4063fd9968b528148a9441b11dfd0203`
- Local ROM SHA256: `f359631cb63bb367e56a6c39a5f95b6fc11a3fda5b8a2c2eed87a3da5aded3d3`
- Local ROM size: `16,931,328 bytes`
- Normalized save: `artifacts/generated/g1hiq3_gegate_ammoon.sav`
- Save/EEP MD5: `50a3f7cf6e022fdec7f37f2cc8ae2e2a`
- N64 save type: `EEPROM 4K`
- Required hardware profile: NTSC, Expansion Pak / 8 MB

User/hardware validation has confirmed the important path: all levels boot,
gameplay, pause/watch, HUD, bullets UI, dossier pages, multiplayer screens,
cheat menu, mission-complete formatting, credits, and current font rendering
are in the expected visual family. The 2026-05-25 follow-up also confirmed that
the Bazaar countdown timer position is corrected on the `g1hiq3_gegate` line.
The in-game anti-aliasing option materially affects perceived text quality, so
future text/HUD comparisons must record and, when possible, normalize the AA
state along with ammo/display options. Do not compare AA-on captures against
AA-off captures and call the difference a render-contract regression.
Keep any future release label honest by rechecking full credits,
failed/aborted mission result pages, and one normal controller walkthrough after
any additional ROM edits.

Packaged rollback release candidate:

- Candidate: `g1mcfix4` / `TND6480i_g1mcfix4_RC1`
- Local ROM: `artifacts/generated/g1mcfix4.z64`
- Local ROM MD5: `FA93BE061C59EF5CABAD24FBF5F66B39`
- Local ROM size: `16,931,328 bytes`
- N64 save type: `EEPROM 4K`
- Required hardware profile: NTSC, Expansion Pak / 8 MB

`g1mcfix4` remains useful as a packaged rollback because it has the existing
stock-GE xdelta release bundle. The newer `g1hiq3_gegate` line should be used
for current testing and for the next public patch package.

## Release Artifacts

Primary patch, from stock GoldenEye 007 USA directly to TND6480i:

- ZIP: `artifacts/release/TND6480i_g1mcfix4_RC1_from_stock_GE007_xdelta.zip`
- xdelta: `artifacts/release/TND6480i_g1mcfix4_RC1_from_stock_GE007_xdelta/TND6480i_g1mcfix4_RC1_from_stock_GE007.xdelta`
- Source ROM MD5: `70c525880240c1e838b8b1be35666c3b`
- Target ROM MD5: `fa93be061c59ef5cabad24fbf5f66b39`
- Patch MD5: `5e0447557b0d275e265c54bd1cb98553`
- ZIP MD5: `8cc937c01eb6d208c6bfe060a57f63af`

Apply with xdelta3:

```powershell
xdelta3 -d `
  -s "GoldenEye 007 (USA).z64" `
  "TND6480i_g1mcfix4_RC1_from_stock_GE007.xdelta" `
  "TND6480i_g1mcfix4_RC1.z64"
```

Other local release helpers:

- BPS package from the local TND baseline:
  `artifacts/release/TND6480i_g1mcfix4_RC1.zip`
- Local ROM copy for flashcart use:
  `artifacts/release/TND6480i_g1mcfix4_RC1_rom_local/TND6480i_g1mcfix4_RC1.z64`
- EverDrive/X7 save helper:
  `artifacts/release/TND6480i_g1mcfix4_RC1_everdrive_sd_helper.zip`
- Current font-good hardware test bundle:
  `artifacts/release/TND6480i_g1hiq3_fontgood_20260525_test.zip`

Font-good test bundle manifest:

```text
G1HQ3AM.Z64  MD5 4063fd9968b528148a9441b11dfd0203
G1HQ3AM.SAV  MD5 50a3f7cf6e022fdec7f37f2cc8ae2e2a
G1HQ3AM.EEP  MD5 50a3f7cf6e022fdec7f37f2cc8ae2e2a
ZIP          MD5 88a835bb72aa2f0dfbe2e8bc06103945
ZIP       SHA256 a2a98c28ac87d13f52d76b8d5eabd74695fcd69c75b30e2d6430af41fadd1802
```

## Hardware Workflow

The final candidate was developed with three feedback loops:

- Emulators: Gopher64, Ares, Project64 for smoke tests, routing, screenshots,
  and fast rejects.
- SC64 / SummerCart64: rapid real-hardware direct boot and explicit EEPROM 4K
  save upload.
- GV-USB2 over S-Video: real N64 capture for visual proof against GE480i
  reference captures.

Prefer SC64 for development iteration. It allows direct upload and explicit save
type control. Use EverDrive X7 for final user-facing SD-card behavior only.

Typical SC64 direct upload:

```powershell
C:\Users\codex\Documents\n64\sc64deployer.exe upload `
  --direct `
  --save-type eeprom4k `
  --save artifacts\generated\g1mcfix4.sav `
  artifacts\generated\g1mcfix4.z64
```

For the current font-good ROM, upload the stable ROM with the normalized
ammo-on save:

```powershell
C:\Users\codex\Documents\n64\sc64deployer.exe upload `
  --direct `
  --save-type eeprom4k `
  --save artifacts\generated\g1hiq3_gegate_ammoon.sav `
  artifacts\generated\g1hiq3_gegate.z64
```

GV-USB2 single-frame capture:

```powershell
ffmpeg -hide_banner -y `
  -f dshow `
  -video_size 720x480 `
  -framerate 29.97 `
  -i video="GV-USB2, Analog Capture" `
  -frames:v 1 diagnostics\captures\current\probe.png
```

### Hardware-In-The-Loop Method

The useful breakthrough was treating real N64 output as a scripted test target,
not as a final manual check. The loop was:

1. Build a narrow ROM candidate from documented offset changes.
2. Smoke it in emulator to reject crashes and obvious black screens quickly.
3. Upload it to SC64 with the intended save type and known-good save state.
4. Power-cycle or reset the N64 when needed through the Kasa-controlled outlet.
5. Capture stills or clips from GV-USB2 over S-Video with ffmpeg.
6. Generate contact sheets or comparison atlases against GE480i reference
   footage.
7. Promote, reject, or narrow the next patch based on measured screen behavior.

This mattered because several candidates looked plausible in emulators but
failed on real hardware, and several visual issues were only obvious from the
capture path or from Analogue 3D output. The SC64 direct-boot path made the loop
fast enough to test many small candidates, while the Kasa outlet reduced the
cost of hard-lock recovery when a bad ROM wedged the console.

## EverDrive X7 Save Notes

EverDrive X7 correctly reports this ROM as:

- Save type: `EEP4k`
- RTC: `Off`
- Region: `NTSC`

The working X7 save file is the per-ROM auto-load file:

```text
ED64\gamedata\TND6480i_g1mcfix4_RC1.eep
```

Manual "copy file to RAM" was not reliable for this project because the X7 can
reload or overwrite from its active `gamedata` file. The reliable flow was:

1. Launch a different save-capable N64 game to flush the active TND save.
2. Reset to the EverDrive menu.
3. Power off the N64.
4. Mount the microSD on the PC.
5. Replace the exact `ED64\gamedata\TND6480i_g1mcfix4_RC1.eep` file.
6. Eject, boot, and launch the ROM normally.

Working all-unlocked X7 save:

- Local patched save: `C:\Users\codex\Documents\TND_X7_Current_unlocked.eep`
- Size: `512 bytes`
- MD5: `DAF246CED5C48CD6AFEF841E9C4078D1`
- Patched slots: `0`, `1`, `3`, and active wear slot `4`
- CRCs: valid after patching

Reusable patch script:

```powershell
powershell -ExecutionPolicy Bypass `
  -File scripts\hardware\patch_everdrive_tnd_save.ps1 `
  -Apply
```

## Repository Layout

- `scripts/`: ROM builders, patchers, emulator smoke tests, hardware helpers.
- `scripts/hardware/`: Kasa/GV-USB2/flashcart-facing helper scripts.
- `docs/`: long-form findings, handoffs, candidate histories, comparisons.
- `reports/`: JSON manifests, smoke results, offset audits, screen analyses.
- `diagnostics/captures/`: screenshots, videos, contact sheets, visual proof.
- `artifacts/roms/`: local source ROMs and baselines, ignored by git.
- `artifacts/generated/`: generated candidates/saves/patches, ignored by git.
- `artifacts/release/`: local release packages, ignored by git.

Important current/history docs:

- `docs/current_candidate_status_20260519.md`
- `docs/project_retrospective_20260525.md`
- `docs/reverse_engineering_technical_findings.md`
- `docs/decomp_480i_findings.md`
- `docs/dossier_matrix_findings_20260518.md`
- `docs/direct_stage_probe_workflow.md`
- `docs/patch_site_audit.md`

## Source ROM Expectations

Patch generation and verification assume a stock GoldenEye 007 USA source ROM:

```text
GoldenEye 007 (USA).z64
MD5: 70c525880240c1e838b8b1be35666c3b
```

Several scripts also use local untracked baselines in `artifacts/roms/`, such as
stock TND64, GE480i, and intermediate TND6480i baselines. Keep those local and
do not commit them.

## Practical Development Rules

Use evidence before promotion:

1. Smoke the candidate in emulator.
2. Capture a hardware startup/contact sheet.
3. Verify screen families against GE480i reference captures.
4. Test real gameplay, pause/watch, and mission/result flow.
5. Record the ROM hash, patch hash, changed offsets, and pass/fail notes.

For text/HUD evidence, also record the save/options state used for the capture:
ammo display, screen mode/aspect, and anti-aliasing. The AA save bit is not yet
mapped in this repo, so treat it as a required manual test condition until it is
identified by a dedicated save diff.

Prioritize fixes in this order:

1. Gameplay stability and all-level bootability.
2. Pause/watch/HUD/readability.
3. Dossier and mission-selection pages.
4. Mission intro/outro/result pages.
5. Front-end polish: logos, gunbarrel, title, cast credits, end credits.

Do not treat emulator-only success as final. The N64 plus GV-USB2 capture path
is the source of truth for visual correctness.

## Useful Scripts

Build/test save files:

```powershell
python scripts\make_tnd_test_save.py `
  --input "C:\Users\codex\Documents\007 - Tomorrow Never Dies (USA).sav" `
  --output artifacts\generated\tnd_test_all_missions.sav `
  --unlock-cheats
```

Patch an exact EverDrive EEPROM dump while preserving its size:

```powershell
python scripts\patch_tnd_eep_in_place.py `
  "C:\Users\codex\Documents\TND_X7_Current.eep" `
  "C:\Users\codex\Documents\TND_X7_Current_unlocked.eep"
```

Run a Gopher64 smoke:

```powershell
python scripts\smoke_gopher64.py `
  artifacts\generated\g1mcfix4.z64 `
  --gopher tools\emulators\gopher64.exe `
  --ffmpeg C:\Users\codex\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe `
  --report reports\smoke\smoke_g1mcfix4.json `
  --seconds 85 `
  --input `
  --capture-dir diagnostics\captures\gopher_g1mcfix4 `
  --capture-times 45,55,65,75,84 `
  --keep-dark-title-captures
```

## Project Scale

At the time of the `g1mcfix4` RC handoff, the local workspace contained roughly:

- `91` git commits on `main`
- `1,512` generated candidate ROMs
- `987` generated `.sav` files
- `979` generated `.eep` files
- `70` BPS patches
- `2,623` reports
- `10,302` diagnostic capture files
- `8,904` PNG captures
- `976` JPG/contact sheets
- `376` MP4 clips
- `35` MKV clips

After the 2026-05-25 text/font follow-up, a fresh local count showed:

- `91` git commits on `main`
- `135` `.z64` ROM/candidate files under the repo root
- `738` `.sav` files
- `766` `.eep` files
- `78` BPS patches
- `2` xdelta patches
- `12` IPS patches
- `1,820` JSON reports/manifests
- `9,568` PNG captures
- `999` JPG/contact-sheet files
- `384` MP4 clips
- `19` MKV clips
- `1,559` files in `artifacts/generated`
- `82` files in `artifacts/release`
- `2,896` files in `reports`
- `10,925` files in `diagnostics/captures`
- `181` scripts
- `23` docs

These counts include rejected and diagnostic candidates. The volume is a warning:
future work should start from the comparison/checklist workflow, not brute-force
candidate generation.
