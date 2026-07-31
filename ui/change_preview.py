import tkinter as tk

import customtkinter as ctk

from change_manager import ChangeClassification
from registry_codec import RegistryCodecError, format_registry_value, registry_type_name


_CHANGE_STYLES = {
    ChangeClassification.ADD: ("ADD", "#2EAD68"),
    ChangeClassification.MODIFY: ("MODIFY", "#D99A2B"),
    ChangeClassification.DELETE: ("DELETE", "#D84A4A"),
    ChangeClassification.NO_CHANGE: ("NO CHANGE", "#7A8491"),
}


def _snapshot_text(snapshot):
    if not snapshot.exists:
        return "Not present"
    try:
        type_name = registry_type_name(snapshot.value_type)
        value_text = format_registry_value(snapshot.value, snapshot.value_type)
    except RegistryCodecError:
        type_name = str(snapshot.value_type)
        value_text = repr(snapshot.value)
    value_text = value_text.replace("\r", "").replace("\n", " · ")
    if len(value_text) > 120:
        value_text = value_text[:117] + "..."
    return f"{type_name}  |  {value_text or '<empty>'}"


class ChangePreviewDialog(ctk.CTkToplevel):
    """Review a ChangePlan before any registry write occurs."""

    def __init__(self, parent, plan, on_apply, backup_default=True):
        super().__init__(parent)
        self.plan = plan
        self.on_apply = on_apply
        self.preview = plan.seal().preview()

        self.title(f"Review changes — {plan.label}")
        self.geometry("980x620")
        self.minsize(760, 500)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        try:
            self.transient(parent.winfo_toplevel())
        except (AttributeError, tk.TclError):
            pass

        ctk.CTkLabel(
            self,
            text=plan.label,
            font=ctk.CTkFont(size=23, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, padx=24, pady=(22, 4), sticky="ew")

        counts = self.preview.counts
        summary = "  •  ".join(
            (
                f"{counts[ChangeClassification.ADD]} add",
                f"{counts[ChangeClassification.MODIFY]} modify",
                f"{counts[ChangeClassification.DELETE]} delete",
                f"{counts[ChangeClassification.NO_CHANGE]} unchanged",
            )
        )
        ctk.CTkLabel(self, text=summary, text_color="#AAB2BD", anchor="w").grid(
            row=1, column=0, padx=24, pady=(0, 10), sticky="ew"
        )

        ctk.CTkLabel(
            self,
            text=(
                "Current state will be checked again before every write. If a later step fails, "
                "completed steps are restored in reverse order."
            ),
            text_color="#86B7E7",
            anchor="w",
            wraplength=900,
        ).grid(row=2, column=0, padx=24, pady=(0, 10), sticky="ew")

        changes_frame = ctk.CTkScrollableFrame(self, corner_radius=8)
        changes_frame.grid(row=3, column=0, padx=24, pady=4, sticky="nsew")

        if not self.preview.changes:
            ctk.CTkLabel(
                changes_frame, text="This plan contains no operations.", text_color="gray"
            ).pack(pady=30)
        else:
            for change in self.preview.changes:
                self._add_change_row(changes_frame, change)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, padx=24, pady=(10, 20), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        self.backup_var = tk.BooleanVar(master=self, value=backup_default)
        self.backup_checkbox = ctk.CTkCheckBox(
            footer,
            text="Create recovery export before applying",
            variable=self.backup_var,
        )
        self.backup_checkbox.grid(row=0, column=0, sticky="w")

        self.error_label = ctk.CTkLabel(
            footer, text="", text_color="#F05A5A", anchor="w", wraplength=650
        )
        self.error_label.grid(row=1, column=0, pady=(8, 0), sticky="ew")

        ctk.CTkButton(footer, text="Cancel", width=100, command=self.destroy).grid(
            row=0, column=1, rowspan=2, padx=(8, 0), sticky="e"
        )
        self.apply_button = ctk.CTkButton(
            footer,
            text=f"Apply {len(self.preview.effective_changes)} change(s)",
            width=160,
            command=self._apply,
            state="normal" if self.preview.has_changes else "disabled",
        )
        self.apply_button.grid(row=0, column=2, rowspan=2, padx=(8, 0), sticky="e")

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(50, self._focus_dialog)

    def _focus_dialog(self):
        try:
            self.grab_set()
            self.focus_force()
        except tk.TclError:
            pass

    def _add_change_row(self, parent, change):
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=4, padx=3)
        row.grid_columnconfigure(1, weight=1)

        badge, color = _CHANGE_STYLES[change.classification]
        ctk.CTkLabel(
            row,
            text=badge,
            width=82,
            text_color=color,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, rowspan=3, padx=10, pady=10, sticky="nw")
        ctk.CTkLabel(
            row,
            text=change.location,
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=1, padx=(0, 10), pady=(8, 2), sticky="ew")
        ctk.CTkLabel(
            row,
            text=f"Before:  {_snapshot_text(change.before)}",
            anchor="w",
            text_color="#AAB2BD",
        ).grid(row=1, column=1, padx=(0, 10), pady=1, sticky="ew")
        ctk.CTkLabel(
            row,
            text=f"After:   {_snapshot_text(change.after)}",
            anchor="w",
            text_color="#DCE3EA",
        ).grid(row=2, column=1, padx=(0, 10), pady=(1, 8), sticky="ew")

    def _apply(self):
        self.error_label.configure(text="")
        self.apply_button.configure(state="disabled", text="Applying...")
        self.update_idletasks()
        try:
            result = self.on_apply(self.plan, bool(self.backup_var.get()))
        except Exception as exc:
            self.error_label.configure(text=f"Apply failed: {exc}")
            if getattr(self.plan, "executed", False):
                self.apply_button.configure(state="disabled", text="Review again required")
            else:
                self.apply_button.configure(
                    state="normal", text=f"Apply {len(self.preview.effective_changes)} change(s)"
                )
            return

        success = getattr(result, "success", bool(result))
        if success:
            self.destroy()
            return

        message = getattr(result, "message", None) or "The change plan was not applied."
        self.error_label.configure(text=message)
        if getattr(self.plan, "executed", False):
            self.apply_button.configure(state="disabled", text="Review again required")
        else:
            self.apply_button.configure(
                state="normal", text=f"Apply {len(self.preview.effective_changes)} change(s)"
            )
