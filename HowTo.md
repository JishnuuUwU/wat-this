# Setup and Usage Guide: `wat-this`

This guide walks you through setting up, configuring, using, and managing the `wat-this` desktop assistant on Windows.

---

## 1. Prerequisites

1. **Operating System**: Windows 10 or 11 (64-bit).
2. **Python**: Python 3.10+ installed.
   > **Note**: During Python setup, ensure **"Add python.exe to PATH"** is checked.
3. **Ollama**: Download and install the Windows client from [ollama.com/download](https://ollama.com/download).

---

## 2. Environment Setup

1. Open PowerShell and navigate to the project directory:
   ```powershell
   cd c:\Users\jishn\Documents\project\wat-this
   ```

2. *(Recommended)* Create and activate an isolated Python virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   > If PowerShell restricts script execution, run:  
   > `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

3. Install required packages:
   ```powershell
   pip install PyQt6 requests pyperclip keyboard duckduckgo_search
   ```

---

## 3. First-Time Setup Wizard

To launch the setup wizard:
- Simply **double-click `SETUP.bat`** in the project folder.

### What the Wizard Does:
- **1. Engine Status**: Probes `http://localhost:11434/api/version` to confirm Ollama is active. Inspects Python 3.12 status and available physical RAM.
- **2. Model Tiers & Installation**:
  - **Lite Tier (`< 2 GB RAM`)**: Installs `smollm2:1.7b` (Hugging Face). Fast, minimal memory, offline.
  - **Normal Tier (`3 – 5 GB RAM`)**: Installs `llama3.2:3b` (Meta). Balanced coding analogies + web search. *(Recommended)*
  - **Extreme Tier (`6 – 10 GB RAM`)**: Installs `mistral:7b` (Mistral AI). Deep technical reasoning and code analysis.
  - Select your preferred tier and click **"Install / Pull Selected Tier Model"**. A live progress bar will track the download percentage and byte count directly from Ollama.
  - Once finished, click **"Set as Active Tier"**.
- **3. Preferences**:
  - Customize the global hotkey (default: `ctrl+alt+space`).
  - Toggle **Auto-copy** (simulates `Ctrl+C` when the hotkey is triggered).
  - Adjust HUD linger duration before auto-fade.
- **4. Launch**: Click the **"Launch wat-this"** button at the bottom right.

---

## 4. Daily Usage Workflow

1. **Start wat-this**:
   Click **"Launch wat-this"** in the Setup Wizard, or run:
   ```powershell
   pythonw src/wat_this.py
   ```
   The assistant runs silently in the background.

2. **Trigger the Explainer**:
   - Highlight any unfamiliar term, error log, or code snippet in any browser, IDE, or document.
   - Press **`Ctrl + Alt + Space`**.
   - The HUD card smoothly fades in adjacent to your cursor and begins following mouse movements.
   - For code, it gives an intuitive real-world analogy. For concepts, it pulls live context.

3. **Dismiss the Card**:
   - Press **`Escape`** for immediate dismissal.
   - Or click anywhere on the card.
   - Or wait 14 seconds for the automatic fade-out animation.

4. **Switching Tiers on the Fly**:
   - Right-click the `wat-this` icon in the system tray.
   - Expand the **Model Tier** menu and select **Lite**, **Normal**, or **Extreme**. The HUD immediately updates its active profile.

5. **Exiting**:
   - Right-click the system tray icon and select **Quit wat-this**.

---

## 5. Uninstallation & Disk Cleanup

To reclaim storage space taken by downloaded models:

1. Open the wizard: Double-click **`SETUP.bat`**.
2. Navigate to the **"4. Uninstall & Cleanup"** tab.
3. The wizard enumerates all `wat-this` models on your system alongside their exact disk footprints (e.g. `llama3.2:3b — 2.00 GB`).
4. Click **Delete** next to any model to immediately remove it via the Ollama engine.
5. Click **"Reset Config to Defaults"** if you want to reset your local preferences.

---

## 6. Troubleshooting

### Issue: "Python was not found; run without arguments to install from the Microsoft Store..."
**Cause**: The Windows App Execution Alias is intercepting the `python` command.  
**Fix**:
1. Open Windows **Settings** > **Apps** > **Advanced app settings** > **App execution aliases**.
2. Turn off the toggles for **App Installer (python.exe)** and **App Installer (python3.exe)**.
3. Re-open your terminal.

### Issue: "Engine Offline: Ensure your local Ollama server is running (`ollama serve`)."
**Fix**:
1. Check that the Ollama app is running in your Windows tray.
2. If not running, open a terminal and execute:
   ```powershell
   ollama serve
   ```

### Issue: Hotkey does not trigger inside certain applications
**Cause**: If the active window is running with Administrator permissions (e.g. Task Manager or an elevated shell), standard Windows user-space keyboard hooks are blocked for security.  
**Fix**: Start your terminal / application by right-clicking and selecting **Run as Administrator**.
