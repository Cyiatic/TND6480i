# Current Candidate Status - 2026-05-18

Current best hardware candidate:

- ROM: `artifacts/generated/g1hlim1.z64`
- Save: `artifacts/generated/g1hlim1.sav`
- EEPROM mirror: `artifacts/generated/g1hlim1.eep`
- BPS: `artifacts/generated/TND6480i_g1hlim1_from_baseline_tnd.bps`
- ROM MD5: `47dc8fbeda8c95cb603a87c4c7966ab5`
- Patch MD5: `2e8ea8358096c87ad443486f708fe6ed`

`g1hlim1` is `g1diff3` plus one additional GE480i front/title word:

- `0x46F18: 0x2418014A -> 0x241801E0`
- Meaning: raise the title/menu height limit from stock 330 to 480.

This keeps the already-validated gameplay, dossier, mission-select, difficulty, gunbarrel, and classification work from `g1diff3`, while reducing the obvious lower-screen stale rectangle during the opening cast credits.

## Hardware Evidence

Primary `g1hlim1` startup/front capture:

- `diagnostics/captures/videos/g1hlim1_full_front_hardware_cycled_20260518.mp4`
- `diagnostics/captures/contact_sheets/g1hlim1_full_front_hardware_cycled_20260518.jpg`
- Opening detail: `diagnostics/captures/contact_sheets/g1hlim1_opening_credits_detail_20260518.jpg`
- Probe comparison matrix: `diagnostics/captures/current/g1_front_opening_probe_matrix_20260518.jpg`

Dossier sanity checks after the height-limit change:

- Difficulty/checkmark route: `diagnostics/captures/contact_sheets/hlmbtn08_difficulty_hardware_cycled_20260518.jpg`
- Mission-select route: `diagnostics/captures/contact_sheets/hlmauto07_mission_hardware_cycled_20260518.jpg`

Earlier `g1diff3` evidence still applies:

- Dossier atlas: `diagnostics/captures/current/g1diff3_dossier_atlas_20260518.jpg`
- Difficulty checkmark fix card: `diagnostics/captures/current/g1diff3_difficulty_checkmark_fix_card_20260518.jpg`
- Classification startup: `diagnostics/captures/contact_sheets/g1diff3_full_front_hardware_cycled_20260518.jpg`

## Current Read

Pass or likely-pass:

- Gameplay path inherited from `g1castz1`/`g1diff3`; user previously reported all levels boot, Bazaar/Labs look fine, pause menu looks fine, and bullets UI is good.
- Classification board fits in the higher-resolution front path.
- File select, mode select, mission select, and difficulty select now match the GE480i dossier family closely enough for hardware testing, while preserving TND red folders and the reduced mission count.
- Difficulty red checkmarks are aligned after the `g1diff3` checkmark coordinate fix.
- `g1hlim1` improves the opening credits by raising the stale stock-height front limit without the extra centering/rectangle side effects seen in broader cast probes.

Still needs work or user-driven proof:

- Briefing/objectives need manual console navigation or a safer initialized route; direct no-input and forced briefing routes can black-screen or strobe.
- Opening cast credits are improved but not final-perfect; broader centering/rectangle probes (`g1castif1`, `g1castrect1`, `g1hlimif1`, `g1hlimifrect1`) were diagnostic and not promoted.
- Final gameplay regression pass on real hardware is still useful after any promoted front-end change, even though `g1hlim1` only touches the front/title height limit.

## Rejected Or Diagnostic

- `g1castrect1`: display-cast scissor/fade rectangles only; booted but did not solve the cast-transition artifacts.
- `g1castif1`: display-cast centering only; improved placement but left hard transition leftovers.
- `g1castifrect1`: centering plus rectangles; no clear improvement over simpler probes.
- `g1hlimif1` / `g1hlimifrect1`: height-limit plus centering variants; still showed stray transition fragments and moved cast elements more aggressively than needed.
- `g1hlimfy1`: height-limit plus float/Y constants; safe-looking but no clear advantage over the one-word `g1hlim1`.
- `g1mtabge4btn0a`: rejected. Forced briefing route caused strobing.
- `g1diff1`: rejected. Difficulty labels moved before the two checkmark coordinate words were included.

## Next Work Order

1. Keep `g1hlim1` as the safety baseline.
2. Have the user run a normal gameplay smoke pass when available, especially opening credits, dossier pages, Bazaar/Labs, and one later level.
3. Build or request a safe capture route for Briefing/Objectives before patching those pages further.
4. Avoid further broad cast/display rectangle transplants unless a comparison card shows a clear target.
