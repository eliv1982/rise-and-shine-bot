from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from typing import Any


ROLE_KEYS = [
    "text_plan_shadow",
    "text_prompt_controlled",
    "text_memory_context",
    "text_reviewer_shadow",
    "scene_plan_shadow",
    "scene_prompt_controlled",
    "orchestrator_shadow",
]

FORMAL_ADDRESS_PATTERNS = [
    "выберите",
    "назовите",
    "сделайте",
    "примите",
    "упростите",
    "запишите",
    "заметьте",
    "позвольте",
    "подумайте",
    "отметьте",
    "остановитесь",
    "подышите",
]


def _safe_json_loads(value: Any) -> Any:
    if not value:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool(value: Any) -> bool:
    return bool(value)


def _true_checks_only(checks: dict | None) -> dict:
    safe = checks if isinstance(checks, dict) else {}
    result = {}
    for key, value in safe.items():
        if value is True:
            result[key] = True
        elif isinstance(value, list) and value:
            result[key] = value
    return result


def _build_warnings(report: dict) -> list[str]:
    warnings: list[str] = []
    motifs = report.get("visual_motifs") or {}
    orchestrator = motifs.get("orchestrator_shadow") or {}
    route = orchestrator.get("route") or {}
    for route_key, metadata_key in [
        ("text_planner", "text_plan_shadow"),
        ("text_memory", "text_memory_context"),
        ("text_reviewer", "text_reviewer_shadow"),
        ("scene_planner", "scene_plan_shadow"),
        ("scene_prompt_controlled", "scene_prompt_controlled"),
    ]:
        if route.get(route_key) and not motifs.get(metadata_key):
            warnings.append(f"missing {metadata_key} while orchestrator route says enabled")

    reviewer = motifs.get("text_reviewer_shadow") or {}
    score = reviewer.get("score")
    if isinstance(score, (int, float)) and score < 1.0:
        warnings.append(f"reviewer score < 1.0 ({score})")
    checks = reviewer.get("checks") or {}
    if checks.get("gender_mismatch"):
        warnings.append("gender mismatch detected")
    if checks.get("soft_action_repeated"):
        warnings.append("soft_action repeated")

    text_chunks = []
    focus_title = report.get("focus_title")
    soft_action = report.get("soft_action")
    if focus_title:
        text_chunks.append(str(focus_title).lower())
    if soft_action:
        text_chunks.append(str(soft_action).lower())
    motifs_text = " ".join(text_chunks)
    if any(pattern in motifs_text for pattern in FORMAL_ADDRESS_PATTERNS):
        warnings.append("formal address detected")

    deduped: list[str] = []
    seen = set()
    for item in warnings:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def build_report_from_row(row: sqlite3.Row) -> dict:
    visual_motifs = _safe_json_loads(row["visual_motifs_json"])
    motifs = visual_motifs if isinstance(visual_motifs, dict) else {}
    reviewer = motifs.get("text_reviewer_shadow") if isinstance(motifs.get("text_reviewer_shadow"), dict) else {}
    text_memory = motifs.get("text_memory_context") if isinstance(motifs.get("text_memory_context"), dict) else {}
    orchestrator = motifs.get("orchestrator_shadow") if isinstance(motifs.get("orchestrator_shadow"), dict) else {}

    role_flags = {key: _bool(motifs.get(key)) for key in ROLE_KEYS}

    report = {
        "visual_history_id": row["visual_history_id"],
        "created_at": row["created_at"],
        "focus_title": _clean_text(row["focus_title"]),
        "soft_action": _clean_text(row["soft_action"]),
        "selected_style": _clean_text(motifs.get("selected_style")),
        "scene_type": _clean_text(row["scene_type"]) or _clean_text(motifs.get("scene_type")),
        "role_flags": role_flags,
        "reviewer": {
            "score": reviewer.get("score"),
            "warnings": list(reviewer.get("warnings") or []),
            "checks": _true_checks_only(reviewer.get("checks")),
        },
        "text_memory": {
            "recent_focus_titles_count": len((text_memory.get("recent_focus_titles") or [])) if "recent_focus_titles" in text_memory else text_memory.get("recent_focus_titles_count", 0),
            "avoid_soft_actions_count": len((text_memory.get("avoid_soft_actions") or [])) if "avoid_soft_actions" in text_memory else text_memory.get("avoid_soft_actions_count", 0),
            "overused_text_patterns": list(text_memory.get("overused_text_patterns") or []),
            "avoid_soft_action_patterns": list(text_memory.get("avoid_soft_action_patterns") or []),
            "overused_soft_action_patterns": list(text_memory.get("overused_soft_action_patterns") or []),
        },
        "orchestrator": {
            "route": orchestrator.get("route") or {},
            "quality": orchestrator.get("quality") or {},
            "decisions": list(orchestrator.get("decisions") or []),
        },
        "visual_motifs": motifs,
    }
    report["warnings"] = _build_warnings(report)
    return report


