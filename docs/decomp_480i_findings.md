# TND64 480i Decomp Findings

Date: 2026-05-09

Source context: local GoldenEye decomp checkout at `C:\Users\codex\Documents\Codex\2026-05-06\files-mentioned-by-the-user-tnd64\parallel_diag\goldeneye_decomp_007\007-master`.

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

Hardware follow-up changed the conclusion again: the direct dimension words are necessary to solve the aliasing symptom eventually, but they are unsafe to patch first, and the combined F/G/H VI-side word family is also not real-hardware safe as a group. `FGH only` rendered in Gopher64, then black-screened on real N64 through 60 seconds. Split F/G/H into smaller probes before trying another 480i payload.

The smaller `F only`, `G only`, `FG only`, `H only`, `H origin only`, `H width only`, and `H scale only` probes all rendered in Gopher64 80 second visual/input smokes. Hardware then black-screened `H only` through 60 seconds, so the culprit is inside the H VI-register family. `H origin only` produced unstable/noisy video on hardware, `H width only` produced visible but severely corrupted output, and `H scale only` stayed pure black through 60 seconds.

## H Offset Mapping After Hardware Sub-Probes

The H offsets map into libultra `__osViSwapContext`, not a TND-specific gameplay function. Disassembly showed that stock GoldenEye and the TND base ROM are byte-identical at the H offsets before patching, so the GE 480i words are not landing in the wrong function.

The GE 480i changes at these offsets alter the low-level VI register handoff:

| Offset | GE 480i intent observed in disassembly |
|---:|---|
| `0x19978` / `0x19980` / `0x19984` | bypass part of the stock origin/fade/repeat-line path |
| `0x199B4` | double the VI width value before writing `VI_WIDTH_REG` |
| `0x199D0` | keep the paired sync write using the still-live `A440` base register |
| `0x19A24` / `0x19A60` / `0x19A64` | move the `y.scale` load earlier, write through the existing VI base, then halve the scale before writing `VI_Y_SCALE_REG` |

The hardware results mean these changes are not safe as isolated knobs. The next candidate should be derived as a coherent VI/mode/framebuffer patch: mode table fields, framebuffer size/location, direct gameplay dimensions, and the libultra 480i behavior need to agree before another H-family hardware upload.

Fallback double-buffer full-dims candidate:

```text
artifacts/generated/TND64_480i_split8030_8076_all_dims_core_no_menu.z64
Profile: split8030_8076_all_dims
MD5: cce443d766bd681a511f7d18bb95b657
N64 CRC: 278D2E7E C311ADE7
```

The full-dims candidates survived process/input smokes but should be treated as suspicious because visual capture can still be black.

## Split8030 Dim0 Resolution

The successful branch keeps the coherent VI/framebuffer package but narrows the direct dimension patch to the first word:

| ROM | Profile | MD5 | N64 CRC | Result |
|---|---|---|---|---|
| `artifacts/generated/TND64_480i_split8030_8076_all_dim0_core_no_menu.z64` | `split8030_8076_all_dim0` | `4fd6d3b38b50c2ec0a1bdd110598516c` | `25FD2E62 AF703620` | Gopher64 rendered; real N64 booted through at least 180s of intro/logo output |
| `artifacts/generated/TND64_480i_split8030_8076_all_dim1_core_no_menu.z64` | `split8030_8076_all_dim1` | `c636ff45bfa1147ee72c44f1cc685679` | `258D2E7E 8DDB244B` | Gopher64 black; not uploaded |

Conclusion: in this split-buffer layout, `0x4F354 -> 0x028001E0` is compatible with real hardware when paired with the split `0x80300000`/`0x8076A000` framebuffer setup and the full F/G/H VI-side family. `0x4F35C -> 0x028001E0` remains unsafe and should stay stock for now.

## 2026-05-10 Title/Gunbarrel Follow-up

The user-tested `split8030_8076_all_dim0` branch boots but still does not prove true 480i in the gunbarrel or Bazaar gameplay. Adding the GE gameplay viewport constants (`0xBB730` family) is valid by direct ROM-word comparison, but it did not fix the hardware cadence by itself.

