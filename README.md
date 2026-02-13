# Registerymanager (Advanced Windows Registry Manager)

A Windows-only Registry Manager written in Python, with a **CustomTkinter** GUI for browsing, editing, backing up, and applying “preset” tweaks to common Windows settings.

> ⚠️ **Warning:** Editing the Windows Registry can break apps or the OS. Always **backup** before changing values, and prefer operating under **HKEY_CURRENT_USER (HKCU)** unless you know exactly what you’re doing.

---

## What it does

- **Browse registry keys** (Tree view) under **HKEY_CURRENT_USER**
- **Read / create / edit / delete registry values**
- **Value filtering** (search within the current key by name/value/type)
- **Favorites** (persisted to `favorites.json`)
- **Presets** (persisted to `presets.json`) for common Windows UI toggles
- **Backups / Restore** using `reg.exe export` / `reg.exe import` (saved to `backups/`)
- **Change history** in memory with **Undo / Redo** stacks (not persisted)

---

## Features (detail)

### 1) Registry Browser
- Tree navigation (lazy-load of subkeys).
- Value panel shows: **Name / Type / Value**.
- Actions:
  - **Edit** an existing value
  - **Delete** a value
  - **Create** a new value (supports `REG_SZ`, `REG_DWORD`, `REG_QWORD`, `REG_BINARY`)
  - **Filter** values by substring match
  - **Backup key** to `.reg`

### 2) Presets (built-in)
The app ships with default presets that modify common HKCU settings, including:

- Enable / Disable **Dark Mode**
- Show / Hide **File Extensions**
- Show / Hide **Hidden Files**
- Enable / Disable **Title Bar Color**

Presets are stored in `presets.json` and can be extended by adding new entries with:
- a target `path` (subkey)
- a list of `values` as `(name, data, type)` triples

### 3) Favorites
Save frequently used key paths into `favorites.json`. Each entry includes:
- hive name (string, e.g. `"HKEY_CURRENT_USER"`)
- key path
- optional label

### 4) Backups + Restore
Backups are created via Windows’ built-in tooling:
- `reg export <key> <file> /y`
- `reg import <file>`

Backups are timestamped and stored under `backups/`.

### 5) History + Undo/Redo
Registry write/delete operations can be recorded into an in-memory history:
- Undo stack / redo stack (bounded deque)
- Undo/redo replays changes by restoring old values or reapplying the new ones

---

## Project structure (high level)

```text
Registerymanager/
  main.py
  registry_handler.py
  preset_manager.py
  favorites_manager.py
  history_manager.py
  presets.json
  ui/
    __init__.py
    main_window.py
    sidebar.py
    browser.py
    editors.py
    styles.py
    search_view.py
    favorites_view.py
    history_view.py
  test_registry_handler.py
  test_ui_import.py
