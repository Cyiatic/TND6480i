# Analogue Test Pack

Use these as short-name ROM/save pairs for Analogue or flashcart comparison.

- `TNDVIABL.Z64` / `TNDVIABL.SAV`: same as `t8040viewge`; current viable gameplay baseline. All levels boot in user testing, but performance is now suspect.
- `TNDCAMGE.Z64` / `TNDCAMGE.SAV`: previous `t8040camge` baseline. Same all-level boot breakthrough, before the added normal gameplay viewport height/top change.
- `TND8040.Z64` / `TND8040.SAV`: lower-level `tnd8040` control before the GE camera/view follow-up constants.
- `TND58.Z64` / `TND58.SAV`: older `tlbpages58` fallback/control. Useful for performance comparison, but expected to have older level-load/rendering issues.

If all four are similarly slow in Wreck/Printworks, the shared 640-wide/480-high render/z-buffer path is the likely performance bottleneck. If only `TNDVIABL` is much slower, focus on the later viewport constants.

The `TNDZ*` ROMs are rejected performance canaries built from current `t8040viewge`, not final visual candidates:

- `TNDZ360.Z64` / `TNDZ360.SAV`: keeps 640-wide depth rows but lowers tested stage depth heights to 360. Test this first.
- `TNDZ640.Z64` / `TNDZ640.SAV`: keeps 640-wide rows but restores stock-ish heights: resolution 330, single-player 240, split 120.
- `TNDZSTK.Z64` / `TNDZSTK.SAV`: restores the stock z/depth allocation footprint: 440x330 and 320x240/120.

User feedback: each `TNDZ*` ROM got progressively worse and reintroduced the Bazaar-style blue rendering failure, so do not use them as the next base.

- `TNDLOWI.Z64` / `TNDLOWI.SAV`: diagnostic control built from `t8040viewge`. It keeps the current all-level-boot 480i VI/framebuffer plumbing, but restores gameplay internal render, viewport, and z/depth dimensions together to stock-sized values. This is not a final 480i visual candidate. Compare Wreck/Printworks speed against `TNDVIABL`; if speed recovers without blue rendering, the slowdown is the true high internal render path. If it is still slow, look below gameplay dimensions at VI/framebuffer/RDP state.
