"""Print one resolved runtime config value, for scripts/backup.sh and
scripts/restore.sh to capture into a shell variable.

A dedicated file (rather than a `python -` stdin heredoc) because
python-dotenv's load_dotenv() locates .env by inspecting the calling frame's
file, which fails when the calling code has no real file (e.g. code piped
into `python -` via a heredoc).

Not a secret leak by itself: callers capture this into a variable and must
never echo/log it back out (DATABASE_URL can contain a password).
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import get_database_url, get_sqlite_db_path  # noqa: E402  (import after sys.path setup)


def _database_url_host() -> str:
    """Hostname from DATABASE_URL, e.g. `postgres` for the Compose-managed
    service - not a secret, used by backup.sh/restore.sh to decide whether
    pg_dump/pg_restore must run inside the postgres container (a Compose
    service hostname is not resolvable from the host shell)."""
    return urlsplit(get_database_url() or "").hostname or ""


_FIELDS = {
    "database_url": lambda: get_database_url() or "",
    "sqlite_db_path": get_sqlite_db_path,
    "database_url_host": _database_url_host,
}


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1 or argv[0] not in _FIELDS:
        print(f"usage: runtime_value.py {{{'|'.join(_FIELDS)}}}", file=sys.stderr)
        return 2
    print(_FIELDS[argv[0]]())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
