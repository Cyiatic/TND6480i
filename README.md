# TND6480i

Tomorrow Never Dies 64 480i reverse-engineering workspace.

This repo tracks the scripts, notes, diagnostics, and release metadata used to
adapt the GoldenEye 007 based **Tomorrow Never Dies 64** romhack toward the
GoldenEye 007 Enhanced 480i behavior: higher-resolution/interlaced rendering,
GE480i-style front-end layout, stable gameplay, and hardware-tested N64 output.

ROM images, generated candidate ROMs, save files, video captures, and binary
patch blobs are intentionally local/untracked. Distribute patches and manifests,
not ROMs.

## Status

Current best hardware/Analogue-confirmed test candidate:

- Candidate: `g1hiq3_gegate` / short flashcart name `G1HQ3AM`
- ROM MD5: `4063fd9968b528148a9441b11dfd0203`
- ROM SHA256:
  `f359631cb63bb367e56a6c39a5f95b6fc11a3fda5b8a2c2eed87a3da5aded3d3`
- Save/EEP MD5: `50a3f7cf6e022fdec7f37f2cc8ae2e2a`
- Save type: `EEPROM 4K`
- Hardware profile: NTSC N64, Expansion Pak / 8 MB

Hardware/user validation has confirmed all levels boot, gameplay is stable,
pause/watch/HUD text is in the expected visual family, dossier pages and menus
are usable, and the final text/font pass looks correct with the right in-game
anti-aliasing/display option state.

If text appears unusually pixelated, check the in-game anti-aliasing option
before treating it as a patch regression. AA-off can make the same
`g1hiq3_gegate` ROM look substantially rougher than the accepted AA-on test
state.

The previous packaged rollback candidate is `g1mcfix4` /
`TND6480i_g1mcfix4_RC1`; it remains documented because it has the existing
stock-GE xdelta release bundle.

## Release Candidate

