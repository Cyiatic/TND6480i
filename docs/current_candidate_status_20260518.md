# Current Candidate Status - 2026-05-18

Current best hardware candidate:

- ROM: `artifacts/generated/g1class1.z64`
- Save: `artifacts/generated/g1class1.sav`
- BPS: `artifacts/generated/TND6480i_g1class1_from_baseline_tnd.bps`
- ROM MD5: `77ecf1aa6fdd0c5bee31198991162a26`
- Patch MD5: `5209be40077fae2f92b9b245fc71e99b`

`g1class1` is `g1casta1` plus the GE480i legal/classification page geometry table at raw 1172 offset `0x9C3C`. The patch copies only the first 16 bytes of each of the 12 legal table records, preserving TND64 text IDs and leaving gameplay, level loading, pause menu, HUD, dossier tables, gunbarrel assets, and title assets untouched.

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

Build reports:

- `reports/tnd480i_g1casta1_gunbarrel_asset_transplant_20260518.json`
- `reports/tnd6480i_g1casta1_bps_manifest.json`
- `reports/tnd480i_g1class1_legal_classification_20260518.json`
- `reports/tnd6480i_g1class1_bps_manifest.json`

## Current Read

The strobe-producing forced briefing route is rejected and should not be used as a basis for more ROM work. The safe current candidate is `g1class1`.

Pass or likely-pass:

- Gameplay path inherited from `g1castz1`; user previously reported all levels boot, Bazaar/Labs look fine, pause menu looks fine, bullets UI is good.
- Classification board geometry now follows the GE480i legal-page spread while preserving TND wording/art.
- Gunbarrel visual composition is much closer to GE480i after the asset transplant; the offset/second aperture is gone.

Still needs work or proof:

- File select still needs a GE480i-aligned dossier/background envelope check. The current file labels/icons are visible, but the right-side background/bleed is not accepted yet.
- Mode select must be judged from normal navigation, not only the direct route, because direct routes can bypass live cursor initialization.
- Mission-select labels need a targeted alignment pass against the GE480i film-caption bands while preserving TND's reduced mission count and red-folder style.
- Difficulty select rows/paper bounds still need a page-specific alignment pass.
- Briefing, Moneypenny, and Primary Objectives need a safe current capture route. The forced route caused strobing, so do not judge or patch these from that route.
- Gunbarrel cadence still needs a live timing check against stock TND64 and GE480i, even though composition is now much better.

## Rejected Candidates

- `g1mtabge4btn0a`: rejected. Forced briefing route caused strobing.
- `g1castm2`: rejected. Mission labels moved into the wrong filmstrip/perforation band.
- `g1castk1`: rejected. Draw-target-only gunbarrel edit did not remove the large offset aperture.
- `g1castgb1`: rejected. Slow/post-blood gunbarrel combo worsened the early sweep.
- `g1castslow1`: diagnostic only. It helped isolate timing/shape but did not solve the aperture composition.

## Next Work Order

1. Keep `g1class1` as the safety baseline.
2. Do not patch from the rejected forced briefing/strobe route.
3. Fix dossier/front-end screens one page at a time from the strict issue atlas, with a comparison card after each hardware capture.
4. Build a safe route or request manual help for Briefing, Moneypenny, and Objectives; add those current captures to the atlas.
5. Only after dossier pages pass, revisit opening credits/logos and final gunbarrel cadence.
