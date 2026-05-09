# TND6480i

Tomorrow Never Dies 64 480i investigation workspace.

This repo tracks the reproducible patch/build scripts, notes, hardware queue, and diagnostic reports. It intentionally does **not** track GoldenEye/TND ROM images, generated candidate ROMs, save files, or binary patch blobs.

## Current Status

- SC64 is working on `COM4` when connected.
- The capture path can see the SC64 menu; see `diagnostics/captures/capture_sc64_menu_before_repo_migration_20260509.png`.
- The most recent blind visual candidate, `TND64_480i_single8076_all_core_no_menu.z64`, did not work on hardware per user test.
- Next useful step is an instrumented SC64/IS-Viewer run, not another blind visual candidate.

## Key Docs

- `docs/morning_handoff_20260509.md`
- `docs/tnd480i_next_hardware_queue.md`
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
  --base-rom artifacts\generated\TND64_480i_single8076_all_core_no_menu.z64 `
  --out-rom artifacts\generated\TND64_480i_single8076_all_core_no_menu_sc64isv.z64 `
  --report reports\tnd480i_single8076_all_core_no_menu_sc64isv_report.json

& $py scripts\build_sc64_isv_entry_instrumented.py `
  --base-rom artifacts\generated\TND64_480i_single8076_all_core_no_menu_sc64isv.z64 `
  --out-rom artifacts\generated\TND64_480i_single8076_all_core_no_menu_sc64isv_entry.z64 `
  --report reports\tnd480i_single8076_all_core_no_menu_sc64isv_entry_report.json
```

## Hardware Rule

Only upload after GV-USB2 visibly shows the SC64 menu, EverDrive menu, or another known-good live video state. Prefer normal SC64 `upload` over `--direct` for the next attempt.
