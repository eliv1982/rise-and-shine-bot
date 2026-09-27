"""Stage 5 item M: Docker HEALTHCHECK is heartbeat-file based (no HTTP server
added just for this). scripts/healthcheck.py must correctly distinguish a
fresh heartbeat from a missing or stale one.
"""
from __future__ import annotations

import importlib.util
import time
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "healthcheck.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("healthcheck_script", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_heartbeat_is_unhealthy(tmp_path):
    module = _load_script_module()
    assert module.check(str(tmp_path / "heartbeat")) is False


def test_fresh_heartbeat_is_healthy(tmp_path):
    module = _load_script_module()
    heartbeat = tmp_path / "heartbeat"
    heartbeat.write_text("2030-01-01T00:00:00+00:00")

    assert module.check(str(heartbeat)) is True


def test_stale_heartbeat_is_unhealthy(tmp_path):
    module = _load_script_module()
    heartbeat = tmp_path / "heartbeat"
    heartbeat.write_text("stale")

    stale_now = time.time() + module.MAX_AGE_SECONDS + 60  # simulate the file having aged out
    assert module.check(str(heartbeat), now=stale_now) is False


def test_boundary_age_is_still_healthy(tmp_path):
    module = _load_script_module()
    heartbeat = tmp_path / "heartbeat"
    heartbeat.write_text("boundary")
    mtime = heartbeat.stat().st_mtime

    assert module.check(str(heartbeat), now=mtime + module.MAX_AGE_SECONDS) is True
    assert module.check(str(heartbeat), now=mtime + module.MAX_AGE_SECONDS + 1) is False


def test_main_returns_zero_for_healthy_and_one_for_unhealthy(monkeypatch, tmp_path, capsys):
    module = _load_script_module()
    heartbeat = tmp_path / "heartbeat"

    import config

    monkeypatch.setattr(config, "get_heartbeat_path", lambda: str(heartbeat))

    assert module.main([]) == 1
    assert "heartbeat missing or stale" in capsys.readouterr().err

    heartbeat.write_text("fresh")
    assert module.main([]) == 0
