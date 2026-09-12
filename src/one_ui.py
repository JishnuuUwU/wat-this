"""
one_ui.py - Modern Obsidian Desktop Design System & Component Library for wat-this.
Pure Python & Tkinter with Zero External DLL Dependencies.
Implements:
1. Modern Obsidian & Slate Palette (Deep #0A0C10, elevated glass surfaces, Indigo/Emerald accents)
2. Canvas Primitives: Anti-aliased Squircles, Rounded Rectangles, and Directional Illumination
3. Modern Components:
   - ModernButton (Pill/Squircle with subtle luminance, icons, hover elevation)
   - ModernStepper (Connected 4-stage horizontal visual pipeline with glowing status nodes)
   - ModernCard (Canvas container with rounded squircle geometry and top ambient edge highlight)
   - ModernProgressBar (Smooth animated progress bar with glowing leading head)
   - ModernKeycap (Elevated tactile keyboard shortcut chips)
   - ModernIconBadge (Squircle category & action badge with soft ambient tint)
   - ModernToggleSwitch (Animated sliding pill switch)
4. Native Windows 11/10 DWM Window Rounding & Dark Mode Utility
"""

import sys
import os
import math
import ctypes
import tkinter as tk
from tkinter import font as tkfont

# ---------------------------------------------------------------------------
# 1. COLOR PALETTE: MINIMALIST MONOCHROME & GRAPHITE
# ---------------------------------------------------------------------------
# Canvas & Backgrounds (Deep Obsidian & Minimalist Charcoal)
COLOR_OBSIDIAN       = "#0A0C10"  # Deepest window canvas background
COLOR_WORKSPACE      = "#0E1117"  # Secondary content canvas
COLOR_SIDEBAR        = "#0A0C10"  # Navigation sidebar background
COLOR_SIDEBAR_HOV    = "#141720"  # Hovered sidebar item
COLOR_SIDEBAR_ACT    = "#181C26"  # Active sidebar capsule

# Card Surfaces (Layered Visual Depth)
COLOR_SURFACE        = "#11141C"  # Standard elevated card surface
COLOR_SURFACE_ELEV   = "#171B26"  # Secondary elevated card (hover/focus)
COLOR_SURFACE_SUB    = "#0D0F16"  # Inset card / text box background
COLOR_SURFACE_HOV    = "#1D2230"  # Interactive hover surface
COLOR_SURFACE_CARD   = "#131620"  # Distinct dashboard card surface

# Hairline Borders & Dividers (Refined Graphite, Zero Neon)
COLOR_BORDER         = "#202534"  # Soft structural hairline border
COLOR_BORDER_SUB     = "#161A24"  # Inner subtle divider
COLOR_BORDER_FOCUS   = "#FFFFFF"  # Minimalist crisp white focus border
COLOR_BORDER_LIGHT   = "#2B3245"  # Subtle top-edge ambient highlight

# Typography Hierarchy
COLOR_TEXT_MAIN      = "#FFFFFF"  # Pure crisp white header
COLOR_TEXT_SEC       = "#94A3B8"  # Slate secondary text / subtitle
COLOR_TEXT_MUTED     = "#64748B"  # Explanatory helper text
COLOR_TEXT_DIM       = "#475569"  # Micro captions & keycap text

# Signature Minimalist Accents (Pure White & Slate)
COLOR_ACCENT         = "#FFFFFF"  # Modern Minimalist Pure White Primary
COLOR_ACCENT_HOV     = "#E2E8F0"  # Light Platinum Silver Hover
COLOR_ACCENT_BG      = "#1C212D"  # Minimalist Charcoal Pill Background
COLOR_ACCENT_BORDER  = "#31384C"  # Structural Border

COLOR_WHITE          = "#FFFFFF"
COLOR_WHITE_HOV      = "#E2E8F0"
COLOR_WHITE_BG       = "#1C212D"

COLOR_BLUE           = "#FFFFFF"  # Default actions use crisp white
COLOR_BLUE_HOV       = "#E2E8F0"
COLOR_BLUE_BG        = "#1C212D"
COLOR_BLUE_BORDER    = "#31384C"

COLOR_SUCCESS        = "#10B981"  # Emerald Success / Online
COLOR_SUCCESS_HOV    = "#34D399"
COLOR_SUCCESS_BG     = "#0D261D"  # Emerald Pill Background
COLOR_SUCCESS_BORDER = "#064E3B"

