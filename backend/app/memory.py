"""Hipocampo do Jarvis: memória semântica de longo prazo em PostgreSQL + pgvector."""
import asyncio
import logging

import numpy as np
import psycopg
from pgvector.psycopg import register_vector_async

from .config import settings
from .ollama_client import ollama

log = logging.getLogger("jarvis.memory")

# nomic-embed-text funciona melhor com prefixos de tarefa
_DOC_PREFIX = "search_document: "
_QUERY_PREFIX = "search_query: "
_DUPLICATE_DISTANCE = 0.06


class Memory:
    def __init__(self) -> None:
        self._ready = False
        self._lock = asyncio.Lock()
        self.dimension: int | None = None
        self.error: str | None = None

    @property
    def ready(self) -> bool:
        return self._ready

    def _prefix(self, kind: str) -> str:
        if "nomic" not in settings.embed_model:
            return ""
        return _DOC_PREFIX if kind == "doc" else _QUERY_PREFIX

    async def _embed(self, text: str, kind: str) -> np.ndarray:
        return np.array(await ollama.embed(self._prefix(kind) + text), dtype=np.float32)

    async def _connect(self) -> psycopg.AsyncConnection:
        conn = await psycopg.AsyncConnection.connect(settings.database_url, autocommit=True)
        await register_vector_async(conn)
        return conn

    async def ensure_ready(self) -> None:
        if self._ready:
            return
        async with self._lock:
            if self._ready:
                return
            try:
                dim = len(await self._embed("calibração", "doc"))
                async with await psycopg.AsyncConnection.connect(settings.database_url, autocommit=True) as conn:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    await conn.execute(f"""
                        CREATE TABLE IF NOT EXISTS memories (
                            id          BIGSERIAL PRIMARY KEY,
                            content     TEXT        NOT NULL,
                            category    TEXT        NOT NULL DEFAULT 'geral',
                            source      TEXT        NOT NULL DEFAULT 'manual',
                            embedding   vector({dim}) NOT NULL,
                            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
                        )""")
                    cur = await conn.execute(
                        "SELECT atttypmod FROM pg_attribute "
                        "WHERE attrelid = 'memories'::regclass AND attname = 'embedding'")
                    row = await cur.fetchone()
                    if row and row[0] != dim:
                        raise RuntimeError(
                            f"A tabela 'memories' usa vetores de {row[0]} dimensões, mas o modelo "
                            f"'{settings.embed_model}' gera {dim}. Volte ao modelo anterior ou "
                            f"apague o volume do banco (docker compose down -v).")
                self.dimension = dim
                self.error = None
                self._ready = True
                log.info("Memória pronta (pgvector, %d dimensões).", dim)
            except Exception as exc:
                self.error = str(exc)
                raise

    async def add(self, content: str, category: str = "geral", source: str = "manual") -> dict:
        await self.ensure_ready()
        content = content.strip()
        if not content:
            raise ValueError("Memória vazia.")
        emb = await self._embed(content, "doc")
        async with await self._connect() as conn:
            cur = await conn.execute(
                "SELECT id, content, embedding <=> %s AS d FROM memories ORDER BY d LIMIT 1", (emb,))
            dup = await cur.fetchone()
            if dup and dup[2] is not None and dup[2] < _DUPLICATE_DISTANCE:
                return {"id": dup[0], "content": dup[1], "duplicate": True}
            cur = await conn.execute(
                "INSERT INTO memories (content, category, source, embedding) "
                "VALUES (%s, %s, %s, %s) RETURNING id, created_at",
                (content, category, source, emb))
            row = await cur.fetchone()
        return {"id": row[0], "content": content, "category": category, "source": source,
                "created_at": row[1].isoformat(), "duplicate": False}

    async def search(self, query: str, k: int | None = None) -> list[dict]:
        await self.ensure_ready()
        emb = await self._embed(query, "query")
        async with await self._connect() as conn:
            cur = await conn.execute(
                "SELECT id, content, category, embedding <=> %s AS d FROM memories "
                "ORDER BY d LIMIT %s", (emb, k or settings.memory_top_k))
            rows = await cur.fetchall()
        return [{"id": r[0], "content": r[1], "category": r[2], "score": round(1 - float(r[3]), 3)}
                for r in rows if r[3] is not None and r[3] <= settings.memory_max_distance]

    async def list(self, limit: int = 200) -> list[dict]:
        await self.ensure_ready()
        async with await self._connect() as conn:
            cur = await conn.execute(
                "SELECT id, content, category, source, created_at FROM memories "
                "ORDER BY created_at DESC LIMIT %s", (limit,))
            rows = await cur.fetchall()
        return [{"id": r[0], "content": r[1], "category": r[2], "source": r[3],
                 "created_at": r[4].isoformat()} for r in rows]

    async def delete(self, memory_id: int) -> bool:
        await self.ensure_ready()
        async with await self._connect() as conn:
            cur = await conn.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
            return cur.rowcount > 0


memory = Memory()
