# TND64 480i Decomp Findings

Date: 2026-05-09

Source context: local GoldenEye decomp checkout at `C:\Users\codex\Documents\Codex\2026-05-06\files-mentioned-by-the-user-tnd64\parallel_diag\goldeneye_decomp_007\007-master`.

## 2026-05-16 Expansion Pak TLB Cache Correction

The earlier framebuffer safety model was wrong in an important way. It treated the low framebuffer at `0x80300000-0x80395FFF` as the most likely TLB/cache collision. The direct ROM startup code shows the risky overlap is instead the high framebuffer on 8 MB systems.

Relevant direct-ROM code:

| ROM offset | Stock/current instruction | Meaning |
|---:|---:|---|
| `0x241C` | `0x3C08802F` | `lui t0,0x802F` |
| `0x2420` | `0x25086000` | `addiu t0,t0,0x6000` |
| `0x2424-0x2430` | load/add/store via `0x8000050C` | add expansion-memory delta and store `g_tlbmanageTlbAllocatedBlock` |
| `0x24A8-0x24BC` | `osMemSize - 0x400000` | initializes the expansion-memory delta |

On a 4 MB console the page-cache base is about `0x802F6000`. On an 8 MB Expansion Pak console the delta is `0x00400000`, so the page-cache base becomes about `0x806F6000`. With 90 pages of `0x2000` bytes, the expected cache range is approximately `0x806F6000-0x807A9FFF`.

That overlaps the high 640x480x16 framebuffer used by the current working split layout:

```text
fb0: 0x80300000-0x80395FFF
fb1: 0x8076A000-0x807FFFFF
```

This better explains the level-specific failures reported by hardware testing: only levels or events that page enough data through the TLB cache would corrupt high framebuffer contents or the cache metadata.

Current tested canary:

```text
artifacts/generated/game_h460_top10_stock_dossier_tlb8060_current.z64
MD5: f449b66024efc95069f46990fa837e8d
N64 CRC: 84B77873 803478C8
```

It changes only the TLB cache base math:

```text
ROM 0x241C: 3C08802F -> 3C088020
ROM 0x2420: 25086000 -> 25080000
```

Expected 8 MB TLB cache range becomes `0x80600000-0x806B3FFF`, below `fb1`. The canary boots on real N64 and reaches no-input gameplay/demo after the PC reboot, but still shows top-band visual corruption. Treat it as a stability/playability canary, not a visual completion patch.

Rejected adjacent approach: moving `fb1` down to `0x8066A000` black-screened on real hardware. Continue by moving cache placement first, not framebuffer placement.

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

## 2026-05-10 Current Hardware Feedback

Latest controller-side testing narrows the remaining issues:

- In-game rendering is now broadly good; the visible gameplay problem is flicker rather than the previous top-rectangle/world-band failure.
- Level-select text is misaligned.
- Still needing focused fixes: gunbarrel cadence/composition, opening credits, menu scale/text/layout, intro cutscene/gameplay polish, and pause/watch text layout.

Implication: preserve the current gameplay viewport path while iterating. The next candidates should avoid broad front/title transplants that risk regressing gameplay and should split work into title/front fixes versus UI text/layout fixes.

After the user returned, `diagnostics/captures/current_state_user_back_20260510_1838.png` was clarified as an intentionally user-driven in-game state. Keep it as evidence for the remaining top/bottom gameplay flicker, but do not use it as a cold-boot/title timing sample.

The clean no-input timing reference for the current `gamefulltop0` fallback is now `diagnostics/captures/videos/gamefulltop0_neutral_start_recheck_20260510_1840.mkv`, with sheet `diagnostics/captures/contact_sheets/gamefulltop0_neutral_start_recheck_labeled_20260510_1840.jpg` and report `reports/capture_cadence/motion_gamefulltop0_neutral_recheck_20260510_1840.json`. That capture loops the title/credits path and confirms the gunbarrel remains stock/TND-like. Because the GE 480i ROM diff does not change the likely title state-machine timing region, the GE-style slowdown is more likely an emergent effect of the 480i render/VI/framebuffer path than a simple front-end timer constant.

## 2026-05-10 Mission Select Text Candidate

Built and uploaded a narrow level-select text alignment candidate from the current good gameplay baseline:

```text
artifacts/generated/TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_missiontext_reserve58000_core_no_menu.z64
MD5: c4d0c2b56ae5fab0617521cb0978147e
N64 CRC: CD679B28 2D5C5F47
```

This candidate only changes four GE 480i mission-select constructor words:

- `0x43148`: `+0x1D` -> `+0x2A`
- `0x43150`: `-0x1F` -> `-0x2D`
- `0x431E0`: `+0x1D` -> `+0x2A`
- `0x431E4`: `-0x1F` -> `-0x2D`

Gopher64 smoke survived 90 seconds with input and reached the watch/gameplay path. The ROM was uploaded through SC64 direct boot with EEPROM 4k and power-cycled by Kasa. Hardware capture after upload: `diagnostics/captures/after_missiontext_upload_boot_20260510.png`.

Hardware result: rejected. The user reported that level text alignment was worse, while the in-game viewport improvements and flicker were unchanged. Do not carry `J_mission_select_text_480i` into the next patch.

## 2026-05-10 Camera Intro Viewport Candidate

Built and uploaded a camera-only overlay from the previous physicalfb gameplay baseline, deliberately excluding the rejected mission-select text patch:

```text
artifacts/generated/TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfulltop0_reserve58000_core_no_menu.z64
MD5: aaf0f43f486c729311d38880994dc7af
N64 CRC: CD6798E0 24E50396
```

This candidate changes only six camera/intro viewport words:

- `0xBB89C`, `0xBB8B8`, `0xBB8C0`: force camera-mode viewport heights to `480`.
- `0xBBA00`, `0xBBA1C`, `0xBBA24`: force camera-mode viewport top offsets to `0`.

Gopher64 smoke survived 85 seconds with input and reached a clean full gameplay frame. The stock-height rollback overlay produced visible top corruption in Gopher64, so it should not be uploaded first. The combined camera height/top candidate was uploaded through SC64 direct boot with EEPROM 4k and power-cycled by Kasa. Hardware capture after upload: `diagnostics/captures/after_camfulltop0_upload_boot_20260510.png`.

