import customtkinter as ctk
import os
import winreg
from dataclasses import dataclass
from tkinter import messagebox
from app_paths import get_app_paths, migrate_legacy_data
from change_manager import ApplyStatus, ChangePlan
from registry_handler import RegistryHandler
from preset_manager import PresetManager
from favorites_manager import FavoritesManager
from history_manager import HistoryManager
from .sidebar import Sidebar
from .browser import RegistryBrowser
from .search_view import SearchView
from .favorites_view import FavoritesView
from .history_view import HistoryView
from .change_preview import ChangePreviewDialog


@dataclass(frozen=True)
class _UiApplyResult:
    success: bool
    message: str

class RegistryApp(ctk.CTk):
    def __init__(self, data_dir=None):
        super().__init__()

        self.title("Advanced Registry Manager")
        self.geometry("1200x750")
        self.minsize(900, 550)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Core managers. Mutable files live under the user's application data
        # directory so packaged/shortcut launches never depend on the CWD.
        self.app_paths = get_app_paths(data_dir)
        self.migration_report = migrate_legacy_data(self.app_paths)
        self.registry_handler = RegistryHandler(self.app_paths["backups"])
        self.preset_manager = PresetManager(self.app_paths["presets"])
        self.favorites_manager = FavoritesManager(self.app_paths["favorites"])
        self.history_manager = HistoryManager()

        # Sidebar
        self.sidebar = Sidebar(self, self.on_navigate)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Main content area
        self.content_frame = ctk.CTkFrame(self, corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=(0, 0))
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Status bar
        self.status_bar = ctk.CTkFrame(self, height=28, corner_radius=0)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.status_label = ctk.CTkLabel(self.status_bar, text="Ready", text_color="gray", anchor="w")
        self.status_label.pack(side="left", padx=10)
        self.undo_label = ctk.CTkLabel(self.status_bar, text="", text_color="gray", anchor="e")
        self.undo_label.pack(side="right", padx=10)

        # Keep a reference to the current browser for navigation
        self.current_browser = None

        self.show_browser()
        if self.migration_report["errors"]:
            self.set_status(
                "Started, but some legacy data could not be migrated. See the console for details.",
                "orange",
            )
            for migration_error in self.migration_report["errors"]:
                print(f"Legacy data migration warning: {migration_error}")
        elif self.migration_report["copied"]:
            self.set_status(
                f"Migrated {len(self.migration_report['copied'])} legacy data item(s).",
                "green",
            )

    def set_status(self, text, color="gray"):
        self.status_label.configure(text=text, text_color=color)

    def update_undo_status(self):
        undo_count = len(self.history_manager.undo_stack)
        redo_count = len(self.history_manager.redo_stack)
        text = f"Undo: {undo_count}  |  Redo: {redo_count}"
        self.undo_label.configure(text=text)

    def on_navigate(self, view_name):
        if view_name == "browser":
            self.show_browser()
        elif view_name == "presets":
            self.show_presets()
        elif view_name == "backups":
            self.show_backups()
        elif view_name == "search":
            self.show_search()
        elif view_name == "favorites":
            self.show_favorites()
        elif view_name == "history":
            self.show_history()

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    # --- Browser ---
    def show_browser(self):
        self.clear_content()
        self.set_status("Browsing Registry")
        browser = RegistryBrowser(
            self.content_frame, 
            self.registry_handler, 
            self.preset_manager,
            history_manager=self.history_manager,
            favorites_manager=self.favorites_manager,
            status_callback=self.set_status,
            review_plan_callback=self.review_change_plan,
        )
        browser.pack(fill="both", expand=True)
        self.current_browser = browser

    def navigate_to_key(self, path):
        """Navigate the browser to a specific key path."""
        self.show_browser()
        if self.current_browser:
            self.current_browser.current_path = path
            self.current_browser.load_values(path)
        self.set_status(f"Navigated to: {path}")

    # --- Search ---
    def show_search(self):
        self.clear_content()
        self.set_status("Search Mode")
        search = SearchView(self.content_frame, self.registry_handler, on_navigate_to_key=self.navigate_to_key)
        search.pack(fill="both", expand=True)

    # --- Favorites ---
    def show_favorites(self):
        self.clear_content()
        self.set_status("Favorites")
        fav_view = FavoritesView(self.content_frame, self.favorites_manager, on_navigate_to_key=self.navigate_to_key)
        fav_view.pack(fill="both", expand=True)

    # --- History ---
    def show_history(self):
        self.clear_content()
        self.set_status("Change History")
        self.update_undo_status()
        hist_view = HistoryView(self.content_frame, self.history_manager, on_undo=self.perform_undo, on_redo=self.perform_redo)
        hist_view.pack(fill="both", expand=True)

    def perform_undo(self):
        entry = self.history_manager.peek_undo()
        if not entry:
            self.set_status("Nothing to undo.", "orange")
            return False

        if not hasattr(entry, "create_inverse_plan"):
            self.set_status("This legacy history item cannot be safely undone.", "red")
            return False

        result = entry.create_inverse_plan().apply()
        if result.success:
            self.history_manager.commit_undo(entry)
            self.set_status(f"Undone: {entry.label}", "green")
        else:
            self.set_status(result.message, self._result_color(result.status))
        self.update_undo_status()
        return result.success

    def perform_redo(self):
        entry = self.history_manager.peek_redo()
        if not entry:
            self.set_status("Nothing to redo.", "orange")
            return False

        if not hasattr(entry, "create_forward_plan"):
            self.set_status("This legacy history item cannot be safely redone.", "red")
            return False

        result = entry.create_forward_plan().apply()
        if result.success:
            self.history_manager.commit_redo(entry)
            self.set_status(f"Redone: {entry.label}", "green")
        else:
            self.set_status(result.message, self._result_color(result.status))
        self.update_undo_status()
        return result.success

    def _result_color(self, status):
        if status in (ApplyStatus.CONFLICT, ApplyStatus.ROLLED_BACK):
            return "orange"
        return "red"

    def review_change_plan(self, plan, on_success=None):
        """Open a zero-write diff review for a prepared change plan."""
        return ChangePreviewDialog(
            self,
            plan,
            on_apply=lambda reviewed_plan, create_backup: self.apply_change_plan(
                reviewed_plan,
                create_backup=create_backup,
                on_success=on_success,
            ),
            backup_default=True,
        )

    def apply_change_plan(self, plan, create_backup=True, on_success=None):
        """Create recovery exports, apply, verify, then commit history."""
        effective = plan.effective_changes
        if create_backup:
            backed_up = set()
            for change in effective:
                location = (change.hive_name.casefold(), change.path.casefold())
                if location in backed_up:
                    continue
                full_path = (
                    f"{change.hive_name}\\{change.path}"
                    if change.path else change.hive_name
                )
                backup_path = self.registry_handler.backup_key(full_path)
                if not backup_path:
                    message = (
                        f"Recovery export failed for {full_path}; no registry changes were applied. "
                        f"{self.registry_handler.last_error or ''}"
                    ).strip()
                    self.set_status(message, "red")
                    return _UiApplyResult(False, message)
                backed_up.add(location)

        result = plan.apply()
        if result.success:
            if effective:
                self.history_manager.record_plan(plan)
            try:
                self.update_undo_status()
                self.set_status(f"Applied: {plan.label}", "green")
                if on_success:
                    on_success()
            except Exception as exc:
                # The registry commit and history record already succeeded. A
                # view refresh error must never invite a retry of the plan.
                try:
                    self.set_status(
                        f"Applied: {plan.label}. View refresh failed: {exc}",
                        "orange",
                    )
                except Exception:
                    print(f"Post-apply UI refresh warning: {exc}")
        else:
            self.set_status(result.message, self._result_color(result.status))
        return result

    # --- Presets ---
    def show_presets(self):
        self.clear_content()
        self.set_status("Presets Manager")
        
        frame = ctk.CTkScrollableFrame(self.content_frame)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Presets Manager", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(10, 20))
        
        presets = self.preset_manager.presets
        if not presets:
            ctk.CTkLabel(frame, text="No presets found.", text_color="gray").pack(pady=10)
        else:
            for name in presets:
                row = ctk.CTkFrame(frame)
                row.pack(fill="x", padx=30, pady=4)
                ctk.CTkLabel(row, text=name, font=("Arial", 14), anchor="w").pack(side="left", padx=15)
                
                preset_data = presets[name]
                path_text = preset_data.get("path", "")
                ctk.CTkLabel(row, text=path_text, text_color="gray", anchor="w").pack(side="left", padx=10, fill="x", expand=True)
                
                value_count = len(preset_data.get("values", []))
                ctk.CTkLabel(
                    row, text=f"{value_count} value(s)", text_color="#86B7E7"
                ).pack(side="right", padx=8)
                ctk.CTkButton(row, text="Review", width=75, command=lambda n=name: self.apply_preset(n)).pack(side="right", padx=5)
                ctk.CTkButton(row, text="Delete", width=70, fg_color="red", hover_color="darkred", 
                              command=lambda n=name: self.delete_preset(n)).pack(side="right", padx=5)

    def delete_preset(self, name):
        self.preset_manager.delete_preset(name)
        self.set_status(f"Deleted preset: {name}", "orange")
        self.show_presets()

    def apply_preset(self, name):
        data = self.preset_manager.get_preset(name)
        if not data:
            self.set_status(f"Preset not found: {name}", "red")
            return
        
        path = data.get("path")
        values = data.get("values") or []
        hive = winreg.HKEY_CURRENT_USER

        try:
            plan = ChangePlan(self.registry_handler, f"Apply preset: {name}")
            for value_spec in values:
                if not isinstance(value_spec, (list, tuple)) or len(value_spec) != 3:
                    raise ValueError("Each preset value must contain name, data, and type.")
                value_name, value_data, value_type = value_spec
                plan.set_value(hive, path, value_name, value_data, value_type)
        except Exception as exc:
            self.set_status(f"Could not prepare preset: {exc}", "red")
            return

        self.review_change_plan(
            plan,
            on_success=lambda: self.navigate_to_key(path),
        )

    # --- Backups ---
    def show_backups(self):
        self.clear_content()
        self.set_status("Backups Manager")
        
        frame = ctk.CTkScrollableFrame(self.content_frame)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Backups Manager", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(10, 20))
        
        backup_folder = self.app_paths["backups"]
        os.makedirs(backup_folder, exist_ok=True)
            
        files = sorted([f for f in os.listdir(backup_folder) if f.endswith(".reg")], reverse=True)
        
        if not files:
            ctk.CTkLabel(frame, text="No backups found.", text_color="gray").pack(pady=10)
        else:
            for f in files:
                row = ctk.CTkFrame(frame)
                row.pack(fill="x", padx=30, pady=4)
                ctk.CTkLabel(row, text=f, font=("Arial", 14), anchor="w").pack(side="left", padx=15, fill="x", expand=True)
                ctk.CTkButton(row, text="Import / merge", width=110, command=lambda fn=f: self.restore_backup(fn)).pack(side="right", padx=5)
                ctk.CTkButton(row, text="Delete", width=70, fg_color="red", hover_color="darkred",
                              command=lambda fn=f: self.delete_backup(fn)).pack(side="right", padx=5)

    def restore_backup(self, filename):
        if not messagebox.askyesno(
            "Import registry backup",
            "This merges the selected .reg file into the Windows Registry. "
            "It is not an exact snapshot restore. Continue?",
            parent=self,
        ):
            self.set_status("Backup import cancelled.", "gray")
            return
        filepath = os.path.join(self.app_paths["backups"], filename)
        success = self.registry_handler.restore_backup(filepath)
        if success:
            self.set_status(f"Imported / merged: {filename}", "green")
        else:
            self.set_status(f"Import failed: {filename}", "red")

    def delete_backup(self, filename):
        filepath = os.path.join(self.app_paths["backups"], filename)
        try:
            os.remove(filepath)
            self.set_status(f"Deleted backup: {filename}", "orange")
        except Exception as e:
            self.set_status(f"Error: {e}", "red")
        self.show_backups()
