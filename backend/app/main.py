"""J.A.R.V.I.S. Core — API HTTP, WebSocket de voz em tempo real e interface web."""
import asyncio
import json
import logging
import struct
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import brain, tts
from .config import settings
from .memory import memory
from .ollama_client import OllamaError, ollama
from .stt import stt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
log = logging.getLogger("jarvis")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
boot_state: dict = {"models": {}, "pulling": None, "error": None}


# ---------------------------------------------------------------- inicialização
async def _bootstrap() -> None:
    """Prepara tudo em segundo plano. A API já responde enquanto isso acontece."""
    asyncio.create_task(_safe(stt.warmup(), "Whisper"))

    for attempt in range(60):
        if await ollama.is_up():
            break
        if attempt == 0:
            log.warning("Ollama não respondeu em %s — tentando novamente...", settings.ollama_base_url)
        await asyncio.sleep(5)
    else:
        boot_state["error"] = f"Ollama inacessível em {settings.ollama_base_url}"
        log.error(boot_state["error"])
        return

    for model in (settings.embed_model, settings.chat_model):
        try:
            if not await ollama.has_model(model):
                if not settings.auto_pull:
                    raise OllamaError(f"Modelo '{model}' não instalado. Rode: ollama pull {model}")
                boot_state["pulling"] = model
                await ollama.pull(model)
            boot_state["models"][model] = True
        except Exception as exc:
            boot_state["models"][model] = False
            boot_state["error"] = str(exc)
            log.error("Falha ao preparar modelo %s: %s", model, exc)
        finally:
            boot_state["pulling"] = None

    await _safe(memory.ensure_ready(), "Memória")
    log.info("J.A.R.V.I.S. online em http://localhost:8000 — às suas ordens, %s.", settings.user_name)


async def _safe(coro, name: str) -> None:
    try:
        await coro
    except Exception as exc:
        log.error("%s falhou ao iniciar: %s", name, exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(_bootstrap())
    yield
    task.cancel()
    await ollama.close()


app = FastAPI(title="J.A.R.V.I.S. Core", version="3.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def friendly_error(exc: Exception) -> str:
    if isinstance(exc, httpx.ConnectError):
        return f"Não consigo alcançar o Ollama em {settings.ollama_base_url}. Ele está rodando?"
    if isinstance(exc, (httpx.TimeoutException,)):
        return "O modelo demorou demais para responder."
    msg = str(exc)
    if "not found" in msg and "model" in msg:
        return f"Modelo não encontrado no Ollama. Rode: ollama pull {settings.chat_model}"
    return msg or exc.__class__.__name__


# ---------------------------------------------------------------- REST
class ChatIn(BaseModel):
    text: str = Field(min_length=1)


class MemoryIn(BaseModel):
    content: str = Field(min_length=1)
    category: str = "geral"


class SearchIn(BaseModel):
    query: str = Field(min_length=1)


_rest_session = brain.Session()


@app.get("/api/health")
async def health():
    ollama_up = await ollama.is_up()
    return {
        "core": "online",
        "ollama": {"up": ollama_up, "url": settings.ollama_base_url,
                   "chat_model": settings.chat_model, "embed_model": settings.embed_model,
                   "models": boot_state["models"], "pulling": boot_state["pulling"]},
        "memory": {"ready": memory.ready, "dimension": memory.dimension, "error": memory.error},
        "stt": {"status": stt.status, "model": settings.whisper_model},
        "tts": {"voice": settings.tts_voice},
        "error": boot_state["error"],
    }


@app.post("/api/chat")
async def chat(body: ChatIn):
    try:
        reply, memories = "", []
        async for kind, value in brain.respond(_rest_session, body.text):
            if kind == "memories":
                memories = value
            elif kind == "done":
                reply = value
        asyncio.create_task(_safe(brain.learn(body.text), "Aprendizado"))
        return {"response": reply, "memories": memories}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=friendly_error(exc))


@app.get("/api/memories")
async def list_memories():
    try:
        return await memory.list()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=friendly_error(exc))


@app.post("/api/memories")
async def add_memory(body: MemoryIn):
    try:
        return await memory.add(body.content, category=body.category, source="manual")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=friendly_error(exc))


@app.post("/api/memories/search")
async def search_memories(body: SearchIn):
    try:
        return await memory.search(body.query, k=10)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=friendly_error(exc))


@app.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: int):
    if not await memory.delete(memory_id):
        raise HTTPException(status_code=404, detail="Memória não encontrada")
    return {"deleted": memory_id}


@app.get("/api/agents")
async def list_agents():
    from .agents import AGENTS
    return [
        {
            "id": a.id,
            "name": a.name,
            "role": a.role,
            "description": a.description.format(user=settings.user_name),
            "voice": a.voice,
            "color": a.color_rgb,
        }
        for a in AGENTS.values()
    ]


