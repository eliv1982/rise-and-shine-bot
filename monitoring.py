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


def log_delivery_event(event: str, **fields: object) -> None:
    """Scheduled-delivery lifecycle: tick, claimed, completed, failed, skipped."""
    logger.info("metric=subscription_delivery %s", _fmt(event=event, **fields))


def log_rate_limited(user_id: int, used: int, limit: int) -> None:
    logger.info(
        "metric=rate_limited %s",
        _fmt(user_id=user_id, used=used, limit=limit),
    )


def log_image_prompt_llm_fallback(reason: Optional[str] = None) -> None:
    logger.info("metric=image_prompt_llm_fallback %s", _fmt(reason=reason or "unknown"))


def log_smalltalk_unregistered_rejected(user_id: int) -> None:
    logger.info("metric=smalltalk_unregistered_rejected %s", _fmt(user_id=user_id))


def log_smalltalk_rate_limited(user_id: int, used: int, limit: int) -> None:
    logger.info(
        "metric=smalltalk_rate_limited %s",
        _fmt(user_id=user_id, used=used, limit=limit),
    )


def log_voice_cleanup_failed(path: str, error: str) -> None:
    logger.warning(
        "metric=voice_cleanup_failed %s",
        _fmt(path=path, error=error[:200]),
    )


def log_outputs_cleanup_completed(removed: int, skipped: int, errors: int, out_dir: str) -> None:
    logger.info(
        "metric=outputs_cleanup_completed %s",
        _fmt(removed=removed, skipped=skipped, errors=errors, dir=out_dir),
    )


def log_outputs_cleanup_failed(error: str) -> None:
    logger.warning("metric=outputs_cleanup_failed %s", _fmt(error=error[:200]))
