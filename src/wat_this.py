"""
wat-this: Ambient Desktop Intelligence Copilot.
Zero-DLL, signed Tkinter desktop application with:
1. Windows Status Bar (System Tray) icon near clock (zero taskbar clutter)
2. Floating Cursor Overlay HUD (Emerges at mouse position on hotkey press)
3. Strict tier-level gating (Lite, Normal, Extreme)
4. Interactive follow-up chat, audio TTS, and local knowledge logging.
"""
import sys
import os
import time
import json
import ctypes
import threading
import subprocess
import urllib.request
import urllib.parse
import pyperclip
import keyboard
import queue
import tkinter as tk
from PIL import Image
import pystray
from pystray import MenuItem as item

# Per-Monitor v2 DPI Awareness (Windows 10 1703+) for crisp rendering and exact pixel cursor tracking
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

def get_dpi_scale():
    """Returns the current Windows monitor DPI scaling factor (e.g. 1.0 for 100%, 1.5 for 150%, 2.0 for 200%)."""
    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()
        if dpi and dpi > 0:
            return max(1.0, dpi / 96.0)
    except Exception:
        pass
    return 1.0

# Ensure Windows console output handles Unicode safely without crash
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure src folder is always in sys.path
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Set explicit Windows AppUserModelID
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("watthis.ambientcopilot.app.1")
except Exception:
    pass

import config_manager
import search_helper
import history_manager
import tts_helper
import screen_context
from annotation_overlay import AnnotationOverlay

import one_ui

# ---------------------------------------------------------------------------
# DESIGN SYSTEM TOKENS (Modern Rounded Dark Theme)
# ---------------------------------------------------------------------------
COLOR_BG_DARK      = one_ui.COLOR_ONEUI_BG        # Canvas background (#121316)
COLOR_CONTAINER    = one_ui.COLOR_ONEUI_CARD      # Squircle Card (#1F2228)
COLOR_SURFACE_ELEV = one_ui.COLOR_ONEUI_CARD_ELEV # Elevated / Hover card (#282C35)
COLOR_BORDER       = one_ui.COLOR_ONEUI_BORDER    # Soft structural border (#2F3542)
COLOR_TEXT_MAIN    = one_ui.COLOR_ONEUI_TEXT      # Crisp white (#FFFFFF)
COLOR_TEXT_SEC     = one_ui.COLOR_ONEUI_TEXT_SEC  # Neutral secondary (#A0A8B5)
COLOR_TEXT_DIM     = one_ui.COLOR_ONEUI_TEXT_DIM  # Muted captions (#5A6170)
COLOR_BLUE         = one_ui.COLOR_ONEUI_BLUE      # Vivid Blue (#2C75FF)
COLOR_BLUE_BG      = one_ui.COLOR_ONEUI_BLUE_BG   # Blue pill tint (#1A2744)
COLOR_GREEN        = one_ui.COLOR_ONEUI_GREEN     # Emerald (#22C55E)
COLOR_GREEN_BG     = one_ui.COLOR_ONEUI_GREEN_BG  # Emerald pill tint (#132D1E)
COLOR_AMBER        = one_ui.COLOR_ONEUI_AMBER     # Amber (#FF9F0A)
COLOR_AMBER_BG     = one_ui.COLOR_ONEUI_AMBER_BG  # Amber pill tint (#332311)
COLOR_RED          = one_ui.COLOR_ONEUI_RED       # Coral red (#FA5252)
COLOR_RED_BG       = one_ui.COLOR_ONEUI_RED_BG    # Red pill tint (#331618)
COLOR_RED_BORDER   = one_ui.COLOR_ONEUI_RED_BORDER
COLOR_AMBER_BORDER = one_ui.COLOR_ONEUI_AMBER_BORDER
COLOR_PURPLE       = one_ui.COLOR_ONEUI_PURPLE    # Violet (#8C52FF)
COLOR_PURPLE_BG    = one_ui.COLOR_ONEUI_PURPLE_BG # Violet pill tint (#251740)

MODE_COLORS = one_ui.ONEUI_MODE_COLORS
MODE_BG_COLORS = one_ui.ONEUI_MODE_BG_COLORS

MODE_ICONS = {
    "explain": "⚡",
    "simplify": "📝",
    "translate": "🌐",
    "regex": "⚙️",
    "fix": "🔍",
    "polish": "✨",
    "docstring": "📜",
    "audit": "🛡️",
    "unittest": "🧪"
}

ACTION_SUMMARIES = {
    "explain": {
        "summary": "Deconstructs complex concepts and logic into plain English with intuitive everyday analogies.",
        "badge": "LITE+",
        "tags": "⚡ Fast • Everyday Analogy • Web Enrich",
        "tagline": "Instant plain English analogy"
    },
    "fix": {
        "summary": "Deep bug analysis to detect syntax flaws, race conditions, and logic errors. Provides a 1-click copyable patch.",
        "badge": "LITE+",
        "tags": "🔧 Instant Patch • Bug Detection • Safe",
        "tagline": "Detect bugs & 1-click patch"
    },
    "simplify": {
        "summary": "Rewrites dense academic, legal, or technical jargon so anyone can understand it like a 10-year-old.",
        "badge": "LITE+",
        "tags": "💡 ELI5 • Beginner Friendly • High Clarity",
        "tagline": "Rewrite for a 10-year-old"
    },
    "translate": {
        "summary": "Contextual translation of foreign language text into natural, idiom-aware plain English.",
        "badge": "LITE+",
        "tags": "🌐 Translation • Multi-language • Natural",
        "tagline": "Contextual English translation"
    },
    "regex": {
        "summary": "Deconstructs complex regular expressions, regex groups, and terminal shell commands component-by-component.",
        "badge": "LITE+",
        "tags": "🔍 Regex Parser • CLI Explainer • Flags",
        "tagline": "Regex & terminal CLI breakdown"
    },
    "polish": {
        "summary": "Refines tone, corrects grammatical and punctuation errors, and transforms rough notes into crisp, executive prose.",
        "badge": "NORMAL+",
        "tags": "✍️ Grammar Polish • Tone Refinement",
        "tagline": "Crisp grammar & tone refinement"
    },
    "docstring": {
        "summary": "Generates professional, standardized function docstrings, JSDoc, and type annotations following official conventions.",
        "badge": "EXTREME",
        "tags": "📝 Type Hints • Standard Docstrings • Clean",
        "tagline": "Standardized docstrings & types"
    },
    "audit": {
        "summary": "Rigorous security and performance audit checking for OWASP vulnerabilities, leaks, and Big-O computational complexity.",
        "badge": "EXTREME",
        "tags": "🛡️ OWASP Audit • Memory Safety • Complexity",
        "tagline": "OWASP security & Big-O audit"
    },
    "unittest": {
        "summary": "Synthesizes robust, production-grade test suites covering happy paths, edge boundaries, exceptions, and mocks.",
        "badge": "EXTREME",
        "tags": "🧪 Unit Tests • Edge Cases • Mocking",
        "tagline": "Production edge-case test suites"
    }
}

FONT_FAMILY  = "Segoe UI"
FONT_HERO    = (FONT_FAMILY, 13, "bold")
FONT_TITLE   = (FONT_FAMILY, 11, "bold")
FONT_SECTION = (FONT_FAMILY, 11, "bold")
FONT_BODY       = (FONT_FAMILY, 10)
FONT_BOLD       = (FONT_FAMILY, 10, "bold")
FONT_BODY_BOLD  = (FONT_FAMILY, 10, "bold")
FONT_SMALL   = (FONT_FAMILY, 9)
FONT_MICRO   = (FONT_FAMILY, 8, "bold")
FONT_SUB     = (FONT_FAMILY, 8)
FONT_CODE    = ("Consolas", 9)

# ---------------------------------------------------------------------------
# WINDOWS DWM & ACRYLIC COMPOSITION BLUR (Hardware-accelerated Frosted Glass)
# ---------------------------------------------------------------------------
class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_int),
        ("AnimationId", ctypes.c_int),
    ]

class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]

class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.c_ulong)
    ]

def get_monitor_work_area(x, y):
    """Returns (left, top, right, bottom) usable work area of the monitor containing (x, y), excluding taskbar."""
    try:
        user32 = ctypes.windll.user32
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT(int(x), int(y))
        MONITOR_DEFAULTTONEAREST = 2
        h_monitor = user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
        if h_monitor:
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(h_monitor, ctypes.byref(info)):
                return (info.rcWork.left, info.rcWork.top, info.rcWork.right, info.rcWork.bottom)
    except Exception:
        pass
    return (0, 0, 1920, 1040)