Broad front/title transplants were rejected. `split8030_8076_all_dim0_frontgameplay480i` and the smaller front-resolution variants reached emulator smoke tests, but real capture showed severe striped/field-gap output on title/cast screens. The unsafe part is not only the obvious front `viSetXY` constants at `0x4D42C/0x4D434/0x4DAE0...`; those need a coherent title/front memory and layout package.

The local GE decomp also clarified two important offset traps:

- Same-offset comments for the `0xBB730` gameplay viewport family in the local decomp do not match the actual GE stock ROM words. Treat them as version/context collisions, not as proof the viewport patches are wrong.
- `0x4F354/0x4F35C` are TND-expanded-hack direct dimension words. They are not portable GE stock-to-GE 480i sites, because GE stock has unrelated words there.

The best emulator-only probe from this pass is:

```text
artifacts/generated/TND64_480i_split8030_8076_all_dim0_gameplay480i_reserve58000_core_no_menu.z64
MD5: 23565d7ca11067e2f2d9dc0d6b82c718
N64 CRC: 25FDDDFA 9AF08FFB
Patch: artifacts/generated/TND6480i_reserve58000_from_baseline_tnd.ips
```

It keeps the split8030 framebuffer package, the dim0 direct dimension word, and the gameplay viewport constants. It adds a TND-specific title allocation/reserve experiment:

- `0x3A38C/0x3A390`: title allocation immediate set to `0x96040` as in GE 480i.
- `0x3D934/0x3D938` and `0x3D950/0x3D958`: intro reserve set to `0x58000`, not GE 480i's `0x86600`.

Reserve sweep result in Gopher64:

| Reserve | 95s no-input result |
|---:|---|
| stock / alloc-only | normal title credits |
| `0x50000` | normal title credits |
| `0x54000` | normal title credits |
| `0x58000` | normal title credits; input smoke reaches watch/gameplay |
| `0x5C000` | loses visible title frame |
| `0x60000` | top-line corruption |
| `0x70000+` | stuck/noisy gunbarrel/title output |

This makes `0x58000` the current highest emulator-clean reserve candidate, but it has not been uploaded to hardware yet.

## 2026-05-10 Hardware Result and Viewport Split

The `reserve58000` candidate was uploaded to SC64 and tested on real N64. It booted and made clear progress: in-game Bazaar output entered a higher-resolution-looking path. It was not acceptable:

- Save slots 1, 3, and 4 froze at selection; slot 2 consistently worked.
- The gunbarrel still behaved stock-like instead of GE 480i-like.
- Gameplay was badly composed: the scene was vertically split/offset with large blue regions and field-like artifacts.
- Watch/report text was scaled or positioned incorrectly compared with the GE 480i watch reference.

The broad `I_gameplay_viewport_480i` group is therefore too large for TND as a same-offset transplant. It now has smaller subgroups in `scripts/build_tnd480i_candidate.py`:

| Group | Purpose | Emulator result |
|---|---|---|
| `I_gameplay_xy_480i` | Only `getWidth320or440()` and `getHeight330or240()` returns | Best current candidate; watch text is much saner in Gopher64 |
| `I_gameplay_view_width_480i` | Viewport width/ULX returns | Reintroduces badly cropped/split gameplay in Gopher64 |
| `I_gameplay_view_height_480i` | Viewport height returns | Stretches the watch/UI vertically in Gopher64 |
| `I_gameplay_fullscreen_view_480i` | Minimal fullscreen viewport add-back | Boots and reaches gameplay, but still looks vertically suspect |

Copying the `menu_only` compressed-main ranges (`0x9C3C-0x9D24`, `0xA240-0xA264`) into the current base overflowed the existing 1172 stream slot:

```text
packed stream too large: 0x11BC8 > 0xFDA7
```

That makes pause/menu text a separate space-management task. The next real-hardware probe should not wait on that; it should test whether the clean XY-only build preserves the new in-game resolution signal without the full viewport corruption.

