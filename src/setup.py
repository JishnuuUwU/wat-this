import sys
import os
import json
import ctypes
import threading
import subprocess
import urllib.request
import urllib.parse
import tkinter as tk
from tkinter import ttk, messagebox

# Set explicit Windows AppUserModelID for taskbar grouping
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("watthis.setup.wizard.1")
except Exception:
    pass

import config_manager
import history_manager
import tts_helper

# ---------------------------------------------------------------------------
# DESIGN SYSTEM TOKENS (Modern Obsidian & Slate Palette)
# ---------------------------------------------------------------------------
COLOR_BG           = "#0D1117"  # Window canvas
COLOR_SIDEBAR      = "#161B22"  # Elevated sidebar
COLOR_SIDEBAR_HOV  = "#1F242C"  # Hovered sidebar item
COLOR_SIDEBAR_ACT  = "#21262D"  # Selected sidebar item
COLOR_CARD         = "#161B22"  # Card container background
COLOR_CARD_SUB     = "#0D1117"  # Inner card background
COLOR_CARD_BORDER  = "#30363D"  # Subtle structural border
COLOR_CARD_ACTIVE  = "#1F6FEB"  # Active selection highlight
COLOR_TEXT         = "#F0F6FC"  # High-contrast primary text
COLOR_TEXT_MUTED   = "#8B949E"  # Secondary neutral text
COLOR_TEXT_DIM     = "#6E7681"  # Muted captions & hints
COLOR_BLUE         = "#388BFD"  # Brand primary accent
COLOR_BLUE_BG      = "#0D203D"  # Brand pill background
COLOR_GREEN        = "#3FB950"  # Success & online state
COLOR_GREEN_BG     = "#122619"  # Emerald pill background
COLOR_AMBER        = "#D29922"  # Warning state
COLOR_RED          = "#F85149"  # Danger / Delete state
COLOR_RED_BG       = "#281215"  # Danger pill background
COLOR_PURPLE       = "#A371F7"  # Extreme tier accent

class ToggleSwitch(tk.Canvas):
    """Modern pill-shaped toggle switch replacing raw checkbuttons."""
    def __init__(self, parent, variable=None, command=None, width=42, height=22, bg=COLOR_CARD, active_color=COLOR_BLUE):
        super().__init__(parent, width=width, height=height, bg=bg, highlightthickness=0, cursor="hand2")
        self.var = variable or tk.BooleanVar(value=False)
        self.command = command
        self.active_color = active_color
        self.bg_color = bg
        self.bind("<Button-1>", self.toggle)
        self.draw()

    def toggle(self, event=None):
        self.var.set(not self.var.get())
        self.draw()
        if self.command:
            self.command()

    def draw(self):
        self.delete("all")
        val = self.var.get()
        track = self.active_color if val else "#30363D"
        # Draw rounded pill track
        self.create_oval(1, 1, 21, 21, fill=track, outline=track)
        self.create_oval(21, 1, 41, 21, fill=track, outline=track)
        self.create_rectangle(11, 1, 31, 21, fill=track, outline=track)
        # Draw thumb
        tx = 21 if val else 2
        self.create_oval(tx, 2, tx + 18, 20, fill="#FFFFFF", outline="#FFFFFF")


