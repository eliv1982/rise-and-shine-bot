"""Unit tests for the pure due-delivery rules in services/delivery_schedule.py.

These pin down the boundary conditions (window edges, backoff/lease edges, and the
schedule_effective_at guard) that the DB-backed scheduler tests exercise only
indirectly; see tests/test_scheduler_delivery.py for the end-to-end contract.
"""
import datetime as dt

from services.delivery_schedule import (
    STATUS_ABANDONED,
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    STATUS_SENT,
    candidate_delivery_dates,
    find_due_deliveries,
    latest_slot,
)

MOSCOW = dt.timezone(dt.timedelta(hours=3))
WINDOW = dt.timedelta(hours=3)
BACKOFF = dt.timedelta(minutes=15)
LEASE = dt.timedelta(minutes=15)


def _at(day, hour, minute):
    return dt.datetime(2030, 1, day, hour, minute, tzinfo=MOSCOW)


def _sub(sub_id, hour=8, minute=0, effective_at=None):
    return {"id": sub_id, "hour": hour, "minute": minute, "schedule_effective_at": effective_at}


# ---------------------------------------------------------------------------
# latest_slot
# ---------------------------------------------------------------------------


def test_latest_slot_exact_minute_is_due():
    day, scheduled = latest_slot(8, 0, _at(1, 8, 0), window=WINDOW)
    assert day == dt.date(2030, 1, 1)
    assert scheduled == _at(1, 8, 0)


def test_latest_slot_future_slot_is_not_due():
    assert latest_slot(8, 0, _at(1, 7, 59), window=WINDOW) is None


def test_latest_slot_just_inside_window_is_due():
    assert latest_slot(8, 0, _at(1, 10, 59), window=WINDOW) is not None


def test_latest_slot_at_window_edge_is_not_due():
    # now - scheduled_at == window exactly: the check is strict ("< window").
    assert latest_slot(8, 0, _at(1, 11, 0), window=WINDOW) is None


def test_latest_slot_falls_back_to_yesterday_when_todays_has_not_arrived():
    # It's 02:00 today; today's 08:00 slot is in the future, so the due slot (if any)
    # is yesterday's 08:00 - already 18h old here, well past a 3h window.
    assert latest_slot(8, 0, _at(2, 2, 0), window=WINDOW) is None


def test_latest_slot_requires_aware_datetime():
    import pytest

    with pytest.raises(ValueError):
        latest_slot(8, 0, dt.datetime(2030, 1, 1, 8, 0))


# ---------------------------------------------------------------------------
# candidate_delivery_dates
# ---------------------------------------------------------------------------


def test_candidate_delivery_dates_is_today_and_yesterday():
    assert candidate_delivery_dates(_at(15, 8, 0)) == ["2030-01-15", "2030-01-14"]


# ---------------------------------------------------------------------------
# find_due_deliveries: ledger-state gating
# ---------------------------------------------------------------------------


def test_find_due_deliveries_new_subscription_with_no_ledger_row_is_due():
    now = _at(1, 8, 0)
    due = find_due_deliveries([_sub(1)], [], now, window=WINDOW, retry_backoff=BACKOFF, lease=LEASE)
    assert len(due) == 1
    assert due[0].subscription_id == 1
    assert not due[0].is_retry


def test_find_due_deliveries_sent_delivery_is_not_due_again():
    now = _at(1, 8, 0)
    ledger = [{"subscription_id": 1, "delivery_date": "2030-01-01", "status": STATUS_SENT, "attempts": 1}]
    due = find_due_deliveries([_sub(1)], ledger, now, window=WINDOW, retry_backoff=BACKOFF, lease=LEASE)
    assert due == []


def test_find_due_deliveries_failed_within_backoff_is_not_due():
    now = _at(1, 8, 10)  # 10 minutes after a failure recorded at 08:00
    ledger = [
        {
            "subscription_id": 1,
            "delivery_date": "2030-01-01",
            "status": STATUS_FAILED,
            "attempts": 1,
            "updated_at": _at(1, 8, 0).isoformat(),
        }
    ]
    due = find_due_deliveries([_sub(1)], ledger, now, window=WINDOW, retry_backoff=BACKOFF, lease=LEASE)
    assert due == []


def test_find_due_deliveries_failed_past_backoff_is_due_for_retry():
    now = _at(1, 8, 16)
    ledger = [
        {
            "subscription_id": 1,
            "delivery_date": "2030-01-01",
            "status": STATUS_FAILED,
            "attempts": 1,
            "updated_at": _at(1, 8, 0).isoformat(),
        }
    ]
    due = find_due_deliveries(
        [_sub(1)], ledger, now, window=WINDOW, max_attempts=3, retry_backoff=BACKOFF, lease=LEASE
    )
    assert len(due) == 1
    assert due[0].is_retry