Current next probe:

```text
artifacts/generated/TND64_480i_gameplayxy480i_reserve58000_core_no_menu.z64
MD5: 20bd8fdd151d3a441179566b0420ad2f
N64 CRC: 25FDEE1E CC9FF7D3
Patch: artifacts/generated/TND6480i_gameplayxy480i_reserve58000_from_baseline_tnd.ips
Patch MD5: e48ba1b2c294336e9a9b0d0df31798c1
```

Hardware follow-up of that XY-only candidate showed the game/watch render in the upper-left quadrant of a black 480i canvas. That confirms the XY patch sets the output buffer/canvas size, but the current-player viewport remains stock-sized.

The next candidate is TND-specific rather than GE-table-specific:

```text
artifacts/generated/TND64_480i_gameplayxy_tndfullscreen480i_reserve58000_core_no_menu.z64
MD5: fd399bb396989f1543b1e72a31d0a5d5
N64 CRC: 25FDDBDC 7822901E
Patch: artifacts/generated/TND6480i_gameplayxy_tndfullscreen480i_reserve58000_from_baseline_tnd.ips
Patch MD5: ea15340466269f48ea4290c4990b5cae
```

It changes only the single-player viewport paths to width `640`, height `480`, and top `0`, leaving 2P/4P constants alone. Gopher64 reaches gameplay and fills the active area, but still shows top-edge corruption, so this is a controlled in-game viewport probe rather than a finished patch. It is not expected to fix the gunbarrel cadence; gunbarrel/front-title video still needs a separate path.

Hardware launch follow-up: this TND-specific fullscreen viewport candidate was uploaded to SC64 with EEPROM 4k save type and launched by Kasa power-cycle. GV-USB2 confirmed it is not stuck at the SC64 menu and moves through the classification/gunbarrel/title sequence. The startup probe contact sheet is `diagnostics/captures/contact_sheets/tndfullscreen_launch_state_probe_sheet_20260510.jpg`. Controller-side gameplay testing is still required before treating the viewport fix as validated.

Controller-side result: all four save slots now work, but the gunbarrel is still not 480i. The user-driven GV-USB2 recording `diagnostics/captures/videos/tndfullscreen_level_intro_ingame_probe_20260509_220851.mkv` shows the level-intro camera path and gameplay path behaving differently. Gameplay no longer sits only in the upper-left, but it is vertically incoherent: large blue regions and split world bands dominate the frame.

The local GoldenEye decomp points at the reason: `viSetXY` / `viSetBuf` and `viSetViewSize` / `viSetViewPosition` are separate. The bad hardware candidate forced several camera-mode viewport tops (`0xBBA00`, `0xBBA1C`, `0xBBA24`) to `0`, but the GoldenEye 480i patch does not change those camera top offsets. New emulator probes split the normal gameplay viewport from the camera/intro viewport:

| Probe | MD5 | Gopher64 result |
|---|---|---|
| `TND64_480i_gameplayxy_tnddefaultgeview480i_reserve58000_core_no_menu.z64` | `06900e77a3f821b3e6ed8ea67d336f8e` | Best next hardware probe: normal player viewport/watch fills correctly without touching camera-mode top offsets |
| `TND64_480i_gameplayxy_tndcamerageview480i_reserve58000_core_no_menu.z64` | `eb3c96678295148ed55d7f5d42a9693d` | Stays upper-left in the captured player/watch state |
| `TND64_480i_gameplayxy_tndgeview480i_reserve58000_core_no_menu.z64` | `c6f6cde7a7bb757c1647cdd17aca6d06` | Reintroduces the blue split/camera-path corruption |

Next real-hardware probe should be the default-view-only candidate. It is expected to leave level intro/gunbarrel unresolved while testing whether normal gameplay and pause/watch composition can be made sane at 480i.

