"""
wat-this: Ambient Desktop Intelligence HUD.
Zero-DLL, signed Tkinter floating copilot with multi-action hotkeys,
interactive follow-up chat, history logging, and native offline Windows TTS.
"""
import sys
import os
import time
import json
import ctypes
import threading
import urllib.request
import urllib.parse
import pyperclip
import keyboard
import tkinter as tk

import config_manager
import search_helper
import history_manager
import tts_helper

MODE_COLORS = {
    "explain": "#89B4FA",    # Blue
    "fix": "#A6E3A1",        # Green
    "simplify": "#F9E2AF",   # Peach/Yellow
    "docstring": "#CBA6F7"   # Mauve/Purple
}

class WatThisApp:
    def __init__(self):
        self.config = config_manager.load_config()
        self.tier_key, self.tier_spec = config_manager.get_active_tier()
        
        # State tracking
        self.current_mode = "explain"
        self.active_abort_event = None
        self.is_thinking = False
        self.accumulated_text = ""
        self.current_snippet = ""
        self.conversation_history = []
        self.status_index = 0
        self.status_states = ["Gathering context.", "Gathering context..", "Gathering context..."]
        self.linger_timer_id = None
        self.is_visible = False
        self.chat_expanded = False
        self.start_time = None

        self.init_ui()
        self.register_all_hotkeys()

        print(f"[DEPLOYED] wat-this Active. Tier: {self.tier_spec.get('name').upper()} ({self.tier_spec.get('ram_target')}).")
        print("Registered Hotkeys:")
        for m_key, m_spec in config_manager.get_modes().items():
            print(f"  - [{m_spec['name']}]: {m_spec['hotkey'].upper()}")
        print(f"  - [Text-to-Speech]: {self.config.get('tts_hotkey', 'ctrl+alt+s').upper()}")

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
        self.root.bind("<Tab>", lambda e: self.toggle_follow_up(True))

        # Main Container
        self.container = tk.Frame(self.root, bg="#181825", bd=1, relief="solid", highlightbackground="#313244", highlightthickness=1)
        self.container.pack(fill="both", expand=True, padx=0, pady=0)

        # Header Frame
        self.header_frame = tk.Frame(self.container, bg="#181825")
        self.header_frame.pack(fill="x", padx=16, pady=(12, 6))

        self.title_lbl = tk.Label(
            self.header_frame,
            text="WAT-THIS",
            font=("Segoe UI Variable Display", 9, "bold"),
            bg="#181825",
            fg="#A6ADC8"
        )
        self.title_lbl.pack(side="left")

        # Mode Badge
        self.mode_badge_lbl = tk.Label(
            self.header_frame,
            text=" EXPLAIN ",
            font=("Segoe UI", 8, "bold"),
            bg="#1E1E2E",
            fg="#89B4FA",
            bd=1,
            relief="solid",
            highlightbackground="#89B4FA",
            highlightthickness=1
        )
        self.mode_badge_lbl.pack(side="left", padx=(8, 4))

        # Tier Badge
        tier_name = self.tier_spec.get("name", "NORMAL").upper()
        tier_ram = self.tier_spec.get("ram_target", "")
        self.tier_badge_lbl = tk.Label(
            self.header_frame,
            text=f" {tier_name} ({tier_ram}) ",
            font=("Segoe UI", 8, "bold"),
            bg="#1E1E2E",
            fg="#6C7086",
            bd=1,
            relief="solid",
            highlightbackground="#45475A",
            highlightthickness=1
        )
        self.tier_badge_lbl.pack(side="left", padx=4)

        # TTS Audio Button
        self.tts_btn = tk.Label(
            self.header_frame,
            text="🔊",
            font=("Segoe UI", 10),
            bg="#181825",
            fg="#A6ADC8",
            cursor="hand2"
        )
        self.tts_btn.pack(side="right", padx=(8, 0))
        self.tts_btn.bind("<Button-1>", lambda e: self.speak_current_content())

        self.hint_lbl = tk.Label(
            self.header_frame,
            text="Esc to close",
            font=("Segoe UI", 8),
            bg="#181825",
            fg="#6C7086"
        )
        self.hint_lbl.pack(side="right")

        # Content Text Area
        self.content_lbl = tk.Label(
            self.container,
            text="",
            font=("Segoe UI Variable Text", 10),
            bg="#181825",
            fg="#CDD6F4",
            wraplength=440,
            justify="left",
            anchor="w"
        )
        self.content_lbl.pack(fill="both", expand=True, padx=16, pady=(4, 10))

        # Follow-Up Expand Frame
        self.follow_up_frame = tk.Frame(self.container, bg="#11111B", bd=1, relief="solid", highlightbackground="#313244", highlightthickness=1)
        self.follow_up_frame.pack(fill="x", padx=14, pady=(0, 10))

        self.expand_prompt_lbl = tk.Label(
            self.follow_up_frame,
            text="💬  Press Tab or click to ask follow-up...",
            font=("Segoe UI", 8),
            bg="#11111B",
            fg="#6C7086",
            cursor="hand2",
            pady=4
        )
        self.expand_prompt_lbl.pack(fill="x")
        self.expand_prompt_lbl.bind("<Button-1>", lambda e: self.toggle_follow_up(True))

        # Input Box for Chat Follow-up (hidden until expanded)
        self.input_box_frame = tk.Frame(self.follow_up_frame, bg="#11111B")
        
        self.chat_entry = tk.Entry(
            self.input_box_frame,
            font=("Segoe UI", 9),
            bg="#1E1E2E",
            fg="#CDD6F4",
            insertbackground="#89B4FA",
            bd=0,
            highlightbackground="#45475A",
            highlightthickness=1,
            relief="flat"
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(6, 6), pady=6, ipady=3)
        self.chat_entry.bind("<Return>", lambda e: self.submit_follow_up())
        self.chat_entry.bind("<Escape>", lambda e: self.hide_hud())

        self.chat_send_btn = tk.Button(
            self.input_box_frame,
            text="Ask",
            font=("Segoe UI", 8, "bold"),
            bg="#89B4FA",
            fg="#11111B",
            activebackground="#B4BEFE",
            bd=0,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.submit_follow_up
        )
        self.chat_send_btn.pack(side="right", padx=(0, 6), pady=6)

        self.fixed_width = 480

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

    def on_hotkey_triggered(self, mode="explain"):
        self.root.after(0, lambda: self.handle_hotkey(mode))

    def on_tts_triggered(self):
        self.root.after(0, self.speak_current_content)

    def speak_current_content(self):
        if self.accumulated_text:
            tts_helper.speak_async(self.accumulated_text)

    def toggle_follow_up(self, expand=True):
        if expand and not self.chat_expanded:
            self.chat_expanded = True
            self.expand_prompt_lbl.pack_forget()
            self.input_box_frame.pack(fill="x")
            self.chat_entry.focus_set()
            # Stop auto-dismiss while user is typing
            if self.linger_timer_id:
                self.root.after_cancel(self.linger_timer_id)
                self.linger_timer_id = None
            self.follow_mouse()

    def simulate_copy(self):
        try:
            VK_CONTROL = 0x11
            KEYEVENTF_KEYUP = 0x0002
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
            ctypes.windll.user32.keybd_event(ord('C'), 0, 0, 0)
            ctypes.windll.user32.keybd_event(ord('C'), 0, KEYEVENTF_KEYUP, 0)
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.08)
        except Exception:
            pass

    def handle_hotkey(self, mode="explain"):
        tts_helper.stop_speech()
        self.current_mode = mode

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

        self.current_snippet = text
        self.conversation_history = []
        self.start_time = time.time()

        # Reload active tier
        self.tier_key, self.tier_spec = config_manager.get_active_tier()
        tier_name = self.tier_spec.get("name", "NORMAL").upper()
        tier_ram = self.tier_spec.get("ram_target", "")
        self.tier_badge_lbl.configure(text=f" {tier_name} ({tier_ram}) ")

        # Mode styling
        mode_spec = config_manager.get_mode_spec(mode)
        mode_color = MODE_COLORS.get(mode, "#89B4FA")
        self.mode_badge_lbl.configure(
            text=f" {mode_spec.get('name', mode).upper()} ",
            fg=mode_color,
            highlightbackground=mode_color
        )

        # Reset follow-up state
        self.chat_expanded = False
        self.input_box_frame.pack_forget()
        self.expand_prompt_lbl.pack(fill="x")
        self.chat_entry.delete(0, tk.END)

        # Cancel previous tasks
        if self.active_abort_event:
            self.active_abort_event.set()
        self.active_abort_event = threading.Event()

        if self.linger_timer_id:
            self.root.after_cancel(self.linger_timer_id)
            self.linger_timer_id = None

        self.is_thinking = True
        self.accumulated_text = ""
        self.status_index = 0

        self.content_lbl.configure(text=self.status_states[0], fg=mode_color)
        self.container.configure(highlightbackground=mode_color)

        self.follow_mouse()
        self.root.deiconify()
        self.root.attributes("-alpha", 0.98)
        self.is_visible = True

        self.update_status_animation()
        self.track_mouse_continuous()

        # Launch AI Pipeline
        threading.Thread(
            target=self.run_ai_pipeline,
            args=(text, mode, self.active_abort_event),
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

            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()

            self.root.update_idletasks()
            win_w = max(self.fixed_width, self.root.winfo_reqwidth())
            win_h = self.root.winfo_reqheight()

            target_x = pt.x + 25
            target_y = pt.y + 25

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

        # Auto-TTS if enabled
        if self.config.get("tts_enabled", False):
            self.speak_current_content()

        # Linger timer unless user is interacting with chat
        if not self.chat_expanded:
            linger_ms = self.config.get("linger_duration_ms", 14000)
            self.linger_timer_id = self.root.after(linger_ms, self.hide_hud)

    def submit_follow_up(self):
        query = self.chat_entry.get().strip()
        if not query or self.is_thinking:
            return

        self.chat_entry.delete(0, tk.END)
        self.is_thinking = True
        self.content_lbl.configure(text=f"Q: {query}\n\nThinking...", fg="#89B4FA")
        
        # Build multi-turn context
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
            with urllib.request.urlopen(req, timeout=20) as response:
                first_token = True
                for line in response:
                    if abort_event.is_set():
                        return
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8', errors='ignore'))
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                if first_token:
                                    first_token = False
                                    self.root.after(0, lambda: self.reset_for_new_stream())
                                self.root.after(0, lambda t=token: self.append_streaming_token(t))
                        except Exception:
                            continue

            if not abort_event.is_set():
                self.root.after(0, self.on_stream_finished)

        except Exception as e:
            if not abort_event.is_set():
                self.root.after(0, lambda: self.on_system_error(f"Chat Error: {e}"))

    def reset_for_new_stream(self):
        self.is_thinking = False
        self.container.configure(highlightbackground="#313244")
        self.content_lbl.configure(fg="#CDD6F4")
        self.accumulated_text = ""

    def on_system_error(self, message):
        self.is_thinking = False
        self.container.configure(highlightbackground="#F38BA8")
        self.content_lbl.configure(text=message, fg="#F38BA8")
        self.root.update_idletasks()
        self.linger_timer_id = self.root.after(6000, self.hide_hud)

    def hide_hud(self):
        tts_helper.stop_speech()
        self.is_visible = False
        self.is_thinking = False
        self.chat_expanded = False
        self.root.attributes("-alpha", 0.0)
        self.root.withdraw()
        self.content_lbl.configure(text="")
        self.accumulated_text = ""

    def run_ai_pipeline(self, text, mode, abort_event):
        spec = self.tier_spec
        target_model = spec.get("model", "llama3.2:3b")
        allow_web = spec.get("web_search", True)
        keep_alive = spec.get("keep_alive", "5m")
        base_prompt = spec.get("system_prompt", "Explain what this is clearly.")
        
        mode_spec = config_manager.get_mode_spec(mode)
        mode_suffix = mode_spec.get("prompt_suffix", "")
        system_prompt = f"{base_prompt} Specific goal: {mode_suffix}"
        
        ollama_url = self.config.get("ollama_url", "http://localhost:11434").rstrip("/")

        code_indicators = ["try:", "def ", "import ", "response =", "return ", "class ", "const ", "function", "public static", "void"]
        is_code = any(indicator in text for indicator in code_indicators) or (len(text) > 20 and "  " in text and ("=" in text or "(" in text or "{" in text))

        web_context = ""
        # Web search only enabled for Explain mode if allowed
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

            with urllib.request.urlopen(req, timeout=14) as response:
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

        except urllib.error.URLError:
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