def apply_window_blur_and_shadow(hwnd, enable=True, gradient_color=0xAA121722):
    """
    Applies native Windows 11/10 Acrylic Blur Behind, Immersive Dark Mode,
    Round Corners, and hardware Drop Shadow to borderless HUD windows.
    Zero DLLs, 100% native Win32/DWM API.
    """
    try:
        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi

        # 1. Dark Mode & Rounded Corners via DwmSetWindowAttribute
        v_true = ctypes.c_int(1)
        v_round = ctypes.c_int(2)  # DWMWCP_ROUND (Smooth rounded corners)
        v_backdrop = ctypes.c_int(3 if enable else 1)  # DWMSBT_TRANSIENTWINDOW (Acrylic) or NONE
        v_border = ctypes.c_int(0x0033281E)

        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(v_true), ctypes.sizeof(v_true))
        # DWMWA_WINDOW_CORNER_PREFERENCE = 33
        dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(v_round), ctypes.sizeof(v_round))
        # DWMWA_BORDER_COLOR = 34
        dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(v_border), ctypes.sizeof(v_border))
        # DWMWA_SYSTEMBACKDROP_TYPE = 38
        dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(v_backdrop), ctypes.sizeof(v_backdrop))

        # 2. Hardware drop shadow via DwmExtendFrameIntoClientArea
        margins = MARGINS(1, 1, 1, 1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

        # 3. Acrylic Blur Behind via SetWindowCompositionAttribute (Windows 10/11)
        if hasattr(user32, "SetWindowCompositionAttribute"):
            accent = ACCENT_POLICY()
            if enable:
                accent.AccentState = 4  # ACCENT_ENABLE_ACRYLICBLURBEHIND
                accent.AccentFlags = 2  # DRAW_ALL_BORDERS
                accent.GradientColor = gradient_color  # AABBGGRR translucent dark slate
            else:
                accent.AccentState = 0  # ACCENT_DISABLED
                accent.AccentFlags = 0
                accent.GradientColor = 0

            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attribute = 19  # WCA_ACCENT_POLICY
            data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
            data.SizeOfData = ctypes.sizeof(accent)
            user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
    except Exception:
        pass

# Universal Win32 Hotkey Mapping (MOD_CONTROL=0x0002 | MOD_ALT=0x0001 | MOD_NOREPEAT=0x4000 = 0x4003)
# All actions are unified into a single command palette trigger: Ctrl + Alt + Space
WIN32_HOTKEYS = {
    101: ("menu", 0x4003, 0x20),  # Ctrl + Alt + Space
}

class WatThisApp:
    def __init__(self):
        self.config = config_manager.load_config()
        self.tier_key, self.tier_spec = config_manager.get_active_tier()

        # Thread-safe GUI event queue
        self.event_queue = queue.Queue()

        # State tracking
        self.stop_hotkeys = threading.Event()
        self.last_trigger_time = 0.0
        self.current_mode = "explain"
        self.hud_state = "picker"  # "picker" or "streamer"
        self.selected_action_idx = 0
        self.current_actions = []
        self.action_rows = []
        self.active_abort_event = None
        self.is_thinking = False
        self.is_streaming = False
        self.is_alive = True
        self.accumulated_text = ""
        self.current_snippet = ""
        self.conversation_history = []
        self.status_index = 0
        self.status_states = []
        self.linger_timer_id = None
        self.gui_queue_timer_id = None
        self.anim_timer_id = None
        self.anim_pos = 0
        self.anim_dir = 1
        self._fade_timer_id = None
        self._current_fade_alpha = 0.0
        self._fade_callback = None
        self._last_geom_time = 0.0
        self.active_hud_alpha = 0.92
        self.hud_visible = False
        self.chat_expanded = False
        self.start_time = None
        self.chat_turns = 0
        self.anchor_x = 400
        self.anchor_y = 300
        self.fixed_width = int(620 * get_dpi_scale())
        self.tray_icon = None
        self.hud_hwnd = None
        self.used_web_search = False
        self.screen_context = {}
        self.is_pinned = False
        self.last_mouse_activity_time = time.time()

        # Hidden root + Windows Status Bar (System Tray) Icon + Floating Cursor HUD
        self.init_app_environment()
        self.annotation_overlay = AnnotationOverlay(self.root)
        self.init_tray_icon()
        self.init_hud_overlay()
        self.process_gui_queue()
        self.register_all_hotkeys()
        self.start_win32_hotkey_listener()

        # Proactive Ollama engine check/warmup in background
        threading.Thread(target=self._ensure_engine_warmup, daemon=True).start()

        print(f"[STATUS BAR] wat-this Active in Windows Status Bar (System Tray). Tier: {self.tier_spec.get('name').upper()} ({self.tier_spec.get('ram_target')}).")
        print("Universal trigger: Press Ctrl+Alt+Space anytime to open Action Palette at cursor.")

    def _ensure_engine_warmup(self):
        """Checks if Ollama daemon is running, starting it silently in the background if offline."""
        try:
            ollama_url = config_manager.normalize_ollama_url(self.config.get("ollama_url", "http://127.0.0.1:11434"))
            if not config_manager.is_ollama_online(ollama_url):
                print("[STATUS BAR] Auto-starting Ollama engine in background...")
                config_manager.ensure_ollama_running(ollama_url, wait_seconds=6)
        except Exception as e:
            print(f"[WARN] Engine warmup probe: {e}")

    # ---------------------------------------------------------------------------
    # 1. APPLICATION ENVIRONMENT & WINDOWS STATUS BAR (SYSTEM TRAY)
    # ---------------------------------------------------------------------------
    def init_app_environment(self):
        self.root = tk.Tk()
        self.root.title("wat-this • Ambient Copilot")
        self.root.withdraw()

    def init_tray_icon(self):
        try:
            icon_path = config_manager.ICON_PATH
            if os.path.exists(icon_path):
                tray_img = Image.open(icon_path)
            else:
                tray_img = Image.new("RGB", (32, 32), color=(56, 139, 253))

            tier_name = self.tier_spec.get("name", "Normal")
            tier_ram = self.tier_spec.get("ram_target", "")

            menu = pystray.Menu(
                item("⚡  Action Palette (Ctrl+Alt+Space)", lambda *args: self.event_queue.put(("hotkey", None))),
                item("🔊  Listen (TTS Audio)", lambda *args: self.event_queue.put(("tts", None))),
                pystray.Menu.SEPARATOR,
                item(f"Active Profile: {tier_name} ({tier_ram})", None, enabled=False),
                item("⚙️  Setup & Settings", lambda *args: self.open_setup()),
                pystray.Menu.SEPARATOR,
                item("✕  Dismiss HUD (Esc)", lambda *args: self.event_queue.put(("hide_hud", None))),
                item("✕  Exit wat-this", lambda *args: self.quit_app())
            )

            self.tray_icon = pystray.Icon(
                "wat-this",
                tray_img,
                f"wat-this • Ambient Copilot ({tier_name})",
                menu
            )
            self.tray_icon.default_action = lambda *args: self.event_queue.put(("hotkey", None))
            self.tray_icon.run_detached()
            print(f"[STATUS BAR] wat-this icon active in Windows Status Bar (System Tray).")
        except Exception as e:
            print(f"[WARN] Tray icon initialization: {e}")

    def update_tray_tooltip(self):
        if getattr(self, "tray_icon", None):
            try:
                tier_name = self.tier_spec.get("name", "Normal")
                self.tray_icon.title = f"wat-this • Ambient Copilot ({tier_name})"
            except Exception:
                pass

    def open_setup(self):
        try:
            setup_script = os.path.join(config_manager.BASE_DIR, "setup.py")
            subprocess.Popen([sys.executable, setup_script], cwd=config_manager.BASE_DIR)
        except Exception as e:
            print(f"[ERROR] Could not open setup: {e}")

    def quit_app(self, *args):
        """Immediately terminates wat-this, removing status bar icon and releasing all resources."""
        print("[STATUS BAR] Exiting wat-this from status bar / user command...")
        self.is_alive = False
        if getattr(self, "active_abort_event", None):
            self.active_abort_event.set()
        tts_helper.stop_speech()
        self.stop_hotkeys.set()

        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        if getattr(self, "tray_icon", None):
            try:
                self.tray_icon.stop()
            except Exception:
                pass

        def _cleanup_tk():
            for tid in ("anim_timer_id", "linger_timer_id", "gui_queue_timer_id", "_fade_timer_id"):
                if getattr(self, tid, None):
                    try:
                        self.root.after_cancel(getattr(self, tid))
                    except Exception:
                        pass
            if getattr(self, "annotation_overlay", None):
                try:
                    self.annotation_overlay.destroy()
                except Exception:
                    pass
            try:
                self.root.quit()
            except Exception:
                pass
            try:
                self.root.destroy()
            except Exception:
                pass

        try:
            self.root.after(0, _cleanup_tk)
        except Exception:
            pass

        def _watchdog_exit():
            time.sleep(0.2)
            os._exit(0)

        threading.Thread(target=_watchdog_exit, daemon=True).start()
        if threading.current_thread() is threading.main_thread():
            _cleanup_tk()
            os._exit(0)

    def stop(self):
        """Clean programmatic stop alias for tests and maintenance."""
        self.quit_app()

    # ---------------------------------------------------------------------------
    # 2. FLOATING CURSOR OVERLAY HUD (Emerges at cursor position)
    # ---------------------------------------------------------------------------
    def init_hud_overlay(self):
        self.hud = tk.Toplevel(self.root)
        self.hud.title("wat-this HUD")
        self.hud.overrideredirect(True)
        self.hud.attributes("-topmost", True)
        self.hud.attributes("-alpha", 0.0)
        self.hud.configure(bg=COLOR_BG_DARK)
        self.hud.withdraw()

        # Apply Windows 11 Native Fluent Rounded Corners & Immersive Dark Mode to HUD
        try:
            self.hud.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.hud.winfo_id()) or self.hud.winfo_id()
            self.hud_hwnd = hwnd
            v_true = ctypes.c_int(1)
            v_round = ctypes.c_int(2)  # DWMWCP_ROUND (Smooth rounded window)
            v_border = ctypes.c_int(0x0033281E)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(v_true), ctypes.sizeof(v_true))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(v_round), ctypes.sizeof(v_round))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(v_border), ctypes.sizeof(v_border))
        except Exception:
            pass

        # Keyboard & Click dismiss handlers
        self.hud.bind("<Escape>", lambda e: self.hide_hud())
        self.hud.bind("<Key>", self._on_hud_key)

        # Mouse activity listeners (keeps popup open while hovering)
        self.hud.bind("<Motion>", self.on_hud_mouse_activity)
        self.hud.bind("<Enter>", self.on_hud_mouse_activity)
        self.hud.bind("<Leave>", self.on_hud_mouse_leave)

        # Main HUD Glass Container
        self.container = tk.Frame(
            self.hud, bg=COLOR_CONTAINER, bd=0, relief="flat",
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        self.container.pack(fill="both", expand=True, padx=0, pady=0)
        self.container.bind("<Motion>", self.on_hud_mouse_activity)
        self.container.bind("<Enter>", self.on_hud_mouse_activity)
        self.container.bind("<Leave>", self.on_hud_mouse_leave)

        # -----------------------------------------------------------------------
        # SHARED HEADER (Always visible, supports dragging)
        # -----------------------------------------------------------------------
        self.header_frame = tk.Frame(self.container, bg=COLOR_CONTAINER)
        self.header_frame.pack(fill="x", padx=20, pady=(14, 8))

        # Left Header: Brand mark + Tier pill
        left_hdr = tk.Frame(self.header_frame, bg=COLOR_CONTAINER)
        left_hdr.pack(side="left")

        self.title_lbl = tk.Label(
            left_hdr, text="●  wat-this", font=("Segoe UI", 9, "bold"),
            bg=COLOR_CONTAINER, fg="#FFFFFF"
        )
        self.title_lbl.pack(side="left", padx=(0, 12))

        tier_name = self.tier_spec.get("name", "NORMAL").upper()
        tier_ram = self.tier_spec.get("ram_target", "")
        self.tier_badge_lbl = tk.Label(
            left_hdr, text=f" {tier_name} • {tier_ram} ", font=FONT_MICRO,
            bg=one_ui.COLOR_SURFACE_SUB, fg=COLOR_TEXT_SEC, bd=0, relief="flat",
            highlightbackground=one_ui.COLOR_BORDER, highlightthickness=1, padx=8, pady=2
        )
        self.tier_badge_lbl.pack(side="left")

        # Right Header: Pin toggle button + Close button
        right_hdr = tk.Frame(self.header_frame, bg=COLOR_CONTAINER)
        right_hdr.pack(side="right")

        self.pin_btn = one_ui.OneUIPillButton(
            right_hdr, text="Pin", icon="📌", variant="surface",
            font=FONT_MICRO, padx=10, pady=2, height=26, bg=COLOR_CONTAINER,
            command=self.toggle_pin
        )
        self.pin_btn.pack(side="left", padx=(0, 8))

        self.dismiss_btn = one_ui.OneUIPillButton(
            right_hdr, text="", icon="✕", variant="surface",
            font=FONT_MICRO, padx=8, pady=2, height=26, bg=COLOR_CONTAINER,
            command=self.hide_hud
        )
        self.dismiss_btn.pack(side="right")

        # Draggable header bindings
        self._drag_start_x = 0
        self._drag_start_y = 0
        self.header_frame.bind("<Button-1>", self._on_drag_start)
        self.header_frame.bind("<B1-Motion>", self._on_drag_motion)
        self.title_lbl.bind("<Button-1>", self._on_drag_start)
        self.title_lbl.bind("<B1-Motion>", self._on_drag_motion)

        # -----------------------------------------------------------------------
        # VIEW 1: MINIMALIST ACTION PICKER (COMMAND PALETTE)
        # -----------------------------------------------------------------------
        self.picker_frame = tk.Frame(self.container, bg=COLOR_CONTAINER)

        # Snippet preview card
        self.picker_snippet_card = tk.Frame(
            self.picker_frame, bg=one_ui.COLOR_SURFACE_SUB, bd=0, relief="flat",
            highlightbackground=one_ui.COLOR_BORDER, highlightthickness=1
        )
        self.picker_snippet_card.pack(fill="x", padx=20, pady=(4, 8))

        self.picker_snippet_lbl = tk.Label(
            self.picker_snippet_card, text="", font=FONT_SMALL,
            bg=one_ui.COLOR_SURFACE_SUB, fg=COLOR_TEXT_SEC, justify="left", anchor="w"
        )
        self.picker_snippet_lbl.pack(fill="x", padx=14, pady=8)

        # Prompt entry (shown when no snippet is selected)
        self.picker_entry_frame = tk.Frame(self.picker_frame, bg=COLOR_CONTAINER)
        self.picker_entry = tk.Entry(
            self.picker_entry_frame, font=FONT_BODY,
            bg=one_ui.COLOR_SURFACE_SUB, fg=COLOR_TEXT_MAIN, insertbackground=COLOR_BLUE,
            bd=0, highlightbackground=one_ui.COLOR_BORDER, highlightthickness=1, relief="flat"
        )
        self.picker_entry.pack(fill="x", padx=20, pady=(0, 8), ipady=7)
        self.picker_entry.bind("<Return>", lambda e: self._on_picker_entry_submit())
        self.picker_entry.bind("<Escape>", lambda e: self.hide_hud())

        # Action rows container
        self.action_list_frame = tk.Frame(self.picker_frame, bg=COLOR_CONTAINER)
        self.action_list_frame.pack(fill="both", expand=True, padx=0, pady=(0, 6))

        # Dedicated Function Summary & Capabilities Preview Card
        self.action_preview_card = tk.Frame(
            self.picker_frame, bg=one_ui.COLOR_SURFACE_SUB, bd=0, relief="flat",
            highlightbackground=one_ui.COLOR_BORDER, highlightthickness=1
        )
        self.action_preview_card.pack(fill="x", padx=20, pady=(4, 8))
        self.action_preview_card.bind("<Configure>", self._on_action_preview_configure)

        preview_hdr = tk.Frame(self.action_preview_card, bg=one_ui.COLOR_SURFACE_SUB)
        preview_hdr.pack(fill="x", padx=14, pady=(8, 2))

        self.preview_title_lbl = tk.Label(
            preview_hdr, text="⚡ Explain & Teach", font=FONT_SECTION,
            bg=one_ui.COLOR_SURFACE_SUB, fg=COLOR_TEXT_MAIN
        )
        self.preview_title_lbl.pack(side="left")

        self.preview_tier_pill = tk.Label(
            preview_hdr, text=" LITE+ ", font=FONT_MICRO,
            bg=one_ui.COLOR_ACCENT_BG, fg=one_ui.COLOR_ACCENT, bd=0, relief="flat",
            highlightbackground=one_ui.COLOR_ACCENT_BG, highlightthickness=1, padx=8, pady=3
        )
        self.preview_tier_pill.pack(side="right")

        self.preview_desc_lbl = tk.Label(
            self.action_preview_card,
            text="Deconstructs complex concepts and logic into plain English with intuitive everyday analogies.",
            font=FONT_SMALL, bg=one_ui.COLOR_SURFACE_SUB, fg=COLOR_TEXT_SEC,
            justify="left", anchor="w"
        )
        self.preview_desc_lbl.pack(fill="x", padx=14, pady=(2, 4))

        self.preview_tags_lbl = tk.Label(
            self.action_preview_card,
            text="⚡ Fast • Everyday Analogy • Web Enrich",
            font=FONT_MICRO, bg=one_ui.COLOR_SURFACE_SUB, fg=one_ui.COLOR_ACCENT,
            anchor="w"
        )
        self.preview_tags_lbl.pack(fill="x", padx=14, pady=(0, 8))

        # Bottom Hint Bar
        self.picker_hint_lbl = tk.Label(
            self.picker_frame, text="1–9 to run  •  ↑↓ to navigate  •  Hover for info  •  Esc to close",
            font=FONT_MICRO, bg=COLOR_CONTAINER, fg=COLOR_TEXT_DIM, pady=4
        )
        self.picker_hint_lbl.pack(fill="x", padx=20, pady=(0, 10))

        # -----------------------------------------------------------------------
        # VIEW 2: STREAMING RESULT VIEW
        # -----------------------------------------------------------------------
        self.stream_frame = tk.Frame(self.container, bg=COLOR_CONTAINER)

        # Sub-header bar inside stream frame (Back button, Mode badge, Action buttons)
        self.stream_subhdr = tk.Frame(self.stream_frame, bg=COLOR_CONTAINER)
        self.stream_subhdr.pack(fill="x", padx=20, pady=(0, 10))

        # Left sub-header: Back button + Mode badge
        stream_left = tk.Frame(self.stream_subhdr, bg=COLOR_CONTAINER)
        stream_left.pack(side="left")

        self.back_btn = one_ui.OneUIPillButton(
            stream_left, text="Back", icon="←", variant="surface",
            font=FONT_MICRO, padx=10, pady=2, height=26, bg=COLOR_CONTAINER,
            command=self.show_action_picker
        )
        self.back_btn.pack(side="left", padx=(0, 8))

        self.stream_mode_badge = tk.Label(
            stream_left, text="⚡ EXPLAIN", font=FONT_MICRO,
            bg=COLOR_BLUE_BG, fg=COLOR_BLUE, bd=0, relief="flat",
            highlightbackground=COLOR_BLUE_BG, highlightthickness=1, padx=10, pady=3
        )
        self.stream_mode_badge.pack(side="left")

        # Right sub-header: Patch, Copy, Guide, Listen
        stream_right = tk.Frame(self.stream_subhdr, bg=COLOR_CONTAINER)
        stream_right.pack(side="right")

        # Patch Button (Fix mode)
        self.patch_btn = one_ui.OneUIPillButton(
            stream_right, text="Patch", icon="⚡", variant="amber",
            font=FONT_MICRO, padx=10, pady=2, height=26, bg=COLOR_CONTAINER,
            command=self.replace_selection_in_editor
        )

        # Copy Button
        self.copy_btn = one_ui.OneUIPillButton(
            stream_right, text="Copy", icon="📋", variant="surface",
            font=FONT_MICRO, padx=10, pady=2, height=26, bg=COLOR_CONTAINER,
            command=self.copy_to_clipboard
        )
        self.copy_btn.pack(side="left", padx=(0, 8))

        # Guide / On-Screen Annotations Button
        self.guide_btn = one_ui.OneUIPillButton(
            stream_right, text="Guide", icon="📍", variant="surface",
            font=FONT_MICRO, padx=10, pady=2, height=26, bg=COLOR_CONTAINER,
            command=self.toggle_annotation_guide
        )
        self.guide_btn.pack(side="left", padx=(0, 8))

        # TTS Listen Button
        self.tts_btn = one_ui.OneUIPillButton(
            stream_right, text="Listen", icon="🔊",
            variant="surface" if config_manager.is_tts_allowed(self.tier_key) else "ghost",
            font=FONT_MICRO, padx=10, pady=2, height=26, bg=COLOR_CONTAINER,
            command=self.toggle_speech
        )
        self.tts_btn.pack(side="left")

        # Activity & Progress Strip
        self.activity_canvas = tk.Canvas(
            self.stream_frame, height=2, bg=COLOR_CONTAINER, highlightthickness=0, bd=0
        )

        # Elevated Content Card
        self.content_card = tk.Frame(
            self.stream_frame, bg=COLOR_SURFACE_ELEV, bd=0, relief="flat",
            highlightbackground=one_ui.COLOR_BORDER, highlightthickness=1
        )
        self.content_card.pack(fill="both", expand=True, padx=20, pady=(2, 10))
        self.content_card.bind("<Motion>", self.on_hud_mouse_activity)
        self.content_card.bind("<Configure>", self._on_content_card_configure)

        # Status indicator: clean flat text, no heavy border box
        self.status_frame = tk.Frame(self.content_card, bg=COLOR_SURFACE_ELEV)
        self.status_pill = tk.Label(
            self.status_frame, text="⧗ Thinking...", font=FONT_SMALL,
            bg=COLOR_SURFACE_ELEV, fg=COLOR_TEXT_SEC, padx=18, pady=10, bd=0, relief="flat",
            anchor="w"
        )
        self.status_pill.pack(fill="x", anchor="w")


        # Content Text Area
        self.content_lbl = tk.Label(
            self.content_card, text="", font=FONT_BODY,
            bg=COLOR_SURFACE_ELEV, fg="#EDF2F7",
            justify="left", anchor="w"
        )
        self.content_lbl.pack(fill="both", expand=True, padx=18, pady=(8, 14))
        self.content_lbl.bind("<Motion>", self.on_hud_mouse_activity)

        # Metadata Footer Row
        self.meta_frame = tk.Frame(self.content_card, bg=COLOR_SURFACE_ELEV)
        self.meta_stats_lbl = tk.Label(
            self.meta_frame, text="", font=FONT_MICRO,
            bg=COLOR_SURFACE_ELEV, fg=COLOR_TEXT_DIM
        )
        self.meta_stats_lbl.pack(side="left", padx=18, pady=(0, 10))

        # Follow-Up Expand Frame
        self.follow_up_frame = tk.Frame(
            self.stream_frame, bg=one_ui.COLOR_SURFACE_SUB, bd=0, relief="flat",
            highlightbackground=one_ui.COLOR_BORDER, highlightthickness=1
        )
        self.follow_up_frame.pack(fill="x", padx=20, pady=(0, 12))

        self.expand_prompt_lbl = tk.Label(
            self.follow_up_frame, text="💬  Press Tab or click to ask follow-up...",
            font=FONT_SMALL, bg=one_ui.COLOR_SURFACE_SUB, fg=COLOR_TEXT_SEC, cursor="hand2", pady=9
        )
        self.expand_prompt_lbl.pack(fill="x")
        self.expand_prompt_lbl.bind("<Button-1>", lambda e: self.toggle_follow_up(True))

        # Input Box for Chat Follow-up
        self.input_box_frame = tk.Frame(self.follow_up_frame, bg=one_ui.COLOR_SURFACE_SUB)
        self.chat_entry = tk.Entry(
            self.input_box_frame, font=FONT_BODY,
            bg=COLOR_CONTAINER, fg=COLOR_TEXT_MAIN, insertbackground=COLOR_BLUE,
            bd=0, highlightbackground=one_ui.COLOR_BORDER, highlightthickness=1, relief="flat"
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(14, 8), pady=8, ipady=6)
        self.chat_entry.bind("<Return>", lambda e: self.submit_follow_up())
        self.chat_entry.bind("<Escape>", lambda e: self.hide_hud())

        self.chat_send_btn = one_ui.ModernButton(
            self.input_box_frame, text="Ask", icon="💬", variant="primary",
            font=FONT_MICRO, padx=14, pady=4, height=30, bg=one_ui.COLOR_SURFACE_SUB,
            command=self.submit_follow_up
        )
        self.chat_send_btn.pack(side="right", padx=(0, 8), pady=8)

        # Default state is picker view
        self.picker_frame.pack(fill="both", expand=True)

        self.fixed_width = int(620 * get_dpi_scale())

        # Initialize HWND and apply native acrylic blur and drop shadow
        self.hud.update_idletasks()
        try:
            p_hwnd = ctypes.windll.user32.GetParent(self.hud.winfo_id())
            self.hud_hwnd = p_hwnd if p_hwnd else self.hud.winfo_id()
        except Exception:
            self.hud_hwnd = self.hud.winfo_id()

        self.apply_tier_visual_mode()

    def _on_content_card_configure(self, event):
        """Dynamically adapts wraplength to actual card width to prevent right-edge text clipping."""
        try:
            avail_w = max(260, event.width - 40)
            if hasattr(self, "content_lbl") and self.content_lbl.winfo_exists():
                self.content_lbl.configure(wraplength=avail_w)
        except Exception:
            pass

    def _on_action_preview_configure(self, event):
        """Dynamically adapts preview text wraplength to preview card width."""
        try:
            avail_w = max(260, event.width - 28)
            if hasattr(self, "preview_desc_lbl") and self.preview_desc_lbl.winfo_exists():
                self.preview_desc_lbl.configure(wraplength=avail_w)
        except Exception:
            pass

    def apply_tier_visual_mode(self):
        """
        Dynamically configures minimalist theme and performance per active tier:
        - Lite (< 4 GB): Solid matte, zero blur overhead for 60fps, 620px width.
        - Normal (6-10 GB): Hardware Acrylic blur, 0.92 alpha, 640px width.
        - Extreme (12-16 GB): Frosted Glass acrylic, violet aura, 680px width.
        """
        blur_pref = self.config.get("blur_enabled", True)

        dpi_scale = get_dpi_scale()
        if self.tier_key == "lite":
            self.fixed_width = int(580 * dpi_scale)
            self.active_hud_alpha = 0.98
            apply_window_blur_and_shadow(self.hud_hwnd, enable=False)
            self.container.configure(bg=COLOR_CONTAINER, highlightbackground=COLOR_BORDER)
            self.tier_badge_lbl.configure(text=" LITE • < 4 GB ", fg="#FFFFFF", bg="#1C212D", highlightbackground="#2E3547")
        elif self.tier_key == "normal":
            self.fixed_width = int(620 * dpi_scale)
            self.active_hud_alpha = float(self.config.get("hud_opacity", 0.94))
            if blur_pref:
                apply_window_blur_and_shadow(self.hud_hwnd, enable=True, gradient_color=0xAA10131B)
            self.container.configure(bg=COLOR_CONTAINER, highlightbackground=COLOR_BORDER)
            self.tier_badge_lbl.configure(text=" NORMAL • 6 – 10 GB ", fg="#FFFFFF", bg="#1C212D", highlightbackground="#2E3547")
        else:  # extreme
            self.fixed_width = int(660 * dpi_scale)
            self.active_hud_alpha = float(self.config.get("hud_opacity", 0.94))
            if blur_pref:
                apply_window_blur_and_shadow(self.hud_hwnd, enable=True, gradient_color=0xAA12151E)
            self.container.configure(bg=COLOR_CONTAINER, highlightbackground=COLOR_BORDER)
            self.tier_badge_lbl.configure(text=" EXTREME • 12 – 16 GB ", fg="#FFFFFF", bg="#1C212D", highlightbackground="#2E3547")

    def copy_to_clipboard(self):
        """Copies accumulated explanation to system clipboard with visual feedback."""
        if not self.accumulated_text:
            return
        try:
            pyperclip.copy(self.accumulated_text)
        except Exception:
            pass
        self.copy_btn.set_text("Copied!", "✓")
        self.copy_btn.set_variant("success")
        self.root.after(1600, self._restore_copy_btn)

    def _restore_copy_btn(self):
        try:
            if self.root.winfo_exists():
                self.copy_btn.set_text("Copy", "📋")
                self.copy_btn.set_variant("surface")
        except Exception:
            pass

    # ---------------------------------------------------------------------------
    # PIN & INTELLIGENT AUTO-DISMISS ENGINE (Zero random disappearances)
    # ---------------------------------------------------------------------------
    def toggle_pin(self):
        """Toggles lock-on-screen pin mode so HUD stays indefinitely."""
        self.is_pinned = not self.is_pinned
        if self.is_pinned:
            self.pin_btn.set_text("Pinned", "📌")
            self.pin_btn.set_variant("success")
            # Cancel any pending auto-dismiss timer
            if self.linger_timer_id:
                try:
                    self.root.after_cancel(self.linger_timer_id)
                except Exception:
                    pass
                self.linger_timer_id = None
        else:
            self.pin_btn.set_text("Pin", "📌")
            self.pin_btn.set_variant("surface")
            # Only start dismiss countdown if not generating and streamer is finished
            if self.hud_visible and not self.is_thinking and not self.is_streaming and self.hud_state == "streamer" and not self.chat_expanded:
                self.schedule_auto_dismiss()

    def is_mouse_over_hud(self):
        """
        Robust screen-coordinate hover detection with a +12px margin of forgiveness.
        Prevents flickering and premature dismissal when traversing internal child widgets.
        """
        if not getattr(self, "hud_visible", False) or not getattr(self, "hud", None):
            return False
        try:
            px = self.hud.winfo_pointerx()
            py = self.hud.winfo_pointery()
            hx = self.hud.winfo_rootx()
            hy = self.hud.winfo_rooty()
            hw = self.hud.winfo_width()
            hh = self.hud.winfo_height()
            margin = 12
            return (hx - margin) <= px <= (hx + hw + margin) and (hy - margin) <= py <= (hy + hh + margin)
        except Exception:
            return False

    def on_hud_mouse_activity(self, event=None):
        """Refreshes active mouse timestamp and cancels pending dismiss while user interacts."""
        self.last_mouse_activity_time = time.time()
        if self.linger_timer_id:
            try:
                self.root.after_cancel(self.linger_timer_id)
            except Exception:
                pass
            self.linger_timer_id = None

    def on_hud_mouse_leave(self, event=None):
        """Called when mouse exits HUD; verifies true departure before starting linger countdown."""
        if self.is_mouse_over_hud():
            return
        if not self.is_pinned and not self.is_thinking and not self.is_streaming and self.hud_state == "streamer" and not self.chat_expanded:
            self.schedule_auto_dismiss()

    def schedule_auto_dismiss(self, delay_ms=None):
        """Schedules auto-dismiss verification. Never closes if pinned, generating, hovering, or in picker."""
        if self.linger_timer_id:
            try:
                self.root.after_cancel(self.linger_timer_id)
            except Exception:
                pass
            self.linger_timer_id = None

        # Guard conditions: HUD must stay active
        if self.is_pinned or self.is_thinking or self.is_streaming or self.hud_state == "picker" or self.chat_expanded:
            return

        wait_ms = delay_ms if delay_ms is not None else self.config.get("linger_duration_ms", 14000)
        self.linger_timer_id = self.root.after(wait_ms, self._check_auto_dismiss)

    def _check_auto_dismiss(self):
        """Double-checks all conditions before finally hiding HUD."""
        self.linger_timer_id = None
        if not getattr(self, "hud_visible", False):
            return

        # 1. Pinned, Generating, in Follow-up Chat, or in Action Picker? Stay open!
        if self.is_pinned or self.is_thinking or self.is_streaming or self.chat_expanded or self.hud_state == "picker":
            return

        # 2. Mouse currently hovered over HUD? Stay open!
        if self.is_mouse_over_hud():
            # Recheck in 3 seconds as long as mouse stays hovered
            self.linger_timer_id = self.root.after(3000, self._check_auto_dismiss)
            return

        # 3. Was there recent mouse activity within the linger window?
        now = time.time()
        linger_s = self.config.get("linger_duration_ms", 14000) / 1000.0
        elapsed_since_activity = now - self.last_mouse_activity_time
        if elapsed_since_activity < linger_s:
            rem_ms = max(1500, int((linger_s - elapsed_since_activity) * 1000))
            self.linger_timer_id = self.root.after(rem_ms, self._check_auto_dismiss)
            return

        # Safe to dismiss now
        self.hide_hud()

    def _on_drag_start(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag_motion(self, event):
        try:
            x = self.hud.winfo_x() + (event.x - self._drag_start_x)
            y = self.hud.winfo_y() + (event.y - self._drag_start_y)
            self.hud.geometry(f"+{x}+{y}")
            self.anchor_x = x
            self.anchor_y = y
        except Exception:
            pass

    def replace_selection_in_editor(self):
        """One-click code patch: extracts the pure fixed code from fenced code block,
        copies it to clipboard, then pastes it into the active editor window."""
        if not self.accumulated_text:
            return

        raw = self.accumulated_text.strip()
        clean_code = raw

        # Extract content from fenced code block(s) — ```lang\n...\n```
        if "```" in raw:
            code_blocks = []
            lines = raw.splitlines()
            inside_block = False
            current_block = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("```"):
                    if inside_block:
                        # End of block
                        if current_block:
                            code_blocks.append("\n".join(current_block))
                        current_block = []
                        inside_block = False
                    else:
                        # Start of block — skip the ```lang line itself
                        inside_block = True
                elif inside_block:
                    current_block.append(line)
            if current_block:  # Unclosed block
                code_blocks.append("\n".join(current_block))

            if code_blocks:
                # Use the largest code block (most complete fix)
                clean_code = max(code_blocks, key=len).strip()

        # If still no extraction happened and it starts with Bug:, remove diagnosis line
        if clean_code.startswith("Bug:"):
            lines = clean_code.splitlines()
            # Strip leading Bug: lines (may be 1-2 sentences)
            code_start = 0
            for i, line in enumerate(lines):
                if not line.startswith("Bug:") and line.strip():
                    code_start = i
                    break
            clean_code = "\n".join(lines[code_start:]).strip()

        if not clean_code:
            # Nothing useful to paste — fall back to full text
            clean_code = raw

        try:
            pyperclip.copy(clean_code)
            self.patch_btn.set_text("Applied!", "✓")
            self.patch_btn.set_variant("success")
            self.root.after(1800, lambda: (self.patch_btn.set_text("Patch", "⚡"), self.patch_btn.set_variant("amber")))
            self.simulate_paste()
        except Exception as e:
            print(f"[WARN] replace_selection_in_editor error: {e}")



    def simulate_paste(self):
        try:
            user32 = ctypes.windll.user32
            VK_CONTROL = 0x11
            VK_MENU = 0x12
            KEYEVENTF_KEYUP = 0x0002
            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.015)
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(ord('V'), 0, 0, 0)
            time.sleep(0.010)
            user32.keybd_event(ord('V'), 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

    def toggle_speech(self):
        """Toggles offline speech playback with immediate button feedback."""
        if not config_manager.is_tts_allowed(self.tier_key):
            self.picker_hint_lbl.configure(text="TTS audio is locked in Lite tier.", fg=COLOR_RED)
            self.root.after(2500, lambda: self.picker_hint_lbl.configure(text="⌨  Press 1–9, arrow keys, or click to run  •  Esc to close", fg=COLOR_TEXT_DIM))
            return

        if tts_helper.is_speaking():
            tts_helper.stop_speech()
            self.tts_btn.set_text("Listen", "🔊")
            self.tts_btn.set_variant("surface")
        else:
            if self.accumulated_text:
                tts_helper.speak_async(self.accumulated_text)
                self.tts_btn.set_text("Stop", "⏹")
                self.tts_btn.set_variant("amber")

    def speak_current_content(self):
        self.toggle_speech()

    def start_activity_animation(self, mode_color):
        """Animates a sleek glowing activity pulse strip under the header while thinking."""
        self.activity_canvas.pack(fill="x", padx=16, pady=(0, 4))
        self.anim_pos = 0
        self.anim_dir = 1
        self._animate_activity_tick(mode_color)

    def _animate_activity_tick(self, mode_color):
        if not self.is_thinking or not self.hud_visible:
            return
        try:
            self.activity_canvas.delete("all")
            w = self.activity_canvas.winfo_width()
            if w <= 1:
                w = self.fixed_width - 32
            bar_len = 90
            self.anim_pos += self.anim_dir * 14
            if self.anim_pos > w - bar_len:
                self.anim_pos = w - bar_len
                self.anim_dir = -1
            elif self.anim_pos < 0:
                self.anim_pos = 0
                self.anim_dir = 1

            self.activity_canvas.create_line(0, 1, w, 1, fill=COLOR_BORDER, width=2)
            self.activity_canvas.create_line(self.anim_pos, 1, self.anim_pos + bar_len, 1, fill=mode_color, width=2)
            self.anim_timer_id = self.root.after(35, lambda: self._animate_activity_tick(mode_color))
        except Exception:
            pass

    def stop_activity_animation(self, stream_color=None):
        if getattr(self, "anim_timer_id", None):
            try:
                self.root.after_cancel(self.anim_timer_id)
            except Exception:
                pass
            self.anim_timer_id = None
        try:
            if stream_color and self.is_streaming:
                w = self.activity_canvas.winfo_width()
                if w <= 1:
                    w = self.fixed_width - 32
                self.activity_canvas.delete("all")
                self.activity_canvas.create_line(0, 1, w, 1, fill=stream_color, width=2)
            else:
                self.activity_canvas.pack_forget()
        except Exception:
            pass

    def show_completion_metadata(self, elapsed=None, target_model=""):
        """Displays subtle metrics pill in footer upon generation completion."""
        try:
            parts = []
            if elapsed is not None:
                parts.append(f"⚡ {elapsed:.1f}s")
            if target_model:
                parts.append(target_model)
            if getattr(self, "used_web_search", False):
                parts.append("🌐 Web Enriched")
            if self.chat_turns > 0:
                max_turns = self.tier_spec.get("max_chat_turns", 3)
                parts.append(f"💬 Turn {self.chat_turns}/{max_turns}")

            meta_text = "   •   ".join(parts)
            self.meta_stats_lbl.configure(text=meta_text)
            self.meta_frame.pack(fill="x", pady=(0, 4))
        except Exception:
            pass

    def register_all_hotkeys(self):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        # Universal Action Palette hotkey: Ctrl + Alt + Space
        hk = self.config.get("hotkey", "ctrl+alt+space")
        if hk:
            try:
                keyboard.add_hotkey(hk, lambda: self.on_hotkey_triggered(None))
                print(f"[HOTKEY] Keyboard hotkey registered: {hk}")
            except Exception as e:
                print(f"[WARN] Failed to bind hotkey '{hk}': {e}")

    def process_gui_queue(self):
        try:
            while not self.event_queue.empty():
                msg_type, data = self.event_queue.get_nowait()
                if msg_type == "hotkey":
                    self.handle_hotkey(data)
                elif msg_type == "tts":
                    self.toggle_speech()
                elif msg_type == "token":
                    self.append_streaming_token(data)
                elif msg_type == "finished":
                    self.on_stream_finished()
                elif msg_type == "error":
                    self.on_system_error(data)
                elif msg_type == "reset_chat":
                    self.reset_for_new_stream()
                elif msg_type == "hide_hud":
                    self.hide_hud()
                elif msg_type == "quit":
                    self.quit_app()
        except Exception:
            pass

        # Sync TTS button state
        if getattr(self, "tts_btn", None) and config_manager.is_tts_allowed(self.tier_key):
            try:
                speaking = tts_helper.is_speaking()
                curr_txt = self.tts_btn.cget("text")
                if speaking and curr_txt != "Stop":
                    self.tts_btn.set_text("Stop", "⏹")
                    self.tts_btn.set_variant("amber")
                elif not speaking and curr_txt == "Stop":
                    self.tts_btn.set_text("Listen", "🔊")
                    self.tts_btn.set_variant("surface")
            except Exception:
                pass

        if self.is_alive:
            try:
                if self.root.winfo_exists():
                    self.gui_queue_timer_id = self.root.after(16, self.process_gui_queue)
            except Exception:
                pass

    def start_win32_hotkey_listener(self):
        t = threading.Thread(target=self._win32_hotkey_worker, daemon=True)
        t.start()

    def _win32_hotkey_worker(self):
        user32 = ctypes.windll.user32
        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", ctypes.c_void_p),
                ("message", ctypes.c_uint),
                ("wParam", ctypes.c_void_p),
                ("lParam", ctypes.c_void_p),
                ("time", ctypes.c_ulong),
                ("pt_x", ctypes.c_long),
                ("pt_y", ctypes.c_long),
                ("lPrivate", ctypes.c_ulong),
            ]
        msg = MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

        for hkid, (mode_name, mods, vk) in WIN32_HOTKEYS.items():
            res = user32.RegisterHotKey(None, hkid, mods, vk)
            if res:
                print(f"[HOTKEY] Native Win32 hotkey registered: ID {hkid} ({mode_name})")
            else:
                print(f"[WARN] Could not register native Win32 hotkey {hkid} ({mode_name})")

        while not self.stop_hotkeys.is_set():
            if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                if msg.message == 0x0312:  # WM_HOTKEY
                    hkid = msg.wParam
                    if hkid in WIN32_HOTKEYS:
                        self.event_queue.put(("hotkey", None))
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                time.sleep(0.01)

        for hkid in WIN32_HOTKEYS:
            user32.UnregisterHotKey(None, hkid)

    def on_hotkey_triggered(self, mode=None):
        self.event_queue.put(("hotkey", mode))

    def on_tts_triggered(self):
        self.event_queue.put(("tts", None))

    def toggle_follow_up(self, expand=True):
        if not config_manager.is_interactive_chat_allowed(self.tier_key):
            return

        max_turns = self.tier_spec.get("max_chat_turns", 3)
        if self.chat_turns >= max_turns and self.tier_key != "extreme":
            self.expand_prompt_lbl.configure(
                text=f"Turn limit ({max_turns}) reached for {self.tier_spec.get('name')} tier. Upgrade to Extreme for unlimited.",
                fg=COLOR_AMBER
            )
            return

        if expand and not self.chat_expanded:
            self.chat_expanded = True
            self.expand_prompt_lbl.pack_forget()
            self.input_box_frame.pack(fill="x")
            self.chat_entry.focus_set()
            if self.linger_timer_id:
                self.root.after_cancel(self.linger_timer_id)
                self.linger_timer_id = None
            self.update_hud_geometry()

    def simulate_copy(self):
        """Snappy 33ms virtual keystroke pulse to copy selected text without hotkey collisions."""
        try:
            user32 = ctypes.windll.user32
            VK_CONTROL = 0x11
            VK_MENU    = 0x12  # Alt
            VK_SPACE   = 0x20
            KEYEVENTF_KEYUP = 0x0002

            # Swift release of modifier keys
            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_SPACE, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.008)

            # Fire standard Ctrl + C (10ms down, 15ms settle: 33ms total latency)
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(ord('C'), 0, 0, 0)
            time.sleep(0.010)
            user32.keybd_event(ord('C'), 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.015)
        except Exception as e:
            print(f"[WARN] simulate_copy error: {e}")

    def _gather_screen_context_bg(self, exclude_hwnds):
        """Background worker: captures foreground window info instantly, then runs OCR async."""
        try:
            # Phase 1: Fast window metadata (~0ms) — no OCR yet
            ctx = screen_context.get_screen_context_summary(
                exclude_hwnds=exclude_hwnds, do_ocr=False
            )
            self.screen_context = ctx

            # Phase 2: OCR on window bounds (~0.8s) — runs after palette is already open
            ctx_with_ocr = screen_context.get_screen_context_summary(
                exclude_hwnds=exclude_hwnds, do_ocr=True
            )
            self.screen_context = ctx_with_ocr
        except Exception as e:
            print(f"[WARN] Screen context error: {e}")

    def handle_hotkey(self, mode=None):
        """
        Unified Hotkey Trigger (Ctrl + Alt + Space):
        1. Captures cursor location and active monitor work area.
        2. Fires ultra-fast 33ms copy pulse to grab highlighted text.
        3. Opens the minimalist Action Palette directly at the cursor.
        Screen context OCR runs in background so the palette appears immediately.
        """
        now = time.time()
        if now - getattr(self, "last_trigger_time", 0) < 0.35:
            return
        self.last_trigger_time = now

        tts_helper.stop_speech()
        self.capture_mouse_position()

        # Reload active tier & dynamically adapt visual theme
        self.tier_key, self.tier_spec = config_manager.get_active_tier()
        self.apply_tier_visual_mode()

        tier_name = self.tier_spec.get("name", "NORMAL").upper()
        tier_ram = self.tier_spec.get("ram_target", "")
        self.tier_badge_lbl.configure(text=f" {tier_name} • {tier_ram} ")
        self.update_tray_tooltip()

        # Update TTS button appearance
        tts_ok = config_manager.is_tts_allowed(self.tier_key)
        self.tts_btn.configure(
            fg=COLOR_TEXT_SEC if tts_ok else "#484F58",
            highlightbackground=COLOR_BORDER
        )

        # Capture foreground window info immediately (no OCR), run OCR in background
        exclude_hwnds = [self.hud_hwnd] if self.hud_hwnd else []
        self.screen_context = {}
        threading.Thread(
            target=self._gather_screen_context_bg,
            args=(exclude_hwnds,),
            daemon=True
        ).start()

        prev_clipboard = ""
        try:
            prev_clipboard = pyperclip.paste()
        except Exception:
            pass

        if self.config.get("auto_copy", True):
            self.simulate_copy()

        # Give Ctrl+C a reliable 80ms window to propagate to the target app
        time.sleep(0.08)

        text = ""
        try:
            current_clipboard = pyperclip.paste()
            if current_clipboard and current_clipboard != prev_clipboard and current_clipboard.strip():
                text = str(current_clipboard).strip()
            elif prev_clipboard and prev_clipboard.strip():
                text = str(prev_clipboard).strip()
        except Exception as e:
            print(f"[RECOVERY] Clipboard read error: {e}")

        max_chars = self.config.get("max_clipboard_chars", 12000)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[Text truncated for memory safety]..."

        self.current_snippet = text
        self.conversation_history = []
        self.chat_turns = 0

        # If a specific mode was directly passed (e.g. from tray menu), run it; else open palette
        if mode and config_manager.is_mode_allowed_in_tier(mode, self.tier_key):
            self.select_action(mode)
        else:
            self.show_action_picker()

    # ---------------------------------------------------------------------------
    # 3. ACTION PICKER & COMMAND PALETTE WORKFLOW
    # ---------------------------------------------------------------------------
    def show_action_picker(self):
        """Pops up the minimalist Action Palette HUD at the cursor."""
        self.hud_state = "picker"
        self.is_thinking = False
        self.is_streaming = False
        if self.active_abort_event:
            self.active_abort_event.set()
        self.stop_activity_animation()
        tts_helper.stop_speech()

        # Switch views
        self.stream_frame.pack_forget()
        self.picker_frame.pack(fill="both", expand=True)

        # Snippet preview card vs Entry
        if self.current_snippet and self.current_snippet.strip():
            clean_snip = " ".join(self.current_snippet.strip().split())
            if len(clean_snip) > 52:
                clean_snip = clean_snip[:49] + "..."
            char_count = len(self.current_snippet)
            self.picker_snippet_lbl.configure(
                text=f"“{clean_snip}” ({char_count} chars)",
                fg=COLOR_TEXT_MAIN
            )
            self.picker_snippet_card.pack(fill="x", padx=14, pady=(2, 6))
            self.picker_entry_frame.pack_forget()
        else:
            self.picker_snippet_card.pack_forget()
            self.picker_entry_frame.pack(fill="x")
            self.picker_entry.delete(0, tk.END)

        self.render_action_buttons()
        self.update_hud_geometry()
        self._fade_in_hud()

        if not self.current_snippet:
            self.picker_entry.focus_set()
        else:
            self.hud.focus_set()

        if self.linger_timer_id:
            try:
                self.root.after_cancel(self.linger_timer_id)
            except Exception:
                pass
            self.linger_timer_id = None

    def render_action_buttons(self):
        """Renders the aesthetic, spacious action list with squircle icon badges and tactile keycaps."""
        for widget in self.action_list_frame.winfo_children():
            widget.destroy()

        self.current_actions = config_manager.get_tier_actions(self.tier_key)
        self.action_rows = []
        self.selected_action_idx = 0

        for idx, act in enumerate(self.current_actions):
            mode = act["mode"]
            name = act["name"]
            shortcut = act["shortcut"]
            icon = act["icon"]
            allowed = act["allowed"]
            mode_color = MODE_COLORS.get(mode, COLOR_BLUE)
            mode_bg = MODE_BG_COLORS.get(mode, COLOR_BLUE_BG)
            summary_info = ACTION_SUMMARIES.get(mode, {})
            tagline = summary_info.get("tagline", "Context-aware AI operation")

            is_sel = (idx == 0 and allowed)

            # Spacious Action Card (Comfortable 56px click target)
            row = tk.Frame(
                self.action_list_frame,
                bg=COLOR_SURFACE_ELEV if is_sel else (COLOR_CONTAINER if allowed else "#0F121A"),
                bd=0, relief="flat",
                highlightbackground=mode_color if is_sel else (one_ui.COLOR_BORDER if allowed else "#161B26"),
                highlightthickness=1,
                cursor="hand2" if allowed else "arrow"
            )
            row.pack(fill="x", padx=20, pady=3, ipady=6)
            row.bind("<Motion>", self.on_hud_mouse_activity)

            # Tactile ModernKeycap Pill Badge: [ 1 ], [ 2 ], etc.
            badge_lbl = one_ui.ModernKeycap(
                row, key=shortcut, font=FONT_MICRO, padx=7, pady=2,
                bg="#1E2638" if is_sel else (one_ui.COLOR_SURFACE_SUB if allowed else "#0F121A"),
                fg=mode_color if is_sel else ("#E2E8F0" if allowed else COLOR_TEXT_DIM),
                border=mode_color if is_sel else (one_ui.COLOR_BORDER_LIGHT if allowed else one_ui.COLOR_BORDER),
                parent_bg=row.cget("bg")
            )
            badge_lbl.pack(side="left", padx=(12, 10), pady=4)

            # Tinted Squircle Icon Badge
            icon_badge = one_ui.OneUIIconBadge(
                row, icon=icon, size=36, radius=10,
                bg_color=mode_bg if allowed else "#141822",
                icon_color=mode_color if allowed else COLOR_TEXT_DIM,
                parent_bg=row.cget("bg")
            )
            icon_badge.pack(side="left", padx=(0, 10))

            # Action Text Block (Title + Subtitle)
            text_box = tk.Frame(row, bg=row.cget("bg"))
            text_box.pack(side="left", fill="both", expand=True)

            name_lbl = tk.Label(
                text_box, text=name, font=FONT_BOLD if allowed else FONT_BODY,
                bg=row.cget("bg"), fg=COLOR_TEXT_MAIN if allowed else COLOR_TEXT_DIM,
                anchor="w"
            )
            name_lbl.pack(fill="x")

            sub_lbl = tk.Label(
                text_box, text=tagline, font=FONT_SMALL,
                bg=row.cget("bg"), fg=COLOR_TEXT_SEC if allowed else COLOR_TEXT_DIM,
                anchor="w"
            )
            sub_lbl.pack(fill="x")

            # Right Status Indicator or Lock Badge
            if not allowed:
                req = act.get("required_tier", "normal").capitalize()
                lock_lbl = tk.Label(
                    row, text=f"🔒 {req.upper()}", font=FONT_MICRO,
                    bg=COLOR_RED_BG, fg=COLOR_RED, padx=8, pady=3,
                    bd=0, relief="flat", highlightbackground=COLOR_RED_BORDER, highlightthickness=1
                )
                lock_lbl.pack(side="right", padx=(0, 12))
                right_ind = lock_lbl
            else:
                status_ind = tk.Label(
                    row, text="●" if is_sel else "›", font=FONT_MICRO,
                    bg=row.cget("bg"), fg=mode_color if is_sel else COLOR_TEXT_DIM
                )
                status_ind.pack(side="right", padx=(0, 14))
                right_ind = status_ind

            def _enter(r=row, b=badge_lbl, ib=icon_badge, c=mode_color, i=idx, tb=text_box, nl=name_lbl, sl=sub_lbl, ri=right_ind, al=allowed, a=act):
                return lambda e: (
                    r.configure(bg=COLOR_SURFACE_ELEV, highlightbackground=c),
                    b.configure(bg="#232E45", highlightbackground=c, fg="#FFFFFF"),
                    ib.configure(bg=COLOR_SURFACE_ELEV),
                    tb.configure(bg=COLOR_SURFACE_ELEV),
                    nl.configure(bg=COLOR_SURFACE_ELEV),
                    sl.configure(bg=COLOR_SURFACE_ELEV),
                    ri.configure(bg=COLOR_SURFACE_ELEV, text="●", fg=c) if (al and hasattr(ri, "configure") and ri.cget("text") != f"🔒 {a.get('required_tier', 'normal').upper()}") else None,
                    self.update_action_summary(i)
                )

            def _leave(r=row, b=badge_lbl, ib=icon_badge, i=idx, tb=text_box, nl=name_lbl, sl=sub_lbl, ri=right_ind, al=allowed, a=act, c=mode_color):
                is_curr_sel = (i == getattr(self, "selected_action_idx", 0))
                def_bg = COLOR_SURFACE_ELEV if is_curr_sel else (COLOR_CONTAINER if al else "#0F121A")
                return lambda e: (
                    r.configure(
                        bg=def_bg,
                        highlightbackground=COLOR_BLUE if is_curr_sel else (one_ui.COLOR_BORDER if al else "#161B26")
                    ),
                    b.configure(
                        bg="#1E2638" if is_curr_sel else (one_ui.COLOR_SURFACE_SUB if al else "#0F121A"),
                        highlightbackground=COLOR_BLUE if is_curr_sel else (one_ui.COLOR_BORDER_LIGHT if al else one_ui.COLOR_BORDER),
                        fg=c if is_curr_sel else ("#E2E8F0" if al else COLOR_TEXT_DIM)
                    ),
                    ib.configure(bg=def_bg),
                    tb.configure(bg=def_bg),
                    nl.configure(bg=def_bg),
                    sl.configure(bg=def_bg),
                    ri.configure(
                        bg=def_bg,
                        text="●" if is_curr_sel else "›",
                        fg=COLOR_BLUE if is_curr_sel else COLOR_TEXT_DIM
                    ) if (al and hasattr(ri, "configure") and ri.cget("text") != f"🔒 {a.get('required_tier', 'normal').upper()}") else None
                )

            interactive_widgets = [row, badge_lbl, icon_badge, text_box, name_lbl, sub_lbl, right_ind]
            for w in interactive_widgets:
                if allowed:
                    w.bind("<Button-1>", lambda e, m=mode: self.select_action(m))
                else:
                    w.bind("<Button-1>", lambda e, a=act: self.flash_locked_badge(a))
                w.bind("<Enter>", _enter())
                w.bind("<Leave>", _leave())
                w.bind("<Motion>", self.on_hud_mouse_activity)

            self.action_rows.append((row, badge_lbl, act, text_box, name_lbl, sub_lbl, right_ind))

        # Initialize summary card for active selection
        self.update_action_summary(self.selected_action_idx)

    def update_action_summary(self, idx):
        """Updates the dedicated Function Summary Card when hovering or navigating actions."""
        if not self.current_actions or not (0 <= idx < len(self.current_actions)):
            return
        act = self.current_actions[idx]
        mode = act.get("mode", "explain")
        name = act.get("name", mode.capitalize())
        shortcut = act.get("shortcut", str(idx + 1))
        icon = act.get("icon", "⚡")
        allowed = act.get("allowed", True)
        req_tier = act.get("required_tier", "lite").upper()

        summary_info = ACTION_SUMMARIES.get(mode, {
            "summary": "Execute customized copilot analysis on target text.",
            "badge": f"{req_tier}+",
            "tags": "AI Action"
        })

        mode_color = MODE_COLORS.get(mode, COLOR_BLUE)
        self.preview_title_lbl.configure(text=f"[{shortcut}] {icon} {name}", fg=mode_color)
        self.preview_desc_lbl.configure(text=summary_info.get("summary", ""))
        self.preview_tags_lbl.configure(text=summary_info.get("tags", ""))

        if allowed:
            self.preview_tier_pill.configure(
                text=f" ✓ {summary_info.get('badge', req_tier)} ",
                fg=COLOR_GREEN, bg=COLOR_GREEN_BG, highlightbackground=COLOR_GREEN
            )
        else:
            self.preview_tier_pill.configure(
                text=f" 🔒 {req_tier} ONLY ",
                fg=COLOR_AMBER, bg=COLOR_AMBER_BG, highlightbackground=COLOR_AMBER_BORDER
            )

    def _on_hud_key(self, event):
        """Unified keyboard handler for Action Palette and Streaming views."""
        state = getattr(self, "hud_state", "picker")
        if state == "picker":
            # If user is actively typing in prompt entry
            if self.hud.focus_get() == getattr(self, "picker_entry", None):
                if event.keysym in ("Return", "KP_Enter"):
                    self._on_picker_entry_submit()
                    return "break"
                elif event.keysym == "Escape":
                    self.hide_hud()
                    return "break"
                return

            keysym = event.keysym
            char = event.char.lower() if event.char else ""

            if keysym == "Escape":
                self.hide_hud()
                return "break"
            elif keysym in ("Return", "KP_Enter"):
                if self.current_actions and 0 <= self.selected_action_idx < len(self.current_actions):
                    act = self.current_actions[self.selected_action_idx]
                    if act.get("allowed"):
                        self.select_action(act["mode"])
                return "break"
            elif keysym in ("Up", "Left"):
                self._move_picker_selection(-1)
                return "break"
            elif keysym in ("Down", "Right"):
                self._move_picker_selection(1)
                return "break"

            # Check direct 1..9, 0 or letter shortcuts
            for act in getattr(self, "current_actions", []):
                if char and char in (act.get("shortcut"), act.get("letter")):
                    if act.get("allowed"):
                        self.select_action(act["mode"])
                    else:
                        self.flash_locked_badge(act)
                    return "break"

        elif state == "streamer":
            # If focused in chat entry, let it handle input
            if self.hud.focus_get() == getattr(self, "chat_entry", None):
                if event.keysym == "Escape":
                    self.hide_hud()
                    return "break"
                return

            if event.keysym == "Escape":
                self.hide_hud()
                return "break"
            elif event.keysym == "BackSpace":
                self.show_action_picker()
                return "break"
            elif event.keysym == "Tab":
                self.toggle_follow_up(True)
                return "break"

    def _move_picker_selection(self, delta):
        if not self.action_rows:
            return

        # Unhighlight current
        curr_row, curr_badge, curr_act, curr_tb, curr_nl, curr_sl, curr_ri = self.action_rows[self.selected_action_idx]
        curr_row.configure(bg=COLOR_CONTAINER, highlightbackground=COLOR_BORDER)
        curr_badge.configure(bg=one_ui.COLOR_SURFACE_SUB, highlightbackground=one_ui.COLOR_BORDER_LIGHT if curr_act.get("allowed") else one_ui.COLOR_BORDER, fg="#E2E8F0" if curr_act.get("allowed") else COLOR_TEXT_DIM)
        curr_tb.configure(bg=COLOR_CONTAINER)
        curr_nl.configure(bg=COLOR_CONTAINER)
        curr_sl.configure(bg=COLOR_CONTAINER)
        if curr_act.get("allowed") and hasattr(curr_ri, "configure") and curr_ri.cget("text") != f"🔒 {curr_act.get('required_tier', 'normal').upper()}":
            curr_ri.configure(bg=COLOR_CONTAINER, text="›", fg=COLOR_TEXT_DIM)

        # Move to next allowed option
        n = len(self.action_rows)
        for _ in range(n):
            self.selected_action_idx = (self.selected_action_idx + delta) % n
            act = self.action_rows[self.selected_action_idx][2]
            if act.get("allowed"):
                break

        # Highlight new
        new_row, new_badge, act, new_tb, new_nl, new_sl, new_ri = self.action_rows[self.selected_action_idx]
        mode_color = MODE_COLORS.get(act["mode"], COLOR_BLUE)
        new_row.configure(bg=COLOR_SURFACE_ELEV, highlightbackground=mode_color)
        new_badge.configure(bg="#232E45", highlightbackground=mode_color, fg="#FFFFFF")
        new_tb.configure(bg=COLOR_SURFACE_ELEV)
        new_nl.configure(bg=COLOR_SURFACE_ELEV)
        new_sl.configure(bg=COLOR_SURFACE_ELEV)
        if act.get("allowed") and hasattr(new_ri, "configure") and new_ri.cget("text") != f"🔒 {act.get('required_tier', 'normal').upper()}":
            new_ri.configure(bg=COLOR_SURFACE_ELEV, text="●", fg=mode_color)
        self.update_action_summary(self.selected_action_idx)

    def _on_picker_entry_submit(self):
        text = self.picker_entry.get().strip()
        if text:
            self.current_snippet = text
            self.select_action("explain")

    def flash_locked_badge(self, act):
        req = act.get("required_tier", "normal").upper()
        self.picker_hint_lbl.configure(
            text=f"🔒 '{act.get('name')}' requires {req} tier. Open Settings to upgrade.",
            fg=COLOR_RED
        )
        self.root.after(2600, lambda: self.picker_hint_lbl.configure(
            text="⌨  Press 1–9, arrow keys, or click to run  •  Esc to close",
            fg=COLOR_TEXT_DIM
        ))

    def select_action(self, mode):
        """Transitions seamlessly from Action Palette to live Streaming Result view."""
        self.hud_state = "streamer"
        self.current_mode = mode

        # If user typed into entry
        if not self.current_snippet and self.picker_entry.winfo_viewable():
            typed = self.picker_entry.get().strip()
            if typed:
                self.current_snippet = typed

        # Switch to streamer view
        self.picker_frame.pack_forget()
        self.stream_frame.pack(fill="both", expand=True)

        mode_spec = config_manager.get_mode_spec(mode)
        mode_color = MODE_COLORS.get(mode, COLOR_BLUE)
        mode_icon = MODE_ICONS.get(mode, "⚡")

        self.stream_mode_badge.configure(
            text=f" {mode_icon} {mode.upper()} ",
            fg=mode_color,
            bg=MODE_BG_COLORS.get(mode, COLOR_BLUE_BG),
            highlightbackground=MODE_BG_COLORS.get(mode, COLOR_BLUE_BG)
        )

        # Patch button in Fix mode
        if mode == "fix":
            self.patch_btn.pack(side="left", padx=(0, 8), before=self.copy_btn)
        else:
            self.patch_btn.pack_forget()

        # Reset streaming state
        self.accumulated_text = ""
        self.content_lbl.configure(text="", fg="#EDF2F7")
        self.meta_frame.pack_forget()
        self.meta_stats_lbl.configure(text="")

        # Configure follow-up chat frame based on active tier
        self.chat_expanded = False
        self.input_box_frame.pack_forget()
        self.chat_entry.delete(0, tk.END)

        if config_manager.is_interactive_chat_allowed(self.tier_key):
            self.follow_up_frame.pack(fill="x", padx=20, pady=(0, 12))
            max_turns = self.tier_spec.get("max_chat_turns", 3)
            self.expand_prompt_lbl.configure(
                text=f"💬  Press Tab or click to ask follow-up ({max_turns} remaining)...",
                fg=COLOR_TEXT_SEC,
                cursor="hand2"
            )
            self.expand_prompt_lbl.pack(fill="x")
        else:
            self.follow_up_frame.pack(fill="x", padx=20, pady=(0, 12))
            self.expand_prompt_lbl.configure(
                text="🔒 Follow-up chat unlocked in Normal (6–10 GB) & Extreme (12–16 GB)",
                fg=COLOR_TEXT_DIM,
                cursor="arrow"
            )
            self.expand_prompt_lbl.pack(fill="x")

        target_model = self.tier_spec.get("model", "llama3.1:8b")
        self.status_states = [
            f"⚡ Initializing {target_model}...",
            f"🔍 Analyzing snippet with {target_model}...",
            f"✦ Formulating concise insights...",
            f"✦ Streaming response..."
        ]
        self.status_pill.configure(
            text=self.status_states[0],
            fg=mode_color,
            bg=COLOR_SURFACE_ELEV
        )
        self.status_frame.pack(fill="x")

        self.update_hud_geometry()
        self.start_activity_animation(mode_color)
        self.update_status_animation()

        # Ensure no lingering dismiss timer is active while generating
        if self.linger_timer_id:
            try:
                self.root.after_cancel(self.linger_timer_id)
            except Exception:
                pass
            self.linger_timer_id = None

        if self.active_abort_event:
            self.active_abort_event.set()
        self.active_abort_event = threading.Event()

        self.is_thinking = True
        self.is_streaming = True
        self.start_time = time.time()

        threading.Thread(
            target=self.run_ai_pipeline,
            args=(self.current_snippet, mode, self.active_abort_event),
            daemon=True
        ).start()

    def toggle_annotation_guide(self):
        """Toggles the transparent on-screen visual guide spotlight and step pin."""
        if getattr(self, "annotation_overlay", None):
            if self.annotation_overlay.is_visible:
                self.annotation_overlay.hide()
                if getattr(self, "guide_btn", None):
                    self.guide_btn.set_variant("surface")
            else:
                mode_color = MODE_COLORS.get(self.current_mode, COLOR_BLUE)
                mode_spec = config_manager.get_mode_spec(self.current_mode)
                self.annotation_overlay.show_cursor_spotlight(
                    self.anchor_x, self.anchor_y,
                    title=f"{mode_spec.get('name', self.current_mode).upper()}",
                    text=f"Active screen guidance: {self.tier_spec.get('name')} tier",
                    step_num=1,
                    color=mode_color
                )
                if getattr(self, "guide_btn", None):
                    self.guide_btn.set_variant("success")

    def update_status_animation(self):
        try:
            if not self.root.winfo_exists():
                return
            if self.is_thinking and self.hud_visible:
                if self.status_states:
                    st_text = self.status_states[self.status_index % len(self.status_states)]
                    self.status_pill.configure(text=st_text)
                    self.status_index += 1
                self.update_hud_geometry()
                self.root.after(450, self.update_status_animation)
        except Exception:
            pass

    def capture_mouse_position(self):
        try:
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            self.anchor_x = pt.x
            self.anchor_y = pt.y
        except Exception:
            self.anchor_x = 400
            self.anchor_y = 300

    def update_hud_geometry(self):
        """Calculates precise multi-monitor geometry, clamping inside work area and flipping when near edges."""
        try:
            if not self.root.winfo_exists() or not self.hud.winfo_exists():
                return

            self.hud.update_idletasks()

            win_w = getattr(self, "fixed_width", 500)
            req_h = self.container.winfo_reqheight()
            win_h = max(110, req_h)

            cur_x = getattr(self, "anchor_x", 400)
            cur_y = getattr(self, "anchor_y", 300)

            # Accurate Multi-Monitor work area (excluding taskbar on monitor containing cursor)
            m_left, m_top, m_right, m_bottom = get_monitor_work_area(cur_x, cur_y)
            m_height = m_bottom - m_top

            # Dynamic max height limit leaving breathing room
            max_h = max(200, m_height - 60)
            win_h = min(win_h, max_h)

            # Position HUD adjacent to cursor with slight offset
            target_x = cur_x + 18
            target_y = cur_y + 18

            # If expanding past monitor right border, flip to left of cursor
            if target_x + win_w > m_right - 12:
                target_x = cur_x - win_w - 18

            # If expanding past monitor bottom border (or taskbar), flip above cursor
            if target_y + win_h > m_bottom - 12:
                target_y = cur_y - win_h - 18

            # Clamp strictly inside current monitor work area
            target_x = max(m_left + 12, min(target_x, m_right - win_w - 12))
            target_y = max(m_top + 12, min(target_y, m_bottom - win_h - 12))

            self.hud.geometry(f"{win_w}x{win_h}+{int(target_x)}+{int(target_y)}")
        except Exception:
            pass

    def append_streaming_token(self, token):
        try:
            if not self.root.winfo_exists():
                return
            if self.is_thinking:
                self.is_thinking = False
                mode_color = MODE_COLORS.get(self.current_mode, COLOR_BLUE)
                self.stop_activity_animation(stream_color=mode_color)
                self.status_frame.pack_forget()
                self.container.configure(highlightbackground=COLOR_BORDER)
                self.content_lbl.configure(fg=COLOR_TEXT_MAIN)
                self.accumulated_text = ""

            self.accumulated_text += token
            # Real-time token streaming with subtle cursor block
            self.content_lbl.configure(text=self.accumulated_text + " ▋")

            now = time.time()
            # Debounce heavy OS window layout updates to eliminate GUI lag
            if ("\n" in token) or (now - getattr(self, "_last_geom_time", 0.0) > 0.08):
                self._last_geom_time = now
                self.update_hud_geometry()
        except Exception:
            pass

    def on_stream_finished(self):
        try:
            if not self.root.winfo_exists():
                return
            self.is_streaming = False
            self.stop_activity_animation()
            self.content_lbl.configure(text=self.accumulated_text)
            self.update_hud_geometry()
            elapsed = time.time() - self.start_time if self.start_time else None
            target_model = self.tier_spec.get("model", "local-ai")

            # Show completion metadata metrics
            self.show_completion_metadata(elapsed, target_model)
            self.update_hud_geometry()

            # Save to local history
            history_manager.add_entry(
                snippet=self.current_snippet,
                response=self.accumulated_text,
                tier=self.tier_key,
                mode=self.current_mode,
                model=target_model,
                latency_s=elapsed
            )

            # Auto-TTS if enabled and allowed in this tier
            if self.config.get("tts_enabled", False) and config_manager.is_tts_allowed(self.tier_key):
                self.speak_current_content()

            # Intelligent auto-dismiss scheduling (respects pin, hover, and interaction)
            self.schedule_auto_dismiss()
        except Exception:
            pass

    def submit_follow_up(self):
        query = self.chat_entry.get().strip()
        if not query or self.is_thinking:
            return

        # Cancel any active auto-dismiss while thinking/chatting
        if self.linger_timer_id:
            try:
                self.root.after_cancel(self.linger_timer_id)
            except Exception:
                pass
            self.linger_timer_id = None

        self.chat_turns += 1
        self.chat_entry.delete(0, tk.END)
        self.is_thinking = True
        self.is_streaming = True
        self.meta_frame.pack_forget()

        target_model = self.tier_spec.get("model", "llama3.1:8b")
        mode_color = MODE_COLORS.get(self.current_mode, COLOR_BLUE)

        self.status_states = [
            f"⚡ Processing follow-up turn {self.chat_turns}...",
            f"✦ Reasoning with {target_model}...",
            f"✦ Streaming response..."
        ]
        self.status_pill.configure(text=self.status_states[0], fg=mode_color, bg=COLOR_SURFACE_ELEV)
        self.status_frame.pack(fill="x")
        self.start_activity_animation(mode_color)

        if not self.current_snippet:
            self.current_snippet = query
            self.start_time = time.time()
            if self.active_abort_event:
                self.active_abort_event.set()
            self.active_abort_event = threading.Event()
            threading.Thread(
                target=self.run_ai_pipeline,
                args=(query, self.current_mode, self.active_abort_event),
                daemon=True
            ).start()
            return

        if not config_manager.is_interactive_chat_allowed(self.tier_key):
            return

        # Multi-turn context
        messages = [
            {"role": "system", "content": self.tier_spec.get("system_prompt", "")},
            {"role": "user", "content": f"Context/Snippet:\n{self.current_snippet}"},
            {"role": "assistant", "content": self.accumulated_text},
            {"role": "user", "content": query}
        ]

        threading.Thread(
            target=self.run_chat_pipeline,
            args=(messages, self.active_abort_event),
            daemon=True
        ).start()

    def run_chat_pipeline(self, messages, abort_event):
        target_model = self.tier_spec.get("model", "llama3.1:8b")
        keep_alive = self.tier_spec.get("keep_alive", "15m")
        ollama_url = config_manager.normalize_ollama_url(self.config.get("ollama_url", "http://127.0.0.1:11434"))

        # Auto-ensure Ollama daemon is running
        if not config_manager.is_ollama_online(ollama_url):
            started = config_manager.ensure_ollama_running(ollama_url, wait_seconds=6)
            if not started:
                if not abort_event.is_set() and self.is_alive:
                    self.event_queue.put(("error", "Engine Offline: Could not connect to or start Ollama (`ollama serve`)."))
                return

        # Model presence check & auto-fallback
        installed = config_manager.get_installed_ollama_models(ollama_url)
        if installed and target_model not in installed:
            for cand in ["llama3.1:8b", "llama3.2:3b", "smollm2:1.7b", "llama3.2"]:
                if cand in installed:
                    target_model = cand
                    break
            else:
                target_model = installed[0]

        options = {
            "num_predict": 400,
            "num_ctx": self.tier_spec.get("num_ctx", 2048),
            "temperature": 0.25,
            "top_p": 0.85
        }

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": True,
            "options": options,
            "keep_alive": keep_alive
        }

        try:
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{ollama_url}/api/chat",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=45) as response:
                first_token = True
                for line in response:
                    if abort_event.is_set() or not self.is_alive:
                        return
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8', errors='ignore'))
                            token = chunk.get("message", {}).get("content", "")
                            if token and self.is_alive:
                                if first_token:
                                    first_token = False
                                    self.event_queue.put(("reset_chat", None))
                                self.event_queue.put(("token", token))
                        except Exception:
                            continue

            if not abort_event.is_set() and self.is_alive:
                self.event_queue.put(("finished", None))

        except urllib.error.HTTPError as he:
            err_msg = f"HTTP {he.code}"
            try:
                raw_body = he.read().decode('utf-8', errors='ignore')
                body_json = json.loads(raw_body)
                if "error" in body_json:
                    err_msg = body_json["error"]
            except Exception:
                pass
            if not abort_event.is_set() and self.is_alive:
                self.event_queue.put(("error", f"Ollama Error: {err_msg}"))
        except urllib.error.URLError as ue:
            if not abort_event.is_set() and self.is_alive:
                self.event_queue.put(("error", f"Connection Error: {ue.reason}. Ensure Ollama is running (`ollama serve`)."))
        except Exception as e:
            if not abort_event.is_set() and self.is_alive:
                self.event_queue.put(("error", f"Chat Error: {e}"))

    def reset_for_new_stream(self):
        self.is_thinking = False
        self.stop_activity_animation(stream_color=MODE_COLORS.get(self.current_mode, COLOR_BLUE))
        self.status_frame.pack_forget()
        self.container.configure(highlightbackground=COLOR_BORDER)
        if getattr(self, "content_card", None):
            self.content_card.configure(highlightbackground=COLOR_BORDER)
        self.content_lbl.configure(fg=COLOR_TEXT_MAIN)
        self.accumulated_text = ""
        self.update_hud_geometry()

    def on_system_error(self, message):
        self.is_thinking = False
        self.is_streaming = False
        self.stop_activity_animation()
        self.status_frame.pack_forget()
        self.container.configure(highlightbackground=COLOR_RED)
        if getattr(self, "content_card", None):
            self.content_card.configure(highlightbackground=COLOR_RED)
        self.content_lbl.configure(text=message, fg=COLOR_RED)
        self.update_hud_geometry()
        self.schedule_auto_dismiss(6000)

    def _fade_in_hud(self):
        """Smooth hardware-accelerated fade-in transition."""
        if self._fade_timer_id:
            try:
                self.root.after_cancel(self._fade_timer_id)
            except Exception:
                pass
            self._fade_timer_id = None

        self.hud.deiconify()
        self.hud_visible = True
        try:
            curr = float(self.hud.attributes("-alpha"))
        except Exception:
            curr = 0.0

        if curr >= self.active_hud_alpha:
            return

        self._current_fade_alpha = max(0.0, curr)
        self._step_fade_in()

    def _step_fade_in(self):
        if not self.is_alive or not getattr(self, "hud", None):
            return
        target = self.active_hud_alpha
        step = max(0.12, (target - self._current_fade_alpha) * 0.45)
        self._current_fade_alpha = min(target, self._current_fade_alpha + step)
        try:
            self.hud.attributes("-alpha", self._current_fade_alpha)
        except Exception:
            pass

        if self._current_fade_alpha < target:
            self._fade_timer_id = self.root.after(16, self._step_fade_in)
        else:
            self._fade_timer_id = None

    def _fade_out_hud(self, callback=None):
        """Smooth hardware-accelerated fade-out transition before hiding."""
        if self._fade_timer_id:
            try:
                self.root.after_cancel(self._fade_timer_id)
            except Exception:
                pass
            self._fade_timer_id = None

        self._fade_callback = callback
        try:
            curr = float(self.hud.attributes("-alpha"))
        except Exception:
            curr = 0.0
        self._current_fade_alpha = curr

        if self._current_fade_alpha <= 0.02:
            if self._fade_callback:
                cb = self._fade_callback
                self._fade_callback = None
                cb()
            return

        self._step_fade_out()

    def _step_fade_out(self):
        if not self.is_alive or not getattr(self, "hud", None):
            return
        step = max(0.14, self._current_fade_alpha * 0.40)
        self._current_fade_alpha = max(0.0, self._current_fade_alpha - step)
        try:
            self.hud.attributes("-alpha", self._current_fade_alpha)
        except Exception:
            pass

        if self._current_fade_alpha > 0.01:
            self._fade_timer_id = self.root.after(16, self._step_fade_out)
        else:
            self._fade_timer_id = None
            if self._fade_callback:
                cb = self._fade_callback
                self._fade_callback = None
                cb()

    def _cleanup_hud_contents(self):
        """Resets HUD window visibility and wipes transient streaming text."""
        try:
            self.hud.attributes("-alpha", 0.0)
            self.hud.withdraw()
        except Exception:
            pass
        if getattr(self, "content_lbl", None):
            self.content_lbl.configure(text="")
        self.accumulated_text = ""
        if getattr(self, "status_frame", None):
            self.status_frame.pack_forget()
        if getattr(self, "meta_frame", None):
            self.meta_frame.pack_forget()
        if getattr(self, "tts_btn", None):
            self.tts_btn.set_text("Listen", "🔊")
            self.tts_btn.set_variant("surface" if config_manager.is_tts_allowed(self.tier_key) else "ghost")

    def hide_hud(self, instant=False):
        if self.linger_timer_id:
            try:
                self.root.after_cancel(self.linger_timer_id)
            except Exception:
                pass
            self.linger_timer_id = None
        self.is_pinned = False
        if getattr(self, "pin_btn", None):
            self.pin_btn.set_text("Pin", "📌")
            self.pin_btn.set_variant("surface")
        tts_helper.stop_speech()
        self.hud_visible = False
        self.is_thinking = False
        self.is_streaming = False
        self.chat_expanded = False
        self.stop_activity_animation()
        if getattr(self, "annotation_overlay", None):
            self.annotation_overlay.hide()
        if getattr(self, "guide_btn", None):
            self.guide_btn.set_variant("surface")
        if getattr(self, "active_abort_event", None):
            self.active_abort_event.set()
        if getattr(self, "patch_btn", None):
            self.patch_btn.pack_forget()

        if instant:
            if self._fade_timer_id:
                try:
                    self.root.after_cancel(self._fade_timer_id)
                except Exception:
                    pass
                self._fade_timer_id = None
            self._cleanup_hud_contents()
        else:
            self._fade_out_hud(callback=self._cleanup_hud_contents)

    def run_ai_pipeline(self, text, mode, abort_event):
        spec = self.tier_spec
        target_model = spec.get("model", "llama3.1:8b")
        allow_web = config_manager.is_web_search_allowed(self.tier_key)
        keep_alive = spec.get("keep_alive", "15m")

        mode_spec = config_manager.get_mode_spec(mode)
        mode_suffix = mode_spec.get("prompt_suffix", "")

        # --- System Prompt: use mode's dedicated system_prompt if defined,
        #     otherwise fall back to tier's generic base.
        #     Always append a hard no-filler directive.
        mode_system = mode_spec.get("system_prompt", "")
        tier_system = spec.get("system_prompt", "Explain what this is clearly.")
        if mode_system:
            system_prompt = (
                f"{mode_system}\n"
                f"IMPORTANT: Do not add greetings, filler phrases, or meta commentary. "
                f"Respond immediately and directly. Never say \'Certainly!\', \'Of course!\', "
                f"\'Sure!\', or \'Great question!\' — just do the task."
            )
        else:
            system_prompt = (
                f"{tier_system} Specific goal: {mode_suffix} "
                f"Provide an immediate, direct response without conversational greetings or pleasantries."
            )

        ollama_url = config_manager.normalize_ollama_url(self.config.get("ollama_url", "http://127.0.0.1:11434"))

        # Auto-ensure Ollama daemon is running
        if not config_manager.is_ollama_online(ollama_url):
            started = config_manager.ensure_ollama_running(ollama_url, wait_seconds=6)
            if not started:
                if not abort_event.is_set() and self.is_alive:
                    self.event_queue.put(("error", "Engine Offline: Could not connect to or start Ollama (`ollama serve`)."))
                return

        # Model presence check & auto-fallback
        installed = config_manager.get_installed_ollama_models(ollama_url)
        if installed and target_model not in installed:
            for cand in ["llama3.1:8b", "llama3.2:3b", "smollm2:1.7b", "llama3.2"]:
                if cand in installed:
                    target_model = cand
                    break
            else:
                target_model = installed[0]

        # --- Code detection ---
        code_indicators = [
            "try:", "def ", "import ", "return ", "class ", "const ", "function",
            "public static", "void ", "if (", "for (", "while (", "elif ", "except ",
            "=>", "->", "#include", "SELECT ", "FROM ", "CREATE TABLE"
        ]
        is_code = (
            any(ind in text for ind in code_indicators) or
            (len(text) > 20 and text.count("\n") > 1 and ("=" in text or "(" in text))
        )

        # --- Web search: smarter per-mode triggering ---
        web_context = ""
        self.used_web_search = False
        words = text.strip().split()
        is_short_concept = (
            1 <= len(words) <= 6
            and "\n" not in text
            and not any(ch in text for ch in ("{", "}", ";", "=>", "->"))
        )

        if allow_web and not abort_event.is_set():
            search_query = None

            if mode == "explain" and not is_code and is_short_concept:
                search_query = text.strip()

            elif mode == "regex":
                if any(ch in text for ch in ("\\", "^", "$", "[", "]", "*", "+", "?", "|")):
                    search_query = f"regex pattern explanation: {text.strip()[:80]}"
                elif text.strip().startswith(("ls", "grep", "awk", "sed", "curl", "git ", "npm ", "pip ", "docker ")):
                    search_query = f"shell command: {text.strip()[:80]}"

            elif mode == "fix" and is_code:
                error_keywords = [
                    "error:", "exception:", "traceback", "SyntaxError", "TypeError",
                    "NameError", "AttributeError", "ValueError", "cannot", "undefined",
                    "ImportError", "KeyError", "IndexError"
                ]
                if any(kw.lower() in text.lower() for kw in error_keywords):
                    for line in text.splitlines():
                        if any(kw.lower() in line.lower() for kw in error_keywords):
                            search_query = line.strip()[:100]
                            break

            if search_query:
                results = search_helper.search_duckduckgo(search_query, max_results=2)
                if results:
                    web_context = "\n".join(results)
                    self.used_web_search = True

        if abort_event.is_set():
            return

        # --- Build the core prompt ---
        prompt = f"Task: {mode_suffix}\n\nTarget text:\n{text}"
        if web_context:
            prompt = f"Task: {mode_suffix}\n\nReference context (from web):\n{web_context}\n\nTarget text:\n{text}"

        # --- Enrich with screen context (background OCR populated in handle_hotkey) ---
        sc = getattr(self, "screen_context", {})
        if not sc or not sc.get("has_content"):
            clean_title = sc.get("clean_title", "") if sc else ""
            if not text and clean_title:
                text = f"[Active Window: {clean_title}]"
                self.current_snippet = text
        if sc and (sc.get("visible_text") or sc.get("clean_title") or sc.get("title")):
            prompt = screen_context.format_prompt_with_screen_context(
                highlighted_text=text,
                screen_context=sc,
                mode_prompt=prompt
            )

        # --- Per-mode token budget and temperature (from mode spec, fallback to tier defaults) ---
        num_ctx = spec.get("num_ctx", 2048)
        max_tokens = mode_spec.get("max_tokens", spec.get("max_tokens", 512))
        temperature = mode_spec.get("temperature", 0.15)

        options = {
            "num_predict": max_tokens,
            "num_ctx": num_ctx,
            "temperature": temperature,
            "top_p": 0.90,
            "top_k": 40,
            "repeat_penalty": 1.1
        }

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": True,
            "system": system_prompt,
            "options": options,
            "keep_alive": keep_alive
        }

        try:
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{ollama_url}/api/generate",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                for line in response:
                    if abort_event.is_set() or not self.is_alive:
                        return
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8', errors='ignore'))
                            token = chunk.get("response", "")
                            if token and self.is_alive:
                                self.event_queue.put(("token", token))
                        except Exception:
                            continue

            if not abort_event.is_set() and self.is_alive:
                self.event_queue.put(("finished", None))

        except urllib.error.HTTPError as he:
            err_msg = f"HTTP {he.code}"
            try:
                raw_body = he.read().decode('utf-8', errors='ignore')
                body_json = json.loads(raw_body)
                if "error" in body_json:
                    err_msg = body_json["error"]
            except Exception:
                pass
            if not abort_event.is_set() and self.is_alive:
                self.event_queue.put(("error", f"Ollama Error: {err_msg}"))
        except urllib.error.URLError as ue:
            if not abort_event.is_set() and self.is_alive:
                self.event_queue.put(("error", f"Connection Error: {ue.reason}. Ensure Ollama is running (`ollama serve`)."))
        except Exception as e:
            if not abort_event.is_set() and self.is_alive:
                self.event_queue.put(("error", f"Execution Error: {str(e)}"))

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    # Prevent multiple conflicting background processes
    MUTEX_NAME = "watthis_singleton_mutex_v1"
    try:
        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183
        mutex_handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            print("[INFO] wat-this is already running in the Windows Status Bar (System Tray).")
            sys.exit(0)
    except Exception:
        pass

    try:
        app = WatThisApp()
        app.run()
    except Exception as exc:
        import traceback
        err_msg = traceback.format_exc()
        print(f"[FATAL CRASH] {err_msg}")
        try:
            log_file = os.path.join(config_manager.BASE_DIR, "wat_this_error.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n--- Crash at {time.ctime()} ---\n{err_msg}\n")
        except Exception:
            pass
        sys.exit(1)
