# Hardware-In-The-Loop Workflow

This project only became tractable once real N64 output was treated as a
scripted test target instead of a final manual check.

## Hardware Setup

- Real NTSC N64 with Expansion Pak / 8 MB.
- SC64 / SummerCart64 for rapid direct boot and explicit EEPROM 4K save type.
- GV-USB2 capture card over S-Video, usually captured with ffmpeg.
- Kasa smart outlet for remote power-cycle recovery after bad ROM locks.
- EverDrive X7 for final SD-card/save behavior checks.
- Analogue 3D as an additional visual-quality check, especially for text and
  anti-aliasing differences.

## Development Loop

1. Build a narrow ROM candidate from documented offset changes.
2. Smoke it in emulator to reject crashes and obvious black screens quickly.
3. Upload it to SC64 with the intended save type and known-good save state.
4. Power-cycle or reset the N64 when needed through the Kasa-controlled outlet.
5. Capture stills or clips from GV-USB2 over S-Video with ffmpeg.
6. Generate contact sheets or comparison atlases against GE480i reference
   footage.
7. Promote, reject, or narrow the next patch based on measured screen behavior.

This mattered because several candidates looked plausible in emulators but
failed on real hardware, and several visual issues were only obvious from the
capture path or from Analogue 3D output.

## SC64 Direct Upload

Prefer SC64 for development iteration. It allows direct upload and explicit save
type control.

Typical direct upload:

```powershell
C:\Users\codex\Documents\n64\sc64deployer.exe upload `
  --direct `
  --save-type eeprom4k `
  --save artifacts\generated\g1mcfix4.sav `
  artifacts\generated\g1mcfix4.z64
```

Current font-good line:

```powershell
C:\Users\codex\Documents\n64\sc64deployer.exe upload `
  --direct `
  --save-type eeprom4k `
  --save artifacts\generated\g1hiq3_gegate_ammoon.sav `
  artifacts\generated\g1hiq3_gegate.z64
```

## GV-USB2 Capture

Single-frame capture:

```powershell
ffmpeg -hide_banner -y `
  -f dshow `
  -video_size 720x480 `
  -framerate 29.97 `
  -i video="GV-USB2, Analog Capture" `
  -frames:v 1 diagnostics\captures\current\probe.png
```

For deeper analysis, capture short clips and generate contact sheets or
side-by-side comparisons against GoldenEye 480i reference footage.

## Kasa Power Recovery

The Kasa outlet reduced the cost of testing bad candidates. When a ROM wedged
the console, the test loop could power-cycle the N64 and return to SC64 without
waiting for a person to physically reset the hardware.

Reusable helpers live in:

- `scripts/hardware/cycle_kasa_n64_buttons.ps1`
- `scripts/hardware/record_gvusb2_kasa_cycle.ps1`

## Why The Emulator Is Not Enough

Emulators were useful for rejecting obviously broken candidates, routing into
menus or stages, and collecting fast comparison screenshots. They were not the
release authority.

The source of truth was:

1. Real N64 output captured through GV-USB2.
2. Human/Analogue 3D review for visible sharpness and text quality.
3. Repeatable hashes and save-option state recorded alongside each candidate.
