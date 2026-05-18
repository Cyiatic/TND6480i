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

## Raw Menu Table Follow-up

Follow-up raw 1172 table probes were built on top of stable `t90texstk`:

- `txmtabx`: GE480i mission table X values only, raw `0xA240-0xA254`.
- `txmtaby`: GE480i mission table Y values only, raw `0xA254-0xA264`.
- `txmtabxy`: GE480i mission table X/Y values, raw `0xA240-0xA264`.
- `txmrawa`: GE480i menu/display table A, raw `0x9C3C-0x9D24`.
- `txmrawab`: GE480i table A plus mission table B.

Hardware route captures show these are not promotion-ready. `txmrawa` leaves file-select and mode-select visually stock-like, while mission-select is pushed into a worse lower-page alignment. `txmtabxy` changes mission cursor/table positioning but does not solve dossier scale/detail. `txmrawab` is rejected as a broad table transplant until it can be decomposed further.

Comparison artifact:

- `diagnostics/captures/contact_sheets/dossier_raw_menu_table_rejects_20260518/sheet.jpg`
- `reports/dossier_raw_menu_table_rejects_20260518.json`

Interpretation: the GE480i raw menu tables are not the missing "make dossier hi-res" switch by themselves. The next useful investigation is the draw path for the dossier texture/font/background composition itself: `frontSetupMenuBackground`, folder/paper sprite draw parameters, and the page-specific text rectangle setup, with small probes that alter one visual layer at a time.

## Hardware Follow-up: Drawpath and Front Gate Probes

After the workflow correction, the next candidates were not accepted or rejected from emulator-only output. Each useful candidate was uploaded to SC64, cold-cycle captured from GV-USB2, and compared against the existing GE480i reference/current `t90texstk` dossier matrix.

New comparison artifacts:

- `diagnostics/captures/contact_sheets/dossier_drawpath_candidate_matrix_20260518/sheet.jpg`
- `diagnostics/captures/contact_sheets/dossier_mode_drawpath_split_matrix_20260518/sheet.jpg`
- `diagnostics/captures/contact_sheets/dossier_mission_drawpath_split_matrix_20260518/sheet.jpg`
- `diagnostics/captures/contact_sheets/dossier_front_gate_file_matrix_20260518/sheet.jpg`
- `diagnostics/captures/contact_sheets/dossier_force0_matrix_20260518/sheet.jpg`
- `diagnostics/captures/contact_sheets/dossier_force0_layout_matrix_20260518/sheet.jpg`

Drawpath result:

- `txdossierdraw2`: rejected. Hardware capture shows missing mode-select option text and no GE480i-scale match on mission select.
- `txmodepos2`: rejected as a standalone overlay. It reproduces the mode-select text disappearance, confirming the corrected GE mode-position constants are not safe on stock-scale `t90texstk`.
- `txmissionfull` / `txmissionhelper`: not promotable. They nudge mission filmstrip placement, but they do not solve scale/detail.

Front/menu gate result:

- `txskipfb`, `txfrontz`, and `txzgate`: no useful file-select scale change versus current `t90texstk`.
- `txforce0`: important diagnostic only. Forcing the front/menu table index at `0x4F1B8` to zero moves the dossier into a smaller scale class closer to the GE480i reference, but it leaves an uncleared gray lower region and breaks mode text placement.
- `force0+filefull`, `force0+modepos2`, and `force0+missionfull`: captured on hardware and compared. `force0+modepos2` restores visible mode option text in the smaller scale class, but the overall page composition is still not promotable. File and mission remain mismatched and the lower clear/background issue persists.

Interpretation: the next promising target is not another blind GE coordinate transplant. The useful signal is around the front/menu table selection path at `0x4F1B8` and the table-driven `viSetAspect`/`viSetXY`/`viSetBuf` sequence immediately after it. Future work should decompose that table path and the associated clear/background dimensions so the dossier can use the correct 480i-scale composition without the gray lower-region corruption.

## Force0 + Raw Menu Table Follow-up

Following the hardware-gated workflow, `txforce0` was combined with the raw GE480i 1172 menu table candidates and captured on the N64 before judgment:

- `fotxmrawa`: `txforce0` plus raw table A (`0x9C3C-0x9D24`).
- `fotxmrawab`: `txforce0` plus raw table A and mission table B (`0x9C3C-0x9D24`, `0xA240-0xA264`).

New comparison artifacts:

- `diagnostics/captures/contact_sheets/dossier_force0_raw_menu_pair_matrix_20260518/sheet.jpg`
- `reports/dossier_force0_raw_menu_pair_matrix_20260518.json`
- `reports/tnd480i_txforce0_raw_menu_table_candidates_20260518.json`

Result:

- `force0+rawA` is rejected. File select and mode select still do not match GE480i scale/composition, and the lower gray/background corruption remains.
- `force0+rawAB` nudges mission select but does not solve the page family. It should not be promoted without a page-aware mechanism, because the same global low-res path breaks file/mode presentation.

Interpretation: forcing the menu path globally is the wrong final shape. The useful signal is that the mission page can be pushed toward the GE480i scale class, but file and mode need their own composition/background handling. The next probe should not be another global `screen_size = 0`; it should target either the per-page setup before `menu_init` or the background/folder draw dimensions after `frontSetupMenuBackground`.

