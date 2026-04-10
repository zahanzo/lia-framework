# L.I.A. (Local Intelligent Assistant) — A modular, multimodal AI framework with MCP plugin support.

A AI assistant that runs on your desktop, listens to your voice, responds naturally, remembers conversations, and can control your computer through custom plugins.

Supports Portuguese (BR) and English out of the box.


<video src="demo/lia-demo.mp4" autoplay loop muted style="max-width: 100%;"></video>

In this brief demonstration, LIA performs:
1. **Dynamic Tooling:** Custom tool registration (`see_screen`, `abrir_app`, `youtube`) directly through the Dashboard, with no server recompilation required.
2. **Local Execution:** LIA opening VS Code natively within the user's environment.
3. **Web Automation:** Maya triggering a background Python script to search for and play music on YouTube.
4. **Contextual Memory:** The AI maintaining context throughout the continuous flow and applying the "Maya" personality to every response.

---

## Features

- **Voice input** — push-to-talk (mouse button) or continuous VAD (Silero)
- **Multiple TTS engines** — Edge-TTS (default), ElevenLabs, Kokoro, Piper
- **Multiple STT engines** — Whisper (local), Google STT
- **Semantic memory (RAG)** — remembers facts across conversations
- **MCP plugin system** — add custom tools via the dashboard (open apps, search web, etc.)
- **Screen vision** — AI can analyze your screen on demand
- **Roleplay mode** — switch to a custom persona via the dashboard
- **Web dashboard** — configure everything in the browser (http://localhost:8000)
- **VTube Studio lip sync** — animate your Live2D avatar mouth when the AI speaks
- **Multi-provider AI** — Groq, OpenRouter, OpenAI, local (Ollama)
- **Bilingual UI** — Portuguese (BR) and English

### 🔍 Feature Deep Dive

* **Focus Mode:** When you need to concentrate, Focus Mode makes the AI extremely brief. It suppresses proactive behaviors and ensures the assistant only speaks when directly spoken to, acting as a silent, efficient helper.
* **Proactive Watchdog:** If enabled, the AI runs a background loop to check system idle time. If you haven't interacted for a while, the assistant can proactively check in on you, making the AI feel much more alive and engaged.
* **Do Not Disturb (DND) Auto-Detection:** The assistant automatically detects if you are in active meetings on platforms like Zoom, Google Meet, or Microsoft Teams. When a meeting is detected, DND is triggered, silencing any proactive interruptions.
* **Roleplay & Persona Management:** Go beyond a standard assistant. You can create custom scenarios, define who the AI is, and who *you* are in the context. This completely overrides the standard system prompt for immersive, creative interactions (with an optional NSFW toggle for unrestricted creative freedom).
* **Chat Mode (Rotating Skills):** To make casual conversations feel less robotic, Chat Mode applies hidden "skills" to the AI's prompt each turn (e.g., "be playful," "ask a curious question"). These rotate dynamically with cooldowns, ensuring varied and natural dialogue.
* **Semantic Memory (RAG):** The assistant automatically extracts concrete facts from your conversations (preferences, projects, hardware specs) and saves them using local vector embeddings (`sentence-transformers`). When you ask a related question later, it fetches these facts to provide highly personalized answers without you needing to repeat yourself.
* **Background Vision:** Beyond manual screen capture, the assistant can be configured to passively monitor screen changes. If a significant visual change occurs, it updates its internal context, allowing it to "see" what you are working on before you even ask.

---

## Requirements

- Windows 10/11
- Python 3.10.11 (recommended — [download](https://www.python.org/downloads/release/python-31011/))
- A microphone (optional but recommended)
- API key for at least one AI provider (Groq is free)

---

## Quick Start

**1. Clone the repository**
```bash
git clone https://github.com/zahanzo/lia-framework
cd lia-framework
```

**2. Create a virtual environment (recommended)**
```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
```

**3. Install core dependencies**
```bash
pip install -r requirements.txt
```

**4. Install optional features you want**
```bash
pip install pyaudio                          # microphone input
pip install faster-whisper torch torchaudio  # local speech recognition
pip install sentence-transformers numpy      # semantic memory
pip install mss                              # screen vision
```

**5. Run setup**
```bash
python setup.py
```
Choose your language (EN or PT-BR). This creates the database and inserts a default persona.

**6. Add your API keys**
```bash
python webui.py
```
Open http://localhost:8000 → System tab → API Keys.
At minimum, add a **Groq** key (free at [console.groq.com](https://console.groq.com)).

**7. Start the assistant**
```bash
python main.py
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| Hold `X` | Talk to the assistant |
| Hold `X2` (mouse side button) | Ask the AI to analyze your screen |
| `Ctrl+Alt+M` | Open the dashboard |
| `Ctrl+Alt+F` | Toggle Focus Mode |

---

## Dashboard

Start the dashboard with `python webui.py` and open http://localhost:8000.

From the dashboard you can:
- Configure AI provider and models (General, Vision, Code, Roleplay)
- Set API keys
- Configure voice engine and STT engine
- Manage the AI persona and prompt
- View and delete memories
- Create and edit MCP plugins
- Toggle Focus Mode, Watchdog, background vision, and lip sync

---

## MCP Plugins
The assistant supports custom tools via the Model Context Protocol. You can add or manage plugins directly through the Plugins tab in the dashboard. Each plugin is a Python snippet that executes when the AI triggers the corresponding tool.

Usage Example
When creating a tool to open an application, you can use the following logic:

```python
import subprocess
```
# The 'arguments' variable contains the tool parameters
```python
app_name = arguments.get("app_name")
```

# Fast-track execution using the [DIRECT] tag
```python
subprocess.Popen(["code"]) 
ai_response = f"[DIRECT] Successfully opened {app_name} for you!"
```

Response Logic: Fast-Track vs. Agentic
To optimize latency and token usage, the framework handles the ai_response variable based on the presence of a specific tag:

- Fast-Track (`[DIRECT]` tag): If the response starts with `[DIRECT]`, the system strips the tag and pushes the text immediately to the chat. This bypasses the second LLM call, ensuring instant feedback for simple actions (e.g., opening files, toggling settings).

- Agentic Track (Default): If the tag is omitted, the framework treats the output as technical data. This data is sent back to the LLM for a second pass, allowing the assistant to interpret the results and provide a natural, context-aware response.

Plugin Environment
The following resources are available within the plugin sandbox:

Libraries: `os`, `sys`, `subprocess`, `requests`, `time`, `pyautogui`, `webbrowser`, `json`.

Context: arguments (dictionary containing the tool parameters).

Database: `run_db` (function to interact with the internal system database).

## Project Structure

```text
ai-assistant/
├── main.py              # main loop — voice input, AI calls, MCP orchestration
├── config.py            # global state, DB helpers, history management
├── webui.py             # FastAPI dashboard (http://localhost:8000)
├── server_mcp.py        # MCP tool server (stdio)
├── mouth.py             # TTS engine queue and playback
├── ears.py              # STT — Whisper, Google, VAD
├── eyes.py              # screen capture and vision analysis
├── memory.py            # semantic memory (RAG) with embeddings
├── skills.py            # rotating chat skill injections
├── lipsync.py           # VTube Studio WebSocket lip sync
├── i18n.py              # EN / PT-BR translations
├── web_input_watcher.py # watches input_web.json for dashboard messages
├── setup.py             # first-time setup wizard
└── requirements.txt     # dependencies
```

---

## AI Providers

| Provider | Key prefix | Notes |
|---|---|---|
| **Groq** | `gsk_...` | Free tier, very fast, recommended |
| **OpenRouter** | `sk-or-...` | Access to 100+ models |
| **OpenAI** | `sk-...` | GPT-4o, o1, etc. |

---

## License

GNU AGPLv3