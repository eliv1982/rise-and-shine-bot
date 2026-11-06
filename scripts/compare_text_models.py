"""Compare Luna and Terra on synthetic affirmation inputs, without bot or DB access.

Default: deterministic, offline request manifest. Live mode requires BOTH
--live and --allow-paid-api-calls and an OPENAI_API_KEY in the process environment.
The local .env is never loaded. No Telegram, images, TTS, subscriptions or retries.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# config.py normally loads .env at import time. Limit this override to imports so
# even an offline run cannot pick up production secrets or runtime configuration.
with patch("dotenv.load_dotenv", return_value=False):
    from config import TextProviderConfig
    from services.yandex_gpt import (
        _affirmation_system_message,
        _affirmation_temperature,
        _build_prompt,
        _build_text_provider_request,
        _parse_text_provider_response,
        normalize_russian_user_facing_text_fields,
    )

import aiohttp


MODELS = ("gpt-6-luna", "gpt-6.1-terra")
FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "text_model_comparison.json"


def build_requests(
    cases: list[dict],
    *,
    repeats: int = 1,
    reasoning_effort: str = "none",
    max_completion_tokens: int = 512,
) -> list[dict]:
    requests = []
    for repeat in range(repeats):
        for index, case in enumerate(cases):
            inputs = case["inputs"]
            prompt = _build_prompt(**inputs)
            language = inputs.get("language", "ru")
            gender = inputs.get("gender")
            # Alternate order to reduce systematic first/second model bias.
            models = MODELS if (index + repeat) % 2 == 0 else tuple(reversed(MODELS))
            for model in models:
                cfg = TextProviderConfig(
                    provider="openai",
                    base_url="https://api.openai.com/v1",
                    api_key="",  # credentials are never part of the manifest
                    model=model,
                    timeout_seconds=60,
                    reasoning_effort=reasoning_effort,
                    max_completion_tokens=max_completion_tokens,
                )
                url, _, payload = _build_text_provider_request(
                    cfg,
                    system_text=_affirmation_system_message(language, gender),
                    user_text=prompt,
                    temperature=_affirmation_temperature(language, gender),
                    max_tokens=512,
                )
                comparable = {key: value for key, value in payload.items() if key != "model"}
                digest = hashlib.sha256(
                    json.dumps(comparable, sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest()
                requests.append({
                    "case_id": case["id"],
                    "repeat": repeat + 1,
                    "inputs": inputs,
                    "review": case["review"],
                    "input_sha256": digest,
                    "url": url,
                    "payload": payload,
                })
    return requests


def assess_response(raw: str, inputs: dict) -> dict:
    """Record format/diversity checks; language, meaning and tone need human review."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines.pop()
        cleaned = "\n".join(lines).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = None
    valid = (
        isinstance(parsed, list) and len(parsed) == 4
        and all(isinstance(item, str) and item.strip() for item in parsed)
    )
    result = {"valid_four_strings": bool(valid), "raw_text": raw}
    if valid:
        affirmations = parsed
        if inputs.get("language", "ru") == "ru":
            affirmations = normalize_russian_user_facing_text_fields(
                parsed, gender=inputs.get("gender"), gender_hint=inputs.get("gender_hint"),
            )
        result.update({
            "affirmations": affirmations,
            "gender_cleanup_changed": affirmations != parsed,
            "unique_affirmations": len({item.strip().casefold() for item in affirmations}),
            "unique_openings": len({" ".join(item.split()[:2]).casefold() for item in affirmations}),
        })
    return result


async def run_live(requests: list[dict], *, api_key: str, timeout_seconds: int) -> list[dict]:
    results = []
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for request in requests:
            cfg = TextProviderConfig(
                provider="openai", base_url="https://api.openai.com/v1", api_key=api_key,
                model=request["payload"]["model"], timeout_seconds=timeout_seconds,
            )
            started = time.perf_counter()
            result = dict(request)
            try:
                async with session.post(
                    request["url"], json=request["payload"],
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                ) as response:
                    result["http_status"] = response.status
                    if response.status != 200:
                        raise RuntimeError(f"Text provider request failed with status {response.status}")
                    data = await response.json()
                # Retain usage even when parsing fails (e.g. all tokens spent on reasoning).
                result["usage"] = data.get("usage")
                result["response_model"] = data.get("model")
                result["response_id"] = data.get("id")
                result["system_fingerprint"] = data.get("system_fingerprint")
                result["finish_reason"] = (data.get("choices") or [{}])[0].get("finish_reason")
                raw = _parse_text_provider_response(cfg, data)
                result.update(assess_response(raw, request["inputs"]))
            except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
                # Never persist an error body or exception text that could echo credentials.
                result["error"] = type(exc).__name__
            result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            results.append(result)
    return results


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main(argv: list[str] | None = None) -> int:
    cases = json.loads(FIXTURES.read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--allow-paid-api-calls", action="store_true")
    parser.add_argument("--case", choices=[case["id"] for case in cases])
    parser.add_argument("--repeats", type=int, choices=range(1, 6), default=1)
    parser.add_argument("--reasoning-effort", choices=["none", "low", "medium", "high", "xhigh", "max"], default="none")
    parser.add_argument("--max-completion-tokens", type=_positive_int, default=512)
    parser.add_argument("--timeout-seconds", type=_positive_int, default=60)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    selected = [case for case in cases if not args.case or case["id"] == args.case]
    if args.live:
        planned_calls = len(selected) * len(MODELS) * args.repeats
        print(f"Planned paid API calls: {planned_calls} "
              f"({len(selected)} cases x {len(MODELS)} models x {args.repeats} repeats).",
              file=sys.stderr, flush=True)
    if args.live and not args.allow_paid_api_calls:
        parser.error("live mode requires --allow-paid-api-calls after separate approval")
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() if args.live else ""
    if args.live and not api_key:
        parser.error("set OPENAI_API_KEY in the process environment; .env is never read")
    requests = build_requests(
        selected, repeats=args.repeats, reasoning_effort=args.reasoning_effort,
        max_completion_tokens=args.max_completion_tokens,
    )
    report = {"mode": "live" if args.live else "offline", "request_count": len(requests)}
    if args.live:
        results = asyncio.run(run_live(requests, api_key=api_key, timeout_seconds=args.timeout_seconds))
        report["results"] = results
    else:
        report["requests"] = requests
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"{report['mode']}: {len(requests)} requests; report: {args.output}")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(rendered, end="")
    return int(args.live and any(
        item.get("error") or not item.get("valid_four_strings") for item in report["results"]
    ))


if __name__ == "__main__":
    raise SystemExit(main())
