import json
import logging
from typing import List, Optional

import aiohttp

from config import get_settings

logger = logging.getLogger(__name__)


def _build_default_theme(sphere: str, subsphere: Optional[str], language: str) -> str:
    """
    Формирует мягкую тему по умолчанию на основе сферы и подсферы.
    """
    sphere_key = sphere.lower()
    subsphere_key = (subsphere or "").lower()

    if language == "en":
        base = {
            "career": "confidence and growth in professional life",
            "relationships": "warm, trusting and respectful communication",
            "health": "gentle support for body and mind",
            "money": "calm and responsible attitude to money and abundance",
            "spirituality": "inner peace, trust in life and spiritual growth",
            "self_realization": "self-realization, creativity and expressing your talents",
            "inner_peace": "inner peace, calmness and emotional balance",
        }.get(sphere_key, "inner harmony and balance")

        if sphere_key == "relationships":
            spec = {
                "partner": "romantic relationship and deep mutual trust",
                "colleagues": "respectful collaboration with colleagues",
                "friends": "warm and supportive friendships",
            }.get(subsphere_key)
            if spec:
                base = spec

        return base

    # Русская версия
    base = {
        "career": "уверенность и рост в профессиональной сфере",
        "relationships": "тёплое, доверительное и уважительное общение",
        "health": "бережная забота о теле и психике",
        "money": "спокойное и ответственное отношение к деньгам и изобилию",
        "spirituality": "внутренний покой, доверие жизни и духовный рост",
        "self_realization": "самореализация, творчество и раскрытие талантов",
        "inner_peace": "внутренний покой, спокойствие и эмоциональный баланс",
    }.get(sphere_key, "внутренняя гармония и баланс")

    if sphere_key == "relationships":
        spec = {
            "partner": "романтичные отношения и глубокое взаимное доверие",
            "colleagues": "уважительное сотрудничество с коллегами",
            "friends": "тёплая и поддерживающая дружба",
        }.get(subsphere_key)
        if spec:
            base = spec

    return base


def _build_prompt(
    sphere: str,
    subsphere: Optional[str],
    language: str,
    user_text: Optional[str],
    gender_hint: Optional[str] = None,
    gender: Optional[str] = None,
) -> str:
    """
    Формирует промпт к YandexGPT с инструкцией вернуть JSON-массив аффирмаций.
    gender: "male" | "female" из БД — используется для грамматики рода (приоритет над gender_hint).
    """
    theme = user_text or _build_default_theme(sphere, subsphere, language)
    sphere_desc = f"sphere: {sphere}"
    if subsphere:
        sphere_desc += f", subsphere: {subsphere}"

    gender_part_en = ""
    gender_part_ru = ""
    if gender_hint:
        gender_part_en = f"For {gender_hint}, "
        gender_part_ru = f"{gender_hint}, "

    if language == "en":
        return (
            "You are a gentle, soulful affirmations writer.\n"
            "Task:\n"
            f"- {gender_part_en}write 3–5 short, heartfelt, non-cliché affirmations.\n"
            "- Language: English.\n"
            f"- Context: {sphere_desc}.\n"
            f"- Theme/hint from user: {theme}.\n"
            "- Focus on authentic emotional resonance, not generic templates.\n"
            "- They should be in the first person (I ...), present tense, and empowering but calm.\n"
            "- Avoid mentioning that you are an AI.\n"
            "Output format:\n"
            "- JSON array of strings only, e.g. [\"I ...\", \"I ...\"].\n"
            "- No comments or explanations, only valid JSON."
        )

    # Род в русском: явно по полю gender из БД ("male" / "female")
    gender_grammar = ""
    is_female = gender == "female" if gender else (gender_hint and ("женщин" in (gender_hint or "").lower() or "woman" in (gender_hint or "").lower()))
    if gender or gender_hint:
        if is_female:
            gender_grammar = (
                " КРИТИЧЕСКИ ВАЖНО: адресат — женщина. Все прилагательные, причастия и глаголы в женском роде: "
                "Я открыта, готова, способна, я создаю, я принимаю (окончания -а, -я и т.д.). "
                "Никогда не используй мужской род (Я открыт, готов — нельзя).\n"
            )
        else:
            gender_grammar = (
                " КРИТИЧЕСКИ ВАЖНО: адресат — мужчина. Все в мужском роде: Я открыт, готов, способен (окончания -а у кратких только для мужского).\n"
            )

    return (
        "Ты — чуткий автор аффирмаций с живым, небанальным стилем.\n"
        "Задача:\n"
        f"- {gender_part_ru}напиши 3–5 коротких, душевных аффирмаций без штампов и клише.\n"
        f"-{gender_grammar}"
        "- Язык: русский.\n"
        f"- Контекст: {sphere_desc}.\n"
        f"- Тема/подсказка от пользователя: {theme}.\n"
        "- Аффирмации в форме от первого лица (\"Я ...\"), в настоящем времени, мягко поддерживающие.\n"
        "- Не упоминай, что ты ИИ.\n"
        "Формат вывода:\n"
        "- Только JSON-массив строк, например: [\"Я ...\", \"Я ...\"].\n"
        "- Без комментариев и пояснений, только валидный JSON."
    )


