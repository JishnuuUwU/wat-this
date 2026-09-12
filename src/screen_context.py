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
import tempfile

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

def clean_window_title(title):
    """
    Strips browser and app chrome noise from window title to isolate the actual document or page topic.
    e.g. 'Degree Class Grouping... - Jira Service Management and 1 more page - Personal - Microsoft Edge'
         -> 'Degree Class Grouping... - Jira Service Management'
    """
    if not title:
        return ""
    # Strip zero-width spaces and invisible characters
    cleaned = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", title).strip()

    # Browser / App tab suffixes
    patterns = [
        r"\s+and\s+\d+\s+more\s+pages?.*$",
        r"\s*-\s*Personal\s*-\s*Microsoft\s*Edge.*$",
        r"\s*-\s*Work\s*-\s*Microsoft\s*Edge.*$",
        r"\s*-\s*\[InPrivate\]\s*-\s*Microsoft\s*Edge.*$",
        r"\s*-\s*Microsoft\s*Edge.*$",
        r"\s*-\s*Google\s*Chrome.*$",
        r"\s*-\s*Mozilla\s*Firefox.*$",
        r"\s*-\s*Brave.*$",
        r"\s*-\s*Visual\s*Studio\s*Code.*$",
    ]
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else title.strip()

def get_foreground_window_info(exclude_hwnds=None):
    """
    Retrieves metadata of the active foreground window before wat-this HUD appeared:
    returns dict with 'hwnd', 'title', 'clean_title', 'class', 'process_name', 'rect': (left, top, right, bottom).
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
            return {"hwnd": 0, "title": "Desktop", "clean_title": "Desktop", "process_name": "explorer.exe", "class": "Progman", "rect": (0, 0, 1920, 1080)}

        # Window Title
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 2)
        user32.GetWindowTextW(hwnd, buff, length + 2)
        raw_title = buff.value.strip()

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

        clean_t = clean_window_title(raw_title)
        return {
            "hwnd": hwnd,
            "title": raw_title if raw_title else proc_name,
            "clean_title": clean_t if clean_t else (raw_title if raw_title else proc_name),
            "process_name": proc_name,
            "class": win_class,
            "rect": (rect.left, rect.top, rect.right, rect.bottom)
        }
    except Exception as e:
        return {"hwnd": 0, "title": "Active Application", "clean_title": "Active Application", "process_name": "System", "class": "", "rect": (0, 0, 1920, 1080)}

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

def capture_screen_rect_to_bmp(rect, output_bmp_path):
    """
    Captures a screen rectangle into a standard 24-bit uncompressed BMP file
    using pure Win32 GDI ctypes in ~7ms with zero external DLL dependencies.
    """
    try:
        x1, y1, x2, y2 = rect
        # Clamp coordinates
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        x1 = max(0, min(sw - 10, x1))
        y1 = max(0, min(sh - 10, y1))
        x2 = max(x1 + 10, min(sw, x2))
        y2 = max(y1 + 10, min(sh, y2))
        w = x2 - x1
        h = y2 - y1
        if w <= 0 or h <= 0:
            return False

        h_desktop = user32.GetDesktopWindow()
        h_dc_screen = user32.GetDC(h_desktop)
        if not h_dc_screen:
            return False

        h_dc_mem = gdi32.CreateCompatibleDC(h_dc_screen)
        h_bmp = gdi32.CreateCompatibleBitmap(h_dc_screen, w, h)
        h_old = gdi32.SelectObject(h_dc_mem, h_bmp)

        gdi32.BitBlt(h_dc_mem, 0, 0, w, h, h_dc_screen, x1, y1, SRCCOPY)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ('biSize', wintypes.DWORD),
                ('biWidth', wintypes.LONG),
                ('biHeight', wintypes.LONG),
                ('biPlanes', wintypes.WORD),
                ('biBitCount', wintypes.WORD),
                ('biCompression', wintypes.DWORD),
                ('biSizeImage', wintypes.DWORD),
                ('biXPelsPerMeter', wintypes.LONG),
                ('biYPelsPerMeter', wintypes.LONG),
                ('biClrUsed', wintypes.DWORD),
                ('biClrImportant', wintypes.DWORD)
            ]

        bi = BITMAPINFOHEADER()
        bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bi.biWidth = w
        bi.biHeight = -h  # top-down DIB
        bi.biPlanes = 1
        bi.biBitCount = 24
        bi.biCompression = 0

        row_size = ((w * 24 + 31) // 32) * 4
        image_size = row_size * h
        bi.biSizeImage = image_size

        buf = ctypes.create_string_buffer(image_size)
        gdi32.GetDIBits(h_dc_mem, h_bmp, 0, h, buf, ctypes.byref(bi), 0)

        # Release GDI handles immediately
        gdi32.SelectObject(h_dc_mem, h_old)
        gdi32.DeleteObject(h_bmp)
        gdi32.DeleteDC(h_dc_mem)
        user32.ReleaseDC(h_desktop, h_dc_screen)

        # BMP 14-byte file header
        file_size = 14 + 40 + image_size
        bmp_header = bytearray(b'BM')
        bmp_header += file_size.to_bytes(4, 'little')
        bmp_header += (0).to_bytes(4, 'little')
        bmp_header += (54).to_bytes(4, 'little')

        with open(output_bmp_path, 'wb') as f:
            f.write(bmp_header)
            f.write(bytearray(bi))
            f.write(buf.raw)
        return True
    except Exception as e:
        return False

def run_windows_native_ocr_snippet(rect=None, timeout_sec=4.0):
    """
    Captures target window/screen region and runs Windows 10/11 built-in
    Windows.Media.Ocr.OcrEngine via pure PowerShell MTA + Windows Runtime extensions.
    Returns list of extracted text strings.
    """
    temp_bmp = os.path.join(tempfile.gettempdir(), f"wat_this_ocr_{os.getpid()}_{int(time.time()*1000)%100000}.bmp")
    try:
        # 1. Determine screen rect
        if not rect:
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
            rect = (0, 0, sw, sh)

        # 2. Fast GDI BitBlt capture (~7ms)
        ok = capture_screen_rect_to_bmp(rect, temp_bmp)
        if not ok or not os.path.exists(temp_bmp) or os.path.getsize(temp_bmp) < 100:
            return []

        norm_path = os.path.abspath(temp_bmp).replace("\\", "\\\\")

        # 3. Robust WinRT OCR script with System.Runtime.WindowsRuntime AsTask awaiter
        ps_script = f"""