def test_find_due_deliveries_failed_at_max_attempts_is_never_retried():
    now = _at(1, 12, 0)
    ledger = [
        {
            "subscription_id": 1,
            "delivery_date": "2030-01-01",
            "status": STATUS_FAILED,
            "attempts": 3,
            "updated_at": _at(1, 8, 0).isoformat(),
        }
    ]
    due = find_due_deliveries(
        [_sub(1)], ledger, now, window=WINDOW, max_attempts=3, retry_backoff=BACKOFF, lease=LEASE
    )
    assert due == []


def test_find_due_deliveries_abandoned_is_never_retried():
    now = _at(1, 12, 0)
    ledger = [
        {
            "subscription_id": 1,
            "delivery_date": "2030-01-01",
            "status": STATUS_ABANDONED,
            "attempts": 1,
            "updated_at": _at(1, 8, 0).isoformat(),
        }
    ]
    due = find_due_deliveries([_sub(1)], ledger, now, window=WINDOW, retry_backoff=BACKOFF, lease=LEASE)
    assert due == []


def test_find_due_deliveries_in_progress_within_lease_is_not_reclaimed():
    now = _at(1, 8, 10)
    ledger = [
        {
            "subscription_id": 1,
            "delivery_date": "2030-01-01",
            "status": STATUS_IN_PROGRESS,
            "attempts": 1,
            "claimed_at": _at(1, 8, 0).isoformat(),
        }
    ]
    due = find_due_deliveries([_sub(1)], ledger, now, window=WINDOW, retry_backoff=BACKOFF, lease=LEASE)
    assert due == []


def test_find_due_deliveries_in_progress_past_lease_is_reclaimed():
    now = _at(1, 8, 16)
    ledger = [
        {
            "subscription_id": 1,
            "delivery_date": "2030-01-01",
            "status": STATUS_IN_PROGRESS,
            "attempts": 1,
            "claimed_at": _at(1, 8, 0).isoformat(),
        }
    ]
    due = find_due_deliveries(
        [_sub(1)], ledger, now, window=WINDOW, max_attempts=3, retry_backoff=BACKOFF, lease=LEASE
    )
    assert len(due) == 1
    assert due[0].is_retry


# ---------------------------------------------------------------------------
# find_due_deliveries: schedule_effective_at guard
# ---------------------------------------------------------------------------


def test_find_due_deliveries_slot_before_effective_at_is_skipped():
    # Subscription's time was (re)set at 08:05; today's 08:00 slot predates that and
    # must not be treated as a missed delivery to catch up.
    now = _at(1, 8, 30)
    sub = _sub(1, effective_at=_at(1, 8, 5).isoformat())
    due = find_due_deliveries([sub], [], now, window=WINDOW, retry_backoff=BACKOFF, lease=LEASE)
    assert due == []


def test_find_due_deliveries_slot_after_effective_at_is_due():
    now = _at(1, 8, 30)
    sub = _sub(1, effective_at=_at(1, 7, 0).isoformat())
    due = find_due_deliveries([sub], [], now, window=WINDOW, retry_backoff=BACKOFF, lease=LEASE)
    assert len(due) == 1


def test_find_due_deliveries_missing_effective_at_does_not_block():
    now = _at(1, 8, 0)
    due = find_due_deliveries([_sub(1, effective_at=None)], [], now, window=WINDOW, retry_backoff=BACKOFF, lease=LEASE)
    assert len(due) == 1


# ---------------------------------------------------------------------------
# find_due_deliveries: multiple subscriptions
# ---------------------------------------------------------------------------


def test_find_due_deliveries_orders_by_scheduled_time_then_subscription_id():
    now = _at(1, 9, 0)
    subs = [_sub(3, hour=8, minute=30), _sub(1, hour=8, minute=0), _sub(2, hour=8, minute=0)]
    due = find_due_deliveries(subs, [], now, window=WINDOW, retry_backoff=BACKOFF, lease=LEASE)
    assert [d.subscription_id for d in due] == [1, 2, 3]


def test_find_due_deliveries_mixes_due_and_not_due_subscriptions():
    now = _at(1, 8, 0)
    subs = [_sub(1, hour=8, minute=0), _sub(2, hour=20, minute=0)]
    due = find_due_deliveries(subs, [], now, window=WINDOW, retry_backoff=BACKOFF, lease=LEASE)
    assert [d.subscription_id for d in due] == [1]
