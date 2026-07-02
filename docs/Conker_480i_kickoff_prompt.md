# Conker 480i Kickoff Prompt

Use this file as the starting instruction for a new Codex conversation/project.

## Paste Or Reference This

```text
Please start a new Conker's Bad Fur Day 480i patch project using the workflow lessons from my TND6480i project.

First, read these handoff documents from the previous project:

C:\Users\codex\Documents\GitHub\TND6480i\docs\N64_480i_porting_playbook.md
C:\Users\codex\Documents\GitHub\TND6480i\docs\project_retrospective_20260525.md
C:\Users\codex\Documents\GitHub\TND6480i\docs\reverse_engineering_technical_findings.md
C:\Users\codex\Documents\GitHub\TND6480i\docs\measurable_480i_validation_workflow_20260525.md
C:\Users\codex\Documents\GitHub\TND6480i\docs\runtime_text_measurement_attempt_20260525.md
C:\Users\codex\Documents\GitHub\TND6480i\docs\direct_stage_probe_workflow.md
C:\Users\codex\Documents\GitHub\TND6480i\docs\credits_render_path_audit_20260519.md
C:\Users\codex\Documents\GitHub\TND6480i\README.md

Important constraints:
- Work only on N64/project-related tasks.
- Use Git from the beginning.
- Keep commercial ROMs, saves, and large captures out of Git unless explicitly told otherwise.
- Build named candidates with manifests, checksums, and patch-site reports.
- Avoid brute-force candidate churn. Make a hypothesis, patch only that scope, test, and document promotion/rejection.
- Use emulators for quick debugging, but require hardware capture before calling anything a release candidate.
- Pair every candidate with the exact save file and save type used for testing.
- Record display options that affect comparisons, including HUD visibility, aspect/screen mode, and anti-aliasing where available.
- Treat user/manual testing as scarce: build objective emulator/capture/direct-probe gates first.

Target project:
- Game: Conker's Bad Fur Day
- Goal: create a working 480i / hi-res style patch.
- Do not assume GoldenEye or TND64 offsets apply directly. Transfer the workflow, not the addresses.

Please begin by:
1. Creating or inspecting the new repo structure.
2. Recording the stock ROM region/hash once I provide the ROM.
3. Creating baseline documentation for stock behavior, emulator behavior, and hardware capture setup.
4. Auditing the ROM/decomp/disassembly for video init, framebuffer allocation, VI settings, viewport setup, z-buffer ownership, text/menu render paths, save behavior, and memory-map pressure.
5. Proposing the first minimal candidate plan before patching.

Use the TND6480i documents as prior art for workflow and pitfalls:
- 480i is a coordinated framebuffer/VI/viewport/z-buffer/memory-map problem.
- Menu and gameplay paths may need separate fixes.
- Direct-stage or direct-screen probes are preferred over repeated manual playthroughs.
- Screen-by-screen comparison against stock and any known 480i reference is required.
- Save options can invalidate HUD/text comparisons.
- Anti-aliasing or other display toggles can materially change perceived text sharpness.
- Text/HUD/UI constants may fix more than text sharpness; verify overlay placement too.
```

## What To Provide Early

The new project will move much faster if these are available:

- clean Conker ROM region and hash
- target hardware setup
- emulator list and versions
- whether Expansion Pak is allowed or required
- any existing Conker decomp/disassembly notes
- any known hi-res/interlace behavior in stock Conker
- flashcart used for hardware tests
- capture-card setup and sample stock recording
- save type, complete save availability, and flashcart save naming rules
- known display-option state for captures, especially anti-aliasing if exposed
- whether a known-good 480i reference exists for comparison

## First Milestone

The first milestone should not be "make it 480i." It should be:

```text
Document stock Conker's video/render/memory path well enough that the first 480i candidate has a falsifiable hypothesis.
```

That keeps the project from repeating the early TND6480i brute-force phase.
