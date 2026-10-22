# Documentação Técnica e Arquitetural — Assistente Pessoal H.E.R.O. (J.A.R.V.I.S. Core)

> **Projeto:** Assistente Pessoal Stark Multi-Agente (J.A.R.V.I.S., F.R.I.D.A.Y., E.D.I.T.H., D.U.M.-E & U)  
> **Versão:** 3.5  
> **Autor / Proprietário:** Douglas  
> **Repositório GitHub:** `assistente-pessoal-hero`  
> **Licença:** MIT  

---

## 1. Visão Geral do Sistema

O **Assistente Pessoal H.E.R.O.** é um ecossistema de inteligência artificial pessoal projetado para operar com **privacidade total (100% local)**, baixa latência e alta fidelidade em voz, memória de longo prazo e roteamento contextual multi-agente.

Inspirado no universo tecnológico de Tony Stark e nos protocolos de IA apresentados em *VisionQuest*, o sistema divide responsabilidades especializadas entre 4 protocolos inteligentes com personalidades, vozes neurais e paletas visuais próprias, integrados a um **Reator Arc HUD** interativo.

```
       ┌────────────────────────────────────────────────────────┐
       │             Interface Web HUD (Reator Arc)             │
       │       Áudio Bidirecional / WebSocket / Canvas Audio     │
       └───────────────────────────┬────────────────────────────┘
                                   │
                           WebSocket /ws
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │                   FastAPI Core Service                 │
       │  ┌───────────────────────┬───────────────────────────┐ │
       │  │ Ouvido (STT): Whisper │ Boca (TTS): Edge-TTS      │ │
       │  └───────────────────────┴───────────────────────────┘ │
       │  ┌───────────────────────────────────────────────────┐ │
       │  │     Roteador Semântico / Contextual de Agentes    │ │
       │  └───────────────────────┬───────────────────────────┘ │
       └──────────────────────────┼─────────────────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌──────────────────┐                             ┌──────────────────┐
│  Ollama Engine   │                             │  PostgreSQL 16   │
│  - Qwen 2.5 7B   │                             │  - pgvector      │
│  - Nomic Embed   │                             │  - Memória RAG   │
└──────────────────┘                             └──────────────────┘
```

---

## 2. Protocolos de IA (Multi-Agentes)

O sistema possui inteligência para alternar dinamicamente entre os agentes **por menção direta** ou **por detecção semântica contextual** (o usuário faz uma pergunta sobre o tema e o agente especialista assume a resposta automaticamente):

| Protocolo | Função Principal | Especialidades Técnicas | Voz Neural (PT-BR) | Tema Visual |
| :--- | :--- | :--- | :--- | :--- |
| **J.A.R.V.I.S.** | Núcleo Central & Segurança | Coordenação geral, proteção do usuário, integridade do sistema e consultas amplas. | `pt-BR-AntonioNeural` | Ciano Stark (`#1edcff`) |
| **E.D.I.T.H.** | Cibersegurança & Operações Virtuais | Defesa virtual (Blue Team), auditoria de código, proteção contra SQLi/XSS/DDoS, pentest ético (Red Team) em sites, apps e APIs. | `pt-BR-ThalitaMultilingual` | Violeta Tático (`#b46eff`) |
| **F.R.I.D.A.Y.** | Socialização & Inteligência Emocional | Mediação interpessoal, conversas difíceis, psicologia, aconselhamento, empatia e humor. | `pt-BR-FranciscaNeural` | Dourado / Âmbar (`#ffaa2d`) |
| **D.U.M.-E & U** | Manutenção Mecânica & Mídia | `U` analisa mídia, arquivos e logs. `D.U.M.-E` atua como supressor de falhas, limpeza de cache e faxina de disco. | `pt-BR-AntonioNeural` | Verde Oficina (`#32e68c`) |

---

## 3. Pilares Arquiteturais

### 3.1 Memória Semântica de Longo Prazo (Hipocampo)
- **Engine:** PostgreSQL 16 com extensão `pgvector`.
- **Embeddings:** `nomic-embed-text` (vetores de 768 dimensões) gerados localmente via Ollama.
- **Aprendizado Ativo:** Após cada fala do usuário, o sistema extrai automaticamente fatos relevantes e armazena na categoria `aprendido` ou `perfil`, evitando duplicatas semânticas através de distância de cosseno.

### 3.2 Pipeline de Áudio em Tempo Real
- **STT (Speech-to-Text):** `faster-whisper` executado localmente no container com Voice Activity Detection (VAD) e pré-aquecimento assíncrono.
- **TTS (Text-to-Speech):** Síntese neural ultra-natural via `edge-tts` com streaming fragmentado por sentença (o áudio começa a tocar enquanto o modelo ainda está completando a resposta).
- **Barge-In (Interrupção Instantânea):** Se o usuário falar ou pressionar `Esc`, a reprodução em andamento é cancelada imediatamente sem perda de turnos no WebSocket.

### 3.3 Interface Web HUD Futurista
- **Canvas Reator Arc:** Visualizador em tempo real alimentado pela Web Audio API (`AudioContext` + `AnalyserNode`) reagindo à frequência da voz.
- **Gaveta Hipocampo:** Visualização, busca e exclusão de memórias armazenadas no banco vetorial.
- **Troca de Protocolo:** Seletores rápidos no topo e feedback sonoro e visual instantâneo.

---

## 4. Requisitos de Hardware e Software

- **Sistema Operacional:** Windows 10/11 (com WSL2 ativado), Linux Ubuntu 22.04+ ou macOS (Apple Silicon).
- **Docker & Docker Compose:** Versão 24+.
- **Ollama:** Versão 0.3+ instalada no host.
- **Hardware Recomendado:**
  - CPU: 4 núcleos ou superior.
  - RAM: Mínimo 8 GB (16 GB recomendado para modelos de 7B).
  - GPU: Opcional (NVIDIA com CUDA acelera a inferência do Ollama e Whisper, mas CPU é 100% suportada).
