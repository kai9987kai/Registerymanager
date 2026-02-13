import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import winreg
from .editors import ValueEditor, NewValueDialog
from .styles import COLOR_BG, COLOR_SELECTED

class RegistryBrowser(ctk.CTkFrame):
    def __init__(self, parent, registry_handler, preset_manager, 
                 history_manager=None, favorites_manager=None, status_callback=None):
        super().__init__(parent, corner_radius=0)
        self.registry_handler = registry_handler
        self.preset_manager = preset_manager
        self.history_manager = history_manager
        self.favorites_manager = favorites_manager
        self.status_callback = status_callback
        
        self.current_hive = winreg.HKEY_CURRENT_USER
        self.current_path = ""
        self.value_filter_var = tk.StringVar()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.create_widgets()

    def set_status(self, text, color="gray"):
        if self.status_callback:
            self.status_callback(text, color)
        
    def create_widgets(self):
        # Split into TreeView (Left) and Value List (Right)
        paned_window = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5, bg=COLOR_BG)
        paned_window.pack(fill="both", expand=True)

        # TreeView Frame
        tree_frame = ctk.CTkFrame(paned_window)
        paned_window.add(tree_frame)
        
        # Style Treeview to match dark theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLOR_BG, foreground="white", fieldbackground=COLOR_BG, borderwidth=0)
        style.map("Treeview", background=[("selected", COLOR_SELECTED)])
        
        self.tree = ttk.Treeview(tree_frame, show="tree")
        
        # Scrollbar for tree
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_open)

        # Populate Root
        root_node = self.tree.insert("", "end", text="HKEY_CURRENT_USER", open=False, values=["HKEY_CURRENT_USER"])
        self.tree.insert(root_node, "end", text="Loading...") # Dummy node

        # Value List Frame
        value_frame = ctk.CTkFrame(paned_window)
        paned_window.add(value_frame)
        
        self.value_list = ctk.CTkScrollableFrame(value_frame)
        self.value_list.pack(fill="both", expand=True, padx=5, pady=5)

    def on_tree_open(self, event):
        items = self.tree.selection()
        if not items: return
        item = items[0]
        self.refresh_tree_item(item)

    def refresh_tree_item(self, item):
        # Clear dummy
        children = self.tree.get_children(item)
        if len(children) == 1 and self.tree.item(children[0], "text") == "Loading...":
            self.tree.delete(children[0])
            
            # Get path
            path_parts = []
            curr = item
            while curr:
                txt = self.tree.item(curr, "text")
                if txt != "HKEY_CURRENT_USER":
                    path_parts.insert(0, txt)
                curr = self.tree.parent(curr)
            
            full_path = "\\".join(path_parts)
            subkeys = self.registry_handler.enum_keys(self.current_hive, full_path)
            
            if subkeys:
                for subkey in subkeys:
                    node = self.tree.insert(item, "end", text=subkey, values=[full_path + "\\" + subkey])
                    self.tree.insert(node, "end", text="Loading...") # Dummy for children

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return
        item = selected_items[0]
        
        # Construct path
        path_parts = []
        curr = item
        while curr:
            txt = self.tree.item(curr, "text")
            if txt != "HKEY_CURRENT_USER":
                path_parts.insert(0, txt)
            curr = self.tree.parent(curr)
        
        self.current_path = "\\".join(path_parts)
        self.set_status(f"HKCU\\{self.current_path}")
        self.load_values(self.current_path)

    def load_values(self, path):
        # Clear existing
        for widget in self.value_list.winfo_children():
            widget.destroy()

        # Toolbar
        toolbar = ctk.CTkFrame(self.value_list, fg_color="transparent")
        toolbar.pack(fill="x", pady=5)
        
        ctk.CTkButton(toolbar, text="⟳ Refresh", width=90, command=lambda: self.load_values(path)).pack(side="left", padx=3)
        ctk.CTkButton(toolbar, text="+ New Value", width=100, command=self.open_new_value_dialog).pack(side="left", padx=3)
        ctk.CTkButton(toolbar, text="Save Preset", width=100, command=self.prompt_save_preset).pack(side="left", padx=3)
        
        # Favorites button
        if self.favorites_manager:
            ctk.CTkButton(toolbar, text="★ Favorite", width=90, fg_color="#DAA520", hover_color="#B8860B",
                          command=self.add_to_favorites).pack(side="left", padx=3)
        
        ctk.CTkButton(toolbar, text="💾 Backup", width=90, command=self.backup_current_key).pack(side="right", padx=3)

        # Path bar
        path_row = ctk.CTkFrame(self.value_list, fg_color="transparent")
        path_row.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(path_row, text="Path:").pack(side="left", padx=(5, 2))
        path_entry = ctk.CTkEntry(path_row)
        path_entry.insert(0, self.current_path)
        path_entry.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(path_row, text="Go", width=60, command=lambda: self.go_to_path(path_entry.get())).pack(side="left", padx=5)

        # Filter
        filter_row = ctk.CTkFrame(self.value_list, fg_color="transparent")
        filter_row.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(filter_row, text="Filter:").pack(side="left", padx=(5, 2))
        filter_entry = ctk.CTkEntry(filter_row, textvariable=self.value_filter_var, placeholder_text="name/value...")
        filter_entry.pack(side="left", fill="x", expand=True, padx=5)
        filter_entry.bind("<Return>", lambda e: self.load_values(path))
        ctk.CTkButton(filter_row, text="Apply", width=70, command=lambda: self.load_values(path)).pack(side="left", padx=3)
        ctk.CTkButton(filter_row, text="Clear", width=70, command=self.clear_value_filter).pack(side="left", padx=3)

        values = self.registry_handler.read_key(self.current_hive, path)
        
        if values and isinstance(values, str):
            # Permission denied
            ctk.CTkLabel(self.value_list, text=f"⚠ {values}", text_color="orange").pack(pady=10)
            return
        
        if values:
            filter_text = self.value_filter_var.get().strip().lower()
            if filter_text:
                filtered_values = []
                for name, data, type_ in values:
                    name_text = (name or "(Default)").lower()
                    data_text = str(data).lower()
                    type_text = str(type_).lower()
                    if filter_text in name_text or filter_text in data_text or filter_text in type_text:
                        filtered_values.append((name, data, type_))
                values = filtered_values

            # Header
            header = ctk.CTkFrame(self.value_list, fg_color="transparent")
            header.pack(fill="x", pady=2)
            ctk.CTkLabel(header, text="Name", width=150, anchor="w", font=("Arial", 12, "bold")).pack(side="left", padx=5)
            ctk.CTkLabel(header, text="Type", width=100, anchor="w", font=("Arial", 12, "bold")).pack(side="left", padx=5)
            ctk.CTkLabel(header, text="Value", anchor="w", font=("Arial", 12, "bold")).pack(side="left", padx=5, fill="x", expand=True)

            for v in values:
                name, data, type_ = v
                row = ctk.CTkFrame(self.value_list)
                row.pack(fill="x", pady=2)
                
                name_lbl = ctk.CTkLabel(row, text=name if name else "(Default)", width=150, anchor="w")
                name_lbl.pack(side="left", padx=5)
                
                # Friendly type name
                type_names = {
                    winreg.REG_SZ: "REG_SZ",
                    winreg.REG_DWORD: "REG_DWORD",
                    winreg.REG_QWORD: "REG_QWORD",
                    winreg.REG_BINARY: "REG_BINARY",
                    winreg.REG_EXPAND_SZ: "REG_EXPAND_SZ",
                    winreg.REG_MULTI_SZ: "REG_MULTI_SZ",
                }
                type_str = type_names.get(type_, str(type_))
                type_lbl = ctk.CTkLabel(row, text=type_str, width=100, anchor="w")
                type_lbl.pack(side="left", padx=5)
                
                val_str = str(data)
                if len(val_str) > 60: val_str = val_str[:60] + "..."
                val_lbl = ctk.CTkLabel(row, text=val_str, anchor="w")
                val_lbl.pack(side="left", padx=5, fill="x", expand=True)
                
                edit_btn = ctk.CTkButton(row, text="Edit", width=50, command=lambda n=name, d=data, t=type_: self.open_editor(n, d, t))
                edit_btn.pack(side="right", padx=3)
                
                del_btn = ctk.CTkButton(row, text="Del", width=50, fg_color="red", hover_color="darkred", 
                                        command=lambda n=name, d=data, t=type_: self.delete_value_ui(n, d, t))
                del_btn.pack(side="right", padx=3)
        else:
            ctk.CTkLabel(self.value_list, text="No values found for this key/filter.", text_color="gray").pack(pady=10)

    def clear_value_filter(self):
        self.value_filter_var.set("")
        self.load_values(self.current_path)

    def go_to_path(self, path):
        path = path.strip().strip("\\")
        self.current_path = path
        self.set_status(f"HKCU\\{path}")
        self.load_values(path)

    def open_editor(self, name, value, val_type):
        ValueEditor(self, name, value, val_type, lambda n, v, t: self.save_value(n, v, t, old_value=value, old_type=val_type))

    def save_value(self, name, value, val_type, old_value=None, old_type=None):
        success = self.registry_handler.write_value(self.current_hive, self.current_path, name, value, val_type)
        if success:
            # Record in history
            if self.history_manager:
                self.history_manager.record("write", self.current_hive, self.current_path, name,
                                            old_value=old_value, old_type=old_type,
                                            new_value=value, new_type=val_type)
            self.set_status(f"Saved: {name}", "green")
            self.load_values(self.current_path)
        else:
            self.set_status(f"Failed to save: {name}", "red")

    def open_new_value_dialog(self):
        def on_create(name, value, val_type):
            if self.registry_handler.write_value(self.current_hive, self.current_path, name, value, val_type):
                if self.history_manager:
                    self.history_manager.record("write", self.current_hive, self.current_path, name,
                                                new_value=value, new_type=val_type)
                self.set_status(f"Created: {name}", "green")
                self.load_values(self.current_path)
            else:
                self.set_status(f"Failed to create: {name}", "red")
        
        NewValueDialog(self, on_create)

    def delete_value_ui(self, name, old_value=None, old_type=None):
        if self.registry_handler.delete_value(self.current_hive, self.current_path, name):
            if self.history_manager:
                self.history_manager.record("delete", self.current_hive, self.current_path, name,
                                            old_value=old_value, old_type=old_type)
            self.set_status(f"Deleted: {name}", "orange")
            self.load_values(self.current_path)
        else:
            self.set_status(f"Failed to delete: {name}", "red")

    def add_to_favorites(self):
        if self.favorites_manager and self.current_path:
            added = self.favorites_manager.add_favorite("HKEY_CURRENT_USER", self.current_path)
            if added:
                self.set_status(f"★ Added to favorites: {self.current_path}", "#DAA520")
            else:
                self.set_status(f"Already in favorites: {self.current_path}", "gray")

    def prompt_save_preset(self):
        dialog = ctk.CTkInputDialog(text="Enter preset name:", title="Save Preset")
        name = dialog.get_input()
        if name:
            values = self.registry_handler.read_key(self.current_hive, self.current_path)
            if values and not isinstance(values, str):
                preset_data = {
                    "hive": "HKEY_CURRENT_USER", 
                    "path": self.current_path,
                    "values": values
                }
                self.preset_manager.save_preset(name, preset_data)
                self.set_status(f"Saved preset: {name}", "green")

    def backup_current_key(self):
        full_path = "HKEY_CURRENT_USER\\" + self.current_path
        filepath = self.registry_handler.backup_key(full_path)
        if filepath:
            self.set_status(f"Backup saved: {filepath}", "green")
        else:
            self.set_status("Backup failed.", "red")
