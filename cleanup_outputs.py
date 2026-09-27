#!/usr/bin/env python3
"""
Удаление устаревших файлов в каталоге outputs (PNG, meta JSON, голосовые для STT, TTS).
По умолчанию возраст берётся из OUTPUT_MAX_AGE_DAYS (.env).

``cleanup_old_outputs`` is the reusable core: it never lets one bad entry abort the sweep
(each file's removal is isolated), and it never descends into subdirectories or follows a
symlink to a target outside ``out_dir`` (``os.listdir`` only lists direct children; removing
a symlink entry only unlinks the link itself, never the file it points to). It is used both
by this CLI and by the bot's own startup/periodic cleanup (see ``scheduler.py``).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time

# Загрузить .env до импорта config
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_CLEANUP_EXTENSIONS = (".png", ".json", ".ogg", ".mp3", ".wav")


def cleanup_old_outputs(out_dir: str, days: int, *, dry_run: bool = False) -> dict:
    """Remove files older than ``days`` under ``out_dir``. Returns removed/skipped/errors counts.

    A failure removing one entry is logged and counted, never raised - one locked or
    permission-denied file must not stop the rest of the sweep or crash a caller.
    """
    result = {"removed": 0, "skipped_non_matching": 0, "errors": 0}
    if days <= 0:
        return result
    if not os.path.isdir(out_dir):
        return result

    cutoff = time.time() - days * 86400
    try:
        names = os.listdir(out_dir)
    except OSError as exc:
        logger.warning("outputs cleanup: failed to list %s: %s", out_dir, exc)
        result["errors"] += 1
        return result

    for name in names:
        path = os.path.join(out_dir, name)
        try:
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in _CLEANUP_EXTENSIONS:
                result["skipped_non_matching"] += 1
                continue
            mtime = os.path.getmtime(path)
            if mtime > cutoff:
                continue
            if dry_run:
                print(f"would remove: {path}")
            else:
                os.remove(path)
                print(f"removed: {path}")
            result["removed"] += 1
        except OSError as exc:
            result["errors"] += 1
            logger.warning("outputs cleanup: failed to remove %s: %s", path, exc)

    return result


async def run_outputs_cleanup(days: int | None = None) -> dict:
    """Async, runtime-facing entry point: resolves settings, runs the sweep off the event
    loop thread, and logs a structured summary. Used at bot startup and by the periodic job.
    """
    import asyncio

    from config import get_outputs_dir, get_settings
    from monitoring import log_outputs_cleanup_completed, log_outputs_cleanup_failed

    try:
        settings = get_settings()
        resolved_days = days if days is not None else settings.output_max_age_days
        out_dir = get_outputs_dir()
        result = await asyncio.to_thread(cleanup_old_outputs, out_dir, resolved_days)
    except Exception as exc:  # pragma: no cover - defensive: must never crash the bot/job
        logger.exception("outputs cleanup failed unexpectedly: %s", exc)
        log_outputs_cleanup_failed(str(exc))
        return {"removed": 0, "skipped_non_matching": 0, "errors": 1}

    log_outputs_cleanup_completed(result["removed"], result["skipped_non_matching"], result["errors"], out_dir)
    if result["errors"]:
        log_outputs_cleanup_failed(f"{result['errors']} file(s) could not be removed under {out_dir}")
    return result


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

    from config import get_outputs_dir, get_settings

    parser = argparse.ArgumentParser(description="Cleanup old files under bot outputs directory.")
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Delete files older than this many days (default: OUTPUT_MAX_AGE_DAYS from env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list what would be deleted",
    )
    args = parser.parse_args()

    settings = get_settings()
    days = args.days if args.days is not None else settings.output_max_age_days
    if days <= 0:
        print("Nothing to do: days <= 0.")
        return 0

    out_dir = get_outputs_dir()
    if not os.path.isdir(out_dir):
        print(f"Outputs directory does not exist: {out_dir}")
        return 0

    result = cleanup_old_outputs(out_dir, days, dry_run=args.dry_run)
    print(
        f"Done. removed={result['removed']} skipped_non_matching={result['skipped_non_matching']} "
        f"errors={result['errors']} days>={days} dir={out_dir}"
    )
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
