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
# DESIGN SYSTEM TOKENS (Obsidian & Slate Theme)
# ---------------------------------------------------------------------------
COLOR_BG_DARK      = "#0D1117"  # Canvas
COLOR_CONTAINER    = "#161B22"  # Surface
COLOR_BORDER       = "#30363D"  # Structural border
COLOR_TEXT_MAIN    = "#F0F6FC"  # High-contrast text
COLOR_TEXT_SEC     = "#8B949E"  # Neutral text
COLOR_TEXT_DIM     = "#6E7681"  # Muted captions
COLOR_BLUE         = "#388BFD"  # Brand primary
COLOR_BLUE_BG      = "#0D203D"
COLOR_GREEN        = "#3FB950"  # Emerald green
COLOR_GREEN_BG     = "#122619"
COLOR_AMBER        = "#D29922"
COLOR_RED          = "#F85149"
COLOR_RED_BG       = "#281215"
COLOR_PURPLE       = "#A371F7"

MODE_COLORS = {
    "explain": COLOR_BLUE,
    "simplify": COLOR_AMBER,
    "fix": COLOR_GREEN,
    "docstring": COLOR_PURPLE
}

FONT_FAMILY = "Segoe UI"
FONT_HERO    = (FONT_FAMILY, 12, "bold")
FONT_TITLE   = (FONT_FAMILY, 10, "bold")
FONT_SECTION = (FONT_FAMILY, 10, "bold")
FONT_BODY    = (FONT_FAMILY, 9)
FONT_BOLD    = (FONT_FAMILY, 9, "bold")
FONT_SMALL   = (FONT_FAMILY, 8)
FONT_MICRO   = (FONT_FAMILY, 8, "bold")
FONT_CODE    = ("Consolas", 9)

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
        self.status_states = ["Gathering context.", "Gathering context..", "Gathering context..."]
        self.linger_timer_id = None
        self.gui_queue_timer_id = None
        self.hud_visible = False
        self.chat_expanded = False
        self.start_time = None
        self.chat_turns = 0
        self.anchor_x = 400
        self.anchor_y = 300
        self.fixed_width = 500
        self.tray_icon = None

        # Hidden root + Windows Status Bar (System Tray) Icon + Floating Cursor HUD
        self.init_app_environment()
        self.init_tray_icon()
        self.init_hud_overlay()
        self.process_gui_queue()
        self.register_all_hotkeys()
        self.start_win32_hotkey_listener()

        print(f"[STATUS BAR] wat-this Active in Windows Status Bar (System Tray). Tier: {self.tier_spec.get('name').upper()} ({self.tier_spec.get('ram_target')}).")
        print("Resident in Windows status bar. Press Ctrl+Alt+Space anytime to trigger HUD.")

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
                item("⚡  Trigger Copilot (Ctrl+Alt+Space)", lambda: self.event_queue.put(("hotkey", "explain"))),
                item("🔍  Fix & Bug Detector (Ctrl+Alt+F)", lambda: self.event_queue.put(("hotkey", "fix"))),
                item("📝  Simplify (ELI5) (Ctrl+Alt+T)", lambda: self.event_queue.put(("hotkey", "simplify"))),
                item("🔊  Listen (TTS Audio) (Ctrl+Alt+S)", lambda: self.event_queue.put(("tts", None))),
                pystray.Menu.SEPARATOR,
                item(f"Active Profile: {tier_name} ({tier_ram})", None, enabled=False),
                item("⚙️  Setup & Settings", lambda: self.open_setup()),
                pystray.Menu.SEPARATOR,
                item("✕  Exit wat-this", lambda: self.quit_app())
            )

            self.tray_icon = pystray.Icon(
                "wat-this",
                tray_img,
                f"wat-this • Ambient Copilot ({tier_name})",
                menu
            )
            self.tray_icon.default_action = lambda: self.event_queue.put(("hotkey", "explain"))
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

    def quit_app(self):
        self.is_alive = False
        if getattr(self, "active_abort_event", None):
            self.active_abort_event.set()
        tts_helper.stop_speech()
        self.stop_hotkeys.set()
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
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        if getattr(self, "tray_icon", None):
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

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

        # Main HUD Container
        self.container = tk.Frame(self.hud, bg=COLOR_CONTAINER, bd=1, relief="solid", highlightbackground=COLOR_BORDER, highlightthickness=1)
        self.container.pack(fill="both", expand=True, padx=0, pady=0)

        # Header Frame
        self.header_frame = tk.Frame(self.container, bg=COLOR_CONTAINER)
        self.header_frame.pack(fill="x", padx=16, pady=(12, 6))

        self.title_lbl = tk.Label(
            self.header_frame, text="WAT-THIS", font=FONT_TITLE,
            bg=COLOR_CONTAINER, fg=COLOR_TEXT_SEC
        )
        self.title_lbl.pack(side="left")

        # Mode Badge
        self.mode_badge_lbl = tk.Label(
            self.header_frame, text=" EXPLAIN ", font=FONT_MICRO,
            bg=COLOR_BG_DARK, fg=COLOR_BLUE, bd=1, relief="solid",
            highlightbackground=COLOR_BLUE, highlightthickness=1, padx=4, pady=1
        )
        self.mode_badge_lbl.pack(side="left", padx=(8, 4))

        # Tier Badge
        tier_name = self.tier_spec.get("name", "NORMAL").upper()
        tier_ram = self.tier_spec.get("ram_target", "")
        self.tier_badge_lbl = tk.Label(
            self.header_frame, text=f" {tier_name} ({tier_ram}) ", font=FONT_MICRO,
            bg=COLOR_BG_DARK, fg=COLOR_TEXT_DIM, bd=1, relief="solid",
            highlightbackground=COLOR_BORDER, highlightthickness=1, padx=4, pady=1
        )
        self.tier_badge_lbl.pack(side="left", padx=4)

        # TTS Audio Button
        self.tts_btn = tk.Label(
            self.header_frame, text="🔊", font=FONT_TITLE,
            bg=COLOR_CONTAINER, fg=COLOR_TEXT_SEC if config_manager.is_tts_allowed(self.tier_key) else "#484F58",
            cursor="hand2"
        )
        self.tts_btn.pack(side="right", padx=(8, 0))
        self.tts_btn.bind("<Button-1>", lambda e: self.speak_current_content())

        self.hint_lbl = tk.Label(
            self.header_frame, text="Esc to close", font=FONT_BODY,
            bg=COLOR_CONTAINER, fg=COLOR_TEXT_DIM
        )
        self.hint_lbl.pack(side="right")

        # Content Text Area
        self.content_lbl = tk.Label(
            self.container, text="", font=FONT_BODY,
            bg=COLOR_CONTAINER, fg=COLOR_TEXT_MAIN, wraplength=460,
            justify="left", anchor="w"
        )
        self.content_lbl.pack(fill="both", expand=True, padx=16, pady=(4, 12))

        # Follow-Up Expand Frame
        self.follow_up_frame = tk.Frame(self.container, bg=COLOR_BG_DARK, bd=1, relief="solid", highlightbackground=COLOR_BORDER, highlightthickness=1)
        self.follow_up_frame.pack(fill="x", padx=14, pady=(0, 10))

        self.expand_prompt_lbl = tk.Label(
            self.follow_up_frame, text="💬  Press Tab or click to ask follow-up...",
            font=FONT_SMALL, bg=COLOR_BG_DARK, fg=COLOR_TEXT_SEC, cursor="hand2", pady=4
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
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(6, 6), pady=6, ipady=3)
        self.chat_entry.bind("<Return>", lambda e: self.submit_follow_up())
        self.chat_entry.bind("<Escape>", lambda e: self.hide_hud())

        self.chat_send_btn = tk.Button(
            self.input_box_frame, text="Ask", font=FONT_MICRO,
            bg=COLOR_BLUE, fg="#FFFFFF", activebackground="#2563EB", activeforeground="#FFFFFF",
            bd=0, padx=10, pady=3, cursor="hand2", command=self.submit_follow_up
        )
        self.chat_send_btn.pack(side="right", padx=(0, 6), pady=6)

        self.fixed_width = 500

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
                    self.speak_current_content()
                elif msg_type == "token":
                    self.append_streaming_token(data)
                elif msg_type == "finished":
                    self.on_stream_finished()
                elif msg_type == "error":
                    self.on_system_error(data)
                elif msg_type == "reset_chat":
                    self.reset_for_new_stream()
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

        # Reload active tier
        self.tier_key, self.tier_spec = config_manager.get_active_tier()
        tier_name = self.tier_spec.get("name", "NORMAL").upper()
        tier_ram = self.tier_spec.get("ram_target", "")
        self.tier_badge_lbl.configure(text=f" {tier_name} ({tier_ram}) ")
        self.update_tray_tooltip()

        # Update TTS button appearance
        tts_ok = config_manager.is_tts_allowed(self.tier_key)
        self.tts_btn.configure(fg=COLOR_TEXT_SEC if tts_ok else "#484F58")

        # ----------------------------------------------------
        # TIER LEVEL FEATURE GATING ENFORCEMENT
        # ----------------------------------------------------
        if not config_manager.is_mode_allowed_in_tier(mode, self.tier_key):
            mode_spec = config_manager.get_mode_spec(mode)
            req_tier = mode_spec.get("required_tier", "normal").upper()

            self.mode_badge_lbl.configure(
                text=" 🔒 TIER LOCKED ",
                fg=COLOR_RED,
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
            self.follow_up_frame.pack_forget()
            self.update_hud_geometry()
            self.hud.deiconify()
            self.hud.attributes("-alpha", 0.98)
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
        self.mode_badge_lbl.configure(
            text=f" {mode_spec.get('name', mode).upper()} ",
            fg=mode_color,
            highlightbackground=mode_color
        )

        # If user pressed hotkey with NO text highlighted and empty clipboard:
        # DO NOT ABORT! Open the HUD and offer an interactive prompt!
        if not text:
            self.current_snippet = ""
            self.conversation_history = []
            self.chat_turns = 0
            self.is_thinking = False
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
            self.hud.attributes("-alpha", 0.98)
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

        # Configure follow-up frame visibility based on tier
        self.chat_expanded = False
        self.input_box_frame.pack_forget()
        self.chat_entry.delete(0, tk.END)

        if config_manager.is_interactive_chat_allowed(self.tier_key):
            self.follow_up_frame.pack(fill="x", padx=14, pady=(0, 10))
            self.expand_prompt_lbl.configure(
                text="💬  Press Tab or click to ask follow-up...",
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

        self.content_lbl.configure(text=self.status_states[0], fg=mode_color)
        self.container.configure(highlightbackground=mode_color)

        self.update_hud_geometry()
        self.hud.deiconify()
        self.hud.attributes("-alpha", 0.98)
        self.hud_visible = True

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
                self.content_lbl.configure(text=self.status_states[self.status_index % len(self.status_states)])
                self.status_index += 1
                self.update_hud_geometry()
                self.root.after(300, self.update_status_animation)
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

            win_w = getattr(self, "fixed_width", 500)
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
                self.container.configure(highlightbackground=COLOR_BORDER)
                self.content_lbl.configure(fg=COLOR_TEXT_MAIN)
                self.accumulated_text = ""

            self.accumulated_text += token
            self.content_lbl.configure(text=self.accumulated_text)
            self.update_hud_geometry()
        except Exception:
            pass

    def on_stream_finished(self):
        try:
            if not self.root.winfo_exists():
                return
            self.is_streaming = False
            self.update_hud_geometry()
            elapsed = time.time() - self.start_time if self.start_time else None
            target_model = self.tier_spec.get("model", "local-ai")

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
        self.content_lbl.configure(text=f"Q: {query}\n\nThinking...", fg=COLOR_BLUE)

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
        ollama_url = self.config.get("ollama_url", "http://localhost:11434").rstrip("/")

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": True,
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

        except Exception as e:
            if not abort_event.is_set() and self.is_alive:
                self.event_queue.put(("error", f"Chat Error: {e}"))

    def reset_for_new_stream(self):
        self.is_thinking = False
        self.container.configure(highlightbackground=COLOR_BORDER)
        self.content_lbl.configure(fg=COLOR_TEXT_MAIN)
        self.accumulated_text = ""
        self.update_hud_geometry()

    def on_system_error(self, message):
        self.is_thinking = False
        self.is_streaming = False
        self.container.configure(highlightbackground=COLOR_RED)
        self.content_lbl.configure(text=message, fg=COLOR_RED)
        self.update_hud_geometry()
        self.linger_timer_id = self.root.after(6000, self.hide_hud)

    def hide_hud(self):
        tts_helper.stop_speech()
        self.hud_visible = False
        self.is_thinking = False
        self.chat_expanded = False
        self.hud.attributes("-alpha", 0.0)
        self.hud.withdraw()
        self.content_lbl.configure(text="")
        self.accumulated_text = ""

    def run_ai_pipeline(self, text, mode, abort_event):
        spec = self.tier_spec
        target_model = spec.get("model", "llama3.2:3b")
        allow_web = config_manager.is_web_search_allowed(self.tier_key)
        keep_alive = spec.get("keep_alive", "5m")
        base_prompt = spec.get("system_prompt", "Explain what this is clearly.")
        
        mode_spec = config_manager.get_mode_spec(mode)
        mode_suffix = mode_spec.get("prompt_suffix", "")
        system_prompt = f"{base_prompt} Specific goal: {mode_suffix}"
        
        ollama_url = self.config.get("ollama_url", "http://localhost:11434").rstrip("/")

        code_indicators = ["try:", "def ", "import ", "response =", "return ", "class ", "const ", "function", "public static", "void"]
        is_code = any(indicator in text for indicator in code_indicators) or (len(text) > 20 and "  " in text and ("=" in text or "(" in text or "{" in text))

        web_context = ""
        # Web search only enabled for Explain mode if allowed in this tier
        if mode == "explain" and allow_web and not is_code and not abort_event.is_set():
            results = search_helper.search_duckduckgo(text, max_results=2)
            if results:
                web_context = "\n".join(results)

        if abort_event.is_set():
            return

        prompt = f"Target text:\n{text}"
        if web_context:
            prompt = f"Live Context:\n{web_context}\n\nTarget text:\n{text}"

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": True,
            "system": system_prompt,
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

        except urllib.error.URLError:
            if not abort_event.is_set() and self.is_alive:
                self.event_queue.put(("error", "Engine Offline: Ensure Ollama is running (`ollama serve`)."))
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
