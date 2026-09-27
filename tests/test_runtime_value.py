"""scripts/runtime_value.py: the single place scripts/backup.sh and
scripts/restore.sh get DATABASE_URL / the SQLite path from, so they see
exactly what config.py would use at runtime.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "runtime_value.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("runtime_value_script", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_database_url_reflects_postgres_when_set(monkeypatch, capsys):
    module = _load_script_module()
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.internal:5432/rise_bot")

    exit_code = module.main(["database_url"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "postgresql://user:pass@db.internal:5432/rise_bot"


def test_database_url_empty_when_unset(monkeypatch, capsys):
    module = _load_script_module()
    monkeypatch.delenv("DATABASE_URL", raising=False)

    exit_code = module.main(["database_url"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == ""


def test_sqlite_db_path_reflects_override(monkeypatch, capsys):
    module = _load_script_module()
    monkeypatch.setenv("SQLITE_DB_PATH", "/data/custom.db")

    exit_code = module.main(["sqlite_db_path"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "/data/custom.db"


def test_unknown_field_is_rejected(capsys):
    module = _load_script_module()

    exit_code = module.main(["not_a_real_field"])

    assert exit_code == 2
    assert "usage" in capsys.readouterr().err
