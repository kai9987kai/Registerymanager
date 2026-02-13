import customtkinter as ctk

class FavoritesView(ctk.CTkFrame):
    """View for managing and navigating to favorite registry keys."""
    
    def __init__(self, parent, favorites_manager, on_navigate_to_key=None):
        super().__init__(parent, corner_radius=0)
        self.favorites_manager = favorites_manager
        self.on_navigate_to_key = on_navigate_to_key
        
        self.create_widgets()
    
    def create_widgets(self):
        ctk.CTkLabel(self, text="Favorites", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(20, 10))
        
        # Add favorite manually
        add_frame = ctk.CTkFrame(self, fg_color="transparent")
        add_frame.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(add_frame, text="Path:").pack(side="left", padx=(0, 5))
        self.path_entry = ctk.CTkEntry(add_frame, placeholder_text="Software\\Microsoft\\...", width=350)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(add_frame, text="Label:").pack(side="left", padx=(10, 5))
        self.label_entry = ctk.CTkEntry(add_frame, placeholder_text="My Favorite", width=150)
        self.label_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(add_frame, text="Add", width=80, command=self.add_favorite).pack(side="left", padx=5)
        
        # Favorites list
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=30, pady=(10, 20))
        
        self.refresh_list()
    
    def add_favorite(self):
        path = self.path_entry.get().strip()
        label = self.label_entry.get().strip() or None
        if path:
            self.favorites_manager.add_favorite("HKEY_CURRENT_USER", path, label)
            self.path_entry.delete(0, "end")
            self.label_entry.delete(0, "end")
            self.refresh_list()
    
    def refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        favorites = self.favorites_manager.get_favorites()
        
        if not favorites:
            ctk.CTkLabel(self.list_frame, text="No favorites yet. Add one above or use the ★ button in the browser.",
                         text_color="gray").pack(pady=20)
            return
        
        for i, fav in enumerate(favorites):
            row = ctk.CTkFrame(self.list_frame)
            row.pack(fill="x", pady=3)
            
            ctk.CTkLabel(row, text="★", text_color="#FFD700", width=25).pack(side="left", padx=(5, 2))
            ctk.CTkLabel(row, text=fav.get("label", ""), font=("Arial", 13, "bold"), anchor="w", width=150).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=fav.get("path", ""), anchor="w", text_color="gray").pack(side="left", padx=5, fill="x", expand=True)
            
            if self.on_navigate_to_key:
                ctk.CTkButton(row, text="Go", width=40, 
                              command=lambda p=fav.get("path", ""): self.on_navigate_to_key(p)).pack(side="right", padx=5)
            
            ctk.CTkButton(row, text="✕", width=35, fg_color="red", hover_color="darkred",
                          command=lambda idx=i: self.remove_favorite(idx)).pack(side="right", padx=5)
    
    def remove_favorite(self, index):
        self.favorites_manager.remove_favorite(index)
        self.refresh_list()
