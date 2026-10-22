# Assistente Pessoal H.E.R.O. 🦾 (J.A.R.V.I.S. Core)

> **Ecossistema Multi-Agente Stark (J.A.R.V.I.S., F.R.I.D.A.Y., E.D.I.T.H., D.U.M.-E & U)**  
> 100% Local, Privado, Roteamento Contextual Automático, Memória Semântica Vetorial e Interface HUD Reator Arc com Áudio em Tempo Real.

---

## 📑 Documentação e Manuais

- 📄 **[Documentação Técnica e Arquitetural (PDF)](docs/DOCUMENTACAO_E_PLANO_HERO.pdf)** — Arquivo consolidado pronto para leitura e impressão.
- 📖 **[Documentação Técnica Detalhada (Markdown)](docs/DOCUMENTACAO_TECNICA.md)**
- 🚀 **[Plano de Implementação Passo a Passo (Markdown)](docs/PLANO_DE_IMPLEMENTACAO.md)**

---

## 🌟 Destaques do Projeto

1. **Protocolos de IA Especializados (VisionQuest):**
   - 🛡️ **J.A.R.V.I.S.:** Núcleo central, integridade do sistema, RAG e segurança geral.
   - 💻 **E.D.I.T.H.:** Cibersegurança e operações virtuais (Blue Team / Red Team, pentests éticos, blindagem de sites, APIs e apps).
   - 🤝 **F.R.I.D.A.Y.:** Socialização, inteligência emocional, psicologia, mediação de conversas e humor.
   - 🔧 **D.U.M.-E & U:** Manutenção mecânica, análise de vídeo/mídia (U) e faxina de cache/logs (D.U.M.-E).
2. **Roteamento Contextual Inteligente:** O usuário não precisa chamar os agentes pelo nome. Perguntas sobre invasão/falhas ativam a **E.D.I.T.H.**, conselhos ativam a **F.R.I.D.A.Y.** e limpeza de disco ativa o **D.U.M.-E**.
3. **Memória de Longo Prazo (Hipocampo):** Banco vetorial PostgreSQL 16 + `pgvector` usando embeddings locais (`nomic-embed-text`) com aprendizado contínuo.
4. **Pipeline de Áudio em Tempo Real:**
   - **Ouvido (STT):** `faster-whisper` com VAD e pré-aquecimento local.
   - **Boca (TTS):** Síntese neural ultra-natural via `edge-tts` com voz própria para cada agente.
   - **Barge-in (Interrupção):** Interrompa o assistente instantaneamente falando por cima ou teclando `Esc`.
5. **HUD Futurista com Reator Arc:** Canvas animado com Web Audio API reagindo à frequência da voz.

---

## 🏗️ Arquitetura do Repositório

```text
assistente-pessoal-hero/
├── docker-compose.yml              # Orquestração do PostgreSQL (pgvector) e Jarvis Core
├── .env.example                    # Modelo de configuração de variáveis
├── docs/
│   ├── DOCUMENTACAO_E_PLANO_HERO.pdf  # Manual consolidado em PDF
│   ├── DOCUMENTACAO_TECNICA.md        # Especificação da arquitetura
│   └── PLANO_DE_IMPLEMENTACAO.md      # Guia de deploy do zero
├── scripts/
│   └── generate_docs_pdf.py        # Compilador ReportLab para o PDF
├── backend/
│   ├── Dockerfile                  # Container com Python 3.11, Whisper, ffmpeg
│   ├── requirements.txt            # Dependências otimizadas (sem conflitos)
│   └── app/
│       ├── main.py                 # FastAPI, WebSockets e API REST
│       ├── brain.py                # Raciocínio, RAG e extração de fatos
│       ├── agents.py               # Definição e roteador de protocolos
│       ├── memory.py               # Conexão direta pgvector (psycopg3)
│       ├── ollama_client.py        # Cliente assíncrono para Ollama local
│       ├── stt.py                  # faster-whisper local
│       ├── tts.py                  # edge-tts com vozes neurais brasileiras
│       └── config.py               # Pydantic Settings
└── frontend/
    ├── index.html                  # HUD Stark Glassmorphism
    ├── styles.css                  # Efeitos neon, temas por agente e responsividade
    └── app.js                      # WebSockets, AudioContext e animação do Reator Arc
```

---

## 🚀 Como Executar em 3 Passos

### 1. Pré-requisitos
- Instale o **[Docker Desktop](https://www.docker.com/)** (com suporte a WSL2 no Windows).
- Instale o **[Ollama](https://ollama.com/)** e baixe os modelos:
  ```bash
  ollama pull qwen2.5:7b
  ollama pull nomic-embed-text
  ```
- No Windows, defina a variável de ambiente `OLLAMA_HOST=0.0.0.0` para permitir a conexão dos containers.

### 2. Configurar o Ambiente
Copie o arquivo de exemplo:
```bash
cp .env.example .env
```
Edite o `.env` e configure seu nome em `JARVIS_USER_NAME=SeuNome`.

### 3. Subir com Docker Compose
```bash
docker compose up --build -d
```
Acesse no navegador:
👉 **`http://localhost:8000`**

---

## ⌨️ Atalhos do HUD

- **Espaço:** Segure para falar (Push-to-Talk).
- **Esc:** Interrompe a resposta imediatamente.
- **Mãos-Livres:** Ative no rodapé para detecção automática de voz contínua.
- **Hipocampo:** Visualize e edite fatos que o assistente aprendeu sobre você.

---

## 📄 Licença
Distribuído sob a licença MIT. Criado por Douglas.
