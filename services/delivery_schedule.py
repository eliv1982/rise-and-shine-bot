"""Rules that decide which scheduled subscription deliveries are due (pure, no I/O).

A *logical delivery* is "the daily ritual of one subscription for one calendar day".
It is identified by ``(subscription_id, delivery_date)`` where ``delivery_date`` is the
date of the scheduled slot in the scheduler's timezone. The identity does not depend
on the process, on the minute the work happens to run, on randomness or on retries.

The durable ledger (``subscription_deliveries``) records what happened to each logical
delivery; this module decides, from the subscriptions plus that ledger, what should be
attempted right now. The database performs the authoritative atomic claim with the
same thresholds, so the checks here only avoid pointless claim attempts.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Iterable, Optional

# How long after its scheduled time a missed delivery may still be sent. Must stay
# below 24h so at most one slot per subscription is ever eligible (no burst of
# obsolete daily rituals after a long outage).
CATCHUP_WINDOW = dt.timedelta(hours=3)
# Total attempts (first try included) per logical delivery.
MAX_DELIVERY_ATTEMPTS = 3
# Minimum pause after a failed attempt before the next one (no tight retry loop).
RETRY_BACKOFF = dt.timedelta(minutes=15)
# An in-progress claim older than this is treated as abandoned by a dead process.
# Must exceed the longest attempt (see scheduler.ATTEMPT_TIMEOUT_SECONDS).
CLAIM_LEASE = dt.timedelta(minutes=15)
# Lateness beyond one tick interval marks a delivery as a catch-up (logging only).
CATCHUP_LOG_THRESHOLD = dt.timedelta(minutes=1)

STATUS_IN_PROGRESS = "in_progress"  # claimed by an attempt that has not finished
STATUS_SENT = "sent"  # confirmed delivered; terminal
STATUS_FAILED = "failed"  # attempt failed; will be retried after the backoff
STATUS_ABANDONED = "abandoned"  # permanent error or attempts exhausted; terminal


def parse_ts(value: Any) -> Optional[dt.datetime]:
    """Parse an ISO timestamp from the DB into an aware datetime (naive means UTC)."""
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def candidate_delivery_dates(now: dt.datetime) -> list[str]:
    """Dates whose slot can still be inside the catch-up window: today and yesterday."""
    today = now.date()
    return [today.isoformat(), (today - dt.timedelta(days=1)).isoformat()]


def latest_slot(
    hour: int,
    minute: int,
    now: dt.datetime,
    window: dt.timedelta = CATCHUP_WINDOW,
) -> Optional[tuple[dt.date, dt.datetime]]:
    """The subscription's slot that is due at ``now``: ``(delivery_date, scheduled_at)``.

    A slot is due from its scheduled minute until ``window`` later. ``now`` must be
    timezone-aware; slots are built in its timezone. Returns None when the most recent
    slot is still in the future or is already too old.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    for days_back in (0, 1):
        day = now.date() - dt.timedelta(days=days_back)
        scheduled_at = dt.datetime.combine(day, dt.time(hour, minute), tzinfo=now.tzinfo)
        if scheduled_at <= now:
            return (day, scheduled_at) if now - scheduled_at < window else None
    return None


@dataclass(frozen=True)
class DueDelivery:
    subscription: dict
    delivery_date: dt.date
    scheduled_at: dt.datetime
    ledger_row: Optional[dict]

    @property
    def subscription_id(self) -> int:
        return self.subscription["id"]

    @property
    def is_retry(self) -> bool:
        return self.ledger_row is not None


def _ledger_allows_attempt(
    row: Optional[dict],
    now: dt.datetime,
    max_attempts: int,
    retry_backoff: dt.timedelta,
    lease: dt.timedelta,
) -> bool:
    if row is None:
        return True
    if int(row.get("attempts") or 0) >= max_attempts:
        return False
    status = row.get("status")
    if status == STATUS_FAILED:
        failed_at = parse_ts(row.get("updated_at"))
        return failed_at is None or now >= failed_at + retry_backoff
    if status == STATUS_IN_PROGRESS:
        claimed_at = parse_ts(row.get("claimed_at"))
        return claimed_at is None or now >= claimed_at + lease
    return False  # sent / abandoned / unknown: never attempted again


def find_due_deliveries(
    subscriptions: Iterable[dict],
    ledger_rows: Iterable[dict],
    now: dt.datetime,
    *,
    window: dt.timedelta = CATCHUP_WINDOW,
    max_attempts: int = MAX_DELIVERY_ATTEMPTS,
    retry_backoff: dt.timedelta = RETRY_BACKOFF,
    lease: dt.timedelta = CLAIM_LEASE,
) -> list[DueDelivery]:
    """Logical deliveries that should be attempted at ``now``, oldest slot first.

    At most one per subscription: the window is shorter than a day, so a subscription
    never has more than one eligible slot.
    """
    ledger = {(row["subscription_id"], row["delivery_date"]): row for row in ledger_rows}
    due: list[DueDelivery] = []
    for sub in subscriptions:
        slot = latest_slot(int(sub["hour"]), int(sub["minute"]), now, window)
        if slot is None:
            continue
        delivery_date, scheduled_at = slot
        # A slot that passed before the schedule was (re)set is not owed: creating or
        # re-timing a subscription must not trigger an immediate "missed" delivery.
        effective_at = parse_ts(sub.get("schedule_effective_at"))
        if effective_at is not None and scheduled_at < effective_at:
            continue
        row = ledger.get((sub["id"], delivery_date.isoformat()))
        if not _ledger_allows_attempt(row, now, max_attempts, retry_backoff, lease):
            continue
        due.append(DueDelivery(sub, delivery_date, scheduled_at, row))
    due.sort(key=lambda item: (item.scheduled_at, item.subscription_id))
    return due
