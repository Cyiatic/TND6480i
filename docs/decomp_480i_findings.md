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

Initial full-dims candidate:

```text
artifacts/generated/TND64_480i_single8076_all_dims_core_no_menu.z64
Profile: single8076_all_dims
MD5: 8f4c7fdf524ec1c7f4fc63223a8b386c
N64 CRC: CDBE2120 73E89F69
```

Binary sanity check against `TND64_480i_single8076_all_core_no_menu.z64`: only the N64 header CRC words and the two direct dimension words changed.

Visual capture follow-up changed the conclusion: the full-dims build stays black in Gopher64, while the old no-dims single-all build renders. One-word tests isolated the risk:

| ROM | Profile | MD5 | N64 CRC | Gopher64 80s visual capture |
|---|---|---|---|---|
| `artifacts/generated/TND64_480i_single8076_all_dim0_core_no_menu.z64` | `single8076_all_dim0` | `ad441669291605a3fd551b51c68bb195` | `CE5E1EF0 26DDA6CD` | renders; window mean luma `122.22`; ares 30s survived |
| `artifacts/generated/TND64_480i_single8076_all_dim1_core_no_menu.z64` | `single8076_all_dim1` | `66c3a0ef8116cfb6c0a52a48dc1a967e` | `CF3E1F20 E5FF8B59` | black; window mean luma `16.81`; ares 30s survived |

The first direct dimension word looked safer in emulator at this stage, but hardware later black-screened `single8076_all_dim0` through 60 seconds. That pushed the investigation toward smaller probes that isolate the direct dimension words from the framebuffer relocation and F/G/H VI-side patches.

| ROM | Profile | MD5 | N64 CRC | Gopher64 80s visual capture |
|---|---|---|---|---|
| `artifacts/generated/TND64_480i_dim0only_core_no_menu.z64` | `dim0_only` | `dfd10a81e5ad9c517382cb3f866696d9` | `C23D9942 3FB57C0D` | black; window mean luma `16.53` |
| `artifacts/generated/TND64_480i_dim1only_core_no_menu.z64` | `dim1_only` | `d909037053d29548ddf6fa11b8924207` | `C2BD98A2 B89F823D` | black; window mean luma `16.53` |
| `artifacts/generated/TND64_480i_fghonly_core_no_menu.z64` | `fg_h_only` | `852a811f1e71603e3b510866a834cb47` | `45AFEB49 BFF2CC66` | rendered; window mean luma `121.17` |

Current conclusion: the direct dimension words are necessary to solve the aliasing symptom eventually, but they are unsafe to patch first. `FGH only` is the next low-risk visual control because it keeps stock direct dimensions and stock framebuffer placement while applying the GE 480i F/G/H VI-side word family.

Fallback double-buffer full-dims candidate:

```text
artifacts/generated/TND64_480i_split8030_8076_all_dims_core_no_menu.z64
Profile: split8030_8076_all_dims
MD5: cce443d766bd681a511f7d18bb95b657
N64 CRC: 278D2E7E C311ADE7
```

The full-dims candidates survived process/input smokes but should be treated as suspicious because visual capture can still be black. The direct-dimension branch needs more decomp work before another hardware attempt.
