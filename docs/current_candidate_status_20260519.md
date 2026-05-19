# Current Candidate Status - 2026-05-19

Current best hardware candidate:

- ROM: `artifacts/generated/g1hiftr1.z64`
- Save: `artifacts/generated/g1hiftr1.sav`
- EEPROM mirror: `artifacts/generated/g1hiftr1.eep`
- BPS: `artifacts/generated/TND6480i_g1hiftr1_from_baseline_tnd.bps`
- ROM MD5: `7fc7fcec15e510d573f13aa960253007`
- Patch MD5: `7a9146620e180b51cc1d562275358cd8`

Convenience copies:

- `artifacts/generated/TND6480i_current_g1hiftr1.z64`
- `artifacts/generated/TND6480i_current_g1hiftr1.sav`
- `artifacts/generated/TND6480i_current_g1hiftr1.eep`
- `artifacts/generated/TND6480i_current_g1hiftr1_from_baseline_tnd.bps`

`g1hiftr1` is `g1hlim1` plus the remaining GE480i display-cast words:

- `0x4D040`, `0x4D044`, `0x4D11C`, `0x4D120`: display-cast interface/model centering.
- `0x4E914`, `0x4E918`, `0x4EA44`, `0x4EA48`: display-cast scissor/fade-fill rectangles.
- `0x4EB20`, `0x4EB38`, `0x4EB40`, `0x4EB58`: cast-credit text center/Y constants.

This keeps the `g1hlim1` gameplay, dossier, file-select, mission-select, and difficulty/checkmark fixes intact while moving the opening cast credits onto the full GE480i display-cast coordinate family.

## Hardware Evidence

Primary `g1hiftr1` startup/front captures:

- `diagnostics/captures/videos/g1hiftr1_front_textrect_hardware_cycled_20260519.mp4`
- `diagnostics/captures/contact_sheets/g1hiftr1_full_front_hardware_cycled_20260519.jpg`
- `diagnostics/captures/contact_sheets/g1hiftr1_opening_detail_20260519.jpg`

Display-cast probe captures:

- `diagnostics/captures/contact_sheets/g1hrect1_opening_detail_20260519.jpg`
- `diagnostics/captures/contact_sheets/g1htxt1_opening_detail_20260519.jpg`
- `diagnostics/captures/contact_sheets/g1htxr1_opening_detail_20260519.jpg`
- `diagnostics/captures/contact_sheets/g1hift1_opening_detail_20260519.jpg`
- `diagnostics/captures/contact_sheets/g1hiftr1_opening_detail_20260519.jpg`

`g1hiftr1` route sanity captures:

- File select: `diagnostics/captures/contact_sheets/htrauto05_hardware_cycled_20260519.jpg`
- Mode select: `diagnostics/captures/contact_sheets/htrauto06_hardware_cycled_20260519.jpg`
- Mission select: `diagnostics/captures/contact_sheets/htrauto07_hardware_cycled_20260519.jpg`
- Difficulty/checkmarks: `diagnostics/captures/contact_sheets/htrbtn08_hardware_cycled_20260519.jpg`
- Forced briefing route diagnostic: `diagnostics/captures/contact_sheets/htrbtn0a_hardware_cycled_20260519.jpg`

Earlier `g1hlim1` evidence still applies for the non-cast pages:

- `diagnostics/captures/current/preingame_issue_cards_g1hlim1_20260519.jpg`
- `diagnostics/captures/contact_sheets/hlmauto05_file_hardware_cycled_20260519.jpg`
- `diagnostics/captures/contact_sheets/hlmauto06_mode_hardware_cycled_20260519.jpg`
- `diagnostics/captures/contact_sheets/hlmauto07_mission_hardware_cycled_20260518.jpg`
- `diagnostics/captures/contact_sheets/hlmbtn08_difficulty_hardware_cycled_20260518.jpg`

## Current Read

Pass or likely-pass:

- Gameplay path remains inherited from `g1hlim1`; this pass touched only display-cast/front-end words.
- File select, mode select, and mission select route captures are unchanged in layout family from `g1hlim1`.
- Difficulty red checkmarks are aligned with the rows in the forced-accept route capture.
- Opening cast credits now use the full GE480i display-cast coordinate set instead of the mixed stock/480i set in `g1hlim1`.

Still needs work or manual proof:

- Normal-controller verification of file select -> mode select -> mission select -> difficulty -> briefing is still the cleanest proof for live cursor/hitbox placement.
- The forced briefing/objectives route can be used diagnostically, but it is still not as trustworthy as manual navigation because it bypasses normal state setup.
- Title/gunbarrel/title-card cadence should be judged against motion, not stills. The red title/gunbarrel overlay is present in stock TND64 too, so it is not by itself a 480i regression.
- Final gameplay smoke on real hardware is still required after any promoted front-end candidate, even though `g1hiftr1` does not alter gameplay code.

## Rejected Or Diagnostic

- `g1hczh1`, `g1hczw1`: simple display-cast z-buffer dimension reverts; both reintroduced worse striping/cropping.
- `g1hrect1`: rectangle-only display-cast probe; mostly neutral and not enough by itself.
- `g1htxt1`: text-only display-cast probe; useful, but does not address the model/camera coordinate mismatch.
- `g1htxr1`: text plus rectangles; useful but still leaves model/camera on stock display-cast centers.
- `g1hift1`: center plus text; useful, but the all-remaining `g1hiftr1` is the cleaner GE480i display-cast transplant.
- `g1hlimif1`, `g1hlimifrect1`: older center/rectangle probes without the text constants; superseded by `g1hiftr1`.

## Next Work Order

1. Use `g1hiftr1` as the active candidate for manual front-end testing.
2. Have the user verify normal controller flow through file select, mode select, mission select, difficulty, briefing, and a quick gameplay smoke.
3. If the dossier backdrop or live cursor is still visually off in normal navigation, patch those pages separately; do not change the display-cast set again unless motion evidence shows a new regression.
4. Keep the gameplay/level code untouched until the front-end-only candidate passes a manual smoke test.