Hardware result: rejected as a direction. The user reported that level text alignment was still bad, in-game retained the same improved viewport plus flicker, and the level intro moved more than it should while remaining confined to the smaller rectangle. Treat the top-zero camera offsets as harmful until there is a better cutscene-specific reason to revisit them.

Next uploaded probe:

```text
artifacts/generated/TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_reserve58000_core_no_menu.z64
MD5: 9eaf413cdb765a33cf164095f897fc14
N64 CRC: CD67980E 8DF351CC
```

This candidate changes only the three camera-mode viewport heights at `0xBB89C`, `0xBB8B8`, and `0xBB8C0` to `480`, deliberately restoring the prior camera top offsets. SC64 upload and Kasa power cycle completed; boot capture is `diagnostics/captures/after_camfullheight_upload_boot_20260510.png`.

Hardware result: promoted to best gameplay baseline so far. The user reported that in-game rendering looked better, with flicker now limited to the top and bottom of the image. Other sections still require more work.

To test whether the remaining top/bottom flicker comes from the non-camera `640x440` viewport centered at top `20`, a new probe was built from the `camfullheight` baseline:

```text
artifacts/generated/TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_reserve58000_core_no_menu.z64
MD5: 17d4ea3194d02d5ea121b1e42aa59469
N64 CRC: CD6799DE DAD61991
```

This candidate keeps the camera-height-only changes and only modifies the non-camera gameplay view:

- `0xBB91C`, `0xBB954`: non-camera default/fallback viewport height `440 -> 480`.
- `0xBBA80`: non-camera default viewport top `20 -> 0`.

Gopher64 smoke survived 85 seconds with input and reached the watch path (`reports/smoke/smoke_physicalfb_camfullheight_gamefulltop0_input_until52_20260510.json`). SC64 upload and Kasa power cycle completed; boot capture is `diagnostics/captures/after_gamefulltop0_upload_boot_20260510.png`.

Hardware result: promoted to the current best gameplay/pause baseline. The user verified the pause menu is good, and in-game appears slightly more stable than the prior `camfullheight` baseline. Leave this as the fallback while front/title/menu experiments continue.

Two isolated gunbarrel RLE workload probes were then generated from this baseline after adding workload padding controls to `scripts/build_tnd480i_gunbarrel_asset_candidate.py`:

- `TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_gunwork259f4_reserve58000_core_no_menu.z64`, MD5 `119710751ac49ec46e95949001fe3fd0`, N64 CRC `CD6790DE 0FA4B3BD`. This padded below the original 440x299 source to match the earlier GE-like stretched asset's encoded RLE length (`0x259F4`). Hardware booted and reached title/menu/demo paths, but produced obvious title/gunbarrel geometry/artifacting. Reject as-is.
- `TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_gunwork259f4right_reserve58000_core_no_menu.z64`, MD5 `ce7d9e8415b36c56d2d1585db418cb79`, N64 CRC `CD6790DE 0FA4B3BD`. This used the same workload target but padded the right-of-source strip instead. It still showed stray top-row garbage and a misframed gunbarrel on hardware. Reject as-is.

After those rejects, the SC64 was restored to the `gamefulltop0` baseline with EEPROM 4k direct boot. Confirmation captures: `diagnostics/captures/after_restore_gamefulltop0_wait5_20260510.png` and `diagnostics/captures/after_restore_gamefulltop0_wait15_20260510.png`.

A cleaner RLE workload candidate was then built by splitting existing zero-value RLE runs instead of changing decoded pixels:

```text
artifacts/generated/TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_gunsplit259f4_reserve58000_core_no_menu.z64
MD5: 3f70b554d8363112d1cc03e7cf53a62c
N64 CRC: CD6790DE 0FA4B3BD
```

This candidate keeps the decoded 640x430 pad-origin gunbarrel bitmap identical to the prior clean baseline, but inflates the encoded RLE stream from `0x1A672` to `0x259F4` by adding `22977` extra zero-run records (`decoded_pixels_modified: 0`). Gopher64 survived 85 seconds and reached the watch/gameplay path (`reports/smoke/smoke_gunsplit259f4_input_until52_20260510.json`). The ROM was uploaded to SC64 with EEPROM 4k and is currently the live console build.

Hardware captures:

- Startup spot checks: `diagnostics/captures/after_gunsplit259f4_upload_boot_20260510.png`, `diagnostics/captures/after_gunsplit259f4_wait5_20260510.png`, `diagnostics/captures/after_gunsplit259f4_wait15_20260510.png`.
- Controlled power-cycle video: `diagnostics/captures/videos/gunsplit259f4_powercycle_startup_20260510.mp4`.
- Contact sheet: `diagnostics/captures/contact_sheets/gunsplit259f4_powercycle_startup_20260510_sheet.jpg`.
- Motion cadence report: `reports/motion_cadence_gunsplit259f4_powercycle_20260510.json` measured about `6.608` updates/sec for the broad `28-45s` segment and `7.316` updates/sec for the later `35-52s` segment. This suggests the run-split idea can affect cadence, but the segment alignment needs user visual confirmation against the real gunbarrel.

Operational note: the disk filled while recording FFV1 captures. Large generated non-reference `.mkv` files under `diagnostics/captures/videos` were removed, preserving reports, still captures, contact sheets, ROMs, docs, and the reference/user clips. Future captures should use compressed H.264/MP4 unless lossless is specifically needed.

Follow-up emulator-only note: the gameplay-good baseline still has `direct render dimensions table 1` at stock `440x330` (`0x4F35C = 0x01B8014A`) while table 0 is `640x480`. Three one-word table-1 probes were generated from the physicalfb baseline:

- `physicalfb_dim1`: `0x4F35C = 0x028001E0`, MD5 `eaea60e5c6a33106ff7ed29600a77d37`.
- `physicalfb_dim1width`: `0x4F35C = 0x0280014A`, MD5 `b6cb6785708e8e911273fe3b906dd13b`.
- `physicalfb_dim1height`: `0x4F35C = 0x01B801E0`, MD5 `2b2ab3e7fa3fd3209315bc88de45ddef`.

All three survived Gopher64 smoke but remained on the TND logo after 85 seconds with input (`reports/smoke/smoke_physicalfb_dim1_input_until52_20260510.json` and `reports/smoke/smoke_physicalfb_dim1_split_input_until52_20260510.json`). Do not upload these table-1 static patches without a more targeted runtime or callsite-specific guard.

