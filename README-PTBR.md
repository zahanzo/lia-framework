#  L.I.A. (Local Intelligent Assistant) — Um framework de IA modular e multimodal com suporte a plugins MCP.

Um assistente de IA local que roda no seu desktop, ouve sua voz, responde naturalmente, lembra de conversas e pode controlar seu computador através de plugins customizados.

Suporte nativo para Português (BR) e Inglês.

https://github.com/user-attachments/assets/2fabac71-d281-41f8-9adb-8b413c03a349

Nesta demonstração rápida, o LIA executa:
1. **Dynamic Tooling:** Registro de ferramentas customizadas (`see_screen`, `abrir_app`, `youtube`) direto pelo Dashboard, sem recompilar o servidor.
2. **Local Execution:** O LIA abrindo o VS Code nativamente no ambiente do usuário.
3. **Web Automation:** A Maya acionando um script Python em background para buscar e tocar música no YouTube.
4. **Contextual Memory:** A IA entendendo o fluxo contínuo e aplicando a personalidade "Maya" em cada resposta.

---

## Recursos

- **Entrada de voz** — push-to-talk (botão do mouse) ou contínuo (VAD com Silero)
- **Múltiplos motores TTS** — Edge-TTS (padrão), ElevenLabs, Kokoro, Piper
- **Múltiplos motores STT** — Whisper (local), Google STT
- **Memória Semântica (RAG)** — lembra de fatos entre diferentes conversas
- **Sistema de plugins MCP** — adicione ferramentas pelo painel (abrir apps, pesquisar na web, etc.)
- **Visão de tela** — a IA pode analisar sua tela sob demanda
- **Modo Roleplay** — mude para uma persona customizada através do painel
- **Dashboard Web** — configure tudo diretamente no navegador (http://localhost:8000)
- **Lip sync com VTube Studio** — anima a boca do seu avatar Live2D quando a IA fala
- **Múltiplos provedores de IA** — Groq, OpenRouter, OpenAI, local (Ollama)
- **Interface Bilíngue** — Português (BR) e Inglês

### 🔍 Detalhamento das Funcionalidades

* **Modo Foco (Focus Mode):** Quando você precisa se concentrar, este modo torna a IA extremamente concisa. Ele suprime comportamentos proativos e garante que a assistente só fale quando chamada diretamente, agindo como uma ajudante silenciosa e eficiente.
* **Watchdog Proativo:** Se ativado, a IA roda um loop em segundo plano verificando o tempo de inatividade. Se você não interagir por um tempo, a assistente pode puxar assunto proativamente, tornando a IA muito mais "viva" e engajada.
* **Não Perturbe (DND) Automático:** O assistente detecta automaticamente se você está em reuniões ativas (Zoom, Google Meet, Teams). Quando uma reunião é detectada, o DND é ativado, silenciando qualquer interrupção proativa.
* **Roleplay & Gestão de Persona:** Vá além de um assistente padrão. Você pode criar cenários customizados, definir quem a IA é e quem *você* é na história. Isso substitui o prompt de sistema padrão para interações imersivas e criativas (com uma chave NSFW opcional para liberdade total).
* **Modo Bate-papo (Skills Rotativas):** Para evitar que conversas casuais pareçam robóticas, este modo aplica "skills" ocultas ao prompt da IA a cada turno (ex: "seja irônica", "faça uma pergunta curiosa"). Elas rotacionam dinamicamente com tempos de recarga, garantindo um diálogo variado e natural.
* **Memória Semântica (RAG):** O assistente extrai automaticamente fatos concretos das suas conversas (preferências, projetos, hardware) e os salva usando embeddings vetoriais locais (`sentence-transformers`). Ao fazer uma pergunta relacionada no futuro, ele busca esses fatos para dar respostas altamente personalizadas sem que você precise se repetir.
* **Visão em Segundo Plano:** Além da captura manual, o assistente pode ser configurado para monitorar mudanças na tela passivamente. Se houver uma alteração visual significativa, ele atualiza seu contexto interno, permitindo que "veja" o que você está fazendo antes mesmo de você perguntar.

---

## Requisitos

- Windows 10/11
- Python 3.10.11 (recomendado — [download](https://www.python.org/downloads/release/python-31011/))
- Um microfone (opcional, mas recomendado)
- Chave de API de pelo menos um provedor de IA (Groq é gratuito)

---

## Início Rápido

**1. Clone o repositório**
```bash
git clone https://github.com/zahanzo/lia-framework
cd lia-framework
```

**2. Crie um ambiente virtual (recomendado)**
```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
```

**3. Instale as dependências principais**
```bash
pip install -r requirements.txt
```

**4. Instale os recursos opcionais que desejar**
```bash
pip install pyaudio                          # entrada de microfone
pip install faster-whisper torch torchaudio  # reconhecimento de voz local
pip install sentence-transformers numpy      # memória semântica
pip install mss                              # visão de tela
```

**5. Rode o setup**
```bash
python setup.py
```
Escolha seu idioma (EN ou PT-BR). Isso cria o banco de dados e insere a persona padrão.

**6. Adicione suas chaves de API**
```bash
python webui.py
```
Abra http://localhost:8000 → Aba Sistema → Chaves de API.
No mínimo, adicione uma chave do **Groq** (grátis em [console.groq.com](https://console.groq.com)).

**7. Inicie o assistente**
```bash
python main.py
```

---

## Atalhos de Teclado

| Atalho | Ação |
|---|---|
| Segurar `X` | Falar com a assistente |
| Segurar `X2` (botão lateral do mouse) | Pedir para a IA analisar sua tela |
| `Ctrl+Alt+M` | Abrir o dashboard |
| `Ctrl+Alt+F` | Alternar Modo Foco |

---

## Dashboard

Inicie o dashboard com `python webui.py` e abra http://localhost:8000.

Pelo dashboard você pode:
- Configurar provedor e modelos de IA (Geral, Visão, Código, Roleplay)
- Inserir chaves de API
- Configurar motor de voz e transcrição (STT)
- Gerenciar a persona da IA e o prompt
- Visualizar e apagar memórias
- Criar e editar plugins MCP
- Alternar Modo Foco, Watchdog, visão em segundo plano e lip sync

---

## Plugins MCP
O assistente suporta ferramentas personalizadas através do Model Context Protocol. Você pode adicionar ou gerenciar plugins diretamente através da aba Plugins no dashboard. Cada plugin é um snippet de Python que executa quando a IA aciona a ferramenta correspondente.

Exemplo de Uso
Ao criar uma ferramenta para abrir um aplicativo, você pode utilizar a seguinte lógica:

```python
import subprocess
```

# A variável 'arguments' contém os parâmetros da ferramenta
```python
app_name = arguments.get("app_name")
```
# Execução de fluxo rápido usando a tag [DIRECT]
```python
subprocess.Popen(["code"]) 
ai_response = f"[DIRECT] Abri o {app_name} para você agora mesmo!"
```

Lógica de Resposta: Fluxo Rápido vs. Agêntico
Para otimizar a latência e o consumo de tokens, o framework manipula a variável ai_response baseando-se na presença de uma tag específica:

- Fluxo Rápido (Tag `[DIRECT]`): Se a resposta começar com `[DIRECT]`, o sistema remove a tag e envia o texto imediatamente para o chat. Isso pula a segunda chamada à LLM, garantindo feedback instantâneo para ações simples (ex: abrir arquivos, alterar configurações de hardware).

- Fluxo Agêntico (Padrão): Se a tag for omitida, o framework trata a saída como dados técnicos. Esses dados são enviados de volta para a LLM para uma segunda passagem, permitindo que o assistente interprete os resultados e forneça uma resposta natural e contextualizada.

Ambiente de Plugins
Os seguintes recursos estão disponíveis dentro do sandbox de plugins:

Bibliotecas: `os`, `sys`, `subprocess`, `requests`, `time`, `pyautogui`, `webbrowser`, `json`.

Contexto: arguments (dicionário contendo os parâmetros da ferramenta).

Banco de Dados: `run_db` (função para interagir com o banco de dados interno do sistema).

---

## Estrutura do Projeto

```text
ai-assistant/
├── main.py              # loop principal — áudio, chamadas de IA, orquestração MCP
├── config.py            # estado global, banco de dados, histórico
├── webui.py             # dashboard FastAPI (http://localhost:8000)
├── server_mcp.py        # servidor de ferramentas MCP (stdio)
├── mouth.py             # fila e reprodução do motor TTS
├── ears.py              # STT — Whisper, Google, VAD
├── eyes.py              # captura e análise de tela
├── memory.py            # memória semântica (RAG) com embeddings
├── skills.py            # injeções rotativas de skills de bate-papo
├── lipsync.py           # lip sync via WebSocket para VTube Studio
├── i18n.py              # traduções EN / PT-BR
├── web_input_watcher.py # monitora input_web.json para comandos do dashboard
├── setup.py             # assistente de configuração inicial
└── requirements.txt     # dependências
```

---

## Provedores de IA

| Provedor | Prefixo da chave | Notas |
|---|---|---|
| **Groq** | `gsk_...` | Plano gratuito, muito rápido, recomendado |
| **OpenRouter** | `sk-or-...` | Acesso a mais de 100 modelos |
| **OpenAI** | `sk-...` | GPT-4o, o1, etc. |

---

## Licença

GNU AGPLv3
