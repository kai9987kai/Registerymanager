import customtkinter as ctk
import winreg
from .styles import FONT_HEADER

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
        elif self.val_type == winreg.REG_QWORD:
            try:
                new_value = int(new_value) 
            except ValueError:
                pass
        
        # Add handling for other types if needed
        self.on_save(self.name, new_value, self.val_type)
        self.destroy()

class NewValueDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_create):
        super().__init__(parent)
        self.on_create = on_create
        self.title("Create New Value")
        self.geometry("420x240")
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.name_entry = ctk.CTkEntry(self)
        self.name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Type:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.type_values = {
            "REG_SZ": winreg.REG_SZ,
            "REG_DWORD": winreg.REG_DWORD,
            "REG_QWORD": winreg.REG_QWORD,
            "REG_BINARY": winreg.REG_BINARY,
        }
        self.type_menu = ctk.CTkOptionMenu(self, values=list(self.type_values.keys()))
        self.type_menu.set("REG_SZ")
        self.type_menu.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Value:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.value_entry = ctk.CTkEntry(self)
        self.value_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkButton(self, text="Create", command=self.create_value).grid(row=3, column=1, padx=10, pady=20, sticky="e")

    def create_value(self):
        name = self.name_entry.get().strip()
        type_name = self.type_menu.get()
        raw_value = self.value_entry.get()
        reg_type = self.type_values[type_name]

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

        self.on_create(name, parsed_value, reg_type)
        self.destroy()
