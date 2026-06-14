import json
import sqlite3

from scripts.inspect_generation_roles import main


def _init_test_db(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE generation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                request_type TEXT NOT NULL,
                focus_title TEXT,
                soft_action TEXT
            );

            CREATE TABLE visual_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generation_id INTEGER,
                telegram_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                scene_type TEXT,
                visual_motifs_json TEXT
            );
            """
        )
        conn.execute(
            """
            INSERT INTO generation_history (
                telegram_user_id, created_at, request_type, focus_title, soft_action
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (1, "2030-01-01T00:00:00+00:00", "manual", "мягкая опора", "Назовите три вещи, которые уже помогают"),
        )
        generation_id = conn.execute("SELECT id FROM generation_history").fetchone()[0]
        motifs = {
            "selected_style": "living_nature_photo",
            "text_plan_shadow": {"enabled": True},
            "text_prompt_controlled": {"enabled": True, "guidance_used": True},
            "text_memory_context": {
                "recent_focus_titles_count": 2,
                "avoid_soft_actions_count": 1,
                "recent_affirmation_openings": ["я принимаю", "сегодня я"],
                "overused_affirmation_openings": ["я принимаю"],
                "overused_text_patterns": ["я выбираю"],
                "avoid_soft_action_patterns": ["name_three_things"],
                "overused_soft_action_patterns": ["name_three_things"],
                "avoid_soft_action_structures": ["contrast_from_not_from"],
                "overused_soft_action_structures": ["contrast_from_not_from"],
                "overused_abstract_words": ["ясность", "страх"],
            },
            "text_reviewer_shadow": {
                "score": 0.8,
                "warnings": ["soft_action_repeated", "abstract_contrast_formula"],
                "checks": {
                    "soft_action_repeated": True,
                    "repeated_soft_action_structure": True,
                    "abstract_contrast_formula": True,
                    "too_generic": True,
                    "gender_mismatch": False,
                },
            },
            "scene_plan_shadow": {"enabled": True},
            "scene_prompt_controlled": {"enabled": True},
            "orchestrator_shadow": {
                "enabled": True,
                "route": {
                    "text_planner": True,
                    "text_memory": True,
                    "text_reviewer": True,
                    "scene_planner": True,
                    "scene_prompt_controlled": True,
                },
                "quality": {
                    "text_reviewer_score": 0.8,
                    "text_warnings_count": 1,
                    "text_memory_overused_count": 2,
                },
                "decisions": ["text planner guidance used", "text memory anti-repeat used"],
            },
        }
        conn.execute(
            """
            INSERT INTO visual_history (
                generation_id, telegram_user_id, created_at, scene_type, visual_motifs_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (generation_id, 1, "2030-01-01T00:00:00+00:00", "forest_path", json.dumps(motifs, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()


def test_inspect_generation_roles_human_output_includes_role_flags(tmp_path, capsys):
    db_path = tmp_path / "roles.db"
    _init_test_db(db_path)

    exit_code = main(["--db", str(db_path), "--limit", "5"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "text_plan_shadow=true" in captured.out
    assert "text_reviewer_shadow=true" in captured.out
    assert "overused_affirmation_openings=['я принимаю']" in captured.out
    assert "overused_soft_action_structures=['contrast_from_not_from']" in captured.out
    assert "orchestrator_decisions" in captured.out


def test_inspect_generation_roles_json_output_is_valid_json(tmp_path, capsys):
    db_path = tmp_path / "roles_json.db"
    _init_test_db(db_path)

    exit_code = main(["--db", str(db_path), "--limit", "5", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["reports"][0]["role_flags"]["orchestrator_shadow"] is True
    assert payload["reports"][0]["reviewer"]["score"] == 0.8
    assert payload["reports"][0]["reviewer"]["checks"]["repeated_soft_action_structure"] is True
    assert payload["reports"][0]["text_memory"]["overused_soft_action_structures"] == ["contrast_from_not_from"]


def test_inspect_generation_roles_invalid_json_does_not_crash(tmp_path, capsys):
    db_path = tmp_path / "roles_bad_json.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE generation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                request_type TEXT NOT NULL,
                focus_title TEXT,
                soft_action TEXT
            );
            CREATE TABLE visual_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generation_id INTEGER,
                telegram_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                scene_type TEXT,
                visual_motifs_json TEXT
            );
            """
        )
        conn.execute(
            "INSERT INTO generation_history (telegram_user_id, created_at, request_type, focus_title, soft_action) VALUES (?, ?, ?, ?, ?)",
            (1, "2030-01-01T00:00:00+00:00", "manual", "focus", "soft"),
        )
        generation_id = conn.execute("SELECT id FROM generation_history").fetchone()[0]
        conn.execute(
            "INSERT INTO visual_history (generation_id, telegram_user_id, created_at, scene_type, visual_motifs_json) VALUES (?, ?, ?, ?, ?)",
            (generation_id, 1, "2030-01-01T00:00:00+00:00", "forest_path", "{bad-json"),
        )
        conn.commit()
    finally:
        conn.close()

    exit_code = main(["--db", str(db_path), "--limit", "5"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "roles:" in captured.out


def test_inspect_generation_roles_missing_db_returns_non_zero(tmp_path, capsys):
    missing_db = tmp_path / "missing.db"

    exit_code = main(["--db", str(missing_db), "--limit", "5"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Database not found" in captured.err