Exact GE 480i title asset follow-up: the GE 480i gunbarrel RLE at `0x2A4D50` was appended exactly to the `gamefulltop0` baseline and redirected through the existing 640x430 title path:

```text
artifacts/generated/TND64_480i_gamefulltop0_ge480i_titleasset_exact_20260510.z64
MD5: c48310588beb3ac33373ca378c27e902
N64 CRC: CD6673DE C4A34147
```

Hardware result: reject as a gameplay-safe baseline. It booted and reached the title path, but the live GV-USB2 state after return showed persistent gameplay corruption: a left-side world view, large grayscale/right-side residue, top color bars, and a blue bottom band. The capture evidence is `diagnostics/captures/current_state_after_return_20260510.png` and `diagnostics/captures/contact_sheets/current_live_ingame_after_return_20260510_sheet.jpg`. The console was restored to `gamefulltop0` afterward; confirmation capture is `diagnostics/captures/after_restore_gamefulltop0_return_wait8_20260510.png`.

The exact GE asset result means the visible gunbarrel problem is not solved by copying the source RLE bitmap alone. It also suggests the title decode/draw path can leave persistent display state damage, so future title-asset candidates should be treated as hardware-risky until they pass an emulator smoke and a short hardware startup/gameplay capture.

Backdrop transform follow-up: a targeted matrix of `insert_sight_backdrop_eye_intro` patches was generated with `scripts/build_tnd480i_backdrop_matrix.py`. The tested knobs were early return, X/Y scale, and the X/Y translate addends at ROM offsets `0x3C6CC`, `0x3C6DC`, `0x3C734/0x3C744`, and `0x3C738/0x3C740`.

Gopher64 result: reject the family for now. All variants survived 36 seconds, but the labeled sheet `diagnostics/captures/contact_sheets/backdrop_matrix_gopher36_20260510.jpg` showed the exact-asset baseline cleaner than the backdrop skip/scale/translate variants. Several variants exposed two white circles in the sampled gunbarrel phase, so there is no hardware-worthy improvement. Report: `reports/smoke/smoke_ge480i_titleasset_backdrop_matrix_36s_20260510.json`.

Front z-buffer follow-up: a two-word `frontzbuf` overlay was tested from the current `gamefulltop0` fallback to see whether matching GE's front-title z-buffer dimensions would reduce the title/gunbarrel mismatch:

```text
artifacts/generated/TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_frontzbuf_reserve58000_core_no_menu.z64
```

It changes only:

- `0x4D42C`: `0x240501B8 -> 0x24050280`
- `0x4D434`: `0x2406014A -> 0x240601E0`

Hardware result: reject. The ROM booted and looped through logos/gunbarrel/credits, but the front/title path had heavy horizontal white striping and the motion cadence did not improve toward GE 480i. Evidence:

- Startup video: `diagnostics/captures/videos/frontzbuf_retest_powercycle_20260510.mkv`
- Contact sheet: `diagnostics/captures/contact_sheets/frontzbuf_retest_powercycle_labeled_20260510.jpg`
- Motion report: `reports/capture_cadence/motion_frontzbuf_retest_vs_refs_20260510.json`
- Restore confirmation after rejection: `diagnostics/captures/current/after_restore_gamefulltop0_after_frontzbuf_reject_wait8_20260510.png`

Do not carry `J_front_zbuffer_480i` into the current fallback.

## 2026-05-10 SC64 VI Diagnostic Note

`scripts/build_sc64_vidiag.py` was used to build a direct SC64 HVI diagnostic from the current `gamefulltop0` fallback:

```text
artifacts/generated/TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_sc64vidiag_hvi_20260510.z64
```

The ROM booted visually in Gopher64 and on hardware, but SC64 buffer dumps at the expected BlockRAM/data-buffer locations did not contain the expected diagnostic words. `0x05001000` and nearby candidate offsets read back zero, while `0x05000000` contained unrelated data. Conclusion: direct CPU stores to the SC64 data-buffer mapping are not a reliable telemetry path here, or the hook is not executing as assumed. Rework this around the SC64 DMA/USB path used by the GE decomp-style `usb.c` code before using it for VI register truth.

## 2026-05-10 Front/Menu Layout Split

The broad GE 480i front/title layout transplant was split into small groups in `scripts/build_tnd480i_candidate.py`:

- `J_front_layout_43a_480i`
- `J_front_layout_460_480i`
- `J_front_layout_float_480i`
- `J_front_layout_y_480i`
- `J_front_layout_4aaa_480i`
- `J_front_layout_gridstep_480i`

Short ROMs were generated from the current fallback (`fl43a`, `fl460`, `flflt`, `fly`, `fl4aaa`, `flgrid`, `fl43a460`, `flsafe`) and smoked with timed Gopher64 captures. All survived no-input startup, but the visual sheets did not show a clear front text/layout improvement. Input smokes also showed `flgrid` as a weak candidate, with noisy watch/menu behavior. Keep these offline unless a later hypothesis needs one specific cluster.

Evidence:

- `diagnostics/captures/contact_sheets/layout_subclusters_gopher_20260510.jpg`
- `diagnostics/captures/contact_sheets/layout_flsafe_input_gopher_20260510.jpg`
- `diagnostics/captures/contact_sheets/layout_individual_input_gopher_20260510.jpg`

## 2026-05-10 Front Text-Box Cluster

A very small front text-box probe was retested with short filenames:

```text
artifacts/generated/flbox.z64
source: artifacts/generated/TND64_480i_gamefulltop0_frontbox_cluster_safe_20260510.z64
```

It applies only five safe GE 480i full-ROM words:

- `0x3EC18`: `0x2408019B -> 0x2408024E`
- `0x3EC1C`: `0x240F0033 -> 0x240F004A`
- `0x3EC44`: `0x240A0075 -> 0x240A00AA`
- `0x3EC5C`: `0x24060033 -> 0x2406004A`
- `0x3EC78`: `0x240E0054 -> 0x240E007A`

Gopher64 survived and hardware booted/looped, but the credits and gunbarrel remained essentially stock-like and the visible front text issue did not materially improve. Reject as non-improving. The console was restored to `gamefulltop0` afterward.

Evidence:

- `diagnostics/captures/contact_sheets/frontbox_noinput_gopher_20260510.jpg`
- `diagnostics/captures/contact_sheets/flbox_powercycle_startup_20260510_sheet.jpg`
- `diagnostics/captures/contact_sheets/flbox_live_followup_20260510_sheet.jpg`
- `diagnostics/captures/current/after_restore_gamefulltop0_after_flbox_reject_20260510.png`