Current prerelease:
[v0.1.0-rc1](https://github.com/Cyiatic/TND6480i/releases/tag/v0.1.0-rc1)

The release asset is a BPS patch package, not a ROM. Apply it to a stock
GoldenEye 007 USA ROM:

```text
Source: GoldenEye 007 (USA).z64
MD5:    70c525880240c1e838b8b1be35666c3b
Patch:  TND6480i_g1hiq3_RC1_from_stock_GE007.bps
Target: g1hiq3_gegate / G1HQ3AM
MD5:    4063fd9968b528148a9441b11dfd0203
```

Use a BPS patcher such as Floating IPS / flips. Full hashes and release notes
are in [release artifacts and save notes](docs/release_artifacts_and_save_notes.md).

## Provenance

This work is based on the **Tomorrow Never Dies 64 11-24 Extended Edition**
romhack. Any public repo, release notes, or patch package should state that
clearly.

## Using This Repo

This repository is primarily a development and documentation workspace. It is
useful in three different ways:

- Players/testers should start with
  [release artifacts and save notes](docs/release_artifacts_and_save_notes.md)
  for the current candidate hashes, save type, and EverDrive/SC64 notes.
- Modders should start with
  [reverse-engineering technical findings](docs/reverse_engineering_technical_findings.md)
  and [patch-site audit](docs/patch_site_audit.md) to understand the memory map,
  VI/framebuffer changes, rejected approaches, and high-value offsets.
- Future 480i porting work should start with
  [N64 480i porting playbook](docs/N64_480i_porting_playbook.md) and
  [measurable validation workflow](docs/measurable_480i_validation_workflow_20260525.md)
  before generating new candidates.

To reproduce the workflow locally, provide your own legal source ROMs and keep
them under `artifacts/roms/`. Generated ROMs, saves, patches, and captures
should stay local unless a release package is deliberately prepared. Most
scripts assume Windows paths from the original workstation and may need path
adjustments for another machine.

## Known Caveats

- No ROMs are distributed here or in the release assets.
- The patch is based on Tomorrow Never Dies 64 11-24 Extended Edition.
- The target hardware profile is NTSC N64 with Expansion Pak / 8 MB.
- Save type is `EEPROM 4K`.
- The in-game anti-aliasing option materially affects perceived text quality.
  Compare AA-on captures against AA-on captures, and AA-off against AA-off.
- Emulator success is useful but not conclusive; real N64 capture remains the
  release authority.

## Documentation Map

- [Release artifacts and save notes](docs/release_artifacts_and_save_notes.md)
- [Credits and acknowledgements](docs/credits.md)
- [Current candidate status](docs/current_candidate_status_20260519.md)
- [Reverse-engineering technical findings](docs/reverse_engineering_technical_findings.md)
- [Measurable 480i validation workflow](docs/measurable_480i_validation_workflow_20260525.md)
- [N64 480i porting playbook](docs/N64_480i_porting_playbook.md)
- [Project retrospective](docs/project_retrospective_20260525.md)
- [Direct stage probe workflow](docs/direct_stage_probe_workflow.md)
- [Patch-site audit](docs/patch_site_audit.md)
- [Publishing notes](docs/publishing_notes_20260702.md)

## Repository Layout

- `scripts/`: ROM builders, patchers, emulator smoke tests, hardware helpers.
- `scripts/hardware/`: Kasa/GV-USB2/flashcart-facing helper scripts.
- `docs/`: long-form findings, handoffs, candidate histories, comparisons.
- `reports/`: JSON manifests, smoke results, offset audits, screen analyses.
- `diagnostics/captures/`: curated screenshots, videos, contact sheets, visual proof.
- `artifacts/roms/`: local source ROMs and baselines, ignored by git.
- `artifacts/generated/`: generated candidates/saves/patches, ignored by git.
- `artifacts/release/`: local release packages, ignored by git.

## How This Was Done

The useful breakthrough was a real-hardware feedback loop:

1. Build a narrow candidate.
2. Smoke it in Gopher64/Ares/Project64.
3. Upload to SC64 / SummerCart64 with explicit EEPROM 4K save state.
4. Reset or power-cycle the real N64, often through a Kasa smart outlet.
5. Capture GV-USB2 S-Video output with ffmpeg.
6. Compare contact sheets and atlases against GoldenEye 480i reference footage.
7. Promote, reject, or narrow the next patch based on measured behavior.

Details: [Hardware-In-The-Loop Workflow](docs/hardware_in_the_loop.md)

## Patch Source ROM

Patch generation and verification assume a stock GoldenEye 007 USA source ROM:

```text
GoldenEye 007 (USA).z64
MD5: 70c525880240c1e838b8b1be35666c3b
```

Several scripts also use local untracked baselines in `artifacts/roms/`, such as
stock TND64, GE480i, and intermediate TND6480i baselines. Keep those local and
do not commit them.

## Development Rules

Use evidence before promotion:

1. Smoke the candidate in emulator.
2. Capture a hardware startup/contact sheet.
3. Verify screen families against GE480i reference captures.
4. Test real gameplay, pause/watch, and mission/result flow.
5. Record ROM hash, patch hash, changed offsets, save/options state, and
   pass/fail notes.

Do not treat emulator-only success as final. Real N64 output through GV-USB2,
plus Analogue/human review where useful, is the source of truth.

## Testing Notes

Useful bug reports should include:

- ROM/release hash or tag.
- Hardware or emulator used.
- Flashcart and save type, if testing on N64.
- Display path, such as S-Video capture, CRT, Analogue 3D, or emulator video.
- In-game display options, especially anti-aliasing and ammo/HUD state.
- Screenshot, capture clip, or contact sheet when the issue is visual.
- Exact menu, level, cutscene, or gameplay route used to reproduce the issue.

## License / Use

The scripts and documentation in this repository are provided for research,
patch development, and interoperability work. This repository does not grant any
rights to GoldenEye 007, Tomorrow Never Dies 64, commercial ROM images, or
third-party assets. Do not distribute ROMs.

## Credits

Key credits: Rare, the Tomorrow Never Dies 64 team, TiJay, Wreck, the
GoldenEye 480i / Hi Res patch contributors, Cyiatic, and OpenAI Codex.

See [Credits And Acknowledgements](docs/credits.md) for the fuller list.

## AI Assistance Disclosure

This project was developed with AI assistance from OpenAI Codex for reverse
engineering support, scripting, documentation, visual comparison workflows, and
candidate iteration. Hardware setup, real-console testing, subjective visual
review, and final project direction were provided by the human project owner.