def fetch_reports(db_path: str, limit: int) -> tuple[list[dict], str | None]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name IN ('visual_history', 'generation_history')
            ORDER BY name
            """
        )
        tables = {row["name"] for row in cur.fetchall()}
        if "visual_history" not in tables or "generation_history" not in tables:
            return [], "Required history tables are missing."

        cur = conn.execute(
            """
            SELECT
                vh.id AS visual_history_id,
                vh.created_at AS created_at,
                vh.scene_type AS scene_type,
                vh.visual_motifs_json AS visual_motifs_json,
                gh.focus_title AS focus_title,
                gh.soft_action AS soft_action
            FROM visual_history vh
            LEFT JOIN generation_history gh ON gh.id = vh.generation_id
            ORDER BY vh.created_at DESC, vh.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [build_report_from_row(row) for row in rows], None
    finally:
        conn.close()


def _format_human_report(report: dict) -> str:
    role_flags = report["role_flags"]
    reviewer = report["reviewer"]
    text_memory = report["text_memory"]
    orchestrator = report["orchestrator"]
    lines = [
        f"[visual_history #{report['visual_history_id']}] {report['created_at']}",
        f"focus_title: {report.get('focus_title') or '—'}",
        f"soft_action: {report.get('soft_action') or '—'}",
        f"selected_style: {report.get('selected_style') or '—'}",
        f"scene_type: {report.get('scene_type') or '—'}",
        "roles: "
        + ", ".join(f"{key}={str(value).lower()}" for key, value in role_flags.items()),
        f"reviewer: score={reviewer.get('score')} warnings={reviewer.get('warnings') or []} checks={reviewer.get('checks') or {}}",
        "text_memory: "
        + f"recent_focus_titles_count={text_memory.get('recent_focus_titles_count', 0)} "
        + f"avoid_soft_actions_count={text_memory.get('avoid_soft_actions_count', 0)} "
        + f"overused_text_patterns={text_memory.get('overused_text_patterns') or []} "
        + f"avoid_soft_action_patterns={text_memory.get('avoid_soft_action_patterns') or []} "
        + f"overused_soft_action_patterns={text_memory.get('overused_soft_action_patterns') or []}",
        f"orchestrator_route: {orchestrator.get('route') or {}}",
        f"orchestrator_quality: {orchestrator.get('quality') or {}}",
        f"orchestrator_decisions: {orchestrator.get('decisions') or []}",
    ]
    if report.get("warnings"):
        lines.append(f"warnings: {report['warnings']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect latest generation role metadata from SQLite history.")
    parser.add_argument("--db", required=True, help="Path to SQLite database, e.g. bot.db")
    parser.add_argument("--limit", type=int, default=5, help="Number of latest visual_history rows to inspect")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of human-readable report")
    args = parser.parse_args(argv)

    db_path = args.db
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    reports, message = fetch_reports(db_path, max(1, args.limit))
    if args.json:
        serializable = []
        for report in reports:
            copy = dict(report)
            copy.pop("visual_motifs", None)
            serializable.append(copy)
        print(json.dumps({"reports": serializable, "message": message}, ensure_ascii=False, indent=2))
        return 0

    if message:
        print(message)
        return 0
    if not reports:
        print("No history rows found.")
        return 0

    for index, report in enumerate(reports):
        if index:
            print("\n" + "-" * 60 + "\n")
        print(_format_human_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
