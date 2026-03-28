"""
Структурированные события для логов (удобно grep / внешний сборщик).
Формат: metric=NAME key=value ...
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _fmt(**kwargs: object) -> str:
    parts = []
    for k, v in kwargs.items():
        if v is None:
            continue
        s = str(v).replace("\n", " ").replace("\r", " ")[:500]
        parts.append(f"{k}={s!r}")
    return " ".join(parts)


def log_generation_ok(user_id: int, source: str, prompt_source: str) -> None:
    logger.info(
        "metric=generation_ok %s",
        _fmt(user_id=user_id, source=source, prompt_source=prompt_source),
    )


def log_generation_fail(user_id: int, source: str, step: str, error: str) -> None:
    logger.info(
        "metric=generation_fail %s",
        _fmt(user_id=user_id, source=source, step=step, error=error[:200]),
    )


def log_rate_limited(user_id: int, used: int, limit: int) -> None:
    logger.info(
        "metric=rate_limited %s",
        _fmt(user_id=user_id, used=used, limit=limit),
    )


def log_image_prompt_llm_fallback(reason: Optional[str] = None) -> None:
    logger.info("metric=image_prompt_llm_fallback %s", _fmt(reason=reason or "unknown"))