COLOR_AMBER          = "#F59E0B"  # Warm Amber
COLOR_AMBER_HOV      = "#FBBF24"
COLOR_AMBER_BG       = "#281D0D"  # Amber Pill Background
COLOR_AMBER_BORDER   = "#78350F"

COLOR_ROSE           = "#EF4444"  # Rose Red / Error
COLOR_ROSE_HOV       = "#F87171"
COLOR_ROSE_BG        = "#2A1417"  # Red Pill Background
COLOR_ROSE_BORDER    = "#7F1D1D"

COLOR_PURPLE         = "#E2E8F0"  # Replaced purple with platinum white
COLOR_PURPLE_HOV     = "#FFFFFF"
COLOR_PURPLE_BG      = "#1C212D"
COLOR_PURPLE_BORDER  = "#31384C"

COLOR_CYAN           = "#38BDF8"  # Sky
COLOR_CYAN_BG        = "#0E2430"
COLOR_CYAN_BORDER    = "#164E63"

COLOR_TEAL           = "#2DD4BF"
COLOR_TEAL_BG        = "#0F2824"
COLOR_TEAL_BORDER    = "#134E48"

# Backward-Compatibility Aliases
COLOR_ONEUI_BG           = COLOR_OBSIDIAN
COLOR_ONEUI_CANVAS       = COLOR_WORKSPACE
COLOR_ONEUI_SIDEBAR      = COLOR_SIDEBAR
COLOR_ONEUI_SIDEBAR_HOV  = COLOR_SIDEBAR_HOV
COLOR_ONEUI_SIDEBAR_ACT  = COLOR_SIDEBAR_ACT

COLOR_ONEUI_CARD         = COLOR_SURFACE
COLOR_ONEUI_CARD_SUB     = COLOR_SURFACE_SUB
COLOR_ONEUI_CARD_ELEV    = COLOR_SURFACE_ELEV
COLOR_ONEUI_BORDER       = COLOR_BORDER
COLOR_ONEUI_BORDER_SUB   = COLOR_BORDER_SUB
COLOR_ONEUI_BORDER_FOCUS = COLOR_BORDER_FOCUS

COLOR_ONEUI_TEXT         = COLOR_TEXT_MAIN
COLOR_ONEUI_TEXT_SEC     = COLOR_TEXT_SEC
COLOR_ONEUI_TEXT_MUTED   = COLOR_TEXT_MUTED
COLOR_ONEUI_TEXT_DIM     = COLOR_TEXT_DIM

COLOR_ONEUI_BLUE         = COLOR_ACCENT
COLOR_ONEUI_BLUE_HOV     = COLOR_ACCENT_HOV
COLOR_ONEUI_BLUE_BG      = COLOR_ACCENT_BG
COLOR_ONEUI_BLUE_BORDER  = COLOR_ACCENT_BORDER

COLOR_ONEUI_GREEN        = COLOR_SUCCESS
COLOR_ONEUI_GREEN_HOV    = COLOR_SUCCESS_HOV
COLOR_ONEUI_GREEN_BG     = COLOR_SUCCESS_BG
COLOR_ONEUI_GREEN_BORDER = COLOR_SUCCESS_BORDER

COLOR_ONEUI_AMBER        = COLOR_AMBER
COLOR_ONEUI_AMBER_HOV    = COLOR_AMBER_HOV
COLOR_ONEUI_AMBER_BG     = COLOR_AMBER_BG
COLOR_ONEUI_AMBER_BORDER = COLOR_AMBER_BORDER

COLOR_ONEUI_RED          = COLOR_ROSE
COLOR_ONEUI_RED_HOV      = COLOR_ROSE_HOV
COLOR_ONEUI_RED_BG       = COLOR_ROSE_BG
COLOR_ONEUI_RED_BORDER   = COLOR_ROSE_BORDER

COLOR_ONEUI_PURPLE       = COLOR_PURPLE
COLOR_ONEUI_PURPLE_HOV   = COLOR_PURPLE_HOV
COLOR_ONEUI_PURPLE_BG    = COLOR_PURPLE_BG
COLOR_ONEUI_PURPLE_BORDER= COLOR_PURPLE_BORDER

