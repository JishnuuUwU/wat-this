"""
annotation_overlay.py - Hardware-Accelerated Zero-DLL Screen Annotation & Visual Guide Layer
Renders non-intrusive click-through visual guides, glowing spotlight regions,
step badges (❶, ❷), and anchored callout notes directly on the user's screen.
"""

import sys
import os
import ctypes
from ctypes import wintypes
import tkinter as tk

# Win32 Constants for Click-Through Layered Window
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

# Color Tokens
COLOR_TRANSPARENT = "#000001"
COLOR_SPOTLIGHT_CYAN   = "#388BFD"
COLOR_SPOTLIGHT_GREEN  = "#3FB950"
COLOR_SPOTLIGHT_PURPLE = "#A371F7"
COLOR_SPOTLIGHT_AMBER  = "#D29922"
COLOR_CARD_BG          = "#161B22"
COLOR_CARD_BORDER      = "#30363D"
COLOR_TEXT_MAIN        = "#F0F6FC"
COLOR_TEXT_MUTED       = "#8B949E"

FONT_BADGE = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 9, "bold")
FONT_DESC  = ("Segoe UI", 8)

class AnnotationOverlay:
    """
    Transparent, click-through overlay window spanning the monitor workspace.
    Draws non-intrusive spotlights, step badges, and guidance callout notes.
    """
    def __init__(self, master_tk):
        self.master = master_tk
        self.win = None
        self.canvas = None
        self.is_visible = False
        self.active_annotations = []
        self.auto_dismiss_job = None
        self.pulse_anim_job = None
        self.pulse_phase = 0.0
        self.pulse_box = None

    def _ensure_overlay_window(self):
        if self.win and self.win.winfo_exists():
            return

        self.win = tk.Toplevel(self.master)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)

        # Multi-monitor virtual screen bounds
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        vx = user32.GetSystemMetrics(76) # SM_XVIRTUALSCREEN
        vy = user32.GetSystemMetrics(77) # SM_YVIRTUALSCREEN
        vw = user32.GetSystemMetrics(78) # SM_CXVIRTUALSCREEN
        vh = user32.GetSystemMetrics(79) # SM_CYVIRTUALSCREEN

        self.screen_x = vx
        self.screen_y = vy
        self.screen_w = max(1920, vw)
        self.screen_h = max(1080, vh)

        self.win.geometry(f"{self.screen_w}x{self.screen_h}+{self.screen_x}+{self.screen_y}")
        self.win.configure(bg=COLOR_TRANSPARENT)

        # Windows Native Color-Keyed Transparency
        try:
            self.win.wm_attributes("-transparentcolor", COLOR_TRANSPARENT)
        except Exception:
            pass

        # Make overlay window completely click-through so user can interact with underlying desktop
        try:
            self.win.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.win.winfo_id()) or self.win.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            )
        except Exception:
            pass

        self.canvas = tk.Canvas(
            self.win, bg=COLOR_TRANSPARENT,
            highlightthickness=0, bd=0, cursor="arrow"
        )
        self.canvas.pack(fill="both", expand=True)

    def show_spotlight_and_callout(self, target_rect, title="Focus Target", text="Relevant code or element", step_num=1, color=COLOR_SPOTLIGHT_CYAN, duration_ms=16000):
        """
        Draws a glowing spotlight box around target_rect (left, top, right, bottom)
        with a numbered step pin (❶, ❷) and an anchored callout instruction card.
        """
        self._ensure_overlay_window()
        self.clear()

        l, t, r, b = target_rect
        # Ensure coordinates are relative to virtual screen
        canvas_x1 = l - self.screen_x
        canvas_y1 = t - self.screen_y
        canvas_x2 = r - self.screen_x
        canvas_y2 = b - self.screen_y

        # If width or height is negligible, provide default spotlight box around cursor or point
        if (canvas_x2 - canvas_x1) < 20:
            canvas_x1 -= 140
            canvas_x2 += 140
        if (canvas_y2 - canvas_y1) < 14:
            canvas_y1 -= 18
            canvas_y2 += 18

        # 1. Glowing Spotlight Bounding Box
        pad = 6
        x1, y1, x2, y2 = canvas_x1 - pad, canvas_y1 - pad, canvas_x2 + pad, canvas_y2 + pad

        # Outer soft glow halo (with tag for pulsing animation)
        self.canvas.create_rectangle(
            x1 - 3, y1 - 3, x2 + 3, y2 + 3,
            outline="#1B3A57", width=1.5, tags="spotlight_glow"
        )
        # Inner crisp spotlight border
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline=color, width=2.5, tags="spotlight_border"
        )

        # Corner aesthetic brackets
        cw = 12
        # Top-left corner bracket
        self.canvas.create_line(x1 - 1, y1 + cw, x1 - 1, y1 - 1, x1 + cw, y1 - 1, fill=color, width=3.5)
        # Top-right corner bracket
        self.canvas.create_line(x2 - cw, y1 - 1, x2 + 1, y1 - 1, x2 + 1, y1 + cw, fill=color, width=3.5)
        # Bottom-left corner bracket
        self.canvas.create_line(x1 - 1, y2 - cw, x1 - 1, y2 + 1, x1 + cw, y2 + 1, fill=color, width=3.5)
        # Bottom-right corner bracket
        self.canvas.create_line(x2 - cw, y2 + 1, x2 + 1, y2 + 1, x2 + 1, y2 - cw, fill=color, width=3.5)

        # 2. Step Badge Pin (e.g. ❶, ❷, ❸)
        step_icons = {1: "❶", 2: "❷", 3: "❸", 4: "❹", 5: "❺", 6: "❻", 7: "❼", 8: "❽", 9: "❾"}
        pin_icon = step_icons.get(step_num, f"[{step_num}]")

        pin_x = x1
        pin_y = max(24, y1 - 24)

        self.canvas.create_oval(pin_x - 14, pin_y - 14, pin_x + 14, pin_y + 14, fill=color, outline="#FFFFFF", width=1.5)
        self.canvas.create_text(pin_x, pin_y, text=pin_icon, fill="#FFFFFF", font=FONT_BADGE)

        # 3. Anchored Callout Instruction Card
        card_w = 320
        card_h = 68
        # Position card to top-right of spotlight, or below if near screen top
        card_x = min(self.screen_w - card_w - 20, max(20, x2 + 18))
        card_y = max(20, min(self.screen_h - card_h - 20, y1 - 8))

        if card_x + card_w > self.screen_w - 20:
            card_x = max(20, x1 - card_w - 18)

        # Connector line with dot
        mid_target_x = x1
        mid_target_y = y1
        self.canvas.create_line(pin_x + 14, pin_y, card_x, card_y + 20, fill=color, width=1.5, dash=(3, 2))
        self.canvas.create_oval(card_x - 3, card_y + 17, card_x + 3, card_y + 23, fill=color, outline=color)

        # Card body (Obsidian slate container)
        self.canvas.create_rectangle(
            card_x, card_y, card_x + card_w, card_y + card_h,
            fill=COLOR_CARD_BG, outline=COLOR_CARD_BORDER, width=1.5
        )
        # Left accent color strip
        self.canvas.create_rectangle(
            card_x, card_y, card_x + 4, card_y + card_h,
            fill=color, outline=color
        )

        # Title / Action Header
        disp_title = f"Step {step_num}: {title}" if title else f"Step {step_num}"
        self.canvas.create_text(
            card_x + 16, card_y + 16, text=disp_title,
            fill=COLOR_TEXT_MAIN, font=FONT_TITLE, anchor="w"
        )

        # Instruction / Description
        clean_text = " ".join(text.split())
        if len(clean_text) > 78:
            clean_text = clean_text[:75] + "..."
        self.canvas.create_text(
            card_x + 16, card_y + 40, text=clean_text,
            fill=COLOR_TEXT_MUTED, font=FONT_DESC, anchor="w"
        )

        # Deiconify and reveal overlay
        self.win.deiconify()
        self.is_visible = True

        # Start breathing radar pulse animation
        self.pulse_box = (x1, y1, x2, y2, color)
        self._start_spotlight_pulse()

        # Auto-dismiss timer
        if self.auto_dismiss_job:
            self.master.after_cancel(self.auto_dismiss_job)
        if duration_ms > 0:
            self.auto_dismiss_job = self.master.after(duration_ms, self.hide)

    def _start_spotlight_pulse(self):
        """Starts smooth breathing radar glow loop around target box."""
        if self.pulse_anim_job:
            try:
                self.master.after_cancel(self.pulse_anim_job)
            except Exception:
                pass
            self.pulse_anim_job = None
        self.pulse_phase = 0.0
        self._animate_pulse_tick()

    def _animate_pulse_tick(self):
        if not self.is_visible or not self.canvas or not self.pulse_box or not self.master.winfo_exists():
            return
        import math
        self.pulse_phase += 0.16
        offset = math.sin(self.pulse_phase) * 3.5
        x1, y1, x2, y2, color = self.pulse_box
        try:
            self.canvas.coords(
                "spotlight_glow",
                x1 - 3 - offset, y1 - 3 - offset,
                x2 + 3 + offset, y2 + 3 + offset
            )
            self.pulse_anim_job = self.master.after(45, self._animate_pulse_tick)
        except Exception:
            pass

    def show_cursor_spotlight(self, cursor_x, cursor_y, title="Target Element", text="Follow instructions in copilot window", step_num=1, color=COLOR_SPOTLIGHT_CYAN):
        """Spotlights the exact region surrounding the cursor position."""
        rect = (cursor_x - 120, cursor_y - 24, cursor_x + 120, cursor_y + 24)
        self.show_spotlight_and_callout(rect, title=title, text=text, step_num=step_num, color=color)

    def clear(self):
        """Clears all drawn annotations and cancels pulse animation."""
        if self.pulse_anim_job:
            try:
                self.master.after_cancel(self.pulse_anim_job)
            except Exception:
                pass
            self.pulse_anim_job = None
        self.pulse_box = None
        if self.canvas:
            self.canvas.delete("all")

    def hide(self):
        """Hides the overlay window completely."""
        self.clear()
        if self.win and self.win.winfo_exists():
            self.win.withdraw()
        self.is_visible = False
        if self.auto_dismiss_job:
            try:
                self.master.after_cancel(self.auto_dismiss_job)
            except Exception:
                pass
            self.auto_dismiss_job = None

    def destroy(self):
        self.hide()
        if self.win and self.win.winfo_exists():
            try:
                self.win.destroy()
            except Exception:
                pass
        self.win = None
        self.canvas = None
