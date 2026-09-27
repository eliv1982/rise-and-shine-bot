"""Docker HEALTHCHECK for the bot container.

Not an HTTP endpoint (this is a polling bot, not a web service) - just checks
that scheduler.py's per-tick heartbeat file (see config.get_heartbeat_path)
was written recently. APScheduler's daily_affirmations job runs every minute,
so a heartbeat older than MAX_AGE_SECONDS means the event loop or the
scheduler is wedged, even though the process itself is still running (which
alone wouldn't be caught by Docker's container-exit-based restart).

Exit 0 = healthy, exit 1 = unhealthy, matching Docker's HEALTHCHECK contract.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 2.5x the 60s tick interval: tolerates one slow/coalesced tick without flapping.
MAX_AGE_SECONDS = 150


def check(heartbeat_path: str, *, max_age_seconds: int = MAX_AGE_SECONDS, now: float | None = None) -> bool:
    path = Path(heartbeat_path)
    if not path.is_file():
        return False
    age = (now if now is not None else time.time()) - path.stat().st_mtime
    return age <= max_age_seconds


def main(argv: list[str] | None = None) -> int:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from config import get_heartbeat_path

    heartbeat_path = get_heartbeat_path()
    if check(heartbeat_path):
        return 0
    print(f"[healthcheck] heartbeat missing or stale: {heartbeat_path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