COLOR_ONEUI_CYAN         = COLOR_CYAN
COLOR_ONEUI_CYAN_BG      = COLOR_CYAN_BG
COLOR_ONEUI_CYAN_BORDER  = COLOR_CYAN_BORDER

COLOR_ONEUI_TEAL         = COLOR_TEAL
COLOR_ONEUI_TEAL_BG      = COLOR_TEAL_BG
COLOR_ONEUI_TEAL_BORDER  = COLOR_TEAL_BORDER

# Mode-to-Accent Mapping (Clean monochrome white with subtle functional accents)
ONEUI_MODE_COLORS = {
    "explain":   "#FFFFFF",
    "fix":       COLOR_SUCCESS,
    "simplify":  COLOR_AMBER,
    "translate": COLOR_CYAN,
    "regex":     "#F472B6",
    "polish":    COLOR_TEAL,
    "docstring": "#FFFFFF",
    "audit":     COLOR_ROSE,
    "unittest":  "#FFFFFF"
}

ONEUI_MODE_BG_COLORS = {
    "explain":   COLOR_ACCENT_BG,
    "fix":       COLOR_SUCCESS_BG,
    "simplify":  COLOR_AMBER_BG,
    "translate": COLOR_CYAN_BG,
    "regex":     "#281420",
    "polish":    COLOR_TEAL_BG,
    "docstring": COLOR_ACCENT_BG,
    "audit":     COLOR_ROSE_BG,
    "unittest":  COLOR_ACCENT_BG
}

# ---------------------------------------------------------------------------
# 2. TYPOGRAPHY & FONT TOKENS
# ---------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"
FONT_HERO       = (FONT_FAMILY, 15, "bold")
FONT_SUBHERO    = (FONT_FAMILY, 12, "bold")
FONT_TITLE      = (FONT_FAMILY, 11, "bold")
FONT_SECTION    = (FONT_FAMILY, 10, "bold")
FONT_BODY       = (FONT_FAMILY, 10)
FONT_BODY_BOLD  = (FONT_FAMILY, 10, "bold")
FONT_SMALL      = (FONT_FAMILY, 9)
FONT_MICRO      = (FONT_FAMILY, 8, "bold")
FONT_SUB        = (FONT_FAMILY, 8)
FONT_CODE       = ("Consolas", 9)

# ---------------------------------------------------------------------------
# 3. WIN32 DWM WINDOW ROUNDING UTILITY
# ---------------------------------------------------------------------------
def apply_win32_rounded_window(hwnd, border_color=0x002A2218, corner_preference=2):
    """
    Applies Windows 11/10 DWM native rounded corners (DWMWCP_ROUND),
    Immersive Dark Mode, and hardware drop shadow to any Tkinter window.
    """
    try:
        dwmapi = ctypes.windll.dwmapi
        v_true = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(v_true), ctypes.sizeof(v_true))

        v_round = ctypes.c_int(corner_preference)
        dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(v_round), ctypes.sizeof(v_round))

        v_border = ctypes.c_int(border_color)
        dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(v_border), ctypes.sizeof(v_border))
    except Exception:
        pass

# ---------------------------------------------------------------------------
# 4. DRAWING UTILITIES: ROUNDED RECTANGLES & SQUIRCLES ON TKINTER CANVAS
# ---------------------------------------------------------------------------
def draw_rounded_rect(canvas, x1, y1, x2, y2, radius=12, fill="", outline="", width=1, tags=None):
    """
    Draws a smooth rounded rectangle / pill on a Tkinter Canvas using
    four rounded corner arcs and connecting rectangles.
    """
    if radius <= 0:
        return canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width, tags=tags)

    diameter = radius * 2
    w = x2 - x1
    h = y2 - y1
    if diameter > min(w, h):
        radius = int(min(w, h) / 2)
        diameter = radius * 2

    tl = (x1, y1, x1 + diameter, y1 + diameter)
    tr = (x2 - diameter, y1, x2, y1 + diameter)
    br = (x2 - diameter, y2 - diameter, x2, y2)
    bl = (x1, y2 - diameter, x1 + diameter, y2)

    items = []
    if fill:
        items.append(canvas.create_arc(tl, start=90, extent=90, fill=fill, outline=fill, width=0, tags=tags))
        items.append(canvas.create_arc(tr, start=0, extent=90, fill=fill, outline=fill, width=0, tags=tags))
        items.append(canvas.create_arc(br, start=270, extent=90, fill=fill, outline=fill, width=0, tags=tags))
        items.append(canvas.create_arc(bl, start=180, extent=90, fill=fill, outline=fill, width=0, tags=tags))
        items.append(canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill, outline=fill, width=0, tags=tags))
        items.append(canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill, outline=fill, width=0, tags=tags))

    if outline and width > 0:
        items.append(canvas.create_arc(tl, start=90, extent=90, style="arc", outline=outline, width=width, tags=tags))
        items.append(canvas.create_arc(tr, start=0, extent=90, style="arc", outline=outline, width=width, tags=tags))
        items.append(canvas.create_arc(br, start=270, extent=90, style="arc", outline=outline, width=width, tags=tags))
        items.append(canvas.create_arc(bl, start=180, extent=90, style="arc", outline=outline, width=width, tags=tags))
        items.append(canvas.create_line(x1 + radius, y1, x2 - radius, y1, fill=outline, width=width, tags=tags))
        items.append(canvas.create_line(x2, y1 + radius, x2, y2 - radius, fill=outline, width=width, tags=tags))
        items.append(canvas.create_line(x2 - radius, y2, x1 + radius, y2, fill=outline, width=width, tags=tags))
        items.append(canvas.create_line(x1, y2 - radius, x1, y1 + radius, fill=outline, width=width, tags=tags))

    return items