Hardware follow-up: `TND64_480i_gameplayxy_tnddefaultgeview480i_reserve58000_core_no_menu.z64` booted and reached gameplay/demo, but still showed a large blue gameplay region with a narrow world band at the top. Removing the default top-offset change produced the next live hardware probe:

```text
artifacts/generated/TND64_480i_gameplayxy_tnddefaultwidthheight480i_reserve58000_core_no_menu.z64
MD5: a17be68fd0eeb2e88bfd2d316e4b40db
N64 CRC: 25FDE5A6 EAB65D42
Patch: artifacts/generated/TND6480i_gameplayxy_tnddefaultwidthheight480i_reserve58000_from_baseline_tnd.ips
Patch MD5: 1839e41e019e0c25db1f6321e0867f4a
```

It is currently loaded on SC64 for controller-side gameplay testing. The startup/cast capture is `diagnostics/captures/videos/widthheight_no_top_startup_probe_20260509_224418.mkv`; that recording did not auto-enter a level.

The gunbarrel cadence remains a separate front-path issue. The user noted that Bond's appearance does not slow down the gunbarrel the way the GE 480i patch does. Front-path split probes now exist for real-hardware cadence testing after the current gameplay probe is classified:

- `TND64_480i_frontxy_gameplayxy_tnddefaultwidthheight480i_reserve58000_core_no_menu.z64`
- `TND64_480i_frontbuf_gameplayxy_tnddefaultwidthheight480i_reserve58000_core_no_menu.z64`
- `TND64_480i_frontxybuf_gameplayxy_tnddefaultwidthheight480i_reserve58000_core_no_menu.z64`
- `TND64_480i_frontzbuf_gameplayxy_tnddefaultwidthheight480i_reserve58000_core_no_menu.z64`

## 2026-05-10 Overnight Title Blitter Rejection

The local decomp clarified that `sub_GAME_7F01B240` is a shared title/image blitter, not a gunbarrel-only path. It is used early enough to affect the Rare splash, so global row-loop or stride edits can break the entire front sequence before the gunbarrel appears.

The TND expanded ROM also does not use GE's original title RLE pointer. In `sub_GAME_7F008DE4`, TND changes the source pointer low half at ROM `0x3D94C` from `0x4D50` to `0xE120`, so the active title RLE source is ROM `0x2AE120`. Its header begins:

```text
0x2AE120: 01FC 01FB 01F7 0158 01B3 02FC ...
```

That means the first width/height pair is `508 x 507`; the earlier `764` stride assumption came from reading a different header-like pair, not the actual active RLE width.

Two hardware canaries rejected this path:

| ROM | Hardware result |
|---|---|
| `TND64_480i_title640draw_tndstride430_nogameplay_reserve58000_core_no_menu.z64` | Reached the Rare splash, then collapsed into a static narrow vertical-bar image for 180s. |
| `TND64_480i_tndrect508src430_gameplayxy_tnddefaultwidthheight480i_reserve58000_core_no_menu.z64` | Reached the Rare splash, then collapsed into a brighter/wider static vertical-bar image for 180s. |

Evidence:

- `diagnostics/captures/contact_sheets/title640draw430_nogameplay_noinput_20260510_sheet.jpg`
- `diagnostics/captures/contact_sheets/tndrect508src430_noinput_20260510_sheet.jpg`
- `reports/capture_cadence_analysis_title640draw430_nogameplay_noinput_20260510.json`
- `reports/capture_cadence_analysis_tndrect508src430_20260510.json`

Conclusion: do not upload any `K_rectloop_*` or `K_title_draw_*` title-blitter candidates first. Even the corrected source stride proves that the shared blitter's hardcoded loop geometry is coupled to TND's title asset/layout in a way that does not tolerate GE 480i row-count transplants. The gunbarrel fix needs to come from a higher-level title/front setup or a targeted dynamic blitter patch, not a global stride/row-loop edit.

## 2026-05-10 Tiny Front-Buffer Hardware Rejection

Two narrow GE 480i buffer-size transplants were tested from a confirmed SC64 menu and restored to the menu afterward:

