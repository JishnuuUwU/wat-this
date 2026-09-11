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
import tkinter as tk
from tkinter import font as tkfont

import config_manager
import search_helper

class WatThisApp:
    def __init__(self):
        self.config = config_manager.load_config()
        self.tier_key, self.tier_spec = config_manager.get_active_tier()
        
        # Concurrency & Abort Control
        self.active_abort_event = None
        self.is_thinking = False
        self.accumulated_text = ""
        self.status_index = 0
        self.status_states = ["Gathering context.", "Gathering context..", "Gathering context..."]
        self.linger_timer_id = None
        self.is_visible = False

        self.init_ui()
        self.register_hotkey()

        print(f"[DEPLOYED] wat-this Active. Tier: {self.tier_spec.get('name').upper()} ({self.tier_spec.get('ram_target')}).")
        print(f"Hotkey: {self.config.get('hotkey', 'ctrl+alt+space').upper()}. Running silently in background.")

    def init_ui(self):
        self.root = tk.Tk()
        self.root.title("wat-this")
        
        # Window Flags: Frameless, Always on top, hidden initially
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.0)
        self.root.configure(bg="#1E1E2E")
        self.root.withdraw()

        # Keyboard & Click dismiss handlers
        self.root.bind("<Escape>", lambda e: self.hide_hud())
        self.root.bind("<Button-1>", lambda e: self.hide_hud())

        # Main Container
        self.container = tk.Frame(self.root, bg="#181825", bd=1, relief="solid", highlightbackground="#313244", highlightthickness=1)
        self.container.pack(fill="both", expand=True, padx=0, pady=0)
        self.container.bind("<Button-1>", lambda e: self.hide_hud())

        # Header Frame
        self.header_frame = tk.Frame(self.container, bg="#181825")
        self.header_frame.pack(fill="x", padx=16, pady=(12, 6))
        self.header_frame.bind("<Button-1>", lambda e: self.hide_hud())

        self.title_lbl = tk.Label(
            self.header_frame,
            text="WAT-THIS",
            font=("Segoe UI Variable Display", 9, "bold"),
            bg="#181825",
            fg="#A6ADC8"
        )
        self.title_lbl.pack(side="left")
        self.title_lbl.bind("<Button-1>", lambda e: self.hide_hud())

        tier_name = self.tier_spec.get("name", "NORMAL").upper()
        tier_ram = self.tier_spec.get("ram_target", "")
        self.badge_lbl = tk.Label(
            self.header_frame,
            text=f" {tier_name} ({tier_ram}) ",
            font=("Segoe UI", 8, "bold"),
            bg="#1E1E2E",
            fg="#89B4FA",
            bd=1,
            relief="solid",
            highlightbackground="#89B4FA",
            highlightthickness=1
        )
        self.badge_lbl.pack(side="left", padx=8)
        self.badge_lbl.bind("<Button-1>", lambda e: self.hide_hud())

        self.hint_lbl = tk.Label(
            self.header_frame,
            text="Esc to close",
            font=("Segoe UI", 8),
            bg="#181825",
            fg="#6C7086"
        )
        self.hint_lbl.pack(side="right")
        self.hint_lbl.bind("<Button-1>", lambda e: self.hide_hud())

        # Content Text Area
        self.content_lbl = tk.Label(
            self.container,
            text="",
            font=("Segoe UI Variable Text", 10),
            bg="#181825",
            fg="#CDD6F4",
            wraplength=420,
            justify="left",
            anchor="w"
        )
        self.content_lbl.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.content_lbl.bind("<Button-1>", lambda e: self.hide_hud())

        self.fixed_width = 460

    def register_hotkey(self):
        hotkey = self.config.get("hotkey", "ctrl+alt+space")
        try:
            keyboard.clear_all_hotkeys()
            keyboard.add_hotkey(hotkey, self.on_hotkey_triggered)
        except Exception as e:
            print(f"[ERROR] Could not register hotkey '{hotkey}': {e}")

    def on_hotkey_triggered(self):
        # Schedule HUD activation on main Tkinter thread
        self.root.after(0, self.handle_hotkey)

    def simulate_copy(self):
        """Simulates Ctrl+C on Windows to copy selected text before reading clipboard."""
        try:
            VK_CONTROL = 0x11
            KEYEVENTF_KEYUP = 0x0002
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
            ctypes.windll.user32.keybd_event(ord('C'), 0, 0, 0)
            ctypes.windll.user32.keybd_event(ord('C'), 0, KEYEVENTF_KEYUP, 0)
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.08)
        except Exception as e:
            print(f"[WARN] Copy simulation bypassed: {e}")

    def handle_hotkey(self):
        if self.config.get("auto_copy", True):
            pyperclip.copy("")
            self.simulate_copy()

        try:
            raw_text = pyperclip.paste()
            if not raw_text:
                return
            text = str(raw_text).strip()
            if not text:
                return
        except Exception as e:
            print(f"[RECOVERY] Clipboard read error: {e}")
            return

        max_chars = self.config.get("max_clipboard_chars", 12000)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[Text truncated for memory safety]..."

        # Reload active tier in case config changed
        self.tier_key, self.tier_spec = config_manager.get_active_tier()
        tier_name = self.tier_spec.get("name", "NORMAL").upper()
        tier_ram = self.tier_spec.get("ram_target", "")
        self.badge_lbl.configure(text=f" {tier_name} ({tier_ram}) ")

        # Cancel any previous in-flight AI threads or timers
        if self.active_abort_event:
            self.active_abort_event.set()
        self.active_abort_event = threading.Event()

        if self.linger_timer_id:
            self.root.after_cancel(self.linger_timer_id)
            self.linger_timer_id = None

        self.is_thinking = True
        self.accumulated_text = ""
        self.status_index = 0

        self.content_lbl.configure(text=self.status_states[0], fg="#89B4FA")
        self.container.configure(highlightbackground="#89B4FA")

        # Position HUD near cursor & display
        self.follow_mouse()
        self.root.deiconify()
        self.root.attributes("-alpha", 0.98)
        self.is_visible = True

        self.update_status_animation()
        self.track_mouse_continuous()

        # Launch AI Pipeline in daemon thread
        threading.Thread(
            target=self.run_ai_pipeline,
            args=(text, self.active_abort_event),
            daemon=True
        ).start()

    def update_status_animation(self):
        if self.is_thinking and self.is_visible:
            self.content_lbl.configure(text=self.status_states[self.status_index % len(self.status_states)])
            self.status_index += 1
            self.root.after(300, self.update_status_animation)

    def follow_mouse(self):
        try:
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))

            # Screen bounds
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()

            # Dynamic dimensions
            self.root.update_idletasks()
            win_w = max(self.fixed_width, self.root.winfo_reqwidth())
            win_h = self.root.winfo_reqheight()

            target_x = pt.x + 25
            target_y = pt.y + 25

            # Collision clamping
            if target_x + win_w > screen_w - 10:
                target_x = pt.x - win_w - 25
            if target_y + win_h > screen_h - 10:
                target_y = pt.y - win_h - 25

            target_x = max(10, min(target_x, screen_w - win_w - 10))
            target_y = max(10, min(target_y, screen_h - win_h - 10))

            self.root.geometry(f"{win_w}x{win_h}+{target_x}+{target_y}")
        except Exception:
            pass

    def track_mouse_continuous(self):
        if self.is_visible and self.is_thinking:
            self.follow_mouse()
            self.root.after(16, self.track_mouse_continuous)

    def append_streaming_token(self, token):
        if self.is_thinking:
            self.is_thinking = False
            self.container.configure(highlightbackground="#313244")
            self.content_lbl.configure(fg="#CDD6F4")
            self.accumulated_text = ""

        self.accumulated_text += token
        self.content_lbl.configure(text=self.accumulated_text)
        self.root.update_idletasks()

    def on_stream_finished(self):
        linger_ms = self.config.get("linger_duration_ms", 14000)
        self.linger_timer_id = self.root.after(linger_ms, self.hide_hud)

    def on_system_error(self, message):
        self.is_thinking = False
        self.container.configure(highlightbackground="#F38BA8")
        self.content_lbl.configure(text=message, fg="#F38BA8")
        self.root.update_idletasks()
        self.linger_timer_id = self.root.after(6000, self.hide_hud)

    def hide_hud(self):
        self.is_visible = False
        self.is_thinking = False
        self.root.attributes("-alpha", 0.0)
        self.root.withdraw()
        self.content_lbl.configure(text="")
        self.accumulated_text = ""

    def run_ai_pipeline(self, text, abort_event):
        spec = self.tier_spec
        target_model = spec.get("model", "llama3.2:3b")
        allow_web = spec.get("web_search", True)
        keep_alive = spec.get("keep_alive", "5m")
        system_prompt = spec.get("system_prompt", "Explain what the target text or code means clearly.")
        ollama_url = self.config.get("ollama_url", "http://localhost:11434").rstrip("/")

        # Code detection heuristics
        code_indicators = ["try:", "def ", "import ", "response =", "return ", "class ", "const ", "function", "public static", "void"]
        is_code = any(indicator in text for indicator in code_indicators) or (len(text) > 20 and "  " in text and ("=" in text or "(" in text or "{" in text))

        web_context = ""
        if allow_web and not is_code and not abort_event.is_set():
            results = search_helper.search_duckduckgo(text, max_results=2)
            if results:
                web_context = "\n".join(results)

        if abort_event.is_set():
            return

        prompt = f"Target text: {text}"
        if web_context:
            prompt = f"Live Context:\n{web_context}\n\nTarget text: {text}"

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

            with urllib.request.urlopen(req, timeout=12) as response:
                for line in response:
                    if abort_event.is_set():
                        return
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8', errors='ignore'))
                            token = chunk.get("response", "")
                            if token:
                                self.root.after(0, lambda t=token: self.append_streaming_token(t))
                        except Exception:
                            continue

            if not abort_event.is_set():
                self.root.after(0, self.on_stream_finished)

        except urllib.error.URLError as e:
            if not abort_event.is_set():
                self.root.after(0, lambda: self.on_system_error("Engine Offline: Ensure Ollama is running (`ollama serve`)."))
        except Exception as e:
            if not abort_event.is_set():
                self.root.after(0, lambda: self.on_system_error(f"Execution Error: {str(e)}"))

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = WatThisApp()
    app.run()
