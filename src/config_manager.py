import os
import sys
import json
import urllib.request
import subprocess

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SRC_DIR)
BASE_DIR = SRC_DIR

CONFIG_PATH = os.path.join(SRC_DIR, "config.json")
if os.path.exists(os.path.join(PROJECT_ROOT, "assets")):
    ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
else:
    ASSETS_DIR = os.path.join(SRC_DIR, "assets")

ICON_PATH = os.path.join(ASSETS_DIR, "icon.png")
ICON_ICO_PATH = os.path.join(ASSETS_DIR, "icon.ico")

DEFAULT_CONFIG = {
    "active_tier": "normal",
    "hotkey": "ctrl+alt+space",
    "auto_copy": True,
    "linger_duration_ms": 14000,
    "max_clipboard_chars": 12000,
    "ollama_url": "http://127.0.0.1:11434",
    "autostart": False,
    "tts_enabled": False,
    "tts_hotkey": "ctrl+alt+s",
    "blur_enabled": True,
    "hud_opacity": 0.92,
    "modes": {
        "explain": {
            "name": "Explain & Teach",
            "key_shortcut": "1",
            "letter_shortcut": "e",
            "icon": "⚡",
            "required_tier": "lite",
            "system_prompt": "You are a clear, friendly educator explaining things to a curious non-technical person. Use one concrete real-world analogy. Never use jargon. Be warm and direct.",
            "prompt_suffix": "Explain what this is in plain English using a helpful real-world analogy. 2–3 sentences max. No bullet lists, no headers, no filler phrases like 'Great question!'.",
            "max_tokens": 320,
            "temperature": 0.2
        },
        "fix": {
            "name": "Fix Code",
            "key_shortcut": "2",
            "letter_shortcut": "f",
            "icon": "🔧",
            "required_tier": "lite",
            "system_prompt": "You are a senior software engineer performing code repair. Your ONLY job is to output: 1) a single sentence naming the bug, then 2) the complete corrected code block. No explanations beyond the one-line diagnosis. No greetings. Output the fixed code immediately.",
            "prompt_suffix": "Find and fix ALL bugs, syntax errors, and logic flaws in this code. Output format: one sentence starting with 'Bug:' naming what was wrong, then the complete corrected code in a fenced code block. Nothing else.",
            "max_tokens": 800,
            "temperature": 0.05
        },
        "simplify": {
            "name": "Simplify (ELI5)",
            "key_shortcut": "3",
            "letter_shortcut": "s",
            "icon": "💡",
            "required_tier": "lite",
            "system_prompt": "You are a rewriter. Your ONLY task is to rewrite the given text in simpler language a 10-year-old can understand. Output ONLY the rewritten version — no meta commentary, no 'Here is the simplified version:', no explanations of what you did.",
            "prompt_suffix": "Rewrite this text in simple language a 10-year-old can understand. Use short sentences. Replace every technical term with an everyday word. Output ONLY the rewritten text.",
            "max_tokens": 400,
            "temperature": 0.25
        },
        "translate": {
            "name": "Quick Translate",
            "key_shortcut": "4",
            "letter_shortcut": "t",
            "icon": "🌐",
            "required_tier": "lite",
            "system_prompt": "You are a professional translator. First identify the source language. If the text is already in plain English, say so in one sentence and stop. Otherwise translate accurately into natural English, preserving meaning and tone.",
            "prompt_suffix": "Step 1: Identify the source language (one word). Step 2: If it is English, output 'Already in English.' and stop. Step 3: Otherwise output the natural English translation followed by a one-sentence note if any cultural idiom or slang was present.",
            "max_tokens": 500,
            "temperature": 0.1
        },
        "regex": {
            "name": "Regex & Shell",
            "key_shortcut": "5",
            "letter_shortcut": "r",
            "icon": "🔍",
            "required_tier": "lite",
            "system_prompt": "You are a regex and shell command expert. If the input is not a regex or shell command, say so in one sentence and offer to help instead. Otherwise break it down component by component using a numbered list.",
            "prompt_suffix": "Identify whether this is a regular expression, a shell/terminal command, or neither. If neither, say what it is and stop. If it is a regex or command: list each component on its own numbered line, explain what it matches/does in plain English, and give one practical example of input it would match or a use-case.",
            "max_tokens": 500,
            "temperature": 0.1
        },
        "polish": {
            "name": "Polish Prose",
            "key_shortcut": "6",
            "letter_shortcut": "p",
            "icon": "✍️",
            "required_tier": "normal",
            "system_prompt": "You are a professional copy editor. Your ONLY output is the corrected and polished version of the text provided. Do NOT add any preamble, commentary, explanation, or headers. Output only the polished text itself.",
            "prompt_suffix": "Rewrite this text with correct grammar, punctuation, and a crisp professional tone. Output ONLY the rewritten text — no 'Here is the polished version:', no commentary before or after.",
            "max_tokens": 600,
            "temperature": 0.3
        },
        "docstring": {
            "name": "Docstrings & Types",
            "key_shortcut": "7",
            "letter_shortcut": "d",
            "icon": "📝",
            "required_tier": "extreme",
            "system_prompt": "You are a senior engineer writing documentation. Detect the programming language. Output only the original code with docstrings and type annotations added in the correct convention for that language (Python: Google-style docstring + type hints; JS/TS: JSDoc; Java: Javadoc). No explanation, no commentary.",
            "prompt_suffix": "Add complete professional docstrings and type annotations to this code. Follow the official convention for the detected language. Output the complete annotated code in a fenced code block. Nothing else.",
            "max_tokens": 1000,
            "temperature": 0.05
        },
        "audit": {
            "name": "Security Audit",
            "key_shortcut": "8",
            "letter_shortcut": "a",
            "icon": "🛡️",
            "required_tier": "extreme",
            "system_prompt": "You are an OWASP-certified application security engineer. Perform a rigorous audit. Output a structured report with clearly labelled sections. Be specific and technical — name exact line numbers or patterns where possible.",
            "prompt_suffix": "Audit this code and output a structured report with these exact sections:\n**Security Vulnerabilities** (OWASP category, severity: CRITICAL/HIGH/MEDIUM/LOW, description)\n**Performance & Complexity** (Big-O, bottlenecks)\n**Edge Cases & Exceptions** (unhandled inputs, race conditions)\n**Recommended Fixes** (concrete, actionable)\nBe specific. Name exact patterns or line locations.",
            "max_tokens": 1400,
            "temperature": 0.05
        },
        "unittest": {
            "name": "Unit Test Generator",
            "key_shortcut": "9",
            "letter_shortcut": "u",
            "icon": "🧪",
            "required_tier": "extreme",
            "system_prompt": "You are a test engineer. Detect the programming language and testing framework (pytest for Python, Jest for JS, JUnit for Java, etc.). Output ONLY runnable test code — no prose, no explanation, just the complete test file.",
            "prompt_suffix": "Generate a complete, runnable unit test file for this code. Cover: happy path, edge cases (empty input, None/null, boundary values), expected exceptions, and one mock if external I/O is involved. Output ONLY the test code in a fenced code block — no explanation before or after.",
            "max_tokens": 1600,
            "temperature": 0.05
        }
    },
    "tiers": {
        "lite": {
            "name": "Lite",
            "model": "smollm2:1.7b",
            "family": "Hugging Face SmolLM2",
            "ram_target": "< 4 GB RAM",
            "tagline": "Ultra-Low Memory Footprint (< 4 GB)",
            "description": "Optimized for entry hardware (< 4 GB RAM). Solid matte minimalist theme with zero Acrylic GPU overhead, sub-2GB RAM allocation, and rapid response.",
            "web_search": False,
            "interactive_chat": False,
            "tts_audio": False,
            "allowed_modes": ["explain", "fix", "simplify", "translate", "regex"],
            "max_chat_turns": 0,
            "num_ctx": 1024,
            "keep_alive": "5m",
            "max_tokens": 512,
            "system_prompt": "You are an ultra-concise, plain-English explainer. Explain what the target text or code means for an absolute beginner. Keep your entire response within 2 gentle, clear sentences. No jargon."
        },
        "normal": {
            "name": "Normal",
            "model": "llama3.1:8b",
            "family": "Meta Llama 3.1",
            "ram_target": "6 – 10 GB RAM",
            "tagline": "Balanced Intelligence (Recommended)",
            "description": "Balanced high-performance profile (6 – 10 GB RAM). Adds tone & prose polish, web grounding, 3-turn interactive chat, hardware Acrylic blur, and SAPI audio.",
            "web_search": True,
            "interactive_chat": True,
            "tts_audio": True,
            "allowed_modes": ["explain", "fix", "simplify", "translate", "regex", "polish"],
            "max_chat_turns": 3,
            "num_ctx": 2048,
            "keep_alive": "15m",
            "max_tokens": 2048,
            "system_prompt": "You are an ultra-clear, calming, plain-English educator. Explain what the target text or code means for an absolute beginner. Do not use complex jargon. If it is code, state what it does in plain words using an everyday real-world analogy. Keep your full response contained within 3 to 4 gentle, clear sentences."
        },
        "extreme": {
            "name": "Extreme (Expert)",
            "model": "qwen2.5:14b",
            "family": "Qwen 2.5 / Mistral",
            "ram_target": "12 – 16 GB RAM",
            "tagline": "Deep Technical Reasoning & Complete Toolset",
            "description": "Full enterprise engineering suite for workstation systems (12 – 16 GB RAM). Unlocks deep security audits, unit test generation, docstrings, unlimited chat, and frosted glass aesthetic.",
            "web_search": True,
            "interactive_chat": True,
            "tts_audio": True,
            "allowed_modes": ["explain", "fix", "simplify", "translate", "regex", "polish", "docstring", "audit", "unittest"],
            "max_chat_turns": 20,
            "num_ctx": 4096,
            "keep_alive": "30m",
            "max_tokens": 4096,
            "system_prompt": "You are a senior principal engineer and technical mentor. Provide a precise, highly structured explanation of the target text or code. Explain core mechanics, highlight subtle edge cases or bugs if present, and give practical implementation insights in concise, clean bullet points or short paragraphs."
        }
    }
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            config = DEFAULT_CONFIG.copy()
            config.update(data)
            return config
    except Exception as e:
        print(f"[WARN] Error reading config.json ({e}). Falling back to defaults.")
        return DEFAULT_CONFIG.copy()

def save_config(config_dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save config.json: {e}")
        return False

def get_active_tier():
    cfg = load_config()
    tier_key = cfg.get("active_tier", "normal")
    return tier_key, cfg.get("tiers", {}).get(tier_key, DEFAULT_CONFIG["tiers"]["normal"])

def set_active_tier(tier_key):
    cfg = load_config()
    if tier_key in cfg.get("tiers", {}):
        cfg["active_tier"] = tier_key
        save_config(cfg)
        return True
    return False

def get_tier_spec(tier_key=None):
    cfg = load_config()
    if not tier_key:
        tier_key = cfg.get("active_tier", "normal")
    return cfg.get("tiers", {}).get(tier_key, DEFAULT_CONFIG["tiers"]["normal"])

def get_modes():
    cfg = load_config()
    return cfg.get("modes", DEFAULT_CONFIG["modes"])

def get_mode_spec(mode_name):
    modes = get_modes()
    return modes.get(mode_name, DEFAULT_CONFIG["modes"].get("explain"))

def is_mode_allowed_in_tier(mode_name, tier_key=None):
    spec = get_tier_spec(tier_key)
    allowed = spec.get("allowed_modes", ["explain", "simplify", "fix", "docstring"])
    return mode_name in allowed

def is_interactive_chat_allowed(tier_key=None):
    spec = get_tier_spec(tier_key)
    return spec.get("interactive_chat", False)

def is_tts_allowed(tier_key=None):
    spec = get_tier_spec(tier_key)
    return spec.get("tts_audio", False)

def is_web_search_allowed(tier_key=None):
    spec = get_tier_spec(tier_key)
    return spec.get("web_search", False)

def get_tier_actions(tier_key=None):
    """
    Returns an ordered list of dicts for the minimalist Action Picker palette:
    [{'mode': 'explain', 'name': 'Explain & Teach', 'shortcut': '1', 'letter': 'e', 'icon': '⚡', 'allowed': True}, ...]
    """
    spec = get_tier_spec(tier_key)
    allowed_modes = spec.get("allowed_modes", [])
    modes = get_modes()

    order = ["explain", "fix", "simplify", "translate", "regex", "polish", "docstring", "audit", "unittest"]
    actions = []
    idx = 1
    for m in order:
        if m in modes:
            m_spec = modes[m]
            actions.append({
                "mode": m,
                "name": m_spec.get("name", m.capitalize()),
                "shortcut": str(idx),
                "key": str(idx),
                "letter": m_spec.get("letter_shortcut", m[0]).lower(),
                "icon": m_spec.get("icon", "⚡"),
                "allowed": m in allowed_modes,
                "required_tier": m_spec.get("required_tier", "lite")
            })
            idx += 1
    return actions

import time

def find_ollama_binary():
    """Locates the Ollama executable on the system."""
    import shutil
    candidate = shutil.which("ollama")
    if candidate and os.path.exists(candidate):
        return candidate
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        p = os.path.join(local_app_data, r"Programs\Ollama\ollama.exe")
        if os.path.exists(p):
            return p
    program_files = os.environ.get("ProgramFiles", "")
    if program_files:
        p = os.path.join(program_files, r"Ollama\ollama.exe")
        if os.path.exists(p):
            return p
    return "ollama"

def normalize_ollama_url(url="http://localhost:11434"):
    """Normalizes Ollama URL, preferring 127.0.0.1 on Windows to bypass IPv6 resolution delays/failures."""
    if not url:
        return "http://127.0.0.1:11434"
    u = url.rstrip("/")
    if "localhost" in u:
        return u.replace("localhost", "127.0.0.1")
    return u

def is_ollama_online(url="http://127.0.0.1:11434"):
    """Checks if Ollama server is responding to HTTP queries."""
    urls = [url, "http://127.0.0.1:11434", "http://localhost:11434"]
    seen = set()
    for u in urls:
        if not u:
            continue
        clean = u.rstrip("/")
        if clean in seen:
            continue
        seen.add(clean)
        try:
            req = urllib.request.Request(f"{clean}/api/version")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return True
        except Exception:
            continue
    return False

def ensure_ollama_running(url="http://127.0.0.1:11434", wait_seconds=6):
    """Checks if Ollama is online, and if not, automatically launches 'ollama serve' in the background."""
    if is_ollama_online(url):
        return True
    
    ollama_bin = find_ollama_binary()
    try:
        # CREATE_NO_WINDOW (0x08000000) spawns Ollama silently without popping up a console
        subprocess.Popen([ollama_bin, "serve"], creationflags=0x08000000)
    except Exception as e:
        print(f"[WARN] Failed to auto-spawn Ollama daemon ({ollama_bin}): {e}")
        return False
        
    start_t = time.time()
    while time.time() - start_t < wait_seconds:
        time.sleep(0.4)
        if is_ollama_online(url):
            return True
    return False

def get_installed_ollama_models(ollama_url="http://localhost:11434"):
    """Queries Ollama API tags to return a list of model names installed on the system."""
    targets = [ollama_url, "http://127.0.0.1:11434", "http://localhost:11434"]
    seen = set()
    for target in targets:
        if not target:
            continue
        clean = target.rstrip("/")
        if clean in seen:
            continue
        seen.add(clean)
        try:
            req = urllib.request.Request(f"{clean}/api/tags")
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [m.get("name") for m in data.get("models", []) if "name" in m]
        except Exception:
            continue
    return []

def get_startup_shortcut_path():
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return None
    return os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup\wat-this.lnk")

def is_windows_autostart_enabled():
    path = get_startup_shortcut_path()
    return os.path.exists(path) if path else False

def set_windows_autostart(enable=True):
    """Configures Windows Startup shortcut via native Windows WScript.Shell (zero DLLs)."""
    shortcut_path = get_startup_shortcut_path()
    if not shortcut_path:
        return False, "APPDATA environment variable not found"
        
    cfg = load_config()
    cfg["autostart"] = bool(enable)
    save_config(cfg)

    if not enable:
        if os.path.exists(shortcut_path):
            try:
                os.remove(shortcut_path)
            except Exception as e:
                return False, str(e)
        return True, "Autostart disabled"

    target_bat = os.path.join(PROJECT_ROOT, "SETUP.bat")
    ps_cmd = (
        f"$s = (New-Object -COM WScript.Shell).CreateShortcut('{shortcut_path}'); "
        f"$s.TargetPath = '{target_bat}'; "
        f"$s.WorkingDirectory = '{PROJECT_ROOT}'; "
        f"$s.Save()"
    )
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            check=True,
            capture_output=True,
            text=True
        )
        return True, "Autostart enabled"
    except Exception as e:
        return False, str(e)