## 2026-05-10 GE Decomp Refresh and Hlimit Canary

The user pointed out the upstream GE decomp at `https://github.com/n64decomp/007`; a fresh local checkout now lives at:

```text
C:\Users\codex\Documents\GitHub\007
```

Key title/gameplay mapping from that source:

- `src/fr.c` programs the VI context from `g_ViBackData` after higher-level code calls `viSetXY`, `viSetBuf`, `viSetViewSize`, and `viSetViewPosition`.
- `src/game/bondview.c` is still the strongest guide for gameplay viewport work; it separates buffer dimensions from view size/position.
- `src/game/title.c` shows the gunbarrel is layered: `manipulateGunbarrelAndLogoMatrices` draws the moving gunbarrel/logo, then the state machine can draw `insert_sniper_sight_eye_intro` and `insert_sight_backdrop_eye_intro` in several phases before and after the blood overlay.
- `src/game/lvl.c` resets non-title stage loading through `viSetVideoMode(MD_NORMAL)`, which explains why gameplay and title/front experiments can have different failure modes.

The current fallback already includes the direct front `viSetXY`/`viSetBuf` words and expanded menu dimension words, so three new direct overlays were intentionally no-ops:

```text
artifacts/generated/gamefulltop0_expandedmenu_current_20260510.z64
artifacts/generated/gamefulltop0_frontxy_expandedmenu_current_20260510.z64
artifacts/generated/gamefulltop0_frontxybuf_expandedmenu_current_20260510.z64
MD5 for all three: 17d4ea3194d02d5ea121b1e42aa59469
```

A one-word title/menu height-limit canary was added as `front_height_limit_480i_only`:

```text
artifacts/generated/gamefulltop0_hlimit_current_20260510.z64
MD5: b68122a8982d25305046caef3398f207
N64 CRC: CD6799C2 7544831F
Report: reports/tnd480i_gamefulltop0_hlimit_current_20260510_report.json
Only direct patch: 0x46F18, 0x2418014A -> 0x241801E0
```

Gopher64 process-smoked this ROM without exit (`reports/smoke/smoke_gamefulltop0_hlimit_noinput52_20260510.json`), but the local emulator visual capture path was degraded during the smoke: ffmpeg `gdigrab` failed with error 5, Pillow `ImageGrab` failed, and the Win32 `PrintWindow` fallback captured only the Gopher64 title bar plus black client area (`reports/smoke/smoke_hlimit_printwindow20_20260510.json`).

Hardware follow-up with the capture-then-Kasa-cycle helper rejected this canary as a gunbarrel/title fix. The clip reaches the title/credits loop and looks materially like the fallback: the double aperture remains and red timing is unchanged (`40.307s` vs fallback `40.340s`). Evidence:

- `diagnostics/captures/videos/hlimit_current_coldboot_20260510.mp4`
- `diagnostics/captures/contact_sheets/hlimit_current_coldboot_20260510_sheet.jpg`
- `diagnostics/captures/contact_sheets/hlimit_current_gunbarrel_24_60_2fps_20260510.jpg`
- `reports/capture_cadence/motion_hlimit_current_vs_helper_fallback_20260510.json`

Do not keep spending hardware cycles on the plain `front_height_limit_480i_only` patch by itself.

Next title direction: isolate title state-machine layers around `insert_sniper_sight_eye_intro` and `insert_sight_backdrop_eye_intro` by callsite, using the current fallback as base. Global title blitter edits, global z-buffer/front-buffer edits, whole-asset swaps, and the single height-limit change have already shown bad hardware side effects or no useful gunbarrel effect.

## 2026-05-10 Early Title Layer Isolation

Using the GE decomp state-machine map, early callsite skip groups were added for the layers before the post-blood states:

| Layer | State 1 | State 2 | State 3 |
|---|---:|---:|---:|
| `insert_sniper_sight_eye_intro` | `0x3DEB4` | `0x3DF58` | `0x3E00C` |
| `insert_sight_backdrop_eye_intro` | `0x3DEBC` | `0x3DF60` | `0x3E014` |

Generated ROMs from the current fallback:

| ROM | MD5 | N64 CRC | Patches |
|---|---|---|---:|
| `gamefulltop0_skip_case1_sniper_20260510.z64` | `dbe6af2893c3b2a33977d07937756a12` | `F367A65A C7CCE752` | 1 |
| `gamefulltop0_skip_case1_backdrop_20260510.z64` | `ca5ea150976e2c4665f369dc01d13113` | `F367A45E 3082C162` | 1 |
| `gamefulltop0_skip_case1_layers_20260510.z64` | `dc3ed2a7e7d9f9ab26c542d22627d24b` | `ECE7BA5A 441178C0` | 2 |
| `gamefulltop0_skip_cases1_3_sniper_20260510.z64` | `a45b83f5b84d807180ad0a75dbe764e2` | `ECE7C4DE 40F37420` | 3 |
| `gamefulltop0_skip_cases1_3_backdrop_20260510.z64` | `add0de788c4b2db436c8e8eb99854870` | `ECE7C2DE 4DBADBF2` | 3 |

All five survived Gopher64 process smokes, but visuals remain unavailable from emulator capture in the current session.

Hardware follow-up first tested the narrowest backdrop canary, `gamefulltop0_skip_case1_backdrop_20260510.z64`. It booted and looped through title/gunbarrel/credits (`diagnostics/captures/contact_sheets/skip_case1_backdrop_powercycle_startup_20260510_sheet.jpg`), but the useful clip started after the beginning of the coldboot path and did not show a compelling improvement. A subsequent attempt to record a coldboot clip by starting ffmpeg in the background failed with exit `-5`, and the immediate capture afterward was black. The SC64 menu was recovered and the current fallback restored.

After adding `scripts/hardware/record_gvusb2_kasa_cycle.ps1`, the wider backdrop canary `gamefulltop0_skip_cases1_3_backdrop_20260510.z64` was tested with a true capture-then-Kasa-cycle recording. It also looked materially like the fallback: the double white aperture phase and stock-like gunbarrel timing remained visible in `diagnostics/captures/contact_sheets/skip_cases1_3_backdrop_coldboot_20260510_sheet.jpg`. The cadence analyzer reported essentially unchanged red timing on the same helper workflow: fallback first sustained red `40.340s`, backdrop-skip first sustained red `40.174s` (`reports/capture_cadence/motion_skip_cases1_3_backdrop_vs_helper_fallback_20260510.json`).

