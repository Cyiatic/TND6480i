# Publishing Notes - 2026-07-02

## Permission / Provenance

TiJay indicated that publishing the TND6480i repository is okay, with one clear
condition: public materials must state that the patch is based on the Tomorrow
Never Dies 64 `11-24 Extended Edition`.

He also said he may speak with Wreck about including the patch as part of a
future Vault bundle. Treat that as an upstream packaging possibility, not as a
promise or release dependency controlled by this repo.

## Public Release Rules

- State the base romhack clearly: Tomorrow Never Dies 64 `11-24 Extended Edition`.
- Distribute patch files, manifests, documentation, and scripts; do not
  distribute ROMs.
- Keep generated ROMs, saves, raw captures, private tools, and credentials out
  of the public repo.
- Preserve the AI assistance disclosure in the README.
- Record source/target hashes and patch/ZIP hashes for any public package.

## Current Release Candidate Line

The current line to package remains:

```text
Candidate: g1hiq3_gegate / G1HQ3AM
ROM MD5: 4063fd9968b528148a9441b11dfd0203
ROM SHA256: f359631cb63bb367e56a6c39a5f95b6fc11a3fda5b8a2c2eed87a3da5aded3d3
Save/EEP MD5: 50a3f7cf6e022fdec7f37f2cc8ae2e2a
Save type: EEPROM 4K
Target hardware: NTSC N64 with Expansion Pak / 8 MB
```
