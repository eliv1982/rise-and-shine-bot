"""Stage 5 item I: SQLite backup must be safe under concurrent writes and must
never silently overwrite a prior backup.

backup_sqlite.py uses sqlite3's online backup API rather than a plain file
copy - this test proves it captures a fully-committed snapshot even while a
separate connection is mid-write, and that it refuses to clobber an existing
destination.
"""
from __future__ import annotations

import importlib.util
import sqlite3
import threading
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "backup_sqlite.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("backup_sqlite_script", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_source_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE affirmations (id INTEGER PRIMARY KEY, text TEXT)")
    conn.execute("INSERT INTO affirmations (text) VALUES ('hello')")
    conn.commit()
    conn.close()


def test_backup_copies_committed_data(tmp_path):
    module = _load_script_module()
    source = tmp_path / "source.db"
    dest = tmp_path / "backup.db"
    _make_source_db(source)

    module.backup_sqlite(str(source), str(dest))

    conn = sqlite3.connect(str(dest))
    rows = conn.execute("SELECT text FROM affirmations").fetchall()
    conn.close()
    assert rows == [("hello",)]


def test_backup_refuses_to_overwrite_existing_destination(tmp_path):
    module = _load_script_module()
    source = tmp_path / "source.db"
    dest = tmp_path / "backup.db"
    _make_source_db(source)
    dest.write_bytes(b"pre-existing content, must survive")

    with pytest.raises(FileExistsError):
        module.backup_sqlite(str(source), str(dest))

    assert dest.read_bytes() == b"pre-existing content, must survive"


def test_backup_fails_loudly_when_source_missing(tmp_path):
    module = _load_script_module()
    with pytest.raises(FileNotFoundError):
        module.backup_sqlite(str(tmp_path / "does_not_exist.db"), str(tmp_path / "backup.db"))


def test_backup_is_safe_while_source_is_being_written(tmp_path):
    """Online backup (not a raw file copy) must not capture a torn snapshot."""
    module = _load_script_module()
    source = tmp_path / "source.db"
    dest = tmp_path / "backup.db"
    _make_source_db(source)

    stop = threading.Event()
    write_errors: list[BaseException] = []

    def keep_writing():
        # A fresh connection here, not shared with the main thread: sqlite3
        # connections are restricted to the thread that created them.
        conn = sqlite3.connect(str(source), timeout=5)
        try:
            n = 0
            while not stop.is_set():
                conn.execute("INSERT INTO affirmations (text) VALUES (?)", (f"row-{n}",))
                conn.commit()
                n += 1
        except BaseException as exc:  # noqa: BLE001 - surfaced via write_errors below
            write_errors.append(exc)
        finally:
            conn.close()

    writer_thread = threading.Thread(target=keep_writing, daemon=True)
    writer_thread.start()
    try:
        module.backup_sqlite(str(source), str(dest))
    finally:
        stop.set()
        writer_thread.join(timeout=5)

    assert not writer_thread.is_alive()
    assert write_errors == []

    # The backup must be a valid, readable database with no corruption, whatever
    # point in the stream of commits it happened to capture.
    conn = sqlite3.connect(str(dest))
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    count = conn.execute("SELECT COUNT(*) FROM affirmations").fetchone()[0]
    conn.close()
    assert integrity == "ok"
    assert count >= 1


def test_cli_reports_clear_errors_without_traceback(tmp_path, capsys):
    module = _load_script_module()
    exit_code = module.main(["--source", str(tmp_path / "missing.db"), "--destination", str(tmp_path / "out.db")])

    assert exit_code == 1
    assert "FAIL" in capsys.readouterr().err
