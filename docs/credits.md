# Credits And Acknowledgements

TND6480i exists because of several layers of N64 modding, reverse engineering,
tooling, and hardware testing work.

## Base Game And Romhack

- Rare: original GoldenEye 007 engine and Nintendo 64 game technology.
- Tomorrow Never Dies 64 team: base Tomorrow Never Dies 64 romhack.
- TiJay: Tomorrow Never Dies 64 11-24 Extended Edition provenance and project
  guidance.
- Wreck: Tomorrow Never Dies 64 / Vault ecosystem support.

## GoldenEye 480i Prior Art

The technical target for this project was the behavior of the GoldenEye 007
Enhanced 480i / Hi Res patch family.

- SubDrag: GoldenEye Hi Res mode work.
- Trevor: 640 x 480i help and testing credit in the GoldenEye Hi Res patch
  notes.
- Zoinkity: 7 MB RAM extension work credited by the GoldenEye Hi Res patch
  notes.

## TND6480i Project Work

- Cyiatic: project owner, hardware setup, real-console testing, subjective
  visual review, patch direction, capture references, and release coordination.
- OpenAI Codex: AI-assisted reverse-engineering support, scripting, candidate
  generation, comparison workflows, documentation, and repo preparation.

## Tooling And References

- SC64 / SummerCart64 and `sc64deployer`: rapid real-hardware upload, save
  control, and recovery loop.
- GV-USB2 capture hardware and ffmpeg: S-Video capture and visual evidence.
- Kasa Smart Control / smart outlet: remote N64 power-cycle recovery.
- Gopher64, Ares, and Project64: emulator smoke tests and quick visual checks.
- Ghidra and the N64 plugin ecosystem: static analysis and MIPS/N64 reverse
  engineering.
- `n64decomp/007` and related GoldenEye decompilation work: reference material
  for GoldenEye engine behavior.
- Community N64 reverse-engineering resources and utilities used during
  investigation are linked or discussed throughout `docs/`.

## Release Note

This repository intentionally does not distribute commercial ROMs, generated ROM
images, private captures, save files, or binary patch blobs. Public releases
should distribute patches, manifests, and documentation only.
