# TND6480i

Tomorrow Never Dies 64 480i investigation workspace.

This repo tracks the reproducible patch/build scripts, notes, hardware queue, and diagnostic reports. It intentionally does **not** track GoldenEye/TND ROM images, generated candidate ROMs, save files, or binary patch blobs.

## Current Status

- SC64 is working on `COM4` when connected.
- The capture path can see the SC64 menu; see `diagnostics/captures/capture_sc64_menu_before_repo_migration_20260509.png`.
- The current working candidate is `artifacts/generated/TND64_480i_split8030_8076_all_dim0_core_no_menu.z64` with MD5 `4fd6d3b38b50c2ec0a1bdd110598516c` and N64 CRC `25FD2E62 AF703620`. It uses split framebuffers at `0x80300000` and `0x8076A000`, applies the GE 480i VI-side word family, and patches only the first direct gameplay dimension word at `0x4F354`.
- This candidate passed a 60 second Gopher64 visual/input smoke and booted on a real N64 via SC64 direct mode, producing visible TND intro/logo output through at least 180 seconds over the GV-USB2 S-Video capture path.
- The rejected split `dim1` sibling, `artifacts/generated/TND64_480i_split8030_8076_all_dim1_core_no_menu.z64`, stayed black in Gopher64 visual capture. Do not patch the second direct dimension word at `0x4F35C` in this branch.
- A verified IPS patch from the clean expanded TND baseline exists locally at `artifacts/generated/TND6480i_split8030_8076_all_dim0_from_baseline_tnd.ips` with MD5 `d08906f5353b6b0dd2d7937f00c09e58`.
- Matching low-cave SC64 HVI-only debug builds now exist for the dim-aware candidates. The primary one is `artifacts/generated/TND64_480i_single8076_all_dim0_core_no_menu_sc64isv_hvionly_lowcave.z64` with MD5 `8e1c0d5b2b8b276af8558602d06a80d5` and N64 CRC `C6224ECF 7FEB4471`; it survived Gopher64 and printed repeated `TND:HVI1` markers.
- The first SC64 debug candidate had a real-hardware runtime-address bug in its trampolines. Fixed debug builds now use the ROM load mapping `0x1000 -> 0x80000400`.
- Corrected entry-time ISV logging still black-screened on known-good baseline TND, so entry hooks are no longer the next path.
- The first no-entry baseline ISV control also black-screened, but it was found to have a `DFB1` hook bug that skipped original framebuffer-global setup. That build is superseded.
- A later HVI-only baseline control still black-screened when its logger lived at ROM `0x331E0`; that high cave may not be resident in RDRAM on hardware. The current diagnostics use a lower early-code cave at `0x3CB0`.
- The low-cave HVI-only baseline control reached visible TND credits output on real hardware, but SC64 ISV did not report `TND:HVI1`.
- The safer `single8076_all_dim0` visual candidate launched on real hardware but stayed black through 60 seconds. Next useful work is offline isolation of the direct-dimension word, single-buffer layout, and H VI-register families before another hardware upload.

## Key Docs

- `docs/morning_handoff_20260509.md`
- `docs/tnd480i_next_hardware_queue.md`
- `docs/decomp_480i_findings.md`
- `docs/patch_site_audit.md`
- `docs/sc64_setup_notes.md`

## Local Artifact Layout

Put ROMs and generated candidates here, untracked:

- `artifacts/roms/`
- `artifacts/generated/`
- `artifacts/tmp/`

Expected source ROMs for current scripts:

- `BASELINE_TND64_Expanded_direct_from_stock.z64`
- `BASELINE_GE_480i_direct_from_stock.z64`
- `TND64_enh480i_core_no_menu_pigz.z64`

## Build Examples

Run from the repo root, pointing at local untracked ROMs:

```powershell
$py = 'C:\Users\codex\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py scripts\build_tnd480i_candidate.py `
  --base-rom artifacts\roms\TND64_enh480i_core_no_menu_pigz.z64 `
  --ge480i-rom artifacts\roms\BASELINE_GE_480i_direct_from_stock.z64 `
  --variant direct_only `
  --direct-profile split8030_8076_all_dim0 `
  --out-rom artifacts\generated\TND64_480i_split8030_8076_all_dim0_core_no_menu.z64 `
  --report reports\tnd480i_split8030_8076_all_dim0_core_no_menu_report.json
```

Patch artifact from the clean expanded TND baseline:

```powershell
& $py scripts\make_ips_patch.py `
  artifacts\roms\BASELINE_TND64_Expanded_direct_from_stock.z64 `
  artifacts\generated\TND64_480i_split8030_8076_all_dim0_core_no_menu.z64 `
  artifacts\generated\TND6480i_split8030_8076_all_dim0_from_baseline_tnd.ips `
  --manifest reports\tnd6480i_split8030_8076_all_dim0_ips_manifest.json
```

SC64 debug build:

```powershell
& $py scripts\build_sc64_isv_instrumented.py `
  --base-rom artifacts\generated\TND64_480i_single8076_all_dim0_core_no_menu.z64 `
  --out-rom artifacts\generated\TND64_480i_single8076_all_dim0_core_no_menu_sc64isv_hvionly_lowcave.z64 `
  --report reports\tnd480i_single8076_all_dim0_core_no_menu_sc64isv_hvionly_lowcave_report.json `
  --hooks HVI1
```

## Hardware Rule

Only upload after GV-USB2 visibly shows the SC64 menu, EverDrive menu, or another known-good live video state. For this confirmed candidate, SC64 `upload --direct` plus a Kasa power cycle was required to launch from the menu.
