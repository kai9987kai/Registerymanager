import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import os
import winreg
from registry_handler import RegistryHandler
from preset_manager import PresetManager

class ValueEditor(ctk.CTkToplevel):
    def __init__(self, parent, name, value, val_type, on_save):
        super().__init__(parent)
        self.title("Edit Value")
        self.geometry("400x200")
        self.on_save = on_save
        self.name = name
        self.val_type = val_type

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.name_entry = ctk.CTkEntry(self)
        self.name_entry.insert(0, name)
        self.name_entry.configure(state="disabled")
        self.name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Value:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.value_entry = ctk.CTkEntry(self)
        self.value_entry.insert(0, str(value))
        self.value_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.save_btn = ctk.CTkButton(self, text="Save", command=self.save)
        self.save_btn.grid(row=2, column=1, padx=10, pady=20, sticky="e")

    def save(self):
        new_value = self.value_entry.get()
        # Basic type conversion (improve based on val_type)
        if self.val_type == winreg.REG_DWORD:
            try:
                new_value = int(new_value)
            except ValueError:
                pass # Handle error
        self.on_save(self.name, new_value, self.val_type)
        self.destroy()

class RegistryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Advanced Registry Manager")
        self.geometry("1100x700")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.registry_handler = RegistryHandler()
        self.preset_manager = PresetManager()
        self.current_hive = winreg.HKEY_CURRENT_USER
        self.current_path = ""
        self.value_filter_var = tk.StringVar()

        self.create_sidebar()
        self.create_main_area()

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="RegManager", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_browser = ctk.CTkButton(self.sidebar_frame, text="Browser", command=self.show_browser)
        self.btn_browser.grid(row=1, column=0, padx=20, pady=10)

        self.btn_presets = ctk.CTkButton(self.sidebar_frame, text="Presets", command=self.show_presets)
        self.btn_presets.grid(row=2, column=0, padx=20, pady=10)

        self.btn_backups = ctk.CTkButton(self.sidebar_frame, text="Backups", command=self.show_backups)
        self.btn_backups.grid(row=3, column=0, padx=20, pady=10)

    def create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        self.show_browser()

    def show_browser(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        # Split into TreeView (Left) and Value List (Right)
        paned_window = tk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL, sashwidth=5, bg="#2b2b2b")
        paned_window.pack(fill="both", expand=True)

        # TreeView Frame
        tree_frame = ctk.CTkFrame(paned_window)
        paned_window.add(tree_frame)
        
        # Style Treeview to match dark theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0)
        style.map("Treeview", background=[("selected", "#1f538d")])
        
        self.tree = ttk.Treeview(tree_frame, show="tree")
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
        item = self.tree.selection()[0]
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
        self.load_values(self.current_path)

    def load_values(self, path):
        # Clear existing
        for widget in self.value_list.winfo_children():
            widget.destroy()

        # Toolbar
        toolbar = ctk.CTkFrame(self.value_list, fg_color="transparent")
        toolbar.pack(fill="x", pady=5)
        
        ctk.CTkButton(toolbar, text="Refresh", width=80, command=lambda: self.load_values(path)).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="New Value", width=90, command=self.open_new_value_dialog).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Save as Preset", width=120, command=self.prompt_save_preset).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Backup Key", width=100, command=self.backup_current_key).pack(side="right", padx=5)

        path_row = ctk.CTkFrame(self.value_list, fg_color="transparent")
        path_row.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(path_row, text="Path:").pack(side="left", padx=(5, 2))
        path_entry = ctk.CTkEntry(path_row)
        path_entry.insert(0, self.current_path)
        path_entry.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(path_row, text="Go", width=60, command=lambda: self.go_to_path(path_entry.get())).pack(side="left", padx=5)

        filter_row = ctk.CTkFrame(self.value_list, fg_color="transparent")
        filter_row.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(filter_row, text="Filter values:").pack(side="left", padx=(5, 2))
        filter_entry = ctk.CTkEntry(filter_row, textvariable=self.value_filter_var, placeholder_text="name/value contains...")
        filter_entry.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(filter_row, text="Apply", width=70, command=lambda: self.load_values(path)).pack(side="left", padx=5)
        ctk.CTkButton(filter_row, text="Clear", width=70, command=self.clear_value_filter).pack(side="left", padx=5)

        values = self.registry_handler.read_key(self.current_hive, path)
        
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
                
                type_lbl = ctk.CTkLabel(row, text=str(type_), width=100, anchor="w")
                type_lbl.pack(side="left", padx=5)
                
                val_str = str(data)
                if len(val_str) > 50: val_str = val_str[:50] + "..."
                val_lbl = ctk.CTkLabel(row, text=val_str, anchor="w")
                val_lbl.pack(side="left", padx=5, fill="x", expand=True)
                
                edit_btn = ctk.CTkButton(row, text="Edit", width=50, command=lambda n=name, d=data, t=type_: self.open_editor(n, d, t))
                edit_btn.pack(side="right", padx=5)
                
                del_btn = ctk.CTkButton(row, text="Del", width=50, fg_color="red", hover_color="darkred", command=lambda n=name: self.delete_value_ui(n))
                del_btn.pack(side="right", padx=5)
        else:
            ctk.CTkLabel(self.value_list, text="No values found for this key/filter.").pack(pady=10)

    def clear_value_filter(self):
        self.value_filter_var.set("")
        self.load_values(self.current_path)

    def go_to_path(self, path):
        path = path.strip().strip("\\")
        self.current_path = path
        self.load_values(path)

    def open_new_value_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Create New Value")
        dialog.geometry("420x240")
        dialog.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(dialog, text="Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_entry = ctk.CTkEntry(dialog)
        name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(dialog, text="Type:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        type_values = {
            "REG_SZ": winreg.REG_SZ,
            "REG_DWORD": winreg.REG_DWORD,
            "REG_QWORD": winreg.REG_QWORD,
            "REG_BINARY": winreg.REG_BINARY,
        }
        type_menu = ctk.CTkOptionMenu(dialog, values=list(type_values.keys()))
        type_menu.set("REG_SZ")
        type_menu.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(dialog, text="Value:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        value_entry = ctk.CTkEntry(dialog)
        value_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        def create_value():
            name = name_entry.get().strip()
            type_name = type_menu.get()
            raw_value = value_entry.get()
            reg_type = type_values[type_name]

            if reg_type in (winreg.REG_DWORD, winreg.REG_QWORD):
                try:
                    parsed_value = int(raw_value, 0)
                except ValueError:
                    print("Invalid integer value.")
                    return
            elif reg_type == winreg.REG_BINARY:
                try:
                    parsed_value = bytes.fromhex(raw_value.replace(" ", ""))
                except ValueError:
                    print("Invalid hex for binary value.")
                    return
            else:
                parsed_value = raw_value

            if self.registry_handler.write_value(self.current_hive, self.current_path, name, parsed_value, reg_type):
                dialog.destroy()
                self.load_values(self.current_path)
            else:
                print("Failed to create value.")

        ctk.CTkButton(dialog, text="Create", command=create_value).grid(row=3, column=1, padx=10, pady=20, sticky="e")

    def delete_value_ui(self, name):
        if self.registry_handler.delete_value(self.current_hive, self.current_path, name):
            self.load_values(self.current_path)
        else:
            print("Failed to delete value")

    def prompt_save_preset(self):
        dialog = ctk.CTkInputDialog(text="Enter preset name:", title="Save Preset")
        name = dialog.get_input()
        if name:
            values = self.registry_handler.read_key(self.current_hive, self.current_path)
            if values:
                # Structure: { "hive": ..., "path": ..., "values": [...] }
                # For simplicity, we assume HKEY_CURRENT_USER for now or store it
                preset_data = {
                    "hive": "HKEY_CURRENT_USER", # Simplified
                    "path": self.current_path,
                    "values": values # [(name, data, type), ...]
                }
                self.preset_manager.save_preset(name, preset_data)
                print(f"Preset '{name}' saved.")

    def backup_current_key(self):
        # Construct full path for reg.exe
        full_path = "HKEY_CURRENT_USER\\" + self.current_path
        filepath = self.registry_handler.backup_key(full_path)
        print(f"Backup saved to {filepath}")

    def open_editor(self, name, value, val_type):
        ValueEditor(self, name, value, val_type, self.save_value)

    def save_value(self, name, value, val_type):
        success = self.registry_handler.write_value(self.current_hive, self.current_path, name, value, val_type)
        if success:
            self.load_values(self.current_path)
        else:
            print("Failed to save")

    def show_presets(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        label = ctk.CTkLabel(self.main_frame, text="Presets Manager", font=ctk.CTkFont(size=24))
        label.pack(pady=20)
        
        # List existing presets
        presets = self.preset_manager.presets
        if not presets:
            ctk.CTkLabel(self.main_frame, text="No presets found.").pack()
        else:
            for name in presets:
                row = ctk.CTkFrame(self.main_frame)
                row.pack(fill="x", padx=50, pady=5)
                
                ctk.CTkLabel(row, text=name, font=("Arial", 14)).pack(side="left", padx=20)
                
                ctk.CTkButton(row, text="Apply", width=80, command=lambda n=name: self.apply_preset_ui(n)).pack(side="right", padx=10)
                ctk.CTkButton(row, text="Delete", width=80, fg_color="red", hover_color="darkred", command=lambda n=name: self.delete_preset_ui(n)).pack(side="right", padx=10)

    def delete_preset_ui(self, name):
        self.preset_manager.delete_preset(name)
        self.show_presets()

    def apply_preset_ui(self, name):
        data = self.preset_manager.get_preset(name)
        if not data: return
        
        path = data.get("path")
        values = data.get("values")
        
        # Assuming HKEY_CURRENT_USER for now
        hive = winreg.HKEY_CURRENT_USER
        
        print(f"Applying preset {name} to {path}...")
        for v in values:
            v_name, v_data, v_type = v
            self.registry_handler.write_value(hive, path, v_name, v_data, v_type)
        
        print("Preset applied.")
        # Optionally navigate to that path
        self.current_path = path
        self.show_browser()
        # We need to expand tree to show this path? That's complex.
        # Just showing browser with current path loaded in value list is easier.
        self.load_values(path)

    def show_backups(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        label = ctk.CTkLabel(self.main_frame, text="Backups Manager", font=ctk.CTkFont(size=24))
        label.pack(pady=20)
        
        backup_folder = "backups"
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
            
        files = [f for f in os.listdir(backup_folder) if f.endswith(".reg")]
        
        if not files:
            ctk.CTkLabel(self.main_frame, text="No backups found.").pack()
        else:
            for f in files:
                row = ctk.CTkFrame(self.main_frame)
                row.pack(fill="x", padx=50, pady=5)
                
                ctk.CTkLabel(row, text=f, font=("Arial", 14)).pack(side="left", padx=20)
                
                ctk.CTkButton(row, text="Restore", width=80, command=lambda f=f: self.restore_backup_ui(f)).pack(side="right", padx=10)

    def restore_backup_ui(self, filename):
        filepath = os.path.join("backups", filename)
        print(f"Restoring backup: {filepath}")
        success = self.registry_handler.restore_backup(filepath)
        if success:
            print("Restore successful.")
        else:
            print("Restore failed.")
