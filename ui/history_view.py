import customtkinter as ctk

class HistoryView(ctk.CTkFrame):
    """View showing the session's change history with undo/redo buttons."""
    
    def __init__(self, parent, history_manager, on_undo=None, on_redo=None):
        super().__init__(parent, corner_radius=0)
        self.history_manager = history_manager
        self.on_undo = on_undo
        self.on_redo = on_redo
        
        self.create_widgets()
    
    def create_widgets(self):
        ctk.CTkLabel(self, text="Change History", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(20, 10))
        
        # Undo/Redo buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=10)
        
        self.undo_btn = ctk.CTkButton(btn_frame, text="↶ Undo", width=100, command=self._do_undo)
        self.undo_btn.pack(side="left", padx=5)
        
        self.redo_btn = ctk.CTkButton(btn_frame, text="↷ Redo", width=100, command=self._do_redo)
        self.redo_btn.pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="Refresh", width=80, command=self.refresh_list).pack(side="right", padx=5)
        
        # History list
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=30, pady=(10, 20))
        
        self.refresh_list()
    
    def _do_undo(self):
        if self.on_undo:
            self.on_undo()
        self.refresh_list()
    
    def _do_redo(self):
        if self.on_redo:
            self.on_redo()
        self.refresh_list()
    
    def refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        # Update button states
        self.undo_btn.configure(state="normal" if self.history_manager.can_undo() else "disabled")
        self.redo_btn.configure(state="normal" if self.history_manager.can_redo() else "disabled")
        
        history = self.history_manager.get_history()
        
        if not history:
            ctk.CTkLabel(self.list_frame, text="No changes recorded in this session.",
                         text_color="gray").pack(pady=20)
            return
        
        for entry in history:
            row = ctk.CTkFrame(self.list_frame)
            row.pack(fill="x", pady=2)
            
            action = entry.get("action", "?")
            action_colors = {"write": "#4CAF50", "delete": "#F44336", "create_key": "#2196F3"}
            color = action_colors.get(action, "white")
            
            ctk.CTkLabel(row, text=f"[{action.upper()}]", width=80, text_color=color, anchor="w").pack(side="left", padx=5)
            
            path_text = entry.get("path", "")
            name_text = entry.get("name", "")
            detail = f"{path_text} \\ {name_text}" if name_text else path_text
            ctk.CTkLabel(row, text=detail, anchor="w").pack(side="left", padx=5, fill="x", expand=True)
            
            ts = entry.get("timestamp", "")
            if ts:
                # Show just time part
                time_part = ts.split("T")[-1][:8] if "T" in ts else ts
                ctk.CTkLabel(row, text=time_part, text_color="gray", width=80).pack(side="right", padx=5)
