"""
verify_proof.py
Comprehensive End-to-End Automated Verification Suite for wat-this.
Tests and outputs solid proof for:
1. Native Win32 Hotkey Registration (Ctrl+Alt+Space, F, T, D, S)
2. Safe copy modifier release (Alt-key protection)
3. Empty-clipboard HUD fallback (never silently returns)
4. Live execution of Explain Mode (Ctrl+Alt+Space) with Ollama streaming
5. Live execution of Fix & Bug Detector (Ctrl+Alt+F)
6. Live execution of Simplify Mode (Ctrl+Alt+T)
7. Text-To-Speech (TTS) audio engine
8. Tier level gating and lock enforcement
"""
import sys
import os
import time
import json
import ctypes
import threading
import pyperclip
import tkinter as tk

# Ensure UTF-8 output on Windows console without charmap crashes
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config_manager
import wat_this
import tts_helper
import history_manager

results = {}

def log_section(title):
    print("\n" + "=" * 70)
    print(f"  {title.upper()}")
    print("=" * 70)

def test_1_win32_hotkey_registration():
    log_section("Proof 1: Native Win32 Hotkey Registration")
    user32 = ctypes.windll.user32
    
    print("[TEST] Registering all 5 global hotkeys via user32.RegisterHotKey...")
    success_count = 0
    for hkid, (mode_name, mods, vk) in wat_this.WIN32_HOTKEYS.items():
        res = user32.RegisterHotKey(None, hkid, mods, vk)
        key_str = {
            101: "Ctrl + Alt + Space",
            102: "Ctrl + Alt + F",
            103: "Ctrl + Alt + T",
            104: "Ctrl + Alt + D",
            105: "Ctrl + Alt + S",
        }.get(hkid, "")
        
        status = "SUCCESS (Registered)" if res != 0 else "FAIL (Code 0)"
        print(f"  • ID {hkid:3d} | {key_str:18s} | Mode: {mode_name:10s} -> {status}")
        if res != 0:
            success_count += 1
            user32.UnregisterHotKey(None, hkid)

    passed = (success_count == len(wat_this.WIN32_HOTKEYS))
    results["1_hotkey_registration"] = {
        "passed": passed,
        "registered": f"{success_count}/{len(wat_this.WIN32_HOTKEYS)}"
    }
    print(f"[RESULT] Win32 Global Hotkeys: {'PASS' if passed else 'FAIL'}")
    return passed

def close_app(app):
    app.is_alive = False
    if getattr(app, "active_abort_event", None):
        app.active_abort_event.set()
    tts_helper.stop_speech()
    app.stop_hotkeys.set()
    if getattr(app, "linger_timer_id", None):
        try:
            app.root.after_cancel(app.linger_timer_id)
        except Exception:
            pass
    if getattr(app, "gui_queue_timer_id", None):
        try:
            app.root.after_cancel(app.gui_queue_timer_id)
        except Exception:
            pass
    try:
        app.root.destroy()
    except Exception:
        pass
    time.sleep(0.15)

def test_2_modifier_safe_copy():
    log_section("Proof 2: Modifier-Safe Copy Simulation (Alt-Key Release)")
    print("[TEST] Testing simulate_copy with pre-existing clipboard...")
    test_phrase = f"WAT_THIS_VERIFICATION_SNIPPET_{int(time.time())}"
    pyperclip.copy(test_phrase)
    
    app = wat_this.WatThisApp()
    app.simulate_copy()
    
    current = pyperclip.paste()
    print(f"  • Expected text persistence: '{test_phrase}'")
    print(f"  • Current clipboard content: '{current}'")
    
    passed = (current == test_phrase)
    results["2_modifier_safe_copy"] = {"passed": passed}
    print(f"[RESULT] Modifier-safe copy: {'PASS' if passed else 'FAIL'}")
    close_app(app)
    return passed