# ---------------------------------------------------------------------------
# 5. COMPONENT: MODERN BUTTON (PILL & SQUIRCLE)
# ---------------------------------------------------------------------------
class ModernButton(tk.Canvas):
    """
    High-end pill/squircle button with subtle ambient shading,
    responsive hover brightening, tactile press feedback, and crisp icons.
    """
    def __init__(self, parent, text="Button", icon="", command=None,
                 variant="surface", font=FONT_TITLE,
                 padx=16, pady=8, height=34, bg=None, cursor="hand2", radius=None):
        self.variant = variant
        self.command = command
        self.text = text
        self.icon = icon
        self.btn_font = font
        self.padx = padx
        self.pady = pady
        self.height = height
        self.custom_radius = radius
        self.is_hovered = False
        self.is_pressed = False

        parent_bg = bg or (parent.cget("bg") if hasattr(parent, "cget") else COLOR_SURFACE)
        self.base_bg = parent_bg

        self.tk_font = tkfont.Font(font=font)
        label_text = f"{icon}  {text}" if (icon and text) else (icon or text)
        text_w = self.tk_font.measure(label_text)
        btn_h = max(height, self.tk_font.metrics("linespace") + (pady * 2))
        btn_w = max(btn_h if not text else 0, text_w + (padx * 2))

        super().__init__(parent, width=btn_w, height=btn_h, bg=parent_bg, highlightthickness=0, bd=0, cursor=cursor)
        self.btn_w = btn_w
        self.btn_h = btn_h
        self.label_text = label_text

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.draw()

    def set_text(self, text, icon=None):
        self.text = text
        if icon is not None:
            self.icon = icon
        self.label_text = f"{self.icon}  {self.text}" if (self.icon and self.text) else (self.icon or self.text)
        text_w = self.tk_font.measure(self.label_text)
        self.btn_w = max(self.btn_h if not self.text else 0, text_w + (self.padx * 2))
        self.configure(width=self.btn_w)
        self.draw()

    def set_variant(self, variant):
        self.variant = variant
        self.draw()

    def set_custom_colors(self, bg, fg, border=None):
        self.variant = "custom"
        self.custom_bg = bg
        self.custom_fg = fg
        self.custom_border = border or bg
        self.draw()

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        updated = False
        if "text" in kwargs:
            self.text = kwargs.pop("text")
            updated = True
        if "icon" in kwargs:
            self.icon = kwargs.pop("icon")
            updated = True
        if "variant" in kwargs:
            self.variant = kwargs.pop("variant")
            updated = True
        if "fg" in kwargs:
            self.custom_fg = kwargs.pop("fg")
            self.variant = "custom"
            updated = True
        if "highlightbackground" in kwargs:
            self.custom_border = kwargs.pop("highlightbackground")
            self.variant = "custom"
            updated = True
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        if "bg" in kwargs:
            val = kwargs.pop("bg")
            if val in (COLOR_OBSIDIAN, COLOR_WORKSPACE, COLOR_SURFACE, COLOR_SURFACE_SUB, COLOR_SURFACE_ELEV, COLOR_SIDEBAR):
                super().configure(bg=val)
                self.base_bg = val
            else:
                self.custom_bg = val
                self.variant = "custom"
            updated = True
        if kwargs:
            safe = {k: v for k, v in kwargs.items() if k not in ("relief", "bd", "padx", "pady")}
            if safe:
                super().configure(**safe)
        if updated:
            self.label_text = f"{self.icon}  {self.text}" if (self.icon and self.text) else (self.icon or self.text)
            text_w = self.tk_font.measure(self.label_text)
            self.btn_w = max(self.btn_h if not self.text else 0, text_w + (self.padx * 2))
            super().configure(width=self.btn_w)
            self.draw()

    config = configure

    def cget(self, key):
        if key == "text":
            return self.text
        if key == "fg":
            return getattr(self, "custom_fg", None)
        return super().cget(key)

    def _get_colors(self):
        if self.variant == "primary":
            bg = "#F1F5F9" if self.is_hovered else "#FFFFFF"
            fg = "#0A0C10"  # High-contrast bold dark black on pure white
            border = "#F1F5F9" if self.is_hovered else "#FFFFFF"
        elif self.variant == "success":
            bg = COLOR_SUCCESS if self.is_hovered else COLOR_SUCCESS_BG
            fg = "#FFFFFF" if self.is_hovered else COLOR_SUCCESS
            border = COLOR_SUCCESS if self.is_hovered else COLOR_SUCCESS_BORDER
        elif self.variant == "amber":
            bg = "#452C10" if self.is_hovered else COLOR_AMBER_BG
            fg = "#FBBF24" if self.is_hovered else COLOR_AMBER
            border = COLOR_AMBER if self.is_hovered else COLOR_AMBER_BORDER
        elif self.variant == "danger":
            bg = COLOR_ROSE if self.is_hovered else COLOR_ROSE_BG
            fg = "#FFFFFF" if self.is_hovered else COLOR_ROSE
            border = COLOR_ROSE if self.is_hovered else COLOR_ROSE_BORDER
        elif self.variant == "ghost":
            bg = COLOR_SURFACE_HOV if self.is_hovered else self.base_bg
            fg = COLOR_TEXT_MAIN if self.is_hovered else COLOR_TEXT_SEC
            border = COLOR_BORDER if self.is_hovered else ""
        elif self.variant == "custom":
            bg = getattr(self, "custom_bg", COLOR_SURFACE_SUB)
            fg = getattr(self, "custom_fg", COLOR_TEXT_MAIN)
            border = getattr(self, "custom_border", COLOR_BORDER)
        else: # "surface"
            bg = COLOR_SURFACE_HOV if self.is_hovered else COLOR_SURFACE_SUB
            fg = COLOR_TEXT_MAIN if self.is_hovered else COLOR_TEXT_SEC
            border = "#3B455E" if self.is_hovered else COLOR_BORDER

        if self.is_pressed:
            bg = "#CBD5E1" if self.variant == "primary" else "#0D1017"

        return bg, fg, border

    def _on_enter(self, e):
        self.is_hovered = True
        self.draw()

    def _on_leave(self, e):
        self.is_hovered = False
        self.is_pressed = False
        self.draw()

    def _on_press(self, e):
        self.is_pressed = True
        self.draw()

    def _on_release(self, e):
        if self.is_pressed and self.is_hovered:
            self.is_pressed = False
            self.draw()
            if self.command:
                self.command()
        else:
            self.is_pressed = False
            self.draw()

    def draw(self):
        self.delete("all")
        bg_col, fg_col, border_col = self._get_colors()
        radius = self.custom_radius if self.custom_radius is not None else int(self.btn_h / 2)
        draw_rounded_rect(self, 1, 1, self.btn_w - 1, self.btn_h - 1, radius=radius,
                          fill=bg_col, outline=border_col, width=1)

        # Subtle top-edge light highlight for primary and surface buttons
        if self.variant in ("primary", "surface") and self.btn_h >= 26 and not self.is_pressed:
            highlight_col = "#FFFFFF" if self.variant == "primary" else "#2D354A"
            self.create_line(radius, 1, self.btn_w - radius, 1, fill=highlight_col, width=1)

        # Centered text label
        self.create_text(
            self.btn_w / 2, self.btn_h / 2,
            text=self.label_text, font=self.btn_font, fill=fg_col
        )

