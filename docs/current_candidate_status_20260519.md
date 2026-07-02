# Current Candidate Status - 2026-05-19

Current best hardware/Analogue-confirmed test candidate:

- ROM: `artifacts/generated/g1hiq3_gegate.z64`
- Short flashcart package: `artifacts/release/TND6480i_g1hiq3_fontgood_20260525_test.zip`
- Short ROM name: `G1HQ3AM.Z64`
- Save mirror: `artifacts/generated/g1hiq3_gegate_ammoon.sav`
- EEPROM mirror: `artifacts/generated/g1hiq3_gegate_ammoon.eep`
- ROM MD5: `4063fd9968b528148a9441b11dfd0203`
- ROM SHA256: `f359631cb63bb367e56a6c39a5f95b6fc11a3fda5b8a2c2eed87a3da5aded3d3`
- Save/EEP MD5: `50a3f7cf6e022fdec7f37f2cc8ae2e2a`
- Save/EEP SHA256: `84d70b8380b9b14b7a005451ac1b6ebe5800b5787bd3ac38acc09e4e31d28058`
- Test ZIP MD5: `88a835bb72aa2f0dfbe2e8bc06103945`
- Test ZIP SHA256: `a2a98c28ac87d13f52d76b8d5eabd74695fcd69c75b30e2d6430af41fadd1802`
- ROM size: `16,931,328` bytes
- Save type: EEPROM 4K
- Region: NTSC
- Memory target: Expansion Pak / 8 MB

Packaged rollback release candidate:

- ROM: `artifacts/generated/g1mcfix4.z64`
- Save mirror: `artifacts/generated/g1mcfix4.sav`
- EEPROM mirror: `artifacts/generated/g1mcfix4.eep`
- ROM MD5: `fa93be061c59ef5cabad24fbf5f66b39`
- ROM size: `16,931,328` bytes
- Save type: EEPROM 4K
- Region: NTSC
- Memory target: Expansion Pak / 8 MB

Primary release patch:

- ZIP: `artifacts/release/TND6480i_g1mcfix4_RC1_from_stock_GE007_xdelta.zip`
- XDelta: `artifacts/release/TND6480i_g1mcfix4_RC1_from_stock_GE007_xdelta/TND6480i_g1mcfix4_RC1_from_stock_GE007.xdelta`
- Source ROM: clean GoldenEye 007 USA
- Source MD5: `70c525880240c1e838b8b1be35666c3b`
- Target MD5: `fa93be061c59ef5cabad24fbf5f66b39`
- Patch MD5: `5e0447557b0d275e265c54bd1cb98553`
- ZIP MD5: `8cc937c01eb6d208c6bfe060a57f63af`

## Current Read

`g1hiq3_gegate` supersedes `g1mcfix4` for current testing because the
2026-05-25 hardware/Analogue follow-up confirmed the font output looks good
after the audited GE480i text/HUD/front-end constants and normalized ammo-on
save were used. It also fixed the Bazaar countdown timer position. `g1mcfix4`
still supersedes `g1mcfix1`, `g1cred1`, and the earlier diagnostic route ROMs
as the packaged rollback line with an existing stock-GE xdelta.

The user hardware pass on real N64 confirmed the important target behavior:

- All levels boot and run.
- Gameplay, pause/watch menu, bullets UI, and reticle are in the intended 480i layout.
- Bazaar and Labs no longer show the old severe rendering failures.
- Dossier pages, mission select, difficulty, briefing, multiplayer menus, credits, and mission-result screens have received real-hardware review after the final fixes.
- Font output now looks good on the `g1hiq3_gegate` line.
- Bazaar countdown timer position is corrected on the `g1hiq3_gegate` line.
- The only intentional non-resolution content edit is the save/difficulty label change from `Custom` to `007`.

2026-05-24 follow-up: the user reported that Analogue 3D output makes the mission intro text, ammo count, and pause/watch text look closer to stock resolution than GE480i. That report started the `g1mcfix4` text-resolution review before final release packaging. The first-test hardware candidate was `artifacts/generated/g1hiq1.z64`; the riskier follow-up was `artifacts/generated/g1hiq2.z64`. This line is superseded by the 2026-05-25 `g1hiq3_gegate` confirmation below. See `docs/text_resolution_followup_20260524.md`.