## Table1 + Skip-Menu-FB Follow-up

New useful probe family:

- `txdim1skip`: stable `t90texstk` plus `0x4F35C = 0x028001E0` and `0x4F1C4 = 0x10000003`.
- `t90doss1`: `txdim1skip` plus file-select GE enhanced coordinates and mode-select GE enhanced coordinates.
- `t90doss1my16`: `t90doss1` plus mode-select vertical constants moved up 16 units.

Important correction: `txdim1` and `txdim1buf` black-screened, and `txskipfb` alone did not visibly change scale. The combined `table1=640x480 + skip menu framebuffer swap` path had not been tested in the previous matrix. Hardware capture shows that this combination boots to routed file/mode/mission pages, so the black-screen was caused by widening table1 while still taking the old menu-framebuffer swap path.

New artifacts:

- `diagnostics/captures/contact_sheets/dossier_txdim1skip_vs_force0_matrix_20260518/sheet.jpg`
- `diagnostics/captures/contact_sheets/dossier_d1s_file_matrix_20260518/sheet.jpg`
- `diagnostics/captures/contact_sheets/dossier_d1smp_mode_matrix_20260518/sheet.jpg`
- `diagnostics/captures/contact_sheets/dossier_t90doss1_mode_y16_matrix_20260518/sheet.jpg`
- `diagnostics/captures/contact_sheets/d1smfauto07_mission_hardware_20260518.jpg`
- `artifacts/generated/t90doss1.z64`
- `artifacts/generated/t90doss1my16.z64`
- `artifacts/generated/TND6480i_t90doss1_from_baseline_tnd.bps`
- `artifacts/generated/TND6480i_t90doss1my16_from_baseline_tnd.bps`

Results:

- `txdim1skip` is a better diagnostic than `txforce0`: it enters the 640x480 table1 path without the earlier black-screen, and without relying on a global forced `screen_size = 0`.
- `d1stxfilefull` is useful on top of `txdim1skip`: file labels move back near the bottom like GE enhanced, while retaining TND red folder styling.
- `d1stxmodepos2` is useful on top of `txdim1skip`: mode option text becomes visible again and lands closer to GE enhanced spacing.
- `t90doss1my16` improves mode-select alignment over `t90doss1` by moving only the mode vertical constants up 16 units.
- `d1stxmissionfull` is rejected for now: it nudges the filmstrip toward the edge/top and is not an improvement over leaving TND mission select on the `txdim1skip` layout.
- `J_front_layout_4aaa_480i` on top of the improved file page did not visibly fix the remaining background coverage/alignment issue.
- `J_front_buffer_sizes_480i` on top of `t90doss1my16` did not visibly fix the remaining file-select background coverage issue in the hardware file route.

Current best dossier probe is `t90doss1my16`, not a promoted final patch. It is appropriate for manual front-end testing; if gameplay stability is the only priority, use the prior `t90texstk` baseline.

## File-Select Blitter Split and Mode Follow-Up

The next hardware pass isolated the file-select backdrop clipping to a single shared-blitter texture-width word:

- Global `dmyrw1`: `0x4FDFC = 0x3C0AE49F` fixes file-select backdrop coverage, but it is too broad because the same shared blitter is also used by title/gunbarrel paths.
- `dmywrect` also fixes coverage, but introduces right-side vertical striping and worse intro artifacts.
- `dmywtile` does not fix the file-select backdrop by itself.

Promotable shape is callsite-specific, not global. `dmyfbrw1` clones the wrapper/blitter into the known cave at `0x4F498`, applies only the `rw1` word to the cloned blitter, and routes only the file-select callsite at `0x41030` to the clone. Hardware evidence:

- `diagnostics/captures/contact_sheets/dmyfbrw1auto05_file_hardware_20260518.jpg`
- `diagnostics/captures/contact_sheets/dossier_dmyfbrw1_file_matrix_20260518/sheet.jpg`
- `reports/tnd480i_dmyfbrw1_callsite_blitter_20260518.json`

Result: the file-select gray backdrop now covers the full page while retaining TND red folders and bottom labels/icons.

Mode select was then moved another 16 units up from `t90doss1my16`, producing `dfbmy32`. This better matches the GE enhanced mode-option text block:

- `diagnostics/captures/contact_sheets/dossier_dfbmy32_mode_matrix_20260518/sheet.jpg`
- `reports/tnd480i_dfbmy32_mode_y_candidate_20260518.json`

The direct mode-route capture does not initialize the live menu cursor, so it cannot prove cursor placement. Source comparison shows the GE480i mode cursor X constant (`183.0`) is wrong for TND's red dossier layout after the text move. `dfbcurx` restores only TND's stock cursor X constant (`0x42338 = 0x3C0142FC`) while keeping the enhanced Y/text alignment. Manual file-select-to-mode navigation should verify the reticle lands beside option 1.

Current best dossier candidate:

- `artifacts/generated/dfbcurx.z64`
- BPS: `artifacts/generated/TND6480i_dfbcurx_from_baseline_tnd.bps`
- Analogue copy: `artifacts/analogue_test/DFBCURX.Z64` with matching `.SAV`/`.EEP`
- Restore confirmation: `diagnostics/captures/contact_sheets/dfbcurx_restore_confirm_20260518.jpg`