# ---------------------------------------------------------------- WebSocket de voz
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    """
    Protocolo:
      cliente -> binário: áudio de uma fala (webm/ogg/wav)
      cliente -> JSON {type:"text", text, speak, agent} | {type:"set_agent", agent} | {type:"interrupt"} | {type:"reset"}
      servidor -> JSON {type: state|user|agent|token|memories|assistant_end|memory_added|stt_empty|error}
      servidor -> binário: [uint32 turn_id][mp3] (uma frase falada)
    """
    await ws.accept()
    session = brain.Session()
    send_lock = asyncio.Lock()
    current: asyncio.Task | None = None
    current_agent = "jarvis"
    turn = 0

    async def send_json(obj: dict) -> None:
        async with send_lock:
            await ws.send_text(json.dumps(obj, ensure_ascii=False))

    async def send_audio(turn_id: int, audio: bytes) -> None:
        async with send_lock:
            await ws.send_bytes(struct.pack(">I", turn_id) + audio)

    async def run_turn(turn_id: int, text: str | None, audio: bytes | None, speak: bool, preferred_agent: str = "jarvis") -> None:
        nonlocal current_agent
        try:
            if audio is not None:
                await send_json({"type": "state", "state": "transcribing", "turn": turn_id})
                text = await stt.transcribe(audio)
                if not text:
                    await send_json({"type": "stt_empty", "turn": turn_id})
                    return
            await send_json({"type": "user", "text": text, "turn": turn_id})
            await send_json({"type": "state", "state": "thinking", "turn": turn_id})

            queue: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()

            async def speaker() -> None:
                while (item := await queue.get()) is not None:
                    sentence, voice = item
                    try:
                        mp3 = await tts.synthesize(sentence, voice=voice)
                        if mp3:
                            await send_audio(turn_id, mp3)
                    except Exception as exc:
                        log.warning("TTS falhou: %s", exc)

            speaker_task = asyncio.create_task(speaker()) if speak else None
            active_voice = None

            try:
                async for kind, value in brain.respond(session, text, agent_id=preferred_agent):
                    if kind == "agent":
                        agent_id = str(value)
                        current_agent = agent_id
                        agent_profile = brain.get_agent(agent_id)
                        active_voice = agent_profile.voice
                        await send_json({
                            "type": "agent",
                            "agent": agent_id,
                            "name": agent_profile.name,
                            "role": agent_profile.role,
                            "color": agent_profile.color_rgb,
                            "turn": turn_id
                        })
                    elif kind == "token":
                        await send_json({"type": "token", "text": value, "turn": turn_id})
                    elif kind == "memories":
                        await send_json({"type": "memories", "items": value, "turn": turn_id})
                    elif kind == "sentence" and speaker_task:
                        await queue.put((value, active_voice))
                await send_json({"type": "assistant_end", "turn": turn_id})
                if speaker_task:
                    await queue.put(None)
                    await speaker_task
            finally:
                if speaker_task and not speaker_task.done():
                    speaker_task.cancel()

            asyncio.create_task(learn_and_notify(text))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("Erro no turno %s", turn_id)
            await send_json({"type": "error", "message": friendly_error(exc), "turn": turn_id})
        finally:
            try:
                await send_json({"type": "state", "state": "idle", "turn": turn_id})
            except Exception:
                pass

    async def learn_and_notify(text: str) -> None:
        try:
            saved = await brain.learn(text)
            if saved:
                await send_json({"type": "memory_added", "items": saved})
        except Exception as exc:
            log.debug("Aprendizado ignorado: %s", exc)

    async def cancel_current() -> None:
        nonlocal current
        if current and not current.done():
            current.cancel()
            try:
                await current
            except (asyncio.CancelledError, Exception):
                pass
        current = None

    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("bytes"):
                await cancel_current()
                turn += 1
                current = asyncio.create_task(run_turn(turn, None, msg["bytes"], True, preferred_agent=current_agent))
            elif msg.get("text"):
                try:
                    data = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                kind = data.get("type")
                if kind == "set_agent":
                    current_agent = data.get("agent", "jarvis")
                    profile = brain.get_agent(current_agent)
                    await send_json({
                        "type": "agent",
                        "agent": profile.id,
                        "name": profile.name,
                        "role": profile.role,
                        "color": profile.color_rgb,
                        "turn": turn
                    })
                elif kind == "text" and str(data.get("text", "")).strip():
                    await cancel_current()
                    turn += 1
                    agent_to_use = data.get("agent") or current_agent
                    current = asyncio.create_task(
                        run_turn(turn, data["text"].strip(), None, bool(data.get("speak", True)), preferred_agent=agent_to_use))
                elif kind == "interrupt":
                    await cancel_current()
                    await send_json({"type": "state", "state": "idle", "turn": turn})
                elif kind == "reset":
                    await cancel_current()
                    session.clear()
    except WebSocketDisconnect:
        pass
    finally:
        await cancel_current()


# ---------------------------------------------------------------- interface web
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")