2026-05-25 follow-up: the active text-quality measurement baseline is now
`artifacts/generated/g1hiq3_gegate.z64` with
`artifacts/generated/g1hiq3_gegate.sav`. It preserves the all-level stability
line while carrying the audited GE480i text/HUD/front-end constant set. For
HUD/text comparisons, use the normalized ammo-on save
`artifacts/generated/g1hiq3_gegate_ammoon.sav`; the older all-missions save has
`OPTION_DISPLAYAMMO` disabled and can make GE480i/TND HUD captures
non-comparable. A no-controller real-hardware watch/HUD capture harness is
available in `scripts/build_force_fp_watch_probe.py`,
`scripts/build_auto_watch_text_probe.py --delay-frames`, and
`scripts/patch_save_options.py`. Matched GE480i/TND watch and HUD captures are
documented in `docs/runtime_text_measurement_attempt_20260525.md`. Keep
`g1mcfix4` as the packaged RC1 rollback; use `g1hiq3_gegate` for current
testing and release packaging.

2026-05-25 hardware/Analogue confirmation: the user reported that the font now
looks good on the current `g1hiq3_gegate` line, and that this same line also
fixed the Bazaar countdown timer position. The short-name test package is
`artifacts/release/TND6480i_g1hiq3_fontgood_20260525_test.zip`, containing
`G1HQ3AM.Z64` plus matching `G1HQ3AM.SAV`/`G1HQ3AM.EEP` save mirrors. Treat this
as the current font-good test build unless a later candidate explicitly
supersedes it.

2026-05-25 anti-aliasing observation: the in-game anti-aliasing option makes a
large visible difference to text quality. Text, HUD, pause/watch, and mission
intro comparisons must record the AA state and avoid mixing AA-on and AA-off
captures. The exact save bit is not yet mapped in `scripts/patch_save_options.py`;
do not force an unknown option bit into release saves until a before/after save
diff proves it.

2026-07-02 publishing/provenance note: TiJay indicated that publishing the repo
is okay as long as it clearly states that this patch is based on the Tomorrow
Never Dies 64 `11-24 Extended Edition`. He also said he may speak with Wreck
about including the patch as part of a future Vault bundle. Document this as
permission to publish the repo with clear provenance, not as a guarantee of
Vault inclusion.

## Save Handling

The EverDrive X7 uses EEPROM 4K for this build. The working all-unlocked save was written to:

- `E:\ED64\gamedata\TND6480i_g1mcfix4_RC1.eep`

Local helper outputs:

- `C:\Users\codex\Documents\TND_X7_Current_unlocked.eep`
- `scripts/patch_tnd_eep_in_place.py`
- `scripts/patch_save_options.py`
- `scripts/hardware/patch_everdrive_tnd_save.ps1`

If the save does not appear on EverDrive X7, the important detail is the path/name pairing: `ED64\gamedata\<exact ROM filename>.eep`. Manual "copy file to RAM" did not work reliably during testing; auto-loading the correctly named file did.

## Rejected Or Diagnostic

Do not treat these as release candidates:

- `g1mcfix1`: former candidate, superseded by `g1mcfix4`.
- `g1cred1`: important intermediate, superseded.
- `g1hbrf1`, `g1hlegal1`, `g1hnext1`, `g1tabhit1`: diagnostic/intermediate only.
- Route helper ROMs such as `brfauto*`, `brfbtn*`, and auto-navigation builds are diagnostic only.

## Next Work Order

1. Treat `g1hiq3_gegate` as the stable current ROM unless a new candidate has stronger static and hardware evidence.
2. Use the ammo-on save for HUD comparisons: `artifacts/generated/g1hiq3_gegate_ammoon.sav`.
3. Record the anti-aliasing setting for any text-quality capture; map the save bit with a deliberate save diff before scripting it.
4. Public-facing docs and release notes must state the patch is based on Tomorrow Never Dies 64 `11-24 Extended Edition`.
5. Generate the next public patch package from stock GoldenEye 007 USA to `g1hiq3_gegate` before calling this a release candidate.
6. Do not continue framebuffer-placement branches for the text concern; `g1hifb1`, `g1hqfb1`, and `g1hiq4_upperpair` were rejected.
7. If a future text regression appears, target runtime glyph/RDP evidence or an Analogue/HDMI capture route, not blind framebuffer moves.
8. Keep large ROMs, saves, release zips, raw captures, and local tools out of normal git commits.
