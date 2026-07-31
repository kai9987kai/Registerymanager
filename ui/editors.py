import customtkinter as ctk
from registry_codec import (
    REGISTRY_TYPE_NAMES,
    RegistryCodecError,
    format_registry_value,
    parse_registry_value,
    registry_type_name,
)


class _RegistryValueDialog(ctk.CTkToplevel):
    """Shared value field and inline validation behavior."""

    def _show_modal(self, parent):
        try:
            self.transient(parent.winfo_toplevel())
        except Exception:
            pass
        self.after(50, self._activate_modal)

    def _activate_modal(self):
        try:
            self.lift()
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def _create_value_field(self, row):
        self.value_entry = ctk.CTkTextbox(self, height=90, wrap="none")
        self.value_entry.grid(
            row=row, column=1, padx=10, pady=10, sticky="nsew"
        )

    def _set_value_text(self, value):
        self.value_entry.delete("1.0", "end")
        self.value_entry.insert("1.0", value)

    def _get_value_text(self):
        return self.value_entry.get("1.0", "end-1c")

    def _set_error(self, message):
        self.error_label.configure(text=message)

    def _run_callback(self, callback, *args):
        try:
            result = callback(*args)
        except Exception as exc:
            self._set_error(f"Operation failed: {exc}")
            return False

        if result is False:
            self._set_error("The registry operation did not complete.")
            return False
        return True


class ValueEditor(_RegistryValueDialog):
    def __init__(self, parent, name, value, val_type, on_save):
        super().__init__(parent)
        self.title("Edit Value")
        self.geometry("500x320")
        self.on_save = on_save
        self.name = name
        self.val_type = val_type

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.name_entry = ctk.CTkEntry(self)
        self.name_entry.insert(0, name or "")
        self.name_entry.configure(state="disabled")
        self.name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Type:").grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")
        try:
            type_text = registry_type_name(val_type)
        except RegistryCodecError:
            type_text = str(val_type)
        ctk.CTkLabel(self, text=type_text, anchor="w").grid(
            row=1, column=1, padx=10, pady=(0, 10), sticky="ew"
        )

        ctk.CTkLabel(self, text="Value:").grid(row=2, column=0, padx=10, pady=10, sticky="nw")
        self._create_value_field(row=2)

        initial_error = ""
        try:
            initial_text = format_registry_value(value, val_type)
        except RegistryCodecError as exc:
            initial_text = str(value)
            initial_error = str(exc)
        self._set_value_text(initial_text)

        self.error_label = ctk.CTkLabel(
            self, text=initial_error, text_color="#F44336", anchor="w", wraplength=380
        )
        self.error_label.grid(row=3, column=1, padx=10, pady=(0, 5), sticky="ew")

        self.save_btn = ctk.CTkButton(self, text="Save", command=self.save)
        self.save_btn.grid(row=4, column=1, padx=10, pady=(5, 15), sticky="e")
        self._show_modal(parent)

    def save(self):
        self._set_error("")
        try:
            new_value = parse_registry_value(
                self._get_value_text(), self.val_type
            )
        except RegistryCodecError as exc:
            self._set_error(str(exc))
            return

        if self._run_callback(
            self.on_save, self.name, new_value, self.val_type
        ):
            self.destroy()


class NewValueDialog(_RegistryValueDialog):
    def __init__(self, parent, on_create):
        super().__init__(parent)
        self.on_create = on_create
        self.title("Create New Value")
        self.geometry("500x330")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.name_entry = ctk.CTkEntry(self)
        self.name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Type:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.type_values = {
            name: value_type
            for value_type, name in REGISTRY_TYPE_NAMES.items()
        }
        self.type_menu = ctk.CTkOptionMenu(self, values=list(self.type_values.keys()))
        self.type_menu.set("REG_SZ")
        self.type_menu.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Value:").grid(row=2, column=0, padx=10, pady=10, sticky="nw")
        self._create_value_field(row=2)

        self.error_label = ctk.CTkLabel(
            self, text="", text_color="#F44336", anchor="w", wraplength=380
        )
        self.error_label.grid(row=3, column=1, padx=10, pady=(0, 5), sticky="ew")

        ctk.CTkButton(self, text="Create", command=self.create_value).grid(
            row=4, column=1, padx=10, pady=(5, 15), sticky="e"
        )
        self._show_modal(parent)

    def create_value(self):
        self._set_error("")
        name = self.name_entry.get().strip()
        type_name = self.type_menu.get()
        reg_type = self.type_values[type_name]

        try:
            parsed_value = parse_registry_value(
                self._get_value_text(), reg_type
            )
        except RegistryCodecError as exc:
            self._set_error(str(exc))
            return

        if self._run_callback(self.on_create, name, parsed_value, reg_type):
            self.destroy()
