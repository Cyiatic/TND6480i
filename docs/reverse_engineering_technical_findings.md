# Reverse Engineering Technical Findings

Date: 2026-05-19

This document summarizes the important technical findings behind the
`g1mcfix4` / `TND6480i_g1mcfix4_RC1` release candidate. It is written for
readers who are comfortable with MIPS words, ROM offsets, VI setup, and N64
memory layout.

It is not an exhaustive patch listing. Use these machine-readable reports for
the full word-level audit:

- `reports/tnd6480i_g1mcfix4_bps_manifest.json`
- `reports/tnd6480i_g1mcfix4_multiplayer_menu_layout_20260519.json`
- `reports/tnd480i_g1mcfix1_mission_complete_20260519.json`
- `reports/tnd480i_g1cred1_credits_crawl_20260519.json`
- `reports/tnd480i_g1tabhit1_tab_hitbox_20260519.json`
- `reports/tnd480i_g1hbrf1_briefing_candidate_20260519.json`
- `docs/decomp_480i_findings.md`
- `docs/ge_decomp_offset_audit.md`

## Address Conventions

Unless noted otherwise, offsets below are physical big-endian ROM offsets in
the `.z64` file.

Some GE/TND code and data are inside a `0x1172` raw-deflate stream beginning at
ROM `0x21990`. When a note says "inflated main offset", the offset is inside
the decompressed stream, not the packed ROM byte position. Repacking that stream
causes large binary diffs around `0x21990+`; those bytes are compression churn,
not necessarily direct instruction edits.

N64 header CRC words at ROM `0x10-0x17` are recalculated after every ROM edit.
Those bytes should be ignored when reasoning about behavior.

## Release Candidate Facts

Active ROM:

```text
artifacts/generated/g1mcfix4.z64
MD5: fa93be061c59ef5cabad24fbf5f66b39
Size: 0x1025A00 bytes
```

Baseline used for the local BPS manifest:

```text
artifacts/roms/BASELINE_TND64_Expanded_direct_from_stock.z64
MD5: 1ee22dd1d70443f5e4766d4238756949
Size: 0x1000000 bytes
```

The final ROM is larger than the expanded TND baseline because a scaled
gunbarrel/title RLE asset is appended at `0x1000000-0x1025A00`.

## Main Architectural Finding

GoldenEye's enhanced 480i behavior is a package, not a single VI register or
one `viSetXY(640, 480)` patch.

The port only became stable when these were made coherent:

- VI mode tables and `__osViSwapContext` behavior.
- Two 640x480x16 framebuffers.
- Framebuffer clear, pointer initialization, and active-buffer selection.
- TLB/page-cache placement under Expansion Pak.
- Gameplay and camera viewport functions.
- Front-end/menu framebuffer and z-buffer dimensions.
- Page-specific dossier/menu layout constants.
- Title/gunbarrel RLE asset dimensions and shared blitter geometry.

Emulator-only success was often misleading. Several candidates that rendered in
Gopher64 or Ares black-screened, corrupted the field layout, or hard-locked on
real N64 hardware.

## 1. Framebuffer Layout

Each 640x480x16 framebuffer is `0x96000` bytes. The final candidate uses two
separate buffers:

```text
fb0: 0x80400000-0x80495FFF
fb1: 0x8076A000-0x807FFFFF
```

The earlier `fb0=0x80300000, fb1=0x8076A000` layout was a useful stepping stone,
but level boot/performance testing eventually moved `fb0` to `0x80400000`.

Important ROM patch groups:

| ROM offset/range | Final role |
|---:|---|
| `0x3C8C-0x3C94` | Load the second framebuffer global instead of deriving it from one contiguous stride. |
| `0x3D24-0x3D68` | Clear both framebuffers, each with size `0x96000`; final clear bases are `0x80400000` and `0x8076A000`. |
| `0x46B4-0x46F0` | Select active framebuffer through `g_ViBackIndex` and store the selected pointer into the VI task data. |
| `0x6584-0x65B4` | Initialize KSEG1 framebuffer globals; final stores are based on `0x80400000` and `0x8076A000`. |