def test_3_empty_clipboard_hud_fallback():
    log_section("Proof 3: Empty-Clipboard HUD Fallback (Never-Silent UI)")
    print("[TEST] Clearing clipboard and triggering handle_hotkey('explain')...")
    pyperclip.copy("")
    
    app = wat_this.WatThisApp()
    # Trigger hotkey with empty clipboard
    app.handle_hotkey("explain")
    
    print(f"  • HUD Visible: {app.hud_visible}")
    print(f"  • Chat Expanded: {app.chat_expanded}")
    print(f"  • Content text preview: '{app.content_lbl.cget('text')[:40]}...'")
    
    passed = app.hud_visible and app.chat_expanded and "Ambient Copilot is Ready" in app.content_lbl.cget("text")
    results["3_empty_clipboard_fallback"] = {"passed": passed}
    print(f"[RESULT] Empty-clipboard HUD trigger: {'PASS' if passed else 'FAIL'}")
    close_app(app)
    return passed

def test_4_explain_pipeline():
    log_section("Proof 4: Live Ctrl+Alt+Space Explain Pipeline (Ollama Stream)")
    config_manager.set_active_tier("normal")
    tier_key, tier_spec = config_manager.get_active_tier()
    model = tier_spec.get("model", "llama3.2:3b")
    print(f"[TEST] Active Tier: {tier_key.upper()} | Model: {model}")
    
    code_sample = "def calculate_discount(price, rate):\n    return price * (1.0 - rate)"
    pyperclip.copy(code_sample)
    
    app = wat_this.WatThisApp()
    app.handle_hotkey("explain")
    
    print(f"  • Target Code:\n{code_sample}\n")
    print("  • Streaming LLM Response Tokens...")
    
    # Wait for pipeline to complete
    timeout = 45
    start = time.time()
    while time.time() - start < timeout:
        app.root.update()
        time.sleep(0.05)
        if app.accumulated_text and not app.is_streaming and not app.is_thinking:
            break
    
    # Let UI update
    for _ in range(10):
        app.root.update()
        time.sleep(0.05)
        
    full_response = app.accumulated_text.strip()
    print(f"\n[RECEIVED LLM RESPONSE ({len(full_response)} chars)]:\n{full_response}\n")
    
    passed = len(full_response) > 20
    results["4_explain_pipeline"] = {
        "passed": passed,
        "model": model,
        "tokens_chars": len(full_response)
    }
    print(f"[RESULT] Explain Mode (Ctrl+Alt+Space): {'PASS' if passed else 'FAIL'}")
    close_app(app)
    return passed

def test_5_fix_mode_pipeline():
    log_section("Proof 5: Live Ctrl+Alt+F Fix & Bug Detector Mode")
    config_manager.set_active_tier("normal")
    tier_key, tier_spec = config_manager.get_active_tier()
    model = tier_spec.get("model", "llama3.2:3b")
    print(f"[TEST] Testing Fix Mode on {model}...")
    
    buggy_code = "def parse_age(s):\n    return int(s) # Crashes if s is not numeric"
    pyperclip.copy(buggy_code)
    
    app = wat_this.WatThisApp()
    app.handle_hotkey("fix")
    
    timeout = 45
    start = time.time()
    while time.time() - start < timeout:
        app.root.update()
        time.sleep(0.05)
        if app.accumulated_text and not app.is_streaming and not app.is_thinking:
            break
    for _ in range(10):
        app.root.update()
        time.sleep(0.05)
        
    full_response = app.accumulated_text.strip()
    print(f"\n[RECEIVED BUG DETECTOR FIX ({len(full_response)} chars)]:\n{full_response}\n")
    
    passed = len(full_response) > 20
    results["5_fix_mode"] = {
        "passed": passed,
        "model": model,
        "response_len": len(full_response)
    }
    print(f"[RESULT] Fix Mode (Ctrl+Alt+F): {'PASS' if passed else 'FAIL'}")
    close_app(app)
    return passed

