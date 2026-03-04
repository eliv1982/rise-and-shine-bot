"""
Озвучивание текста через Yandex SpeechKit TTS.
Голос выбирается по полу пользователя; результат в формате oggopus для голосовых сообщений.
Склейка аффирмаций с паузами — через ffmpeg (concat demuxer).
"""
import asyncio
import logging
import os
import shutil
import time
from typing import List, Optional

import aiohttp

from config import get_outputs_dir, get_settings

logger = logging.getLogger(__name__)


_ffmpeg_path: Optional[str] = None


def _find_ffmpeg() -> str:
    """
    Возвращает путь к ffmpeg. Работает на Windows (в т.ч. поиск после winget) и на сервере (Linux).
    На сервере: установи ffmpeg (apt install ffmpeg) — тогда достаточно PATH.
    Либо задай FFMPEG_PATH в .env / переменных окружения.
    """
    global _ffmpeg_path
    if _ffmpeg_path is not None:
        return _ffmpeg_path
    env_path = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BINARY")
    if env_path and os.path.isfile(env_path):
        _ffmpeg_path = env_path
        return _ffmpeg_path
    which = shutil.which("ffmpeg")
    if which:
        _ffmpeg_path = which
        return _ffmpeg_path
    # Только на Windows — типичные пути после winget
    if os.name == "nt":
        for candidate in (
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"),
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        ):
            if os.path.isfile(candidate):
                _ffmpeg_path = candidate
                return _ffmpeg_path
        winget = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
        if os.path.isdir(winget):
            for name in os.listdir(winget):
                if "ffmpeg" in name.lower():
                    pkg = os.path.join(winget, name)
                    if os.path.isdir(pkg):
                        for sub in os.listdir(pkg):
                            bin_path = os.path.join(pkg, sub, "bin", "ffmpeg.exe")
                            if os.path.isfile(bin_path):
                                _ffmpeg_path = bin_path
                                return _ffmpeg_path
    _ffmpeg_path = "ffmpeg"
    return _ffmpeg_path

# Скорость речи для озвучки аффирмаций (чуть медленнее)
AFFIRMATION_SPEED = 0.75

# Максимальная длина текста за один запрос (лимит API ~5000 символов, берём с запасом)
MAX_TEXT_LENGTH = 4500


def _voice_for_gender(gender: Optional[str]) -> str:
    """
    Возвращает имя голоса SpeechKit: filipp для мужчин, oksana для женщин и по умолчанию.
    """
    if gender == "male":
        return "filipp"
    return "oksana"


async def synthesize_speech(
    text: str,
    gender: Optional[str] = None,
    *,
    emotion: str = "good",
    speed: float = 0.85,
) -> str:
    """
    Синтезирует речь из текста через Yandex SpeechKit TTS.

    :param text: Текст для озвучки (на русском).
    :param gender: Пол пользователя из БД ("female" / "male") для выбора голоса.
    :param emotion: Эмоция голоса (good / neutral / evil).
    :param speed: Скорость речи (0.1–3.0), по умолчанию 0.85.
    :return: Путь к созданному аудиофайлу (oggopus).
    :raises RuntimeError: При ошибке запроса или недоступности TTS.
    """
    if not text or not text.strip():
        raise RuntimeError("Текст для озвучки пуст")

    text = text.strip()
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH].rsplit(maxsplit=1)[0] or text[:MAX_TEXT_LENGTH]

    settings = get_settings()
    voice = _voice_for_gender(gender)
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"

    # Текст и параметры в теле запроса (form), чтобы не упираться в лимит длины URL
    form = aiohttp.FormData()
    form.add_field("text", text)
    form.add_field("lang", "ru-RU")
    form.add_field("voice", voice)
    form.add_field("emotion", emotion)
    form.add_field("speed", str(speed))
    form.add_field("folderId", settings.yandex_folder_id)
    form.add_field("format", "oggopus")

    headers = {
        "Authorization": f"Api-Key {settings.yandex_speechkit_api_key}",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form, headers=headers, timeout=60) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("SpeechKit TTS error: status=%s, body=%s", resp.status, body[:500])
                    raise RuntimeError(
                        "Сервис озвучки временно недоступен. Попробуй позже."
                    )
                data = await resp.read()
    except aiohttp.ClientError as exc:
        logger.exception("SpeechKit TTS request failed: %s", exc)
        raise RuntimeError("Сервис озвучки временно недоступен. Попробуй позже.") from exc

    out_dir = get_outputs_dir()
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"tts_{voice}_{int(time.time() * 1000)}.ogg")
    with open(path, "wb") as f:
        f.write(data)
    return path