The complementary `gamefulltop0_skip_cases1_3_sniper_20260510.z64` canary was then captured with the same helper. It removed the normal gunbarrel/title progression and left the intro stuck on a small white crescent for the rest of the 82-second clip (`diagnostics/captures/contact_sheets/skip_cases1_3_sniper_coldboot_20260510_sheet.jpg`). The cadence analyzer found no sustained red phase (`reports/capture_cadence/motion_skip_cases1_3_sniper_20260510.json`).

Conclusion: the sniper/RLE layer is essential to advance the state-machine visuals and cannot simply be skipped. The useful insight is narrower: the double-aperture problem is not from the backdrop layer alone, and the fix probably needs to adjust how `insert_sniper_sight_eye_intro` computes/draws its RLE slice under the 480i dimensions rather than removing or replacing the whole layer.

## 2026-05-10 Sniper/RLE Slice Argument Canaries

The next canaries kept `insert_sniper_sight_eye_intro` alive and changed only the argument setup immediately before its call to `sub_GAME_7F007CC8`.

Divisor probes changed the `1280.0f` high word at `0x3C95C`:

| ROM | MD5 | N64 CRC | Patch |
|---|---|---|---|
| `gamefulltop0_sniper_div640_20260510.z64` | `1ba3dfa574477439e97b9ab2e712208c` | `CD6798DE 9FD2A8B7` | `0x3C0144A0 -> 0x3C014420` |
| `gamefulltop0_sniper_div960_20260510.z64` | `f41a7ad5776641b93793b8de5ac64d0d` | `CD6798FE E6DBBD85` | `0x3C0144A0 -> 0x3C014470` |
| `gamefulltop0_sniper_div2560_20260510.z64` | `ac27081891a4f69ca0d40eabf4aad462` | `CD6798DE 47E115B8` | `0x3C0144A0 -> 0x3C014520` |

All three process-smoked in Gopher64 (`reports/smoke/smoke_sniper_divisors_20260510.json`) and booted on hardware. They reached the title/credits path, but none removed the paired white aperture or produced a GE 480i-like cadence shift. Evidence:

- `diagnostics/captures/contact_sheets/sniper_div640_coldboot_20260510_sheet.jpg`
- `diagnostics/captures/contact_sheets/sniper_div960_coldboot_20260510_sheet.jpg`
- `diagnostics/captures/contact_sheets/sniper_div2560_coldboot_20260510_sheet.jpg`
- `reports/capture_cadence/motion_sniper_div640_vs_helper_fallback_20260510.json`
- `reports/capture_cadence/motion_sniper_div960_vs_helper_fallback_20260510.json`
- `reports/capture_cadence/motion_sniper_div2560_vs_helper_fallback_20260510.json`

The second group changed the final x argument at `0x3C980`, replacing `mfc1 a1,f18` with constant `a1` values:

| ROM | MD5 | N64 CRC | Patch |
|---|---|---|---|
| `gamefulltop0_sniper_x0_20260510.z64` | `148ee74db44750692d5c1e5693156177` | `CD6D49DE 0E96ACFD` | `0x44059000 -> 0x00002825` |
| `gamefulltop0_sniper_xleft160_20260510.z64` | `68657693a9e4d1f1b71e619647eec008` | `8D6647DE C9E7394F` | `0x44059000 -> 0x2405FF60` |
| `gamefulltop0_sniper_xright160_20260510.z64` | `f34fc3e88a6bea4a2832e4a69c092d9c` | `8D67B9DE 9360E9F4` | `0x44059000 -> 0x240500A0` |

All three process-smoked in Gopher64 (`reports/smoke/smoke_sniper_xargs_20260510.json`) and booted on hardware. They are rejected as fixes, but they proved that the RLE slice is composited separately from the moving barrel layer: forcing or biasing `a1` visibly separates the two barrel images. Evidence:

- `diagnostics/captures/contact_sheets/sniper_x0_coldboot_20260510_sheet.jpg`
- `diagnostics/captures/contact_sheets/sniper_xleft160_coldboot_20260510_sheet.jpg`
- `diagnostics/captures/contact_sheets/sniper_xright160_coldboot_20260510_sheet.jpg`
- `reports/capture_cadence/motion_sniper_x0_vs_helper_fallback_20260510.json`
- `reports/capture_cadence/motion_sniper_xleft160_vs_helper_fallback_20260510.json`
- `reports/capture_cadence/motion_sniper_xright160_vs_helper_fallback_20260510.json`

Updated conclusion: this is not a simple sniper-slice divisor problem. The double-barrel symptom is a two-layer composition problem between `insert_sniper_sight_eye_intro` and the moving gunbarrel layer. The next title candidates should target when the RLE slice layer is drawn, which source/destination state it uses, or the display-list state around the layer handoff, rather than shifting its final x coordinate.

## 2026-05-10 Internal RLE and Moving-Barrel Display-List Canaries

The next probes separated the inner RLE blit from the moving gunbarrel display-list draws in `src/game/title.c`.

| ROM | MD5 | N64 CRC | Direct patch |
|---|---|---|---|
| `gamefulltop0_sniper_internal_rle_skip_20260510.z64` | `7af2e7bb1c53f3ef5b423a78a7dbccac` | `CE67A5DA A1AD2863` | `0x3C984: jal sub_GAME_7F007CC8 -> move v0,s0` |
| `gamefulltop0_moving_skip_prebarrel_20260510.z64` | `b468a4d4460c9f92b645b31919d7415a` | `ED6795DE D941C24E` | `0x3C624: lui t8,0x0600 -> addiu t8,zero,0` |
| `gamefulltop0_moving_skip_postbarrel_20260510.z64` | `fd5e75b9f3bc940a9807810eb3e51a8d` | `ED6795DE 394185AD` | `0x3C68C: lui t7,0x0600 -> addiu t7,zero,0` |
| `gamefulltop0_moving_skip_bothbarrels_20260510.z64` | `a6e42abfdf7bed3dabb9ff2ea43bf109` | `9D67ADDE CB6F1824` | both moving display-list suppressions |

