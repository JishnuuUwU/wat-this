"""
History Manager for wat-this.
Provides persistent, zero-dependency local JSON storage for explained snippets,
modes, models, latency metrics, and one-click Markdown export.
"""
import os
import json
import time
import threading
from datetime import datetime

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SRC_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

_lock = threading.Lock()

def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

def load_history():
    _ensure_data_dir()
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with _lock:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[WARN] Could not load history ({e}). Initializing empty list.")
        return []

def save_history(history_list):
    _ensure_data_dir()
    try:
        with _lock:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history_list, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save history: {e}")
        return False

def add_entry(snippet, response, tier="normal", mode="explain", model="", latency_s=None):
    """Appends a new query/explanation entry to local history."""
    if not snippet or not response:
        return
    
    entries = load_history()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "id": int(time.time() * 1000),
        "timestamp": now_str,
        "mode": mode,
        "tier": tier,
        "model": model,
        "latency_s": round(latency_s, 2) if latency_s is not None else None,
        "snippet": snippet.strip(),
        "response": response.strip()
    }
    
    # Prepend to keep newest first
    entries.insert(0, entry)
    
    # Cap at 500 entries to conserve memory & disk
    if len(entries) > 500:
        entries = entries[:500]
        
    save_history(entries)
    return entry

def get_history(limit=50, query=None, mode=None):
    """Returns history entries filtered by search query or mode."""
    entries = load_history()
    results = []
    
    q = query.lower() if query else None
    
    for item in entries:
        if mode and item.get("mode") != mode:
            continue
        if q:
            in_snip = q in item.get("snippet", "").lower()
            in_resp = q in item.get("response", "").lower()
            in_model = q in item.get("model", "").lower()
            if not (in_snip or in_resp or in_model):
                continue
        results.append(item)
        if len(results) >= limit:
            break
            
    return results

def clear_history():
    """Clears all local history records."""
    return save_history([])

def export_to_markdown(target_path=None):
    """Exports all recorded explanations into a formatted Markdown document."""
    entries = load_history()
    lines = [
        "# wat-this Knowledge Notebook & Explanation History",
        f"*Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        f"*Total Records: {len(entries)}*",
        "",
        "---",
        ""
    ]
    
    for i, item in enumerate(entries, 1):
        mode_badge = item.get('mode', 'explain').upper()
        tier_badge = item.get('tier', 'normal').upper()
        model_name = item.get('model', 'Local AI')
        latency = f" ({item.get('latency_s')}s)" if item.get('latency_s') else ""
        
        lines.append(f"## {i}. [{mode_badge} | {tier_badge}] {item.get('timestamp')}")
        lines.append(f"- **Engine**: `{model_name}`{latency}")
        lines.append("")
        lines.append("### Highlighted Context / Snippet")
        lines.append("```")
        lines.append(item.get("snippet", ""))
        lines.append("```")
        lines.append("")
        lines.append("### Explanation / Output")
        lines.append(item.get("response", ""))
        lines.append("")
        lines.append("---")
        lines.append("")
        
    md_content = "\n".join(lines)
    
    if target_path:
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            return True, target_path
        except Exception as e:
            return False, str(e)
            
    return True, md_content