Key final words:

| Offset | Final word | Meaning |
|---:|---:|---|
| `0x3D30` | `0x3C048040` | clear `fb0` base upper, `0x80400000` |
| `0x3D48` | `0x3C048076` | clear `fb1` base upper, `0x8076A000` |
| `0x3D4C` | `0x3484A000` | clear `fb1` base lower, `0xA000` |
| `0x6584` | `0x3C048040` | initialize `fb0` base upper, `0x80400000` |
| `0x658C` | `0x3C058076` | initialize `fb1` base upper, `0x8076A000` |
| `0x6590` | `0x34A5A000` | initialize `fb1` base lower, `0xA000` |

The important change from the stock/expanded TND path is that the active
framebuffer is no longer safely modeled as "one base plus a small stock stride."
The 480i buffer is too large for that. The final code treats the two buffers as
explicit globals and selects between them.

## 2. TLB/Page-Cache Placement

The earliest memory model was wrong. The visible failures were not only caused
by a low framebuffer collision. The Expansion Pak page cache was also competing
with high framebuffer memory.

Stock direct startup behavior:

```text
ROM 0x241C: 3C08802F  ; lui   t0,0x802F
ROM 0x2420: 25086000  ; addiu t0,t0,0x6000
```

The game adds the Expansion Pak delta later. On an 8 MB console, that places the
90-page cache around:

```text
0x806F6000-0x807A9FFF
```

That overlaps the high 480i framebuffer at `0x8076A000-0x807FFFFF`.

The final candidate keeps the 90-page cache for performance, but relocates the
base down so the cache ends exactly before `fb1`:

```text
ROM 0x241C: 3C08802B  ; direct base upper 0x802B
ROM 0x2420: 25086000  ; direct base lower 0x6000
ROM 0x2618: 2C81005A  ; keep 90-page wrap count

Expected 8 MB range:
0x806B6000-0x80769FFF
```

The 58-page cache candidate also avoided the overlap, but Wreck/Printworks
performance regressed badly. The final layout keeps the 90-page cache and moves
`fb0` to `0x80400000` instead.

## 3. VI / `__osViSwapContext`

The GE480i low-level VI family maps into libultra `__osViSwapContext`, not a
TND-specific gameplay function. Same-offset decomp comments in the local GE
checkout sometimes collide with the ROM version and should not be trusted
blindly.

Important H-family sites:

| Offset | Role |
|---:|---|
| `0x19978`, `0x19980`, `0x19984` | origin/control-flow bypass around the stock repeat-line path |
| `0x199B4` | doubles the width value before `VI_WIDTH_REG` |
| `0x199D0` | keeps the paired sync write using the live `A440` VI base |
| `0x19A24`, `0x19A60`, `0x19A64` | moves/scales the `y.scale` path before `VI_Y_SCALE_REG` |

Important result: these edits were unsafe when tested as isolated knobs. `H
only`, `H origin only`, `H width only`, and `H scale only` all produced black or
corrupt hardware output. They only make sense as part of the full framebuffer,
mode-table, and viewport package.

## 4. Gameplay And Camera Viewports

The first obvious symptom was that Bond's hand and level geometry remained
aliased even when VI output appeared interlaced. That separated the output mode
from the game/camera render dimensions.

Direct render dimension table:

| Offset | TND base | Final | Meaning |
|---:|---:|---:|---|
| `0x4F354` | `0x014000F0` | `0x028001E0` | `320x240 -> 640x480` |
| `0x4F35C` | `0x01B8014A` | `0x028001E0` | `440x330 -> 640x480` |

The second word was not safe early in isolation. It became usable only after the
front/menu framebuffer path and memory package were fixed.

Gameplay `bondview`-family returns:

| Offset | Final word | Meaning |
|---:|---:|---|
| `0xBB730` | `0x24020280` | low-res width return `640` |
| `0xBB740` | `0x24020280` | hi-res width return `640` |
| `0xBB754` | `0x240201E0` | low-res height return `480` |
| `0xBB764` | `0x240201E0` | hi-res height return `480` |

