# Hardware Session 2026-05-09

## State

- GV-USB2 confirmed the SC64 menu was visible.
- SC64 was detected on `COM4`.
- `sc64deployer info` showed `Bootloader -> Menu from SD card`, ROM writes enabled, and SD initialized before upload.

## Action

Uploaded the full single-buffer SC64 IS-Viewer entry diagnostic:

```text
artifacts/generated/TND64_480i_single8076_all_core_no_menu_sc64isv_entry.z64
MD5: 76071b20801ad798fa47233e95daf27f
N64 CRC: 5BC25FC8 8378A8B1
Expected markers: TND:ENTR, TND:BCLR, TND:DFB1, TND:HVI1
```

Command:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\GitHub\TND6480i\artifacts\generated\TND64_480i_single8076_all_core_no_menu_sc64isv_entry.z64'
```

SC64 reported:

```text
Boot mode set to [Bootloader -> ROM]
Save type set to [None]
```

## Result

- No physical reset occurred during the three-minute listener window.
- The console remained at the SC64 menu.
- The debug listener repeatedly started and stopped because no uploaded ROM was running yet.
- No `TND:*` markers were observed.

## Follow-up Reset

The user later pressed reset while the first debug ROM was queued. Capture changed to flat blue, and SC64 still reported `Bootloader -> ROM`.

Listener output:

```text
[IS-Viewer 64]: Listening on ROM offset [0x03FF0000]
[Debug]: Started
[IS-Viewer 64]: Stopped listening
[Debug]: Stopped
```

Direct dump of `0x03FF0000` showed only `0x5A` fill bytes and no `TND:*` marker. This did not prove the candidate reached or missed entry, because the debug trampoline was later found to have a real-hardware runtime-address bug.

The SC64 state was reset over USB afterward so the next physical power cycle should return to the menu:

```text
Boot mode: Bootloader -> Menu from SD card
```

## Runtime Fix

The N64 header PC is `0x80000400`, so ROM offset `0x1000` executes at `0x80000400`. The first SC64 debug instrumentation used `0x80000000 + rom_offset`, which was `0xC00` too high on real hardware. That likely explains the flat blue screen and missing `TND:ENTR` marker from the first debug ROM.

`scripts/build_sc64_isv_instrumented.py` now maps:

```text
runtime_address = 0x80000400 + (rom_offset - 0x1000)
```

Corrected entry-debug candidates:

| ROM | MD5 | N64 CRC | Emulator smoke |
|---|---|---|---|
| `artifacts/generated/BASELINE_TND64_Expanded_sc64isv_entry_runtimefix.z64` | `72f86a8a04e311d42b1aa92c6b83c447` | `6A4A700D 70F582D9` | Gopher64 25s survived |
| `artifacts/generated/TND64_480i_single8076_all_core_no_menu_sc64isv_entry_runtimefix.z64` | `908e47837ffab866e8b0a5a721a22d9b` | `5BC5B7C8 E9315FF5` | Gopher64 25s survived |

## Corrected Baseline Entry-Debug Hardware Result

After a clean SC64 menu power cycle, the corrected baseline entry-debug ROM was uploaded:

```text
artifacts/generated/BASELINE_TND64_Expanded_sc64isv_entry_runtimefix.z64
```

The user reset the N64. The console left the menu into black video, the debug listener never stayed attached, and the `0x03FF0000` ISV buffer still contained only `0x5A` fill bytes. That means entry-time ISV writes are still not a safe hardware diagnostic, even with the runtime address mapping fixed. Do not use entry-debug builds as the next hardware step.

SC64 was reset over USB afterward:

```text
Boot mode: Bootloader -> Menu from SD card
```

The console still needs a physical power cycle to return visible video.

## No-Entry Debug Builds

Built no-entry, runtime-fixed debug controls that only log later breadcrumbs from safer game-init paths:

| ROM | MD5 | N64 CRC | Expected markers | Emulator smoke |
|---|---|---|---|---|
| `artifacts/generated/BASELINE_TND64_Expanded_sc64isv_noentry_runtimefix.z64` | `484ac2cdaf535e56935efda0015f519f` | `5146CF58 370EE12D` | `TND:BCLR`, `TND:DFB1`, `TND:HVI1` | Gopher64 25s survived |
| `artifacts/generated/TND64_480i_single8076_all_core_no_menu_sc64isv_noentry_runtimefix.z64` | `0c6c3662173be66c0ccc1a19010abfd0` | `C3C81044 B73D1559` | `TND:BCLR`, `TND:DFB1`, `TND:HVI1` | Gopher64 25s survived |

## No-Entry Debug Hardware Result

After a clean SC64 menu state, the no-entry baseline control was uploaded:

```text
artifacts/generated/BASELINE_TND64_Expanded_sc64isv_noentry_runtimefix.z64
```

The console entered black video after reset. `sc64deployer debug --isv 0x03FF0000 --no-writeback` repeatedly started and stopped, never stayed attached, and a direct dump of `0x03FF0000` still contained only `0x5A` fill bytes. The post-test capture was flat black.

This result should not be used as proof that late ISV logging itself is impossible. A review immediately afterward found a bug in the `DFB1` hook: it overwrote the original framebuffer-global setup block and skipped the fb0 store / fb1 pointer calculation. That can black-screen a known-good baseline by itself.

SC64 was reset over USB afterward:

```text
Boot mode: Bootloader -> Menu from SD card
```

The capture remained flat black until the console receives a physical reset/power cycle.

## Corrected No-Entry Debug Builds

`scripts/build_sc64_isv_instrumented.py` now supports `--hooks` and routes the `DFB1` hook through a trampoline that replays the original framebuffer-global stores before logging.

| ROM | MD5 | N64 CRC | Expected markers | Emulator smoke |
|---|---|---|---|---|
| `artifacts/generated/BASELINE_TND64_Expanded_sc64isv_hvionly_runtimefix.z64` | `3da0d7373a5c5feac35d36a1a6b41493` | `5ABBA557 BACFDFFA` | `TND:HVI1` | Gopher64 25s survived |
| `artifacts/generated/BASELINE_TND64_Expanded_sc64isv_noentry_v2_runtimefix.z64` | `2d1f9bd38e684b98d199b34da3edbbcc` | `B5D098AD D2A048D6` | `TND:BCLR`, `TND:DFB1`, `TND:HVI1` | Gopher64 25s survived |
| `artifacts/generated/TND64_480i_single8076_all_core_no_menu_sc64isv_hvionly_runtimefix.z64` | `d2be3ae28d62c20d83e37bb9d1c9a724` | `C323C56F 529E9D3E` | `TND:HVI1` | Gopher64 25s survived |

## HVI-Only High-Cave Hardware Result

After the SC64 menu was visibly restored, the HVI-only baseline control was uploaded:

```text
artifacts/generated/BASELINE_TND64_Expanded_sc64isv_hvionly_runtimefix.z64
```

After reset, the console entered flat black video. The ISV listener never stayed attached, and dumping `0x03FF0000` still showed only `0x5A` fill bytes. SC64 was reset over USB back to:

```text
Boot mode: Bootloader -> Menu from SD card
```

This test strongly suggests a remaining diagnostic problem rather than a TND 480i problem. The HVI-only build left framebuffer setup untouched, so the likely issue is that the logger/trampoline cave at ROM `0x331E0` is not resident in RDRAM when early boot/video code calls it on real hardware.

## Low-Cave Diagnostic Builds

The diagnostic script now places the logger and trampolines in early padding at ROM `0x3CB0-0x3D20`, near known-loaded code. It also supports `--transport isv`, `--transport aux`, and `--transport none`.

| ROM | MD5 | N64 CRC | Transport | Expected markers | Emulator smoke |
|---|---|---|---|---|---|
| `artifacts/generated/BASELINE_TND64_Expanded_hvijump_lowcave.z64` | `e12d5f83eadd9ad4ae3f5427c3648e02` | `E21F057C 49DC630F` | none | none | Gopher64 25s survived |
| `artifacts/generated/BASELINE_TND64_Expanded_sc64isv_hvionly_lowcave.z64` | `efc8c7caaa898e421f82eb42b2d62edb` | `5AB52A0F BAB5C1D8` | ISV | `TND:HVI1` | Gopher64 25s survived |
| `artifacts/generated/BASELINE_TND64_Expanded_sc64isv_noentry_v3_lowcave.z64` | `f33cf07e6b97a69c95f148e3ac68ae8a` | `B5D59353 47CD57E8` | ISV | `TND:BCLR`, `TND:DFB1`, `TND:HVI1` | Gopher64 25s survived |
| `artifacts/generated/TND64_480i_single8076_all_core_no_menu_sc64isv_hvionly_lowcave.z64` | `d324a80841416d57c33e64c17923be03` | `C32248EF F42057CC` | ISV | `TND:HVI1` | Gopher64 25s survived |
| `artifacts/generated/BASELINE_TND64_Expanded_sc64aux_hvionly_lowcave.z64` | `5a9f649b8a4a51d5aea8815703bc6fb6` | `E89798F4 07CC0928` | AUX | `HVI1` word via AUX | Gopher64 panicked in its SC64 cart path |

## Offline Decomp Follow-up

The user-tested no-dims single-all visual ROM booted far enough to inspect Bond's hand but did not visibly render at 480i. A decomp pass against local `007-decomp` explains why that could happen: gameplay still passes stock direct dimensions through `viSetXY`/`viSetBuf`, and the no-dims candidate left ROM offsets `0x4F354` and `0x4F35C` at `0x014000F0` (`320x240`) and `0x01B8014A` (`440x330`).

New visual candidates now include direct `640x480` dimension words:

| ROM | MD5 | N64 CRC | Profile | Emulator smoke |
|---|---|---|---|---|
| `artifacts/generated/TND64_480i_single8076_all_dims_core_no_menu.z64` | `8f4c7fdf524ec1c7f4fc63223a8b386c` | `CDBE2120 73E89F69` | `single8076_all_dims` | Gopher64 80s input survived; ares 30s survived |
| `artifacts/generated/TND64_480i_split8030_8076_all_dims_core_no_menu.z64` | `cce443d766bd681a511f7d18bb95b657` | `278D2E7E C311ADE7` | `split8030_8076_all_dims` | Gopher64 80s input survived; ares 30s survived |

No hardware upload was performed for these dim-aware candidates during this offline follow-up.

Matching low-cave HVI-only debug builds:

| ROM | MD5 | N64 CRC | Expected markers | Emulator smoke |
|---|---|---|---|---|
| `artifacts/generated/TND64_480i_single8076_all_dims_core_no_menu_sc64isv_hvionly_lowcave.z64` | `05c4e67a8b293eb10208ff396afbffb2` | `C5E24FCF 6BB1D73D` | `TND:HVI1` | Gopher64 25s survived; 740 `TND:HVI1` markers |
| `artifacts/generated/TND64_480i_split8030_8076_all_dims_core_no_menu_sc64isv_hvionly_lowcave.z64` | `1d7399907d353fe12266f9120541b221` | `37FE4249 55E07F56` | `TND:HVI1` | Gopher64 25s survived; 755 `TND:HVI1` markers |

## Next Step

After the N64 is physically reset/power-cycled and the SC64 menu is visible again, test the low-cave HVI-only baseline control first:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\GitHub\TND6480i\artifacts\generated\BASELINE_TND64_Expanded_sc64isv_hvionly_lowcave.z64'
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' debug --isv 0x03FF0000 --no-writeback
```

Then press the real N64 reset button once. If `TND:HVI1` appears on the known-good baseline, the debug channel is validated and the corrected v3 all-hook baseline can be tested next. Only after that should the low-cave HVI-only 480i debug ROM be used.

If we want the lowest-risk branch before any debug writes, upload `BASELINE_TND64_Expanded_hvijump_lowcave.z64` and verify visually that baseline TND still boots. That proves the low-cave trampoline mechanics before involving ISV.