# Alias for backward compatibility
OneUIPillButton = ModernButton

# ---------------------------------------------------------------------------
# 6. COMPONENT: VISUAL STEPPER MILESTONE PIPELINE
# ---------------------------------------------------------------------------
class ModernStepper(tk.Canvas):
    """
    Visual 4-stage horizontal pipeline widget.
    Replaces raw console brackets with modern connected milestone nodes.
    Each node features an anti-aliased circular indicator, stage title, and dynamic telemetry subtitle.
    """
    def __init__(self, parent, height=88, bg=COLOR_SURFACE_SUB):
        super().__init__(parent, height=height, bg=bg, highlightthickness=0, bd=0)
        self.bg_col = bg
        self.steps = [
            {"title": "Hardware Memory", "sub": "Probing system RAM...", "state": "pending"},
            {"title": "Ollama Daemon",    "sub": "Local AI runtime",       "state": "pending"},
            {"title": "Neural Weights",   "sub": "Optimal profile model",  "state": "pending"},
            {"title": "Live Verification","sub": "End-to-end smoke test",  "state": "pending"},
        ]
        self.bind("<Configure>", lambda e: self.draw())
        self.draw()

    def set_step_state(self, idx, state, subtitle=None):
        """
        Updates node state: 'pending', 'running', 'success', 'error'.
        Optionally updates the subtitle string underneath.
        """
        if 0 <= idx < len(self.steps):
            self.steps[idx]["state"] = state
            if subtitle:
                self.steps[idx]["sub"] = subtitle
            self.draw()

    def reset_all(self):
        for s in self.steps:
            s["state"] = "pending"
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 100:
            w = 600
        if h < 40:
            h = 88

        n = len(self.steps)
        margin_x = 52
        avail_w = w - (margin_x * 2)
        spacing = avail_w / (n - 1) if n > 1 else 0
        node_y = 26

        # Background connecting track line
        self.create_line(margin_x, node_y, w - margin_x, node_y, fill="#1E2432", width=2)

        # Completed track line segments
        for i in range(n - 1):
            if self.steps[i]["state"] == "success":
                x1 = margin_x + (i * spacing)
                x2 = margin_x + ((i + 1) * spacing)
                col = COLOR_SUCCESS if self.steps[i + 1]["state"] == "success" else "#FFFFFF"
                self.create_line(x1, node_y, x2, node_y, fill=col, width=2)

        radius = 13
        for i, step in enumerate(self.steps):
            cx = margin_x + (i * spacing)
            cy = node_y
            state = step["state"]

            if state == "success":
                circle_bg = COLOR_SUCCESS_BG
                circle_border = COLOR_SUCCESS
                icon_col = "#34D399"
                icon_txt = "✓"
            elif state == "running":
                circle_bg = "#1A202C"
                circle_border = "#FFFFFF"
                icon_col = "#FFFFFF"
                icon_txt = "●"
            elif state == "error":
                circle_bg = COLOR_ROSE_BG
                circle_border = COLOR_ROSE
                icon_col = "#F87171"
                icon_txt = "✕"
            else: # pending
                circle_bg = "#11141C"
                circle_border = "#242B3A"
                icon_col = "#64748B"
                icon_txt = str(i + 1)

            # Outer glow ring
            if state in ("running", "success"):
                self.create_oval(cx - radius - 3, cy - radius - 3, cx + radius + 3, cy + radius + 3,
                                 outline=circle_border, width=1)

            # Node circle
            self.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                             fill=circle_bg, outline=circle_border, width=1.5)

            # Icon inside node
            self.create_text(cx, cy, text=icon_txt, font=(FONT_FAMILY, 9, "bold"), fill=icon_col)

            # Node Stage Title
            title_col = COLOR_TEXT_MAIN if state in ("running", "success") else COLOR_TEXT_SEC
            self.create_text(cx, cy + 22, text=step["title"], font=(FONT_FAMILY, 9, "bold"), fill=title_col)

            # Node Telemetry Subtitle
            sub_col = COLOR_TEXT_MUTED if state != "error" else COLOR_ROSE
            sub_txt = step["sub"]
            if len(sub_txt) > 30:
                sub_txt = sub_txt[:28] + ".."
            self.create_text(cx, cy + 37, text=sub_txt, font=(FONT_FAMILY, 8), fill=sub_col)

