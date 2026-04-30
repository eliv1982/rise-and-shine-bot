import logging
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Literal, Optional

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import get_outputs_dir
from services.language_policy import is_input_language_compatible
from services.speechkit_stt import transcribe_audio_with_meta
from services.text_quality import is_gibberish_text

VoiceProcessingStatus = Literal[
    "ok",
    "stt_failed",
    "unclear",
    "language_mismatch",
]

SttTranscriber = Callable[..., Awaitable[dict[str, Any]]]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoiceProcessingResult:
    status: VoiceProcessingStatus
    text: Optional[str] = None
    stt_meta: Optional[dict[str, Any]] = None


class VoiceInputProcessor:
    def __init__(self, stt_transcriber: SttTranscriber = transcribe_audio_with_meta) -> None:
        self._stt_transcriber = stt_transcriber

    async def process(
        self,
        message: Message,
        state: FSMContext,
        *,
        language: str,
        pending_kind: str,
    ) -> VoiceProcessingResult:
        voice = message.voice
        if not voice:
            await state.update_data(
                recognized_text_pending=None,
                recognized_text_pending_kind=None,
            )
            return VoiceProcessingResult(status="stt_failed")

        file = await message.bot.get_file(voice.file_id)
        dest_dir = get_outputs_dir()
        os.makedirs(dest_dir, exist_ok=True)
        local_path = os.path.join(
            dest_dir,
            f"voice_{pending_kind}_{message.from_user.id}_{voice.file_unique_id}.ogg",
        )
        await message.bot.download_file(file.file_path, destination=local_path)

        try:
            stt_meta = await self._stt_transcriber(local_path, language=language)
            recognized = str(stt_meta.get("recognized_text_final") or "")
        except Exception as exc:
            logger.exception("STT failed for %s voice: %s", pending_kind, exc)
            await state.update_data(
                recognized_text_pending=None,
                recognized_text_pending_kind=None,
            )
            return VoiceProcessingResult(status="stt_failed")

        await state.update_data(last_stt_meta=stt_meta, last_recognized_text=recognized)

        if is_gibberish_text(recognized):
            await state.update_data(recognized_text_pending=None, recognized_text_pending_kind=None)
            return VoiceProcessingResult(status="unclear", text=recognized, stt_meta=stt_meta)

        if not is_input_language_compatible(recognized, language):
            await state.update_data(recognized_text_pending=None, recognized_text_pending_kind=None)
            return VoiceProcessingResult(status="language_mismatch", text=recognized, stt_meta=stt_meta)

        await state.update_data(
            recognized_text_pending=recognized,
            recognized_text_pending_kind=pending_kind,
            last_recognized_text=recognized,
            last_stt_meta=stt_meta,
        )
        return VoiceProcessingResult(status="ok", text=recognized, stt_meta=stt_meta)
