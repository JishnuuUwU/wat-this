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
    "ollama_url": "http://localhost:11434",
    "autostart": False,
    "tts_enabled": False,
    "tts_hotkey": "ctrl+alt+s",
    "modes": {
        "explain": {
            "name": "Explain & Teach",
            "hotkey": "ctrl+alt+space",
            "prompt_suffix": "Explain what this is in plain English with a helpful analogy if it's code. Keep it clear, friendly, and accessible."
        },
        "fix": {
            "name": "Fix & Bug Detector",
            "hotkey": "ctrl+alt+f",
            "prompt_suffix": "Carefully analyze the target code. Identify bugs, syntax errors, or performance issues. Explain the problem concisely and provide the corrected code snippet."
        },
        "simplify": {
            "name": "Simplify (ELI5)",
            "hotkey": "ctrl+alt+t",
            "prompt_suffix": "Rewrite and explain this text or concept for an absolute beginner as if explaining to a 10-year-old. Remove all technical jargon."
        },
        "docstring": {
            "name": "Generate Docstrings & Types",
            "hotkey": "ctrl+alt+d",
            "prompt_suffix": "Generate complete, clean, professional documentation/docstrings and type hints for this code. Format it according to the language's best conventions."
        }
    },
    "tiers": {
        "lite": {
            "name": "Lite",
            "model": "smollm2:1.7b",
            "family": "Hugging Face SmolLM2",
            "ram_target": "< 2 GB RAM",
            "tagline": "Fastest & Ultra-Low Memory Footprint",
            "description": "Strictly optimized for sub-2GB RAM usage. Uses Hugging Face's compact on-device model for lightning-fast plain-language explanations with zero web overhead.",
            "web_search": False,
            "keep_alive": "1m",
            "max_tokens": 2048,
            "system_prompt": "You are an ultra-concise, plain-English explainer. Explain what the target text or code means for an absolute beginner. Keep your entire response within 2 gentle, clear sentences. No jargon."
        },
        "normal": {
            "name": "Normal",
            "model": "llama3.2:3b",
            "family": "Meta Llama 3.2",
            "ram_target": "3 – 5 GB RAM",
            "tagline": "Balanced Intelligence (Recommended)",
            "description": "Powered by Meta's Llama 3.2 3B. High-accuracy instruction following, code analogies, and DuckDuckGo live web search enrichment.",
            "web_search": True,
            "keep_alive": "5m",
            "max_tokens": 4096,
            "system_prompt": "You are an ultra-clear, calming, plain-English educator. Explain what the target text or code means for an absolute beginner. Do not use complex jargon. If it is code, state what it does in plain words using an everyday real-world analogy. Keep your full response contained within 3 to 4 gentle, clear sentences."
        },
        "extreme": {
            "name": "Extreme (Expert)",
            "model": "mistral:7b",
            "family": "Mistral AI",
            "ram_target": "6 – 10 GB RAM",
            "tagline": "Deep Technical Reasoning & Code Analysis",
            "description": "Powered by Mistral AI 7B. Comprehensive reasoning engine delivering architectural analysis, code edge-case detection, and synthesis.",
            "web_search": True,
            "keep_alive": "15m",
            "max_tokens": 8192,
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

def get_installed_ollama_models(ollama_url="http://localhost:11434"):
    """Queries Ollama API tags to return a list of model names installed on the system."""
    try:
        req = urllib.request.Request(f"{ollama_url.rstrip('/')}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name") for m in data.get("models", []) if "name" in m]
    except Exception:
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

