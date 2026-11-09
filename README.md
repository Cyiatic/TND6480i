<img src="assets/tnd6480i-logo.png" alt="Tomorrow Never Dies 6480i Expanded" width="483">

# TND6480i

Tomorrow Never Dies 64 480i reverse-engineering workspace.

This repo tracks the scripts, notes, diagnostics, and release metadata used to
adapt the GoldenEye 007 based **Tomorrow Never Dies 64** romhack toward the
GoldenEye 007 Enhanced 480i behavior: higher-resolution/interlaced rendering,
GE480i-style front-end layout, stable gameplay, and hardware-tested N64 output.

ROM images, generated candidate ROMs, save files, video captures, and binary
patch blobs are intentionally local/untracked. Distribute patches and manifests,
not ROMs.

## Download

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

## Known caveats

- No ROMs are distributed here or in the release assets.
- The patch is based on Tomorrow Never Dies 64 11-24 Extended Edition.
- The target hardware profile is NTSC N64 with Expansion Pak / 8 MB.
- Save type is `EEPROM 4K`.
- The in-game anti-aliasing option materially affects perceived text quality.
  Compare AA-on captures against AA-on captures, and AA-off against AA-off.
- Emulator success is useful but not conclusive; real N64 capture remains the
  release authority.

## Using this repo

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

Several scripts also use local untracked baselines in `artifacts/roms/`, such as
stock TND64, GE480i, and intermediate TND6480i baselines. Keep those local and
do not commit them.

## Documentation

Start with the [documentation index](docs/README.md). The most useful entry points:

| I want to… | Start here |
| --- | --- |
| Apply the patch, check hashes, set up saves | [Release artifacts and save notes](docs/release_artifacts_and_save_notes.md) |
| Understand the memory map and patch sites | [Technical findings](docs/reverse_engineering_technical_findings.md) · [Patch-site audit](docs/patch_site_audit.md) |
| Port another N64 game to 480i | [N64 480i porting playbook](docs/N64_480i_porting_playbook.md) · [Measurable validation workflow](docs/measurable_480i_validation_workflow_20260525.md) |
| Reproduce the hardware test loop | [Hardware-in-the-loop workflow](docs/hardware_in_the_loop.md) |
| Read how the project went | [Project retrospective](docs/project_retrospective_20260525.md) |
| Find dated handoffs, candidate notes and session logs | [docs/archive/](docs/archive/README.md) |

## Repository layout

- `assets/`: README logo and cover art.
- `scripts/`: ROM builders, patchers, emulator smoke tests, hardware helpers.
- `scripts/hardware/`: Kasa/GV-USB2/flashcart-facing helper scripts.
- `docs/`: long-form findings, workflows and guides ([index](docs/README.md)).
- `docs/archive/`: dated handoffs, candidate notes, session logs and superseded status pages.
- `reports/`: JSON manifests, smoke results, offset audits, screen analyses.
- `diagnostics/captures/`: curated screenshots, videos, contact sheets, visual proof.
- `artifacts/roms/`: local source ROMs and baselines, ignored by git.
- `artifacts/generated/`: generated candidates/saves/patches, ignored by git.
- `artifacts/release/`: local release packages, ignored by git.

## How this was done

The useful breakthrough was a real-hardware feedback loop:

1. Build a narrow candidate.
2. Smoke it in Gopher64/Ares/Project64.
3. Upload to SC64 / SummerCart64 with explicit EEPROM 4K save state.
4. Reset or power-cycle the real N64, often through a Kasa smart outlet.
5. Capture GV-USB2 S-Video output with ffmpeg.
6. Compare contact sheets and atlases against GoldenEye 480i reference footage.
7. Promote, reject, or narrow the next patch based on measured behavior.

Details: [Hardware-In-The-Loop Workflow](docs/hardware_in_the_loop.md)

## Development rules

Use evidence before promotion:

1. Smoke the candidate in emulator.
2. Capture a hardware startup/contact sheet.
3. Verify screen families against GE480i reference captures.
4. Test real gameplay, pause/watch, and mission/result flow.
5. Record ROM hash, patch hash, changed offsets, save/options state, and
   pass/fail notes.

Do not treat emulator-only success as final. Real N64 output through GV-USB2,
plus Analogue/human review where useful, is the source of truth.

## Reporting bugs

Useful bug reports should include:

- ROM/release hash or tag.
- Hardware or emulator used.
- Flashcart and save type, if testing on N64.
- Display path, such as S-Video capture, CRT, Analogue 3D, or emulator video.
- In-game display options, especially anti-aliasing and ammo/HUD state.
- Screenshot, capture clip, or contact sheet when the issue is visual.
- Exact menu, level, cutscene, or gameplay route used to reproduce the issue.

## Credits and provenance

This work is based on the **Tomorrow Never Dies 64 11-24 Extended Edition**
romhack. Any public repo, release notes, or patch package should state that
clearly.

Key credits: Rare, the Tomorrow Never Dies 64 team, TiJay, Wreck, the
GoldenEye 480i / Hi Res patch contributors, Cyiatic, and OpenAI Codex.

See [Credits And Acknowledgements](docs/credits.md) for the fuller list.

## License

The scripts and documentation are MIT-licensed; see [LICENSE](LICENSE). They are
provided for research, patch development, and interoperability work. The license
covers this repository's own code and writing only: it grants no rights to
GoldenEye 007, Tomorrow Never Dies 64, commercial ROM images, or third-party
assets. Do not distribute ROMs.

## AI Assistance Disclosure

This project was developed with AI assistance from OpenAI Codex for reverse
engineering support, scripting, documentation, visual comparison workflows, and
candidate iteration. The repository owner directed the work, reviewed the
resulting changes, and remains responsible for the project's technical claims
and final decisions. Hardware setup, real-console testing, and subjective visual
evaluation were performed by the repository owner.
