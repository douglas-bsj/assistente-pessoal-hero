"""Configuração central, lida de variáveis de ambiente."""
import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = field(default_factory=lambda: _env("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"))
    chat_model: str = field(default_factory=lambda: _env("OLLAMA_CHAT_MODEL", "qwen2.5:3b"))
    embed_model: str = field(default_factory=lambda: _env("OLLAMA_EMBED_MODEL", "nomic-embed-text"))
    auto_pull: bool = field(default_factory=lambda: _env("OLLAMA_AUTO_PULL", "true").lower() in ("1", "true", "yes"))

    database_url: str = field(default_factory=lambda: _env(
        "DATABASE_URL", "postgresql://jarvis:stark_industries@localhost:5432/jarvis_memory"))
    memory_top_k: int = field(default_factory=lambda: int(_env("MEMORY_TOP_K", "5")))
    memory_max_distance: float = field(default_factory=lambda: float(_env("MEMORY_MAX_DISTANCE", "0.55")))

    whisper_model: str = field(default_factory=lambda: _env("WHISPER_MODEL", "base"))
    whisper_language: str = field(default_factory=lambda: _env("WHISPER_LANGUAGE", "pt"))
    whisper_device: str = field(default_factory=lambda: _env("WHISPER_DEVICE", "cpu"))
    models_dir: str = field(default_factory=lambda: _env("MODELS_DIR", "/models"))

    tts_voice: str = field(default_factory=lambda: _env("TTS_VOICE", "pt-BR-AntonioNeural"))
    tts_rate: str = field(default_factory=lambda: _env("TTS_RATE", "+8%"))

    user_name: str = field(default_factory=lambda: _env("JARVIS_USER_NAME", "senhor"))
    history_turns: int = field(default_factory=lambda: int(_env("HISTORY_TURNS", "10")))
    timezone: str = field(default_factory=lambda: _env("TZ", "America/Sao_Paulo"))


settings = Settings()
