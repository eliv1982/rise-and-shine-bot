import logging
import mimetypes
import os
import re
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


def _resolve_stt_language(provider_cfg: SttProviderConfig, language: str) -> str:
    if language == "auto":
        return ""
    # OpenAI STT may auto-detect; explicit env language has priority.
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


def score_stt_result(text: str, language_hint: Optional[str] = None) -> float:
    t = (text or "").strip()
    if len(t) < 4:
        return -3.0
    low = t.lower()
    suspicious_fragments = ("weh weh", "do stoint", "sosday", "nstra", "divertuz")
    penalty = 0.0
    if any(fragment in low for fragment in suspicious_fragments):
        penalty += 2.5
    words = re.findall(r"[A-Za-zА-Яа-яЁё]+", t)
    if len(words) < 2:
        return -2.0 - penalty
    unique_ratio = len(set(w.lower() for w in words)) / max(1, len(words))
    if unique_ratio < 0.34:
        penalty += 1.5
    weird_tokens = 0
    for w in words:
        lw = w.lower()
        if len(lw) >= 6 and not re.search(r"[aeiouyаеёиоуыэюя]", lw):
            weird_tokens += 1
    if words and weird_tokens / len(words) > 0.4:
        penalty += 2.0
    cyr = len(re.findall(r"[А-Яа-яЁё]", t))
    lat = len(re.findall(r"[A-Za-z]", t))
    # English UI with accidental Cyrillic should not be treated as poor by default:
    # fallback scoring below decides which attempt is better.
    language_bonus = 0.0
    if language_hint == "ru":
        language_bonus += 0.6 if cyr > 0 else -0.6
    elif language_hint == "en":
        language_bonus += 0.4 if lat > 0 else -0.4
    base = min(2.5, 0.25 * len(words)) + unique_ratio + language_bonus
    return base - penalty


def is_poor_stt_result(text: str, expected_language: Optional[str] = None) -> bool:
    return score_stt_result(text, language_hint=expected_language) < 0.3


async def _transcribe_once(provider_cfg: SttProviderConfig, audio_path: str, language_hint: str) -> str:
    lang_code = _resolve_stt_language(provider_cfg, language_hint)
    mime_type = _detect_mime_type(audio_path)
    with open(audio_path, "rb") as f:
        data = f.read()
    async with aiohttp.ClientSession() as session:
        base_url = (provider_cfg.base_url or "https://api.openai.com/v1").rstrip("/")
        url = f"{base_url}/audio/transcriptions"
        form = aiohttp.FormData()
        form.add_field("file", data, filename=os.path.basename(audio_path), content_type=mime_type)
        form.add_field("model", provider_cfg.model)
        if lang_code:
            form.add_field("language", lang_code)
        headers = {"Authorization": f"Bearer {provider_cfg.api_key}"}
        async with session.post(url, headers=headers, data=form, timeout=provider_cfg.timeout_seconds) as resp:
            if resp.status != 200:
                body = await resp.text()
                logger.error("OpenAI STT error: status=%s, body=%s", resp.status, body)
                raise RuntimeError(f"Speech recognition failed with status {resp.status}")
            result_json = await resp.json()
        return (result_json.get("text") or "").strip()


async def transcribe_audio_with_meta(
    audio_path: str,
    language: str = "ru",
) -> dict[str, str | int | list[str]]:
    provider_cfg = get_stt_provider_config()
    if not os.path.exists(audio_path):
        raise RuntimeError(f"Audio file not found: {audio_path}")

    allow_cross = bool(provider_cfg.options.get("allow_cross_language_stt_fallback", False))
    attempts = [language]
    if allow_cross:
        alternate = "ru" if language == "en" else "en"
        if alternate != language:
            attempts.append(alternate)

    best_text = ""
    used_attempts = []
    for attempt_lang in attempts:
        used_attempts.append(attempt_lang)
        if not provider_cfg.language:
            # Attempt 1: auto language. Attempt 2: explicit alternate hint.
            lang_for_attempt = "auto" if len(used_attempts) == 1 else attempt_lang
        else:
            lang_for_attempt = attempt_lang
        text = await _transcribe_once(provider_cfg, audio_path, lang_for_attempt)
        current_score = score_stt_result(text, language_hint=attempt_lang)
        best_score = score_stt_result(best_text, language_hint=attempt_lang) if best_text else -999.0
        if text and (current_score > best_score or not best_text):
            best_text = text
        if text and not is_poor_stt_result(text, expected_language=attempt_lang):
            break

    if not best_text:
        logger.error("STT provider returned empty result after retries")
        raise RuntimeError("Speech recognition returned empty result")

    recognized_lang = "auto"
    if re.search(r"[А-Яа-яЁё]", best_text):
        recognized_lang = "ru"
    elif re.search(r"[A-Za-z]", best_text):
        recognized_lang = "en"

    return {
        "recognized_text_raw": best_text,
        "recognized_text_final": best_text,
        "recognized_language": recognized_lang,
        "stt_provider": provider_cfg.provider,
        "stt_model": provider_cfg.model,
        "stt_attempt_count": len(used_attempts),
        "stt_language_attempts": used_attempts,
    }


async def transcribe_audio(
    audio_path: str,
    language: str = "ru",
) -> str:
    """Compatibility wrapper returning only final text."""
    try:
        meta = await transcribe_audio_with_meta(audio_path=audio_path, language=language)
    except Exception as exc:
        provider = get_stt_provider_config().provider
        logger.exception("Error calling STT provider (%s): %s", provider, exc)
        raise RuntimeError(f"Error calling STT provider: {exc}") from exc
    text = str(meta.get("recognized_text_final") or "").strip()
    if not text:
        raise RuntimeError("Speech recognition returned empty result")
    logger.info("STT recognized text: %s", text)
    return text