async def _create_silence_from_segment(
    ffmpeg_cmd: str, out_path: str, first_segment_path: str, duration: float, cwd: str
) -> Optional[str]:
    """Запасной способ: тишина = первый сегмент с volume=0 (тот же кодек). Возвращает out_path или None."""
    first_basename = os.path.basename(first_segment_path)
    out_basename = os.path.basename(out_path)
    proc = await asyncio.create_subprocess_exec(
        ffmpeg_cmd, "-y", "-nostdin", "-i", first_basename,
        "-af", "volume=0", "-t", str(duration), "-c:a", "libopus", "-b:a", "64k", out_basename,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning("ffmpeg silence-from-segment failed: %s", (stderr or b"").decode(errors="replace")[-800:])
        return None
    return out_path


def _make_concat_list_file(list_path: str, segment_paths: List[str], silence_basename: str) -> None:
    """Пишет файл списка для ffmpeg concat demuxer: сегмент1, тишина, сегмент2, тишина, ...
    Используются только имена файлов (относительно list_path), чтобы не ломаться на путях с пробелами."""
    lines = []
    for i, path in enumerate(segment_paths):
        name = os.path.basename(path)
        # Экранируем одинарные кавычки в имени для ffmpeg
        name_esc = name.replace("'", "'\\''") if os.name != "nt" else name
        lines.append(f"file '{name_esc}'")
        if i < len(segment_paths) - 1:
            silence_esc = silence_basename.replace("'", "'\\''") if os.name != "nt" else silence_basename
            lines.append(f"file '{silence_esc}'")
    with open(list_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


async def synthesize_affirmations_with_pauses(
    affirmations: List[str],
    gender: Optional[str] = None,
    *,
    pause_seconds: float = 5.0,
    speed: float = AFFIRMATION_SPEED,
) -> str:
    """
    Озвучивает список аффирмаций по одной, с паузой между ними.
    Склейка через ffmpeg (concat). Возвращает путь к итоговому ogg-файлу.
    """
    if not affirmations:
        raise RuntimeError("Нет аффирмаций для озвучки")
    affirmations = [a.strip() for a in affirmations if a and a.strip()]
    if not affirmations:
        raise RuntimeError("Нет аффирмаций для озвучки")

    out_dir = os.path.abspath(get_outputs_dir())
    os.makedirs(out_dir, exist_ok=True)
    ts = int(time.time() * 1000)
    temp_paths: List[str] = []

    try:
        for i, text in enumerate(affirmations):
            path_i = await synthesize_speech(text, gender=gender, emotion="good", speed=speed)
            temp_paths.append(os.path.abspath(path_i))

        if len(temp_paths) == 1:
            result_path = os.path.join(out_dir, f"tts_affirmations_{ts}.ogg")
            shutil.copy(temp_paths[0], result_path)
            return result_path

        ffmpeg_cmd = _find_ffmpeg()
        logger.info("Using ffmpeg: %s (%d segments)", ffmpeg_cmd, len(temp_paths))
        silence_basename = f"silence_5s_{ts}.ogg"
        list_basename = f"concat_list_{ts}.txt"
        result_basename = f"tts_affirmations_{ts}.ogg"
        # Все пути для ffmpeg — относительные (cwd=out_dir), чтобы не ломаться на пробелах в пути
        # 1) Тишина: lavfi -> libopus (стерео: libopus в ряде сборок не принимает mono)
        proc_silence = await asyncio.create_subprocess_exec(
            ffmpeg_cmd, "-y", "-nostdin", "-f", "lavfi", "-i", "anullsrc=r=48000:channel_layout=stereo",
            "-t", str(pause_seconds), "-c:a", "libopus", "-b:a", "64k", silence_basename,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            cwd=out_dir,
        )
        _, stderr_s = await proc_silence.communicate()
        stderr_text = stderr_s.decode(errors="replace") if stderr_s else ""
        if proc_silence.returncode != 0:
            logger.warning("ffmpeg silence failed (code=%s): %s", proc_silence.returncode, stderr_text[-1500:])
            # Запасной вариант: тишина из первого сегмента (volume=0, 5 сек) — тот же кодек
            silence_alt = await _create_silence_from_segment(
                ffmpeg_cmd, os.path.join(out_dir, silence_basename), temp_paths[0], pause_seconds, out_dir
            )
            if not silence_alt:
                fallback_path = os.path.join(out_dir, result_basename)
                shutil.copy(temp_paths[0], fallback_path)
                return fallback_path
            silence_basename = os.path.basename(silence_alt)

        list_path = os.path.join(out_dir, list_basename)
        _make_concat_list_file(list_path, temp_paths, silence_basename)
        proc = await asyncio.create_subprocess_exec(
            ffmpeg_cmd, "-y", "-nostdin", "-f", "concat", "-safe", "0", "-i", list_basename,
            "-c:a", "libopus", "-b:a", "64k", result_basename,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            cwd=out_dir,
        )
        _, stderr_c = await proc.communicate()
        stderr_concat = stderr_c.decode(errors="replace") if stderr_c else ""
        if proc.returncode != 0:
            logger.warning("ffmpeg concat failed (code=%s): %s", proc.returncode, stderr_concat[-1500:])
            fallback_path = os.path.join(out_dir, result_basename)
            shutil.copy(temp_paths[0], fallback_path)
            return fallback_path

        return os.path.join(out_dir, result_basename)
    except FileNotFoundError as e:
        logger.warning("ffmpeg not found (%s), returning first segment", e)
        if temp_paths:
            fallback_path = os.path.join(out_dir, f"tts_affirmations_{ts}.ogg")
            shutil.copy(temp_paths[0], fallback_path)
            return fallback_path
        raise RuntimeError("Для озвучки с паузами нужен ffmpeg. Установи: https://ffmpeg.org") from e
    except Exception as e:
        logger.exception("Merge TTS with pauses failed: %s", e)
        if temp_paths:
            fallback_path = os.path.join(out_dir, f"tts_affirmations_{ts}.ogg")
            shutil.copy(temp_paths[0], fallback_path)
            return fallback_path
        raise
    finally:
        for p in temp_paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass
        for name in (f"silence_5s_{ts}.ogg", f"concat_list_{ts}.txt"):
            p = os.path.join(out_dir, name)
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass
