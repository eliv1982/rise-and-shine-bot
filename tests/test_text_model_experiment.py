import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json

import pytest

from scripts import run_text_model_experiment as experiment


def freeze_experiment_time(monkeypatch, instant):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz)

    monkeypatch.setattr(experiment, "datetime", FrozenDateTime)


@pytest.fixture
def verified_pricing_time(monkeypatch):
    # Only these mocked execution tests run on the verified pricing date.
    freeze_experiment_time(monkeypatch, datetime(2026, 11, 6, 12, tzinfo=timezone.utc))


def test_authorized_plan_has_matched_pairs_and_exact_counts():
    plan = experiment.build_plan()
    assert plan == experiment.build_plan()
    assert plan["counts"] == {
        "gpt-6-luna/none": 6, "gpt-6.1-terra/none": 6,
        "gpt-6-luna/low": 2, "gpt-6.1-terra/low": 2,
    }
    assert plan["low_case_ids"] == ["ru_memory_diversity", "ru_untrusted_theme"]
    for left, right in zip(plan["requests"][::2], plan["requests"][1::2]):
        assert left["input_sha256"] == right["input_sha256"]
        assert left["payload"]["input"] == right["payload"]["input"]
        assert left["payload"]["store"] is False
        assert left["payload"]["service_tier"] == "default"
        assert "tools" not in left["payload"]
        if left["payload"]["reasoning"]["effort"] == "low":
            assert left["payload"]["max_output_tokens"] == 4096
            assert "temperature" not in left["payload"]


@pytest.mark.parametrize("count", [-1, True, None, 16_385])
def test_invalid_or_long_inputs_fail_before_spend(count):
    with pytest.raises(experiment.StopExperiment):
        experiment.reservation(experiment.build_plan()["requests"][0], count)


def test_even_maximum_accepted_inputs_and_outputs_fit_one_dollar():
    total = sum(experiment.reservation(r, 16_384) for r in experiment.build_plan()["requests"])
    assert total == Decimal("0.242176")
    assert total < experiment.BUDGET


def test_missing_write_usage_is_unknown_cost_and_not_zero():
    request = experiment.build_plan()["requests"][0]
    exact, upper = experiment.usage_cost({"usage": {
        "input_tokens": 100, "output_tokens": 200, "total_tokens": 300,
        "input_tokens_details": {"cached_tokens": 0},
    }}, request, 100)
    assert exact is None
    assert upper > 0


def test_blind_examples_hide_identity_and_metrics(tmp_path):
    result = dict(experiment.build_plan()["requests"][0],
                  raw_text='["GPT-6 Luna", "OpenAI", "Terra", "gpt-6.1-terra"]',
                  usage={"input_tokens": 100}, latency_seconds=1, reasoning_tokens=0)
    experiment.blind_materials([result], tmp_path)
    blind = (tmp_path / "blind-review.md").read_text(encoding="utf-8").lower()
    assert not any(name in blind for name in ("gpt", "luna", "terra", "openai", "latency", "usage"))
    key = json.loads((tmp_path / "blind-key.json").read_text(encoding="utf-8"))
    assert key["S01"]["model"] == result["payload"]["model"]


class FakeSession:
    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    def request(self, *args, **kwargs):
        pytest.fail("Experiment tests must never send real HTTP requests")


def fake_preflight(plan):
    return {"status": "passed", "input_counts": {r["request_id"]: 100 for r in plan["requests"]}}


def response(request, **changes):
    english = request["inputs"].get("language", "ru") == "en"
    card = {
        "focus": "Gentle growth" if english else "Бережный рост",
        "affirmations": ["I value my experience", "My voice matters", "I choose clarity", "My pace deserves respect"] if english else [
            "Я ценю свой опыт", "Мой голос важен", "Я выбираю ясность", "Мой ритм достоин уважения",
        ],
    }
    return {
        "id": "synthetic-response", "model": request["payload"]["model"],
        "service_tier": "default", "status": "completed",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(card)}]}],
        "usage": {"input_tokens": 100, "output_tokens": 200, "total_tokens": 300,
                  "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                  "output_tokens_details": {"reasoning_tokens": 50}},
        **changes,
    }


