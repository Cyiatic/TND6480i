# TND64 480i Morning Handoff

Date: 2026-05-09

## Current State

- No ROM was uploaded after the hardware path became ambiguous.
- Passive GV-USB2 capture still shows flat blue: `parallel_diag/capture_before_morning_handoff_20260509.png`.
- Do not upload or queue another ROM until a physical reset/power-cycle brings back the SC64 menu, EverDrive menu, or another known-good live video state.
- Patch audit is written to `parallel_diag/patch_site_audit.md`.

## What Changed Overnight

- Added profile entries to `build_tnd480i_candidate.py` for single-buffer H-origin variants and `split8030_8076_all_nodims`.
- Built new full-origin candidate ROMs:

| ROM | MD5 | N64 CRC |
|---|---|---|
| `TND64_480i_single8076_mem_fg_h_origin_core_no_menu.z64` | `913e7ba3cff9a9e904fdc9dd0adef3f9` | `461F9710 4BA15C2E` |
| `TND64_480i_single8076_mem_fg_h_origin_width_core_no_menu.z64` | `abe8ece07e0fc48000bd058c6ebd2c8a` | `3BDE9710 3B526C17` |
| `TND64_480i_single8076_mem_fg_h_origin_scale_core_no_menu.z64` | `c8e04cc802ff804376199fa9793f6acf` | `3E9EA710 19BEFF21` |
| `TND64_480i_single8076_all_core_no_menu.z64` | `3c6306b06ad9d52121ccc6817038a525` | `C35E1F10 C9208D74` |
| `TND64_480i_split8030_8076_all_core_no_menu.z64` | `6464d1b85aa7fc60d5a6fbf36fa71bf7` | `257D2E42 BCCC76EB` |

- Built a full-origin SC64 IS-Viewer diagnostic:

| ROM | MD5 | N64 CRC | Expected markers |
|---|---|---|---|
| `TND64_480i_single8076_all_core_no_menu_sc64isv_entry.z64` | `76071b20801ad798fa47233e95daf27f` | `5BC25FC8 8378A8B1` | `TND:ENTR`, `TND:BCLR`, `TND:DFB1`, `TND:HVI1` |

## Emulator Checks

- All five new uninstrumented variants opened a Gopher64 main window and survived 30 seconds.
- `TND64_480i_single8076_all_core_no_menu.z64` survived a 75 second Gopher64 Start/A input smoke with 156 key taps.
- `TND64_480i_split8030_8076_all_core_no_menu.z64` survived a 76 second Gopher64 Start/A input smoke with 158 key taps.
- Both full uninstrumented variants survived 30 second ares process smokes and stayed responsive.
- The full-origin SC64 entry diagnostic survived a 30 second Gopher64 visible smoke.

Reports:

- `parallel_diag/gopher64_screens/smoke_offline_origin_variants_report.json`
- `parallel_diag/gopher64_screens/smoke_offline_full_variants_input_report.json`
- `parallel_diag/ares_offline_full_variants_process_smoke.json`
- `parallel_diag/gopher64_screens/smoke_offline_single8076_all_sc64isv_entry_report.json`

## Why The Queue Changed

The user-tested table-only ROM (`TND64_enh480i_core_no_menu_pigz.z64`) has the compressed-main 480i tables but leaves the direct framebuffer and VI side-code words at TND stock values. That explains why it booted without rendering like the GE 480i patch.

The previous "best" single-buffer ROM applied GE width/vsync and scale words but skipped the GE origin/control-flow bypass at `0x19978/0x19980`. The new first pick applies that full GE H branch family while keeping the safer single-high framebuffer placement at `0x8076A000`.

## Next Hardware Step

First restore visible video. If capture stays flat blue, stop.

For one visual hardware test after the SC64 menu is visible:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\Codex\2026-05-06\files-mentioned-by-the-user-tnd64\TND64_480i_single8076_all_core_no_menu.z64'
```

For debug instead of pure visual testing:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\Codex\2026-05-06\files-mentioned-by-the-user-tnd64\TND64_480i_single8076_all_core_no_menu_sc64isv_entry.z64'
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' debug --isv 0x03FF0000
```

Avoid `--direct` for the next attempt. Use normal `upload` from a visibly working SC64 menu.
