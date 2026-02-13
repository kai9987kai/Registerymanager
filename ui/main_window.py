import customtkinter as ctk
import os
import winreg
from registry_handler import RegistryHandler
from preset_manager import PresetManager
from favorites_manager import FavoritesManager
from history_manager import HistoryManager
from .sidebar import Sidebar
from .browser import RegistryBrowser
from .search_view import SearchView
from .favorites_view import FavoritesView
from .history_view import HistoryView

class RegistryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Advanced Registry Manager")
        self.geometry("1200x750")
        self.minsize(900, 550)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Core managers
        self.registry_handler = RegistryHandler()
        self.preset_manager = PresetManager()
        self.favorites_manager = FavoritesManager()
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
            status_callback=self.set_status
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
        entry = self.history_manager.pop_undo()
        if not entry:
            self.set_status("Nothing to undo.", "orange")
            return
        
        action = entry.get("action")
        hive = winreg.HKEY_CURRENT_USER
        path = entry.get("path", "")
        name = entry.get("name", "")
        
        if action == "write":
            old_val = entry.get("old_value")
            old_type = entry.get("old_type")
            if old_val is not None and old_type is not None:
                self.registry_handler.write_value(hive, path, name, old_val, old_type)
                self.set_status(f"Undone: restored {name}", "green")
            else:
                # Value didn't exist before, so delete it
                self.registry_handler.delete_value(hive, path, name)
                self.set_status(f"Undone: removed {name}", "green")
        elif action == "delete":
            old_val = entry.get("old_value")
            old_type = entry.get("old_type")
            if old_val is not None and old_type is not None:
                self.registry_handler.write_value(hive, path, name, old_val, old_type)
                self.set_status(f"Undone: restored deleted {name}", "green")
        
        self.update_undo_status()

    def perform_redo(self):
        entry = self.history_manager.pop_redo()
        if not entry:
            self.set_status("Nothing to redo.", "orange")
            return
        
        action = entry.get("action")
        hive = winreg.HKEY_CURRENT_USER
        path = entry.get("path", "")
        name = entry.get("name", "")
        
        if action == "write":
            new_val = entry.get("new_value")
            new_type = entry.get("new_type")
            if new_val is not None and new_type is not None:
                self.registry_handler.write_value(hive, path, name, new_val, new_type)
                self.set_status(f"Redone: set {name}", "green")
        elif action == "delete":
            self.registry_handler.delete_value(hive, path, name)
            self.set_status(f"Redone: deleted {name}", "green")
        
        self.update_undo_status()

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
                
                ctk.CTkButton(row, text="Apply", width=70, command=lambda n=name: self.apply_preset(n)).pack(side="right", padx=5)
                ctk.CTkButton(row, text="Delete", width=70, fg_color="red", hover_color="darkred", 
                              command=lambda n=name: self.delete_preset(n)).pack(side="right", padx=5)

    def delete_preset(self, name):
        self.preset_manager.delete_preset(name)
        self.set_status(f"Deleted preset: {name}", "orange")
        self.show_presets()

    def apply_preset(self, name):
        data = self.preset_manager.get_preset(name)
        if not data: return
        
        path = data.get("path")
        values = data.get("values")
        hive = winreg.HKEY_CURRENT_USER
        
        for v in values:
            v_name, v_data, v_type = v
            self.registry_handler.write_value(hive, path, v_name, v_data, v_type)
        
        self.set_status(f"Applied preset: {name}", "green")
        self.navigate_to_key(path)

    # --- Backups ---
    def show_backups(self):
        self.clear_content()
        self.set_status("Backups Manager")
        
        frame = ctk.CTkScrollableFrame(self.content_frame)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Backups Manager", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(10, 20))
        
        backup_folder = "backups"
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
            
        files = sorted([f for f in os.listdir(backup_folder) if f.endswith(".reg")], reverse=True)
        
        if not files:
            ctk.CTkLabel(frame, text="No backups found.", text_color="gray").pack(pady=10)
        else:
            for f in files:
                row = ctk.CTkFrame(frame)
                row.pack(fill="x", padx=30, pady=4)
                ctk.CTkLabel(row, text=f, font=("Arial", 14), anchor="w").pack(side="left", padx=15, fill="x", expand=True)
                ctk.CTkButton(row, text="Restore", width=80, command=lambda fn=f: self.restore_backup(fn)).pack(side="right", padx=5)
                ctk.CTkButton(row, text="Delete", width=70, fg_color="red", hover_color="darkred",
                              command=lambda fn=f: self.delete_backup(fn)).pack(side="right", padx=5)

    def restore_backup(self, filename):
        filepath = os.path.join("backups", filename)
        success = self.registry_handler.restore_backup(filepath)
        if success:
            self.set_status(f"Restored: {filename}", "green")
        else:
            self.set_status(f"Restore failed: {filename}", "red")

    def delete_backup(self, filename):
        filepath = os.path.join("backups", filename)
        try:
            os.remove(filepath)
            self.set_status(f"Deleted backup: {filename}", "orange")
        except Exception as e:
            self.set_status(f"Error: {e}", "red")
        self.show_backups()
