import customtkinter as ctk
import winreg
import threading

class SearchView(ctk.CTkFrame):
    """Full search view with threaded background search."""
    
    def __init__(self, parent, registry_handler, on_navigate_to_key=None):
        super().__init__(parent, corner_radius=0)
        self.registry_handler = registry_handler
        self.on_navigate_to_key = on_navigate_to_key
        self.stop_event = threading.Event()
        self.search_thread = None
        
        self.create_widgets()
    
    def create_widgets(self):
        # Title
        ctk.CTkLabel(self, text="Registry Search", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(20, 10))
        
        # Search bar
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(search_frame, text="Query:").pack(side="left", padx=(0, 5))
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search keys and values...", width=400)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.search_entry.bind("<Return>", lambda e: self.start_search())
        
        self.search_btn = ctk.CTkButton(search_frame, text="Search", width=100, command=self.start_search)
        self.search_btn.pack(side="left", padx=5)
        
        self.stop_btn = ctk.CTkButton(search_frame, text="Stop", width=80, fg_color="red", hover_color="darkred", 
                                       command=self.stop_search, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        # Options row
        options_frame = ctk.CTkFrame(self, fg_color="transparent")
        options_frame.pack(fill="x", padx=30, pady=(0, 10))
        
        ctk.CTkLabel(options_frame, text="Start path:").pack(side="left", padx=(0, 5))
        self.start_path_entry = ctk.CTkEntry(options_frame, placeholder_text="Leave blank for root (HKCU)", width=350)
        self.start_path_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        # Status
        self.status_label = ctk.CTkLabel(self, text="", text_color="gray")
        self.status_label.pack(pady=5)
        
        # Results
        self.results_frame = ctk.CTkScrollableFrame(self)
        self.results_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))
    
    def start_search(self):
        query = self.search_entry.get().strip()
        if not query:
            return
        
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        self.stop_event.clear()
        self.search_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text="Searching...", text_color="orange")
        
        start_path = self.start_path_entry.get().strip()
        
        self.search_thread = threading.Thread(
            target=self._run_search, 
            args=(query, start_path), 
            daemon=True
        )
        self.search_thread.start()
    
    def stop_search(self):
        self.stop_event.set()
        self.status_label.configure(text="Search stopped.", text_color="yellow")
        self.search_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
    
    def _run_search(self, query, start_path):
        results = self.registry_handler.search_registry(
            winreg.HKEY_CURRENT_USER, start_path, query, self.stop_event
        )
        
        # Schedule UI update on main thread
        self.after(0, lambda: self._show_results(results))
    
    def _show_results(self, results):
        self.search_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        
        if not results:
            self.status_label.configure(text="No results found.", text_color="gray")
            return
        
        self.status_label.configure(text=f"Found {len(results)} result(s).", text_color="green")
        
        # Show up to 200 results
        for i, result in enumerate(results[:200]):
            row = ctk.CTkFrame(self.results_frame)
            row.pack(fill="x", pady=2)
            
            type_color = "#4CAF50" if result['type'] == 'Key' else "#2196F3"
            type_lbl = ctk.CTkLabel(row, text=f"[{result['type']}]", width=70, text_color=type_color, anchor="w")
            type_lbl.pack(side="left", padx=5)
            
            path_lbl = ctk.CTkLabel(row, text=result['path'], anchor="w")
            path_lbl.pack(side="left", padx=5, fill="x", expand=True)
            
            if result['type'] == 'Value':
                name_lbl = ctk.CTkLabel(row, text=f"  {result['name']}={result.get('data', '')[:40]}", 
                                        anchor="w", text_color="gray")
                name_lbl.pack(side="left", padx=5)
            
            if self.on_navigate_to_key:
                go_btn = ctk.CTkButton(row, text="Go", width=40, 
                                        command=lambda p=result['path']: self.on_navigate_to_key(p))
                go_btn.pack(side="right", padx=5)
        
        if len(results) > 200:
            ctk.CTkLabel(self.results_frame, text=f"... and {len(results) - 200} more results (search narrower).",
                         text_color="gray").pack(pady=5)