FONT_FAMILY = "Segoe UI"
FONT_HERO    = (FONT_FAMILY, 15, "bold")
FONT_TITLE   = (FONT_FAMILY, 12, "bold")
FONT_SECTION = (FONT_FAMILY, 10, "bold")
FONT_BODY    = (FONT_FAMILY, 9)
FONT_BOLD    = (FONT_FAMILY, 9, "bold")
FONT_SMALL   = (FONT_FAMILY, 8)
FONT_MICRO   = (FONT_FAMILY, 8, "bold")
FONT_CODE    = ("Consolas", 9)

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
        self.root.title("wat-this Settings & Maintenance")
        self.root.geometry("960x640")
        self.root.minsize(900, 600)
        self.root.configure(bg=COLOR_BG)

        # Set Window Icon
        if os.path.exists(config_manager.ICON_ICO_PATH):
            try:
                self.root.iconbitmap(config_manager.ICON_ICO_PATH)
            except Exception:
                pass

        # Load 36px PNG Icon for Sidebar Header
        self.icon_img = None
        icon_png = os.path.join(config_manager.ASSETS_DIR, "icon_36.png")
        if not os.path.exists(icon_png):
            icon_png = config_manager.ICON_PATH
        if os.path.exists(icon_png):
            try:
                self.icon_img = tk.PhotoImage(file=icon_png)
            except Exception:
                pass

        self.installed_models = []
        self.is_pulling = False
        self.history_items = []
        self.nav_buttons = {}
        self.active_tab = "diagnostics"

        self.init_styles()
        self.init_layout()
        self.switch_view("diagnostics")
        self.check_ollama_status()

    def init_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Treeview styling for Knowledge Notebook
        self.style.configure("Treeview",
            background=COLOR_CARD,
            foreground=COLOR_TEXT,
            fieldbackground=COLOR_CARD,
            borderwidth=0,
            rowheight=28,
            font=FONT_BODY
        )
        self.style.map("Treeview",
            background=[("selected", COLOR_CARD_ACTIVE)],
            foreground=[("selected", "#FFFFFF")]
        )
        self.style.configure("Treeview.Heading",
            background=COLOR_SIDEBAR,
            foreground=COLOR_TEXT_MUTED,
            font=FONT_MICRO,
            borderwidth=0,
            relief="flat"
        )
        self.style.configure("Horizontal.TProgressbar",
            troughcolor=COLOR_CARD_SUB,
            background=COLOR_BLUE,
            thickness=10,
            borderwidth=0
        )

    # ---------------------------------------------------------------------------
    # ROOT TWO-COLUMN LAYOUT (Sidebar + Main Content)
    # ---------------------------------------------------------------------------
    def init_layout(self):
        # LEFT SIDEBAR
        self.sidebar = tk.Frame(self.root, bg=COLOR_SIDEBAR, width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Header Branding
        brand_frame = tk.Frame(self.sidebar, bg=COLOR_SIDEBAR)
        brand_frame.pack(fill="x", padx=18, pady=(20, 24))

        if self.icon_img:
            lbl_ico = tk.Label(brand_frame, image=self.icon_img, bg=COLOR_SIDEBAR)
            lbl_ico.pack(side="left", padx=(0, 10))

        title_col = tk.Frame(brand_frame, bg=COLOR_SIDEBAR)
        title_col.pack(side="left", fill="both")

        tk.Label(
            title_col, text="wat-this", font=FONT_HERO,
            bg=COLOR_SIDEBAR, fg=COLOR_TEXT
        ).pack(anchor="w")

        tk.Label(
            title_col, text="Ambient Copilot", font=FONT_MICRO,
            bg=COLOR_SIDEBAR, fg=COLOR_BLUE
        ).pack(anchor="w")

        # Navigation Items
        nav_container = tk.Frame(self.sidebar, bg=COLOR_SIDEBAR)
        nav_container.pack(fill="x", padx=10, pady=0)

        nav_items = [
            ("diagnostics", "⚡  Diagnostics", "Host memory & Ollama service"),
            ("tiers",       "🎛️  Model Profiles", "Lite, Normal, and Extreme"),
            ("history",     "📓  Notebook",       "Queries & Obsidian exports"),
            ("prefs",       "⚙️  Preferences",    "Hotkeys, Autostart & Audio"),
            ("storage",     "💾  Storage Reclaim", "Free up model disk space"),
        ]

        for key, label, sub in nav_items:
            btn_frame = tk.Frame(nav_container, bg=COLOR_SIDEBAR, cursor="hand2")
            btn_frame.pack(fill="x", pady=2)

            # Left indicator strip
            bar = tk.Frame(btn_frame, bg=COLOR_SIDEBAR, width=3)
            bar.pack(side="left", fill="y")

            lbl_txt = tk.Label(
                btn_frame, text=f" {label}", font=FONT_SECTION,
                bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MUTED, anchor="w", padx=10, pady=8
            )
            lbl_txt.pack(side="left", fill="x", expand=True)

            # Hover & click events
            for w in (btn_frame, lbl_txt):
                w.bind("<Enter>", lambda e, k=key: self._nav_hover(k, True))
                w.bind("<Leave>", lambda e, k=key: self._nav_hover(k, False))
                w.bind("<Button-1>", lambda e, k=key: self.switch_view(k))

            self.nav_buttons[key] = {"frame": btn_frame, "bar": bar, "lbl": lbl_txt}

        # Sidebar Footer
        side_footer = tk.Frame(self.sidebar, bg=COLOR_SIDEBAR)
        side_footer.pack(side="bottom", fill="x", padx=16, pady=18)

        # Active Tier Indicator
        self.sidebar_tier_lbl = tk.Label(
            side_footer, text="Active: Normal", font=FONT_MICRO,
            bg=COLOR_CARD, fg=COLOR_BLUE, bd=1, relief="solid",
            highlightbackground=COLOR_CARD_BORDER, highlightthickness=1,
            padx=10, pady=4
        )
        self.sidebar_tier_lbl.pack(fill="x", pady=(0, 10))

        # Launch Button
        self.btn_launch = tk.Button(
            side_footer, text="🚀  Launch wat-this", font=FONT_BOLD,
            bg=COLOR_BLUE, fg="#FFFFFF", activebackground="#2563EB", activeforeground="#FFFFFF",
            bd=0, pady=8, cursor="hand2", command=self.launch_wat_this
        )
        self.btn_launch.pack(fill="x")

        # RIGHT MAIN CANVAS
        self.canvas_area = tk.Frame(self.root, bg=COLOR_BG)
        self.canvas_area.pack(side="right", fill="both", expand=True)

        # Top Bar (Header & Status)
        self.topbar = tk.Frame(self.canvas_area, bg=COLOR_BG)
        self.topbar.pack(fill="x", padx=28, pady=(20, 12))

        self.view_title_lbl = tk.Label(
            self.topbar, text="Diagnostics & System Telemetry", font=FONT_HERO,
            bg=COLOR_BG, fg=COLOR_TEXT
        )
        self.view_title_lbl.pack(side="left", anchor="w")

        self.service_badge = tk.Label(
            self.topbar, text=" ● Ollama Online ", font=FONT_MICRO,
            bg=COLOR_GREEN_BG, fg=COLOR_GREEN, bd=1, relief="solid",
            highlightbackground=COLOR_GREEN, highlightthickness=1, padx=8, pady=3
        )
        self.service_badge.pack(side="right")

        self.view_sub_lbl = tk.Label(
            self.canvas_area, text="Inspect system RAM and verify background Ollama runtime connectivity.",
            font=FONT_BODY, bg=COLOR_BG, fg=COLOR_TEXT_MUTED
        )
        self.view_sub_lbl.pack(anchor="w", padx=28, pady=(0, 14))

        # View Containers (Stacked pages)
        self.view_container = tk.Frame(self.canvas_area, bg=COLOR_BG)
        self.view_container.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        self.pages = {
            "diagnostics": tk.Frame(self.view_container, bg=COLOR_BG),
            "tiers":       tk.Frame(self.view_container, bg=COLOR_BG),
            "history":     tk.Frame(self.view_container, bg=COLOR_BG),
            "prefs":       tk.Frame(self.view_container, bg=COLOR_BG),
            "storage":     tk.Frame(self.view_container, bg=COLOR_BG),
        }

        self.build_diagnostics_page()
        self.build_tiers_page()
        self.build_history_page()
        self.build_prefs_page()
        self.build_storage_page()

    def _nav_hover(self, key, is_hover):
        if key == self.active_tab:
            return
        bg = COLOR_SIDEBAR_HOV if is_hover else COLOR_SIDEBAR
        self.nav_buttons[key]["frame"].configure(bg=bg)
        self.nav_buttons[key]["lbl"].configure(bg=bg)

    def switch_view(self, key):
        self.active_tab = key

        # Update sidebar styling
        for k, widgets in self.nav_buttons.items():
            if k == key:
                widgets["frame"].configure(bg=COLOR_SIDEBAR_ACT)
                widgets["bar"].configure(bg=COLOR_BLUE)
                widgets["lbl"].configure(bg=COLOR_SIDEBAR_ACT, fg=COLOR_TEXT)
            else:
                widgets["frame"].configure(bg=COLOR_SIDEBAR)
                widgets["bar"].configure(bg=COLOR_SIDEBAR)
                widgets["lbl"].configure(bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MUTED)

        # Update titles
        titles = {
            "diagnostics": ("Diagnostics & System Telemetry", "Inspect system RAM, verify background Ollama runtime, and monitor health."),
            "tiers":       ("Model Profiles & Resource Allocation", "Select or install local LLM tiers strictly gated by memory budgets."),
            "history":     ("Knowledge Notebook & Activity", "Review past questions, latency metrics, and export notes directly to Obsidian/Markdown."),
            "prefs":       ("Global Preferences & Hotkeys", "Tune system startup, offline Windows TTS voice readout, and workflow actions."),
            "storage":     ("Storage Management & Model Deletion", "Reclaim storage space by removing unused Ollama model weights from disk.")
        }
        title, sub = titles.get(key, ("", ""))
        self.view_title_lbl.configure(text=title)
        self.view_sub_lbl.configure(text=sub)

        # Show target page
        for p_key, frame in self.pages.items():
            if p_key == key:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

        # Update active tier label
        active_key, active_spec = config_manager.get_active_tier()
        self.sidebar_tier_lbl.configure(text=f"Active: {active_spec.get('name')} ({active_spec.get('ram_target')})")

    # ---------------------------------------------------------------------------
    # PAGE 1: DIAGNOSTICS & TELEMETRY
    # ---------------------------------------------------------------------------
    def build_diagnostics_page(self):
        page = self.pages["diagnostics"]

        # Grid of Stat Cards (RAM, Ollama, Profile)
        stat_row = tk.Frame(page, bg=COLOR_BG)
        stat_row.pack(fill="x", pady=(0, 16))

        # CARD 1: HOST MEMORY
        c_ram = tk.Frame(stat_row, bg=COLOR_CARD, bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, highlightthickness=1)
        c_ram.pack(side="left", fill="both", expand=True, padx=(0, 10), ipady=12)

        tk.Label(c_ram, text="PHYSICAL SYSTEM RAM", font=FONT_MICRO, bg=COLOR_CARD, fg=COLOR_BLUE).pack(anchor="w", padx=16, pady=(12, 4))
        
        tot_ram, avail_ram = MemoryChecker.get_system_ram_gb()
        tot_txt = f"{tot_ram} GB" if tot_ram else "Host Memory"
        tk.Label(c_ram, text=tot_txt, font=FONT_HERO, bg=COLOR_CARD, fg=COLOR_TEXT).pack(anchor="w", padx=16, pady=(0, 2))

        used_pct = int(((tot_ram - avail_ram) / tot_ram) * 100) if (tot_ram and avail_ram) else 0
        ram_stat = f"Available: {avail_ram} GB  |  Usage: {used_pct}%" if avail_ram else "Standard Host Telemetry"
        tk.Label(c_ram, text=ram_stat, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT_MUTED).pack(anchor="w", padx=16, pady=(0, 10))

        # Visual mini progress bar for RAM
        self.ram_bar = ttk.Progressbar(c_ram, mode="determinate", value=used_pct)
        self.ram_bar.pack(fill="x", padx=16, pady=(0, 10))

        rec_tier = "Normal (3 – 5 GB)"
        if avail_ram and avail_ram < 3.0:
            rec_tier = "Lite (< 2 GB)"
        elif avail_ram and avail_ram > 8.0:
            rec_tier = "Extreme (Mistral 7B)"
        
        rec_pill = tk.Label(
            c_ram, text=f" Recommended: {rec_tier} ", font=FONT_MICRO,
            bg=COLOR_GREEN_BG, fg=COLOR_GREEN, bd=1, relief="solid", highlightbackground=COLOR_GREEN, highlightthickness=1
        )
        rec_pill.pack(anchor="w", padx=16)

        # CARD 2: OLLAMA ENGINE HEALTH
        c_eng = tk.Frame(stat_row, bg=COLOR_CARD, bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, highlightthickness=1)
        c_eng.pack(side="left", fill="both", expand=True, padx=10, ipady=12)

        tk.Label(c_eng, text="LOCAL OLLAMA RUNTIME", font=FONT_MICRO, bg=COLOR_CARD, fg=COLOR_BLUE).pack(anchor="w", padx=16, pady=(12, 4))
        self.diag_ver_lbl = tk.Label(c_eng, text="Connecting...", font=FONT_HERO, bg=COLOR_CARD, fg=COLOR_TEXT)
        self.diag_ver_lbl.pack(anchor="w", padx=16, pady=(0, 2))

        self.diag_endpoint_lbl = tk.Label(c_eng, text="Endpoint: http://localhost:11434", font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT_MUTED)
        self.diag_endpoint_lbl.pack(anchor="w", padx=16, pady=(0, 14))

        act_box = tk.Frame(c_eng, bg=COLOR_CARD)
        act_box.pack(anchor="w", padx=16)

        tk.Button(
            act_box, text="Refresh Status", font=FONT_SMALL,
            bg=COLOR_CARD_SUB, fg=COLOR_TEXT, activebackground=COLOR_CARD_ACTIVE, activeforeground="#FFF",
            bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, padx=10, pady=4, cursor="hand2",
            command=self.check_ollama_status
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            act_box, text="Spawn Service", font=FONT_SMALL,
            bg=COLOR_CARD_SUB, fg=COLOR_TEXT, activebackground=COLOR_CARD_ACTIVE, activeforeground="#FFF",
            bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, padx=10, pady=4, cursor="hand2",
            command=self.spawn_ollama_serve
        ).pack(side="left")

        # CARD 3: ACTIVE MODEL SPECS
        c_prof = tk.Frame(stat_row, bg=COLOR_CARD, bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, highlightthickness=1)
        c_prof.pack(side="left", fill="both", expand=True, padx=(10, 0), ipady=12)

        tk.Label(c_prof, text="ACTIVE PROFILE SUMMARY", font=FONT_MICRO, bg=COLOR_CARD, fg=COLOR_BLUE).pack(anchor="w", padx=16, pady=(12, 4))
        
        _, spec = config_manager.get_active_tier()
        self.diag_profile_name = tk.Label(c_prof, text=spec.get("name", "Normal").upper(), font=FONT_HERO, bg=COLOR_CARD, fg=COLOR_TEXT)
        self.diag_profile_name.pack(anchor="w", padx=16, pady=(0, 2))

        self.diag_profile_sub = tk.Label(
            c_prof, text=f"Model: {spec.get('model')} | Cache: {spec.get('keep_alive')}",
            font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT_MUTED
        )
        self.diag_profile_sub.pack(anchor="w", padx=16, pady=(0, 14))

        tk.Button(
            c_prof, text="Change Model Profile →", font=FONT_SMALL,
            bg=COLOR_CARD_SUB, fg=COLOR_BLUE, activebackground=COLOR_CARD_ACTIVE, activeforeground="#FFF",
            bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, padx=10, pady=4, cursor="hand2",
            command=lambda: self.switch_view("tiers")
        ).pack(anchor="w", padx=16)

        # Bottom System Info Box
        info_card = tk.Frame(page, bg=COLOR_CARD, bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, highlightthickness=1)
        info_card.pack(fill="both", expand=True, pady=(10, 0), padx=0, ipady=14)

        tk.Label(info_card, text="ENVIRONMENT INTEGRITY & ARCHITECTURE", font=FONT_SECTION, bg=COLOR_CARD, fg=COLOR_TEXT).pack(anchor="w", padx=16, pady=(12, 6))

        rows = [
            ("Execution Model", "Zero-DLL Pure Python & Tkinter (Strict Windows Smart App Control Compliant)"),
            ("Ollama Host", "Local HTTP Daemon (127.0.0.1:11434) — Private & On-Device"),
            ("Search Engine", "Zero-DLL DuckDuckGo JSON Client (No native C++ wheels required)"),
            ("Audio Readout", "Windows Native SAPI (System.Speech.Synthesis) — 100% Offline"),
            ("Keyboard Hooks", "Universal Win32 Keyhook Listener (Non-intrusive ambient background)")
        ]
        for title, val in rows:
            r = tk.Frame(info_card, bg=COLOR_CARD)
            r.pack(fill="x", padx=16, pady=3)
            tk.Label(r, text=f"•  {title}:", font=FONT_BOLD, bg=COLOR_CARD, fg=COLOR_TEXT_MUTED, width=18, anchor="w").pack(side="left")
            tk.Label(r, text=val, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="left")

    # ---------------------------------------------------------------------------
    # PAGE 2: MODEL TIERS & PROFILE CARDS
    # ---------------------------------------------------------------------------
    def build_tiers_page(self):
        page = self.pages["tiers"]
        tiers = self.config.get("tiers", {})
        self.selected_tier = tk.StringVar(value=self.config.get("active_tier", "normal"))
        self.tier_cards = {}
        self.tier_badges = {}

        tiers_container = tk.Frame(page, bg=COLOR_BG)
        tiers_container.pack(fill="both", expand=True)

        for key, spec in tiers.items():
            is_active = (key == self.selected_tier.get())
            card = tk.Frame(
                tiers_container, bg=COLOR_CARD, bd=1, relief="solid",
                highlightbackground=COLOR_CARD_ACTIVE if is_active else COLOR_CARD_BORDER,
                highlightthickness=1.5 if is_active else 1
            )
            card.pack(fill="x", pady=4, ipady=8)
            self.tier_cards[key] = card

            # Card Header (Radio, Name, Model, Badge)
            hdr = tk.Frame(card, bg=COLOR_CARD)
            hdr.pack(fill="x", padx=14, pady=(8, 2))

            rb = tk.Radiobutton(
                hdr, text=f" {spec.get('name')} Profile",
                variable=self.selected_tier, value=key, font=FONT_TITLE,
                bg=COLOR_CARD, fg=COLOR_TEXT, selectcolor=COLOR_CARD_SUB, activebackground=COLOR_CARD,
                command=self.update_tier_highlights
            )
            rb.pack(side="left")

            # Status pill (Installed vs Not Installed)
            b_lbl = tk.Label(
                hdr, text=" CHECKING ", font=FONT_MICRO,
                bg=COLOR_CARD_SUB, fg=COLOR_TEXT_MUTED, bd=1, relief="solid",
                highlightbackground=COLOR_CARD_BORDER, highlightthickness=1, padx=6, pady=2
            )
            b_lbl.pack(side="right")
            self.tier_badges[key] = b_lbl

            # Sub-header: Model family & memory ceiling
            meta_txt = f"Model: {spec.get('model')}  |  RAM Budget: {spec.get('ram_target')}  |  Cache: {spec.get('keep_alive')}"
            tk.Label(card, text=meta_txt, font=FONT_BOLD, bg=COLOR_CARD, fg=COLOR_BLUE).pack(anchor="w", padx=36, pady=(0, 4))

            # Feature capabilities tag pills
            pills_row = tk.Frame(card, bg=COLOR_CARD)
            pills_row.pack(anchor="w", padx=36, pady=(0, 6))

            modes_list = [m.capitalize() for m in spec.get("allowed_modes", [])]
            tk.Label(pills_row, text=f"Modes: {', '.join(modes_list)}", font=FONT_CODE, bg=COLOR_GREEN_BG, fg=COLOR_GREEN, padx=6, pady=1).pack(side="left", padx=(0, 6))
            
            chat_ok = spec.get("interactive_chat", False)
            chat_lbl = "Chat: Multi-turn" if key == "extreme" else ("Chat: 2-Turn" if chat_ok else "Chat: Locked")
            tk.Label(pills_row, text=chat_lbl, font=FONT_CODE, bg=COLOR_CARD_SUB, fg=COLOR_TEXT if chat_ok else COLOR_TEXT_DIM, padx=6, pady=1).pack(side="left", padx=(0, 6))

            tts_ok = spec.get("tts_audio", False)
            tk.Label(pills_row, text="TTS: Enabled" if tts_ok else "TTS: Locked", font=FONT_CODE, bg=COLOR_CARD_SUB, fg=COLOR_TEXT if tts_ok else COLOR_TEXT_DIM, padx=6, pady=1).pack(side="left", padx=(0, 6))

            web_ok = spec.get("web_search", False)
            tk.Label(pills_row, text="Web: Grounded" if web_ok else "Web: Offline", font=FONT_CODE, bg=COLOR_CARD_SUB, fg=COLOR_TEXT if web_ok else COLOR_TEXT_DIM, padx=6, pady=1).pack(side="left")

            # Description
            tk.Label(
                card, text=spec.get("description", ""), font=FONT_BODY,
                bg=COLOR_CARD, fg=COLOR_TEXT_MUTED, wraplength=640, justify="left"
            ).pack(anchor="w", padx=36, pady=(0, 6))

        # Bottom Pull & Progress Box
        bottom_box = tk.Frame(page, bg=COLOR_CARD, bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, highlightthickness=1)
        bottom_box.pack(fill="x", pady=(10, 0), ipady=8)

        self.p_bar = ttk.Progressbar(bottom_box, mode="determinate")
        self.p_bar.pack(fill="x", padx=16, pady=(10, 4))

        self.p_status = tk.Label(bottom_box, text="Select a tier to install or activate.", font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT_MUTED)
        self.p_status.pack(anchor="w", padx=16, pady=(0, 10))

        actions_bar = tk.Frame(bottom_box, bg=COLOR_CARD)
        actions_bar.pack(fill="x", padx=16, pady=(0, 6))

        self.install_btn = tk.Button(
            actions_bar, text="⬇️  Download & Install Selected Model", font=FONT_BOLD,
            bg=COLOR_BLUE, fg="#FFFFFF", activebackground="#2563EB", activeforeground="#FFFFFF",
            bd=0, padx=14, pady=7, cursor="hand2", command=self.start_model_pull
        )
        self.install_btn.pack(side="left", padx=(0, 10))

        set_btn = tk.Button(
            actions_bar, text="✓  Set as Active Profile", font=FONT_BOLD,
            bg=COLOR_CARD_SUB, fg=COLOR_TEXT, activebackground=COLOR_CARD_ACTIVE, activeforeground="#FFF",
            bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, padx=14, pady=6, cursor="hand2",
            command=self.save_active_tier
        )
        set_btn.pack(side="left")

    def update_tier_highlights(self):
        sel = self.selected_tier.get()
        for k, card in self.tier_cards.items():
            if k == sel:
                card.configure(highlightbackground=COLOR_CARD_ACTIVE, highlightthickness=1.5)
            else:
                card.configure(highlightbackground=COLOR_CARD_BORDER, highlightthickness=1)

    # ---------------------------------------------------------------------------
    # PAGE 3: KNOWLEDGE NOTEBOOK & EXPORTS
    # ---------------------------------------------------------------------------
    def build_history_page(self):
        page = self.pages["history"]

        # Search Bar & Filter Controls
        top_ctrl = tk.Frame(page, bg=COLOR_BG)
        top_ctrl.pack(fill="x", pady=(0, 12))

        tk.Label(top_ctrl, text="🔍", font=FONT_BODY, bg=COLOR_BG, fg=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))
        
        self.history_search_entry = tk.Entry(
            top_ctrl, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT, insertbackground=COLOR_TEXT,
            bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, highlightthickness=1
        )
        self.history_search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=3)
        self.history_search_entry.bind("<KeyRelease>", lambda e: self.filter_history())

        tk.Button(
            top_ctrl, text="Clear Filter", font=FONT_SMALL,
            bg=COLOR_CARD, fg=COLOR_TEXT, bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER,
            padx=10, pady=4, cursor="hand2", command=self.clear_history_filter
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            top_ctrl, text="📄  Export to Markdown", font=FONT_BOLD,
            bg=COLOR_GREEN, fg="#FFFFFF", activebackground="#238636", activeforeground="#FFFFFF",
            bd=0, padx=12, pady=5, cursor="hand2", command=self.export_history_action
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            top_ctrl, text="🗑️  Clear All", font=FONT_SMALL,
            bg=COLOR_RED_BG, fg=COLOR_RED, bd=1, relief="solid", highlightbackground=COLOR_RED,
            padx=10, pady=4, cursor="hand2", command=self.clear_all_history_action
        ).pack(side="left")

        # Split Container: Treeview above, Preview below
        paned = tk.PanedWindow(page, orient="vertical", bg=COLOR_CARD_BORDER, bd=1, sashwidth=4)
        paned.pack(fill="both", expand=True)

        tree_frame = tk.Frame(paned, bg=COLOR_CARD)
        cols = ("timestamp", "mode", "tier", "snippet")
        self.history_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=7)
        self.history_tree.heading("timestamp", text="Recorded Time")
        self.history_tree.heading("mode", text="Mode")
        self.history_tree.heading("tier", text="Tier")
        self.history_tree.heading("snippet", text="Highlighted Snippet Context")

        self.history_tree.column("timestamp", width=140, anchor="w")
        self.history_tree.column("mode", width=90, anchor="center")
        self.history_tree.column("tier", width=80, anchor="center")
        self.history_tree.column("snippet", width=420, anchor="w")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=tree_scroll.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        self.history_tree.bind("<<TreeviewSelect>>", self.on_history_select)

        paned.add(tree_frame)

        # Output Preview Frame
        preview_frame = tk.Frame(paned, bg=COLOR_CARD)
        hdr_bar = tk.Frame(preview_frame, bg=COLOR_CARD)
        hdr_bar.pack(fill="x", padx=12, pady=(8, 4))

        tk.Label(hdr_bar, text="OUTPUT & METADATA PREVIEW", font=FONT_MICRO, bg=COLOR_CARD, fg=COLOR_BLUE).pack(side="left")
        
        self.history_preview_txt = tk.Text(
            preview_frame, font=FONT_BODY, bg=COLOR_CARD_SUB, fg=COLOR_TEXT,
            bd=0, padx=12, pady=10, wrap="word", height=6
        )
        self.history_preview_txt.pack(fill="both", expand=True, padx=12, pady=(0, 10))

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
                meta = f"Model: {item.get('model', 'Local AI')}  |  Tier: {item.get('tier', '').upper()}  |  Latency: {item.get('latency_s', '')}s\n"
                meta += "─" * 65 + "\n\n"
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

    # ---------------------------------------------------------------------------
    # PAGE 4: PREFERENCES & MODES
    # ---------------------------------------------------------------------------
    def build_prefs_page(self):
        page = self.pages["prefs"]

        # Windows Integration Card
        int_card = tk.Frame(page, bg=COLOR_CARD, bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, highlightthickness=1)
        int_card.pack(fill="x", pady=(0, 12), ipady=8)

        tk.Label(int_card, text="SYSTEM INTEGRATION", font=FONT_MICRO, bg=COLOR_CARD, fg=COLOR_BLUE).pack(anchor="w", padx=16, pady=(10, 8))

        # Windows Startup Row
        row_as = tk.Frame(int_card, bg=COLOR_CARD)
        row_as.pack(fill="x", padx=16, pady=(0, 4))
        self.var_autostart = tk.BooleanVar(value=config_manager.is_windows_autostart_enabled())
        self.sw_autostart = ToggleSwitch(row_as, variable=self.var_autostart, bg=COLOR_CARD)
        self.sw_autostart.pack(side="left", padx=(0, 12))
        tk.Label(row_as, text="Launch wat-this automatically when Windows starts", font=FONT_BOLD, bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="left")
        tk.Label(int_card, text="Creates a clean shortcut in %APPDATA%\\Startup. Zero registry modifications.", font=FONT_SMALL, bg=COLOR_CARD, fg=COLOR_TEXT_MUTED).pack(anchor="w", padx=70, pady=(0, 10))

        # Windows TTS Audio Row
        row_tts = tk.Frame(int_card, bg=COLOR_CARD)
        row_tts.pack(fill="x", padx=16, pady=(0, 4))
        self.var_tts = tk.BooleanVar(value=self.config.get("tts_enabled", False))
        self.sw_tts = ToggleSwitch(row_tts, variable=self.var_tts, bg=COLOR_CARD)
        self.sw_tts.pack(side="left", padx=(0, 12))
        tk.Label(row_tts, text="Automatically read explanations aloud (Offline Windows TTS)", font=FONT_BOLD, bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="left")
        tk.Label(int_card, text="Uses Windows native System.Speech.Synthesis. (Available on Normal & Extreme tiers).", font=FONT_SMALL, bg=COLOR_CARD, fg=COLOR_TEXT_MUTED).pack(anchor="w", padx=70, pady=(0, 8))

        # Hotkeys & Gating Table Card
        hk_card = tk.Frame(page, bg=COLOR_CARD, bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, highlightthickness=1)
        hk_card.pack(fill="x", pady=(0, 12), ipady=8)

        tk.Label(hk_card, text="WORKFLOW MODES & TIER REQUIREMENTS", font=FONT_MICRO, bg=COLOR_CARD, fg=COLOR_BLUE).pack(anchor="w", padx=16, pady=(10, 6))

        modes = config_manager.get_modes()
        for m_key, m_info in modes.items():
            row = tk.Frame(hk_card, bg=COLOR_CARD)
            row.pack(fill="x", padx=16, pady=3)

            tk.Label(row, text=f"•  {m_info.get('name')}", font=FONT_BOLD, bg=COLOR_CARD, fg=COLOR_TEXT, width=22, anchor="w").pack(side="left")
            tk.Label(row, text=m_info.get('hotkey', '').upper(), font=FONT_CODE, bg=COLOR_CARD_SUB, fg=COLOR_BLUE, padx=8, pady=2).pack(side="left", padx=8)

            req_tier = m_info.get("required_tier", "lite").upper()
            badge_fg = COLOR_BLUE if req_tier == "LITE" else (COLOR_GREEN if req_tier == "NORMAL" else COLOR_PURPLE)
            badge_bg = COLOR_BLUE_BG if req_tier == "LITE" else (COLOR_GREEN_BG if req_tier == "NORMAL" else "#251B33")
            pill_txt = f" {req_tier}+ " if req_tier != "EXTREME" else " EXTREME ONLY "
            tk.Label(row, text=pill_txt, font=FONT_MICRO, bg=badge_bg, fg=badge_fg, bd=1, relief="solid", highlightbackground=badge_fg, highlightthickness=1, padx=4, pady=1).pack(side="left", padx=8)

        # TTS Audio Hotkey Row
        tts_row = tk.Frame(hk_card, bg=COLOR_CARD)
        tts_row.pack(fill="x", padx=16, pady=(3, 10))
        tk.Label(tts_row, text="•  Text-to-Speech Audio", font=FONT_BOLD, bg=COLOR_CARD, fg=COLOR_TEXT, width=22, anchor="w").pack(side="left")
        tk.Label(tts_row, text=self.config.get("tts_hotkey", "ctrl+alt+s").upper(), font=FONT_CODE, bg=COLOR_CARD_SUB, fg=COLOR_BLUE, padx=8, pady=2).pack(side="left", padx=8)
        tk.Label(tts_row, text=" NORMAL+ ", font=FONT_MICRO, bg=COLOR_GREEN_BG, fg=COLOR_GREEN, bd=1, relief="solid", highlightbackground=COLOR_GREEN, highlightthickness=1, padx=4, pady=1).pack(side="left", padx=8)

        # Linger Timer Card
        linger_card = tk.Frame(page, bg=COLOR_CARD, bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, highlightthickness=1)
        linger_card.pack(fill="x", pady=(0, 14), ipady=8)

        tk.Label(linger_card, text="DISPLAY BEHAVIOR", font=FONT_MICRO, bg=COLOR_CARD, fg=COLOR_BLUE).pack(anchor="w", padx=16, pady=(10, 4))
        
        l_box = tk.Frame(linger_card, bg=COLOR_CARD)
        l_box.pack(fill="x", padx=16, pady=(0, 6))

        tk.Label(l_box, text="HUD Linger Duration (seconds before auto-fade):", font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="left", padx=(0, 12))
        self.entry_linger = tk.Spinbox(
            l_box, from_=4, to=60, font=FONT_BODY, bg=COLOR_CARD_SUB, fg=COLOR_TEXT,
            bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, width=6
        )
        self.entry_linger.delete(0, "end")
        self.entry_linger.insert(0, str(int(self.config.get("linger_duration_ms", 14000) / 1000)))
        self.entry_linger.pack(side="left")

        # Save Button
        tk.Button(
            page, text="💾  Save All Preferences", font=FONT_BOLD,
            bg=COLOR_BLUE, fg="#FFFFFF", activebackground="#2563EB", activeforeground="#FFFFFF",
            bd=0, padx=16, pady=8, cursor="hand2", command=self.save_preferences
        ).pack(anchor="w", pady=(4, 0))

    # ---------------------------------------------------------------------------
    # PAGE 5: STORAGE RECLAIM & CLEANUP
    # ---------------------------------------------------------------------------
    def build_storage_page(self):
        page = self.pages["storage"]

        top_info = tk.Frame(page, bg=COLOR_CARD, bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, highlightthickness=1)
        top_info.pack(fill="x", pady=(0, 12), ipady=8)

        tk.Label(top_info, text="DISK STORAGE RECLAMATION", font=FONT_MICRO, bg=COLOR_CARD, fg=COLOR_BLUE).pack(anchor="w", padx=16, pady=(10, 4))
        tk.Label(
            top_info, text="Downloaded local model weights occupy disk space. You can safely remove models below anytime to reclaim gigabytes of disk space.",
            font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT_MUTED, wraplength=640, justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 6))

        self.uninstall_list_frame = tk.Frame(page, bg=COLOR_CARD, bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER, highlightthickness=1)
        self.uninstall_list_frame.pack(fill="both", expand=True, pady=(0, 12), ipady=8)

        btn_row = tk.Frame(page, bg=COLOR_BG)
        btn_row.pack(fill="x")

        tk.Button(
            btn_row, text="↺  Reset Configuration to Factory Defaults", font=FONT_SMALL,
            bg=COLOR_CARD, fg=COLOR_TEXT_MUTED, bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER,
            padx=14, pady=6, cursor="hand2", command=self.reset_defaults
        ).pack(side="left")

    # ---------------------------------------------------------------------------
    # ENGINE & MODEL CONTROLLERS
    # ---------------------------------------------------------------------------
    def check_ollama_status(self):
        self.service_badge.configure(text=" ● Probing Ollama... ", fg=COLOR_AMBER, bg=COLOR_CARD_SUB)
        threading.Thread(target=self._check_ollama_worker, daemon=True).start()

    def _check_ollama_worker(self):
        url = self.config.get("ollama_url", "http://localhost:11434").rstrip("/")
        try:
            req = urllib.request.Request(f"{url}/api/version")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ver = data.get("version", "Active")
                self.root.after(0, lambda: self.service_badge.configure(text=f" ● Ollama Online (v{ver}) ", fg=COLOR_GREEN, bg=COLOR_GREEN_BG, highlightbackground=COLOR_GREEN))
                self.root.after(0, lambda: self.diag_ver_lbl.configure(text=f"Connected (v{ver})", fg=COLOR_GREEN))
                self.refresh_inventory()
        except Exception:
            self.root.after(0, lambda: self.service_badge.configure(text=" ✕ Ollama Offline ", fg=COLOR_RED, bg=COLOR_RED_BG, highlightbackground=COLOR_RED))
            self.root.after(0, lambda: self.diag_ver_lbl.configure(text="Offline (Click Spawn)", fg=COLOR_RED))

    def spawn_ollama_serve(self):
        ollama_bin = r"C:\Users\jishn\AppData\Local\Programs\Ollama\ollama.exe"
        if not os.path.exists(ollama_bin):
            ollama_bin = "ollama"
        try:
            subprocess.Popen([ollama_bin, "serve"], creationflags=0x08000000)
            self.service_badge.configure(text=" ● Starting Ollama... ", fg=COLOR_AMBER, bg=COLOR_CARD_SUB)
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
            badge = self.tier_badges.get(key)
            if badge:
                m_name = spec.get("model", "")
                is_inst = any(m_name in m or m.startswith(m_name) for m in self.installed_models)
                if is_inst:
                    badge.configure(text=" ✓ INSTALLED ", fg=COLOR_GREEN, bg=COLOR_GREEN_BG, highlightbackground=COLOR_GREEN)
                else:
                    badge.configure(text=" NOT INSTALLED ", fg=COLOR_RED, bg=COLOR_RED_BG, highlightbackground=COLOR_RED)

        # Update Storage Reclaim List
        for child in self.uninstall_list_frame.winfo_children():
            child.destroy()

        tk.Label(self.uninstall_list_frame, text="LOCAL MODEL INVENTORY", font=FONT_MICRO, bg=COLOR_CARD, fg=COLOR_BLUE).pack(anchor="w", padx=16, pady=(10, 6))

        tier_models = [spec.get("model") for spec in tiers.values()]
        found_any = False
        for m in models_data:
            name = m.get("name", "")
            size_gb = m.get("size", 0) / (1024 ** 3)
            if any(tm in name for tm in tier_models):
                found_any = True
                row = tk.Frame(self.uninstall_list_frame, bg=COLOR_CARD_SUB, bd=1, relief="solid", highlightbackground=COLOR_CARD_BORDER)
                row.pack(fill="x", padx=16, pady=4, ipady=4)

                tk.Label(row, text=f"•  {name}", font=FONT_BOLD, bg=COLOR_CARD_SUB, fg=COLOR_TEXT).pack(side="left", padx=12)
                tk.Label(row, text=f"Disk Usage: {size_gb:.2f} GB", font=FONT_BODY, bg=COLOR_CARD_SUB, fg=COLOR_TEXT_MUTED).pack(side="left", padx=16)

                del_btn = tk.Button(
                    row, text="Delete", font=FONT_MICRO,
                    bg=COLOR_RED_BG, fg=COLOR_RED, bd=1, relief="solid", highlightbackground=COLOR_RED,
                    padx=10, pady=2, cursor="hand2", command=lambda mn=name: self.delete_model(mn)
                )
                del_btn.pack(side="right", padx=12)

        if not found_any:
            tk.Label(self.uninstall_list_frame, text="No model weights currently downloaded.", font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT_MUTED).pack(padx=16, pady=16)

    def delete_model(self, model_name):
        if messagebox.askyesno("Confirm Deletion", f"Delete model '{model_name}' to immediately free up disk space?"):
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
        active_key, active_spec = config_manager.get_active_tier()
        self.sidebar_tier_lbl.configure(text=f"Active: {active_spec.get('name')} ({active_spec.get('ram_target')})")
        messagebox.showinfo("Active Profile Saved", f"Profile successfully set to '{active_spec.get('name')}'.")

    def save_preferences(self):
        want_autostart = self.var_autostart.get()
        config_manager.set_windows_autostart(want_autostart)
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
            
            self.btn_launch.configure(
                text="✓  Copilot Active on Taskbar",
                bg=COLOR_GREEN,
                activebackground=COLOR_GREEN
            )
            messagebox.showinfo(
                "wat-this Running",
                "wat-this is now running on your Windows Taskbar!\n\n"
                "• Check your taskbar for 'wat-this • Ambient Copilot'.\n"
                "• Highlight any text anywhere and press Ctrl + Alt + Space.\n"
                "• You can minimize this setup window anytime."
            )
            self.root.iconify()
        except Exception as e:
            messagebox.showerror("Launch Error", f"Could not start wat-this: {e}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SetupApp()
    app.run()