Camera/non-camera viewport fit:

| Offset | Final word | Meaning |
|---:|---:|---|
| `0xBB7A4` | `0x24020280` | camera/toggle width `640` |
| `0xBB7C0-0xBB7E0` | `0x24020280` family | non-camera/cinema/fallback widths `640` |
| `0xBB89C` | `0x240201F0` | GE480i camera height `496` |
| `0xBB8B8` | `0x2402017C` | GE480i camera height `380` |
| `0xBB8C0` | `0x24020260` | GE480i camera height `608` |
| `0xBB91C` | `0x240201B8` | non-camera default height `440` |
| `0xBB954` | `0x240201B8` | non-camera fallback height `440` |
| `0xBBA80` | `0x24020014` | non-camera default top `20` |

Forcing the camera-path top values to zero caused the "top rectangle" and blue
skybox-style corruption. The final candidate keeps the GE-style camera height
family and the non-camera top `20` rather than using a single full-screen
`top=0` hammer.

## 5. Z-Buffer And Stage Stability

GE480i-style front/game z-buffer dimensions are present in the final branch.
Relevant sites include:

| Offset | Final word | Meaning |
|---:|---:|---|
| `0x4D42C` | `0x24050280` | front z-buffer width `640` |
| `0x4D434` | `0x240601E0` | front z-buffer height `480` |
| `0x106ED4` | `0x240F0280` | expanded/menu width `640` |
| `0x106EE4` | `0x241801E0` | expanded/menu height `480` |
| `0x106EF0` | `0x24190280` | low-res expanded/menu width `640` |
| `0x106F10` | `0x240801E0` | single-player z-buffer height `480` |
| `0x106F24` | `0x240901E0` | split/multiplayer z-buffer height `480` |

Restoring stock z-buffer heights was tested as a memory-saving hypothesis. It
regressed Bazaar/Labs-style rendering and was rejected. The level-boot fix was
the TLB/framebuffer memory layout, not shrinking z-buffer height.

## 6. Title And Gunbarrel

The gunbarrel was not fixed by moving the moving aperture layer alone. The
important discovery was that TND's title/gunbarrel RLE source is not GE's stock
asset geometry, and the shared title blitter is used by multiple early screens.
Global blitter edits could fix one frame and break Rare/logo/title output.

The final candidate appends a scaled 640x430 title/gunbarrel asset and points
the title RLE source range at it:

```text
asset range: 0x1000000-0x1025A00
```

Key final words:

| Offset | Final word | Meaning |
|---:|---:|---|
| `0x3D928` | `0x3C030100` | title RLE source upper `0x0100` |
| `0x3D94C` | `0x24630000` | title RLE source lower `0x0000` |
| `0x3D948` | `0x3C0B0102` | title RLE end upper `0x0102` |
| `0x3D954` | `0x256B5A00` | title RLE end lower `0x5A00` |
| `0x4FDEC` | `0x3C170713` | title/gunbarrel texture setup upper |
| `0x4FDFC` | `0x3C0AE49F` | texture rectangle target width family |
| `0x4FE34` | `0x3C0143D7` | draw height float upper, `430.0` |
| `0x4FE3C` | `0x36F7F006` | texture setup lower |
| `0x4FE44` | `0x44818000` | use immediate height float |
| `0x4FF00` | `0x3C0E009F` | texture rectangle lower width family |
| `0x501AC` | `0x292101AE` | source row loop limit `430` |
| `0x501B4` | `0x26100280` | source stride `640` |

Rejected gunbarrel ideas that should not be reintroduced casually:

- Skipping the sniper/RLE layer removed too much art or stranded the intro.
- Forcing RLE end colors made the duplicate layer less visible but dimmed the
  barrel and did not solve cadence.
- Redirecting the sniper wrapper to the adjacent 640-stride blitter was
  mechanically viable but ABI-incompatible visually.
