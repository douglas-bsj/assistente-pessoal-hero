"""Cérebro do Jarvis: monta o contexto (persona + memórias + histórico), conversa e aprende."""
import logging
import re
from datetime import datetime
from typing import AsyncIterator
from zoneinfo import ZoneInfo

from .config import settings
from .memory import memory
from .ollama_client import ollama

log = logging.getLogger("jarvis.brain")

PERSONA = """Você é J.A.R.V.I.S. (Just A Rather Very Intelligent System), o assistente pessoal de {user}.
Personalidade: leal, extremamente competente, calmo, com humor britânico sutil e elegante.
Regras:
- Responda SEMPRE em português do Brasil, de forma natural e falada.
- Seja conciso: no máximo 3 frases curtas, a menos que peçam detalhes.
- Não use markdown, listas, emojis ou blocos de código: sua resposta será convertida em voz.
- Trate o usuário por "senhor" ou pelo nome, se souber.
- Use as memórias abaixo quando forem relevantes, sem dizer que está "consultando memórias".
- Se não souber algo, admita com elegância. Nunca invente fatos sobre o usuário."""

EXTRACT_PROMPT = """Você extrai fatos duradouros sobre o usuário a partir da mensagem dele.
Extraia APENAS informações úteis a longo prazo: nome, preferências, família, trabalho, projetos,
rotina, objetivos, ou qualquer coisa que ele peça explicitamente para lembrar.
Ignore perguntas, comandos momentâneos, saudações e conversa casual.
Escreva cada fato em português, curto, em terceira pessoa (ex: "O usuário prefere café preto").
Responda somente JSON no formato {"facts": ["..."]}. Sem fatos: {"facts": []}."""

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…;:])\s+|\n+")
_MIN_TTS_CHARS = 28


class Session:
    """Memória de curto prazo (conversa atual)."""

    def __init__(self) -> None:
        self.history: list[dict] = []

    def add_turn(self, user: str, assistant: str) -> None:
        self.history += [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}]
        self.history = self.history[-settings.history_turns * 2:]

    def clear(self) -> None:
        self.history.clear()


_WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]


def _now() -> str:
    try:
        now = datetime.now(ZoneInfo(settings.timezone))
    except Exception:
        now = datetime.now()
    return f"{_WEEKDAYS[now.weekday()]}, {now:%d/%m/%Y %H:%M}"


from .agents import get_agent, detect_requested_agent, AGENTS


async def build_messages(session: Session, user_text: str, agent_id: str = "jarvis") -> tuple[list[dict], list[dict], str]:
    memories: list[dict] = []
    try:
        memories = await memory.search(user_text)
    except Exception as exc:
        log.warning("Memória indisponível: %s", exc)

    active_agent = detect_requested_agent(user_text, current_agent=agent_id)
    profile = get_agent(active_agent)

    system = profile.system_prompt.format(user=settings.user_name)
    if memories:
        system += "\n\nMemórias sobre o usuário:\n" + "\n".join(f"- {m['content']}" for m in memories)
    system += f"\n\nData/hora atual: {_now()}."
    return [{"role": "system", "content": system}, *session.history,
            {"role": "user", "content": user_text}], memories, active_agent


_CHINESE_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]+")


async def respond(session: Session, user_text: str, agent_id: str = "jarvis") -> AsyncIterator[tuple[str, object]]:
    """Gera eventos: ("agent", str), ("memories", list), ("token", str), ("sentence", str), ("done", str)."""
    messages, memories, active_agent = await build_messages(session, user_text, agent_id)
    yield "agent", active_agent
    if memories:
        yield "memories", memories

    full, buffer, pending = "", "", ""
    async for raw_token in ollama.chat_stream(messages, options={"temperature": 0.35, "top_p": 0.85}):
        token = _CHINESE_RE.sub("", raw_token)
        if not token:
            continue
        full += token
        buffer += token
        yield "token", token
        parts = _SENTENCE_SPLIT.split(buffer)
        if len(parts) > 1:
            buffer = parts[-1]
            for sentence in parts[:-1]:
                pending = f"{pending} {sentence}".strip()
                if len(pending) >= _MIN_TTS_CHARS:
                    yield "sentence", pending
                    pending = ""
    tail = f"{pending} {buffer}".strip()
    if tail:
        yield "sentence", tail

    session.add_turn(user_text, full.strip())
    yield "done", full.strip()


async def learn(user_text: str) -> list[dict]:
    """Extrai fatos duradouros da fala do usuário e grava na memória de longo prazo."""
    if len(user_text.strip()) < 5:
        return []
    data = await ollama.chat_json([
        {"role": "system", "content": EXTRACT_PROMPT},
        {"role": "user", "content": user_text},
    ])
    saved = []
    for fact in (data.get("facts") or [])[:5]:
        if isinstance(fact, str) and len(fact.strip()) > 5:
            item = await memory.add(fact, category="aprendido", source="auto")
            if not item.get("duplicate"):
                saved.append(item)
    if saved:
        log.info("Aprendi %d fato(s) novo(s).", len(saved))
    return saved
