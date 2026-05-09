# TND64 480i Decomp Findings

Date: 2026-05-09

Source context: local GoldenEye decomp checkout at `C:\Users\codex\Documents\n64\007-decomp`.

## Why the No-Dims Candidate Was Suspicious

The user-tested `TND64_480i_single8076_all_core_no_menu.z64` included the single-high framebuffer placement and the GE 480i VI-side word family, but it did not patch the direct gameplay dimension constants at ROM offsets `0x4F354` and `0x4F35C`.

Those words remained:

| Offset | Old word | Meaning |
|---:|---:|---|
| `0x4F354` | `0x014000F0` | `320x240` |
| `0x4F35C` | `0x01B8014A` | `440x330` |

The GE 480i ROM uses `0x028001E0` at both sites, meaning `640x480`.

## Decomp Mapping

- `src/game/bondview.c` calls `viSetXY(getWidth320or440(), getHeight330or240())` and `viSetBuf(...)` for gameplay.
- `getWidth320or440()` returns either `SCREEN_WIDTH_320` or `SCREEN_WIDTH_440` in stock code.
- `getHeight330or240()` returns either `SCREEN_HEIGHT` or `SCREEN_HEIGHT_330` in stock code.
- `src/fr.c` then uses `g_ViBackData->bufx` and `g_ViBackData->bufy` when programming VI width, scale, and origin.

That matches the hardware symptom: the ROM can boot and show Bond's hand, but if gameplay still feeds `320x240` or `440x330` into the VI path, the image can remain visibly aliased instead of proving true 480i output.

## Resulting Candidates

Primary visual candidate:

```text
artifacts/generated/TND64_480i_single8076_all_dims_core_no_menu.z64
Profile: single8076_all_dims
MD5: 8f4c7fdf524ec1c7f4fc63223a8b386c
N64 CRC: CDBE2120 73E89F69
```

Binary sanity check against `TND64_480i_single8076_all_core_no_menu.z64`: only the N64 header CRC words and the two direct dimension words changed.

Fallback double-buffer candidate:

```text
artifacts/generated/TND64_480i_split8030_8076_all_dims_core_no_menu.z64
Profile: split8030_8076_all_dims
MD5: cce443d766bd681a511f7d18bb95b657
N64 CRC: 278D2E7E C311ADE7
```

Both survived the local Gopher64 input smoke and ares process smoke. Neither has been uploaded to hardware.
