# Registry Manager

A safety-first Windows registry workbench built with Python and CustomTkinter. It browses and searches `HKEY_CURRENT_USER`, edits all common registry value types, manages favorites and presets, and creates recovery exports with Windows' built-in `reg.exe`.

> **Warning:** Direct registry editing bypasses normal Windows safeguards. Review every diff and keep a recovery backup. Prefer Windows Settings, Control Panel, or an application's own configuration UI when one exists.

## Why it is different

Registry Manager treats edits as **Safe Change Plans**:

1. Snapshot the exact current value, including whether it exists and its type.
2. Preview an add/modify/delete/no-change diff before writing.
3. Re-check the snapshot immediately before apply so stale previews cannot overwrite external changes.
4. Apply every operation and read it back for verification.
5. If a later operation fails, compensate earlier operations in reverse order.
6. Record a successful multi-value plan as one undoable history item.

This is a guarded, compensating workflow—not a claim of native registry transaction atomicity. Another process can still write between checks, so recovery exports remain important.

## Features

- Lazy registry tree and value browsing under HKCU
- Search by key name, value name, or data
- Lossless editors for `REG_SZ`, `REG_EXPAND_SZ`, `REG_MULTI_SZ`, `REG_BINARY`, `REG_DWORD`, and `REG_QWORD`
- Previewed, conflict-aware create/edit/delete operations
- Previewed preset batches with all-or-rollback behavior
- Grouped undo and redo that only move history after verified success
- Favorites and user presets with atomic UTF-8 persistence
- Binary preset serialization without data loss
- Unique `.reg` recovery exports and explicitly labelled import/merge behavior
- Mutable data stored under `%LOCALAPPDATA%\RegistryManager`

## Install and run

Requirements: Windows 10/11 and Python 3.10 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

CustomTkinter is pinned in `requirements.txt` so a clean installation is reproducible.

## Data locations

Registry Manager keeps mutable data out of the source/install directory:

```text
%LOCALAPPDATA%\RegistryManager\
  presets.json
  favorites.json
  backups\
```

Set `REGISTRY_MANAGER_DATA_DIR` to override this root for portable use or testing.

On first run after upgrading, existing working-directory presets, favorites, and `.reg` backups are copied into the per-user directory without deleting or overwriting the originals.

`reg export` creates recovery files. Importing a `.reg` file **merges** its contents into the registry; it is not an exact snapshot reconciliation and does not necessarily remove values created after export.

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe -m compileall -q .
git diff --check
```

Most safety behavior is tested against an in-memory fake backend with injected conflicts and write failures. Windows integration tests use a UUID-scoped key below `HKCU\Software\RegistryManagerTests` and clean it up afterward.

## Project layout

```text
main.py                 Application entry point
change_manager.py       Safe Change Plan model, verification, and compensation
registry_codec.py       Lossless registry value formatting and parsing
registry_handler.py     Minimal-rights winreg and reg.exe adapter
history_manager.py      Commit-on-success grouped undo/redo stacks
app_paths.py            Per-user data locations
preset_manager.py       Atomic typed preset persistence
favorites_manager.py    Atomic favorites persistence
ui/                     CustomTkinter views and dialogs
test_*.py               Unit and Windows integration tests
```

## Safety model

- The app currently operates under `HKEY_CURRENT_USER`; it does not request elevation.
- It opens keys with operation-specific rights such as `KEY_QUERY_VALUE` and `KEY_SET_VALUE`.
- Apply, undo, and redo use optimistic state checks and post-write verification.
- A compensation failure is surfaced explicitly; the app never reports full success after a partial write.
- Session history is intentionally memory-only so registry values are not silently journaled to disk.

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
