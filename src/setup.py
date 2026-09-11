import sys
import os
import json
import ctypes
import threading
import webbrowser
import subprocess
import urllib.request
import urllib.parse
import tkinter as tk
from tkinter import ttk, messagebox

import config_manager
import history_manager
import tts_helper

class MemoryChecker:
    @staticmethod
    def get_system_ram_gb():
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            total_gb = stat.ullTotalPhys / (1024 ** 3)
            avail_gb = stat.ullAvailPhys / (1024 ** 3)
            return round(total_gb, 1), round(avail_gb, 1)
        except Exception:
            return None, None

class SetupApp:
    def __init__(self):
        self.config = config_manager.load_config()
        self.root = tk.Tk()
        self.root.title("wat-this Setup & Maintenance")
        self.root.geometry("740x640")
        self.root.minsize(680, 580)
        self.root.configure(bg="#181825")

        if os.path.exists(config_manager.ICON_ICO_PATH):
            try:
                self.root.iconbitmap(config_manager.ICON_ICO_PATH)
            except Exception:
                pass

        self.installed_models = []
        self.is_pulling = False
        self.history_items = []
        
        self.init_styles()
        self.init_ui()
        self.check_ollama_status()

    def init_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure(".", background="#181825", foreground="#CDD6F4", font=("Segoe UI", 10))
        self.style.configure("TNotebook", background="#181825", borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#11111B", foreground="#A6ADC8", padding=[14, 8], font=("Segoe UI", 9, "bold"))
        self.style.map("TNotebook.Tab",
            background=[("selected", "#1E1E2E")],
            foreground=[("selected", "#89B4FA")]
        )
        self.style.configure("TFrame", background="#1E1E2E")
        self.style.configure("Card.TFrame", background="#11111B", relief="solid", borderwidth=1)
        self.style.configure("TLabel", background="#1E1E2E", foreground="#CDD6F4")
        self.style.configure("Card.TLabel", background="#11111B", foreground="#CDD6F4")
        self.style.configure("Muted.TLabel", background="#11111B", foreground="#A6ADC8", font=("Segoe UI", 9))
        self.style.configure("TProgressbar", thickness=16, troughcolor="#11111B", background="#89B4FA")
        
        # Treeview styling for history
        self.style.configure("Treeview", background="#11111B", foreground="#CDD6F4", fieldbackground="#11111B", rowheight=26)
        self.style.map("Treeview", background=[("selected", "#313244")], foreground=[("selected", "#89B4FA")])
        self.style.configure("Treeview.Heading", background="#181825", foreground="#89B4FA", font=("Segoe UI", 9, "bold"))

    def init_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#181825")
        header.pack(fill="x", padx=20, pady=(16, 10))

        title_lbl = tk.Label(
            header,
            text="wat-this Setup & Maintenance",
            font=("Segoe UI Variable Display", 15, "bold"),
            bg="#181825",
            fg="#CDD6F4"
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            header,
            text="Manage local AI models, review query notebook, and configure ambient desktop workflows.",
            font=("Segoe UI", 9),
            bg="#181825",
            fg="#A6ADC8"
        )
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # Tab Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=4)

        self.tab_engine = ttk.Frame(self.notebook)
        self.tab_tiers = ttk.Frame(self.notebook)
        self.tab_history = ttk.Frame(self.notebook)
        self.tab_prefs = ttk.Frame(self.notebook)
        self.tab_uninstall = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_engine, text=" 1. Diagnostics ")
        self.notebook.add(self.tab_tiers, text=" 2. Models & Install ")
        self.notebook.add(self.tab_history, text=" 3. Knowledge Notebook ")
        self.notebook.add(self.tab_prefs, text=" 4. Preferences & Modes ")
        self.notebook.add(self.tab_uninstall, text=" 5. Storage & Cleanup ")

        self.build_engine_tab()
        self.build_tiers_tab()
        self.build_history_tab()
        self.build_prefs_tab()
        self.build_uninstall_tab()

        # Bottom Bar
        bottom = tk.Frame(self.root, bg="#181825")
        bottom.pack(fill="x", padx=20, pady=12)

        self.status_lbl = tk.Label(bottom, text="Ready.", font=("Segoe UI", 9), bg="#181825", fg="#89B4FA")
        self.status_lbl.pack(side="left")

        close_btn = tk.Button(
            bottom, text="Close", font=("Segoe UI", 9),
            bg="#313244", fg="#CDD6F4", activebackground="#45475A", activeforeground="#CDD6F4",
            bd=0, padx=14, pady=6, cursor="hand2", command=self.root.destroy
        )
        close_btn.pack(side="right", padx=(8, 0))

        launch_btn = tk.Button(
            bottom, text="Launch wat-this", font=("Segoe UI", 9, "bold"),
            bg="#89B4FA", fg="#11111B", activebackground="#B4BEFE", activeforeground="#11111B",
            bd=0, padx=16, pady=6, cursor="hand2", command=self.launch_wat_this
        )
        launch_btn.pack(side="right")

    def build_engine_tab(self):
        container = tk.Frame(self.tab_engine, bg="#1E1E2E")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        # Hardware Diagnostic Box
        box_ram = tk.Frame(container, bg="#11111B", bd=1, relief="solid", highlightbackground="#313244", highlightthickness=1)
        box_ram.pack(fill="x", pady=(0, 14))

        tk.Label(box_ram, text="HOST HARDWARE TELEMETRY", font=("Segoe UI", 9, "bold"), bg="#11111B", fg="#89B4FA").pack(anchor="w", padx=12, pady=(10, 4))

        tot_ram, avail_ram = MemoryChecker.get_system_ram_gb()
        ram_text = f"Installed Physical RAM: {tot_ram} GB  |  Currently Available: {avail_ram} GB" if tot_ram else "RAM Detection: Standard Host"
        tk.Label(box_ram, text=ram_text, font=("Segoe UI", 10), bg="#11111B", fg="#CDD6F4").pack(anchor="w", padx=12, pady=(0, 4))

        rec_tier = "Normal"
        if avail_ram and avail_ram < 3.0:
            rec_tier = "Lite (Sub-2GB)"
        elif avail_ram and avail_ram > 8.0:
            rec_tier = "Extreme (Mistral 7B) or Normal"
        tk.Label(box_ram, text=f"Recommended Profile: {rec_tier}", font=("Segoe UI", 9, "italic"), bg="#11111B", fg="#A6E3A1").pack(anchor="w", padx=12, pady=(0, 10))

        # Ollama Service Diagnostics
        box_ollama = tk.Frame(container, bg="#11111B", bd=1, relief="solid", highlightbackground="#313244", highlightthickness=1)
        box_ollama.pack(fill="x", pady=(0, 14))

        tk.Label(box_ollama, text="LOCAL OLLAMA ENGINE STATUS", font=("Segoe UI", 9, "bold"), bg="#11111B", fg="#89B4FA").pack(anchor="w", padx=12, pady=(10, 4))

        self.lbl_ollama_status = tk.Label(box_ollama, text="Checking Ollama Daemon...", font=("Segoe UI", 10), bg="#11111B", fg="#F9E2AF")
        self.lbl_ollama_status.pack(anchor="w", padx=12, pady=(0, 6))

        btn_row = tk.Frame(box_ollama, bg="#11111B")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        tk.Button(
            btn_row, text="Refresh Status", font=("Segoe UI", 8),
            bg="#313244", fg="#CDD6F4", bd=0, padx=10, pady=4, cursor="hand2", command=self.check_ollama_status
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_row, text="Start Ollama Server", font=("Segoe UI", 8),
            bg="#313244", fg="#CDD6F4", bd=0, padx=10, pady=4, cursor="hand2", command=self.spawn_ollama_serve
        ).pack(side="left")

    def build_tiers_tab(self):
        container = tk.Frame(self.tab_tiers, bg="#1E1E2E")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        tiers = self.config.get("tiers", {})
        self.selected_tier = tk.StringVar(value=self.config.get("active_tier", "normal"))
        self.tier_cards = {}
        self.badge_labels = {}

        for key, spec in tiers.items():
            card = tk.Frame(container, bg="#11111B", bd=1, relief="solid", highlightbackground="#313244", highlightthickness=1)
            card.pack(fill="x", pady=4)
            self.tier_cards[key] = card

            row1 = tk.Frame(card, bg="#11111B")
            row1.pack(fill="x", padx=10, pady=(8, 2))

            rb = tk.Radiobutton(
                row1, text=f"{spec.get('name')}  —  {spec.get('ram_target')}",
                variable=self.selected_tier, value=key, font=("Segoe UI", 10, "bold"),
                bg="#11111B", fg="#CDD6F4", selectcolor="#1E1E2E", activebackground="#11111B",
                command=self.update_tier_highlights
            )
            rb.pack(side="left")

            badge = tk.Label(row1, text="CHECKING", font=("Segoe UI", 8, "bold"), bg="#1E1E2E", fg="#A6ADC8", padx=6, pady=1)
            badge.pack(side="right")
            self.badge_labels[key] = badge

            family_info = f"[{spec.get('family', '')}] " if spec.get("family") else ""
            meta = f"{family_info}Model: {spec.get('model')} | Web Context: {'Enabled' if spec.get('web_search') else 'Disabled (Offline)'}"
            tk.Label(card, text=meta, font=("Segoe UI", 8, "bold"), bg="#11111B", fg="#89B4FA").pack(anchor="w", padx=32, pady=(0, 2))

            tk.Label(card, text=spec.get("description", ""), font=("Segoe UI", 9), bg="#11111B", fg="#BAC2DE", wraplength=580, justify="left").pack(anchor="w", padx=32, pady=(0, 8))

        self.update_tier_highlights()

        # Download / Progress Box
        p_box = tk.Frame(container, bg="#11111B", bd=1, relief="solid", highlightbackground="#313244", highlightthickness=1)
        p_box.pack(fill="x", pady=(10, 0))

        self.p_bar = ttk.Progressbar(p_box, mode="determinate")
        self.p_bar.pack(fill="x", padx=12, pady=(10, 4))

        self.p_status = tk.Label(p_box, text="Ready.", font=("Segoe UI", 9), bg="#11111B", fg="#A6ADC8")
        self.p_status.pack(anchor="w", padx=12, pady=(0, 8))

        act_row = tk.Frame(p_box, bg="#11111B")
        act_row.pack(fill="x", padx=12, pady=(0, 10))

        self.install_btn = tk.Button(
            act_row, text="Install / Pull Selected Tier Model", font=("Segoe UI", 9, "bold"),
            bg="#89B4FA", fg="#11111B", bd=0, padx=14, pady=6, cursor="hand2", command=self.start_model_pull
        )
        self.install_btn.pack(side="left", padx=(0, 8))

        set_btn = tk.Button(
            act_row, text="Set as Active Tier", font=("Segoe UI", 9),
            bg="#313244", fg="#CDD6F4", bd=0, padx=12, pady=6, cursor="hand2", command=self.save_active_tier
        )
        set_btn.pack(side="left")

    def build_history_tab(self):
        container = tk.Frame(self.tab_history, bg="#1E1E2E")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        # Top Bar (Search + Action Buttons)
        top_bar = tk.Frame(container, bg="#1E1E2E")
        top_bar.pack(fill="x", pady=(0, 8))

        tk.Label(top_bar, text="Filter:", font=("Segoe UI", 9, "bold"), bg="#1E1E2E", fg="#A6ADC8").pack(side="left", padx=(0, 6))
        self.history_search_entry = tk.Entry(top_bar, font=("Segoe UI", 9), bg="#11111B", fg="#CDD6F4", insertbackground="#CDD6F4", bd=1, relief="solid")
        self.history_search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.history_search_entry.bind("<KeyRelease>", lambda e: self.filter_history())

        tk.Button(
            top_bar, text="Clear Filter", font=("Segoe UI", 8),
            bg="#313244", fg="#CDD6F4", bd=0, padx=8, pady=3, cursor="hand2",
            command=self.clear_history_filter
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            top_bar, text="Export to Markdown", font=("Segoe UI", 8, "bold"),
            bg="#A6E3A1", fg="#11111B", bd=0, padx=10, pady=3, cursor="hand2",
            command=self.export_history_action
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            top_bar, text="Clear All", font=("Segoe UI", 8),
            bg="#F38BA8", fg="#11111B", bd=0, padx=8, pady=3, cursor="hand2",
            command=self.clear_all_history_action
        ).pack(side="left")

        # Split pane: Treeview above, Preview below
        paned = tk.PanedWindow(container, orient="vertical", bg="#313244", bd=1, sashwidth=4)
        paned.pack(fill="both", expand=True)

        tree_frame = tk.Frame(paned, bg="#11111B")
        cols = ("timestamp", "mode", "tier", "snippet")
        self.history_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=6)
        self.history_tree.heading("timestamp", text="Time")
        self.history_tree.heading("mode", text="Mode")
        self.history_tree.heading("tier", text="Tier")
        self.history_tree.heading("snippet", text="Highlighted Snippet")

        self.history_tree.column("timestamp", width=130, anchor="w")
        self.history_tree.column("mode", width=80, anchor="center")
        self.history_tree.column("tier", width=70, anchor="center")
        self.history_tree.column("snippet", width=420, anchor="w")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=tree_scroll.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        self.history_tree.bind("<<TreeviewSelect>>", self.on_history_select)

        paned.add(tree_frame)

        # Preview Frame
        preview_frame = tk.Frame(paned, bg="#11111B")
        tk.Label(preview_frame, text="Explanation Output Preview:", font=("Segoe UI", 8, "bold"), bg="#11111B", fg="#89B4FA").pack(anchor="w", padx=8, pady=(4, 2))
        
        self.history_preview_txt = tk.Text(
            preview_frame, font=("Segoe UI", 9), bg="#181825", fg="#CDD6F4",
            bd=0, padx=8, pady=6, wrap="word", height=6
        )
        self.history_preview_txt.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        paned.add(preview_frame)
        self.refresh_history_list()

    def refresh_history_list(self, query=None):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        self.history_items = history_manager.get_history(limit=100, query=query)
        for item in self.history_items:
            snip_clean = item.get("snippet", "").replace("\n", " ")[:80]
            self.history_tree.insert(
                "", "end", iid=str(item.get("id")),
                values=(item.get("timestamp"), item.get("mode", "explain").upper(), item.get("tier", "normal").upper(), snip_clean)
            )

    def filter_history(self):
        q = self.history_search_entry.get().strip()
        self.refresh_history_list(query=q if q else None)

    def clear_history_filter(self):
        self.history_search_entry.delete(0, tk.END)
        self.refresh_history_list()

    def on_history_select(self, event):
        selected = self.history_tree.selection()
        if not selected:
            return
        entry_id = selected[0]
        for item in self.history_items:
            if str(item.get("id")) == str(entry_id):
                self.history_preview_txt.delete("1.0", tk.END)
                resp = item.get("response", "")
                meta = f"Model: {item.get('model', 'Local AI')} | Tier: {item.get('tier', '').upper()} | Latency: {item.get('latency_s', '')}s\n"
                meta += "-" * 50 + "\n\n"
                self.history_preview_txt.insert(tk.END, meta + resp)
                break

    def export_history_action(self):
        export_file = os.path.join(config_manager.PROJECT_ROOT, "wat_this_notebook.md")
        success, path_or_err = history_manager.export_to_markdown(export_file)
        if success:
            messagebox.showinfo("Export Success", f"Knowledge notebook saved to:\n{path_or_err}")
            try:
                os.startfile(export_file)
            except Exception:
                pass
        else:
            messagebox.showerror("Export Failed", f"Could not export notebook: {path_or_err}")

    def clear_all_history_action(self):
        if messagebox.askyesno("Clear History", "Permanently delete all stored queries and explanations?"):
            history_manager.clear_history()
            self.refresh_history_list()
            self.history_preview_txt.delete("1.0", tk.END)
            messagebox.showinfo("Cleared", "History has been wiped.")

    def build_prefs_tab(self):
        container = tk.Frame(self.tab_prefs, bg="#1E1E2E")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        # Autostart with Windows Box
        as_frame = tk.Frame(container, bg="#11111B", bd=1, relief="solid", highlightbackground="#313244", highlightthickness=1)
        as_frame.pack(fill="x", pady=(0, 10))

        self.var_autostart = tk.BooleanVar(value=config_manager.is_windows_autostart_enabled())
        tk.Checkbutton(
            as_frame, text="Start wat-this automatically when Windows starts",
            variable=self.var_autostart, font=("Segoe UI", 9, "bold"), bg="#11111B", fg="#CDD6F4",
            selectcolor="#1E1E2E", activebackground="#11111B"
        ).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(as_frame, text="Registers a shortcut in Windows Startup directory. Zero registry modifications.", font=("Segoe UI", 8), bg="#11111B", fg="#6C7086").pack(anchor="w", padx=12, pady=(0, 10))

        # Text to Speech Box
        tts_frame = tk.Frame(container, bg="#11111B", bd=1, relief="solid", highlightbackground="#313244", highlightthickness=1)
        tts_frame.pack(fill="x", pady=(0, 10))

        self.var_tts = tk.BooleanVar(value=self.config.get("tts_enabled", False))
        tk.Checkbutton(
            tts_frame, text="Automatically read explanations aloud (Offline Windows TTS)",
            variable=self.var_tts, font=("Segoe UI", 9, "bold"), bg="#11111B", fg="#CDD6F4",
            selectcolor="#1E1E2E", activebackground="#11111B"
        ).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(tts_frame, text="You can also press Ctrl+Alt+S anytime on an open HUD to listen on demand.", font=("Segoe UI", 8), bg="#11111B", fg="#6C7086").pack(anchor="w", padx=12, pady=(0, 10))

        # Hotkeys Table Frame
        hk_box = tk.Frame(container, bg="#11111B", bd=1, relief="solid", highlightbackground="#313244", highlightthickness=1)
        hk_box.pack(fill="x", pady=(0, 10))

        tk.Label(hk_box, text="ACTIVE GLOBAL HOTKEYS & WORKFLOW MODES", font=("Segoe UI", 9, "bold"), bg="#11111B", fg="#89B4FA").pack(anchor="w", padx=12, pady=(10, 6))

        modes = config_manager.get_modes()
        for m_key, m_info in modes.items():
            row = tk.Frame(hk_box, bg="#11111B")
            row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=f"• {m_info.get('name')}:", font=("Segoe UI", 9), bg="#11111B", fg="#BAC2DE", width=24, anchor="w").pack(side="left")
            tk.Label(row, text=m_info.get('hotkey', '').upper(), font=("Consolas", 9, "bold"), bg="#1E1E2E", fg="#A6E3A1", padx=6, pady=1).pack(side="left")

        # TTS Hotkey row
        row_tts = tk.Frame(hk_box, bg="#11111B")
        row_tts.pack(fill="x", padx=12, pady=(2, 10))
        tk.Label(row_tts, text="• Text-to-Speech Audio:", font=("Segoe UI", 9), bg="#11111B", fg="#BAC2DE", width=24, anchor="w").pack(side="left")
        tk.Label(row_tts, text=self.config.get("tts_hotkey", "ctrl+alt+s").upper(), font=("Consolas", 9, "bold"), bg="#1E1E2E", fg="#A6E3A1", padx=6, pady=1).pack(side="left")

        # Linger Frame
        l_frame = tk.Frame(container, bg="#11111B", bd=1, relief="solid", highlightbackground="#313244", highlightthickness=1)
        l_frame.pack(fill="x", pady=(0, 14))
        tk.Label(l_frame, text="HUD Display Duration (seconds):", font=("Segoe UI", 9, "bold"), bg="#11111B", fg="#CDD6F4").pack(anchor="w", padx=12, pady=(8, 4))
        self.entry_linger = tk.Spinbox(l_frame, from_=4, to=60, font=("Segoe UI", 10), bg="#181825", fg="#CDD6F4", bd=1, relief="solid")
        self.entry_linger.delete(0, "end")
        self.entry_linger.insert(0, str(int(self.config.get("linger_duration_ms", 14000) / 1000)))
        self.entry_linger.pack(anchor="w", padx=12, pady=(0, 8))

        tk.Button(
            container, text="Save Preferences", font=("Segoe UI", 9, "bold"),
            bg="#89B4FA", fg="#11111B", bd=0, padx=16, pady=6, cursor="hand2", command=self.save_preferences
        ).pack(anchor="w")

    def build_uninstall_tab(self):
        container = tk.Frame(self.tab_uninstall, bg="#1E1E2E")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            container,
            text="Free Storage Space:\nDelete downloaded models from Ollama to immediately reclaim disk space.",
            font=("Segoe UI", 9), bg="#1E1E2E", fg="#BAC2DE", justify="left"
        ).pack(anchor="w", pady=(0, 10))

        self.uninstall_list_frame = tk.Frame(container, bg="#11111B", bd=1, relief="solid", highlightbackground="#313244", highlightthickness=1)
        self.uninstall_list_frame.pack(fill="both", expand=True, pady=(0, 10))

        btn_row = tk.Frame(container, bg="#1E1E2E")
        btn_row.pack(fill="x")

        tk.Button(
            btn_row, text="Reset Config to Defaults", font=("Segoe UI", 9),
            bg="#313244", fg="#CDD6F4", bd=0, padx=12, pady=6, cursor="hand2", command=self.reset_defaults
        ).pack(side="left")

    def update_tier_highlights(self):
        sel = self.selected_tier.get()
        for k, card in self.tier_cards.items():
            if k == sel:
                card.configure(highlightbackground="#89B4FA", highlightthickness=1.5)
            else:
                card.configure(highlightbackground="#313244", highlightthickness=1)

    def check_ollama_status(self):
        self.status_lbl.configure(text="Connecting to Ollama...")
        threading.Thread(target=self._check_ollama_worker, daemon=True).start()

    def _check_ollama_worker(self):
        url = self.config.get("ollama_url", "http://localhost:11434").rstrip("/")
        try:
            req = urllib.request.Request(f"{url}/api/version")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ver = data.get("version", "Active")
                self.root.after(0, lambda: self.lbl_ollama_status.configure(text=f"✓ Ollama Runtime Connected (v{ver})", fg="#A6E3A1"))
                self.root.after(0, lambda: self.status_lbl.configure(text="Ollama connected."))
                self.refresh_inventory()
        except Exception:
            self.root.after(0, lambda: self.lbl_ollama_status.configure(text="✕ Ollama Service Not Detected", fg="#F38BA8"))
            self.root.after(0, lambda: self.status_lbl.configure(text="Ollama offline. Run 'ollama serve'."))

    def spawn_ollama_serve(self):
        ollama_bin = r"C:\Users\jishn\AppData\Local\Programs\Ollama\ollama.exe"
        if not os.path.exists(ollama_bin):
            ollama_bin = "ollama"
        try:
            subprocess.Popen([ollama_bin, "serve"], creationflags=0x08000000)
            self.status_lbl.configure(text="Starting Ollama server daemon...")
            self.root.after(3000, self.check_ollama_status)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start Ollama server: {e}")

    def refresh_inventory(self):
        threading.Thread(target=self._refresh_inventory_worker, daemon=True).start()

    def _refresh_inventory_worker(self):
        url = self.config.get("ollama_url", "http://localhost:11434").rstrip("/")
        try:
            req = urllib.request.Request(f"{url}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                self.installed_models = [m.get("name", "") for m in models]
                self.root.after(0, lambda: self.update_badges(models))
        except Exception:
            pass

    def update_badges(self, models_data):
        tiers = self.config.get("tiers", {})
        for key, spec in tiers.items():
            badge = self.badge_labels.get(key)
            if badge:
                m_name = spec.get("model", "")
                is_inst = any(m_name in m or m.startswith(m_name) for m in self.installed_models)
                if is_inst:
                    badge.configure(text="✓ INSTALLED", fg="#A6E3A1", bg="#182A24")
                else:
                    badge.configure(text="NOT INSTALLED", fg="#F38BA8", bg="#2B1D24")

        # Populate Uninstall View
        for child in self.uninstall_list_frame.winfo_children():
            child.destroy()

        tier_models = [spec.get("model") for spec in tiers.values()]
        found_any = False
        for m in models_data:
            name = m.get("name", "")
            size_gb = m.get("size", 0) / (1024 ** 3)
            if any(tm in name for tm in tier_models):
                found_any = True
                row = tk.Frame(self.uninstall_list_frame, bg="#11111B")
                row.pack(fill="x", padx=12, pady=6)
                tk.Label(row, text=f"{name}  —  {size_gb:.2f} GB", font=("Segoe UI", 9, "bold"), bg="#11111B", fg="#CDD6F4").pack(side="left")
                del_btn = tk.Button(
                    row, text="Delete", font=("Segoe UI", 8, "bold"),
                    bg="#F38BA8", fg="#11111B", bd=0, padx=8, pady=2, cursor="hand2",
                    command=lambda mn=name: self.delete_model(mn)
                )
                del_btn.pack(side="right")

        if not found_any:
            tk.Label(self.uninstall_list_frame, text="No wat-this models are currently taking up disk space.", font=("Segoe UI", 9, "italic"), bg="#11111B", fg="#A6ADC8").pack(padx=12, pady=16)

    def delete_model(self, model_name):
        if messagebox.askyesno("Confirm Deletion", f"Delete model '{model_name}' to free up disk space?"):
            url = self.config.get("ollama_url", "http://localhost:11434").rstrip("/")
            try:
                req_data = json.dumps({"model": model_name}).encode("utf-8")
                req = urllib.request.Request(f"{url}/api/delete", data=req_data, method="DELETE", headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    messagebox.showinfo("Removed", f"Model '{model_name}' has been deleted.")
                    self.refresh_inventory()
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete model: {e}")

    def start_model_pull(self):
        if self.is_pulling:
            return
        tier_key = self.selected_tier.get()
        model_name = self.config.get("tiers", {}).get(tier_key, {}).get("model")
        if not model_name:
            return

        self.is_pulling = True
        self.install_btn.configure(state="disabled")
        self.p_bar["value"] = 0
        self.p_status.configure(text=f"Connecting to Ollama to pull {model_name}...")
        threading.Thread(target=self._pull_worker, args=(model_name, tier_key), daemon=True).start()

    def _pull_worker(self, model_name, tier_key):
        url = self.config.get("ollama_url", "http://localhost:11434").rstrip("/")
        try:
            req_data = json.dumps({"model": model_name, "stream": True}).encode("utf-8")
            req = urllib.request.Request(f"{url}/api/pull", data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                for line in resp:
                    if line:
                        try:
                            data = json.loads(line.decode("utf-8"))
                            status = data.get("status", "")
                            tot = data.get("total", 0)
                            comp = data.get("completed", 0)
                            if tot > 0:
                                pct = int((comp / tot) * 100)
                                comp_mb = comp / (1024 * 1024)
                                tot_mb = tot / (1024 * 1024)
                                msg = f"{status} — {pct}% ({comp_mb:.1f} MB / {tot_mb:.1f} MB)"
                                self.root.after(0, lambda p=pct, m=msg: self._update_pull_progress(p, m))
                            else:
                                self.root.after(0, lambda m=status: self._update_pull_progress(0, m))
                        except Exception:
                            continue

            config_manager.set_active_tier(tier_key)
            self.root.after(0, lambda: self._pull_finished(True, f"Model '{model_name}' successfully installed!"))
        except Exception as e:
            self.root.after(0, lambda: self._pull_finished(False, f"Download failed: {e}"))

    def _update_pull_progress(self, pct, msg):
        self.p_bar["value"] = pct
        self.p_status.configure(text=msg)

    def _pull_finished(self, success, msg):
        self.is_pulling = False
        self.install_btn.configure(state="normal")
        self.p_status.configure(text=msg)
        if success:
            messagebox.showinfo("Installation Complete", msg)
            self.refresh_inventory()
        else:
            messagebox.showwarning("Download Incomplete", msg)

    def save_active_tier(self):
        tier_key = self.selected_tier.get()
        config_manager.set_active_tier(tier_key)
        self.update_tier_highlights()
        messagebox.showinfo("Active Tier Saved", f"Active tier set to '{tier_key.upper()}'.")

    def save_preferences(self):
        # Autostart
        want_autostart = self.var_autostart.get()
        config_manager.set_windows_autostart(want_autostart)
        
        # TTS
        self.config["tts_enabled"] = self.var_tts.get()

        try:
            self.config["linger_duration_ms"] = int(self.entry_linger.get()) * 1000
        except Exception:
            pass

        config_manager.save_config(self.config)
        messagebox.showinfo("Saved", "Preferences and Windows Autostart updated.")

    def reset_defaults(self):
        if messagebox.askyesno("Reset", "Reset all settings and active tier to factory defaults?"):
            config_manager.save_config(config_manager.DEFAULT_CONFIG)
            self.config = config_manager.load_config()
            self.selected_tier.set(self.config.get("active_tier", "normal"))
            self.update_tier_highlights()
            messagebox.showinfo("Reset", "Configuration reset to default settings.")

    def launch_wat_this(self):
        try:
            main_script = os.path.join(config_manager.BASE_DIR, "wat_this.py")
            pyw = r"C:\Users\jishn\AppData\Local\Programs\Python\Python312\pythonw.exe"
            py_exec = pyw if os.path.exists(pyw) else sys.executable
            subprocess.Popen([py_exec, main_script], cwd=config_manager.BASE_DIR)
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Launch Error", f"Could not start wat-this: {e}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SetupApp()
    app.run()