$ErrorActionPreference = 'SilentlyContinue'
try {{
    Add-Type -AssemblyName "System.Runtime.WindowsRuntime"
    $asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{ $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.IsGenericMethod }} | Select-Object -First 1

    function Await-WinRT($asyncOp, $type) {{
        $method = $asTaskGeneric.MakeGenericMethod($type)
        $task = $method.Invoke($null, @($asyncOp))
        return $task.GetAwaiter().GetResult()
    }}

    [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
    [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
    [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null
    [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null
    [Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if (-not $engine) {{ exit 0 }}

    $p = [System.IO.Path]::GetFullPath('{norm_path}')
    $file = Await-WinRT ([Windows.Storage.StorageFile]::GetFileFromPathAsync($p)) ([Windows.Storage.StorageFile])
    $stream = Await-WinRT ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await-WinRT ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await-WinRT ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

    $result = Await-WinRT ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $bitmap.Dispose()
    $stream.Dispose()

    if ($result) {{
        foreach ($line in $result.Lines) {{
            Write-Output $line.Text
        }}
    }}
}} catch {{
    exit 0
}}
"""
        proc = subprocess.Popen(
            ["powershell.exe", "-Mta", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=0x08000000 # CREATE_NO_WINDOW
        )
        stdout, _ = proc.communicate(timeout=timeout_sec)
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        return lines
    except Exception:
        return []
    finally:
        if os.path.exists(temp_bmp):
            try:
                os.remove(temp_bmp)
            except Exception:
                pass

def get_screen_context_summary(exclude_hwnds=None, max_context_chars=1800, do_ocr=True):
    """
    Gathers comprehensive desktop & active window context:
    - Active Application process name (e.g. Code.exe, msedge.exe)
    - Active Window clean title (e.g. 'Degree Class Grouping - Jira Service Management')
    - Active Window visible UI text / OCR lines
    Returns formatted context dict.
    """
    win_info = get_foreground_window_info(exclude_hwnds)
    hwnd = win_info.get("hwnd", 0)
    raw_title = win_info.get("title", "")
    clean_title = win_info.get("clean_title", raw_title)
    proc = win_info.get("process_name", "")
    rect = win_info.get("rect", (0, 0, 1920, 1080))

    # Fast child window text extraction (0ms)
    child_texts = capture_window_text_native(hwnd)

    # Native Windows Media WinRT OCR on window bounds
    ocr_lines = []
    if do_ocr and rect and (rect[2] - rect[0] > 60) and (rect[3] - rect[1] > 60):
        ocr_lines = run_windows_native_ocr_snippet(rect, timeout_sec=4.0)

    combined_text = []
    seen = set()
    for item in child_texts[:8]:
        item_c = item.strip()
        if item_c and item_c not in seen:
            seen.add(item_c)
            combined_text.append(item_c)

    for line in ocr_lines[:25]:
        line_c = line.strip()
        if line_c and line_c not in seen:
            seen.add(line_c)
            combined_text.append(line_c)

    clean_snippet = "\n".join(combined_text)
    if len(clean_snippet) > max_context_chars:
        clean_snippet = clean_snippet[:max_context_chars] + "..."

    return {
        "title": raw_title,
        "clean_title": clean_title,
        "process": proc,
        "rect": rect,
        "visible_text": clean_snippet,
        "has_content": bool(clean_snippet.strip() or clean_title)
    }

def format_prompt_with_screen_context(highlighted_text, screen_context, mode_prompt=""):
    """
    Constructs an intelligent prompt embedding on-screen content alongside the highlighted target.
    If no text is highlighted, the visible screen content becomes the primary focal subject.
    Explicitly instructs the LLM NOT to explain raw executable names (e.g. msedge.exe).
    """
    clean_title = screen_context.get("clean_title") or screen_context.get("title", "")
    proc = screen_context.get("process", "")
    vis_text = screen_context.get("visible_text", "")

    # Check if highlighted_text is just an active window fallback or actual text
    is_real_selection = bool(highlighted_text and highlighted_text.strip() and not highlighted_text.startswith("[Active Window:") and not highlighted_text.startswith("[Screen:"))

    if is_real_selection:
        context_parts = []
        if clean_title:
            context_parts.append(f"Application / Page: {clean_title} ({proc})")
        if vis_text:
            context_parts.append(f"Surrounding Screen Context:\n{vis_text}")
        context_block = "\n".join(context_parts)

        prompt = (
            f"[SURROUNDING SCREEN CONTEXT]\n{context_block}\n\n"
            f"[SELECTED FOCAL TARGET]:\n{highlighted_text}\n\n"
            f"[TASK]: {mode_prompt}"
        )
    else:
        # The user opened copilot on active screen without selecting a snippet
        content_body = vis_text if vis_text else clean_title
        prompt = (
            f"[VISIBLE ON-SCREEN CONTENT]:\n{content_body}\n\n"
            f"[ACTIVE WINDOW / ENVIRONMENT]:\nPage / Document: '{clean_title}' ({proc})\n\n"
            f"[TASK]: The user triggered the copilot on this active screen without selecting a snippet.\n"
            f"Analyze and respond based on the VISIBLE ON-SCREEN CONTENT above: {mode_prompt}\n"
            f"IMPORTANT DIRECTIVE: Focus completely on the actual content, document, inquiry, or code shown on screen. "
            f"Do NOT explain what the application executable (e.g. '{proc}', msedge.exe, chrome.exe) is."
        )

    return prompt
