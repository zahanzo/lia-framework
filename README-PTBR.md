# L.I.A. (Local Intelligent Assistant) / Maya Framework

Um framework de IA modular e multimodal concebido para correr localmente no teu computador. Ouve a tua voz, responde de forma natural, lembra-se das conversas e pode controlar o teu computador através de um sofisticado sistema de plugins baseado no Model Context Protocol (MCP).

Suporta Português (BR/PT) e Inglês de forma nativa.

https://github.com/user-attachments/assets/2fabac71-d281-41f8-9adb-8b413c03a349

Nesta breve demonstração, a LIA executa:
1. **Ferramentas Dinâmicas:** Registo de ferramentas personalizadas (`see_screen`, `abrir_app`, `youtube`) diretamente através do Dashboard, sem necessidade de recompilar o servidor.
2. **Execução Local:** A LIA a abrir o VS Code de forma nativa no ambiente do utilizador.
3. **Automação Web:** A Maya a acionar um script Python em segundo plano para pesquisar e reproduzir música no YouTube.
4. **Memória Contextual:** A IA a manter o contexto ao longo do fluxo contínuo e a aplicar a personalidade "Maya" a todas as respostas.

---

## 🚀 Principais Funcionalidades

* **Interação Multimodal:** Suporta entrada de voz via push-to-talk ou VAD contínuo (Silero). Inclui suporte para vários motores de STT (Whisper, Google) e TTS (Edge-TTS, ElevenLabs, Kokoro, Piper).
* **Loja de Plugins da Comunidade:** Navega, instala e gere ferramentas MCP personalizadas diretamente na interface (UI). Criaste uma ferramenta fixe? Usa o botão integrado **"Generate GitHub Issue"** para empacotar instantaneamente o teu código, schema JSON e dependências, submetendo-a para a loja da comunidade.
* **Memória Semântica (RAG):** Extrai e guarda automaticamente factos das tuas conversas usando embeddings vetoriais locais (`sentence-transformers`) e SQLite para respostas futuras altamente personalizadas.
* **Visão de Ecrã:** Pode analisar o conteúdo do ecrã a pedido ou monitorizar alterações passivamente em segundo plano para manter o contexto visual sem precisares de pedir.
* **Diversos Motores de IA:** Suporte nativo para Groq, OpenRouter, OpenAI e provedores locais como Ollama ou LM Studio.
* **Modo Roleplay:** Cria e ativa cenários e personas personalizadas, substituindo completamente o prompt de sistema padrão.
* **Watchdog Proativo:** Um loop em segundo plano opcional que permite à IA iniciar uma conversa após períodos de inatividade.
* **DND Automático (Não Incomodar):** Deteta reuniões ativas (Zoom, Meet, Teams) e silencia interrupções proativas automaticamente.
* **Sincronização Labial VTube Studio:** Anima a boca de avatares Live2D em sincronia com a fala da IA.

---

## 🖥️ Hardware Recomendado

Para garantir uma experiência fluida com o L.I.A., especialmente ao usar funcionalidades de Visão e RAG (Memória Semântica) em conjunto com modelos de IA locais:

* **GPU:** NVIDIA (Série RTX 30 ou mais recente) ou AMD (Série RX 6000 ou mais recente) é altamente recomendada.
* **VRAM (Mínimo):** **8GB de VRAM** para correr confortavelmente modelos mais pequenos (como Llama 3 8B ou Mistral 7B) com uma janela de contexto estável.
* **VRAM (Ideal):** **12GB ou mais** (ex: uma RTX 3060 12GB) para suportar totalmente as capacidades de Visão e múltiplos plugins MCP em simultâneo sem estrangulamentos de memória.
* **RAM do Sistema:** 16GB ou superior.

---

## ⚙️ Início Rápido

**1. Clonar o repositório**
```bash
git clone https://github.com/your-username/lia-framework
cd lia-framework
```

**2. Criar um ambiente virtual (recomendado)**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**3. Instalar dependências**
```bash
pip install -r requirements.txt
```

**4. Executar a configuração**
```bash
python setup.py
```
*Escolhe o teu idioma (EN ou PT-BR). Isto cria a base de dados e insere uma persona padrão.*

