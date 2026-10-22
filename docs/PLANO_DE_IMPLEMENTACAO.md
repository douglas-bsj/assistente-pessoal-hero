# Plano de Implementação Passo a Passo — Assistente Pessoal H.E.R.O.

Guia completo para qualquer desenvolvedor ou usuário que deseje implantar o **Assistente Pessoal H.E.R.O.** do zero em sua própria máquina ou servidor local.

---

## Fase 1: Preparação do Ambiente Host

### 1.1 Instalação do Docker
1. Instale o **Docker Desktop** (no Windows, certifique-se de habilitar o backend WSL2 nas configurações).
2. Verifique a instalação no terminal:
   ```bash
   docker --version
   docker compose version
   ```

### 1.2 Instalação e Configuração do Ollama
1. Baixe e instale o Ollama em [ollama.com](https://ollama.com).
2. Configure o Ollama para aceitar conexões locais vindas dos containers Docker:
   - **No Windows:**
     - Abra as Variáveis de Ambiente do Sistema.
     - Adicione a variável de ambiente: `OLLAMA_HOST=0.0.0.0`
     - Reinicie o aplicativo do Ollama (pela bandeja do sistema).
   - **No Linux:**
     - Edite o serviço do systemd: `systemctl edit ollama.service`
     - Adicione:
       ```ini
       [Service]
       Environment="OLLAMA_HOST=0.0.0.0"
       ```
     - Reinicie: `sudo systemctl restart ollama`
3. Baixe os modelos necessários no terminal:
   ```bash
   # Modelo de Raciocínio e Chat em Português (ou qwen2.5:3b para máquinas mais leves)
   ollama pull qwen2.5:7b

   # Modelo de Embeddings Vetoriais (768 dimensões)
   ollama pull nomic-embed-text
   ```

---

## Fase 2: Configuração do Projeto

### 2.1 Clonar o Repositório
```bash
git clone https://github.com/douglas-bsj/assistente-pessoal-hero.git
cd assistente-pessoal-hero
```

### 2.2 Configurar o Arquivo de Ambiente (.env)
Copie o modelo de exemplo para criar seu `.env`:
```bash
cp .env.example .env
```

Edite o arquivo `.env` para personalizar seus parâmetros:
```env
# Nome do Usuário
JARVIS_USER_NAME=SeuNome

# Configurações do Ollama
# No Docker para Windows/Mac utilize host.docker.internal:11434
# No Linux utilize o IP da máquina ou 172.17.0.1:11434
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_CHAT_MODEL=qwen2.5:7b
OLLAMA_EMBED_MODEL=nomic-embed-text

# Whisper (STT) - Opções: tiny, base, small, medium
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8

# Voz Neural Padrão (TTS)
TTS_VOICE=pt-BR-AntonioNeural
```

---

## Fase 3: Build e Inicialização dos Containers

### 3.1 Subir os Serviços via Docker Compose
Execute no diretório raiz:
```bash
docker compose up --build -d
```

Este comando irá orquestrar:
1. `jarvis-db`: Banco de dados relacional e vetorial PostgreSQL 16 com `pgvector`.
2. `jarvis-core`: API FastAPI, modelo Whisper local, síntese neural Edge-TTS e servidor de arquivos estáticos do HUD.

### 3.2 Verificar o Status e Saúde dos Serviços
```bash
# Ver status dos containers
docker compose ps

# Acompanhar logs em tempo real
docker compose logs -f jarvis-core
```
Aguarde a mensagem: `J.A.R.V.I.S. online em http://localhost:8000`.

---

## Fase 4: Operação e Testes

### 4.1 Acessar a Interface HUD
Abra seu navegador em:
👉 **`http://localhost:8000`**

### 4.2 Configurar Microfone
- Permita a permissão de microfone solicitada pelo navegador.
- Utilize fone com microfone (headset) para evitar que o áudio das caixas de som seja captado pelo microfone (eco acústico).
- **Atalhos:**
  - Pressione e segure a tecla **Espaço** para falar (Push-to-Talk).
  - Pressione **Esc** para interromper o assistente instantaneamente (Barge-In).
  - Ative o checkbox **Mãos-Livres (VAD)** para ativação contínua por voz.

### 4.3 Testando o Roteamento de Agentes
Faça os seguintes testes para confirmar o funcionamento dos protocolos:
- *"Como posso blindar meu site contra ataques de injeção SQL?"* ➔ **E.D.I.T.H.** assumirá a resposta com o tema violeta.
- *"Como devo conduzir uma conversa difícil com um colega?"* ➔ **F.R.I.D.A.Y.** assumirá a resposta com o tema dourado.
- *"Como faço para limpar arquivos temporários e cache?"* ➔ **D.U.M.-E & U** assumirá a resposta com o tema verde.
- *"Qual é a data de hoje e como está a segurança central?"* ➔ **J.A.R.V.I.S.** responderá como coordenador central.

---

## Fase 5: Manutenção e Resolução de Problemas

### 5.1 Redefinir Memória Vetorial
Caso queira limpar todo o histórico de memórias e recomeçar do zero:
```bash
docker compose down -v
docker compose up -d
```

### 5.2 Alterar Modelo para Máquinas Menos Potentes
Se sua máquina possuir menos de 16 GB de RAM ou não tiver GPU dedicada, altere no `.env`:
```env
OLLAMA_CHAT_MODEL=qwen2.5:3b
WHISPER_MODEL=tiny
```
Em seguida execute:
```bash
ollama pull qwen2.5:3b
docker compose restart jarvis-core
```