- Slowing the case-1 title-state `g_TitleX` decrement produced GE-like cadence
  as a diagnostic, but the final candidate does not carry that timing canary.

## 7. Front-End / Dossier Pages

The dossier work was the largest lesson in avoiding blind offset transplants.
GE480i coordinates are useful references, but TND's red dossier assets and fewer
missions mean some GE constants are wrong for TND.

Important findings:

- `0x4F35C = 0x028001E0` plus `0x4F1C4 = 0x10000003` put the front-end into the
  640x480 table path while skipping the old menu-framebuffer swap that
  black-screened earlier candidates.
- The file-select backdrop callsite at `0x41030` was restored to the original
  wrapper in the final branch. The cloned 480i blitter path fixed one coverage
  problem but caused a right-side smear/stretch on the file-select page.
- The clone/slack space remains useful: the mission-select label table is stored
  at ROM `0x4F9FC`, runtime `0x7F01AECC`.

Mission-select label table:

```text
ROM table: 0x4F9FC
Runtime:   0x7F01AECC
X table:   90, 191, 292, 393, 494
Y table:   92, 193, 294, 395
```

Pointer patches into the mission-select constructor:

| Offset | Final role |
|---:|---|
| `0x4302C` | high half for custom X table |
| `0x43030` | high half for custom Y table |
| `0x43034` | low half for custom Y table |
| `0x43038` | low half for custom X table |

Other front-end ranges:

| Range/sites | Role |
|---:|---|
| `0x43300-0x43D20` | difficulty page constructor/interface/checkmark GE480i coordinate family |
| `0x454E8-0x45604` | briefing/objective wrap thresholds |
| `0x4A000-0x4C500` | briefing/objective page coordinates |
| `0x3EFAC-0x3F00C` | common `NEXT` tab label geometry |
| `0x3F0A8-0x3F114` | `NEXT` tab hit detection/highlight band |
| `0x4C564-0x4C5F4` | mission-complete `Kill total` label/value spacing |
| `0x4C874-0x4CE8C` | cheat menu two-column label/value layout |
| `0x4566C-0x49F74` | multiplayer menu0E/menu0F/control-style layout cluster |

The final multiplayer pass intentionally copied only GE stock-to-GE480i words
where `g1mcfix3` still matched GE stock. TND-specific or already-custom words
were left alone. This avoided trampling romhack-specific multiplayer behavior.

## 8. Credits

The end-credits crawl is separate from the intro display-cast/character-credit
screens.

Rolling credits crawl fixes:

| Offset | Role |
|---:|---|
| `0xBD870` | default first-column X, `220 -> 320` |
| `0xBD878` | default second-column X, `220 -> 320` |
| `0xBD930` | pre-scan first-column explicit X, `+100` |
| `0xBD95C` | pre-scan second-column explicit X, `+100` |
| `0xBDA00` | render first-column explicit X, `+100` |
| `0xBDB80` | render second-column explicit X, `+100` |

Display-cast/intro character credit fixes touched row-specific text and
rectangle constants, including:

| Offset | Role |
|---:|---|
| `0x4ED24` | second-row credit text center X |
| `0x4ED3C` | second-row credit text Y |
| `0x4ED44` | second-row clip bottom |
| `0x4ED5C` | second-row render Y |
| `0x4EE14` | third-row credit text center X |
| `0x4EE2C` | third-row credit text Y |
| `0x4EE34` | third-row clip bottom |
| `0x4EE4C` | third-row render Y |

## 9. Save And Identity Notes

The ROM's internal title remains `GOLDENEYE`, and the save type is EEPROM 4K.
The visible `Custom` label was changed to `007`; that is an intentional text
label edit and not part of the 480i mechanics.

EverDrive X7 pairing depends on:

```text
ED64\gamedata\<exact ROM filename>.eep
```

The working final all-unlocked X7 save is:

```text
E:\ED64\gamedata\TND6480i_g1mcfix4_RC1.eep
MD5: DAF246CED5C48CD6AFEF841E9C4078D1
```

