# Setup and Usage Guide: `wat-this`

This guide walks you through setting up, configuring, using, and managing the `wat-this` ambient desktop copilot on Windows 10 & 11.

---

## 1. Prerequisites

1. **Operating System**: Windows 10 or 11 (64-bit). Fully compatible with **Smart App Control (SAC)** and **WDAC** via zero-DLL architecture.
2. **Python**: Python 3.10+ (Python 3.12 recommended).
3. **Ollama**: Download and install from [ollama.com/download](https://ollama.com/download) or install via winget:
   ```powershell
   winget install Ollama.Ollama -e --accept-package-agreements
   ```

---

## 2. One-Click Setup & Launch

To start `wat-this` or configure settings:
- Simply **double-click `SETUP.bat`** in the project root.

`SETUP.bat` automatically verifies your environment, ensures background services are ready, and launches the configuration wizard.

---

## 3. The Setup Wizard Tabs

### Tab 1: Diagnostics
- Probes `http://localhost:11434/api/version` to confirm Ollama is active.
- Reads host physical and available RAM to suggest an optimal model tier profile.
- Offers a one-click button to spawn the Ollama server daemon if offline.

### Tab 2: Models & Install
- **Lite Tier (`< 2 GB RAM`)**: `smollm2:1.7b` (Hugging Face). Ultra-low memory, sub-second responses, offline.
- **Normal Tier (`3 – 5 GB RAM`)**: `llama3.2:3b` (Meta). Balanced intelligence, everyday code analogies, DuckDuckGo search enrichment. *(Recommended)*
- **Extreme Tier (`6 – 10 GB RAM`)**: `mistral:7b` (Mistral AI). Deep technical reasoning, architectural breakdown, and synthesis.
- Click **"Install / Pull Selected Tier Model"** to download with live progress. Once downloaded, click **"Set as Active Tier"**.

### Tab 3: Knowledge Notebook & Exports
- Automatically logs all explained snippets, active model, latency metrics, and responses.
- Real-time search filter by keyword or model name.
- **"Export to Markdown"**: Generates a formatted `wat_this_notebook.md` notebook ready for Obsidian, Notion, or personal notes.
- **"Clear All"**: Wipes history records with confirmation.

### Tab 4: Preferences & Specialized Modes
- **Start with Windows**: One-click toggle to launch `wat-this` silently on Windows startup (uses clean `%APPDATA%\Startup` shortcut).
- **Auto-Speak with Windows TTS**: Automatically reads explanations aloud using native Windows SAPI.
- **Global Hotkey Table**: Review and customize hotkeys.
- **HUD Linger Duration**: Set auto-dismiss timer (4 to 60 seconds).

### Tab 5: Storage & Cleanup
- View exact disk space occupied by downloaded models.
- One-click deletion of models to immediately reclaim gigabytes of disk space.

---

## 4. Multi-Action Workflow & Hotkeys

`wat-this` features dedicated instant actions for engineers, researchers, and students:

| Action Mode | Global Hotkey | Purpose & Behavior |
| :--- | :--- | :--- |
| **Explain & Teach** | `Ctrl + Alt + Space` | Plain-English summary + everyday real-world analogy. |
| **Fix & Bug Detector** | `Ctrl + Alt + F` | Analyzes code for syntax bugs or logic flaws and outputs fixed snippet. |
| **Simplify (ELI5)** | `Ctrl + Alt + T` | Rewrites dense academic or legal text for an absolute beginner. |
| **Generate Docstrings** | `Ctrl + Alt + D` | Generates clean docstrings, JSDoc, and type annotations for selected functions. |
| **Text-to-Speech (Audio)** | `Ctrl + Alt + S` | Reads current card text aloud via offline Windows voice. |

---

## 5. Interactive Conversational Follow-Up

When the explanation card appears:
1. Press **`Tab`** or click the bottom bar: **`💬 Press Tab to ask follow-up...`**
2. An inline input drawer expands without leaving your active window.
3. Type questions like:
   - *"Show me an example in Go"*
   - *"How do I fix this edge case?"*
   - *"What does the second parameter do?"*
4. Press **`Enter`** to stream the answer right into the card.

---

## 6. Closing & Dismissal

- Press **`Escape`** for immediate dismissal.
- Click anywhere on the card.
- Or let the auto-fade timer (default: 14s) close it automatically once you finish reading.
