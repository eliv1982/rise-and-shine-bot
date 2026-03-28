#!/usr/bin/env python3
"""
Удаление устаревших файлов в каталоге outputs (PNG, meta JSON, голосовые для STT, TTS).
По умолчанию возраст берётся из OUTPUT_MAX_AGE_DAYS (.env).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

# Загрузить .env до импорта config
from dotenv import load_dotenv

load_dotenv()


def main() -> int:
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

    cutoff = time.time() - days * 86400
    removed = 0
    skipped = 0

    for name in os.listdir(out_dir):
        path = os.path.join(out_dir, name)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext not in (".png", ".json", ".ogg", ".mp3", ".wav"):
            skipped += 1
            continue
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if mtime > cutoff:
            continue
        if args.dry_run:
            print(f"would remove: {path}")
        else:
            try:
                os.remove(path)
                print(f"removed: {path}")
            except OSError as e:
                print(f"error removing {path}: {e}", file=sys.stderr)
                return 1
        removed += 1

    print(f"Done. removed={removed} skipped_non_matching={skipped} days>={days} dir={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