**5. Iniciar o Dashboard Web**
```bash
python webui.py
```
*Abre `http://localhost:8000` → Separador System → API Keys. Adiciona pelo menos uma chave de provedor (ex: Groq).*

**6. Iniciar o assistente**
```bash
python main.py
```

---

## ⌨️ Atalhos de Teclado

| Atalho | Ação |
|---|---|
| Segurar `X` | Falar com o assistente |
| Segurar `X2` (botão lateral do rato) | Pedir à IA para analisar o ecrã |
| `Ctrl+Alt+M` | Abrir o dashboard |
| `Ctrl+Alt+F` | Alternar o Modo Foco |

---

## 🧩 Ferramentas Avançadas e Plugins MCP

O assistente suporta ferramentas personalizadas através do Model Context Protocol (MCP). Podes adicionar ou gerir plugins diretamente através do separador Plugins no dashboard. Cada plugin é um trecho de código Python que é executado quando a IA aciona a ferramenta correspondente.

### Sistema de Ferramentas em Camadas
O L.I.A. implementa uma hierarquia de ferramentas estruturada para otimizar o contexto da IA:
1.  **Ferramentas Globais:** Sempre disponíveis.
2.  **Ferramentas Contextuais:** Ativas apenas quando um "Master" específico (ex: `typing_control`) está ativado.
3.  **Recuperação Semântica:** Usa RAG para encontrar e injetar apenas as ferramentas mais relevantes para a consulta do utilizador, evitando o excesso de contexto.

### Respostas Fast-Track vs. Agênticas
Ao escreveres os teus próprios plugins Python no dashboard, podes otimizar a latência e o uso de tokens utilizando a tag `[DIRECT]`.

* **Fast-Track (tag `[DIRECT]`):** Se a resposta da tua ferramenta começar com `[DIRECT]`, o sistema remove a tag e envia o texto imediatamente para o chat. Isto ignora a segunda chamada ao LLM, garantindo feedback instantâneo para ações simples (ex: abrir ficheiros).
```python
import subprocess
app_name = arguments.get("app_name")
subprocess.Popen(["code"]) 
ai_response = f"[DIRECT] O {app_name} foi aberto com sucesso para ti!"
```

* **Caminho Agêntico (Padrão):** Se a tag for omitida, o framework trata a saída como dados técnicos. Estes dados são enviados de volta ao LLM para uma segunda passagem, permitindo que o assistente interprete os resultados e forneça uma resposta natural e ciente do contexto.

---

## 🔑 Provedores de IA Suportados

| Provedor | Prefixo da Chave | Notas |
|---|---|---|
| **Groq** | `gsk_...` | Escalão gratuito disponível, inferência extremamente rápida. |
| **OpenRouter** | `sk-or-...` | Acesso a mais de 100 modelos de vários provedores. |
| **OpenAI** | `sk-...` | Acesso padrão ao GPT-4o, o1, etc. |
| **Local (Ollama/LM Studio)** | `N/A` | Corre de forma 100% offline para máxima privacidade. |

---

## 📦 Estrutura do Projeto

```text
ai-assistant/
├── main.py              # Loop principal — entrada de voz, chamadas de IA, orquestração MCP
├── config.py            # Estado global, ajudantes de BD (SQLite), gestão de histórico
├── webui.py             # Dashboard FastAPI (http://localhost:8000)
├── server_mcp.py        # Servidor de ferramentas MCP (stdio)
├── mouth.py             # Fila do motor TTS e reprodução
├── ears.py              # STT — Whisper, Google, VAD
├── eyes.py              # Captura de ecrã e análise de visão
├── memory.py            # Memória semântica (RAG) com embeddings
├── skills.py            # Injeções rotativas de habilidades de chat
├── lipsync.py           # Sincronização labial via WebSocket para VTube Studio
├── i18n.py              # Traduções EN / PT-BR
├── web_input_watcher.py # Monitoriza o input_web.json para mensagens do dashboard
├── setup.py             # Assistente de configuração inicial
└── requirements.txt     # Dependências
```

---

## 📜 Licença

Licenciado sob **GNU AGPLv3**.