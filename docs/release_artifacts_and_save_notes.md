# Release Artifacts And Save Notes

This repo intentionally does not track ROM images, generated candidate ROMs,
save files, video captures, or binary patch blobs. Public releases should
distribute patches, manifests, and documentation, not ROMs.

## Current Test Candidate

- Candidate: `g1hiq3_gegate` / short flashcart name `G1HQ3AM`
- Local ROM: `artifacts/generated/g1hiq3_gegate.z64`
- Local ROM MD5: `4063fd9968b528148a9441b11dfd0203`
- Local ROM SHA256:
  `f359631cb63bb367e56a6c39a5f95b6fc11a3fda5b8a2c2eed87a3da5aded3d3`
- Local ROM size: `16,931,328 bytes`
- Normalized save: `artifacts/generated/g1hiq3_gegate_ammoon.sav`
- Save/EEP MD5: `50a3f7cf6e022fdec7f37f2cc8ae2e2a`
- N64 save type: `EEPROM 4K`
- Required hardware profile: NTSC, Expansion Pak / 8 MB

This is the current hardware/Analogue-confirmed line and should be used for
current testing and the next public patch package.

Important display-option caveat: the in-game anti-aliasing option materially
affects perceived text quality. If pause/watch/HUD/mission-intro text looks
pixelated, verify the AA setting before treating the patch as regressed. The
accepted `g1hiq3_gegate` result was judged with the correct display-option
state, and AA-off can make the same ROM appear much rougher.

The public `v0.1.0-rc1` BPS release targets this exact `g1hiq3_gegate` ROM:

- Target MD5: `4063fd9968b528148a9441b11dfd0203`
- Target SHA256:
  `f359631cb63bb367e56a6c39a5f95b6fc11a3fda5b8a2c2eed87a3da5aded3d3`

## Packaged Rollback Candidate

- Candidate: `g1mcfix4` / `TND6480i_g1mcfix4_RC1`
- Local ROM: `artifacts/generated/g1mcfix4.z64`
- Local ROM MD5: `FA93BE061C59EF5CABAD24FBF5F66B39`
- Local ROM size: `16,931,328 bytes`
- N64 save type: `EEPROM 4K`
- Required hardware profile: NTSC, Expansion Pak / 8 MB

`g1mcfix4` remains useful as a packaged rollback because it has the existing
stock-GE xdelta release bundle.

## Existing Xdelta Package

Primary patch, from stock GoldenEye 007 USA directly to TND6480i:

- ZIP:
  `artifacts/release/TND6480i_g1mcfix4_RC1_from_stock_GE007_xdelta.zip`
- xdelta:
  `artifacts/release/TND6480i_g1mcfix4_RC1_from_stock_GE007_xdelta/TND6480i_g1mcfix4_RC1_from_stock_GE007.xdelta`
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

## Font-Good Test Bundle Manifest

```text
G1HQ3AM.Z64  MD5 4063fd9968b528148a9441b11dfd0203
G1HQ3AM.SAV  MD5 50a3f7cf6e022fdec7f37f2cc8ae2e2a
G1HQ3AM.EEP  MD5 50a3f7cf6e022fdec7f37f2cc8ae2e2a
ZIP          MD5 88a835bb72aa2f0dfbe2e8bc06103945
ZIP       SHA256 a2a98c28ac87d13f52d76b8d5eabd74695fcd69c75b30e2d6430af41fadd1802
```

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
