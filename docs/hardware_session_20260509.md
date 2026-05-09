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

## Next Step

The debug ROM is queued. Press the real N64 reset button once, then restart:

```powershell
& 'C:\Users\codex\Documents\n64\sc64deployer.exe' debug --isv 0x03FF0000 --no-writeback
```

If the ROM runs long enough, capture GV-USB2 frames at 2, 5, 10, 20, 40, and 60 seconds after reset.
