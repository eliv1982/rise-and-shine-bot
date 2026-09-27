"""Safe SQLite backup for scripts/backup.sh.

Uses sqlite3's online backup API (Connection.backup()), which SQLite documents
as safe to run against a database that is actively being written to, under any
journal mode (including WAL) - unlike a plain file copy, which can capture a
torn/mid-transaction snapshot if it races a writer.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


def backup_sqlite(source: str, destination: str) -> None:
    source_path = Path(source)
    if not source_path.is_file():
        raise FileNotFoundError(f"source database not found: {source_path}")
    dest_path = Path(destination)
    if dest_path.exists():
        raise FileExistsError(f"backup destination already exists, refusing to overwrite: {dest_path}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    source_conn = sqlite3.connect(str(source_path))
    try:
        dest_conn = sqlite3.connect(str(dest_path))
        try:
            source_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        source_conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe online backup of a SQLite database.")
    parser.add_argument("--source", required=True, help="Path to the live SQLite database")
    parser.add_argument("--destination", required=True, help="Path to write the backup to (must not already exist)")
    args = parser.parse_args(argv)

    try:
        backup_sqlite(args.source, args.destination)
    except (FileNotFoundError, FileExistsError) as exc:
        print(f"[backup] FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"[backup] wrote {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