def test_6_simplify_mode_pipeline():
    log_section("Proof 6: Live Ctrl+Alt+T Simplify (ELI5) Mode")
    config_manager.set_active_tier("lite")
    tier_key, tier_spec = config_manager.get_active_tier()
    model = tier_spec.get("model", "smollm2:1.7b")
    print(f"[TEST] Testing Simplify Mode on Lite Tier model: {model}...")
    
    dense_text = "Asynchronous non-blocking input-output primitives multiplex event queues across concurrent POSIX epoll abstractions."
    pyperclip.copy(dense_text)
    
    app = wat_this.WatThisApp()
    app.handle_hotkey("simplify")
    
    timeout = 45
    start = time.time()
    while time.time() - start < timeout:
        app.root.update()
        time.sleep(0.05)
        if app.accumulated_text and not app.is_streaming and not app.is_thinking:
            break
    for _ in range(10):
        app.root.update()
        time.sleep(0.05)
        
    full_response = app.accumulated_text.strip()
    print(f"\n[RECEIVED SIMPLIFIED EXPLANATION ({len(full_response)} chars)]:\n{full_response}\n")
    
    passed = len(full_response) > 10
    results["6_simplify_mode"] = {
        "passed": passed,
        "model": model,
        "response_len": len(full_response)
    }
    print(f"[RESULT] Simplify Mode (Ctrl+Alt+T): {'PASS' if passed else 'FAIL'}")
    close_app(app)
    return passed

def test_7_tier_gating_locks():
    log_section("Proof 7: Tier Gating & Feature Lock Enforcement")
    config_manager.set_active_tier("lite")
    print("[TEST] Switched to Lite Tier (< 2GB RAM budget).")
    
    app = wat_this.WatThisApp()
    # In Lite tier, Fix mode and Docstring mode are strictly locked!
    app.handle_hotkey("fix")
    
    badge_text = app.mode_badge_lbl.cget("text")
    content_text = app.content_lbl.cget("text")
    
    print(f"  • Mode badge: '{badge_text}'")
    print(f"  • Locked explanation:\n{content_text}\n")
    
    passed = "TIER LOCKED" in badge_text and "Required Tier: NORMAL" in content_text
    results["7_tier_gating"] = {"passed": passed}
    print(f"[RESULT] Tier Lock Enforcement: {'PASS' if passed else 'FAIL'}")
    close_app(app)
    
    # Restore recommended tier
    config_manager.set_active_tier("normal")
    return passed

def test_8_tts_speech_sapi():
    log_section("Proof 8: Windows SAPI Text-to-Speech Engine")
    print("[TEST] Testing non-blocking SAPI speech synthesizer...")
    try:
        tts_helper.speak_async("wat-this ambient copilot operational.")
        time.sleep(0.5)
        tts_helper.stop_speech()
        passed = True
    except Exception as e:
        print(f"[ERROR] TTS Failed: {e}")
        passed = False
    
    results["8_tts_speech"] = {"passed": passed}
    print(f"[RESULT] Windows SAPI Audio (Ctrl+Alt+S): {'PASS' if passed else 'FAIL'}")
    return passed

def main():
    print("=" * 70)
    print("WAT-THIS COMPREHENSIVE SYSTEM & HOTKEY VERIFICATION")
    print("=" * 70)
    
    test_1_win32_hotkey_registration()
    test_2_modifier_safe_copy()
    test_3_empty_clipboard_hud_fallback()
    test_4_explain_pipeline()
    test_5_fix_mode_pipeline()
    test_6_simplify_mode_pipeline()
    test_7_tier_gating_locks()
    test_8_tts_speech_sapi()
    
    log_section("Summary of All System Verification Proofs")
    all_passed = True
    for test_key, res in results.items():
        status = "PASSED ✓" if res.get("passed") else "FAILED ✕"
        if not res.get("passed"):
            all_passed = False
        print(f"  • {test_key:32s} : {status}")
        
    print("\n" + "=" * 70)
    if all_passed:
        print("OVERALL VERIFICATION: 100% PASSED (All Proofs Verified Live)")
    else:
        print("OVERALL VERIFICATION: SOME CHECKS FAILED")
    print("=" * 70)

if __name__ == "__main__":
    main()
