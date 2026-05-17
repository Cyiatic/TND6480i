# Analogue Test Pack

Use these as short-name ROM/save pairs for Analogue or flashcart comparison.

- `TNDVIABL.Z64` / `TNDVIABL.SAV`: same as `t8040viewge`; current viable gameplay baseline. All levels boot in user testing, but performance is now suspect.
- `TNDCAMGE.Z64` / `TNDCAMGE.SAV`: previous `t8040camge` baseline. Same all-level boot breakthrough, before the added normal gameplay viewport height/top change.
- `TND8040.Z64` / `TND8040.SAV`: lower-level `tnd8040` control before the GE camera/view follow-up constants.
- `TND58.Z64` / `TND58.SAV`: older `tlbpages58` fallback/control. Useful for performance comparison, but expected to have older level-load/rendering issues.

If all four are similarly slow in Wreck/Printworks, the shared 640-wide/480-high render/z-buffer path is the likely performance bottleneck. If only `TNDVIABL` is much slower, focus on the later viewport constants.
