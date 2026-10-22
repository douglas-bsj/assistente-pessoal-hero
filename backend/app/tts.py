"""Boca do Jarvis: síntese de voz neural com edge-tts."""
import re

import edge_tts

from .config import settings

_MD = re.compile(r"[*_`#>~|]+")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]+")
_CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]+")


def clean_for_speech(text: str) -> str:
    text = _LINK.sub(r"\1", text)
    text = _MD.sub("", text)
    text = _EMOJI.sub("", text)
    text = _CJK.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


async def synthesize(text: str, voice: str | None = None) -> bytes:
    text = clean_for_speech(text)
    if not any(c.isalnum() for c in text):
        return b""
    selected_voice = voice or settings.tts_voice
    communicate = edge_tts.Communicate(text, selected_voice, rate=settings.tts_rate)
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            audio.extend(chunk["data"])
    return bytes(audio)
