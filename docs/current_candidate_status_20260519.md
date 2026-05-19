# Current Candidate Status - 2026-05-19

Current best hardware candidate:

- ROM: `artifacts/generated/g1hbrf1.z64`
- Save: `artifacts/generated/g1hbrf1.sav`
- EEPROM mirror: `artifacts/generated/g1hbrf1.eep`
- BPS: `artifacts/generated/TND6480i_g1hbrf1_from_baseline_tnd.bps`
- ROM MD5: `074ccc643853e308aafd0cbccb8302b9`
- Patch MD5: `dd30a377ad16ef27e5df48531cb2d166`

Convenience copies:

- `artifacts/generated/TND6480i_current_g1hbrf1.z64`
- `artifacts/generated/TND6480i_current_g1hbrf1.sav`
- `artifacts/generated/TND6480i_current_g1hbrf1.eep`
- `artifacts/generated/TND6480i_current_g1hbrf1_from_baseline_tnd.bps`

`g1hbrf1` is `g1hct2` plus the GE480i briefing/objective menu and wrap-threshold deltas:

- `0x454E8-0x45604`: briefing/objective text wrap thresholds.
- `0x4A000-0x4C500`: briefing/background/Moneypenny/Q/objectives page geometry.
- 76 changed words total, all isolated to the briefing/objective page family.

`g1hct2` already included:

- The working gameplay/level stability chain from `g1hlim1`.
- GE480i dossier/file/mode/mission/difficulty geometry work.
- Difficulty red checkmark alignment fixes at `0x43D04` and `0x43D0C`.
- Display-cast/cast-credit text and rectangle fixes through `g1hiftr1` plus the remaining second/third credit-row text constants.

## Hardware Evidence

Promoted `g1hbrf1` front boot:

- `diagnostics/captures/videos/g1hbrf1_front_hardware_cycled_20260519.mp4`
- `diagnostics/captures/contact_sheets/g1hbrf1_front_hardware_cycled_20260519.jpg`

Promoted `g1hbrf1` dossier route captures:

- File select: `diagnostics/captures/contact_sheets/brfauto05_hardware_cycled_20260519.jpg`
- Mode select: `diagnostics/captures/contact_sheets/brfauto06_hardware_cycled_20260519.jpg`
- Mission select: `diagnostics/captures/contact_sheets/brfauto07_hardware_cycled_20260519.jpg`
- Difficulty/checkmarks: `diagnostics/captures/contact_sheets/brfbtn08_hardware_cycled_20260519.jpg`

Briefing/objective page captures:

- Objectives: `diagnostics/captures/contact_sheets/brfbtn0c_hardware_cycled_20260519.jpg`
- Background: `diagnostics/captures/contact_sheets/brfbtn0cpg1_hardware_cycled_20260519.jpg`
- M briefing: `diagnostics/captures/contact_sheets/brfbtn0cpg2_hardware_cycled_20260519.jpg`
- Q Branch: `diagnostics/captures/contact_sheets/brfbtn0cpg3_hardware_cycled_20260519.jpg`
- Moneypenny: `diagnostics/captures/contact_sheets/brfbtn0cpg4_hardware_cycled_20260519.jpg`

Current screen-by-screen atlas:

- `diagnostics/captures/current/preingame_issue_cards_g1hbrf1_20260519.jpg`
- `reports/preingame_issue_cards_g1hbrf1_20260519.json`

## Current Read

Pass or likely-pass:

- Gameplay/level stability remains inherited from the previously user-verified good build; `g1hbrf1` touched only front briefing/objective code.
- File select, mode select, mission select, and difficulty pages capture cleanly under `g1hbrf1`.
- Red difficulty completion checks are aligned with their rows in the current route capture.
- Background, M briefing, Q Branch, Moneypenny, and Primary Objectives now render with the high-res dossier geometry instead of the old oversized/stock briefing layout.

Still needs manual proof:

- Normal controller flow through file select -> mode select -> mission select -> difficulty -> briefing, because route probes can bypass live cursor/hitbox setup.
- Final gameplay smoke after `g1hbrf1`, even though the binary changes are not in gameplay/level code.
- Opening cast credits and logo/title cadence should be judged with motion evidence, not single stills.
- File-select wallpaper origin and mission-select caption bands are readable and stable, but should be checked on CRT/console against the GE480i visual target before declaring final polish complete.

## Rejected Or Diagnostic

- `g1hlegal1`: rebuilt the legal/classification stream on top of `g1hbrf1`, but the raw legal table already matched GE480i, so it provides no behavior improvement and should not replace `g1hbrf1`.
- `brfauto05`, `brfauto06`, `brfauto07`, `brfbtn08`, `brfbtn0c`, `brfbtn0cpg1`-`brfbtn0cpg4`: diagnostic route ROMs only, never release candidates.
- `g1hczh1`, `g1hczw1`: display-cast z-buffer dimension reverts; both were worse.
- `g1hrect1`, `g1htxt1`, `g1htxr1`, `g1hift1`: superseded by the full `g1hiftr1`/`g1hct2` display-cast path.

## Next Work Order

1. Use `g1hbrf1` as the active candidate for manual front-end testing.
2. Verify normal controller navigation through the dossier and briefing pages.
3. If normal navigation exposes a cursor/hitbox mismatch, patch that page separately without touching gameplay.
4. If the opening credits still look zoomed or the fade rectangle is visible on CRT, isolate the display-cast model/fade constants next.
