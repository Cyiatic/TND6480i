# Tooling Improvements

Date: 2026-05-08

## Installed / Staged During This Session

- Git for Windows: `git version 2.54.0.windows.1`
- GoldenEye decomp shallow clone:
  - `C:\Users\codex\Documents\n64\007-decomp`
  - source: `https://github.com/n64decomp/007`
- Python MIPS tooling:
  - `capstone` was already present
  - `keystone-engine` installed for scriptable MIPS assembly
- WSL2 staging:
  - `Microsoft-Windows-Subsystem-Linux` enabled
  - `VirtualMachinePlatform` enabled
  - Ubuntu installed via winget / `wsl --install -d Ubuntu --no-launch`
  - after reboot, Ubuntu is registered and running as WSL2
  - decomp build packages installed in Ubuntu: `binutils-mips-linux-gnu`, `make`, `git`, `python3`, `libcapstone-dev`, `pkg-config`, `build-essential`
  - MIPS binutils smoke test passed with `mips-linux-gnu-as -32 -EB` and `mips-linux-gnu-objdump`
- MSYS2:
  - installed via winget as `MSYS2.MSYS2` version `20260322`
  - package databases refreshed with `pacman -Sy`
  - native build tools installed: `base-devel`, `gcc`, `binutils`, `make`, `git`, `python`, `pkgconf`, `diffutils`, `patch`, `autoconf`, `automake`, `libtool`
  - no MIPS cross-binutils package was visible in the MSYS2 package catalog

## Emulator Roles

- Gopher64:
  - fastest current smoke-test path
  - easiest to automate over RDP
  - good for boot/menu/gameplay survival checks
  - `scripts/smoke_gopher64.py` can launch ROMs, optionally drive Start/A input, and count `TND:*` stdout markers in JSON reports
- ares:
  - stricter, more hardware-like reference than Project64
  - useful when Gopher64 passes but the real N64 fails
- parallel-launcher / ParaLLEl-RDP:
  - useful for low-level RDP/VI comparison if configured
  - worth using for video-mode behavior before trusting Project64
- Project64:
  - convenience sanity check only
  - low trust for VI/register edge cases

Possible future additions only if needed:

- CEN64 or MAME N64 driver for stricter low-level behavior, with the caveat that setup and speed may be annoying.
- Rosalie's Mupen GUI / simple64 for another Mupen64Plus-based frontend, but this is lower priority because parallel-launcher is already installed.

## MIPS Toolchain Options

Immediate practical path:

- Use Python `keystone-engine` to assemble short MIPS hooks/trampolines.
- Use Python `capstone` to disassemble and verify patched bytes.
- This is enough for our current ROM-hack patching and avoids hand-encoding instructions.

Full build/decomp path:

- Prefer WSL2 Ubuntu or Debian for the GoldenEye decomp build environment.
- The decomp README calls for:
  - `binutils-mips-linux-gnu`
  - `make`
  - `git`
  - `python3`
  - `libcapstone-dev`
  - `pkg-config`
  - `build-essential`
- WSL2 Ubuntu is usable and has the GoldenEye decomp build package set installed.

WSL setup already performed:

```powershell
wsl --install -d Ubuntu --no-launch
```

Installed decomp build packages:

```bash
sudo apt-get update
sudo apt-get install binutils-mips-linux-gnu make git python3 libcapstone-dev pkg-config build-essential
```

Do not do this in the middle of an active hardware-debug session if it risks requiring a reboot.

## Ghidra / Decomp Workflow

Use the local GoldenEye decomp as a reference corpus rather than trying to build it immediately.

High-value reference files:

- `C:\Users\codex\Documents\n64\007-decomp\src\vi.c`
- `C:\Users\codex\Documents\n64\007-decomp\src\game\viewport.c`
- `C:\Users\codex\Documents\n64\007-decomp\src\game\bondview.c`
- `C:\Users\codex\Documents\n64\007-decomp\src\libultra\io\viint.h`
- `C:\Users\codex\Documents\n64\007-decomp\src\libultrare\io\vitbl.c`
- `C:\Users\codex\Documents\n64\007-decomp\src\libultra\io\viswapcontext.c`

Next Ghidra improvement:

1. Import or open the relevant TND main segment in Ghidra.
2. Label known patch offsets:
   - `0x3C8C` framebuffer stride/setup
   - `0x3D24` framebuffer clear/deallocate path
   - `0x46B4` active framebuffer selection
   - `0x6584` framebuffer global setup
   - `0x19978-0x19AC8` VI register setup path
3. Compare the VI path against the decomp's libultra `viswapcontext` and `vitbl` code.
4. Build a small symbol/notes map in `parallel_diag` before making more hooks.

## Capture / Video Mode

GV-USB2 plus ffmpeg is good for scripted black/menu/game-visible checks.

LightCapture may still help if it exposes:

- deinterlace on/off
- field order
- input timing / detected mode
- capture format

If the LightCapture options dialog is visible, capture a desktop screenshot and inspect the Japanese labels before changing settings.
