"""
Zero-Dependency Windows SAPI / System.Speech Text-to-Speech Engine for wat-this.
Uses Windows built-in SpeechSynthesizer via background subprocess.
Zero external pip packages, zero native DLLs, 100% offline.
"""
import re
import subprocess
import threading

_active_process = None
_lock = threading.Lock()

def clean_text_for_speech(text):
    """Strips Markdown syntax, code blocks, and URLs so speech sounds natural."""
    if not text:
        return ""
    # Remove code blocks
    cleaned = re.sub(r'```[\s\S]*?```', ' Code block omitted. ', text)
    # Remove inline code
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
    # Remove URLs
    cleaned = re.sub(r'http[s]?://\S+', '', cleaned)
    # Remove markdown symbols (*, _, #, >, -)
    cleaned = re.sub(r'[*_#>\-\[\]\(\)]', ' ', cleaned)
    # Clean up excess spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def stop_speech():
    """Immediately halts any currently speaking synthesizer."""
    global _active_process
    with _lock:
        if _active_process:
            try:
                _active_process.terminate()
            except Exception:
                pass
            _active_process = None

def speak_async(text):
    """Speaks the text aloud in the background without blocking the UI."""
    global _active_process
    stop_speech()
    
    clean_text = clean_text_for_speech(text)
    if not clean_text:
        return
        
    def _worker():
        global _active_process
        # PowerShell command using standard .NET System.Speech.Synthesis
        ps_script = (
            "$text = [Console]::In.ReadToEnd(); "
            "Add-Type -AssemblyName System.Speech; "
            "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$synth.Rate = 1; "
            "$synth.Volume = 100; "
            "$synth.Speak($text);"
        )
        
        try:
            p = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8"
            )
            with _lock:
                _active_process = p
                
            p.communicate(input=clean_text)
        except Exception as e:
            print(f"[WARN] TTS speech output failed: {e}")
        finally:
            with _lock:
                if _active_process == p:
                    _active_process = None

    threading.Thread(target=_worker, daemon=True).start()
