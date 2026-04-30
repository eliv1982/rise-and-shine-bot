from services.generation_context import build_generation_context_snapshot


def test_generation_context_uses_explicit_theme_and_preserves_separate_style_notes():
    snapshot = build_generation_context_snapshot(
        {
            "sphere": "relationships",
            "subsphere": "partner",
            "theme_text": "stale theme from fsm",
            "style": "custom",
            "custom_style_description": "soft coastal editorial photo",
            "visual_mode": "photo",
        },
        theme_text="explicit theme",
    )

    assert snapshot.theme_text == "explicit theme"
    assert snapshot.custom_style_description == "soft coastal editorial photo"
    assert snapshot.subsphere == "partner"


def test_generation_context_preserves_current_fallbacks_for_missing_values():
    snapshot = build_generation_context_snapshot({}, theme_text=None)

    assert snapshot.sphere is None
    assert snapshot.subsphere is None
    assert snapshot.style == "nature"
    assert snapshot.visual_mode == "illustration"
    assert snapshot.custom_style_description is None
    assert snapshot.last_stt_meta is None
    assert snapshot.recent_generation_history == []


def test_generation_context_copies_recent_generation_history():
    history = [{"selected_style": "sea_coast_photo"}]

    snapshot = build_generation_context_snapshot(
        {"recent_generation_history": history},
        theme_text=None,
    )
    history.append({"selected_style": "light_interior_photo"})

    assert snapshot.recent_generation_history == [{"selected_style": "sea_coast_photo"}]
