"""Deploy preflight: validate required runtime configuration before scripts/deploy.sh
replaces the running container.

Read-only. Never contacts Telegram/OpenAI/Postgres - only checks that the
configuration that will be loaded at startup is complete and internally
consistent. Reuses config.get_settings() (which loads .env exactly the way
the app does at startup) as the single source of truth for which env vars
are required, instead of duplicating that list here.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from config import get_settings  # importing triggers config.py's own load_dotenv()

    try:
        get_settings()
    except RuntimeError as exc:
        print(f"[preflight] required configuration is missing: {exc}", file=sys.stderr)
        return 1

    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import check_runtime_config

    return check_runtime_config.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
