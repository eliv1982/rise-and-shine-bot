import asyncio
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import compare_text_models as comparison


def _cases():
    return json.loads(comparison.FIXTURES.read_text(encoding="utf-8"))


def test_offline_manifest_uses_identical_inputs_for_both_models():
    first = comparison.build_requests(_cases(), repeats=2)
    assert first == comparison.build_requests(_cases(), repeats=2)
    assert len(first) == 24
    for index in range(0, len(first), 2):
        luna, terra = first[index:index + 2]
        assert {luna["payload"]["model"], terra["payload"]["model"]} == set(comparison.MODELS)
        assert luna["case_id"] == terra["case_id"]
        assert luna["input_sha256"] == terra["input_sha256"]
        assert luna["payload"]["messages"] == terra["payload"]["messages"]
        assert "max_tokens" not in luna["payload"]
        assert "Authorization" not in json.dumps(luna)


def test_offline_cli_has_no_credentials_or_network(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline comparison must not open a network session")

    monkeypatch.setattr(comparison.aiohttp, "ClientSession", forbidden)
    monkeypatch.setenv("OPENAI_API_KEY", "secret-must-not-be-read")
    monkeypatch.setenv("OPENAI_TEXT_MODEL", "ignored-runtime-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://ignored.invalid/v1")
    output = tmp_path / "requests.json"
    assert comparison.main(["--output", str(output)]) == 0
    raw = output.read_text(encoding="utf-8")
    assert "secret-must-not-be-read" not in raw
    assert "ignored-runtime-model" not in raw
    assert "ignored.invalid" not in raw
    report = json.loads(raw)
    assert report["mode"] == "offline"
    assert report["request_count"] == 12


def test_standalone_cli_never_loads_dotenv_or_imports_bot_database(tmp_path):
    script = Path(comparison.__file__).resolve()
    output = tmp_path / "requests.json"
    # Run from another directory, in a fresh process. A dotenv read or importing
    # bot/database/scheduler is a failure, regardless of this pytest session's imports.
    code = "\n".join([
        "import dotenv, runpy, sys",
        "def forbidden(*a, **kw): raise AssertionError('dotenv read')",
        "dotenv.load_dotenv = forbidden",
        f"sys.argv = [{str(script)!r}, '--output', {str(output)!r}]",
        "try:",
        f"    runpy.run_path({str(script)!r}, run_name='__main__')",
        "except SystemExit as exc: assert exc.code == 0",
        "assert not {'database', 'bot', 'scheduler'} & sys.modules.keys()",
    ])
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["request_count"] == 12


@pytest.mark.parametrize("argv", [["--live"], ["--live", "--allow-paid-api-calls"]])
def test_live_cli_requires_explicit_opt_in_and_process_key(monkeypatch, argv):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        comparison.main(argv)
    assert exc.value.code == 2


@pytest.mark.parametrize("extra,expected", [
    ([], 12), (["--case", "ru_female_career"], 2), (["--repeats", "3"], 36),
])
def test_live_cli_announces_count_before_any_network_call(monkeypatch, tmp_path, capsys, extra, expected):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    async def fake_live(requests, **kwargs):
        # Assertion runs at the boundary where the first real session would open.
        assert f"Planned paid API calls: {expected}" in capsys.readouterr().err
        assert len(requests) == expected
        return [{"valid_four_strings": True} for _ in requests]

    monkeypatch.setattr(comparison, "run_live", fake_live)
    assert comparison.main([
        "--live", "--allow-paid-api-calls", "--output", str(tmp_path / "fake-live.json"), *extra,
    ]) == 0


def test_announcing_paid_count_does_not_bypass_explicit_consent(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def forbidden(*args, **kwargs):
        raise AssertionError("No network without explicit paid opt-in")

    monkeypatch.setattr(comparison, "run_live", forbidden)
    with pytest.raises(SystemExit) as exc:
        comparison.main(["--live", "--case", "ru_female_career"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "Planned paid API calls: 2" in err
    assert "requires --allow-paid-api-calls" in err


def test_case_filter_and_reasoning_parameters(tmp_path):
    output = tmp_path / "low.json"
    assert comparison.main([
        "--case", "ru_female_career", "--reasoning-effort", "low",
        "--max-completion-tokens", "4096", "--output", str(output),
    ]) == 0
    requests = json.loads(output.read_text(encoding="utf-8"))["requests"]
    assert len(requests) == 2
    for request in requests:
        assert request["payload"]["reasoning_effort"] == "low"
        assert request["payload"]["max_completion_tokens"] == 4096
        assert "temperature" not in request["payload"]


@pytest.mark.parametrize("raw,valid", [
    ('["a", "b", "c", "d"]', True), ('```json\n["a", "b", "c", "d"]\n```', True),
    ('[]', False), ('["", "b", "c", "d"]', False), ('not JSON', False),
])
def test_comparison_flags_invalid_format_without_hiding_raw_output(raw, valid):
    result = comparison.assess_response(raw, {"language": "en"})
    assert result["valid_four_strings"] is valid
    assert result["raw_text"] == raw


def test_comparison_records_gender_cleanup_and_diversity():
    result = comparison.assess_response(
        '["Я готов", "Я готов", "Мой голос важен", "Сегодня есть выбор"]',
        {"language": "ru", "gender": "female"},
    )
    assert result["gender_cleanup_changed"] is True
    assert result["affirmations"][0] == "Я готова"
    assert result["unique_affirmations"] == 3
    assert result["unique_openings"] == 3


@pytest.mark.parametrize("status,content,finish", [
    (200, '["a", "b", "c", "d"]', "stop"),
    (429, None, None), (200, "", "length"),
])
def test_live_transport_is_mocked_and_records_usage_without_secrets(monkeypatch, status, content, finish):
    calls = []

    class Response:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def json(self):
            return {
                "id": "synthetic-id", "model": "resolved-model", "system_fingerprint": "test",
                "choices": [{"message": {"content": content}, "finish_reason": finish}],
                "usage": {"completion_tokens": 100, "completion_tokens_details": {"reasoning_tokens": 40}},
            }

    Response.status = status

    class Session:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response()

    monkeypatch.setattr(comparison.aiohttp, "ClientSession", Session)
    requests = comparison.build_requests(_cases()[:1])
    results = asyncio.run(comparison.run_live(requests, api_key="test-secret", timeout_seconds=5))
    assert len(calls) == len(results) == 2
    assert "test-secret" not in json.dumps(results)
    for result in results:
        assert result["http_status"] == status
        assert result["elapsed_seconds"] >= 0
        if status == 200:
            assert result["usage"]["completion_tokens_details"]["reasoning_tokens"] == 40
            assert result["response_model"] == "resolved-model"
        if status != 200 or finish == "length":
            assert result["error"] == "RuntimeError"
        else:
            assert result["valid_four_strings"] is True
