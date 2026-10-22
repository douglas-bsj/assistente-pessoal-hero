"""Cliente assíncrono mínimo para a API REST do Ollama."""
import json
import logging
from typing import AsyncIterator

import httpx

from .config import settings

log = logging.getLogger("jarvis.ollama")


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._client = httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(180.0, connect=5.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def is_up(self) -> bool:
        try:
            r = await self._client.get("/api/tags", timeout=3.0)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def list_models(self) -> list[str]:
        r = await self._client.get("/api/tags", timeout=5.0)
        r.raise_for_status()
        return [m.get("name", "") for m in r.json().get("models", [])]

    async def has_model(self, name: str) -> bool:
        wanted = name if ":" in name else f"{name}:latest"
        return any(m in (name, wanted) for m in await self.list_models())

    async def pull(self, name: str) -> None:
        log.info("Baixando modelo %s no Ollama (pode demorar na primeira vez)...", name)
        last = None
        async with self._client.stream("POST", "/api/pull", json={"model": name}, timeout=None) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if "error" in data:
                    raise OllamaError(data["error"])
                status = data.get("status")
                if status and status != last and not status.startswith("pulling "):
                    log.info("  %s: %s", name, status)
                last = status
        log.info("Modelo %s pronto.", name)

    async def embed(self, text: str) -> list[float]:
        r = await self._client.post("/api/embed", json={"model": settings.embed_model, "input": text})
        if r.status_code != 200:
            raise OllamaError(f"Embedding falhou ({r.status_code}): {r.text[:200]}")
        return r.json()["embeddings"][0]

    async def chat_stream(self, messages: list[dict], options: dict | None = None) -> AsyncIterator[str]:
        payload = {
            "model": settings.chat_model,
            "messages": messages,
            "stream": True,
            "keep_alive": "30m",
            "options": options or {},
        }
        async with self._client.stream("POST", "/api/chat", json=payload) as r:
            if r.status_code != 200:
                body = (await r.aread()).decode(errors="ignore")
                raise OllamaError(f"Chat falhou ({r.status_code}): {body[:300]}")
            async for line in r.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if "error" in data:
                    raise OllamaError(data["error"])
                chunk = data.get("message", {}).get("content", "")
                if chunk:
                    yield chunk
                if data.get("done"):
                    break

    async def chat_json(self, messages: list[dict]) -> dict:
        payload = {
            "model": settings.chat_model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "keep_alive": "30m",
            "options": {"temperature": 0},
        }
        r = await self._client.post("/api/chat", json=payload)
        if r.status_code != 200:
            raise OllamaError(f"Chat JSON falhou ({r.status_code}): {r.text[:200]}")
        content = r.json().get("message", {}).get("content", "{}")
        try:
            data = json.loads(content)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}


ollama = OllamaClient(settings.ollama_base_url)
