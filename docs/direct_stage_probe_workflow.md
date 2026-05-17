# Direct Stage Probe Workflow

Last updated: 2026-05-17

Purpose: reduce manual TND6480i hardware testing by generating one short ROM per level that boots directly into that stage. This avoids repeated save-file loading, dossier navigation, difficulty selection, and long full-romhack test passes.

## Builder

```text
python scripts/build_direct_stage_probe_roms.py
```

Default input:

```text
artifacts/generated/tnd58.z64
artifacts/generated/tnd58.sav
```

Default output:

```text
artifacts/generated/stage_probes/p00bzr.z64
artifacts/generated/stage_probes/p01pty.z64
...
artifacts/generated/stage_probes/p13end.z64
reports/stage_probes/direct_stage_probes_latest.json
```

The ROM stems are intentionally short for SC64 save matching. Each probe has same-stem `.sav` and `.eep` files.

## Patch

The builder patches the early `bossMainloop` debug-token path at ROM offsets `0x6C94-0x6CA4`. It replaces the unused `-level_` token parser with:

```text
lui   at, 0x8002
addiu v0, zero, <stage_id>
sw    v0, 0x41A8(at)   ; g_StageNum
b     after_token_parser
nop
```

This is a probe-only change. It does not alter the actual 480i patch sites and should not be included in a public gameplay patch.

## Level Map

| Probe | TND64 level | Stage ID | Original GE slot |
| --- | --- | ---: | --- |
| `p00bzr` | Bazaar | 33 | Dam |
| `p01pty` | Party | 34 | Facility |
| `p02lab` | Labs | 35 | Runway |
| `p03prs` | Press | 36 | Surface 1 |
| `p04hot` | Hotel | 9 | Bunker 1 |
| `p05prk` | Parkhaus | 20 | Silo |
| `p06wrk` | Wreck | 26 | Frigate |
| `p07twr` | Tower | 43 | Surface 2 |
| `p08cty` | City | 27 | Bunker 2 |
| `p09bot` | Boat | 22 | Statue |
| `p10brg` | Bridge | 24 | Archives |
| `p11vol` | Volcano | 29 | Streets |
| `p12als` | Alaska | 30 | Depot |
| `p13end` | The End | 25 | Train |

## Hardware Proof

`p06wrk` was validated on 2026-05-17:

```text
artifacts/generated/stage_probes/p06wrk.z64
diagnostics/captures/videos/direct_p06wrk_hardware_20260517.mp4
diagnostics/captures/contact_sheets/direct_p06wrk_hardware_20260517.jpg
```

The GV-USB2 contact sheet shows direct boot into the Wreck intro/gameplay path without menu input. This proves the direct-stage probe mechanism works on real N64 + SC64.

## Recommended Test Loop

1. Build or update a candidate normally.
2. Rebuild stage probes using that candidate as `--base`.
3. Run one known-good control probe in Gopher64, usually `p06wrk` or `p10brg`.
4. Run one failing probe, usually `p01pty`, `p08cty`, or `p13end`.
5. Upload exactly one probe to SC64 and capture 20-45 seconds through GV-USB2.
6. Compare the capture against the previous probe for the same stage.

This is now the preferred path for Party/City/The End/Tower/Boat/Hotel/Volcano troubleshooting. Full manual playthroughs should be reserved for promising candidates only.
