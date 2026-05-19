# Current Candidate Status - 2026-05-18

Current best hardware candidate:

- ROM: `artifacts/generated/g1casta1.z64`
- Save: `artifacts/generated/g1casta1.sav`
- BPS: `artifacts/generated/TND6480i_g1casta1_from_baseline_tnd.bps`
- ROM MD5: `73cfc56eb1f20e83a533956ab811fd24`
- Patch MD5: `1f4fa34581cc6156ab34b47168851230`

`g1casta1` is `g1castz1` plus the known scaled 640x430 gunbarrel RLE asset transplant and matching title/gunbarrel draw-target words. It intentionally does not change gameplay, level loading, pause menu, HUD, or dossier tables beyond the stable inherited work.

## Hardware Evidence

Primary per-screen acceptance atlas:

- `diagnostics/captures/current/preingame_annotations_g1casta1_20260518.jpg`
- Machine-readable manifest: `reports/preingame_annotations_g1casta1_20260518.json`
- Individual cards: `diagnostics/captures/current/preingame_annotations_g1casta1_20260518/`

Gunbarrel and front-end capture evidence:

- `diagnostics/captures/contact_sheets/g1casta1_full_front_hardware_cycled_20260518.jpg`
- `diagnostics/captures/contact_sheets/g1casta1_gunbarrel_detail_20260518.jpg`
- `diagnostics/captures/contact_sheets/g1casta1_title_transition_20260518.jpg`

Build reports:

- `reports/tnd480i_g1casta1_gunbarrel_asset_transplant_20260518.json`
- `reports/tnd6480i_g1casta1_bps_manifest.json`

## Current Read

The strobe-producing forced briefing route is rejected and should not be used as a basis for more ROM work. The safe current candidate is `g1casta1`.

Pass or likely-pass:

- Gameplay path inherited from `g1castz1`; user previously reported all levels boot, Bazaar/Labs look fine, pause menu looks fine, bullets UI is good.
- Gunbarrel visual composition is much closer to GE480i after the asset transplant; the offset/second aperture is gone.
- File select, mode select, and difficulty pages are usable and visually close enough to defer broad changes.

Still needs work or proof:

- Mission-select labels need a targeted alignment pass against the GE480i film-caption bands while preserving TND's reduced mission count and red-folder style.
- Briefing, Moneypenny, and Primary Objectives need a safe current capture route. The forced route caused strobing, so do not judge or patch these from that route.
- Classification screen needs a final safe-area check, but it is lower priority than mission select and objective pages.
- Gunbarrel cadence still needs a live timing check against stock TND64 and GE480i, even though composition is now much better.

## Rejected Candidates

- `g1mtabge4btn0a`: rejected. Forced briefing route caused strobing.
- `g1castm2`: rejected. Mission labels moved into the wrong filmstrip/perforation band.
- `g1castk1`: rejected. Draw-target-only gunbarrel edit did not remove the large offset aperture.
- `g1castgb1`: rejected. Slow/post-blood gunbarrel combo worsened the early sweep.
- `g1castslow1`: diagnostic only. It helped isolate timing/shape but did not solve the aperture composition.

## Next Work Order

1. Keep `g1casta1` as the safety baseline.
2. Do not patch from the rejected forced briefing/strobe route.
3. Fix mission-select label placement with a small table-only or callsite-only change, then hardware-capture that one screen before judging.
4. Build a safe route or request manual help for Briefing, Moneypenny, and Objectives; add those current captures to the atlas.
5. Only after those pass, revisit classification and final gunbarrel cadence.
