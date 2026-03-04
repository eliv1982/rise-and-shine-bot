import logging
import mimetypes
import os
from typing import Optional

import aiohttp

from config import get_settings

logger = logging.getLogger(__name__)


def _detect_mime_type(path: str) -> str:
    """
    Определяет MIME-тип по расширению файла, по умолчанию audio/ogg.
    """
    mime, _ = mimetypes.guess_type(path)
    if mime is None:
        return "audio/ogg"
    return mime


def _map_language_to_stt_code(language: str) -> str:
    """
    Преобразует 'ru' / 'en' в коды, ожидаемые SpeechKit.
    """
    if language == "en":
        return "en-US"
    return "ru-RU"


async def transcribe_audio(
    audio_path: str,
    language: str = "ru",
) -> str:
    """
    Отправляет аудиофайл в Yandex SpeechKit STT и возвращает распознанный текст.
    В случае ошибки поднимает RuntimeError.
    """
    settings = get_settings()

    if not os.path.exists(audio_path):
        raise RuntimeError(f"Audio file not found: {audio_path}")

    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

    lang_code = _map_language_to_stt_code(language)
    params = {
        "lang": lang_code,
        "folderId": settings.yandex_folder_id,
    }

    mime_type = _detect_mime_type(audio_path)

    headers = {
        # Можно использовать Api-Key или IAM-токен; здесь предполагаем ключ.
        "Authorization": f"Api-Key {settings.yandex_speechkit_api_key}",
        "Content-Type": mime_type,
    }

    try:
        with open(audio_path, "rb") as f:
            data = f.read()

        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params, headers=headers, data=data, timeout=120) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error("SpeechKit STT error: status=%s, body=%s", resp.status, text)
                    raise RuntimeError(f"SpeechKit STT request failed with status {resp.status}")
                result_json = await resp.json()
    except Exception as exc:
        logger.exception("Error calling SpeechKit STT: %s", exc)
        raise RuntimeError(f"Error calling SpeechKit STT: {exc}") from exc

    # Ожидаемый формат: {"result": "распознанный текст", ...}
    text = result_json.get("result", "").strip()
    if not text:
        logger.error("SpeechKit STT returned empty result: %s", result_json)
        raise RuntimeError("SpeechKit STT returned empty result")

    logger.info("SpeechKit STT recognized text: %s", text)
    return text

