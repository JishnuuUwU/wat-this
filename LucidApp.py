import sys
import json
import threading
import requests
import pyperclip
import keyboard
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QPoint
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QFont, QCursor, QAction
from ddgs import DDGS

OLLAMA_URL = "http://localhost:11434/api/generate"
TARGET_MODEL = "qwen2.5:1.5b"
MAX_CLIPBOARD_CHARS = 12000  # Defensive boundary: Protects context window and local memory

class AppSignals(QObject):
    hotkey_pressed = pyqtSignal()
    token_received = pyqtSignal(str)
    stream_finished = pyqtSignal()
    system_error = pyqtSignal(str)

class LucidApp(QWidget):
    def __init__(self):
        super().__init__()
        self.signals = AppSignals()
        
        # Resilient state management indicators
        self.status_states = ["Gathering context.", "Gathering context..", "Gathering context..."]
        self.status_index = 0
        self.is_thinking = False
        self.accumulated_text = ""
        
        self.init_ui()
        self.init_tray()
        self.init_isolated_animations()
        self.connect_signals()
        
        # Thread-safe global event registration
        keyboard.add_hotkey('ctrl+alt+space', lambda: self.signals.hotkey_pressed.emit())
        print("[DEPLOYED] Lucid Ultimate Engine active. Minimize terminal and use Ctrl+Alt+Space.")

    def init_ui(self):
        # Master OS-level window hierarchy constraints
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setWindowOpacity(0.0)
        self.setFixedWidth(440) 

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel("")
        self.label.setWordWrap(True)
        
        # Deeply legible geometric layout type-spec
        font = QFont("Segoe UI Variable Text", 11)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
        self.label.setFont(font)
        
        # Premium Slate & Lavender Muted Interface Theme
        self.base_style = """
            QLabel {
                color: #CDD6F4;
                background-color: rgba(30, 30, 46, 0.98);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
                padding: 22px 26px;
                line-height: 1.6;
            }
        """
        self.thinking_style = """
            QLabel {
                color: #89B4FA;
                background-color: rgba(24, 24, 37, 0.98);
                border: 1px solid rgba(137, 180, 250, 0.2);
                border-radius: 14px;
                padding: 22px 26px;
            }
        """
        self.label.setStyleSheet(self.base_style)
        layout.addWidget(self.label)
        self.setLayout(layout)

        # Synchronous UI Core Clocks
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_text)
        
        self.mouse_follow_timer = QTimer()
        self.mouse_follow_timer.timeout.connect(self.continuous_mouse_follow)

    def init_isolated_animations(self):
        # Entrance Fade Configuration
        self.ent_fade = QPropertyAnimation(self, b"windowOpacity")
        self.ent_fade.setDuration(180)
        self.ent_fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Exit Fade Configuration
        self.ex_fade = QPropertyAnimation(self, b"windowOpacity")
        self.ex_fade.setDuration(220)
        self.ex_fade.setEasingCurve(QEasingCurve.Type.InCubic)
        
        self.exit_group = QParallelAnimationGroup()
        self.exit_group.addAnimation(self.ex_fade)
        self.exit_group.finished.connect(self.final_hide)

    def init_tray(self):
        self.system_tray = QSystemTrayIcon(self)
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
        self.system_tray.setIcon(icon)
        
        tray_menu = QMenu()
        quit_action = QAction("Quit Lucid", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        
        self.system_tray.setContextMenu(tray_menu)
        self.system_tray.show()

    def connect_signals(self):
        self.signals.hotkey_pressed.connect(self.handle_hotkey)
        self.signals.token_received.connect(self.append_streaming_token)
        self.signals.stream_finished.connect(self.lock_and_linger)
        self.signals.system_error.connect(self.handle_graceful_failure)

    def continuous_mouse_follow(self):
        if not self.isVisible():
            return
        try:
            cursor_pos = QCursor.pos()
            active_screen = QApplication.screenAt(cursor_pos) or QApplication.primaryScreen()
            if not active_screen:
                return
                
            screen_geo = active_screen.geometry()
            
            # Position offset avoiding cursor arrow focus overlap
            target_x = cursor_pos.x() + 25
            target_y = cursor_pos.y() + 25
            
            # Defensively contain boundary box inside active display viewport
            if target_x + self.width() > screen_geo.x() + screen_geo.width():
                target_x = cursor_pos.x() - self.width() - 25
            if target_y + self.height() > screen_geo.y() + screen_geo.height():
                target_y = screen_geo.y() + screen_geo.height() - self.height() - 25
                
            self.move(target_x, target_y)
        except Exception as e:
            print(f"[RECOVERY] Mouse tracker anomaly intercepted: {e}")

    def handle_hotkey(self):
        try:
            raw_text = pyperclip.paste()
            if not raw_text:
                return
            text = str(raw_text).strip()
            if not text:
                return
        except Exception as e:
            print(f"[RECOVERY] Clipboard read failure: {e}")
            return

        # Defensive Boundary: Protect system from accidental massive payload copies
        if len(text) > MAX_CLIPBOARD_CHARS:
            print(f"[WARN] Inbound text truncated from {len(text)} to {MAX_CLIPBOARD_CHARS} chars.")
            text = text[:MAX_CLIPBOARD_CHARS] + "\n...[Text truncated for performance]..."

        # Hard state reset: safely interrupt any running exit routines or text blocks
        self.exit_group.stop()
        self.is_thinking = True
        self.status_index = 0
        self.accumulated_text = ""
        
        self.label.setStyleSheet(self.thinking_style)
        self.label.setText(self.status_states[0])
        self.adjustSize()
        
        # Engage tracking system loop instantly
        self.continuous_mouse_follow()
        self.mouse_follow_timer.start(16) 
        
        # Enforce structural foreground order inside OS Window management matrix
        self.show()
        self.raise_()
        self.activateWindow()
        
        self.ent_fade.setStartValue(self.windowOpacity())
        self.ent_fade.setEndValue(1.0)
        self.ent_fade.start()
        
        self.status_timer.start(300)
        
        threading.Thread(target=self.run_ai_pipeline, args=(text,), daemon=True).start()

    def update_status_text(self):
        if self.is_thinking:
            self.label.setText(self.status_states[self.status_index % len(self.status_states)])
            self.status_index += 1
            self.adjustSize()

    def append_streaming_token(self, token):
        if self.is_thinking:
            self.is_thinking = False
            self.status_timer.stop()
            self.label.setStyleSheet(self.base_style)
            self.label.setText("")

        self.accumulated_text += token
        self.label.setText(self.accumulated_text)
        self.adjustSize()

    def lock_and_linger(self):
        # Safe display window execution duration
        QTimer.singleShot(14000, self.start_exit_animation)

    def handle_graceful_failure(self, error_message):
        self.is_thinking = False
        self.status_timer.stop()
        self.label.setStyleSheet(self.base_style)
        self.label.setText(error_message)
        self.adjustSize()
        QTimer.singleShot(6000, self.start_exit_animation)

    def start_exit_animation(self):
        if self.isVisible() and self.exit_group.state() != QParallelAnimationGroup.State.Running:
            self.mouse_follow_timer.stop()
            self.ex_fade.setStartValue(self.windowOpacity())
            self.ex_fade.setEndValue(0.0)
            self.exit_group.start()

    def final_hide(self):
        self.hide()
        self.label.setText("")
        self.accumulated_text = ""

    def run_ai_pipeline(self, text):
        # Context Parsing Matrix: Bypass DDG overhead completely for technical code segments
        code_indicators = ["try:", "def ", "import ", "response =", "return ", "class ", "const ", "function", "public static", "void"]
        is_code = any(indicator in text for indicator in code_indicators) or (len(text) > 20 and "  " in text and ("=" in text or "(" in text or "{" in text))
        
        web_context = ""
        if not is_code:
            try:
                with DDGS() as ddgs:
                    results = [r['body'] for r in ddgs.text(text, max_results=2)]
                    if results:
                        web_context = "\n".join(results)
            except Exception as e:
                print(f"[RECOVERY] Network context scraper bypassed gracefully: {e}")

        prompt = f"Target text: {text}"
        if web_context:
            prompt = f"Live Context:\n{web_context}\n\nUsing this structural background, explain: {text}"

        payload = {
            "model": TARGET_MODEL,
            "prompt": prompt,
            "stream": True, 
            "system": (
                "You are an ultra-clear, calming, plain-English educator. Explain exactly what the target "
                "text or code means for an absolute beginner. Do not use complex jargon. If it is code, state "
                "what it does in plain words using an everyday real-world analogy. Keep your full response "
                "contained within 3 to 4 gentle, clear sentences."
            ),
            "keep_alive": 0
        }

        try:
            # Connect to engine with dedicated stream buffers
            response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=12)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        # Defensive byte decoding to handle erratic chunk endings safely
                        chunk = json.loads(line.decode('utf-8', errors='ignore'))
                        token = chunk.get("response", "")
                        if token:
                            self.signals.token_received.emit(token)
                    except json.JSONDecodeError:
                        continue # Skip fragmented lines comfortably
                        
            self.signals.stream_finished.emit()
            
        except requests.exceptions.Timeout:
            self.signals.system_error.emit("Connection Timeout: The local AI engine took too long to wake up.")
        except requests.exceptions.ConnectionError:
            self.signals.system_error.emit("Engine Offline: Ensure your local Ollama server is running (`ollama serve`).")
        except Exception as e:
            self.signals.system_error.emit(f"Execution Error: Could not compile request layers.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) 
    lucid = LucidApp()
    sys.exit(app.exec())