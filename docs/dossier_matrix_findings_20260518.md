# Dossier Matrix Findings - 2026-05-18

Current stable full candidate remains:

- `artifacts/generated/t90texstk.z64`
- MD5: `9a3a600850585864be1fff8640548165`

Primary comparison matrix:

- `diagnostics/captures/contact_sheets/dossier_candidate_matrix_20260518/sheet.jpg`
- `reports/dossier_candidate_matrix_20260518.json`

Complete dossier page matrix:

- `diagnostics/captures/contact_sheets/dossier_page_matrix_20260518/sheet.jpg`
- `reports/dossier_page_matrix_20260518.json`

Reference matrix from existing recordings:

- `diagnostics/captures/contact_sheets/dossier_matrix_ge_tnd_old_current_20260518/sheet.jpg`
- `reports/dossier_matrix_ge_tnd_old_current_20260518.json`

## Summary

The old TND6480i recording and current `t90texstk` front-end/dossier pages are still visually stock-sized compared with the GE480i dossier reference. The stable gameplay candidate should not be disturbed for this work; the issue is front-end/dossier composition.

The complete dossier page matrix rows are file select, mode select, mission select, difficulty select, and briefing. Columns are GE480i reference, stock TND64, the old TND6480i recording, and current `t90texstk` direct-console captures where clean direct routes exist. Current direct captures are available for file/mode/mission only; difficulty and briefing are intentionally blank because direct menu IDs lack the required state and previously produced title/black captures.

The direct page-route captures are useful because they prove the GE480i coordinate transplants are not promotion-ready:

- `txfilefull` / `tffauto05`: file-select GE480i file-page words hide the bottom labels/icons.
- `txfileplace` / `tfpauto05`: keeps `Select File` and copy/erase icons, but loses `Copy`/`Erase` text.
- `txfileicons` / `tfiauto05`: keeps `Copy`/`Erase` text, but loses `Select File` and the icons.
- `txfsg2` / `fg2auto05`: scale group 2 hides `Select File`; do not carry it blindly.
- `txfsg0` / `fg0auto05`: keeps `Select File`, `Copy`, `Erase`, and erase icon, but copy icon is not right.
- `txfsg1` / `fg1auto05`: keeps `Select File`, `Copy`, `Erase`, and copy icon, but erase icon is not right.
- `txfsg01` / `f01auto05`: keeps the labels, but loses copy/erase icons.
- `txfp0g01` / `fpqauto05`: regresses to mostly `Select File` only.

For mode/mission:

- `txmode06` / `tm6auto06`: changes the mode page somewhat but does not make it match GE480i scale/detail.
- `txm07draw` / `tm7auto07`: shifts the mission select filmstrip/text, but not in a promotable way.
- `txmstxt` / `tmtauto07`: mission text-only shift is not a clear win and is consistent with earlier manual rejection of the mission text offset group.

## Important Interpretation

The file-select offsets at `0x419F0-0x41C48` are not general dossier page scale controls. They map to the file-select copy/erase/select icon positions in `constructor_menu05_fileselect`. The earlier function-range label made them look like a broader menu page scale area, but source comparison shows they are file-page icon constants.

`t90texstk` already has the expanded menu width/height and front `viSetXY`/`viSetBuf` 640x480 words applied:

- `J_expanded_menu_resolution_480i`: already matches GE480i values.
- `J_front_visetxybuf_480i`: already matches GE480i values.

The remaining mismatch is therefore not solved by blindly adding high coordinate constants. The high-Y GE file-select constants push TND labels/icons offscreen or into unusable positions. The next pass should classify the relevant source-level controls and avoid broad coordinate transplants.

## Next Technical Work

1. Keep `t90texstk` as the gameplay/playability baseline.
2. Build any dossier candidate as a narrow overlay on `t90texstk`.
3. For file select, do not promote `txfilefull`, `txfileplace`, `txfileicons`, `txfsg01`, or `txfp0g01`.
4. Use the GoldenEye `front.c` mapping to split file-select X and Y constants separately; the high-Y values are the likely cause of vanished labels/icons.
5. For mode/mission, classify `frontSetupMenuBackground`, cursor tables, and per-page text rectangles separately before another hardware upload.
6. Difficulty/briefing need a better direct-route state setup; raw direct menu IDs still do not provide reliable standalone pages.
