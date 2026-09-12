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

# Ensure Windows console output handles Unicode safely without crash
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Set explicit Windows AppUserModelID
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("watthis.ambientcopilot.app.1")
except Exception:
    pass

import config_manager
import search_helper
import history_manager
import tts_helper

# ---------------------------------------------------------------------------
# DESIGN SYSTEM TOKENS (Obsidian Frosted Glass Theme)
# ---------------------------------------------------------------------------
COLOR_BG_DARK      = "#0D1117"  # Canvas
COLOR_CONTAINER    = "#141A23"  # Translucent frosted surface
COLOR_SURFACE_ELEV = "#1C2330"  # Slightly elevated sub-card
COLOR_BORDER       = "#2A323D"  # Subtle structural border
COLOR_TEXT_MAIN    = "#F0F6FC"  # High-contrast text
COLOR_TEXT_SEC     = "#9BA3AF"  # Neutral text
COLOR_TEXT_DIM     = "#6B7280"  # Muted captions
COLOR_BLUE         = "#3B82F6"  # Brand sapphire primary
COLOR_BLUE_BG      = "#0F264A"
COLOR_GREEN        = "#10B981"  # Emerald green
COLOR_GREEN_BG     = "#0E2C1E"
COLOR_AMBER        = "#F59E0B"  # Warm amber
COLOR_RED          = "#EF4444"
COLOR_RED_BG       = "#2B1417"
COLOR_PURPLE       = "#8B5CF6"  # Violet

MODE_COLORS = {
    "explain": COLOR_BLUE,
    "simplify": COLOR_AMBER,
    "fix": COLOR_GREEN,
    "docstring": COLOR_PURPLE
}

MODE_ICONS = {
    "explain": "⚡",
    "simplify": "📝",
    "fix": "🔍",
    "docstring": "📜"
}

FONT_FAMILY  = "Segoe UI"
FONT_HERO    = (FONT_FAMILY, 12, "bold")
FONT_TITLE   = (FONT_FAMILY, 10, "bold")
FONT_SECTION = (FONT_FAMILY, 10, "bold")
FONT_BODY    = (FONT_FAMILY, 10)
FONT_BOLD    = (FONT_FAMILY, 10, "bold")
FONT_SMALL   = (FONT_FAMILY, 8)
FONT_MICRO   = (FONT_FAMILY, 8, "bold")
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
        v_round = ctypes.c_int(3)  # DWMWCP_ROUND
        v_backdrop = ctypes.c_int(3 if enable else 1)  # DWMSBT_TRANSIENTWINDOW (Acrylic) or NONE

        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(v_true), ctypes.sizeof(v_true))
        # DWMWA_WINDOW_CORNER_PREFERENCE = 33
        dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(v_round), ctypes.sizeof(v_round))
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

