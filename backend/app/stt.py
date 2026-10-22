"""Ouvido do Jarvis: transcrição local com faster-whisper."""
import asyncio
import io
import logging
import os
import threading

from .config import settings

log = logging.getLogger("jarvis.stt")


class SpeechToText:
    def __init__(self) -> None:
        self._model = None
        self._lock = threading.Lock()
        self.status = "não carregado"

    def _load(self):
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel  # import tardio: acelera o boot da API

                self.status = "carregando"
                log.info("Carregando Whisper '%s' (%s)...", settings.whisper_model, settings.whisper_device)
                try:
                    self._model = WhisperModel(
                        settings.whisper_model,
                        device=settings.whisper_device,
                        compute_type="int8" if settings.whisper_device == "cpu" else "float16",
                        download_root=os.path.join(settings.models_dir, "whisper"),
                    )
                except Exception as exc:
                    self.status = f"erro: {exc}"
                    raise
                self.status = "pronto"
                log.info("Whisper pronto.")
        return self._model

    async def warmup(self) -> None:
        await asyncio.to_thread(self._load)

    def _transcribe(self, audio: bytes) -> str:
        model = self._load()
        segments, _ = model.transcribe(
            io.BytesIO(audio),
            language=settings.whisper_language or None,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segments).strip()

    async def transcribe(self, audio: bytes) -> str:
        return await asyncio.to_thread(self._transcribe, audio)


stt = SpeechToText()