Manual copy-to-RAM did not reliably replace the active save during testing; the
per-ROM `gamedata` file did.

## Non-Obvious Rejections

These findings are useful because they describe traps future patch authors
should avoid:

- Emulator video output can say "interlaced" while gameplay is still rendering
  at stock internal dimensions.
- Same-offset GE decomp comments are not always same-version ROM truth. Verify
  the old word against the actual stock ROM before trusting the source line.
- The raw GE480i menu tables do not automatically make TND's dossier pages
  correct; some constants remove labels/icons because TND's assets and mission
  list differ.
- Global title blitter patches are dangerous. Rare logo, gunbarrel, title, file
  select, and cast screens share more code than is visually obvious.
- Shrinking z-buffer height was the wrong stability fix. The level crashes were
  resolved by TLB/framebuffer placement, not by reverting 480i z-buffer sizes.
- The 58-page TLB cache avoided overlap but made some stages unacceptably slow.
  The release candidate keeps 90 pages and relocates memory instead.

## Practical Reverse-Engineering Workflow

The workflow that finally worked:

1. Classify each patch as code, packed-main data, visual asset, or route-only
   test.
2. Compare the old word against stock GE, GE480i, and current TND before
   transplanting anything.
3. Prefer one subsystem per candidate: framebuffer, TLB, viewport, dossier page,
   title asset, etc.
4. Use direct-stage probe ROMs for level stability instead of repeatedly driving
   the whole game.
5. Use GV-USB2 hardware captures as the source of truth for screen geometry.
6. Promote only candidates with a matching save file and hardware evidence.

Route-only patches such as direct menu IDs or direct stage IDs must never be
carried into release builds.

## Assembly Modder Appendix

This section is aimed at anyone reading or porting the patch at the MIPS word
level. The short version: treat this patch as a set of related render-system
contracts, not as a pile of independent constants.

### Final Memory Map To Keep In Your Head

Ranges in this table are end-exclusive.

| Region | Final value/range | Notes |
|---|---:|---|
| ROM image | `0x000000-0x1025A00` | Release image after appending the scaled title/gunbarrel asset |
| Appended asset | `0x1000000-0x1025A00` | RLE-style data used by the front-end/title path |
| Framebuffer 0 | `0x80400000-0x80496000` | 640x480i 16-bit color buffer |
| Framebuffer 1 | `0x8076A000-0x80800000` | Second 640x480i buffer, high in expansion RAM |
| TLB/page cache | `0x806B6000-0x8076A000` | 90 pages, immediately below framebuffer 1 |
| Save type | EEPROM 4K | EverDrive path is `ED64\gamedata\<rom stem>.eep` |

The important boundary is the handoff between the page cache and framebuffer 1.
Earlier candidates left the page cache overlapping the second framebuffer, which
explained the Party/City/The End boot failures and the Hotel/Volcano prism
effects. Reducing the cache to 58 pages avoided overlap but cost too much
performance. The release keeps 90 pages and moves the cache down instead.

### Patch-Site Audit Checklist

Before promoting a new assembly change, do this audit:

1. Classify the site: direct ROM code, decompressed main segment, visual asset,
   data table, save text, or route-only probe.
2. Read the word from stock GE007, GE480i, stock TND64, and the current TND6480i
   candidate.
3. If the current TND word no longer equals the stock GE word, assume the
   romhack or an earlier TND6480i pass owns that word. Do not blindly transplant
   GE480i over it.
4. Check branch delay slots in pairs. A visually small change near `jal`, `b`,
   `beq`, `bne`, or `jr ra` can be half of the actual behavior.
5. Recompute the N64 header CRC after any ROM edit.
6. Verify first in emulator for boot/smoke behavior, then on hardware through
   GV-USB2 for geometry, field cadence, and text placement.

The most useful reference file for this audit style is
`docs/ge_decomp_offset_audit.md`. It records cases where same-offset GE decomp
comments existed but the old word did not match the stock GE ROM, which means
the comment was not safe to use as proof by itself.

### Safe Patch Shapes

These approaches produced stable candidates:

