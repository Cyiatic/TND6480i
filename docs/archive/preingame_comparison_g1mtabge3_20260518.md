# TND6480i pre-ingame comparison, g1mtabge3

Current candidate: `artifacts/generated/g1mtabge4.z64`

Comparison matrix: `diagnostics/captures/current/preingame_comparison_matrix_g1mtabge3_20260518.jpg`

Opening credits verification sheet: `diagnostics/captures/current/opening_credits_scale_verification_g1mtabge3_20260518.jpg`

Mission-select follow-up comparison: `diagnostics/captures/current/g1mtabge4_mission_vs_ge480i_20260518.jpg`

Machine-readable report: `reports/preingame_comparison_matrix_g1mtabge3_20260518.json`

All GV-USB2 captures were normalized from 720x480 capture geometry to 720x540 display aspect before visual comparison.

## Screen-by-screen status

| Screen | Reference used | Current status | Patch implication |
| --- | --- | --- | --- |
| Classification / CMK board | Stock TND64 and GE480i legal screen | Needs clean validation. Current capture was taken during the startup loop, but prior testing said the line runs off the right edge. | Re-check with a clean capture, then adjust legal text layout only if it still exceeds the safe area. |
| TiJayFly logo | Stock TND64 | Visible and not obviously cropped, but startup cadence is slower in the current candidate. | Do not prioritize unless cadence is tied to the gunbarrel timing path. |
| Rare logo | GE480i and stock TND64 | Visible; current startup cadence is slower than stock TND64. | Treat as timing/intro-pipeline evidence, not a primary visual patch target yet. |
| White circle / barrel entry | GE480i and stock TND64 | Fails. Current renders as separated white discs instead of the normal overlapping circle sweep. | Gunbarrel geometry/source rectangle still wrong. Revert/avoid extra gunbarrel edits while gameplay remains stable. |
| Gunbarrel with Bond visible | GE480i and stock TND64 | Fails. Bond and the barrel are out of phase, and the visible barrel aperture does not match the reference. | Needs a dedicated gunbarrel pass after dossier/menu correctness is locked. |
| Gunbarrel red wipe | GE480i and stock TND64 | Fails. Red overlay timing/shape still differs from both references. | Same as above: isolate from gameplay and dossier work. |
| Title logo | GE480i title behavior and stock TND title asset | Needs measurement. It is visible, but not yet proven to match GE480i-style sharp/centered presentation. | Quantify bounds before patching. |
| Opening credits | GE480i credit scale and stock TND credit placement | Verified fail. Current character presentation is cropped/zoomed into heads or upper fragments compared with GE480i and stock TND, and user observed character credit text running offscreen. | Later scene-scale/viewport plus safe-area/text-bound pass. |
| File select dossier | GE480i file select | Mostly close. File icons and text are present, but the wallpaper/background appears shifted left versus GE480i. | Low-risk background-origin adjustment after mission text. |
| Bond dossier / mode select | GE480i Bond dossier | Improved and visually close. Remaining issue is likely cursor/hitbox/tab placement, which a still frame cannot prove. | Treat as fixed visually; validate navigation hit targets separately. |
| Mission select | GE480i mission select | Improved in `g1mtabge4`. Mission labels now sit on the filmstrip caption band instead of cutting through the photo area or dropping below the strip. | Treat `g1mtabge4` as the current mission-select baseline; verify through normal navigation before final promotion. |
| Difficulty select | GE480i difficulty page | Still unknown current. Direct route probes land on the Bond/mode page, and driven accept-path probes black out after title/menu transition. | Needs a safer driven menu path or human/controller navigation before patching. |
| Briefing / objectives | GE480i briefing/objective pages | Still unknown current. Direct route probes land on the Bond/mode page, and driven accept-path probes black out after title/menu transition. | Needs a safer driven menu path or human/controller navigation before patching. |

## Immediate next patch target

Mission-select label placement has a new hardware-verified candidate: `g1mtabge4`, built by moving the custom Y table to `[92, 193, 294, 395]`.

Next fixable target without a manual controller path is the file-select background origin. Difficulty and briefing are still blocked on a reliable driven route.

Gunbarrel remains wrong, but it should stay behind dossier/menu fixes because previous gunbarrel work consumed a lot of time without improving the playable path.