# ---------------------------------------------------------------------------
# 7. COMPONENT: TACTILE KEYCAP CHIP
# ---------------------------------------------------------------------------
class ModernKeycap(tk.Canvas):
    """
    Tactile keyboard keycap chip for shortcuts (e.g. '1', '2', 'Esc', 'Tab').
    Draws an elevated squircle pill with subtle bevel and crisp contrast.
    """
    def __init__(self, parent, key="1", font=FONT_MICRO, padx=8, pady=3,
                 bg="#161B26", fg="#CBD5E1", border="#2A3245", parent_bg=None):
        tk_font = tkfont.Font(font=font)
        text_w = tk_font.measure(key)
        line_h = tk_font.metrics("linespace")
        btn_w = max(24, text_w + (padx * 2))
        btn_h = max(22, line_h + (pady * 2))

        pbg = parent_bg or (parent.cget("bg") if hasattr(parent, "cget") else COLOR_SURFACE)
        super().__init__(parent, width=btn_w, height=btn_h, bg=pbg, highlightthickness=0, bd=0)
        self.key = key
        self.btn_font = font
        self.bg_col = bg
        self.fg_col = fg
        self.border_col = border
        self.btn_w = btn_w
        self.btn_h = btn_h
        self.draw()

    def set_key(self, key):
        self.key = key
        self.draw()

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if "bg" in kwargs:
            self.bg_col = kwargs.pop("bg")
        if "fg" in kwargs:
            self.fg_col = kwargs.pop("fg")
        if "highlightbackground" in kwargs:
            self.border_col = kwargs.pop("highlightbackground")
        if "border" in kwargs:
            self.border_col = kwargs.pop("border")
        if "key" in kwargs:
            self.key = kwargs.pop("key")
        self.draw()

    config = configure

    def cget(self, key):
        if key == "text" or key == "key":
            return self.key
        if key == "bg":
            return self.bg_col
        if key == "fg":
            return self.fg_col
        return super().cget(key)

    def draw(self):
        self.delete("all")
        draw_rounded_rect(self, 1, 1, self.btn_w - 1, self.btn_h - 1, radius=5,
                          fill=self.bg_col, outline=self.border_col, width=1)
        self.create_line(4, 1, self.btn_w - 4, 1, fill="#38435C", width=1)
        self.create_text(self.btn_w / 2, self.btn_h / 2, text=self.key, font=self.btn_font, fill=self.fg_col)