| ROM | MD5 | N64 CRC | Hardware result |
|---|---|---|---|
| `TND64_480i_gunbufBE200_gameplayxy_tnddefaultwidthheight_reserve58000_core_no_menu.z64` | `3ae03142133f81bd8e9204f540ff6388` | `25FDE5AE B8400652` | Boots and loops title/gunbarrel/credits, but cadence remains stock-like. |
| `TND64_480i_frontbufsizes_gameplayxy_tnddefaultwidthheight_reserve58000_core_no_menu.z64` | `cd2c4a0fbea43316ebf93cd4ad950a10` | `25C2D9D8 C0DF02E5` | Boots and loops title/gunbarrel/credits, but cadence remains stock-like. |

The first candidate only changes the size passed to `initializeGunBarrelIntro` at `0x3FC90/0x3FC94` from `0x78000` to GE 480i's `0xBE200`, plus header CRC. The second also changes the adjacent front-state size at `0x40540/0x40544` from `0x6E000` to GE 480i's `0xB4200`.

Fair cadence comparison using the same high-red detector:

| Capture | White-to-red intervals |
|---|---|
| Known width/height branch | `4.704s`, `4.839s`, `4.805s` |
| `gunbufBE200` | `4.771s`, `4.771s`, `4.838s` |
| `frontbufsizes` | `4.705s`, `4.805s` |
| GE 480i reference | `7.908s` |

Evidence:

- `diagnostics/captures/videos/gunbufBE200_noinput_live_20260510.mkv`
- `diagnostics/captures/videos/frontbufsizes_noinput_startup_20260510.mkv`
- `diagnostics/captures/contact_sheets/gunbufBE200_noinput_live_20260510_sheet.jpg`
- `diagnostics/captures/contact_sheets/frontbufsizes_noinput_startup_20260510_sheet.jpg`
- `reports/capture_cadence_segments_compare_known_gunbuf_frontbufsizes_ge480i_20260510.json`

Conclusion: larger title/front allocation sizes alone do not produce the GE 480i slowdown. Do not retry the `0x86600` reserve versions without a separate emulator-visual reason; earlier reserve sweeps showed high reserves quickly make the title path noisy or stuck.

The more interesting static clue is in `video_related_8` around ROM `0x46B4-0x46F0`. GE 480i replaces the stock contiguous-framebuffer stride math with a `0x96000` stride from a dynamic base. The current split-buffer branch replaces that same region with `C_split_select_global`, selecting `cfb_16[g_ViBackIndex]` from the custom split framebuffer globals. That makes the GE 480i `0x46C8` group non-portable as a direct transplant: the next candidate needs a split-buffer-aware equivalent of GE 480i's framebuf/mode handoff, not a blind overwrite of the split selector.

## 2026-05-10 Pad-Origin Title Asset Follow-up

User hardware testing of the resized 640x430 asset branch found that it removed the save-slot freeze only when the file-select backdrop call was skipped, but it introduced an obvious second gunbarrel aperture and left the folder background black.

The decoded active TND title source is `440 x 299`. Stretching that source to `640 x 430` moves the source image's own aperture away from the Bond model aperture. The next hardware-loaded candidate therefore keeps the 640x430 RLE header/stride/row-loop path but pads the original 440x299 source at the origin of a 640x430 canvas instead of resizing it.

Current hardware-loaded ROM:

```text
artifacts/generated/TND64_480i_frontbuf_gunbarrel_padorigin_gameplayxy_tnddefaultwidthheight480i_virtualfb_reserve58000_core_no_menu.z64
MD5: 8595e4f1416fdca1bf96ad86c8907d6f
N64 CRC: 2FB6A3F7 556AA840
```

The S-video startup capture `diagnostics/captures/videos/frontbuf_padorigin_noskip_offupload_poweron_startup_20260510.mkv` confirms that the obvious second gunbarrel is gone at `frame_035s.png`, and the 150-second no-input capture did not lock. The unresolved question is whether restoring the file-select backdrop call reintroduces save-slot freezes on hardware.
