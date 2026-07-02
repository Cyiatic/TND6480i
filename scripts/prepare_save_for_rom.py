#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path


EEPROM_4K_PADDED_SIZE = 2048


def digest(path, algorithm):
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rom_internal_title(rom_data):
    title = rom_data[0x20:0x34].decode("ascii", errors="ignore").strip(" \0")
    if not title:
        title = "UNKNOWN"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", title)


def padded_eeprom(data):
    if len(data) >= EEPROM_4K_PADDED_SIZE:
        return data
    return data + b"\x00" * (EEPROM_4K_PADDED_SIZE - len(data))


def write_with_backup(path, data, dry_run=False):
    action = {"path": str(path), "bytes": len(data), "backup": None, "changed": False}
    if path.exists():
        existing = path.read_bytes()
        if existing == data:
            return action
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = path.with_name(f"{path.name}.bak_{timestamp}")
        action["backup"] = str(backup)
        action["changed"] = True
        if not dry_run:
            shutil.copy2(path, backup)
    else:
        action["changed"] = True

    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return action


def main():
    parser = argparse.ArgumentParser(
        description="Pair the complete TND EEPROM save with ROM candidates for SC64 and emulators."
    )
    parser.add_argument("roms", nargs="+", type=Path)
    parser.add_argument(
        "--save",
        type=Path,
        default=Path(r"C:\Users\codex\Documents\007 - Tomorrow Never Dies (USA).sav"),
    )
    parser.add_argument(
        "--gopher-save-dir",
        type=Path,
        default=Path.home() / "AppData" / "Roaming" / "gopher64" / "saves",
    )
    parser.add_argument(
        "--parallel-save-dir",
        type=Path,
        default=Path.home()
        / "AppData"
        / "Local"
        / "parallel-launcher"
        / "data"
        / "retro-data"
        / "saves",
    )
    parser.add_argument(
        "--parallel-srm-template",
        type=Path,
        default=None,
        help="Optional existing Parallel Launcher .srm to use as a container template.",
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    save_data = args.save.read_bytes()
    eep_data = padded_eeprom(save_data)
    manifest = {
        "source_save": str(args.save),
        "source_save_bytes": len(save_data),
        "source_save_md5": digest(args.save, "md5"),
        "gopher_save_dir": str(args.gopher_save_dir),
        "parallel_save_dir": str(args.parallel_save_dir),
        "parallel_srm_template": str(args.parallel_srm_template)
        if args.parallel_srm_template
        else None,
        "roms": [],
    }

    parallel_srm_data = None
    if args.parallel_srm_template:
        parallel_srm_data = bytearray(args.parallel_srm_template.read_bytes())
        parallel_srm_data[: len(save_data)] = save_data

    for rom in args.roms:
        rom_data = rom.read_bytes()
        sha256 = hashlib.sha256(rom_data).hexdigest().upper()
        title = rom_internal_title(rom_data)
        sibling_sav = rom.with_suffix(".sav")
        sibling_eep = rom.with_suffix(".eep")
        gopher_eep = args.gopher_save_dir / f"{title}-{sha256}.eep"
        parallel_srm = args.parallel_save_dir / f"{rom.stem}.srm"

        writes = [
            write_with_backup(sibling_sav, save_data, args.dry_run),
            write_with_backup(sibling_eep, eep_data, args.dry_run),
            write_with_backup(gopher_eep, eep_data, args.dry_run),
        ]
        if parallel_srm_data is not None:
            writes.append(write_with_backup(parallel_srm, bytes(parallel_srm_data), args.dry_run))

        entry = {
            "rom": str(rom),
            "rom_md5": digest(rom, "md5"),
            "rom_sha256": sha256,
            "internal_title": title,
            "writes": writes,
        }
        manifest["roms"].append(entry)

    text = json.dumps(manifest, indent=2) + "\n"
    if args.manifest:
        if not args.dry_run:
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
