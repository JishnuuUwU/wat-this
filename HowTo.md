# Setup and Usage Guide: `wat-this`

This guide walks you through setting up, configuring, using, and managing the `wat-this` ambient desktop copilot on Windows 10 & 11.

---

## 1. Prerequisites

1. **Operating System**: Windows 10 or 11 (64-bit). Fully compatible with **Smart App Control (SAC)** and **WDAC** via zero-DLL architecture.
2. **Python**: Python 3.10+ (Python 3.12 64-bit recommended).
3. **Ollama**: Download and install from [ollama.com/download](https://ollama.com/download) or install via winget:
   ```powershell
   winget install Ollama.Ollama -e --accept-package-agreements
   ```

---

## 2. One-Click Setup & Launch

To start using `wat-this` or customize configurations:
- **`RUN_APP.bat`**: Double-click to launch the ambient copilot in the Windows Status Bar (System Tray near the clock).
- **`SETUP.bat`**: Double-click to open the Setup & Tier Configuration Wizard (diagnostics, model installer, knowledge notebook).

---

## 3. The Setup Wizard Tabs

### Tab 1: Diagnostics
- Probes `http://localhost:11434/api/version` to confirm Ollama is active.
- Reads host physical and available RAM to suggest an optimal model tier profile (`< 4 GB` Lite, `6 – 10 GB` Normal, `12 – 16 GB` Extreme).
- Offers a one-click button to spawn the Ollama server daemon if offline.

### Tab 2: Models & Install
- **Lite Tier (`< 4 GB RAM`)**: `smollm2:1.7b` (Hugging Face).
  - *Unlocked Modes*: **Explain**, **Translate**, **Simplify**, **Fix**, **TL;DR**, **Step-by-Step**.
  - *Memory Target*: Sub-4GB RAM budget with aggressive **1m memory release**.
  - *Visual Aesthetic*: Compact solid obsidian matte (`#0D1117`), 0.98 opacity, zero blur overhead.
- **Normal Tier (`6 – 10 GB RAM`)**: `llama3.1:8b` (Meta, fallback to `llama3.2:3b`).
  - *Unlocked Modes*: All Lite modes + **Web Fact-Check & Verify**, **Terminal Command Explainer**.
  - *Memory Target*: 6 – 10 GB RAM with **5m cache**.
  - *Visual Aesthetic*: Fluid 500px width, hardware Acrylic frosted glass blur, 0.92 opacity.
- **Extreme Tier (`12 – 16 GB RAM`)**: `qwen2.5:14b` (Alibaba, fallback to `llama3.1:8b`).
  - *Unlocked Modes*: All modes + **Deep Reason & Chain-of-Thought**.
  - *Memory Target*: 12 – 16 GB RAM with **15m warm cache** and unlimited follow-up chat.
  - *Visual Aesthetic*: Luxury 560px width, deep purple frosted glass acrylic, 0.92 opacity.
- Click **"Download & Install Selected Model"** to download with live progress. Once downloaded, click **"Set as Active Profile"**.

### Tab 3: Knowledge Notebook & Exports
- Automatically logs all explained snippets, active model, latency metrics, and responses.
- Real-time search filter by keyword or model name.
- **"Export to Markdown"**: Generates a formatted `wat_this_notebook.md` notebook ready for Obsidian, Notion, or personal notes.
- **"Clear All"**: Wipes history records with confirmation.

### Tab 4: Preferences & Specialized Modes
- **Start with Windows**: One-click toggle to launch `wat-this` silently on Windows startup (uses clean `%APPDATA%\Startup` shortcut).
- **Auto-Speak with Windows TTS**: Automatically reads explanations aloud using native Windows SAPI (`Normal` & `Extreme` tiers).
- **Universal Command Palette**: Review the unified `Ctrl + Alt + Space` shortcut and option keys `[1]`–`[9]`.
- **Acrylic Blur & Frosted Glass**: Toggle native Windows 11 Acrylic blur backdrop effect.
- **HUD Linger Duration**: Set auto-dismiss timer (4 to 60 seconds).

### Tab 5: Storage & Cleanup
- View exact disk space occupied by downloaded models.
- One-click deletion of models to immediately reclaim gigabytes of disk space.

---

## 4. Universal Command Palette (`Ctrl + Alt + Space`)

All previous individual hotkeys have been unified into a single global keybind: **`Ctrl + Alt + Space`**.

### How It Works:
1. **Highlight text or code** in any application (browser, IDE, terminal, PDF reader), or **simply keep your active window open** without selecting anything to analyze the entire screen context!
2. Press **`Ctrl + Alt + Space`**.
3. A minimalist, cursor-anchored **Action Options Palette** instantly pops up at your cursor position with a preview of your highlighted snippet or active screen context.
4. **Interactive Hover Summaries**: Move your mouse over any action button or navigate using the **`↑` / `↓`** arrow keys:
   - A dedicated preview card at the bottom of the palette updates dynamically with a plain-English explanation of what the mode does, capability tags (`⚡ Fast`, `🌐 Web Grounded`, `🔧 Instant Patch`), and tier requirements.
5. Select your desired action:
   - Press numbers **`1`** through **`9`** on your keyboard.
   - Or press **`Enter`** on the highlighted item.
   - Or click any option card with your mouse.

### Action Options:

| Key | Action Option | Required Tier | Behavior |
| :---: | :--- | :--- | :--- |
| **`1`** | **Explain & Teach** | **Lite+** | Plain-English summary + real-world analogy. |
| **`2`** | **Fix & Bug Detector** | **Lite+** | Identifies syntax/logic flaws and outputs clean code with a "⚡ Patch" button. |
| **`3`** | **Simplify (ELI5)** | **Lite+** | Rewrites dense academic or legal text for an absolute beginner. |
| **`4`** | **Quick Translate** | **Lite+** | Accurately translates foreign language text into clear English. |
| **`5`** | **Regex & Shell** | **Lite+** | Deconstructs regular expressions or CLI commands component-by-component. |
| **`6`** | **Polish Prose** | **Normal+** | Refines tone, corrects grammatical/punctuation errors, and polishes prose. |
| **`7`** | **Docstrings & Types** | **Extreme** | Standardized function docstrings and type annotations. |
| **`8`** | **Security Audit** | **Extreme** | Audits code for OWASP vulnerabilities, leaks, and Big-O complexity. |
| **`9`** | **Unit Test Generator** | **Extreme** | Synthesizes robust, production-grade test suites with mocks. |

---

## 5. Streaming HUD & On-Screen Visual Guide (Annotations)

When your chosen action begins streaming:
- **`📍 Guide` Button (On-Screen Annotations)**:
  - Toggles a hardware-accelerated, transparent, click-through overlay directly on your desktop.
  - Draws a **glowing spotlight bounding box** around the target code or screen area under inspection.
  - Places a numbered **target pin (`❶`, `❷`)** with an anchored **callout guide card** showing where to look and what to do next.
  - 100% click-through: you can click right through the overlay to your editor or browser without the overlay intercepting mouse clicks!
- **Whole-Screen Context Engine**:
  - Automatically captures the active foreground application name (e.g. `Code.exe`, `chrome.exe`), window title, and visible screen text via Windows native OCR.
  - If no text was highlighted, the AI automatically analyzes the visible screen context!
- **`← Options` Button**: Switch to a different action on the same snippet without having to re-highlight or re-copy.
- **⚡ Patch Button** *(Fix Mode)*: Extracts the corrected code block and copies it to your clipboard with one click.
- **Listen (TTS)**: Reads the explanation aloud using native offline Windows voice.
- **Copy**: Copies the generated answer to your clipboard.
- **Inline Follow-Up Chat**: Press **`Tab`** or click the chat bar at the bottom to ask clarifying questions directly within the HUD.

---

## 6. Closing, Hover Persistence & Pinning

- **Smooth Alpha Transitions**: The HUD features 60 FPS hardware-accelerated fade-in (`0.0 -> 0.92`) and graceful fade-out on dismiss, eliminating abrupt pop-in flashes.
- **Hover Persistence**: As long as your mouse cursor is hovered over the HUD (with a generous +12px tolerance margin), it will **NEVER** close randomly. Take all the time you need to read, copy, or interact.
- **Generation Protection**: The HUD will **NEVER** close while the AI is actively thinking or streaming tokens.
- **`📌 Pin` Button**: Click **`📌 Pin`** in the top-right header to lock the HUD indefinitely on your desktop (button turns emerald **`📌 Pinned`**). This is perfect for keeping code explanations or tutorials visible side-by-side while working.
- **Auto-Dismiss Countdown**: Once generation is finished and your mouse leaves the HUD boundaries, the gentle auto-fade timer (default: 14s) starts countdown.
- **Breathing Spotlight Radar**: When **`📍 Guide`** is activated, the spotlight border around your target code pulses with a subtle breathing oscillation to guide your eyes naturally without distracting.
- **Manual Dismissal**:
  - Press **`Escape`** or click **`✕`** in the header for smooth, immediate fade-out of both the HUD and any on-screen visual guide annotations.
