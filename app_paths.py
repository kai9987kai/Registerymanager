"""Stable locations for mutable Registry Manager data."""

import os
import filecmp
import shutil
import tempfile
from pathlib import Path


APP_DATA_OVERRIDE = "REGISTRY_MANAGER_DATA_DIR"


def get_app_data_dir(override=None):
    """Return (and create) the per-user application data directory."""
    configured = override or os.environ.get(APP_DATA_OVERRIDE)
    if configured:
        base = Path(configured).expanduser()
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) / "RegistryManager" if local_app_data else Path.home() / ".registry_manager"

    base = base.resolve()
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_app_paths(override=None):
    """Return all mutable data locations rooted under one directory."""
    root = get_app_data_dir(override)
    backups = root / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    return {
        "root": root,
        "presets": root / "presets.json",
        "favorites": root / "favorites.json",
        "backups": backups,
    }


def _atomic_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        handle, temp_name = tempfile.mkstemp(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".migrating",
        )
        os.close(handle)
        temp_path = Path(temp_name)
        shutil.copy2(source, temp_path)
        os.replace(temp_path, destination)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def _available_backup_destination(backups_dir, source):
    candidate = backups_dir / source.name
    if not candidate.exists():
        return candidate
    try:
        if filecmp.cmp(candidate, source, shallow=False):
            return None
    except OSError:
        pass

    index = 1
    while True:
        candidate = backups_dir / f"{source.stem}_legacy_{index}{source.suffix}"
        if not candidate.exists():
            return candidate
        try:
            if filecmp.cmp(candidate, source, shallow=False):
                return None
        except OSError:
            pass
        index += 1


def migrate_legacy_data(paths, legacy_roots=None):
    """Copy pre-upgrade CWD data into the per-user data directory once.

    Existing destination files are never overwritten, and legacy files are
    left in place so migration is recoverable.
    """
    if legacy_roots is None:
        legacy_roots = (Path.cwd(), Path(__file__).resolve().parent)

    report = {"copied": [], "errors": []}
    destination_root = Path(paths["root"]).resolve()
    seen_roots = set()

    for legacy_root in legacy_roots:
        try:
            root = Path(legacy_root).expanduser().resolve()
        except OSError as exc:
            report["errors"].append(f"{legacy_root}: {exc}")
            continue
        if root in seen_roots or root == destination_root:
            continue
        seen_roots.add(root)

        for name, destination_key in (
            ("presets.json", "presets"),
            ("favorites.json", "favorites"),
        ):
            source = root / name
            destination = Path(paths[destination_key])
            if not source.is_file() or destination.exists():
                continue
            try:
                _atomic_copy(source, destination)
                report["copied"].append(str(destination))
            except OSError as exc:
                report["errors"].append(f"{source}: {exc}")

        legacy_backups = root / "backups"
        if not legacy_backups.is_dir():
            continue
        for source in legacy_backups.glob("*.reg"):
            try:
                destination = _available_backup_destination(
                    Path(paths["backups"]), source
                )
                if destination is None:
                    continue
                _atomic_copy(source, destination)
                report["copied"].append(str(destination))
            except OSError as exc:
                report["errors"].append(f"{source}: {exc}")

    return report
