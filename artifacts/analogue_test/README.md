# Analogue Test Pack

Use these as short-name ROM/save pairs for Analogue or flashcart comparison.

- `TNDVIABL.Z64` / `TNDVIABL.SAV`: same as `t8040viewge`; current viable gameplay baseline. All levels boot in user testing, but performance is now suspect.
- `TNDCAMGE.Z64` / `TNDCAMGE.SAV`: previous `t8040camge` baseline. Same all-level boot breakthrough, before the added normal gameplay viewport height/top change.
- `TND8040.Z64` / `TND8040.SAV`: lower-level `tnd8040` control before the GE camera/view follow-up constants.
- `TND58.Z64` / `TND58.SAV`: older `tlbpages58` fallback/control. Useful for performance comparison, but expected to have older level-load/rendering issues.

If all four are similarly slow in Wreck/Printworks, the slowdown is shared below the later viewport constants.

The `TNDZ*` ROMs are rejected performance canaries built from current `t8040viewge`, not final visual candidates:

- `TNDZ360.Z64` / `TNDZ360.SAV`: keeps 640-wide depth rows but lowers tested stage depth heights to 360. Test this first.
- `TNDZ640.Z64` / `TNDZ640.SAV`: keeps 640-wide rows but restores stock-ish heights: resolution 330, single-player 240, split 120.
- `TNDZSTK.Z64` / `TNDZSTK.SAV`: restores the stock z/depth allocation footprint: 440x330 and 320x240/120.

User feedback: each `TNDZ*` ROM got progressively worse and reintroduced the Bazaar-style blue rendering failure, so do not use them as the next base.

- `TNDLOWI.Z64` / `TNDLOWI.SAV`: diagnostic control built from `t8040viewge`. It keeps the current all-level-boot 480i VI/framebuffer plumbing, but restores gameplay internal render, viewport, and z/depth dimensions together to stock-sized values. This is not a final 480i visual candidate. User feedback on direct-stage Wreck: still slow, so the current bottleneck is below gameplay dimensions.

Current performance canaries:

- `TND90GE.Z64` / `TND90GE.SAV`: current best test candidate. It keeps the 90-page TLB cache relocated below `fb1`, moves `fb0` to `0x80400000`, and keeps the GE 480i camera/viewport constants from `t8040viewge`. Direct Wreck hardware cadence matches the old good TND6480i recording instead of the slow `tnd58/t8040` line, and direct probes for Party, City, The End, Hotel, Volcano, Tower, and Boat reached rendered scenes.
- `T90FB.Z64` / `T90FB.SAV`: minimal sibling to `TND90GE`; same fast 90-page relocated TLB cache plus `fb0=0x80400000`, but without the later GE camera/viewport constants. Use only if `TND90GE` has a viewport-specific regression.
- `TNDBLIT.Z64` / `TNDBLIT.SAV`: `t8040viewge` with the shared title/sniper blitter geometry cluster restored to stock TND. Direct-stage Wreck is the current SC64 canary and visually lines up with the stock Wreck control better than `TNDLOWI`.
- `TNDBUF.Z64` / `TNDBUF.SAV`: `t8040viewge` with only front `viSetBuf` width/height restored to stock. Test only if `TNDBLIT` does not explain the slowdown.
- `TNDBOTH.Z64` / `TNDBOTH.SAV`: combined `TNDBLIT` + `TNDBUF`. Do not test before the isolated canaries are classified.