# ---------------------------------------------------------------------------
# 8. COMPONENT: FLUID PROGRESS BAR
# ---------------------------------------------------------------------------
class ModernProgressBar(tk.Canvas):
    """
    Sleek, extra-rounded progress bar with fluid interpolation animation.
    Avoids abrupt value jumping by easing smoothly to target values.
    """
    def __init__(self, parent, width=300, height=8, bg=COLOR_SURFACE, bar_color=COLOR_ACCENT):
        super().__init__(parent, width=width, height=height, bg=bg, highlightthickness=0, bd=0)
        self.w = width
        self.h = height
        self.bar_color = bar_color
        self.bg_color = bg
        self.current_pct = 0.0
        self.target_pct = 0.0
        self.animating = False

        self.bind("<Configure>", self._on_configure)
        self.draw()

    def _on_configure(self, e):
        if e.width > 10:
            self.w = e.width
            self.draw()

    def set_progress(self, pct, animate=True):
        clamped = max(0.0, min(100.0, float(pct)))
        self.target_pct = clamped
        if animate:
            if not self.animating:
                self.animating = True
                self._animate_tick()
        else:
            self.current_pct = self.target_pct
            self.draw()

    def _animate_tick(self):
        diff = self.target_pct - self.current_pct
        if abs(diff) < 0.5:
            self.current_pct = self.target_pct
            self.animating = False
            self.draw()
            return

        self.current_pct += diff * 0.25
        self.draw()
        self.after(16, self._animate_tick)

    def draw(self):
        self.delete("all")
        radius = int(self.h / 2)
        # Background track
        draw_rounded_rect(self, 0, 0, self.w, self.h, radius=radius, fill=COLOR_SURFACE_SUB, outline="#202638", width=1)

        # Active fill
        if self.current_pct > 0:
            fill_w = max(radius * 2, int((self.current_pct / 100.0) * self.w))
            draw_rounded_rect(self, 0, 0, min(self.w, fill_w), self.h, radius=radius,
                              fill=self.bar_color, outline=self.bar_color, width=0)