All four process-smoked in Gopher64 (`reports/smoke/smoke_internal_rle_and_moving_barrel_skips_20260510.json`) and were hardware-tested with capture-then-Kasa-cycle clips.

The internal-RLE skip is not a final patch because it removes too much gunbarrel art and advances the red phase too early, but it is the clearest diagnostic so far: the doubled rifled-barrel/RLE image largely disappears when the call at `0x3C984` is bypassed. That makes `sub_GAME_7F007CC8` or the `sub_GAME_7F01B240` blitter/source state the primary target. Evidence:

- `diagnostics/captures/contact_sheets/sniper_internal_rle_skip_coldboot_20260510_sheet.jpg`
- `reports/capture_cadence/motion_sniper_internal_rle_skip_vs_helper_fallback_20260510.json` (`first_sustained_red`: fallback `40.340s`, canary `38.172s`)

The moving display-list suppressions are also rejects as fixes. They reduce some early paired-dot/aperture clutter and preserve more art than the internal-RLE skip, but the cadence remains stock-like:

- `diagnostics/captures/contact_sheets/moving_skip_prebarrel_coldboot_20260510_sheet.jpg`, red `40.440s`
- `diagnostics/captures/contact_sheets/moving_skip_postbarrel_coldboot_20260510_sheet.jpg`, red `40.474s`
- `diagnostics/captures/contact_sheets/moving_skip_bothbarrels_coldboot_20260510_sheet.jpg`, red `40.407s`

Updated conclusion: the useful fix is unlikely to be another whole-layer skip. The RLE path must remain active enough to advance the intro, but its source rectangle, destination rectangle, clipping, or per-state draw timing needs to be corrected for the 480i/front-buffer dimensions so it does not composite a second misaligned gunbarrel over the moving layer.

## 2026-05-10 Single-State Sniper and RLE Color Canaries

The narrow state-1 sniper skip was tested after the wider state-1-3 sniper skip to verify whether only the first pre-blood sniper/RLE call was expendable:

| ROM | MD5 | N64 CRC | Result |
|---|---|---|---|
| `gamefulltop0_skip_case1_sniper_20260510.z64` | `dbe6af2893c3b2a33977d07937756a12` | `F367A65A C7CCE752` | Reject: strands the intro on a small crescent and never reaches sustained red. |

Evidence:

- `diagnostics/captures/videos/skip_case1_sniper_coldboot_20260510.mp4`
- `diagnostics/captures/contact_sheets/skip_case1_sniper_coldboot_20260510_sheet.jpg`
- `reports/capture_cadence/motion_skip_case1_sniper_vs_helper_fallback_20260510.json`

The next probes kept the RLE blit active but replaced the three end-color loads for `D_8002A7E8` before the `sub_GAME_7F007CC8` call at `0x3C984`. They test whether the doubled rifled layer is mostly the bright end of the grayscale ramp.

| ROM | MD5 | N64 CRC | End color |
|---|---|---|---:|
| `gamefulltop0_sniper_rle_endcolor0_20260510.z64` | `c465c11faec8be0f8e4f389a02fb41ed` | `E81C7992 D3503108` | `0x00` |
| `gamefulltop0_sniper_rle_endcolor32_20260510.z64` | `dd0a0cba5b692cfc24e78f9ecaff8a97` | `38E79981 5FE5BF84` | `0x20` |
| `gamefulltop0_sniper_rle_endcolor128_20260510.z64` | `22e65ee67c5dfe5a19d3785ef27cf5cb` | `38E79AC1 5D09DD3D` | `0x80` |

Evidence:

- `reports/smoke/smoke_sniper_rle_endcolors_20260510.json`
- `diagnostics/captures/contact_sheets/sniper_rle_endcolor0_coldboot_20260510_sheet.jpg`
- `diagnostics/captures/contact_sheets/sniper_rle_endcolor32_coldboot_20260510_sheet.jpg`
- `diagnostics/captures/contact_sheets/sniper_rle_endcolor128_coldboot_20260510_sheet.jpg`
- `reports/capture_cadence/motion_sniper_rle_endcolors_vs_helper_fallback_20260510.json`

Result: `endcolor0` and `endcolor32` largely suppress the doubled RLE/rifling layer while preserving progression through the red/title/credits sequence, but they also remove too much barrel art. `endcolor128` keeps the doubled look. All three remain stock-like in cadence: fallback first sustained red `40.340s`, `endcolor0` `40.307s`, `endcolor32` `40.474s`, and `endcolor128` `40.507s`.

Updated conclusion: RLE color ramp control is useful as a visual diagnostic and may become part of a selective/per-state cleanup, but it does not create the GE 480i-style gunbarrel slowdown. The remaining cadence problem is still likely in the front/title render workload, VI/framebuffer path, or state timing around the gunbarrel sequence.

## 2026-05-11 Gunbarrel Case-1 Timing Canaries

The next pass isolated the state-machine timing in `sub_GAME_7F009254` case 1. In the fallback ROM, the Bond-on-screen phase calls `insert_sniper_sight_eye_intro` and `insert_sight_backdrop_eye_intro`, then decrements `g_TitleX` by loading the NTSC `5.8183274f` constant through the instructions at ROM `0x3DF04/0x3DF08`. The timing canary replaces only those two instructions with a literal `3.625f` decrement and keeps the `-80.0f` threshold at `0x3DF0C/0x3DF10` intact.

| ROM | MD5 | N64 CRC | Result |
|---|---|---|---|
| `gamefulltop0_gunbarrel_case1_slow3625_20260510.z64` | `5b5d99331565d65ef13e7e255fe372d7` | `CD26F5CF BD500799` | Useful diagnostic: delays first sustained red from fallback `40.340s` to `45.078s`, giving the expected slower Bond-on-screen gunbarrel phase, but the doubled RLE barrel remains. |
| `gamefulltop0_gunbarrel_slow3625_endcolor64_20260510.z64` | `96c05a35d0d064814a2613487fd1951a` | `3826F4CE 0020B8DC` | Reject as final: preserves the slow timing (`45.045s`) and dims the duplicate layer, but the barrel art is too dark/underpowered. |
| `gamefulltop0_gunbarrel_slow3625_endcolor96_20260510.z64` | `c42feb1742b8eed834bc1b82dd87504c` | `3826F44E 3FE40BE9` | Reject as final: survives emulator and hardware, with slow timing (`44.745s`), but still leaves an underpowered/miscomposited barrel and does not solve the duplicate aperture/rifling problem cleanly. |

