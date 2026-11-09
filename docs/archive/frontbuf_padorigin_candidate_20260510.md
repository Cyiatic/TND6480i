# 2026-05-10 Frontbuf Pad-Origin Candidate

Current hardware-loaded candidate:

`artifacts/generated/TND64_480i_frontbuf_gunbarrel_padorigin_gameplayxy_tnddefaultwidthheight480i_virtualfb_reserve58000_core_no_menu.z64`

Build profile:

`split8030_8076_all_dim0_frontbuf_title640asset_gameplayxy_tnddefaultwidthheight480i_virtualfb`

Asset mode:

`pad-origin`

ROM identity:

- MD5: `8595e4f1416fdca1bf96ad86c8907d6f`
- N64 CRC: `2FB6A3F7 556AA840`
- Build report: `reports/tnd480i_frontbuf_gunbarrel_padorigin_gameplayxy_tnddefaultwidthheight480i_virtualfb_reserve58000_core_no_menu_report.json`
- Hardware startup capture: `diagnostics/captures/videos/frontbuf_padorigin_noskip_offupload_poweron_startup_20260510.mkv`
- Hardware keyframes: `diagnostics/captures/frontbuf_padorigin_noskip_keyframes_20260510/`
- Cadence report: `reports/capture_cadence_analysis_frontbuf_padorigin_noskip_vs_refs_20260510.json`

Why this branch replaced the previous frontbuf asset640 candidate:

- The previous resized 640x430 source moved TND's own gunbarrel aperture away from the Bond aperture, producing a second barrel / swiss-cheese look.
- `pad-origin` keeps the original 440x299 TND gunbarrel art inside a 640x430 RLE canvas, so the 640x430 title blitter path is still exercised without stretching the source art.
- Hardware frame `frame_035s.png` shows the obvious second barrel removed.
- The file-select backdrop call is restored in this no-skip variant, so it should no longer intentionally black out the folder background.

Known open items for controller-side hardware testing:

- Check save slots 1, 2, 3, and 4. The restored file-select backdrop may reintroduce the old slot-freeze behavior; this is the first thing to classify.
- Check whether the main folder screen background is visible instead of black.
- Check gunbarrel visual quality and cadence on the CRT/capture path.
- Check level intro and gameplay for the known blue skybox/world-band issue.
- Check pause/watch text against the enhanced480i reference.

Fallbacks already built:

- `TND64_480i_frontbuf_gunbarrel_padorigin_skipfileselect_gameplayxy_tnddefaultwidthheight480i_virtualfb_reserve58000_core_no_menu.z64`
  - Same padded gunbarrel source, but keeps the black-folder skip that made all saves work in the previous candidate.
- `TND64_480i_frontbuf_titletarget_stocksource_gameplayxy_tnddefaultwidth480i_virtualfb_reserve58000_core_no_menu.z64`
  - Cleaner emulator gameplay/pause behavior, but likely loses the GE480-like gunbarrel workload because it does not use the appended 640x430 RLE stride/row-loop path.
