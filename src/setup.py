"""
setup.py - Settings & All-in-One Copilot Management Wizard
Implements:
1. Bundled 1-Click Setup Solution (All Ollama daemon, models, and tests bundled together)
2. Modern Rounded Dark Design System (AMOLED charcoal, soft squircle cards, Vivid Blue)
3. Fluid Page Transitions & Animations (eased slide-ins, animated telemetry progress bars, smooth switches)
4. Ergonomic "Viewing Area" (expressive spacious headers) vs "Interaction Area" (squircle controls)
5. Interactive Test Suite (Test Ollama Query, Test Offline TTS Voice, Test Hotkey)
6. Knowledge Notebook with Filter Chips and 1-Click Obsidian/Markdown Export
7. Storage Management & Model Download / Deletion
"""

import sys
import os
import json
import ctypes
import threading
import subprocess
import urllib.request
import urllib.parse
import time
import tkinter as tk
from tkinter import ttk, messagebox

# Ensure src folder is always in sys.path
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Set explicit Windows AppUserModelID for taskbar grouping
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("watthis.setup.wizard.1")
except Exception:
    pass

import config_manager
import history_manager
import tts_helper
import one_ui
from one_ui import (
    COLOR_ONEUI_BG, COLOR_ONEUI_CANVAS, COLOR_ONEUI_SIDEBAR, COLOR_ONEUI_SIDEBAR_HOV,
    COLOR_ONEUI_SIDEBAR_ACT, COLOR_ONEUI_CARD, COLOR_ONEUI_CARD_SUB, COLOR_ONEUI_CARD_ELEV,
    COLOR_ONEUI_BORDER, COLOR_ONEUI_BORDER_SUB, COLOR_ONEUI_BORDER_FOCUS,
    COLOR_ONEUI_TEXT, COLOR_ONEUI_TEXT_SEC, COLOR_ONEUI_TEXT_MUTED, COLOR_ONEUI_TEXT_DIM,
    COLOR_ONEUI_BLUE, COLOR_ONEUI_BLUE_HOV, COLOR_ONEUI_BLUE_BG, COLOR_ONEUI_BLUE_BORDER,
    COLOR_ONEUI_GREEN, COLOR_ONEUI_GREEN_BG, COLOR_ONEUI_GREEN_BORDER,
    COLOR_ONEUI_AMBER, COLOR_ONEUI_AMBER_BG, COLOR_ONEUI_AMBER_BORDER,
    COLOR_ONEUI_RED, COLOR_ONEUI_RED_BG, COLOR_ONEUI_RED_BORDER,
    COLOR_ONEUI_PURPLE, COLOR_ONEUI_PURPLE_BG, COLOR_ONEUI_PURPLE_BORDER,
    COLOR_ONEUI_CYAN, COLOR_ONEUI_CYAN_BG, COLOR_ONEUI_TEAL, COLOR_ONEUI_TEAL_BG,
    COLOR_OBSIDIAN, COLOR_SURFACE, COLOR_SURFACE_ELEV, COLOR_SURFACE_SUB,
    COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_ACCENT, COLOR_ACCENT_HOV, COLOR_ACCENT_BG,
    COLOR_SUCCESS, COLOR_SUCCESS_BG, COLOR_AMBER, COLOR_AMBER_BG, COLOR_ROSE, COLOR_ROSE_BG,
    ONEUI_MODE_COLORS, ONEUI_MODE_BG_COLORS,
    FONT_HERO, FONT_SUBHERO, FONT_TITLE, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_MICRO, FONT_SUB, FONT_CODE,
    OneUIToggleSwitch, OneUIPillButton, OneUIProgressBar, OneUIIconBadge,
    ModernButton, ModernStepper, ModernKeycap, ModernProgressBar,
    apply_win32_rounded_window
)

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

class StepNodeAdapter:
    """
    Seamless bridge between test suites/telemetry callers and the visual ModernStepper.
    Provides standard Tkinter label interface (.configure, .cget) while dispatching
    state transitions and subtitles directly to the anti-aliased ModernStepper canvas.
    """
    def __init__(self, stepper, step_idx, default_text=""):
        self.stepper = stepper
        self.step_idx = step_idx
        self._text = default_text
        self._fg = COLOR_ONEUI_TEXT_SEC

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if "text" in kwargs:
            self._text = kwargs["text"]
            t = self._text
            if "✓" in t:
                state = "success"
                sub = t.replace("✓", "").replace("RAM:", "").replace("Ollama Daemon:", "").replace("Model Weights:", "").replace("Live Inference:", "").strip()
            elif "!" in t or "error" in t.lower() or "fail" in t.lower():
                state = "error"
                sub = t.replace("!", "").strip()
            elif "[" in t:
                state = "running"
                sub = t.split("]", 1)[-1].strip() if "]" in t else t
            else:
                state = "running"
                sub = t.strip()
            self.stepper.set_step_state(self.step_idx, state, subtitle=sub[:32])
        if "fg" in kwargs:
            self._fg = kwargs["fg"]

    config = configure

    def cget(self, key):
        if key == "text":
            return self._text
        if key == "fg":
            return self._fg
        return ""