Evidence:

- `reports/smoke/smoke_gunbarrel_case1_slow3625_20260510.json`
- `reports/smoke/smoke_gunbarrel_slow3625_endcolor64_20260510.json`
- `reports/smoke/smoke_gunbarrel_slow3625_endcolor96_20260510.json`
- `diagnostics/captures/contact_sheets/gunbarrel_case1_slow3625_gunbarrel_24_74_2fps_20260510.jpg`
- `diagnostics/captures/contact_sheets/gunbarrel_slow3625_endcolor64_gunbarrel_24_74_2fps_20260510.jpg`
- `diagnostics/captures/contact_sheets/gunbarrel_slow3625_endcolor96_gunbarrel_24_74_2fps_20260510.jpg`
- `reports/capture_cadence/motion_gunbarrel_case1_slow3625_vs_helper_fallback_20260510.json`
- `reports/capture_cadence/motion_gunbarrel_slow3625_endcolor64_vs_refs_20260510.json`
- `reports/capture_cadence/motion_gunbarrel_slow3625_endcolor96_vs_refs_20260510.json`

Conclusion: the GE-like gunbarrel slowdown can be mimicked by slowing the case-1 `g_TitleX` advance, so cadence is now a controllable state-machine dimension. It should not be mistaken for the full 480i fix: the visible composition failure is still the RLE/blitter layer interaction. Keep the `3.625f` timing patch available as a later polish ingredient, but the next useful work is source/destination/clipping or per-state gating around the inner RLE blit rather than more color-only or global asset tests.

## 2026-05-11 Sniper Wrapper Alt-640 Blitter Canary

The GE decomp comparison shows an adjacent 640-stride sibling to the active sniper/title blitter:

- `sub_GAME_7F01B240` is what `insert_sniper_sight_eye_intro` reaches through the wrapper at ROM `0x3C7F8`; it advances source rows by `0x1B8` in stock GE and is globally patched by the GE 480i ROM to `0x280` plus wider texture-rectangle constants.
- `sub_GAME_7F01B6E0` already has a `0x280` source stride and a different row loop/argument contract.

Because global `K_title_draw_*` patches already froze TND's shared title blitter into vertical bars, the new canary changed only the sniper wrapper's final call at `0x3C8A4`:

```text
artifacts/generated/gamefulltop0_sniper_call_alt640_blitter_20260511.z64
MD5: 5633d9bf60a79da22cdd2aa5b1085306
N64 CRC: CD679BDE 85B1D274
Direct patch: 0x3C8A4, jal sub_GAME_7F01B240 -> jal sub_GAME_7F01B6E0
Smoke: reports/smoke/smoke_sniper_call_alt640_blitter_20260511.json
```

Hardware result: reject as a patch, but keep as a useful map clue. The ROM survives, loops through title/credits, and does not recreate the old vertical-bar freeze. The gunbarrel, however, becomes visibly worse: the RLE layer turns into a large magenta/pink miscomposited barrel over the moving aperture, with stock-like/early red timing (`39.873s` first sustained red). Evidence:

- `diagnostics/captures/videos/sniper_call_alt640_blitter_coldboot_20260511.mp4`
- `diagnostics/captures/contact_sheets/sniper_call_alt640_blitter_gunbarrel_24_74_2fps_20260511.jpg`
- `reports/capture_cadence/motion_sniper_call_alt640_blitter_vs_refs_20260511.json`
- `diagnostics/captures/current/after_restore_fallback_from_alt640_blitter_20260511.png`

Conclusion: a callsite-specific blitter route is viable mechanically, but the raw sibling routine is not ABI-compatible enough to use directly. The next useful static target is not another raw call redirect; it is to compare `sub_GAME_7F01B240` and `sub_GAME_7F01B6E0` instruction-by-instruction and selectively borrow only the source stride, tile size, row loop, or texture-rectangle setup pieces into a guarded/callsite-specific path.

## 2026-05-11 Menu05-09 and Moving-Post Promotion

The best hardware branch after the slow-timing and stock-texture-setup work is now:

```text
artifacts/generated/gbslow_menu05_09_moving_post_20260511.z64
MD5: 739ae518dddfc423482a859b63e6f33e
N64 CRC: 735E38D7 95D565A3
```

Direct ingredients added on top of `gamefulltop0_gbslow_shared_blitter_stock_texture_setup_20260511.z64`:

| Ingredient | Direct range/site | Result |
|---|---:|---|
| `menu05_09_safe` | `0x403DC:0x45138` | Applies 161 safe GE-enhanced-480i direct front/menu words. Gopher64 menu-flow sheets show better document/paper menu behavior than the old current-best branch. |
| `moving_skip_post_matrix_barrel_only` | `0x3C68C` | Reduces the initial paired white aperture/dot phase while preserving the slow cadence and most moving-barrel art. |

Hardware evidence:

- `diagnostics/captures/videos/gbslow_menu05_09_moving_post_coldboot_20260511.mp4`
- `diagnostics/captures/contact_sheets/gbslow_menu05_09_moving_post_gunbarrel_24_74_2fps_20260511.jpg`
- `diagnostics/captures/contact_sheets/gbslow_menu05_09_moving_post_long_noinput_8s_20260511.jpg`
- `reports/capture_cadence/motion_gbslow_menu05_09_moving_post_long_vs_short_20260511.json`

Cadence stayed in the GE-like slow band: first sustained red `44.845s` in the short capture and `44.978s` in the long capture, with white-to-red just under six seconds. The long no-input recording still loops title/credits/gunbarrel and does not reach gameplay/demo, so intro/gameplay proof still requires emulator automation or user-driven console input.

The remaining visible hardware issues on this branch are not solved by the promoted ingredients: title/credits/cast composition can still clip or mirror, menu/level-select alignment is not final, and intro/gameplay framing/flicker need another driven check.

Offline blitter microprobes from this branch are rejected:

| ROM | Change | Result |
|---|---|---|
| `gbslow_menu05_09_moving_post_stock_stripsteps_20260511.z64` | Restores stock strip-step words at `0x500EC/0x500FC/0x50148/0x50168` | Startup/progression differs but no clear visual win. |
| `gbslow_menu05_09_moving_post_stock_rowcount_20260511.z64` | Restores stock row limit at `0x501AC` | Reintroduces static/garbage in Gopher64. |
| `gbslow_menu05_09_moving_post_stock_stride_20260511.z64` | Restores stock stride at `0x501B4` | Reintroduces static/garbage in Gopher64. |

