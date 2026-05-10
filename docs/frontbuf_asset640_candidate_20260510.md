# 2026-05-10 Frontbuf Asset640 Candidate

Current best hardware candidate:

`artifacts/generated/TND64_480i_frontbuf_gunbarrel_asset640_skipfileselect_gameplayxy_tnddefaultwidthheight480i_virtualfb_reserve58000_core_no_menu.z64`

Build profile:

`split8030_8076_all_dim0_frontbuf_title640asset_skipfileselect_gameplayxy_tnddefaultwidthheight480i_virtualfb`

ROM identity:

- MD5: see `reports/tnd480i_frontbuf_gunbarrel_asset640_skipfileselect_gameplayxy_tnddefaultwidthheight480i_virtualfb_reserve58000_core_no_menu_report.json`
- Hardware startup capture: `diagnostics/captures/videos/frontbuf_asset640_skipfileselect_offupload_poweron_startup_20260510.mkv`
- Keyframes: `diagnostics/captures/frontbuf_asset640_skipfileselect_keyframes_20260510/`
- Contact sheet: `diagnostics/captures/contact_sheets/compare_frontbuf_asset_startup_20260510.jpg`

Why this branch is favored:

- The appended 640x430 gunbarrel RLE plus 640-source stride produces GE480-like gunbarrel motion cadence.
- The `frontbuf` split keeps `viSetBuf` at 640x480 without applying the full front-resolution/layout patch set that caused horizontal credit/title striping.
- Hardware motion cadence for the gunbarrel segment is 8.288 updates/sec, close to the GE480 reference at 8.141 and well below stock TND at 10.799.
- Startup credits are much cleaner than `frontres` and `frontlayout`; frame 55 is clean and frame 70 is black rather than horizontally striped.

Known risks / next test:

- Needs human console gameplay validation: save slots 1-4, level intro, first-person gameplay, Bond hand scale, pause/watch text, and smaller GE480-style red aiming reticle.
- `frontbuf` may suppress or delay some later attract/credit visuals compared with stock, but it avoids the severe repeated white-bar corruption.
- The generated ROM is larger than 16 MiB because the 640x430 RLE is appended, so the release patch should use a format that can represent the expanded ROM, not classic IPS.