def setup_transport(monkeypatch, plan, tmp_path, *, fail=False, mismatch=False):
    monkeypatch.setattr(experiment.aiohttp, "ClientSession", FakeSession)
    calls = []

    async def preflight(session, supplied):
        return fake_preflight(supplied)

    async def api(session, method, path, *, payload=None):
        assert isinstance(session, FakeSession)
        assert method == "POST"
        assert path == "/responses"
        report = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
        # The hold and pending ID are durable before entering the paid transport.
        assert Decimal(report["reserved_usd"]) > 0
        assert report["pending_request_id"] == plan["requests"][len(calls)]["request_id"]
        calls.append(payload)
        if fail:
            raise asyncio.TimeoutError()
        return response(plan["requests"][len(calls) - 1], **({"service_tier": "priority"} if mismatch else {}))

    monkeypatch.setattr(experiment, "preflight", preflight)
    monkeypatch.setattr(experiment, "api_json", api)
    return calls


@pytest.mark.parametrize("fail,mismatch", [(True, False), (False, True)])
def test_uncertain_charge_stops_without_retry_and_retains_hold(
    monkeypatch, tmp_path, verified_pricing_time, fail, mismatch,
):
    plan = experiment.build_plan()
    calls = setup_transport(monkeypatch, plan, tmp_path, fail=fail, mismatch=mismatch)
    report = asyncio.run(experiment.execute(plan, api_key="must-not-leak", output=tmp_path, live=True))
    assert len(calls) == report["paid_requests_submitted"] == 1
    assert report["status"] == "stopped"
    assert report["stop_reason"] == ("TimeoutError" if fail else "unexpected_model_or_tier")
    assert Decimal(report["reserved_usd"]) > 0
    assert report["results"][0]["latency_seconds"] >= 0
    assert "must-not-leak" not in (tmp_path / "results.json").read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        asyncio.run(experiment.execute(plan, api_key="must-not-leak", output=tmp_path, live=True))
    assert len(calls) == 1


def test_completed_run_preserves_usage_reasoning_and_blind_key(monkeypatch, tmp_path, verified_pricing_time):
    plan = experiment.build_plan()
    calls = setup_transport(monkeypatch, plan, tmp_path)
    report = asyncio.run(experiment.execute(plan, api_key="must-not-leak", output=tmp_path, live=True))
    assert len(calls) == 16
    assert report["status"] == "completed"
    assert all(r["reasoning_tokens"] == 50 and r["usage"]["total_tokens"] == 300 for r in report["results"])
    assert len(json.loads((tmp_path / "blind-key.json").read_text(encoding="utf-8"))) == 16
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_reasoning_tokens"] == 800
    assert summary["request_count"] == summary["valid_four_strings"] == 16
    assert sum(group["requests"] for group in summary["groups"]) == 16
    assert (tmp_path / "metrics.csv").exists()


@pytest.mark.parametrize("instant", [
    "2026-11-06T21:00:00+00:00",  # Already November 7 in the guard's UTC+3 timezone.
    "2026-11-17T12:00:00+00:00",
], ids=["next_day_in_moscow", "stale_later_date"])
def test_stale_pricing_blocks_live_before_transport(monkeypatch, tmp_path, instant):
    freeze_experiment_time(monkeypatch, datetime.fromisoformat(instant))

    def unexpected_transport(*args, **kwargs):
        pytest.fail("Stale pricing must stop before any provider access")

    monkeypatch.setattr(experiment.aiohttp, "ClientSession", unexpected_transport)
    monkeypatch.setattr(experiment, "preflight", unexpected_transport)
    monkeypatch.setattr(experiment, "api_json", unexpected_transport)

    report = asyncio.run(experiment.execute(
        experiment.build_plan(), api_key="must-not-leak", output=tmp_path, live=True,
    ))

    assert report["status"] == "stopped"
    assert report["stop_reason"] == "reverify_current_prices_before_live"
    assert report["paid_requests_submitted"] == 0
    assert Decimal(report["reserved_usd"]) == 0
    assert report["results"] == []
    assert json.loads((tmp_path / "results.json").read_text(encoding="utf-8")) == report


def test_preflight_cannot_generate_and_overbudget_plan_is_rejected(monkeypatch):
    plan = experiment.build_plan()
    paths = []

    async def api(session, method, path, *, payload=None):
        paths.append(path)
        assert path != "/responses"
        if path.startswith("/models/"):
            return {"id": path.rsplit("/", 1)[-1]}
        return {"object": "response.input_tokens", "input_tokens": 100}

    monkeypatch.setattr(experiment, "api_json", api)
    monkeypatch.setattr(experiment, "BUDGET", Decimal("0.001"))
    with pytest.raises(experiment.StopExperiment, match="plan_exceeds_one_dollar"):
        asyncio.run(experiment.preflight(None, plan))
    assert len(paths) == 18
