# Current Candidate Status - 2026-05-18

Current best hardware candidate:

- ROM: `artifacts/generated/g1diff2.z64`
- Save: `artifacts/generated/g1diff2.sav`
- BPS: `artifacts/generated/TND6480i_g1diff2_from_baseline_tnd.bps`
- ROM MD5: `7dcf2cf0ea0ab9005cc20f5b864bb84f`
- Patch MD5: `91c3969bd82bc2246c43a3b63eff794b`

`g1diff2` is `g1class1` plus two narrow dossier fixes: GE480i mission-select table B at raw 1172 offset `0xA240` with the matching g1mtab mission-label table, and the complete GE480i difficulty-select constructor/interface word deltas in ROM range `0x43300-0x43D00`. It leaves gameplay, level loading, pause menu, HUD, file/mode dossier setup, classification, gunbarrel assets, and title assets untouched.

## Hardware Evidence

Primary per-screen acceptance atlas:

- `diagnostics/captures/current/preingame_annotations_g1casta1_20260518.jpg`
- Machine-readable manifest: `reports/preingame_annotations_g1casta1_20260518.json`
- Individual cards: `diagnostics/captures/current/preingame_annotations_g1casta1_20260518/`
- Strict issue atlas: `diagnostics/captures/current/preingame_issue_cards_g1casta1_20260518.jpg`
- Strict issue manifest: `reports/preingame_issue_cards_g1casta1_20260518.json`

Gunbarrel and front-end capture evidence:

- `diagnostics/captures/contact_sheets/g1casta1_full_front_hardware_cycled_20260518.jpg`
- `diagnostics/captures/contact_sheets/g1casta1_gunbarrel_detail_20260518.jpg`
- `diagnostics/captures/contact_sheets/g1casta1_title_transition_20260518.jpg`
- Classification fix card: `diagnostics/captures/current/g1class1_classification_fix_card_20260518.jpg`
- Classification startup capture: `diagnostics/captures/contact_sheets/g1class1_startup_cycle_20260518.jpg`
- Mission select fix card: `diagnostics/captures/current/g1gridbg1_mission_fix_card_20260518.jpg`
- Difficulty select fix card: `diagnostics/captures/current/g1diff2_difficulty_fix_card_20260518.jpg`

Build reports:

- `reports/tnd480i_g1casta1_gunbarrel_asset_transplant_20260518.json`
- `reports/tnd6480i_g1casta1_bps_manifest.json`
- `reports/tnd480i_g1class1_legal_classification_20260518.json`
- `reports/tnd6480i_g1class1_bps_manifest.json`
- `reports/tnd480i_g1gridbg1_mission_grid_20260518.json`
- `reports/tnd6480i_g1gridbg1_bps_manifest.json`
- `reports/tnd480i_g1diff2_difficulty_20260518.json`
- `reports/tnd6480i_g1diff2_bps_manifest.json`

## Current Read

The strobe-producing forced briefing route is rejected and should not be used as a basis for more ROM work. The safe current candidate is `g1diff2`.

Pass or likely-pass:

- Gameplay path inherited from `g1castz1`; user previously reported all levels boot, Bazaar/Labs look fine, pause menu looks fine, bullets UI is good.
- Classification board geometry now follows the GE480i legal-page spread while preserving TND wording/art.
- Mission-select labels and cursor grid now use the GE480i table-B spacing while preserving TND's reduced mission count and red-folder style.
- Difficulty-select row block now uses the complete GE480i difficulty constructor/interface deltas; `g1diff1` was rejected because it missed the two difficulty-name X constants and caused overlap.
- Gunbarrel visual composition is much closer to GE480i after the asset transplant; the offset/second aperture is gone.

Still needs work or proof:

- File select still needs a GE480i-aligned dossier/background envelope check. The current file labels/icons are visible, but the right-side background/bleed is not accepted yet.
- Mode select must be judged from normal navigation, not only the direct route, because direct routes can bypass live cursor initialization.
- Briefing, Moneypenny, and Primary Objectives need a safe current capture route. The forced route caused strobing, so do not judge or patch these from that route.
- Gunbarrel cadence still needs a live timing check against stock TND64 and GE480i, even though composition is now much better.

## Rejected Candidates

- `g1mtabge4btn0a`: rejected. Forced briefing route caused strobing.
- `g1diff1`: rejected. It copied most GE480i difficulty row constants but stopped before the two difficulty-name X constants, producing overlapping difficulty labels.
- `g1castm2`: rejected. Mission labels moved into the wrong filmstrip/perforation band.
- `g1castk1`: rejected. Draw-target-only gunbarrel edit did not remove the large offset aperture.
- `g1castgb1`: rejected. Slow/post-blood gunbarrel combo worsened the early sweep.
- `g1castslow1`: diagnostic only. It helped isolate timing/shape but did not solve the aperture composition.

## Next Work Order

1. Keep `g1diff2` as the safety baseline.
2. Do not patch from the rejected forced briefing/strobe route.
3. Fix remaining dossier/front-end screens one page at a time from the strict issue atlas, with a comparison card after each hardware capture.
4. Build a safe route or request manual help for Briefing, Moneypenny, and Objectives; add those current captures to the atlas.
5. Only after dossier pages pass, revisit opening credits/logos and final gunbarrel cadence.
