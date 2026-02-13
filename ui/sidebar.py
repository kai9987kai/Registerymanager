import customtkinter as ctk
from .styles import FONT_LOGO, SIDEBAR_WIDTH

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, on_navigate):
        super().__init__(parent, width=SIDEBAR_WIDTH, corner_radius=0)
        self.on_navigate = on_navigate
        self.grid_rowconfigure(7, weight=1)

        self.logo_label = ctk.CTkLabel(self, text="RegManager", font=FONT_LOGO)
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_browser = ctk.CTkButton(self, text="🗂  Browser", command=lambda: self.on_navigate("browser"), anchor="w")
        self.btn_browser.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.btn_search = ctk.CTkButton(self, text="🔍  Search", command=lambda: self.on_navigate("search"), anchor="w")
        self.btn_search.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        self.btn_favorites = ctk.CTkButton(self, text="★  Favorites", command=lambda: self.on_navigate("favorites"), anchor="w")
        self.btn_favorites.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        self.btn_presets = ctk.CTkButton(self, text="⚙  Presets", command=lambda: self.on_navigate("presets"), anchor="w")
        self.btn_presets.grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        self.btn_backups = ctk.CTkButton(self, text="💾  Backups", command=lambda: self.on_navigate("backups"), anchor="w")
        self.btn_backups.grid(row=5, column=0, padx=20, pady=5, sticky="ew")

        self.btn_history = ctk.CTkButton(self, text="↶  History", command=lambda: self.on_navigate("history"), anchor="w")
        self.btn_history.grid(row=6, column=0, padx=20, pady=5, sticky="ew")

        # Appearance mode toggle at the bottom
        self.appearance_menu = ctk.CTkOptionMenu(self, values=["System", "Dark", "Light"],
                                                  command=self.change_appearance)
        self.appearance_menu.set("System")
        self.appearance_menu.grid(row=8, column=0, padx=20, pady=(10, 20), sticky="s")

    def change_appearance(self, mode):
        ctk.set_appearance_mode(mode)