- Move the framebuffer and the page cache as one memory-budget decision.
- Port GE stock-to-GE480i deltas only where the current TND word still matches
  the old GE stock word.
- Patch menu pages in page-sized clusters, then verify each page against a
  hardware capture. Dossier pages share code, but their constants are not
  interchangeable.
- Add a new visual asset at the end of the ROM and update only the relevant
  pointer/dimension sites.
- Use short route ROMs to reach stages or menus, then discard the route patches
  before building a public candidate.

### Unsafe Patch Shapes

These approaches produced misleading or broken candidates:

- Copying raw GE480i menu tables wholesale. TND64 has different mission counts,
  art, labels, and page flow.
- Treating VI registers alone as proof of 480i. The console can output
  interlaced video while the game still renders stock-size content internally.
- Applying global title/front-end blitter changes. The Rare logo, gunbarrel,
  title, file select, and cast-credit paths share enough code that one fix can
  break another screen.
- Promoting direct-stage or direct-menu route patches. They are test harnesses,
  not release code.
- Shrinking z-buffer or cache sizes as a stability cure. Those masked symptoms
  while causing performance or visual regressions.

### Route-Only Probe Sites

The direct-stage probe builder patches ROM `0x6C94-0x6CA4` in the early
`bossMainloop` debug-token path:

```text
lui   at, 0x8002
addiu v0, zero, <stage_id>
sw    v0, 0x41A8(at)   ; g_StageNum
b     after_token_parser
nop
```

That writes runtime `g_StageNum` at `0x800241A8` and is intentionally excluded
from release builds. A similar warning applies to direct-menu route patches such
as the temporary menu-id edit around `0x3FF34`; those were only for getting the
hardware quickly to a target page.

### High-Value Reports For Assembly Readers

These generated reports are worth opening before touching related areas:

| File | Why it matters |
|---|---|
| `reports/tnd6480i_g1mcfix4_multiplayer_menu_layout_20260519.json` | Final 227-word multiplayer page cluster, with old/new words |
| `reports/tnd6480i_g1mcfix3_cheat_menu_value_spacing_20260519.json` | Cheat value spacing pass before the final candidate |
| `reports/tnd6480i_g1mcfix2_cheat_menu_layout_20260519.json` | Cheat menu two-column layout pass |
| `reports/tnd480i_g1hbrf1_briefing_candidate_20260519.json` | Briefing/objective/NEXT-tab fixes |
| `reports/tnd480i_g1tabhit1_tab_hitbox_20260519.json` | NEXT-tab hitbox/highlight correction |
| `reports/tnd6480i_g1mtabge4_bps_manifest.json` | Mission-table positioning candidate history |
| `docs/direct_stage_probe_workflow.md` | Probe-only boot path and stage ID map |
| `docs/ge_decomp_offset_audit.md` | Stock/480i/TND/decomp word comparison table |

### Interpreting Common MIPS Words In This Patch

Many edits are plain coordinate or pointer changes:

- `lui` high halves (`0x3Cxx....`) and `ori`/`addiu` low halves (`0x34xx....`,
  `0x24xx....`) usually build pointers or signed constants.
- `addiu zero,<imm>` forms such as `0x2404....` often feed X/Y/width/height
  arguments into drawing functions.
- `jal` callsites and their delay slots are common in the front-end. Audit the
  call and delay-slot word together.
- Signed 16-bit immediates matter. A value that looks like `0xFFFD` is `-3`,
  not a giant positive coordinate.
- Runtime addresses in reports are helper annotations, not a universal ROM-to-
  RAM mapping. Verify each segment in Ghidra or by old-word matching.

### Compression And Capacity Notes

Some relevant front-end code/data lives in the raw-deflate stream beginning at
ROM `0x21990` with header marker `0x1172`. Broad menu-table experiments
overflowed the available packed space, for example a `0x11BC8` packed result
against a `0xFDA7` budget. For those areas, prefer targeted word edits or a
known rebuild path that proves the compressed stream still fits.

### Hardware Validation Cues

