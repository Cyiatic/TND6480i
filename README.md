# TND6480i

Tomorrow Never Dies 64 480i investigation workspace.

This repo tracks the reproducible patch/build scripts, notes, hardware queue, and diagnostic reports. It intentionally does **not** track GoldenEye/TND ROM images, generated candidate ROMs, save files, or binary patch blobs.

## Current Status

- SC64 is working on `COM4` when connected.
- The capture path can see the SC64 menu; see `diagnostics/captures/capture_sc64_menu_before_repo_migration_20260509.png`.
- The most recent blind visual candidate, `TND64_480i_single8076_all_core_no_menu.z64`, booted far enough for a user test but did not visibly render at 480i. Decomp follow-up found it still left the direct gameplay dimension words at `320x240`/`440x330`.
- New dim-aware visual candidates exist locally. The primary one is `artifacts/generated/TND64_480i_single8076_all_dims_core_no_menu.z64` with MD5 `8f4c7fdf524ec1c7f4fc63223a8b386c` and N64 CRC `CDBE2120 73E89F69`; it survived Gopher64 input smoke and ares process smoke. It has not been uploaded to hardware.
- Matching low-cave SC64 HVI-only debug builds now exist for the dim-aware candidates. The primary one is `artifacts/generated/TND64_480i_single8076_all_dims_core_no_menu_sc64isv_hvionly_lowcave.z64` with MD5 `05c4e67a8b293eb10208ff396afbffb2` and N64 CRC `C5E24FCF 6BB1D73D`; it survived Gopher64 and printed repeated `TND:HVI1` markers.
- The first SC64 debug candidate had a real-hardware runtime-address bug in its trampolines. Fixed debug builds now use the ROM load mapping `0x1000 -> 0x80000400`.
- Corrected entry-time ISV logging still black-screened on known-good baseline TND, so entry hooks are no longer the next path.
- The first no-entry baseline ISV control also black-screened, but it was found to have a `DFB1` hook bug that skipped original framebuffer-global setup. That build is superseded.
- A later HVI-only baseline control still black-screened when its logger lived at ROM `0x331E0`; that high cave may not be resident in RDRAM on hardware. The current diagnostics use a lower early-code cave at `0x3CB0`.
- Next useful step is validating the low-cave HVI-only SC64/IS-Viewer baseline control on real hardware before another 480i candidate test.

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
  --direct-profile single8076_all_nodims `
  --out-rom artifacts\generated\TND64_480i_single8076_all_core_no_menu.z64 `
  --report reports\tnd480i_single8076_all_core_no_menu_report.json
```

SC64 debug build:

```powershell
& $py scripts\build_sc64_isv_instrumented.py `
  --base-rom artifacts\generated\TND64_480i_single8076_all_dims_core_no_menu.z64 `
  --out-rom artifacts\generated\TND64_480i_single8076_all_dims_core_no_menu_sc64isv_hvionly_lowcave.z64 `
  --report reports\tnd480i_single8076_all_dims_core_no_menu_sc64isv_hvionly_lowcave_report.json `
  --hooks HVI1
```

## Hardware Rule

Only upload after GV-USB2 visibly shows the SC64 menu, EverDrive menu, or another known-good live video state. Prefer normal SC64 `upload` over `--direct` for the next attempt.