# Alias for backward compatibility
OneUIProgressBar = ModernProgressBar

# ---------------------------------------------------------------------------
# 9. COMPONENT: SQUIRCLE ICON BADGE
# ---------------------------------------------------------------------------
class ModernIconBadge(tk.Canvas):
    """
    Smooth rounded squircle badge for category & action icons.
    Provides a soft tinted background with vibrant high-contrast icon glyph.
    """
    def __init__(self, parent, icon="⚡", size=40, radius=11, bg_color=COLOR_ACCENT_BG,
                 icon_color=COLOR_ACCENT, parent_bg=COLOR_SURFACE):
        super().__init__(parent, width=size, height=size, bg=parent_bg, highlightthickness=0, bd=0)
        self.size = size
        self.radius = radius
        self.icon = icon
        self.bg_color = bg_color
        self.icon_color = icon_color
        self.draw()

    def update_icon(self, icon, bg_color=None, icon_color=None):
        self.icon = icon
        if bg_color:
            self.bg_color = bg_color
        if icon_color:
            self.icon_color = icon_color
        self.draw()

    def draw(self):
        self.delete("all")
        draw_rounded_rect(self, 1, 1, self.size - 1, self.size - 1, radius=self.radius,
                          fill=self.bg_color, outline=self.bg_color, width=0)
        font_sz = max(11, int(self.size * 0.42))
        self.create_text(
            self.size / 2, self.size / 2,
            text=self.icon, font=(FONT_FAMILY, font_sz, "bold"), fill=self.icon_color
        )

# Alias for backward compatibility
OneUIIconBadge = ModernIconBadge

# ---------------------------------------------------------------------------
# 10. COMPONENT: ANIMATED PILL TOGGLE SWITCH
# ---------------------------------------------------------------------------
class ModernToggleSwitch(tk.Canvas):
    """
    Tactile Pill-shaped Toggle Switch.
    """
    def __init__(self, parent, variable=None, command=None, width=46, height=24, bg=COLOR_SURFACE, active_color=COLOR_ACCENT):
        super().__init__(parent, width=width, height=height, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.var = variable or tk.BooleanVar(value=False)
        self.command = command
        self.active_color = active_color
        self.bg_color = bg
        self.w = width
        self.h = height

        self.animating = False
        self.min_tx = 3.0
        self.max_tx = float(width - height + 3)
        self.target_tx = self.max_tx if self.var.get() else self.min_tx
        self.current_tx = self.target_tx

        self.bind("<Button-1>", self.toggle)
        self.draw()

    def toggle(self, event=None):
        new_val = not self.var.get()
        self.var.set(new_val)
        target = self.max_tx if new_val else self.min_tx
        self._start_slide_animation(target)
        if self.command:
            self.command()

    def _start_slide_animation(self, target_tx):
        self.target_tx = target_tx
        if not self.animating:
            self.animating = True
            self._animate_tick()

    def _animate_tick(self):
        diff = self.target_tx - self.current_tx
        if abs(diff) < 0.8:
            self.current_tx = self.target_tx
            self.animating = False
            self.draw()
            return

        self.current_tx += diff * 0.38
        self.draw()
        self.after(16, self._animate_tick)

    def draw(self):
        self.delete("all")
        midpoint = (self.min_tx + self.max_tx) / 2.0
        is_on_side = (self.current_tx > midpoint)

        track_color = self.active_color if is_on_side else "#252B3A"
        track_border = self.active_color if is_on_side else "#333C4E"

        radius = int(self.h / 2)
        draw_rounded_rect(self, 1, 1, self.w - 1, self.h - 1, radius=radius - 1,
                          fill=track_color, outline=track_border, width=1)

        thumb_diameter = self.h - 6
        tx = self.current_tx
        ty = 3

        self.create_oval(tx + 1, ty + 1, tx + thumb_diameter + 1, ty + thumb_diameter + 1, fill="#0A0C10", outline="")
        self.create_oval(tx, ty, tx + thumb_diameter, ty + thumb_diameter, fill="#FFFFFF", outline="#FFFFFF")

# Alias for backward compatibility
OneUIToggleSwitch = ModernToggleSwitch