Use visual behavior, not only emulator metadata:

- A real 480i path usually changes text sharpness and field flicker, and it can
  change cadence during heavy scenes.
- The pause menu and dossier text are good high-contrast geometry checks.
- The gunbarrel is a timing and geometry check: duplicate barrels, white-circle
  collapse, or Bond outrunning the aperture are separate failure modes.
- Stage probes are best for stability; full playthroughs are best for save/menu
  and result-screen coverage.

## 2026-05-25 Text/HUD Follow-Up

The `g1mcfix4` release candidate was playable, but Analogue 3D review showed
that mission text, ammo digits, and pause/watch text still looked closer to
stock resolution than GE480i. The successful follow-up line is:

```text
ROM: artifacts/generated/g1hiq3_gegate.z64
MD5: 4063fd9968b528148a9441b11dfd0203
Short package: artifacts/release/TND6480i_g1hiq3_fontgood_20260525_test.zip
Short ROM: G1HQ3AM.Z64
Save: artifacts/generated/g1hiq3_gegate_ammoon.sav
Save MD5: 50a3f7cf6e022fdec7f37f2cc8ae2e2a
```

Static contract report:

```text
reports/measurement/render_contract_g1hiq3_vs_g1mcfix4_20260525.json
```

Compared with `g1mcfix4`, `g1hiq3_gegate` keeps the same stable split
framebuffer and non-overlapping TLB/page-cache model, but it closes the audited
GE480i parity gaps in these categories:

| Category | `g1hiq3_gegate` vs GE480i |
|---|---:|
| VI swap sites | `8/8` exact |
| Direct dimensions | `2/2` exact |
| Bondview viewports | `14/14` exact |
| Text viewports | `5/5` exact |
| HUD numeric Y sites | `8/8` exact |
| Menu buffer sites | `7/7` exact |
| In-game overlay family | `60/60` exact |

This is the important technical distinction: the text/font fix did not require
switching to GE480i's contiguous upper framebuffer pair. The rejected
`g1hifb1`, `g1hqfb1`, and `g1hiq4_upperpair` branches showed that changing the
framebuffer presentation model could regress boot, audio, rendering, or speed.
The stable answer was to preserve TND6480i's split memory model and make the
text/HUD/front-end constants match the GE480i render contract.

Hardware/Analogue review then confirmed:

- The font now looks good.
- Bazaar's countdown timer position is corrected.
- The all-level boot/stability line remains intact.

Save-option correction was required before HUD comparison:

```text
scripts/patch_save_options.py
reports/measurement/g1hiq3_gegate_ammoon_save_options_20260525.json
```

The valid folder option word changed from `0x001A` to `0x003A`, setting
`OPTION_DISPLAYAMMO` and refreshing per-slot CRCs. Without this, GE480i and TND
HUD captures can appear different for save-setting reasons rather than render
reasons.

Anti-aliasing is another capture variable. The user later observed that the
in-game AA option has a large visible effect on text quality. That bit is not
mapped in the save-option helper yet, so future assembly-level text work should
begin with a same-folder EEPROM diff where only AA is toggled. Until then, AA
state must be recorded manually for watch/HUD/mission-intro captures and should
not be conflated with a glyph-rectangle or framebuffer regression.

Matched hardware capture evidence:

```text
diagnostics/captures/videos/force_fp_watch_ge480i_v3_20260525.mp4
diagnostics/captures/videos/force_fp_watch_tnd6480i_v3_20260525.mp4
diagnostics/captures/videos/force_fp_hud_ge480i_v2_20260525.mp4
diagnostics/captures/videos/force_fp_hud_tnd6480i_v2_20260525.mp4
reports/measurement/force_watch_text_metrics_ge_vs_tnd_v3_t50_20260525.json
reports/measurement/force_hud_text_metrics_ge_vs_tnd_v2_t38_20260525.json
```

For future assembly-level work, treat `g1hiq3_gegate` as the current known-good
word set. `g1mcfix4` is a rollback/release-packaging reference, not the latest
text-quality baseline.
