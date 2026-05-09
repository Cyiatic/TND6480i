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

## Next Step

After the N64 is physically power-cycled and the SC64 menu is visible again, test the no-entry baseline debug control first:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' upload 'C:\Users\codex\Documents\GitHub\TND6480i\artifacts\generated\BASELINE_TND64_Expanded_sc64isv_noentry_runtimefix.z64'
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' debug --isv 0x03FF0000 --no-writeback
```

Then press the real N64 reset button once. If later markers appear on the known-good baseline, the debug channel is validated and the no-entry 480i debug candidate can be tested next.