# Native Win32 Hotkey Mapping (MOD_CONTROL=0x0002 | MOD_ALT=0x0001 | MOD_NOREPEAT=0x4000 = 0x4003)
WIN32_HOTKEYS = {
    101: ("explain",   0x4003, 0x20),  # Ctrl + Alt + Space
    102: ("fix",       0x4003, 0x46),  # Ctrl + Alt + F
    103: ("simplify",  0x4003, 0x54),  # Ctrl + Alt + T
    104: ("docstring", 0x4003, 0x44),  # Ctrl + Alt + D
    105: ("tts",       0x4003, 0x53),  # Ctrl + Alt + S
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
        self._last_geom_time = 0.0
        self.active_hud_alpha = 0.93
        self.hud_visible = False
        self.chat_expanded = False
        self.start_time = None
        self.chat_turns = 0
        self.anchor_x = 400
        self.anchor_y = 300
        self.fixed_width = 520
        self.tray_icon = None
        self.hud_hwnd = None
        self.used_web_search = False

        # Hidden root + Windows Status Bar (System Tray) Icon + Floating Cursor HUD
        self.init_app_environment()
        self.init_tray_icon()
        self.init_hud_overlay()
        self.process_gui_queue()
        self.register_all_hotkeys()
        self.start_win32_hotkey_listener()

        # Proactive Ollama engine check/warmup in background
        threading.Thread(target=self._ensure_engine_warmup, daemon=True).start()

        print(f"[STATUS BAR] wat-this Active in Windows Status Bar (System Tray). Tier: {self.tier_spec.get('name').upper()} ({self.tier_spec.get('ram_target')}).")
        print("Resident in Windows status bar. Press Ctrl+Alt+Space anytime to trigger HUD.")

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
        self.root.withdraw()  # Hidden from taskbar; resident in Windows status bar

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
                item("⚡  Trigger Copilot (Ctrl+Alt+Space)", lambda *args: self.event_queue.put(("hotkey", "explain"))),
                item("🔍  Fix & Bug Detector (Ctrl+Alt+F)", lambda *args: self.event_queue.put(("hotkey", "fix"))),
                item("📝  Simplify (ELI5) (Ctrl+Alt+T)", lambda *args: self.event_queue.put(("hotkey", "simplify"))),
                item("🔊  Listen (TTS Audio) (Ctrl+Alt+S)", lambda *args: self.event_queue.put(("tts", None))),
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
            self.tray_icon.default_action = lambda *args: self.event_queue.put(("hotkey", "explain"))
            self.tray_icon.run_detached()
            print(f"[STATUS BAR] wat-this icon added to Windows Status Bar (System Tray).")
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

        # Unhook global keyboard hotkeys
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        # Stop pystray tray icon so it immediately disappears from Windows Status Bar
        if getattr(self, "tray_icon", None):
            try:
                self.tray_icon.stop()
            except Exception:
                pass

        # Scheduled clean tear-down of Tkinter on main GUI thread
        def _cleanup_tk():
            if getattr(self, "anim_timer_id", None):
                try:
                    self.root.after_cancel(self.anim_timer_id)
                except Exception:
                    pass
            if getattr(self, "linger_timer_id", None):
                try:
                    self.root.after_cancel(self.linger_timer_id)
                except Exception:
                    pass
            if getattr(self, "gui_queue_timer_id", None):
                try:
                    self.root.after_cancel(self.gui_queue_timer_id)
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

        # Arm a watchdog timer to unconditionally terminate the process and release the mutex
        def _watchdog_exit():
            time.sleep(0.2)
            os._exit(0)

        threading.Thread(target=_watchdog_exit, daemon=True).start()

        # If already called from the main thread, execute cleanup and exit immediately
        if threading.current_thread() is threading.main_thread():
            _cleanup_tk()
            os._exit(0)

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

        # Keyboard & Click dismiss handlers
        self.hud.bind("<Escape>", lambda e: self.hide_hud())
        self.hud.bind("<Tab>", lambda e: self.toggle_follow_up(True))

        # Main HUD Glass Container
        self.container = tk.Frame(
            self.hud, bg=COLOR_CONTAINER, bd=1, relief="solid",
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        self.container.pack(fill="both", expand=True, padx=0, pady=0)

        # Header Frame
        self.header_frame = tk.Frame(self.container, bg=COLOR_CONTAINER)
        self.header_frame.pack(fill="x", padx=16, pady=(12, 6))

        # Left Header: Logo, Mode Badge, Tier Badge
        left_hdr = tk.Frame(self.header_frame, bg=COLOR_CONTAINER)
        left_hdr.pack(side="left")

        self.title_lbl = tk.Label(
            left_hdr, text="WAT-THIS", font=FONT_MICRO,
            bg=COLOR_CONTAINER, fg=COLOR_TEXT_DIM
        )
        self.title_lbl.pack(side="left", padx=(0, 6))

        # Mode Badge
        self.mode_badge_lbl = tk.Label(
            left_hdr, text="⚡ EXPLAIN", font=FONT_MICRO,
            bg=COLOR_BLUE_BG, fg=COLOR_BLUE, bd=1, relief="solid",
            highlightbackground=COLOR_BLUE, highlightthickness=1, padx=6, pady=2
        )
        self.mode_badge_lbl.pack(side="left", padx=3)

        # Tier Badge
        tier_name = self.tier_spec.get("name", "NORMAL").upper()
        tier_ram = self.tier_spec.get("ram_target", "")
        self.tier_badge_lbl = tk.Label(
            left_hdr, text=f" {tier_name} • {tier_ram} ", font=FONT_MICRO,
            bg=COLOR_BG_DARK, fg=COLOR_TEXT_SEC, bd=1, relief="solid",
            highlightbackground=COLOR_BORDER, highlightthickness=1, padx=6, pady=2
        )
        self.tier_badge_lbl.pack(side="left", padx=3)

        # Right Header: Copy Button, TTS Audio Button, Dismiss Hint
        right_hdr = tk.Frame(self.header_frame, bg=COLOR_CONTAINER)
        right_hdr.pack(side="right")

        # Copy Action Button
        self.copy_btn = tk.Label(
            right_hdr, text="📋 Copy", font=FONT_SMALL,
            bg=COLOR_BG_DARK, fg=COLOR_TEXT_SEC, bd=1, relief="solid",
            highlightbackground=COLOR_BORDER, highlightthickness=1,
            cursor="hand2", padx=8, pady=2
        )
        self.copy_btn.pack(side="left", padx=(0, 6))
        self.copy_btn.bind("<Button-1>", lambda e: self.copy_to_clipboard())
        self.copy_btn.bind("<Enter>", lambda e: self.copy_btn.configure(bg=COLOR_SURFACE_ELEV, fg=COLOR_TEXT_MAIN))
        self.copy_btn.bind("<Leave>", lambda e: self.copy_btn.configure(bg=COLOR_BG_DARK, fg=COLOR_TEXT_SEC))

        # TTS Audio Button
        self.tts_btn = tk.Label(
            right_hdr, text="🔊 Listen", font=FONT_SMALL,
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_SEC if config_manager.is_tts_allowed(self.tier_key) else "#484F58",
            bd=1, relief="solid",
            highlightbackground=COLOR_BORDER, highlightthickness=1,
            cursor="hand2", padx=8, pady=2
        )
        self.tts_btn.pack(side="left", padx=(0, 6))
        self.tts_btn.bind("<Button-1>", lambda e: self.toggle_speech())
        self.tts_btn.bind("<Enter>", lambda e: self.tts_btn.configure(bg=COLOR_SURFACE_ELEV) if config_manager.is_tts_allowed(self.tier_key) else None)
        self.tts_btn.bind("<Leave>", lambda e: self.tts_btn.configure(bg=COLOR_BG_DARK) if config_manager.is_tts_allowed(self.tier_key) else None)

        self.hint_lbl = tk.Label(
            right_hdr, text="✕ Esc", font=FONT_MICRO,
            bg=COLOR_BG_DARK, fg=COLOR_TEXT_DIM, padx=6, pady=2,
            bd=1, relief="solid", highlightbackground=COLOR_BORDER, highlightthickness=1,
            cursor="hand2"
        )
        self.hint_lbl.pack(side="left")
        self.hint_lbl.bind("<Button-1>", lambda e: self.hide_hud())
        self.hint_lbl.bind("<Enter>", lambda e: self.hint_lbl.configure(bg=COLOR_SURFACE_ELEV, fg=COLOR_TEXT_MAIN))
        self.hint_lbl.bind("<Leave>", lambda e: self.hint_lbl.configure(bg=COLOR_BG_DARK, fg=COLOR_TEXT_DIM))

        # Activity & Progress Strip (Canvas 2px height)
        self.activity_canvas = tk.Canvas(
            self.container, height=2, bg=COLOR_CONTAINER, highlightthickness=0, bd=0
        )

        # Status Pill Frame (shown during thinking)
        self.status_frame = tk.Frame(self.container, bg=COLOR_CONTAINER)
        self.status_pill = tk.Label(
            self.status_frame, text="⚡ Initializing copilot...", font=FONT_SMALL,
            bg=COLOR_BG_DARK, fg=COLOR_BLUE, padx=8, pady=3, bd=1, relief="solid",
            highlightbackground=COLOR_BLUE, highlightthickness=1
        )
        self.status_pill.pack(anchor="w", padx=16, pady=(4, 2))

        # Content Text Area
        self.content_lbl = tk.Label(
            self.container, text="", font=FONT_BODY,
            bg=COLOR_CONTAINER, fg=COLOR_TEXT_MAIN, wraplength=480,
            justify="left", anchor="w"
        )
        self.content_lbl.pack(fill="both", expand=True, padx=16, pady=(4, 8))

        # Metadata Footer Row (Completed stats)
        self.meta_frame = tk.Frame(self.container, bg=COLOR_CONTAINER)
        self.meta_stats_lbl = tk.Label(
            self.meta_frame, text="", font=FONT_MICRO,
            bg=COLOR_CONTAINER, fg=COLOR_TEXT_DIM
        )
        self.meta_stats_lbl.pack(side="left", padx=16, pady=(0, 4))

        # Follow-Up Expand Frame
        self.follow_up_frame = tk.Frame(
            self.container, bg=COLOR_BG_DARK, bd=1, relief="solid",
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        self.follow_up_frame.pack(fill="x", padx=14, pady=(0, 10))

        self.expand_prompt_lbl = tk.Label(
            self.follow_up_frame, text="💬  Press Tab or click to ask follow-up...",
            font=FONT_SMALL, bg=COLOR_BG_DARK, fg=COLOR_TEXT_SEC, cursor="hand2", pady=5
        )
        self.expand_prompt_lbl.pack(fill="x")
        self.expand_prompt_lbl.bind("<Button-1>", lambda e: self.toggle_follow_up(True))

        # Input Box for Chat Follow-up (hidden until expanded)
        self.input_box_frame = tk.Frame(self.follow_up_frame, bg=COLOR_BG_DARK)

        self.chat_entry = tk.Entry(
            self.input_box_frame, font=FONT_BODY,
            bg=COLOR_CONTAINER, fg=COLOR_TEXT_MAIN, insertbackground=COLOR_BLUE,
            bd=0, highlightbackground=COLOR_BORDER, highlightthickness=1, relief="flat"
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(8, 6), pady=6, ipady=4)
        self.chat_entry.bind("<Return>", lambda e: self.submit_follow_up())
        self.chat_entry.bind("<Escape>", lambda e: self.hide_hud())

        self.chat_send_btn = tk.Button(
            self.input_box_frame, text="Ask", font=FONT_MICRO,
            bg=COLOR_BLUE, fg="#FFFFFF", activebackground="#2563EB", activeforeground="#FFFFFF",
            bd=0, padx=12, pady=4, cursor="hand2", command=self.submit_follow_up
        )
        self.chat_send_btn.pack(side="right", padx=(0, 6), pady=6)

        self.fixed_width = 520

        # Initialize HWND and apply native acrylic blur and drop shadow
        self.hud.update_idletasks()
        try:
            p_hwnd = ctypes.windll.user32.GetParent(self.hud.winfo_id())
            self.hud_hwnd = p_hwnd if p_hwnd else self.hud.winfo_id()
        except Exception:
            self.hud_hwnd = self.hud.winfo_id()

        self.apply_tier_visual_mode()

    def apply_tier_visual_mode(self):
        """
        Dynamically applies hardware-accelerated Acrylic blur, rounded corners,
        and transparency for Normal and Extreme tiers, while keeping Lite tier
        on an ultra-lightweight solid profile.
        """
        is_normal_or_above = self.tier_key in ("normal", "extreme")
        blur_pref = self.config.get("blur_enabled", True)

        if is_normal_or_above and blur_pref:
            apply_window_blur_and_shadow(self.hud_hwnd, enable=True)
            self.active_hud_alpha = float(self.config.get("hud_opacity", 0.93))
            self.container.configure(highlightbackground=COLOR_BORDER)
        else:
            apply_window_blur_and_shadow(self.hud_hwnd, enable=False)
            self.active_hud_alpha = 0.98
            self.container.configure(highlightbackground=COLOR_BORDER)

    def copy_to_clipboard(self):
        """Copies accumulated explanation to system clipboard with visual feedback."""
        if not self.accumulated_text:
            return
        try:
            pyperclip.copy(self.accumulated_text)
            self.copy_btn.configure(text="✓ Copied!", fg=COLOR_GREEN, highlightbackground=COLOR_GREEN)
            self.root.after(1600, self._restore_copy_btn)
        except Exception:
            pass

    def _restore_copy_btn(self):
        try:
            if self.root.winfo_exists():
                self.copy_btn.configure(text="📋 Copy", fg=COLOR_TEXT_SEC, highlightbackground=COLOR_BORDER)
        except Exception:
            pass

    def toggle_speech(self):
        """Toggles offline speech playback with immediate button feedback."""
        if not config_manager.is_tts_allowed(self.tier_key):
            self.hint_lbl.configure(text="TTS locked in Lite", fg=COLOR_RED)
            self.root.after(2500, lambda: self.hint_lbl.configure(text="Esc", fg=COLOR_TEXT_DIM))
            return

        if tts_helper.is_speaking():
            tts_helper.stop_speech()
            self.tts_btn.configure(text="🔊 Listen", fg=COLOR_TEXT_SEC, highlightbackground=COLOR_BORDER)
        else:
            if self.accumulated_text:
                tts_helper.speak_async(self.accumulated_text)
                self.tts_btn.configure(text="⏹ Stop", fg=COLOR_AMBER, highlightbackground=COLOR_AMBER)

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
                max_turns = self.tier_spec.get("max_chat_turns", 2)
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

        modes = config_manager.get_modes()
        for mode_key, mode_info in modes.items():
            hk = mode_info.get("hotkey")
            if hk:
                try:
                    keyboard.add_hotkey(hk, lambda m=mode_key: self.on_hotkey_triggered(m))
                except Exception as e:
                    print(f"[WARN] Failed to bind hotkey '{hk}' for {mode_key}: {e}")

        # Bind TTS hotkey
        tts_hk = self.config.get("tts_hotkey", "ctrl+alt+s")
        if tts_hk:
            try:
                keyboard.add_hotkey(tts_hk, self.on_tts_triggered)
            except Exception:
                pass

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

        # Dynamically sync TTS button with background speech synthesizer state
        if getattr(self, "tts_btn", None) and config_manager.is_tts_allowed(self.tier_key):
            try:
                speaking = tts_helper.is_speaking()
                curr_txt = self.tts_btn.cget("text")
                if speaking and curr_txt != "⏹ Stop":
                    self.tts_btn.configure(text="⏹ Stop", fg=COLOR_AMBER, highlightbackground=COLOR_AMBER)
                elif not speaking and curr_txt == "⏹ Stop":
                    self.tts_btn.configure(text="🔊 Listen", fg=COLOR_TEXT_SEC, highlightbackground=COLOR_BORDER)
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
        # Initialize thread message queue
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
                        mode_name = WIN32_HOTKEYS[hkid][0]
                        if mode_name == "tts":
                            self.event_queue.put(("tts", None))
                        else:
                            self.event_queue.put(("hotkey", mode_name))
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                time.sleep(0.01)

        for hkid in WIN32_HOTKEYS:
            user32.UnregisterHotKey(None, hkid)

    def on_hotkey_triggered(self, mode="explain"):
        self.event_queue.put(("hotkey", mode))

    def on_tts_triggered(self):
        self.event_queue.put(("tts", None))

    def speak_current_content(self):
        if not config_manager.is_tts_allowed(self.tier_key):
            self.hint_lbl.configure(text="TTS locked in Lite", fg=COLOR_RED)
            self.root.after(2500, lambda: self.hint_lbl.configure(text="Esc to close", fg=COLOR_TEXT_DIM))
            return

        if self.accumulated_text:
            tts_helper.speak_async(self.accumulated_text)

    def toggle_follow_up(self, expand=True):
        if not config_manager.is_interactive_chat_allowed(self.tier_key):
            return

        max_turns = self.tier_spec.get("max_chat_turns", 2)
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
        try:
            user32 = ctypes.windll.user32
            VK_CONTROL = 0x11
            VK_MENU    = 0x12  # Alt
            VK_SPACE   = 0x20
            KEYEVENTF_KEYUP = 0x0002

            # Explicitly release any physical modifier keys that could corrupt Ctrl+C into Ctrl+Alt+C
            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_SPACE, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(ord('F'), 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(ord('T'), 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(ord('D'), 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(ord('S'), 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.03)

            # Fire standard Ctrl + C
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(ord('C'), 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(ord('C'), 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.06)
        except Exception as e:
            print(f"[WARN] simulate_copy error: {e}")

    def handle_hotkey(self, mode="explain"):
        now = time.time()
        if now - getattr(self, "last_trigger_time", 0) < 0.35:
            return
        self.last_trigger_time = now

        tts_helper.stop_speech()
        self.current_mode = mode
        self.capture_mouse_position()

        # Reload active tier & dynamically adapt visual theme (Frosted Glass / Blur / Opacity)
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

        # ----------------------------------------------------
        # TIER LEVEL FEATURE GATING ENFORCEMENT
        # ----------------------------------------------------
        if not config_manager.is_mode_allowed_in_tier(mode, self.tier_key):
            mode_spec = config_manager.get_mode_spec(mode)
            req_tier = mode_spec.get("required_tier", "normal").upper()

            self.mode_badge_lbl.configure(
                text=" 🔒 LOCKED ",
                fg=COLOR_RED,
                bg=COLOR_RED_BG,
                highlightbackground=COLOR_RED
            )
            self.container.configure(highlightbackground=COLOR_RED)
            self.content_lbl.configure(
                text=(
                    f"Feature '{mode_spec.get('name')}' is locked in the {tier_name} profile.\n\n"
                    f"• Required Tier: {req_tier}\n"
                    f"• Active Profile: {tier_name} ({tier_ram})\n\n"
                    f"Open Settings to upgrade your model tier."
                ),
                fg=COLOR_RED
            )
            self.status_frame.pack_forget()
            self.meta_frame.pack_forget()
            self.stop_activity_animation()
            self.follow_up_frame.pack_forget()
            self.update_hud_geometry()
            self.hud.deiconify()
            self.hud.attributes("-alpha", self.active_hud_alpha)
            self.hud_visible = True

            if self.linger_timer_id:
                self.root.after_cancel(self.linger_timer_id)
            self.linger_timer_id = self.root.after(7000, self.hide_hud)
            return

        # Feature allowed: grab text and execute pipeline
        prev_clipboard = ""
        try:
            prev_clipboard = pyperclip.paste()
        except Exception:
            pass

        if self.config.get("auto_copy", True):
            self.simulate_copy()

        text = ""
        try:
            current_clipboard = pyperclip.paste()
            if current_clipboard and current_clipboard.strip():
                text = str(current_clipboard).strip()
            elif prev_clipboard and prev_clipboard.strip():
                text = str(prev_clipboard).strip()
        except Exception as e:
            print(f"[RECOVERY] Clipboard read error: {e}")

        mode_spec = config_manager.get_mode_spec(mode)
        mode_color = MODE_COLORS.get(mode, COLOR_BLUE)
        mode_icon = MODE_ICONS.get(mode, "⚡")

        self.mode_badge_lbl.configure(
            text=f" {mode_icon} {mode_spec.get('name', mode).upper()} ",
            fg=mode_color,
            bg=COLOR_BG_DARK,
            highlightbackground=mode_color
        )

        # If user pressed hotkey with NO text highlighted and empty clipboard:
        # Open HUD and provide interactive input prompt
        if not text:
            self.current_snippet = ""
            self.conversation_history = []
            self.chat_turns = 0
            self.is_thinking = False
            self.status_frame.pack_forget()
            self.meta_frame.pack_forget()
            self.stop_activity_animation()
            self.container.configure(highlightbackground=mode_color)
            self.content_lbl.configure(
                text=(
                    "⚡ Ambient Copilot is Ready & Listening\n\n"
                    "• Highlight text in any application and press Ctrl+Alt+Space\n"
                    "• Or type your question or code snippet in the box below:"
                ),
                fg=COLOR_TEXT_MAIN
            )
            self.follow_up_frame.pack(fill="x", padx=14, pady=(0, 10))
            self.expand_prompt_lbl.pack_forget()
            self.input_box_frame.pack(fill="x")
            self.chat_expanded = True
            self.update_hud_geometry()
            self.hud.deiconify()
            self.hud.attributes("-alpha", self.active_hud_alpha)
            self.hud_visible = True
            self.chat_entry.delete(0, tk.END)
            self.chat_entry.focus_set()
            if self.linger_timer_id:
                self.root.after_cancel(self.linger_timer_id)
            self.linger_timer_id = self.root.after(20000, self.hide_hud)
            return

        max_chars = self.config.get("max_clipboard_chars", 12000)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[Text truncated for memory safety]..."

        self.current_snippet = text
        self.conversation_history = []
        self.chat_turns = 0
        self.start_time = time.time()
        self.used_web_search = False

        # Configure follow-up frame visibility based on tier
        self.chat_expanded = False
        self.input_box_frame.pack_forget()
        self.chat_entry.delete(0, tk.END)

        if config_manager.is_interactive_chat_allowed(self.tier_key):
            self.follow_up_frame.pack(fill="x", padx=14, pady=(0, 10))
            max_turns = self.tier_spec.get("max_chat_turns", 2)
            self.expand_prompt_lbl.configure(
                text=f"💬  Press Tab or click to ask follow-up ({max_turns} remaining)...",
                fg=COLOR_TEXT_SEC,
                cursor="hand2"
            )
            self.expand_prompt_lbl.pack(fill="x")
        else:
            self.follow_up_frame.pack(fill="x", padx=14, pady=(0, 10))
            self.expand_prompt_lbl.configure(
                text="🔒 Follow-up chat unlocked in Normal & Extreme tiers",
                fg=COLOR_TEXT_DIM,
                cursor="arrow"
            )
            self.expand_prompt_lbl.pack(fill="x")

        # Cancel previous tasks
        if self.active_abort_event:
            self.active_abort_event.set()
        self.active_abort_event = threading.Event()

        if self.linger_timer_id:
            self.root.after_cancel(self.linger_timer_id)
            self.linger_timer_id = None

        self.is_thinking = True
        self.is_streaming = True
        self.accumulated_text = ""
        self.status_index = 0
        target_model = self.tier_spec.get("model", "llama3.2:3b")

        self.status_states = [
            f"⚡ Initializing {target_model}...",
            f"🔍 Analyzing snippet with {target_model}...",
            f"✦ Formulating concise insights...",
            f"✦ Streaming response..."
        ]

        self.meta_frame.pack_forget()
        self.meta_stats_lbl.configure(text="")
        self.content_lbl.configure(text="", fg=COLOR_TEXT_MAIN)
        self.status_pill.configure(
            text=self.status_states[0],
            fg=mode_color,
            highlightbackground=mode_color
        )
        self.status_frame.pack(fill="x")
        self.container.configure(highlightbackground=mode_color)

        self.update_hud_geometry()
        self.hud.deiconify()
        self.hud.attributes("-alpha", self.active_hud_alpha)
        self.hud_visible = True

        self.start_activity_animation(mode_color)
        self.update_status_animation()

        # Launch AI Pipeline
        threading.Thread(
            target=self.run_ai_pipeline,
            args=(text, mode, self.active_abort_event),
            daemon=True
        ).start()

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
        try:
            if not self.root.winfo_exists() or not self.hud.winfo_exists():
                return

            self.hud.update_idletasks()

            win_w = getattr(self, "fixed_width", 520)
            req_h = self.container.winfo_reqheight()
            win_h = max(110, req_h)

            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()

            # Dynamic max height limit leaving breathing room
            max_h = screen_h - 100
            win_h = min(win_h, max_h)

            target_x = getattr(self, "anchor_x", 400) + 20
            target_y = getattr(self, "anchor_y", 300) + 20

            # If expanding past right screen border, shift left
            if target_x + win_w > screen_w - 15:
                target_x = getattr(self, "anchor_x", 400) - win_w - 20

            # If expanding past bottom screen border (taskbar area), flip upwards above cursor
            if target_y + win_h > screen_h - 45:
                target_y = getattr(self, "anchor_y", 300) - win_h - 20

            # Hard clamp inside monitor bounds
            target_x = max(15, min(target_x, screen_w - win_w - 15))
            target_y = max(15, min(target_y, screen_h - win_h - 15))

            self.hud.geometry(f"{win_w}x{win_h}+{target_x}+{target_y}")
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
            # Remove streaming cursor
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

            # Linger timer unless user is interacting with chat
            if not self.chat_expanded:
                linger_ms = self.config.get("linger_duration_ms", 14000)
                self.linger_timer_id = self.root.after(linger_ms, self.hide_hud)
        except Exception:
            pass

    def submit_follow_up(self):
        query = self.chat_entry.get().strip()
        if not query or self.is_thinking:
            return

        self.chat_turns += 1
        self.chat_entry.delete(0, tk.END)
        self.is_thinking = True
        self.meta_frame.pack_forget()

        target_model = self.tier_spec.get("model", "llama3.2:3b")
        mode_color = MODE_COLORS.get(self.current_mode, COLOR_BLUE)

        self.status_states = [
            f"⚡ Processing follow-up turn {self.chat_turns}...",
            f"✦ Reasoning with {target_model}...",
            f"✦ Streaming response..."
        ]
        self.status_pill.configure(text=self.status_states[0], fg=mode_color, highlightbackground=mode_color)
        self.status_frame.pack(fill="x")
        self.start_activity_animation(mode_color)

        # If user opened HUD with empty clipboard and entered a question, execute as main query
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
        target_model = self.tier_spec.get("model", "llama3.2:3b")
        keep_alive = self.tier_spec.get("keep_alive", "5m")
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
            for cand in ["llama3.2:3b", "smollm2:1.7b", "llama3.2"]:
                if cand in installed:
                    target_model = cand
                    break
            else:
                target_model = installed[0]

        options = {
            "num_predict": 400,
            "temperature": 0.3,
            "top_p": 0.9
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
        self.content_lbl.configure(fg=COLOR_TEXT_MAIN)
        self.accumulated_text = ""
        self.update_hud_geometry()

    def on_system_error(self, message):
        self.is_thinking = False
        self.is_streaming = False
        self.stop_activity_animation()
        self.status_frame.pack_forget()
        self.container.configure(highlightbackground=COLOR_RED)
        self.content_lbl.configure(text=message, fg=COLOR_RED)
        self.update_hud_geometry()
        self.linger_timer_id = self.root.after(6000, self.hide_hud)

    def hide_hud(self):
        tts_helper.stop_speech()
        self.hud_visible = False
        self.is_thinking = False
        self.is_streaming = False
        self.chat_expanded = False
        self.stop_activity_animation()
        self.hud.attributes("-alpha", 0.0)
        self.hud.withdraw()
        self.content_lbl.configure(text="")
        self.accumulated_text = ""
        self.status_frame.pack_forget()
        self.meta_frame.pack_forget()
        self.tts_btn.configure(
            text="🔊 Listen",
            fg=COLOR_TEXT_SEC if config_manager.is_tts_allowed(self.tier_key) else "#484F58",
            highlightbackground=COLOR_BORDER
        )

    def run_ai_pipeline(self, text, mode, abort_event):
        spec = self.tier_spec
        target_model = spec.get("model", "llama3.2:3b")
        allow_web = config_manager.is_web_search_allowed(self.tier_key)
        keep_alive = spec.get("keep_alive", "5m")
        base_prompt = spec.get("system_prompt", "Explain what this is clearly.")
        
        mode_spec = config_manager.get_mode_spec(mode)
        mode_suffix = mode_spec.get("prompt_suffix", "")
        system_prompt = (
            f"{base_prompt} Specific goal: {mode_suffix} "
            f"Provide an immediate, direct, and concise explanation in plain English without conversational greetings, pleasantries, or introductory filler."
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
            for cand in ["llama3.2:3b", "smollm2:1.7b", "llama3.2"]:
                if cand in installed:
                    target_model = cand
                    break
            else:
                target_model = installed[0]

        code_indicators = ["try:", "def ", "import ", "response =", "return ", "class ", "const ", "function", "public static", "void"]
        is_code = any(indicator in text for indicator in code_indicators) or (len(text) > 20 and "  " in text and ("=" in text or "(" in text or "{" in text))

        web_context = ""
        self.used_web_search = False

        # Latency optimization: only trigger web search if query is a short concept (1-5 words) and strictly not code
        words = text.strip().split()
        is_short_concept = (len(words) <= 5 and not ("\n" in text) and not any(ch in text for ch in ("{", "}", ";", "(", ")", "=")))

        if mode == "explain" and allow_web and not is_code and is_short_concept and not abort_event.is_set():
            results = search_helper.search_duckduckgo(text, max_results=2)
            if results:
                web_context = "\n".join(results)
                self.used_web_search = True

        if abort_event.is_set():
            return

        prompt = f"Target text:\n{text}"
        if web_context:
            prompt = f"Live Context:\n{web_context}\n\nTarget text:\n{text}"

        max_tokens = 320 if mode in ("explain", "simplify") else (600 if mode == "fix" else 800)
        options = {
            "num_predict": max_tokens,
            "temperature": 0.2,
            "top_p": 0.9,
            "top_k": 40
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

            with urllib.request.urlopen(req, timeout=45) as response:
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
