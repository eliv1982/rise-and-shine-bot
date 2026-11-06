"""One bounded, synthetic Luna/Terra experiment. Offline by default.

No dotenv loading, bot/database imports, retries, tools or production writes.
Responses is used only here so the server can count the exact input before spend.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import secrets
from statistics import median
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import compare_text_models as comparison

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "outputs" / "text-model-experiment-2026-11-06"
BASE_URL = "https://api.openai.com/v1"
BUDGET = Decimal("1.00")
VERIFIED_ON = "2026-11-06"
LOW_CASES = ("ru_memory_diversity", "ru_untrusted_theme")
# Official Standard, short-context USD / million tokens. Count every input at
# the highest input/cache-write rate, even if it was actually discounted.
RATES = {
    "gpt-6-luna": {"input": "0.10", "cached": "0.01", "write": "0.125", "output": "0.50"},
    "gpt-6.1-terra": {"input": "1.00", "cached": "0.05", "write": "1.25", "output": "5.00"},
}
SOURCES = [
    "https://developers.openai.com/api/docs/pricing",
    "https://developers.openai.com/api/docs/models/gpt-6-luna",
    "https://developers.openai.com/api/docs/models/gpt-6.1-terra",
    "https://developers.openai.com/cookbook/articles/per_run_spending_controller_responses_api",
]


class StopExperiment(RuntimeError):
    """Only fixed, credential-free error codes are persisted."""


def money(value: Decimal) -> str:
    return format(value, ".9f")


def save(path: Path, value: dict) -> None:
    """Checkpoint before a paid submission; never discard an uncertain hold."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def build_plan() -> dict:
    cases = json.loads(comparison.FIXTURES.read_text(encoding="utf-8"))
    if len(cases) != 6 or len({c["id"] for c in cases}) != 6:
        raise StopExperiment("unexpected_synthetic_manifest")
    low_cases = [next(c for c in cases if c["id"] == name) for name in LOW_CASES]
    requests = comparison.build_requests(cases, reasoning_effort="none", max_completion_tokens=512)
    requests += comparison.build_requests(low_cases, reasoning_effort="low", max_completion_tokens=4096)
    for index, request in enumerate(requests):
        old = request["payload"]
        payload = {
            "model": old["model"], "input": old["messages"],
            "reasoning": {"effort": old["reasoning_effort"]},
            "max_output_tokens": old["max_completion_tokens"],
            "service_tier": "default", "store": False, "truncation": "disabled",
            "prompt_cache_options": {"ttl": "30m"},
        }
        if "temperature" in old:
            payload["temperature"] = old["temperature"]
        request["payload"] = payload
        request["url"] = BASE_URL + "/responses"
        request["request_id"] = f"request-{index + 1:02d}"
        comparable = {k: v for k, v in payload.items() if k != "model"}
        request["input_sha256"] = hashlib.sha256(
            json.dumps(comparable, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
    return {
        "mode": "offline", "budget_usd": str(BUDGET), "request_count": len(requests),
        "counts": dict(Counter(f"{r['payload']['model']}/{r['payload']['reasoning']['effort']}" for r in requests)),
        "low_case_ids": list(LOW_CASES), "pricing_verified_on": VERIFIED_ON,
        "rates_usd_per_million": RATES, "sources": SOURCES,
        "fixture_sha256": hashlib.sha256(comparison.FIXTURES.read_bytes()).hexdigest(),
        "requests": requests,
    }


def token_count(value) -> int:
    if type(value) is not int or value < 0:
        raise StopExperiment("invalid_token_count")
    return value


def reservation(request: dict, count: int) -> Decimal:
    count = token_count(count)
    # Keeps the run in documented short-context pricing and well below model limits.
    if not 0 < count <= 16_384:
        raise StopExperiment("input_limit_exceeded")
    payload = request["payload"]
    limit = token_count(payload["max_output_tokens"])
    if limit not in (512, 4096):
        raise StopExperiment("unexpected_output_limit")
    rates = RATES[payload["model"]]
    worst_input = max(Decimal(rates[key]) for key in ("input", "cached", "write"))
    return (count * worst_input + limit * Decimal(rates["output"])) / 1_000_000


def usage_cost(data: dict, request: dict, counted: int) -> tuple[Decimal | None, Decimal]:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        raise StopExperiment("missing_usage")
    incoming = token_count(usage.get("input_tokens"))
    outgoing = token_count(usage.get("output_tokens"))
    total = token_count(usage.get("total_tokens"))
    if incoming != counted or total != incoming + outgoing or outgoing > request["payload"]["max_output_tokens"]:
        raise StopExperiment("usage_bounds_mismatch")
    details = usage.get("input_tokens_details") or {}
    cached = token_count(details.get("cached_tokens"))
    written = details.get("cache_write_tokens")
    rates = RATES[request["payload"]["model"]]
    # Missing cache-write accounting must never free a reservation. Retain an
    # upper bound separately from any exact cost reconstructed from usage.
    upper = (incoming * Decimal(rates["write"]) + outgoing * Decimal(rates["output"])) / 1_000_000
    if written is None:
        return None, upper
    written = token_count(written)
    ordinary = incoming - cached - written
    if ordinary < 0:
        raise StopExperiment("invalid_cache_accounting")
    exact = (ordinary * Decimal(rates["input"]) + cached * Decimal(rates["cached"])
             + written * Decimal(rates["write"]) + outgoing * Decimal(rates["output"])) / 1_000_000
    return exact, upper


async def api_json(session, method: str, path: str, *, payload=None) -> dict:
    # No redirects: never send credentials to another host. No retries, even 429.
    async with session.request(method, BASE_URL + path, json=payload, allow_redirects=False) as response:
        if response.status != 200:
            raise StopExperiment(f"http_{response.status}")
        data = await response.json()
    if not isinstance(data, dict):
        raise StopExperiment("invalid_api_json")
    return data


async def preflight(session, plan: dict) -> dict:
    checks = {"models": [], "input_counts": {}, "request_reservations_usd": {}}
    for model in comparison.MODELS:
        data = await api_json(session, "GET", "/models/" + model)
        if data.get("id") != model:
            raise StopExperiment("model_access_mismatch")
        checks["models"].append({"model": model, "accessible": True})
    total = Decimal(0)
    for request in plan["requests"]:
        payload = request["payload"]
        # Exact same model and input, with no tools, files, history or instructions
        # outside input. These are the fields that contribute input tokens.
        data = await api_json(session, "POST", "/responses/input_tokens", payload={
            "model": payload["model"], "input": payload["input"],
        })
        if data.get("object") != "response.input_tokens":
            raise StopExperiment("unexpected_count_response")
        count = token_count(data.get("input_tokens"))
        held = reservation(request, count)
        checks["input_counts"][request["request_id"]] = count
        checks["request_reservations_usd"][request["request_id"]] = money(held)
        total += held
    checks["total_maximum_usd"] = money(total)
    if total > BUDGET:
        raise StopExperiment("plan_exceeds_one_dollar")
    checks["status"] = "passed"
    return checks


def blind_materials(results: list[dict], output: Path) -> None:
    # Randomize once and keep identities in a separate key. Blind examples have
    # no model, effort, latency, usage, transport IDs, hashes or execution order.
    shuffled = list(results)
    secrets.SystemRandom().shuffle(shuffled)
    key = {}
    examples = []
    lines = ["# Слепое сравнение текстов", "", "Оцените язык, род, тему, бережность, разнообразие и выполнение ограничений.", ""]
    for index, result in enumerate(shuffled, 1):
        sample = f"S{index:02d}"
        text = result.get("raw_text", "")
        # A model can mention itself in output: remove such identification only
        # from blind material; preserve the unmodified raw output in results.
        import re
        text = re.sub(r"(?i)gpt[- ._]*6(?:[ ._]*1)?[- ._]*(?:luna|terra)|gpt[- ._]*6(?:[ ._]*1)?|openai|\bluna\b|\bterra\b", "[скрыто]", text)
        example = {"sample_id": sample, "case_id": result["case_id"],
                   "inputs": result["inputs"], "review": result["review"], "text": text}
        examples.append(example)
        key[sample] = {"request_id": result["request_id"], "model": result["payload"]["model"],
                       "effort": result["payload"]["reasoning"]["effort"]}
        lines.extend([f"## {sample} — {result['case_id']}", "", result["review"], "",
                      "Контекст: " + json.dumps(result["inputs"], ensure_ascii=False), "",
                      text or "[Текст не получен]", ""])
    save(output / "blind-examples.json", {"examples": examples})
    (output / "blind-review.md").write_text("\n".join(lines), encoding="utf-8")
    save(output / "blind-key.json", key)


def write_metrics(report: dict, output: Path) -> dict:
    """Local-only aggregation: never invokes a model or reshuffles blind IDs."""
    rows = []
    grouped = {}
    for result in report["results"]:
        usage = result.get("usage") or {}
        details = usage.get("input_tokens_details") or {}
        model = result["payload"]["model"]
        effort = result["payload"]["reasoning"]["effort"]
        row = {
            "request_id": result["request_id"], "case_id": result["case_id"],
            "model": model, "reasoning_effort": effort,
            "input_tokens": usage.get("input_tokens"),
            "cached_tokens": details.get("cached_tokens"),
            "cache_write_tokens": details.get("cache_write_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "reasoning_tokens": result.get("reasoning_tokens"),
            "latency_seconds": result.get("latency_seconds"),
            "usage_cost_usd": result.get("usage_cost_usd"),
            "usage_cost_upper_usd": result.get("usage_cost_upper_usd"),
            "valid_four_strings": result.get("valid_four_strings", False),
        }
        rows.append(row)
        grouped.setdefault((model, effort), []).append(row)
    total_cost = sum((Decimal(row["usage_cost_usd"]) for row in rows if row["usage_cost_usd"] is not None), Decimal(0))
    summary = {
        "status": report["status"], "request_count": len(rows),
        "valid_four_strings": sum(row["valid_four_strings"] for row in rows),
        "usage_cost_usd": money(total_cost) if all(row["usage_cost_usd"] is not None for row in rows) else None,
        "reserved_maximum_usd": report["reserved_usd"],
        "total_reasoning_tokens": sum(row["reasoning_tokens"] or 0 for row in rows),
        "missing_reasoning_usage": sum(row["reasoning_tokens"] is None for row in rows),
        "groups": [],
    }
    for (model, effort), members in grouped.items():
        summary["groups"].append({
            "model": model, "reasoning_effort": effort, "requests": len(members),
            **{key: sum(row[key] or 0 for row in members) for key in (
                "input_tokens", "cached_tokens", "cache_write_tokens", "output_tokens", "total_tokens", "reasoning_tokens",
            )},
            "median_latency_seconds": round(median(row["latency_seconds"] for row in members), 6),
            "min_latency_seconds": min(row["latency_seconds"] for row in members),
            "max_latency_seconds": max(row["latency_seconds"] for row in members),
            "usage_cost_usd": money(sum((Decimal(row["usage_cost_usd"]) for row in members), Decimal(0)))
                if all(row["usage_cost_usd"] is not None for row in members) else None,
        })
    save(output / "summary.json", summary)
    if rows:
        with (output / "metrics.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    lines = ["# Результат ограниченного эксперимента", "",
             f"Статус: {summary['status']}. Выполнено: {len(rows)}/16. Формат четырёх строк: {summary['valid_four_strings']}/16.", "",
             f"Стоимость по usage и проверенным тарифам: ${summary['usage_cost_usd']}. Резерв до генерации: ${report['reserved_usd']}. Бюджет: $1.00.", "",
             "Сначала откройте [слепые тексты](blind-review.md). Соответствие моделей находится отдельно в blind-key.json.", "",
             "| Модель | Effort | Запросы | Input | Output | Reasoning | Медиана latency, с | USD по usage |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for group in summary["groups"]:
        lines.append(f"| {group['model']} | {group['reasoning_effort']} | {group['requests']} | {group['input_tokens']} | {group['output_tokens']} | {group['reasoning_tokens']} | {group['median_latency_seconds']:.3f} | {group['usage_cost_usd']} |")
    reasoning_note = (
        "API сообщил reasoning_tokens=0 во всех ответах, в том числе low. Усилие low было явно отправлено; скрытая работа модели по этому полю не выводится."
        if rows and summary["total_reasoning_tokens"] == 0 and summary["missing_reasoning_usage"] == 0
        else f"Сумма reasoning_tokens по доступному usage: {summary['total_reasoning_tokens']}; ответов без этого поля: {summary['missing_reasoning_usage']}."
    )
    lines.extend(["", reasoning_note, "",
                  "Reasoning входит в output. Цена рассчитана с учётом cache writes; это расчёт по API usage, не сверка с биллингом аккаунта.", "",
                  "Полные usage и latency каждого запроса: results.json и metrics.csv. Все 16 исходных и нормализованных текстов: results.json.", "",
                  "Сравнение выполнено через Responses с прежними production-промптами. Малый набор без повторов не позволяет надёжно ранжировать качество; перенос на Chat Completions требует отдельной проверки.", "",
                  "Сообщения подписчикам, production, БД, .env и подписки не изменялись; deploy, commit и push не выполнялись.", ""])
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


async def execute(plan: dict, *, api_key: str, output: Path, live: bool) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "results.json"
    # Claim this authorized experiment across processes/restarts. Even an
    # interrupted request cannot be repeated by restarting the CLI.
    if live:
        with (output / "paid-run.claim").open("x", encoding="utf-8") as claim:
            claim.write("Single authorized run; do not delete to retry.\n")
            claim.flush()
            os.fsync(claim.fileno())
    report = {"mode": "live" if live else "preflight", "status": "checking",
              "budget_usd": str(BUDGET), "reserved_usd": money(Decimal(0)),
              "paid_requests_submitted": 0, "results": []}
    destination = report_path if live else output / "preflight.json"
    save(destination, report)
    timeout = aiohttp.ClientTimeout(total=60)
    try:
        if datetime.now(timezone(timedelta(hours=3))).date().isoformat() != VERIFIED_ON:
            raise StopExperiment("reverify_current_prices_before_live")
        async with aiohttp.ClientSession(timeout=timeout, headers={
            "Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
        }) as session:
            report["preflight"] = await preflight(session, plan)
            report["status"] = "preflight_passed"
            save(destination, report)
            if not live:
                return report
            held_total = Decimal(0)
            for request in plan["requests"]:
                request_id = request["request_id"]
                count = report["preflight"]["input_counts"][request_id]
                held = reservation(request, count)
                if held_total + held > BUDGET:
                    raise StopExperiment("budget_exhausted_before_submission")
                held_total += held
                report["reserved_usd"] = money(held_total)
                report["pending_request_id"] = request_id
                report["paid_requests_submitted"] += 1
                # Reserve durably BEFORE submission. Never refund, including errors.
                save(destination, report)
                started = time.perf_counter()
                result = dict(request)
                report["results"].append(result)
                try:
                    data = await api_json(session, "POST", "/responses", payload=request["payload"])
                    result.update({k: data.get(k) for k in (
                        "id", "model", "service_tier", "status", "usage", "incomplete_details",
                    )})
                    result["reasoning_tokens"] = (data.get("usage") or {}).get("output_tokens_details", {}).get("reasoning_tokens")
                    raw = "\n".join(part["text"] for item in data.get("output", [])
                                    if item.get("type") == "message" for part in item.get("content", [])
                                    if part.get("type") == "output_text" and isinstance(part.get("text"), str))
                    result.update(comparison.assess_response(raw, request["inputs"]))
                    if data.get("model") != request["payload"]["model"] or data.get("service_tier") != "default":
                        raise StopExperiment("unexpected_model_or_tier")
                    exact, upper = usage_cost(data, request, count)
                    result["usage_cost_usd"] = money(exact) if exact is not None else None
                    result["usage_cost_upper_usd"] = money(upper)
                    if upper > held or data.get("status") != "completed":
                        raise StopExperiment("incomplete_or_unbounded_response")
                    if token_count(result["reasoning_tokens"]) > data["usage"]["output_tokens"]:
                        raise StopExperiment("invalid_reasoning_usage")
                except BaseException:
                    result["charge_status"] = "reservation_retained_do_not_retry"
                    raise
                finally:
                    result["latency_seconds"] = round(time.perf_counter() - started, 3)
                    save(destination, report)
                report.pop("pending_request_id", None)
                save(destination, report)
            report["status"] = "completed"
    except (aiohttp.ClientError, asyncio.TimeoutError, StopExperiment, ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
        report["status"] = "stopped"
        report["stop_reason"] = str(exc) if isinstance(exc, StopExperiment) else type(exc).__name__
    finally:
        save(destination, report)
        if live:
            blind_materials(report["results"], output)
            write_metrics(report, output)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true", help="Access and exact token counts only; no generation")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--allow-paid-api-calls", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    plan = build_plan()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if (args.output_dir / "paid-run.claim").exists():
        parser.error("this experiment was already claimed; do not retry paid requests")
    save(args.output_dir / "plan.json", plan)
    print("Plan: 16 paid requests (6+6 none, 2+2 low); maximum authorized: $1.00", flush=True)
    if not args.preflight and not args.live:
        return 0
    if args.live and not args.allow_paid_api_calls:
        parser.error("live mode requires --allow-paid-api-calls")
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        parser.error("OPENAI_API_KEY is required in this process; .env is not loaded")
    report = asyncio.run(execute(plan, api_key=key, output=args.output_dir, live=args.live))
    print(json.dumps({k: report.get(k) for k in (
        "status", "stop_reason", "paid_requests_submitted", "reserved_usd",
    )}), flush=True)
    return int(report["status"] not in ("completed", "preflight_passed"))


if __name__ == "__main__":
    raise SystemExit(main())