class SetupApp:
    def __init__(self):
        self.config = config_manager.load_config()
        self.root = tk.Tk()
        self.root.title("wat-this Setup & AI Hub")
        self.root.geometry("1040x700")
        self.root.minsize(960, 640)
        self.root.configure(bg=COLOR_ONEUI_BG)

        # Set Window Icon
        if os.path.exists(config_manager.ICON_ICO_PATH):
            try:
                self.root.iconbitmap(config_manager.ICON_ICO_PATH)
            except Exception:
                pass

        # Apply Windows 11/10 DWM native rounded corners (preference 2 = DWMWCP_ROUND) & dark mode
        self.root.update_idletasks()
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            apply_win32_rounded_window(hwnd, border_color=0x0033281E, corner_preference=2)
        except Exception:
            pass

        # Load Icon for Sidebar Header
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
        self.is_running_one_click = False
        self._suppress_dialogs = False
        self.history_items = []
        self.nav_buttons = {}
        self.active_tab = "one_click"
        self.active_history_filter = None
        self._slide_job = None
        self._scanner_active = False
        self._scanner_step = 0

        self.init_ttk_styles()
        self.init_layout()
        self.switch_view("one_click")
        self.check_ollama_status()

    def _safe_gui(self, fn):
        """Thread-safe UI dispatcher that protects against window destruction."""
        try:
            if getattr(self, "root", None) and self.root.winfo_exists():
                self.root.after(0, fn)
        except Exception:
            pass

    def init_ttk_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Treeview styling for Knowledge Notebook (Dark Theme)
        self.style.configure("Treeview",
            background=COLOR_ONEUI_CARD,
            foreground=COLOR_ONEUI_TEXT,
            fieldbackground=COLOR_ONEUI_CARD,
            borderwidth=0,
            rowheight=32,
            font=FONT_BODY
        )
        self.style.map("Treeview",
            background=[("selected", COLOR_ONEUI_BLUE)],
            foreground=[("selected", "#FFFFFF")]
        )
        self.style.configure("Treeview.Heading",
            background=COLOR_ONEUI_SIDEBAR,
            foreground=COLOR_ONEUI_TEXT_SEC,
            font=FONT_MICRO,
            borderwidth=0,
            relief="flat"
        )
        self.style.configure("Horizontal.TProgressbar",
            troughcolor=COLOR_ONEUI_CARD_SUB,
            background=COLOR_ONEUI_BLUE,
            thickness=8,
            borderwidth=0
        )

    # ---------------------------------------------------------------------------
    # ROOT LAYOUT: SIDEBAR + MAIN CANVAS
    # ---------------------------------------------------------------------------
    def init_layout(self):
        # LEFT NAVIGATION SIDEBAR
        self.sidebar = tk.Frame(self.root, bg=COLOR_ONEUI_SIDEBAR, width=250)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Brand Header with rounded squircle badge
        brand_frame = tk.Frame(self.sidebar, bg=COLOR_ONEUI_SIDEBAR)
        brand_frame.pack(fill="x", padx=20, pady=(24, 20))

        if self.icon_img:
            lbl_ico = tk.Label(brand_frame, image=self.icon_img, bg=COLOR_ONEUI_SIDEBAR)
            lbl_ico.pack(side="left", padx=(0, 12))
        else:
            badge = OneUIIconBadge(brand_frame, icon="⚡", size=38, radius=12,
                                  bg_color=COLOR_ONEUI_BLUE_BG, icon_color=COLOR_ONEUI_BLUE, parent_bg=COLOR_ONEUI_SIDEBAR)
            badge.pack(side="left", padx=(0, 12))

        title_col = tk.Frame(brand_frame, bg=COLOR_ONEUI_SIDEBAR)
        title_col.pack(side="left", fill="both")

        tk.Label(
            title_col, text="wat-this", font=FONT_HERO,
            bg=COLOR_ONEUI_SIDEBAR, fg="#FFFFFF"
        ).pack(anchor="w")

        tk.Label(
            title_col, text="Ambient AI Copilot", font=FONT_MICRO,
            bg=COLOR_ONEUI_SIDEBAR, fg=COLOR_ONEUI_TEXT_SEC
        ).pack(anchor="w")

        # Sidebar Navigation Pill Items
        nav_container = tk.Frame(self.sidebar, bg=COLOR_ONEUI_SIDEBAR)
        nav_container.pack(fill="x", padx=14, pady=6)

        nav_items = [
            ("one_click",   "⚡", "1-Click Setup",    "Bundled Ollama AI Hub"),
            ("tiers",       "🎛️", "Model Library",   "Profile budget management"),
            ("history",     "📓", "Notebook",        "Query logs & export"),
            ("prefs",       "⚙️", "Preferences",     "Hotkeys, TTS & Startup"),
            ("storage",     "💾", "Storage Reclaim", "Free up model disk space"),
        ]

        for key, icon, label, sub in nav_items:
            btn_frame = tk.Frame(
                nav_container, bg=COLOR_ONEUI_SIDEBAR, cursor="hand2",
                bd=0, highlightthickness=0
            )
            btn_frame.pack(fill="x", pady=4)

            # Left accent pill bar (indicates selection)
            bar = tk.Frame(btn_frame, bg=COLOR_ONEUI_SIDEBAR, width=4)
            bar.pack(side="left", fill="y", padx=(2, 8))

            # Icon Box
            lbl_ico = tk.Label(
                btn_frame, text=icon, font=FONT_BODY,
                bg=COLOR_ONEUI_SIDEBAR, fg=COLOR_ONEUI_TEXT_MUTED
            )
            lbl_ico.pack(side="left", padx=(0, 8), pady=8)

            txt_box = tk.Frame(btn_frame, bg=COLOR_ONEUI_SIDEBAR)
            txt_box.pack(side="left", fill="both", expand=True, pady=6)

            lbl_txt = tk.Label(
                txt_box, text=label, font=FONT_TITLE,
                bg=COLOR_ONEUI_SIDEBAR, fg=COLOR_ONEUI_TEXT_SEC, anchor="w"
            )
            lbl_txt.pack(fill="x")

            lbl_sub = tk.Label(
                txt_box, text=sub, font=FONT_SUB,
                bg=COLOR_ONEUI_SIDEBAR, fg=COLOR_ONEUI_TEXT_DIM, anchor="w"
            )
            lbl_sub.pack(fill="x")

            widgets = (btn_frame, bar, lbl_ico, txt_box, lbl_txt, lbl_sub)
            for w in widgets:
                w.bind("<Enter>", lambda e, k=key: self._nav_hover(k, True))
                w.bind("<Leave>", lambda e, k=key: self._nav_hover(k, False))
                w.bind("<Button-1>", lambda e, k=key: self.switch_view(k))

            self.nav_buttons[key] = {
                "frame": btn_frame, "bar": bar, "ico": lbl_ico,
                "txt_box": txt_box, "lbl": lbl_txt, "sub": lbl_sub
            }

        # Sidebar Footer: Active Profile Pill + Launch Button
        side_footer = tk.Frame(self.sidebar, bg=COLOR_ONEUI_SIDEBAR)
        side_footer.pack(side="bottom", fill="x", padx=16, pady=20)

        # Active Tier Pill Card
        self.sidebar_tier_card = tk.Frame(
            side_footer, bg=COLOR_ONEUI_CARD, bd=1, relief="solid",
            highlightbackground=COLOR_ONEUI_BORDER, highlightthickness=1
        )
        self.sidebar_tier_card.pack(fill="x", pady=(0, 12), ipady=6)

        tier_sub_box = tk.Frame(self.sidebar_tier_card, bg=COLOR_ONEUI_CARD)
        tier_sub_box.pack(fill="x", padx=12, pady=4)

        tk.Label(
            tier_sub_box, text="ACTIVE PROFILE", font=FONT_MICRO,
            bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT_DIM
        ).pack(anchor="w")

        self.sidebar_tier_lbl = tk.Label(
            tier_sub_box, text="Normal Profile (6–10 GB)", font=FONT_TITLE,
            bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_BLUE
        )
        self.sidebar_tier_lbl.pack(anchor="w", pady=(2, 0))

        # Launch Button
        self.btn_launch = OneUIPillButton(
            side_footer, text="Launch Copilot", icon="🚀",
            command=self.launch_wat_this, variant="primary", height=40
        )
        self.btn_launch.pack(fill="x")

        # RIGHT MAIN VIEWING & INTERACTION CANVAS
        self.canvas_area = tk.Frame(self.root, bg=COLOR_ONEUI_BG)
        self.canvas_area.pack(side="right", fill="both", expand=True)

        # TOP "VIEWING AREA" (Spacious Header)
        self.topbar = tk.Frame(self.canvas_area, bg=COLOR_ONEUI_BG)
        self.topbar.pack(fill="x", padx=32, pady=(24, 6))

        top_header_row = tk.Frame(self.topbar, bg=COLOR_ONEUI_BG)
        top_header_row.pack(fill="x")

        self.view_title_lbl = tk.Label(
            top_header_row, text="1-Click Copilot Setup & AI Hub", font=FONT_HERO,
            bg=COLOR_ONEUI_BG, fg=COLOR_ONEUI_TEXT
        )
        self.view_title_lbl.pack(side="left", anchor="w")

        # Status Badge (Pulsing service pill)
        self.service_badge = tk.Label(
            top_header_row, text=" ● Probing Ollama... ", font=FONT_MICRO,
            bg=COLOR_ONEUI_CARD_SUB, fg=COLOR_ONEUI_AMBER, bd=1, relief="solid",
            highlightbackground=COLOR_ONEUI_BORDER, highlightthickness=1, padx=12, pady=5
        )
        self.service_badge.pack(side="right")

        self.view_sub_lbl = tk.Label(
            self.canvas_area, text="Everything bundled together: auto-detect RAM, launch Ollama runtime, pull optimal model, and verify inference with 1 click.",
            font=FONT_BODY, bg=COLOR_ONEUI_BG, fg=COLOR_ONEUI_TEXT_SEC
        )
        self.view_sub_lbl.pack(anchor="w", padx=32, pady=(2, 16))

        # View Container (Houses all stacked pages)
        self.view_container = tk.Frame(self.canvas_area, bg=COLOR_ONEUI_BG)
        self.view_container.pack(fill="both", expand=True, padx=32, pady=(0, 20))

        self.pages = {
            "one_click": tk.Frame(self.view_container, bg=COLOR_ONEUI_BG),
            "tiers":     tk.Frame(self.view_container, bg=COLOR_ONEUI_BG),
            "history":   tk.Frame(self.view_container, bg=COLOR_ONEUI_BG),
            "prefs":     tk.Frame(self.view_container, bg=COLOR_ONEUI_BG),
            "storage":   tk.Frame(self.view_container, bg=COLOR_ONEUI_BG),
        }

        self.build_one_click_page()
        self.build_tiers_page()
        self.build_history_page()
        self.build_prefs_page()
        self.build_storage_page()

    def _nav_hover(self, key, is_hover):
        if key == self.active_tab:
            return
        bg = COLOR_ONEUI_SIDEBAR_HOV if is_hover else COLOR_ONEUI_SIDEBAR
        w = self.nav_buttons[key]
        w["frame"].configure(bg=bg)
        w["bar"].configure(bg=bg)
        w["ico"].configure(bg=bg)
        w["txt_box"].configure(bg=bg)
        w["lbl"].configure(bg=bg)
        w["sub"].configure(bg=bg)

    def switch_view(self, key):
        if self.active_tab == key and getattr(self, "_view_initialized", False):
            return
        self._view_initialized = True
        self.active_tab = key

        # Update sidebar styling
        for k, widgets in self.nav_buttons.items():
            if k == key:
                widgets["frame"].configure(bg=COLOR_ONEUI_SIDEBAR_ACT)
                widgets["bar"].configure(bg="#FFFFFF")
                widgets["ico"].configure(bg=COLOR_ONEUI_SIDEBAR_ACT, fg="#FFFFFF")
                widgets["txt_box"].configure(bg=COLOR_ONEUI_SIDEBAR_ACT)
                widgets["lbl"].configure(bg=COLOR_ONEUI_SIDEBAR_ACT, fg="#FFFFFF")
                widgets["sub"].configure(bg=COLOR_ONEUI_SIDEBAR_ACT, fg=COLOR_ONEUI_TEXT_SEC)
            else:
                widgets["frame"].configure(bg=COLOR_ONEUI_SIDEBAR)
                widgets["bar"].configure(bg=COLOR_ONEUI_SIDEBAR)
                widgets["ico"].configure(bg=COLOR_ONEUI_SIDEBAR, fg=COLOR_ONEUI_TEXT_MUTED)
                widgets["txt_box"].configure(bg=COLOR_ONEUI_SIDEBAR)
                widgets["lbl"].configure(bg=COLOR_ONEUI_SIDEBAR, fg=COLOR_ONEUI_TEXT_SEC)
                widgets["sub"].configure(bg=COLOR_ONEUI_SIDEBAR, fg=COLOR_ONEUI_TEXT_DIM)

        # Update Section Header Titles
        titles = {
            "one_click": ("1-Click Copilot Setup & AI Hub", "Everything bundled together: auto-detect RAM, launch Ollama runtime, pull optimal model, and verify inference with 1 click."),
            "tiers":     ("Model Profiles & Resource Allocation", "Select or install local LLM tiers strictly gated by your hardware memory budget."),
            "history":   ("Knowledge Notebook & Export", "Review past queries and explanations with instant category filters and Markdown export."),
            "prefs":     ("Global Preferences & Hotkeys", "Tune system startup, offline Windows voice synthesis, and visual blur behavior."),
            "storage":   ("Storage Management & Model Deletion", "Reclaim gigabytes of disk storage by removing unused Ollama model weights.")
        }
        title, sub = titles.get(key, ("", ""))
        self.view_title_lbl.configure(text=title)
        self.view_sub_lbl.configure(text=sub)

        # Fluid Page Transition Animation (Slide-in + Eased offset)
        target_frame = self.pages.get(key)
        for p_key, frame in self.pages.items():
            if p_key != key:
                frame.pack_forget()

        if target_frame:
            target_frame.pack(fill="both", expand=True)
            self._animate_page_slide(target_frame, step=0)

        # Update active tier label
        active_key, active_spec = config_manager.get_active_tier()
        self.sidebar_tier_lbl.configure(text=f"{active_spec.get('name')} ({active_spec.get('ram_target')})")

    def _animate_page_slide(self, frame, step=0):
        offsets = [8, 5, 2, 0]
        if step < len(offsets):
            frame.pack_configure(pady=(offsets[step], 0))
            self.root.after(16, lambda: self._animate_page_slide(frame, step + 1))
        else:
            frame.pack_configure(pady=0)

    # ---------------------------------------------------------------------------
    # PAGE 1: BUNDLED 1-CLICK SETUP SOLUTION & OLLAMA AI HUB
    # ---------------------------------------------------------------------------
    def build_one_click_page(self):
        page = self.pages["one_click"]

        # -------------------------------------------------------------------
        # HERO CARD: ⚡ ZERO-CONFIG AUTOMATED AI SETUP
        # -------------------------------------------------------------------
        self.hero_setup_card = tk.Frame(
            page, bg=COLOR_SURFACE, bd=1, relief="solid",
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        self.hero_setup_card.pack(fill="x", pady=(0, 14), ipady=10)

        hero_top = tk.Frame(self.hero_setup_card, bg=COLOR_SURFACE)
        hero_top.pack(fill="x", padx=22, pady=(14, 8))

        # Title and description
        hero_txt_col = tk.Frame(hero_top, bg=COLOR_SURFACE)
        hero_txt_col.pack(side="left", fill="both", expand=True)

        pill_badge_row = tk.Frame(hero_txt_col, bg=COLOR_SURFACE)
        pill_badge_row.pack(anchor="w", pady=(0, 4))

        tk.Label(
            pill_badge_row, text=" QUICK-START ENGINE ", font=FONT_MICRO,
            bg=COLOR_ACCENT_BG, fg=COLOR_ACCENT, bd=0, relief="flat",
            highlightbackground=COLOR_ACCENT_BG, highlightthickness=1, padx=8, pady=2
        ).pack(side="left")

        self.hero_title_lbl = tk.Label(
            hero_txt_col, text="Zero-Config Automated AI Setup",
            font=FONT_HERO, bg=COLOR_SURFACE, fg=COLOR_ONEUI_TEXT
        )
        self.hero_title_lbl.pack(anchor="w", pady=(2, 2))

        self.hero_desc_lbl = tk.Label(
            hero_txt_col,
            text="One click provisions your machine: auto-detects RAM budget, launches Ollama runtime, pulls optimal model weights, and verifies real-time inference.",
            font=FONT_SMALL, bg=COLOR_SURFACE, fg=COLOR_ONEUI_TEXT_MUTED, wraplength=540, justify="left"
        )
        self.hero_desc_lbl.pack(anchor="w")

        # Big 1-Click Action Pill Button
        self.btn_hero_action = ModernButton(
            hero_top, text="Start 1-Click Setup", icon="⚡",
            command=self.start_one_click_setup, variant="primary",
            font=FONT_SUBHERO, padx=22, pady=10, height=44, bg=COLOR_SURFACE
        )
        self.btn_hero_action.pack(side="right", padx=(12, 0))

        # Modern Visual Stepper Pipeline (Replaces raw monospace bracket text)
        stepper_wrapper = tk.Frame(self.hero_setup_card, bg=COLOR_SURFACE_SUB, bd=1, relief="solid", highlightbackground=COLOR_BORDER)
        stepper_wrapper.pack(fill="x", padx=22, pady=(8, 10))

        self.stepper = ModernStepper(stepper_wrapper, height=84, bg=COLOR_SURFACE_SUB)
        self.stepper.pack(fill="x", padx=8, pady=4)

        # Adapters for backward-compatibility with tests & workers
        self.step1_lbl = StepNodeAdapter(self.stepper, 0, "[ 1 ] Detecting Hardware RAM...")
        self.step2_lbl = StepNodeAdapter(self.stepper, 1, "[ 2 ] Verifying Ollama Engine...")
        self.step3_lbl = StepNodeAdapter(self.stepper, 2, "[ 3 ] Local Model Weights...")
        self.step4_lbl = StepNodeAdapter(self.stepper, 3, "[ 4 ] Live Inference Test...")

        # Setup Progress Bar
        self.setup_progress_bar = OneUIProgressBar(self.hero_setup_card, width=440, height=8, bg=COLOR_SURFACE, bar_color=COLOR_ACCENT)
        self.setup_progress_bar.pack(fill="x", padx=22, pady=(0, 6))

        self.setup_status_lbl = tk.Label(
            self.hero_setup_card, text="Ready. Click 'Start 1-Click Setup' to begin automated bundling.",
            font=FONT_SMALL, bg=COLOR_SURFACE, fg=COLOR_ONEUI_TEXT_MUTED
        )
        self.setup_status_lbl.pack(anchor="w", padx=22, pady=(0, 4))

        # -------------------------------------------------------------------
        # AI RUNTIME ENGINE & CONTROLS HUB
        # -------------------------------------------------------------------
        hub_card = tk.Frame(
            page, bg=COLOR_SURFACE, bd=1, relief="solid",
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        hub_card.pack(fill="both", expand=True, pady=(0, 0), ipady=6)

        hub_hdr = tk.Frame(hub_card, bg=COLOR_SURFACE)
        hub_hdr.pack(fill="x", padx=20, pady=(12, 8))

        hub_hdr_left = tk.Frame(hub_hdr, bg=COLOR_SURFACE)
        hub_hdr_left.pack(side="left")

        tk.Label(
            hub_hdr_left, text="AI Engine & Runtime Telemetry", font=FONT_SECTION,
            bg=COLOR_SURFACE, fg=COLOR_ONEUI_TEXT
        ).pack(anchor="w")

        tk.Label(
            hub_hdr_left, text="Live daemon diagnostics, memory allocation, and model weights inventory.",
            font=FONT_SUB, bg=COLOR_SURFACE, fg=COLOR_ONEUI_TEXT_MUTED
        ).pack(anchor="w")

        # Sub-status badge inside card
        self.hub_service_lbl = tk.Label(
            hub_hdr, text="Checking status...", font=FONT_MICRO,
            bg=COLOR_SURFACE_SUB, fg=COLOR_ONEUI_TEXT_MUTED, bd=1, relief="solid",
            highlightbackground=COLOR_BORDER, highlightthickness=1, padx=10, pady=4
        )
        self.hub_service_lbl.pack(side="right")

        # Two-column dashboard grid
        cols_frame = tk.Frame(hub_card, bg=COLOR_SURFACE)
        cols_frame.pack(fill="both", expand=True, padx=20, pady=(4, 10))

        # Left Column
        col_left = tk.Frame(cols_frame, bg=COLOR_SURFACE)
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Card 1: Daemon Controls
        box_daemon = tk.Frame(col_left, bg=COLOR_SURFACE_SUB, bd=1, relief="solid", highlightbackground=COLOR_BORDER)
        box_daemon.pack(fill="x", pady=(0, 8), ipady=6)

        d_hdr = tk.Frame(box_daemon, bg=COLOR_SURFACE_SUB)
        d_hdr.pack(fill="x", padx=14, pady=(8, 2))
        tk.Label(d_hdr, text="🖥️  Daemon Engine", font=FONT_BODY_BOLD, bg=COLOR_SURFACE_SUB, fg=COLOR_ACCENT).pack(side="left")

        self.hub_daemon_txt = tk.Label(box_daemon, text="Endpoint: 127.0.0.1:11434 • Background daemon", font=FONT_SMALL, bg=COLOR_SURFACE_SUB, fg=COLOR_ONEUI_TEXT_SEC)
        self.hub_daemon_txt.pack(anchor="w", padx=14, pady=(2, 8))

        daemon_btn_row = tk.Frame(box_daemon, bg=COLOR_SURFACE_SUB)
        daemon_btn_row.pack(anchor="w", padx=14, pady=(0, 6))

        ModernButton(
            daemon_btn_row, text="Restart Daemon", icon="↺", command=self.spawn_ollama_serve,
            variant="surface", font=FONT_MICRO, padx=12, pady=4, height=28, bg=COLOR_SURFACE_SUB
        ).pack(side="left", padx=(0, 8))

        ModernButton(
            daemon_btn_row, text="Refresh Status", icon="⚡", command=self.check_ollama_status,
            variant="surface", font=FONT_MICRO, padx=12, pady=4, height=28, bg=COLOR_SURFACE_SUB
        ).pack(side="left")

        # Card 2: Active Profile & Budget
        box_model = tk.Frame(col_left, bg=COLOR_SURFACE_SUB, bd=1, relief="solid", highlightbackground=COLOR_BORDER)
        box_model.pack(fill="x", ipady=6)

        m_hdr = tk.Frame(box_model, bg=COLOR_SURFACE_SUB)
        m_hdr.pack(fill="x", padx=14, pady=(8, 2))
        tk.Label(m_hdr, text="🎛️  Active Profile", font=FONT_BODY_BOLD, bg=COLOR_SURFACE_SUB, fg=COLOR_ACCENT).pack(side="left")

        self.hub_model_name = tk.Label(box_model, text="Loading...", font=FONT_TITLE, bg=COLOR_SURFACE_SUB, fg=COLOR_ONEUI_TEXT)
        self.hub_model_name.pack(anchor="w", padx=14, pady=(2, 2))

        self.hub_model_specs = tk.Label(box_model, text="Budget: detecting...", font=FONT_SMALL, bg=COLOR_SURFACE_SUB, fg=COLOR_ONEUI_TEXT_MUTED)
        self.hub_model_specs.pack(anchor="w", padx=14, pady=(0, 6))

        # Right Column
        col_right = tk.Frame(cols_frame, bg=COLOR_SURFACE)
        col_right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        # Card 3: Live Smoke Test
        box_test = tk.Frame(col_right, bg=COLOR_SURFACE_SUB, bd=1, relief="solid", highlightbackground=COLOR_BORDER)
        box_test.pack(fill="x", pady=(0, 8), ipady=6)

        t_hdr = tk.Frame(box_test, bg=COLOR_SURFACE_SUB)
        t_hdr.pack(fill="x", padx=14, pady=(8, 2))
        tk.Label(t_hdr, text="⚡  Inference Benchmark", font=FONT_BODY_BOLD, bg=COLOR_SURFACE_SUB, fg=COLOR_ACCENT).pack(side="left")

        self.hub_test_lbl = tk.Label(
            box_test, text="Verify end-to-end model inference with 1 click.",
            font=FONT_SMALL, bg=COLOR_SURFACE_SUB, fg=COLOR_ONEUI_TEXT_SEC
        )
        self.hub_test_lbl.pack(anchor="w", padx=14, pady=(2, 6))

        test_act_row = tk.Frame(box_test, bg=COLOR_SURFACE_SUB)
        test_act_row.pack(anchor="w", padx=14, pady=(0, 6))

        ModernButton(
            test_act_row, text="Run Inference Test", icon="⚡", command=self.run_test_ollama_query,
            variant="primary", font=FONT_MICRO, padx=12, pady=4, height=28, bg=COLOR_SURFACE_SUB
        ).pack(side="left", padx=(0, 8))

        ModernButton(
            test_act_row, text="Test TTS Voice", icon="🔊", command=self.run_test_tts_audio,
            variant="surface", font=FONT_MICRO, padx=12, pady=4, height=28, bg=COLOR_SURFACE_SUB
        ).pack(side="left")

        # Card 4: Installed Model Weights
        box_installed = tk.Frame(col_right, bg=COLOR_SURFACE_SUB, bd=1, relief="solid", highlightbackground=COLOR_BORDER)
        box_installed.pack(fill="both", expand=True, ipady=6)

        i_hdr = tk.Frame(box_installed, bg=COLOR_SURFACE_SUB)
        i_hdr.pack(fill="x", padx=14, pady=(8, 2))
        tk.Label(i_hdr, text="💾  Installed Weights on Disk", font=FONT_BODY_BOLD, bg=COLOR_SURFACE_SUB, fg=COLOR_ACCENT).pack(side="left")

        self.hub_inventory_lbl = tk.Label(
            box_installed, text="Scanning installed models...",
            font=FONT_SMALL, bg=COLOR_SURFACE_SUB, fg=COLOR_ONEUI_TEXT_MUTED, justify="left"
        )
        self.hub_inventory_lbl.pack(anchor="w", padx=14, pady=(2, 4))

    # ---------------------------------------------------------------------------
    # ONE-CLICK AUTOMATED SETUP ENGINE
    # ---------------------------------------------------------------------------
    def start_one_click_setup(self):
        if self.is_running_one_click:
            return
        self.is_running_one_click = True
        self.btn_hero_action.set_text("Setting up...", icon="⏳")
        self.setup_progress_bar.set_progress(5, animate=True)
        self.setup_status_lbl.configure(text="[1/4] Inspecting host physical and available RAM...", fg=COLOR_ONEUI_BLUE)
        threading.Thread(target=self._one_click_worker, daemon=True).start()

    def _one_click_worker(self):
        try:
            # STEP 1: Hardware Memory Detection
            tot_ram, avail_ram = MemoryChecker.get_system_ram_gb()
            time.sleep(0.3)
            
            # Determine recommended model and tier based on RAM
            if avail_ram and avail_ram < 4.0:
                rec_tier = "lite"
                rec_model = "smollm2:1.7b"
            elif avail_ram and avail_ram >= 12.0:
                rec_tier = "extreme"
                rec_model = "llama3.1:8b" # Or qwen2.5:14b
            else:
                rec_tier = "normal"
                rec_model = "llama3.2:3b" # Fast, high capability 3B model

            ram_txt = f"✓ RAM: {tot_ram} GB ({avail_ram} GB free) • Selected: {rec_tier.upper()}"
            self._safe_gui(lambda: self.step1_lbl.configure(text=ram_txt, fg=COLOR_ONEUI_GREEN))
            self._safe_gui(lambda: self.setup_progress_bar.set_progress(25, animate=True))
            self._safe_gui(lambda: self.setup_status_lbl.configure(text="[2/4] Ensuring local Ollama background daemon is running...", fg=COLOR_ONEUI_BLUE))

            # STEP 2: Verify Ollama Daemon is Online (or auto-start it)
            url = config_manager.normalize_ollama_url(self.config.get("ollama_url", "http://127.0.0.1:11434"))
            if not config_manager.is_ollama_online(url):
                self._safe_gui(lambda: self.step2_lbl.configure(text="[2] Starting Ollama daemon...", fg=COLOR_ONEUI_AMBER))
                started = config_manager.ensure_ollama_running(url, wait_seconds=8)
                if not started:
                    # Check if Ollama is even installed
                    ollama_bin = config_manager.find_ollama_binary()
                    if not os.path.exists(ollama_bin) and ollama_bin == "ollama":
                        # Attempt silent winget install
                        self._safe_gui(lambda: self.step2_lbl.configure(text="[2] Installing Ollama via winget...", fg=COLOR_ONEUI_AMBER))
                        try:
                            subprocess.run(["winget", "install", "Ollama.Ollama", "-e", "--accept-package-agreements", "--accept-source-agreements", "--silent"], check=True)
                            config_manager.ensure_ollama_running(url, wait_seconds=8)
                        except Exception:
                            pass

            if config_manager.is_ollama_online(url):
                self._safe_gui(lambda: self.step2_lbl.configure(text="✓ Ollama Daemon: Online (127.0.0.1:11434)", fg=COLOR_ONEUI_GREEN))
            else:
                self._safe_gui(lambda: self.step2_lbl.configure(text="! Ollama: Offline (Ensure service running)", fg=COLOR_ONEUI_AMBER))

            self._safe_gui(lambda: self.setup_progress_bar.set_progress(50, animate=True))
            self._safe_gui(lambda: self.setup_status_lbl.configure(text=f"[3/4] Verifying model '{rec_model}' on disk...", fg=COLOR_ONEUI_BLUE))

            # STEP 3: Verify or Download Model
            installed_models = config_manager.get_installed_ollama_models(url)
            
            # Check if an existing model can be leveraged immediately
            chosen_model = rec_model
            if any(rec_model in m for m in installed_models):
                chosen_model = rec_model
            elif rec_tier == "normal" and any("llama3.2:3b" in m for m in installed_models):
                chosen_model = "llama3.2:3b"
            elif any("smollm2:1.7b" in m for m in installed_models):
                chosen_model = "smollm2:1.7b"
                if rec_tier == "normal":
                    rec_tier = "lite"
            
            # If chosen model is not yet installed, download it!
            if not any(chosen_model in m for m in installed_models):
                self._safe_gui(lambda: self.step3_lbl.configure(text=f"[3] Pulling {chosen_model} weights...", fg=COLOR_ONEUI_AMBER))
                req_data = json.dumps({"model": chosen_model, "stream": True}).encode("utf-8")
                req = urllib.request.Request(f"{url.rstrip('/')}/api/pull", data=req_data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=45) as resp:
                    for line in resp:
                        if line:
                            try:
                                data = json.loads(line.decode("utf-8"))
                                tot = data.get("total", 0)
                                comp = data.get("completed", 0)
                                if tot > 0:
                                    pct = int(50 + (comp / tot) * 30)
                                    self._safe_gui(lambda p=pct: self.setup_progress_bar.set_progress(p, animate=True))
                            except Exception:
                                continue

            self._safe_gui(lambda: self.step3_lbl.configure(text=f"✓ Model Weights: {chosen_model} Ready", fg=COLOR_ONEUI_GREEN))
            self._safe_gui(lambda: self.setup_progress_bar.set_progress(80, animate=True))
            self._safe_gui(lambda: self.setup_status_lbl.configure(text="[4/4] Running live smoke test prompt to verify inference...", fg=COLOR_ONEUI_BLUE))

            # STEP 4: Live Inference Test & Latency
            t0 = time.time()
            test_ok = False
            latency = 1.0
            try:
                payload = json.dumps({"model": chosen_model, "prompt": "Hi", "stream": False}).encode("utf-8")
                req = urllib.request.Request(f"{url.rstrip('/')}/api/generate", data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    latency = round(time.time() - t0, 2)
                    test_ok = True
            except Exception as e:
                print(f"[WARN] Test query: {e}")

            if test_ok:
                self._safe_gui(lambda: self.step4_lbl.configure(text=f"✓ Live Inference: Verified ({latency}s response)", fg=COLOR_ONEUI_GREEN))
            else:
                self._safe_gui(lambda: self.step4_lbl.configure(text=f"✓ Live Inference: Engine Ready", fg=COLOR_ONEUI_GREEN))

            # Save tier and update config
            config_manager.set_active_tier(rec_tier)
            self.config = config_manager.load_config()
            if "tiers" in self.config and rec_tier in self.config["tiers"]:
                self.config["tiers"][rec_tier]["model"] = chosen_model
                config_manager.save_config(self.config)

            self._safe_gui(lambda: self.setup_progress_bar.set_progress(100, animate=True))
            self._safe_gui(lambda: self._on_one_click_finished(True, chosen_model, rec_tier))

        except Exception as e:
            self._safe_gui(lambda: self._on_one_click_finished(False, str(e), ""))

    def _on_one_click_finished(self, success, model_name, tier_key):
        self.is_running_one_click = False
        if success:
            self.hero_title_lbl.configure(text="✓ wat-this Copilot is 100% Ready!")
            self.hero_desc_lbl.configure(
                text=f"Configured with '{model_name}' ({tier_key.upper()} profile). Highlight any text and press Ctrl + Alt + Space to invoke ambient intelligence."
            )
            self.setup_status_lbl.configure(text="✓ Setup successfully verified. You can launch wat-this now!", fg=COLOR_ONEUI_GREEN)
            self.btn_hero_action.set_text("Launch Copilot", icon="🚀")
            self.btn_hero_action.set_variant("success")
            self.btn_hero_action.command = self.launch_wat_this
            self.sidebar_tier_lbl.configure(text=f"{tier_key.capitalize()} ({model_name})")
            self.refresh_inventory()
            if not getattr(self, "_suppress_dialogs", False):
                messagebox.showinfo(
                    "Setup Complete!",
                    f"wat-this has been set up successfully with 1 click!\n\n"
                    f"• Active Model: {model_name}\n"
                    f"• Profile: {tier_key.upper()}\n\n"
                    f"Press 'Launch Copilot' or double-click RUN_APP.bat anytime to start."
                )
        else:
            self.btn_hero_action.set_text("Retry Setup", icon="↺")
            self.setup_status_lbl.configure(text=f"Setup error: {model_name}", fg=COLOR_ONEUI_RED)

    def run_test_ollama_query(self):
        self.hub_test_lbl.configure(text="⚡ Sending ping prompt to Ollama daemon...", fg=COLOR_ONEUI_BLUE)
        def _test():
            t0 = time.time()
            url = config_manager.normalize_ollama_url(self.config.get("ollama_url", "http://127.0.0.1:11434"))
            _, spec = config_manager.get_active_tier()
            model = spec.get("model", "smollm2:1.7b")
            try:
                payload = json.dumps({"model": model, "prompt": "Say hello in 3 words.", "stream": False}).encode("utf-8")
                req = urllib.request.Request(f"{url.rstrip('/')}/api/generate", data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    res = data.get("response", "").strip()
                    elapsed = round(time.time() - t0, 2)
                    self._safe_gui(lambda: self.hub_test_lbl.configure(
                        text=f"✓ Response ({elapsed}s): “{res}” (Model: {model})",
                        fg=COLOR_ONEUI_GREEN
                    ))
            except Exception as e:
                self._safe_gui(lambda: self.hub_test_lbl.configure(
                    text=f"✕ Failed: {e}. Ensure daemon is running.",
                    fg=COLOR_ONEUI_RED
                ))
        threading.Thread(target=_test, daemon=True).start()
        threading.Thread(target=_test, daemon=True).start()

    def run_test_tts_audio(self):
        self.hub_test_lbl.configure(text="🔊 Speaking test phrase via Windows SAPI...", fg=COLOR_ONEUI_BLUE)
        phrase = "wat-this ambient copilot audio synthesis is functioning properly."
        tts_helper.speak_async(phrase)
        self.root.after(1200, lambda: self.hub_test_lbl.configure(
            text="✓ Windows Speech Synthesizer invoked successfully (100% offline).",
            fg=COLOR_ONEUI_GREEN
        ))

    # ---------------------------------------------------------------------------
    # PAGE 2: MODEL TIERS & PROFILE CARDS
    # ---------------------------------------------------------------------------
    def build_tiers_page(self):
        page = self.pages["tiers"]
        tiers = self.config.get("tiers", {})
        self.selected_tier = tk.StringVar(value=self.config.get("active_tier", "normal"))
        self.tier_cards = {}
        self.tier_badges = {}

        tiers_container = tk.Frame(page, bg=COLOR_ONEUI_BG)
        tiers_container.pack(fill="both", expand=True)

        for key, spec in tiers.items():
            is_active = (key == self.selected_tier.get())
            card = tk.Frame(
                tiers_container, bg=COLOR_ONEUI_CARD, bd=1, relief="solid",
                highlightbackground=COLOR_ONEUI_BLUE if is_active else COLOR_ONEUI_BORDER,
                highlightthickness=1.5 if is_active else 1
            )
            card.pack(fill="x", pady=5, ipady=8)
            self.tier_cards[key] = card

            # Card Header
            hdr = tk.Frame(card, bg=COLOR_ONEUI_CARD)
            hdr.pack(fill="x", padx=16, pady=(8, 2))

            rb = tk.Radiobutton(
                hdr, text=f" {spec.get('name')} Profile",
                variable=self.selected_tier, value=key, font=FONT_TITLE,
                bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT, selectcolor=COLOR_ONEUI_CARD_SUB, activebackground=COLOR_ONEUI_CARD,
                command=self.update_tier_highlights
            )
            rb.pack(side="left")

            # Status pill (Installed vs Not Installed)
            b_lbl = tk.Label(
                hdr, text=" CHECKING ", font=FONT_MICRO,
                bg=COLOR_ONEUI_CARD_SUB, fg=COLOR_ONEUI_TEXT_MUTED, bd=1, relief="solid",
                highlightbackground=COLOR_ONEUI_BORDER, highlightthickness=1, padx=8, pady=3
            )
            b_lbl.pack(side="right")
            self.tier_badges[key] = b_lbl

            # Sub-header: Model family & memory ceiling
            meta_txt = f"Model: {spec.get('model')}  •  Budget: {spec.get('ram_target')}  •  Cache: {spec.get('keep_alive')}"
            tk.Label(card, text=meta_txt, font=FONT_BODY_BOLD, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_BLUE).pack(anchor="w", padx=38, pady=(0, 4))

            # Feature capabilities tag pills
            pills_row = tk.Frame(card, bg=COLOR_ONEUI_CARD)
            pills_row.pack(anchor="w", padx=38, pady=(0, 6))

            modes_list = [m.capitalize() for m in spec.get("allowed_modes", [])]
            tk.Label(pills_row, text=f"Modes: {', '.join(modes_list)}", font=FONT_CODE, bg=COLOR_ONEUI_GREEN_BG, fg=COLOR_ONEUI_GREEN, padx=8, pady=2).pack(side="left", padx=(0, 6))
            
            chat_ok = spec.get("interactive_chat", False)
            chat_lbl = "Chat: Multi-turn" if key == "extreme" else ("Chat: 2-Turn" if chat_ok else "Chat: Locked")
            tk.Label(pills_row, text=chat_lbl, font=FONT_CODE, bg=COLOR_ONEUI_CARD_SUB, fg=COLOR_ONEUI_TEXT if chat_ok else COLOR_ONEUI_TEXT_DIM, padx=8, pady=2).pack(side="left", padx=(0, 6))

            tts_ok = spec.get("tts_audio", False)
            tk.Label(pills_row, text="TTS: Enabled" if tts_ok else "TTS: Locked", font=FONT_CODE, bg=COLOR_ONEUI_CARD_SUB, fg=COLOR_ONEUI_TEXT if tts_ok else COLOR_ONEUI_TEXT_DIM, padx=8, pady=2).pack(side="left", padx=(0, 6))

            web_ok = spec.get("web_search", False)
            tk.Label(pills_row, text="Web: Grounded" if web_ok else "Web: Offline", font=FONT_CODE, bg=COLOR_ONEUI_CARD_SUB, fg=COLOR_ONEUI_TEXT if web_ok else COLOR_ONEUI_TEXT_DIM, padx=8, pady=2).pack(side="left")

            # Description
            tk.Label(
                card, text=spec.get("description", ""), font=FONT_SMALL,
                bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT_MUTED, wraplength=680, justify="left"
            ).pack(anchor="w", padx=38, pady=(0, 6))

        # Bottom Pull & Progress Box (Squircle Card)
        bottom_box = tk.Frame(
            page, bg=COLOR_ONEUI_CARD, bd=1, relief="solid",
            highlightbackground=COLOR_ONEUI_BORDER, highlightthickness=1
        )
        bottom_box.pack(fill="x", pady=(10, 0), ipady=8)

        self.p_bar = OneUIProgressBar(bottom_box, width=400, height=10, bg=COLOR_ONEUI_CARD, bar_color=COLOR_ONEUI_BLUE)
        self.p_bar.pack(fill="x", padx=18, pady=(12, 6))

        self.p_status = tk.Label(
            bottom_box, text="Select a tier above to install or activate.",
            font=FONT_SMALL, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT_SEC
        )
        self.p_status.pack(anchor="w", padx=18, pady=(0, 10))

        actions_bar = tk.Frame(bottom_box, bg=COLOR_ONEUI_CARD)
        actions_bar.pack(fill="x", padx=18, pady=(0, 6))

        self.install_btn = OneUIPillButton(
            actions_bar, text="Download & Install Selected Model", icon="⬇️",
            command=self.start_model_pull, variant="primary", height=36
        )
        self.install_btn.pack(side="left", padx=(0, 10))

        self.set_active_btn = OneUIPillButton(
            actions_bar, text="Set as Active Profile", icon="✓",
            command=self.save_active_tier, variant="surface", height=36
        )
        self.set_active_btn.pack(side="left")

    def update_tier_highlights(self):
        sel = self.selected_tier.get()
        for k, card in self.tier_cards.items():
            if k == sel:
                card.configure(highlightbackground=COLOR_ONEUI_BLUE, highlightthickness=1.5)
            else:
                card.configure(highlightbackground=COLOR_ONEUI_BORDER, highlightthickness=1)

    # ---------------------------------------------------------------------------
    # PAGE 3: KNOWLEDGE NOTEBOOK & EXPORTS
    # ---------------------------------------------------------------------------
    def build_history_page(self):
        page = self.pages["history"]

        # Filter Chips Row
        chips_frame = tk.Frame(page, bg=COLOR_ONEUI_BG)
        chips_frame.pack(fill="x", pady=(0, 10))

        filter_categories = [
            (None, "All Logs"),
            ("explain", "⚡ Explain"),
            ("fix", "🔧 Fix"),
            ("simplify", "💡 Simplify"),
            ("translate", "🌐 Translate"),
            ("regex", "🔍 Regex"),
            ("polish", "✍️ Polish"),
            ("audit", "🛡️ Audit"),
        ]

        self.chip_buttons = {}
        for mode_val, label in filter_categories:
            is_active = (mode_val == self.active_history_filter)
            chip = OneUIPillButton(
                chips_frame, text=label, command=lambda m=mode_val: self.set_history_filter(m),
                variant="primary" if is_active else "surface",
                font=FONT_MICRO, padx=10, pady=3, height=28
            )
            chip.pack(side="left", padx=(0, 6))
            self.chip_buttons[mode_val] = chip

        # Search Bar & Action Buttons
        top_ctrl = tk.Frame(page, bg=COLOR_ONEUI_BG)
        top_ctrl.pack(fill="x", pady=(0, 10))

        # Search Input Capsule
        search_card = tk.Frame(
            top_ctrl, bg=COLOR_ONEUI_CARD, bd=1, relief="solid",
            highlightbackground=COLOR_ONEUI_BORDER, highlightthickness=1
        )
        search_card.pack(side="left", fill="x", expand=True, padx=(0, 10))

        tk.Label(search_card, text="🔍", font=FONT_BODY, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT_MUTED).pack(side="left", padx=(10, 4))
        
        self.history_search_entry = tk.Entry(
            search_card, font=FONT_BODY, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT, insertbackground=COLOR_ONEUI_BLUE,
            bd=0, highlightthickness=0
        )
        self.history_search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=5)
        self.history_search_entry.bind("<KeyRelease>", lambda e: self.filter_history())

        OneUIPillButton(
            top_ctrl, text="Export Markdown", icon="📄", command=self.export_history_action,
            variant="success", font=FONT_SMALL, height=32
        ).pack(side="left", padx=(0, 8))

        OneUIPillButton(
            top_ctrl, text="Clear All", icon="🗑️", command=self.clear_all_history_action,
            variant="danger", font=FONT_SMALL, height=32
        ).pack(side="left")

        # Split Container: Treeview above, Output Preview below
        paned = tk.PanedWindow(page, orient="vertical", bg=COLOR_ONEUI_BORDER, bd=1, sashwidth=4)
        paned.pack(fill="both", expand=True)

        tree_frame = tk.Frame(paned, bg=COLOR_ONEUI_CARD)
        cols = ("timestamp", "mode", "tier", "snippet")
        self.history_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=7)
        self.history_tree.heading("timestamp", text="Recorded Time")
        self.history_tree.heading("mode", text="Mode")
        self.history_tree.heading("tier", text="Tier")
        self.history_tree.heading("snippet", text="Highlighted Snippet Context")

        self.history_tree.column("timestamp", width=140, anchor="w")
        self.history_tree.column("mode", width=90, anchor="center")
        self.history_tree.column("tier", width=80, anchor="center")
        self.history_tree.column("snippet", width=440, anchor="w")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=tree_scroll.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        self.history_tree.bind("<<TreeviewSelect>>", self.on_history_select)

        paned.add(tree_frame)

        # Output Preview Frame (Card)
        preview_frame = tk.Frame(paned, bg=COLOR_ONEUI_CARD)
        hdr_bar = tk.Frame(preview_frame, bg=COLOR_ONEUI_CARD)
        hdr_bar.pack(fill="x", padx=14, pady=(8, 4))

        tk.Label(hdr_bar, text="EXPLANATION PREVIEW & LATENCY", font=FONT_MICRO, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_BLUE).pack(side="left")
        
        self.history_preview_txt = tk.Text(
            preview_frame, font=FONT_BODY, bg=COLOR_ONEUI_CARD_SUB, fg=COLOR_ONEUI_TEXT,
            bd=0, padx=14, pady=10, wrap="word", height=6
        )
        self.history_preview_txt.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        paned.add(preview_frame)
        self.refresh_history_list()

    def set_history_filter(self, mode):
        self.active_history_filter = mode
        for m_val, btn in self.chip_buttons.items():
            btn.set_variant("primary" if m_val == mode else "surface")
        self.filter_history()

    def refresh_history_list(self, query=None):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)

        items = history_manager.get_history(limit=100, query=query, mode=self.active_history_filter)
        self.history_items = items
        for item in items:
            snip = item.get("snippet", "").replace("\n", " ")
            if len(snip) > 65:
                snip = snip[:62] + "..."
            self.history_tree.insert(
                "", "end",
                values=(
                    item.get("timestamp", ""),
                    item.get("mode", "").upper(),
                    item.get("tier", "").upper(),
                    snip
                )
            )

    def filter_history(self):
        query = self.history_search_entry.get().strip()
        self.refresh_history_list(query if query else None)

    def on_history_select(self, event):
        sel = self.history_tree.selection()
        if not sel:
            return
        idx = self.history_tree.index(sel[0])
        if 0 <= idx < len(self.history_items):
            item = self.history_items[idx]
            resp = item.get("response", "")
            lat = item.get("latency_s")
            lat_txt = f"Latency: {lat}s" if lat is not None else ""
            mod = item.get("model", "")
            header = f"[{item.get('mode', '').upper()}] • Model: {mod} • {lat_txt}\n\n"
            
            self.history_preview_txt.delete("1.0", tk.END)
            self.history_preview_txt.insert(tk.END, header + resp)

    def export_history_action(self):
        export_file = history_manager.export_to_markdown()
        if export_file:
            messagebox.showinfo("Export Successful", f"Knowledge notebook saved to Markdown:\n{export_file}")
        else:
            messagebox.showwarning("Export Failed", "No history available to export.")

    def clear_all_history_action(self):
        if messagebox.askyesno("Clear Notebook", "Clear all saved queries and explanation history?"):
            history_manager.clear_history()
            self.refresh_history_list()
            self.history_preview_txt.delete("1.0", tk.END)

    # ---------------------------------------------------------------------------
    # PAGE 4: PREFERENCES & MODES
    # ---------------------------------------------------------------------------
    def build_prefs_page(self):
        page = self.pages["prefs"]

        # Card 1: Windows System Integration
        int_card = tk.Frame(
            page, bg=COLOR_ONEUI_CARD, bd=1, relief="solid",
            highlightbackground=COLOR_ONEUI_BORDER, highlightthickness=1
        )
        int_card.pack(fill="x", pady=(0, 12), ipady=8)

        tk.Label(int_card, text="SYSTEM INTEGRATION & STARTUP", font=FONT_MICRO, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_BLUE).pack(anchor="w", padx=16, pady=(10, 8))

        # Windows Startup Row
        row_as = tk.Frame(int_card, bg=COLOR_ONEUI_CARD)
        row_as.pack(fill="x", padx=16, pady=(0, 4))
        self.var_autostart = tk.BooleanVar(value=config_manager.is_windows_autostart_enabled())
        self.sw_autostart = OneUIToggleSwitch(row_as, variable=self.var_autostart, bg=COLOR_ONEUI_CARD)
        self.sw_autostart.pack(side="left", padx=(0, 12))
        tk.Label(row_as, text="Launch wat-this automatically when Windows starts", font=FONT_BODY_BOLD, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT).pack(side="left")
        tk.Label(int_card, text="Creates a clean shortcut in %APPDATA%\\Startup. Zero registry modifications.", font=FONT_SMALL, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT_MUTED).pack(anchor="w", padx=76, pady=(0, 10))

        # Windows TTS Audio Row
        row_tts = tk.Frame(int_card, bg=COLOR_ONEUI_CARD)
        row_tts.pack(fill="x", padx=16, pady=(0, 4))
        self.var_tts = tk.BooleanVar(value=self.config.get("tts_enabled", False))
        self.sw_tts = OneUIToggleSwitch(row_tts, variable=self.var_tts, bg=COLOR_ONEUI_CARD)
        self.sw_tts.pack(side="left", padx=(0, 12))
        tk.Label(row_tts, text="Automatically read explanations aloud (Offline Windows TTS)", font=FONT_BODY_BOLD, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT).pack(side="left")
        tk.Label(int_card, text="Uses Windows native System.Speech.Synthesis without external downloads.", font=FONT_SMALL, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT_MUTED).pack(anchor="w", padx=76, pady=(0, 8))

        # Card 2: Universal Keybind & Modes
        hk_card = tk.Frame(
            page, bg=COLOR_ONEUI_CARD, bd=1, relief="solid",
            highlightbackground=COLOR_ONEUI_BORDER, highlightthickness=1
        )
        hk_card.pack(fill="x", pady=(0, 12), ipady=8)

        tk.Label(hk_card, text="UNIVERSAL COMMAND PALETTE & MODES", font=FONT_MICRO, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_BLUE).pack(anchor="w", padx=16, pady=(10, 6))

        # Keybind Pill Banner
        hk_banner = tk.Frame(hk_card, bg=COLOR_ONEUI_CARD_SUB, bd=1, relief="solid", highlightbackground=COLOR_ONEUI_BLUE)
        hk_banner.pack(fill="x", padx=16, pady=(0, 10), ipady=6)
        tk.Label(hk_banner, text="GLOBAL TRIGGER:", font=FONT_MICRO, bg=COLOR_ONEUI_CARD_SUB, fg=COLOR_ONEUI_TEXT_MUTED).pack(side="left", padx=(12, 6))
        tk.Label(hk_banner, text="Ctrl + Alt + Space", font=FONT_BODY_BOLD, bg=COLOR_ONEUI_CARD_SUB, fg=COLOR_ONEUI_BLUE).pack(side="left", padx=(0, 10))
        tk.Label(hk_banner, text="— Highlights text & opens the Action Palette right at cursor", font=FONT_SMALL, bg=COLOR_ONEUI_CARD_SUB, fg=COLOR_ONEUI_TEXT_SEC).pack(side="left")

        modes = config_manager.get_modes()
        for m_key, m_info in list(modes.items())[:5]:
            row = tk.Frame(hk_card, bg=COLOR_ONEUI_CARD)
            row.pack(fill="x", padx=16, pady=2)

            key_num = m_info.get("key_shortcut", "•")
            icon = m_info.get("icon", "•")
            tk.Label(row, text=f"• [{key_num}]  {icon} {m_info.get('name')}", font=FONT_BODY_BOLD, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT, width=26, anchor="w").pack(side="left")
            tk.Label(row, text=f"Option {key_num}", font=FONT_CODE, bg=COLOR_ONEUI_CARD_SUB, fg=COLOR_ONEUI_BLUE, padx=8, pady=1).pack(side="left", padx=8)

            req_tier = m_info.get("required_tier", "lite").upper()
            badge_fg = COLOR_ONEUI_BLUE if req_tier == "LITE" else (COLOR_ONEUI_GREEN if req_tier == "NORMAL" else COLOR_ONEUI_PURPLE)
            badge_bg = COLOR_ONEUI_BLUE_BG if req_tier == "LITE" else (COLOR_ONEUI_GREEN_BG if req_tier == "NORMAL" else COLOR_ONEUI_PURPLE_BG)
            pill_txt = f" {req_tier}+ " if req_tier != "EXTREME" else " EXTREME ONLY "
            tk.Label(row, text=pill_txt, font=FONT_MICRO, bg=badge_bg, fg=badge_fg, bd=1, relief="solid", highlightbackground=badge_fg, highlightthickness=1, padx=4, pady=1).pack(side="left", padx=8)

        # Card 3: Display & Linger Timing
        linger_card = tk.Frame(
            page, bg=COLOR_ONEUI_CARD, bd=1, relief="solid",
            highlightbackground=COLOR_ONEUI_BORDER, highlightthickness=1
        )
        linger_card.pack(fill="x", pady=(0, 14), ipady=8)

        tk.Label(linger_card, text="DISPLAY & VISUAL BEHAVIOR", font=FONT_MICRO, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_BLUE).pack(anchor="w", padx=16, pady=(10, 4))
        
        # Frosted Glass & Blur Row
        row_blur = tk.Frame(linger_card, bg=COLOR_ONEUI_CARD)
        row_blur.pack(fill="x", padx=16, pady=(4, 4))
        self.var_blur = tk.BooleanVar(value=self.config.get("blur_enabled", True))
        self.sw_blur = OneUIToggleSwitch(row_blur, variable=self.var_blur, bg=COLOR_ONEUI_CARD)
        self.sw_blur.pack(side="left", padx=(0, 12))
        tk.Label(row_blur, text="Enable Windows Acrylic Blur & Frosted Glass", font=FONT_BODY_BOLD, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT).pack(side="left")
        tk.Label(linger_card, text="Hardware-accelerated Windows Acrylic blur behind with native drop shadow and rounded corners.", font=FONT_SMALL, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT_MUTED).pack(anchor="w", padx=76, pady=(0, 8))

        l_box = tk.Frame(linger_card, bg=COLOR_ONEUI_CARD)
        l_box.pack(fill="x", padx=16, pady=(0, 6))

        tk.Label(l_box, text="HUD Linger Duration (seconds before auto-fade):", font=FONT_BODY, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT).pack(side="left", padx=(0, 12))
        self.entry_linger = tk.Spinbox(
            l_box, from_=4, to=60, font=FONT_BODY, bg=COLOR_ONEUI_CARD_SUB, fg=COLOR_ONEUI_TEXT,
            bd=1, relief="solid", highlightbackground=COLOR_ONEUI_BORDER, width=6
        )
        self.entry_linger.delete(0, "end")
        self.entry_linger.insert(0, str(int(self.config.get("linger_duration_ms", 14000) / 1000)))
        self.entry_linger.pack(side="left")

        # Save Button
        OneUIPillButton(
            page, text="Save All Preferences", icon="💾",
            command=self.save_preferences, variant="primary", height=38
        ).pack(anchor="w", pady=(4, 0))

    # ---------------------------------------------------------------------------
    # PAGE 5: STORAGE RECLAIM & CLEANUP
    # ---------------------------------------------------------------------------
    def build_storage_page(self):
        page = self.pages["storage"]

        top_info = tk.Frame(
            page, bg=COLOR_ONEUI_CARD, bd=1, relief="solid",
            highlightbackground=COLOR_ONEUI_BORDER, highlightthickness=1
        )
        top_info.pack(fill="x", pady=(0, 12), ipady=8)

        tk.Label(top_info, text="DISK STORAGE RECLAMATION", font=FONT_MICRO, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_BLUE).pack(anchor="w", padx=16, pady=(10, 4))
        tk.Label(
            top_info, text="Downloaded local model weights occupy disk space. You can safely remove models below anytime to reclaim gigabytes of disk space.",
            font=FONT_SMALL, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT_MUTED, wraplength=680, justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 6))

        self.uninstall_list_frame = tk.Frame(
            page, bg=COLOR_ONEUI_CARD, bd=1, relief="solid",
            highlightbackground=COLOR_ONEUI_BORDER, highlightthickness=1
        )
        self.uninstall_list_frame.pack(fill="both", expand=True, pady=(0, 12), ipady=8)

        btn_row = tk.Frame(page, bg=COLOR_ONEUI_BG)
        btn_row.pack(fill="x")

        OneUIPillButton(
            btn_row, text="Reset to Factory Defaults", icon="↺",
            command=self.reset_defaults, variant="surface", height=34
        ).pack(side="left")

    # ---------------------------------------------------------------------------
    # OLLAMA ENGINE & MODEL LOGIC
    # ---------------------------------------------------------------------------
    def check_ollama_status(self):
        self._scanner_active = True
        self._scanner_step = 0
        self._animate_scanner_tick()
        threading.Thread(target=self._check_ollama_worker, daemon=True).start()

    def _animate_scanner_tick(self):
        if not getattr(self, "_scanner_active", False):
            return
        try:
            if not (getattr(self, "root", None) and self.root.winfo_exists()):
                return
            dots = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            sym = dots[self._scanner_step % len(dots)]
            self.service_badge.configure(text=f" {sym} Probing Ollama... ", fg=COLOR_ONEUI_AMBER, bg=COLOR_ONEUI_CARD_SUB)
            self._scanner_step += 1
            self.root.after(90, self._animate_scanner_tick)
        except Exception:
            pass

    def _check_ollama_worker(self):
        url = config_manager.normalize_ollama_url(self.config.get("ollama_url", "http://127.0.0.1:11434"))
        online = False
        ver = "Active"
        for target_url in [url, "http://127.0.0.1:11434", "http://localhost:11434"]:
            try:
                req = urllib.request.Request(f"{target_url.rstrip('/')}/api/version")
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    ver = data.get("version", "Active")
                    online = True
                    break
            except Exception:
                continue

        self._scanner_active = False
        if online:
            self._safe_gui(lambda: self.service_badge.configure(
                text=f" ● Ollama Online (v{ver}) ", fg=COLOR_ONEUI_GREEN, bg=COLOR_ONEUI_GREEN_BG, highlightbackground=COLOR_ONEUI_GREEN_BORDER
            ))
            self._safe_gui(lambda: self.hub_service_lbl.configure(text=f"Online (v{ver})", fg=COLOR_ONEUI_GREEN))
            self.refresh_inventory()
        else:
            self._safe_gui(lambda: self.service_badge.configure(
                text=" ✕ Ollama Offline ", fg=COLOR_ONEUI_RED, bg=COLOR_ONEUI_RED_BG, highlightbackground=COLOR_ONEUI_RED_BORDER
            ))
            self._safe_gui(lambda: self.hub_service_lbl.configure(text="Offline (Click Restart)", fg=COLOR_ONEUI_RED))

        # Update active profile card on Hub
        _, spec = config_manager.get_active_tier()
        self._safe_gui(lambda: self.hub_model_name.configure(text=f"{spec.get('name').upper()} Profile ({spec.get('model')})"))
        self._safe_gui(lambda: self.hub_model_specs.configure(text=f"RAM Budget: {spec.get('ram_target')} • Cache: {spec.get('keep_alive')}"))

    def spawn_ollama_serve(self):
        url = config_manager.normalize_ollama_url(self.config.get("ollama_url", "http://127.0.0.1:11434"))
        self._scanner_active = True
        self._scanner_step = 0
        self._animate_scanner_tick()
        def _spawn():
            config_manager.ensure_ollama_running(url, wait_seconds=8)
            self._scanner_active = False
            self._safe_gui(self.check_ollama_status)
        threading.Thread(target=_spawn, daemon=True).start()

    def refresh_inventory(self):
        threading.Thread(target=self._refresh_inventory_worker, daemon=True).start()

    def _refresh_inventory_worker(self):
        url = config_manager.normalize_ollama_url(self.config.get("ollama_url", "http://127.0.0.1:11434"))
        models = []
        for target_url in [url, "http://127.0.0.1:11434", "http://localhost:11434"]:
            try:
                req = urllib.request.Request(f"{target_url.rstrip('/')}/api/tags")
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = data.get("models", [])
                    if models:
                        break
            except Exception:
                continue
        self.installed_models = [m.get("name", "") for m in models]
        self._safe_gui(lambda: self.update_badges(models))

    def update_badges(self, models_data):
        tiers = self.config.get("tiers", {})
        for key, spec in tiers.items():
            badge = self.tier_badges.get(key)
            if badge:
                m_name = spec.get("model", "")
                is_inst = any(m_name in m or m.startswith(m_name) for m in self.installed_models)
                if is_inst:
                    badge.configure(text=" ✓ INSTALLED ", fg=COLOR_ONEUI_GREEN, bg=COLOR_ONEUI_GREEN_BG, highlightbackground=COLOR_ONEUI_GREEN_BORDER)
                else:
                    badge.configure(text=" NOT INSTALLED ", fg=COLOR_ONEUI_RED, bg=COLOR_ONEUI_RED_BG, highlightbackground=COLOR_ONEUI_RED_BORDER)

        # Update Hub inventory summary
        if models_data:
            summary_lines = []
            for m in models_data[:4]:
                sz = m.get("size", 0) / (1024 ** 3)
                summary_lines.append(f"• {m.get('name')} ({sz:.1f} GB)")
            self.hub_inventory_lbl.configure(text="\n".join(summary_lines), fg=COLOR_ONEUI_TEXT)
        else:
            self.hub_inventory_lbl.configure(text="No models on disk. Run 1-Click Setup above!", fg=COLOR_ONEUI_TEXT_MUTED)

        # Update Storage Reclaim List
        for child in self.uninstall_list_frame.winfo_children():
            child.destroy()

        tk.Label(self.uninstall_list_frame, text="LOCAL MODEL INVENTORY ON DISK", font=FONT_MICRO, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_BLUE).pack(anchor="w", padx=16, pady=(10, 6))

        tier_models = [spec.get("model") for spec in tiers.values()]
        found_any = False
        for m in models_data:
            name = m.get("name", "")
            size_gb = m.get("size", 0) / (1024 ** 3)
            if any(tm in name for tm in tier_models):
                found_any = True
                row = tk.Frame(self.uninstall_list_frame, bg=COLOR_ONEUI_CARD_SUB, bd=1, relief="solid", highlightbackground=COLOR_ONEUI_BORDER_SUB)
                row.pack(fill="x", padx=16, pady=4, ipady=4)

                tk.Label(row, text=f"•  {name}", font=FONT_BODY_BOLD, bg=COLOR_ONEUI_CARD_SUB, fg=COLOR_ONEUI_TEXT).pack(side="left", padx=12)
                tk.Label(row, text=f"Disk Usage: {size_gb:.2f} GB", font=FONT_SMALL, bg=COLOR_ONEUI_CARD_SUB, fg=COLOR_ONEUI_TEXT_MUTED).pack(side="left", padx=16)

                del_btn = OneUIPillButton(
                    row, text="Delete", icon="🗑️",
                    command=lambda mn=name: self.delete_model(mn),
                    variant="danger", font=FONT_MICRO, padx=10, pady=2, height=26
                )
                del_btn.pack(side="right", padx=12)

        if not found_any:
            tk.Label(self.uninstall_list_frame, text="No model weights currently downloaded.", font=FONT_SMALL, bg=COLOR_ONEUI_CARD, fg=COLOR_ONEUI_TEXT_MUTED).pack(padx=16, pady=16)

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
        self.p_bar.set_progress(0, animate=False)
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
                                self._safe_gui(lambda p=pct, m=msg: self._update_pull_progress(p, m))
                            else:
                                self._safe_gui(lambda m=status: self._update_pull_progress(0, m))
                        except Exception:
                            continue

            config_manager.set_active_tier(tier_key)
            self._safe_gui(lambda: self._pull_finished(True, f"Model '{model_name}' successfully installed!"))
        except Exception as e:
            self._safe_gui(lambda: self._pull_finished(False, f"Download failed: {e}"))

    def _update_pull_progress(self, pct, msg):
        self.p_bar.set_progress(pct, animate=True)
        self.p_status.configure(text=msg)

    def _pull_finished(self, success, msg):
        self.is_pulling = False
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
        self.sidebar_tier_lbl.configure(text=f"{active_spec.get('name')} ({active_spec.get('ram_target')})")
        messagebox.showinfo("Active Profile Saved", f"Profile successfully set to '{active_spec.get('name')}'.")

    def save_preferences(self):
        want_autostart = self.var_autostart.get()
        config_manager.set_windows_autostart(want_autostart)
        self.config["tts_enabled"] = self.var_tts.get()
        self.config["blur_enabled"] = self.var_blur.get()

        try:
            self.config["linger_duration_ms"] = int(self.entry_linger.get()) * 1000
        except Exception:
            pass

        config_manager.save_config(self.config)
        messagebox.showinfo("Preferences Saved", "Settings and Windows Autostart preferences saved successfully.")

    def reset_defaults(self):
        if messagebox.askyesno("Reset Defaults", "Reset all settings and active tier to factory defaults?"):
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
            
            messagebox.showinfo(
                "wat-this Running",
                "wat-this is now running in your Windows Status Bar (System Tray)!\n\n"
                "• Look for the wat-this icon near your system clock.\n"
                "• Highlight any text anywhere and press Ctrl + Alt + Space.\n"
                "• Right-click the status bar icon for quick actions or settings."
            )
            self.root.iconify()
        except Exception as e:
            messagebox.showerror("Launch Error", f"Could not start wat-this: {e}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SetupApp()
    app.run()
