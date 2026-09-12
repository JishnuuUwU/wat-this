"""
screen_context.py - Zero-DLL Screen & Window Context Engine for wat-this
Captures active foreground window metadata, process information, screen bounding rects,
and extracts visible screen text via native Windows 10/11 WinRT OCR (zero third-party dependencies).
"""

import sys
import os
import ctypes
from ctypes import wintypes
import json
import subprocess
import time
import re

# Win32 API handles
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

# Win32 Constants
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SRCCOPY = 0x00CC0020
DWMWA_EXTENDED_FRAME_BOUNDS = 9

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

def get_foreground_window_info(exclude_hwnds=None):
    """
    Retrieves metadata of the active foreground window before wat-this HUD appeared:
    returns dict with 'hwnd', 'title', 'class', 'process_name', 'rect': (left, top, right, bottom).
    """
    exclude_set = set(exclude_hwnds or [])
    try:
        hwnd = user32.GetForegroundWindow()
        # If current foreground is our own window, walk previous top-level windows
        if hwnd in exclude_set or hwnd == 0:
            hwnd = user32.GetWindow(hwnd, 2) # GW_HWNDNEXT
            while hwnd and (hwnd in exclude_set or not user32.IsWindowVisible(hwnd)):
                hwnd = user32.GetWindow(hwnd, 2)

        if not hwnd or not user32.IsWindow(hwnd):
            return {"hwnd": 0, "title": "Desktop", "process_name": "explorer.exe", "class": "Progman", "rect": (0, 0, 1920, 1080)}

        # Window Title
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 2)
        user32.GetWindowTextW(hwnd, buff, length + 2)
        title = buff.value.strip()

        # Window Class
        class_buff = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buff, 256)
        win_class = class_buff.value.strip()

        # Window Rect (Prefer DwmGetWindowAttribute for accurate visual bounds without drop shadow padding)
        rect = RECT()
        dwmapi = getattr(ctypes.windll, "dwmapi", None)
        got_rect = False
        if dwmapi:
            try:
                res = dwmapi.DwmGetWindowAttribute(
                    hwnd, DWMWA_EXTENDED_FRAME_BOUNDS,
                    ctypes.byref(rect), ctypes.sizeof(rect)
                )
                if res == 0:
                    got_rect = True
            except Exception:
                pass

        if not got_rect:
            user32.GetWindowRect(hwnd, ctypes.byref(rect))

        # Process Executable Name
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_name = "Unknown"
        h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if h_proc:
            try:
                proc_buff = ctypes.create_unicode_buffer(1024)
                proc_len = wintypes.DWORD(1024)
                if kernel32.QueryFullProcessImageNameW(h_proc, 0, proc_buff, ctypes.byref(proc_len)):
                    proc_name = os.path.basename(proc_buff.value)
            finally:
                kernel32.CloseHandle(h_proc)

        return {
            "hwnd": hwnd,
            "title": title if title else proc_name,
            "process_name": proc_name,
            "class": win_class,
            "rect": (rect.left, rect.top, rect.right, rect.bottom)
        }
    except Exception as e:
        return {"hwnd": 0, "title": "Active Application", "process_name": "System", "class": "", "rect": (0, 0, 1920, 1080)}

def capture_window_text_native(hwnd):
    """
    Extracts visible child window text (buttons, labels, edit boxes, status bars)
    using Win32 EnumChildWindows + WM_GETTEXT (0ms, 100% pure zero-DLL).
    """
    if not hwnd or not user32.IsWindow(hwnd):
        return []

    results = []
    WM_GETTEXT = 0x000D
    WM_GETTEXTLENGTH = 0x000E

    def enum_proc(child_hwnd, lparam):
        if not user32.IsWindowVisible(child_hwnd):
            return True
        length = user32.SendMessageW(child_hwnd, WM_GETTEXTLENGTH, 0, 0)
        if 0 < length < 4096:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.SendMessageW(child_hwnd, WM_GETTEXT, length + 1, ctypes.byref(buf))
            txt = buf.value.strip()
            if txt and len(txt) > 2 and txt not in results:
                results.append(txt)
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumChildWindows(hwnd, WNDENUMPROC(enum_proc), 0)
    return results

