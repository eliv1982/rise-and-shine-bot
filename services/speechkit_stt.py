import logging
import mimetypes
import os
from typing import Optional

import aiohttp

from config import SttProviderConfig, get_stt_provider_config

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


def _resolve_stt_language(provider_cfg: SttProviderConfig, language: str) -> str:
    if provider_cfg.provider == "yandex":
        return "en-US" if language == "en" else "ru-RU"
    # OpenAI-compatible STT may auto-detect; explicit env language has priority.
    if provider_cfg.language:
        return provider_cfg.language
    return ""


def get_stt_debug_info(language: str) -> dict[str, str]:
    cfg = get_stt_provider_config()
    return {
        "stt_provider": cfg.provider,
        "stt_model": cfg.model,
        "recognized_language": _resolve_stt_language(cfg, language) or "auto",
    }


async def transcribe_audio(
    audio_path: str,
    language: str = "ru",
) -> str:
    """Provider-aware STT (Yandex/OpenAI-compatible) with backward compatibility."""
    provider_cfg = get_stt_provider_config()

    if not os.path.exists(audio_path):
        raise RuntimeError(f"Audio file not found: {audio_path}")
    lang_code = _resolve_stt_language(provider_cfg, language)

    mime_type = _detect_mime_type(audio_path)

    try:
        with open(audio_path, "rb") as f:
            data = f.read()

        async with aiohttp.ClientSession() as session:
            if provider_cfg.provider == "yandex":
                url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
                params = {
                    "lang": lang_code or _map_language_to_stt_code(language),
                    "folderId": str(provider_cfg.options.get("folder_id") or ""),
                }
                headers = {
                    "Authorization": f"Api-Key {provider_cfg.api_key}",
                    "Content-Type": mime_type,
                }
                async with session.post(url, params=params, headers=headers, data=data, timeout=provider_cfg.timeout_seconds) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logger.error("Yandex STT error: status=%s, body=%s", resp.status, text)
                        raise RuntimeError(f"Speech recognition failed with status {resp.status}")
                    result_json = await resp.json()
                text = result_json.get("result", "").strip()
            elif provider_cfg.provider == "openai":
                base_url = (provider_cfg.base_url or "https://api.openai.com/v1").rstrip("/")
                url = f"{base_url}/audio/transcriptions"
                form = aiohttp.FormData()
                form.add_field("file", data, filename=os.path.basename(audio_path), content_type=mime_type)
                form.add_field("model", provider_cfg.model)
                if lang_code:
                    form.add_field("language", lang_code)
                headers = {
                    "Authorization": f"Bearer {provider_cfg.api_key}",
                }
                async with session.post(url, headers=headers, data=form, timeout=provider_cfg.timeout_seconds) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error("OpenAI STT error: status=%s, body=%s", resp.status, body)
                        raise RuntimeError(f"Speech recognition failed with status {resp.status}")
                    result_json = await resp.json()
                text = (result_json.get("text") or "").strip()
            else:
                raise RuntimeError(f"Unsupported STT provider: {provider_cfg.provider}")
    except Exception as exc:
        logger.exception("Error calling STT provider (%s): %s", provider_cfg.provider, exc)
        raise RuntimeError(f"Error calling STT provider: {exc}") from exc

    if not text:
        logger.error("STT provider returned empty result")
        raise RuntimeError("Speech recognition returned empty result")

    logger.info("STT recognized text via %s: %s", provider_cfg.provider, text)
    return text