This reinforces the current callsite/blitter interpretation: TND needs the stock texture setup words, but the GE 480i-style strip/row/stride behavior is still necessary in the shared blitter context. The next work should focus on higher-level title/front state, menu layout words after `0x454E8`, and callsite-specific RLE clipping/timing rather than reverting the blitter's row-count or stride.

## 2026-05-11 Display-Cast Rect/Text Rejection

The display-cast/front credits path was probed from the current-best `gbslow_menu05_09_moving_post_20260511.z64` branch because the no-input hardware loop still showed clipped or mirrored cast/credits screens after the gunbarrel. Five safe-range candidates were built:

| ROM | MD5 | Result |
|---|---|---|
| `gbslow_moving_post_displaycast_iface_20260511.z64` | `a257d6d50bb308fcf2115ccf51677070` | Gopher-safe, but visually no clear improvement over the promoted baseline. |
| `gbslow_moving_post_displaycast_rects_20260511.z64` | `a7fa5c4ae331eaa48e45a6e9d055e15c` | Hardware reject: cadence stayed good, but the no-input front loop blanked after the gunbarrel instead of continuing into the visible cast/credits sequence. |
| `gbslow_moving_post_displaycast_text_20260511.z64` | `e9f5548dd5b9c63a0861826880bda1bf` | Gopher reject: pushes display-cast text off the right side. |
| `gbslow_moving_post_displaycast_rects_text_20260511.z64` | `754e115b61799c912161879a52ca47cb` | Gopher reject: same text-position failure. |
| `gbslow_moving_post_displaycast_iface_rects_text_20260511.z64` | `c32678948da0a5d860e1de10a6af8634` | Gopher reject: same text-position failure. |

Hardware evidence for the only uploaded candidate:

- `diagnostics/captures/videos/gbslow_displaycast_rects_coldboot_20260511.mp4`
- `diagnostics/captures/contact_sheets/gbslow_displaycast_rects_coldboot_8s_labeled_20260511.jpg`
- `diagnostics/captures/contact_sheets/gbslow_displaycast_rects_gunbarrel_24_74_2fps_20260511.jpg`
- `reports/capture_cadence/motion_gbslow_displaycast_rects_vs_moving_post_20260511.json`

Conclusion: do not upload more display-cast rectangle/text overlays until the front loop state is better understood. The current-best ROM was restored to SC64 afterward.

## 2026-05-11 Playability Priority Reset

User testing showed the project is not yet playable enough to justify spending the next pass on gunbarrel/front polish. The new order is in-game playability first, pause/watch second, level intro/outro third, dossier/mission menu usability fourth, then front/title/gunbarrel/logos/demos.

The live console candidate was changed to:

```text
artifacts/generated/game_h460_top10_current.z64
MD5: 892cbd5e8253e9cc3c6c4c4645bd69c0
N64 CRC: CD679836 961D35FD
```

This candidate is based on the last solid gameplay/watch fallback, not the later gunbarrel/menu branch. It changes only the normal gameplay viewport height/top pair:

| Offset | Change | Purpose |
|---:|---|---|
| `0xBB91C` | `480 -> 460` | non-camera default viewport height |
| `0xBB954` | `480 -> 460` | non-camera fallback viewport height |
| `0xBBA80` | `0 -> 10` | non-camera default viewport top |

Hardware sanity after upload showed TND credits output at `diagnostics/captures/current/after_upload_game_h460_top10_wait10_20260511.png`. Gopher64 input evidence is `diagnostics/captures/contact_sheets/game_viewport_centering_input70_20260510.jpg`.

Next useful work: test Bazaar on hardware for top/bottom flicker, overscan, text boxes, countdown placement, and watch flicker. If it is still too tall, try the already-built `game_h440_top20_current.z64`. If it regresses, roll back to `TND64_480i_frontbuf_padorigin_watch_hud_menutable_menuxy_tndgeview_physicalfb_camfullheight_gamefulltop0_reserve58000_core_no_menu.z64`.

## 2026-05-17 Stage Z-Buffer Memory Diagnostic

After `tlbpages58` made Wreck clean/slow but left Party/City/Credits and the prism/crash levels broken, the stock-camera fallback was tested and behaved the same. That reduces confidence in the camera-viewport explanation. The next narrow hypothesis is that the active 640x480 stage z-buffer allocation is too expensive for some TND64 stages/effects.

The GE-style z-buffer allocation words are already present in the current branch:

| Offset | Current word | Meaning |
|---:|---|---|
| `0x106ED4` | `0x240F0280` | resolution-path z-buffer width 640 |
| `0x106EE4` | `0x241801E0` | resolution-path z-buffer height 480 |
| `0x106EF0` | `0x24190280` | low-res path z-buffer width 640 |
| `0x106F10` | `0x240801E0` | single-player z-buffer height 480 |
| `0x106F24` | `0x240901E0` | split/multiplayer z-buffer height 480 |

The first hardware-worthy diagnostic keeps the two 640-wide rows but restores stock heights:

```text
artifacts/generated/game_h460_top10_stock_dossier_tlbpages58_zbuf640hstock_007label_current.z64
MD5: dfd0af4e1ca054ad940d18e3ba89f713
BPS MD5: b943e4ea0e79fe93ac5ac3751a404409
```

It changes only:

| Offset | Change |
|---:|---|
| `0x106EE4` | `480 -> 330` |
| `0x106F10` | `480 -> 240` |
| `0x106F24` | `480 -> 120` |

Hardware startup passed through CMK/logos/gunbarrel/title/cast (`diagnostics/captures/contact_sheets/zbuf640hstock_007label_powercycle_startup_20260517.jpg`), but manual testing rejected it: the save did not load and Bazaar had the blue issue again. Treat the stock-height z-buffer idea as a regression. Do not proceed to `zbuf640h360` or `zbufstock` unless a later analysis gives a stronger reason.

Recovery: the previous `tlbpages58` branch was restored to SC64 using short staging filenames (`tnd58.z64` / `tnd58.sav`) and the generated all-missions save (`MD5 79ed3fe6851b080ff21de69fd12f034d`). Startup evidence is `diagnostics/captures/contact_sheets/tnd58_shortname_restore_powercycle_startup_20260517.jpg`.