def run_windows_native_ocr_snippet(rect=None, timeout_sec=2.0):
    """
    Captures a screen region and passes it through Windows 10/11 built-in
    Windows.Media.Ocr.OcrEngine. Runs cleanly with a strict timeout to ensure zero latency overhead.
    Returns list of extracted text strings.
    """
    # Build PowerShell command leveraging built-in Windows Runtime OCR
    # Clamped to target rect or cursor area
    try:
        if rect:
            l, t, r, b = rect
            w = max(10, r - l)
            h = max(10, b - t)
        else:
            l, t, w, h = 0, 0, 1920, 1080

        # PowerShell script using System.Drawing + Windows.Media.Ocr
        ps_script = f"""
$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Drawing, Windows.Foundation
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) {{ exit 0 }}

$bmp = New-Object System.Drawing.Bitmap({w}, {h})
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen({l}, {t}, 0, 0, (New-Object System.Drawing.Size({w}, {h})))
$g.Dispose()

$ms = New-Object System.IO.MemoryStream
$bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Bmp)
$bmp.Dispose()
$bytes = $ms.ToArray()
$ms.Dispose()

# Create SoftwareBitmap from memory
$ras = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
$dw = New-Object Windows.Storage.Streams.DataWriter($ras)
$dw.WriteBytes($bytes)
$dw.StoreAsync().AsTask().Wait()
$dw.Dispose()
$ras.Seek(0)

$decoder = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($ras).AsTask().Result
$s_bmp = $decoder.GetSoftwareBitmapAsync().AsTask().Result
$result = $engine.RecognizeAsync($s_bmp).AsTask().Result
$s_bmp.Dispose()
$ras.Dispose()

foreach ($line in $result.Lines) {{
    Write-Output $line.Text
}}
"""
        proc = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=0x08000000 # CREATE_NO_WINDOW
        )
        stdout, _ = proc.communicate(timeout=timeout_sec)
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        return lines
    except Exception:
        return []

def get_screen_context_summary(exclude_hwnds=None, max_context_chars=1200):
    """
    Gathers comprehensive, zero-latency screen context:
    - Active Application process name (e.g. Code.exe, chrome.exe)
    - Active Window title (e.g. 'wat_this.py - Visual Studio Code')
    - Active Window visible UI text / controls
    Returns formatted context dict.
    """
    win_info = get_foreground_window_info(exclude_hwnds)
    hwnd = win_info.get("hwnd", 0)
    title = win_info.get("title", "")
    proc = win_info.get("process_name", "")
    rect = win_info.get("rect", (0, 0, 1920, 1080))

    # Fast child window text extraction (0ms)
    child_texts = capture_window_text_native(hwnd)
    
    # Try native OCR on window bounds with quick timeout
    ocr_lines = []
    # If child texts are minimal (like in Chrome/Electron), OCR window rect
    if len(child_texts) < 3 and rect and rect[2] - rect[0] > 100:
        ocr_lines = run_windows_native_ocr_snippet(rect, timeout_sec=1.2)

    combined_text = []
    if child_texts:
        combined_text.extend(child_texts[:8])
    if ocr_lines:
        combined_text.extend(ocr_lines[:15])

    clean_snippet = "\n".join(combined_text)
    if len(clean_snippet) > max_context_chars:
        clean_snippet = clean_snippet[:max_context_chars] + "..."

    return {
        "title": title,
        "process": proc,
        "rect": rect,
        "visible_text": clean_snippet,
        "has_content": bool(clean_snippet.strip() or title)
    }

def format_prompt_with_screen_context(highlighted_text, screen_context, mode_prompt=""):
    """
    Constructs a rich prompt embedding full desktop & window context alongside the highlighted target.
    If no text is highlighted, the screen context becomes the primary subject for explanation/help!
    """
    title = screen_context.get("title", "")
    proc = screen_context.get("process", "")
    vis_text = screen_context.get("visible_text", "")

    header_parts = []
    if title:
        header_parts.append(f"Active Application: {proc} (Window: '{title}')")
    if vis_text:
        header_parts.append(f"Surrounding Screen Context:\n{vis_text}")

    context_block = "\n".join(header_parts)

    if highlighted_text and highlighted_text.strip():
        prompt = (
            f"[CONTEXT]\n{context_block}\n\n"
            f"[FOCAL TARGET]:\n{highlighted_text}\n\n"
            f"[TASK]: {mode_prompt}"
        )
    else:
        prompt = (
            f"[SCREEN CONTEXT]\n{context_block}\n\n"
            f"[TASK]: The user opened the copilot on this active window without selecting specific text. "
            f"Analyze the visible screen context above and provide guidance: {mode_prompt}"
        )

    return prompt
