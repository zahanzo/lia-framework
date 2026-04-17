# L.I.A. (Local Intelligent Assistant) / Maya Framework

A modular, multimodal AI framework designed to run locally on your desktop. It listens to your voice, responds naturally, remembers conversations, and can control your computer through a sophisticated plugin system based on the Model Context Protocol (MCP).

Supports Portuguese (BR) and English out of the box.

https://github.com/user-attachments/assets/2fabac71-d281-41f8-9adb-8b413c03a349

In this brief demonstration, LIA performs:
1. **Dynamic Tooling:** Custom tool registration (`see_screen`, `abrir_app`, `youtube`) directly through the Dashboard, with no server recompilation required.
2. **Local Execution:** LIA opening VS Code natively within the user's environment.
3. **Web Automation:** Maya triggering a background Python script to search for and play music on YouTube.
4. **Contextual Memory:** The AI maintaining context throughout the continuous flow and applying the "Maya" personality to every response.

---

## 🚀 Main Features

* **Multimodal Interaction:** Supports voice input via push-to-talk or continuous VAD (Silero). Includes support for multiple STT (Whisper, Google) and TTS engines (Edge-TTS, ElevenLabs, Kokoro, Piper).
* **Community Plugin Store:** Browse, install, and manage custom MCP tools directly from the UI. Created a cool tool? Use the built-in **"Generate GitHub Issue"** button to instantly package your code, JSON schema, and dependencies, submitting it to the community store.
* **Semantic Memory (RAG):** Automatically extracts and stores facts from your conversations using local vector embeddings (`sentence-transformers`) and SQLite for highly personalized future responses.
* **Screen Vision:** Can analyze screen content on demand or monitor changes passively in the background to maintain visual context without you needing to ask.
* **Diverse AI Engines:** Native support for Groq, OpenRouter, OpenAI, and local providers like Ollama or LM Studio.
* **Roleplay Mode:** Create and activate custom scenarios and personas, completely overriding the standard system prompt.
* **Proactive Watchdog:** An optional background loop that allows the AI to initiate conversation after periods of inactivity.
* **Automatic DND:** Detects active meetings (Zoom, Meet, Teams) and silences proactive interruptions automatically.
* **VTube Studio Lip Sync:** Animates Live2D avatar mouths in sync with AI speech output.

---

## 🖥️ Recommended Hardware

To ensure a smooth experience with L.I.A., especially when using Vision features and RAG (Semantic Memory) alongside local AI models:

* **GPU:** NVIDIA (RTX 30 series or newer) or AMD (RX 6000 series or newer) is highly recommended.
* **VRAM (Minimum):** **8GB of VRAM** to comfortably run smaller models (like Llama 3 8B or Mistral 7B) with a stable context window.
* **VRAM (Ideal):** **12GB or more** (e.g., an RTX 3060 12GB) to fully support Vision capabilities and multiple MCP plugins simultaneously without memory bottlenecks.
* **System RAM:** 16GB or higher.

---

## ⚙️ Quick Start

**1. Clone the repository**
```bash
git clone https://github.com/your-username/lia-framework
cd lia-framework
```

**2. Create a virtual environment (recommended)**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Run setup**
```bash
python setup.py
```
*Choose your language (EN or PT-BR). This creates the database and inserts a default persona.*

**5. Start the Web Dashboard**
```bash
python webui.py
```
*Open `http://localhost:8000` → System tab → API Keys. Add at least one provider key (e.g., Groq).*

**6. Start the assistant**
```bash
python main.py
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| Hold `X` | Talk to the assistant |
| Hold `X2` (mouse side button) | Ask the AI to analyze your screen |
| `Ctrl+Alt+M` | Open the dashboard |
| `Ctrl+Alt+F` | Toggle Focus Mode |

---

## 🧩 Advanced Tooling & MCP Plugins

The assistant supports custom tools via the Model Context Protocol. You can add or manage plugins directly through the Plugins tab in the dashboard. Each plugin is a Python snippet that executes when the AI triggers the corresponding tool.

### Layered Tool System
L.I.A. implements a structured tool hierarchy to optimize AI context:
1.  **Global Tools:** Always available.
2.  **Contextual Tools:** Only active when a specific "Master" (e.g., `typing_control`) is enabled.
3.  **Semantic Retrieval:** Uses RAG to find and inject only the most relevant tools for a user query, preventing context overflow.

### Fast-Track vs. Agentic Responses
When writing your own Python plugins in the dashboard, you can optimize latency and token usage using the `[DIRECT]` tag.

* **Fast-Track (`[DIRECT]` tag):** If your tool's response starts with `[DIRECT]`, the system strips the tag and pushes the text immediately to the chat. This bypasses the second LLM call, ensuring instant feedback for simple actions.
```python
import subprocess
app_name = arguments.get("app_name")
subprocess.Popen(["code"]) 
ai_response = f"[DIRECT] Successfully opened {app_name} for you!"
```

* **Agentic Track (Default):** If the tag is omitted, the framework treats the output as technical data. This data is sent back to the LLM for a second pass, allowing the assistant to interpret the results and provide a natural, context-aware response.

---

## 🔑 Supported AI Providers

| Provider | Key prefix | Notes |
|---|---|---|
| **Groq** | `gsk_...` | Free tier available, extremely fast inference. |
| **OpenRouter** | `sk-or-...` | Access to 100+ models from various providers. |
| **OpenAI** | `sk-...` | Standard access to GPT-4o, o1, etc. |
| **Local (Ollama/LM Studio)** | `N/A` | Runs completely offline for maximum privacy. |

---

## 📦 Project Structure

```text
ai-assistant/
├── main.py              # Main loop — voice input, AI calls, MCP orchestration
├── config.py            # Global state, DB helpers (SQLite), history management
├── webui.py             # FastAPI dashboard (http://localhost:8000)
├── server_mcp.py        # MCP tool server (stdio)
├── mouth.py             # TTS engine queue and playback
├── ears.py              # STT — Whisper, Google, VAD
├── eyes.py              # Screen capture and vision analysis
├── memory.py            # Semantic memory (RAG) with embeddings
├── skills.py            # Rotating chat skill injections
├── lipsync.py           # VTube Studio WebSocket lip sync
├── i18n.py              # EN / PT-BR translations
├── web_input_watcher.py # Watches input_web.json for dashboard messages
├── setup.py             # First-time setup wizard
└── requirements.txt     # Dependencies
```

---

## 📜 License

Licensed under **GNU AGPLv3**.