async def generate_affirmations(
    sphere: str,
    language: str = "ru",
    user_text: Optional[str] = None,
    subsphere: Optional[str] = None,
    gender_hint: Optional[str] = None,
    gender: Optional[str] = None,
) -> List[str]:
    """
    Асинхронно вызывает YandexGPT и возвращает список аффирмаций.
    gender: "male" | "female" из БД — для согласования рода в русском.
    """
    settings = get_settings()

    model_uri = f"gpt://{settings.yandex_folder_id}/yandexgpt-lite/latest"
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    prompt_text = _build_prompt(
        sphere=sphere,
        subsphere=subsphere,
        language=language,
        user_text=user_text,
        gender_hint=gender_hint,
        gender=gender,
    )

    # Используем поле modelUri и completionOptions согласно актуальному API.
    payload = {
        "modelUri": model_uri,
        "completionOptions": {
            "maxTokens": 512,
            "temperature": 0.7,
        },
        "messages": [
            {
                "role": "system",
                "text": "You are a helpful, careful assistant that follows the format instructions exactly.",
            },
            {
                "role": "user",
                "text": prompt_text,
            },
        ],
    }

    headers = {
        "Authorization": f"Api-Key {settings.yandex_api_key}",
        "x-folder-id": settings.yandex_folder_id,
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=60) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error("YandexGPT error: status=%s, body=%s", resp.status, text)
                    raise RuntimeError(f"YandexGPT request failed with status {resp.status}")
                data = await resp.json()
    except Exception as exc:
        logger.exception("Error calling YandexGPT: %s", exc)
        raise RuntimeError(f"Error calling YandexGPT: {exc}") from exc

    try:
        result = data["result"]["alternatives"][0]["message"]["text"]
    except Exception as exc:
        logger.exception("Unexpected YandexGPT response format: %s", exc)
        raise RuntimeError("Unexpected YandexGPT response format") from exc

    # Некоторые версии модели любят оборачивать JSON в ```...``` – аккуратно счищаем обёртку.
    cleaned = result.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
            affirmations = parsed
        else:
            logger.warning("YandexGPT returned non-list JSON; using raw text.")
            affirmations = [cleaned]
    except json.JSONDecodeError:
        logger.warning("Failed to parse YandexGPT output as JSON; returning raw text.")
        affirmations = [cleaned]

    return affirmations


async def generate_smalltalk_reply(user_text: str, language: str = "ru") -> str:
    """
    Генерирует короткий ответ small talk.
    """
    settings = get_settings()

    model_uri = f"gpt://{settings.yandex_folder_id}/yandexgpt-lite/latest"
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    if language == "en":
        prompt = (
            "You are a caring friend and a bot for affirmations.\n"
            f"User message: \"{user_text}\"\n"
            "Reply briefly and warmly, in English, as a supportive friend.\n"
            "Gently remind that you are a bot for affirmations and can generate a new one on request.\n"
            "Keep the answer short."
        )
    else:
        prompt = (
            "Ты — заботливый друг и бот для аффирмаций.\n"
            f"Сообщение пользователя: «{user_text}».\n"
            "Ответь коротко и по-доброму, на русском, как поддерживающий друг.\n"
            "Мягко напомни, что ты бот для аффирмаций и можешь сгенерировать новую по запросу.\n"
            "Ответ должен быть коротким."
        )

    payload = {
        "modelUri": model_uri,
        "completionOptions": {
            "maxTokens": 200,
            "temperature": 0.7,
        },
        "messages": [
            {
                "role": "system",
                "text": "You are a helpful, friendly assistant.",
            },
            {
                "role": "user",
                "text": prompt,
            },
        ],
    }

    headers = {
        "Authorization": f"Api-Key {settings.yandex_api_key}",
        "x-folder-id": settings.yandex_folder_id,
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload, timeout=60) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error("YandexGPT smalltalk error: status=%s, body=%s", resp.status, text)
                raise RuntimeError(f"YandexGPT smalltalk failed with status {resp.status}")
            data = await resp.json()

    try:
        result = data["result"]["alternatives"][0]["message"]["text"]
    except Exception as exc:
        logger.exception("Unexpected YandexGPT smalltalk response format: %s", exc)
        raise RuntimeError("Unexpected YandexGPT smalltalk response format") from exc

    return result.strip()

