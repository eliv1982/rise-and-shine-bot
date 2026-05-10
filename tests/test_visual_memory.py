import asyncio

from services import visual_memory


def test_extract_visual_motifs_from_prompt_finds_basic_motifs():
    prompt = "A beach scene with sea waves, ceramic cup, notebook on a table near a window."

    motifs = visual_memory.extract_visual_motifs_from_prompt(prompt)

    assert motifs == ["beach", "mug", "notebook", "table", "window"]


def test_extract_visual_motifs_from_prompt_returns_empty_for_none_or_empty():
    assert visual_memory.extract_visual_motifs_from_prompt(None) == []
    assert visual_memory.extract_visual_motifs_from_prompt("") == []
    assert visual_memory.extract_visual_motifs_from_prompt(123) == []


def test_build_visual_memory_context_counts_overused_motifs():
    recent_generations = [
        {"image_prompt": "Beach sunrise with mug on table."},
        {"image_prompt": "Ocean coast with coffee cup near window."},
        {"image_prompt": "Forest path with flowers."},
    ]
    recent_visuals = [
        {"scene_type": "riverside", "visual_motifs": {"selected_style": "soft_editorial", "visual_mode": "photo"}},
        {"scene_type": "forest_path", "visual_motifs": {"selected_style": "dreamy_painterly", "visual_mode": "illustration"}},
    ]

    context = visual_memory.build_visual_memory_context(recent_generations, recent_visuals, limit=10)

    assert context["motif_counts"]["beach"] == 2
    assert context["motif_counts"]["mug"] == 2
    assert context["overused_motifs"] == ["beach", "mug"]


def test_hard_avoid_today_includes_recent_cliche_motifs_even_once():
    recent_generations = [
        {"image_prompt": "Notebook on a table."},
        {"image_prompt": "Open window and a person by the sea."},
        {"image_prompt": "Forest and flowers."},
        {"image_prompt": "Garden only."},
    ]

    context = visual_memory.build_visual_memory_context(recent_generations, [], limit=10)

    assert "notebook" in context["hard_avoid_today"]
    assert "table" in context["hard_avoid_today"]
    assert "window" in context["hard_avoid_today"]
    assert "human" in context["hard_avoid_today"]
    assert "beach" in context["hard_avoid_today"]


def test_prefer_scene_types_excludes_recent_scene_types():
    recent_visuals = [
        {"scene_type": "forest_path", "visual_motifs": {"scene_type": "forest_path"}},
        {"scene_type": "library_corner", "visual_motifs": {}},
        {"scene_type": None, "visual_motifs": {"scene_type": "riverside"}},
    ]

    context = visual_memory.build_visual_memory_context([], recent_visuals, limit=10)

    assert "forest_path" not in context["prefer_scene_types"]
    assert "library_corner" not in context["prefer_scene_types"]
    assert "riverside" not in context["prefer_scene_types"]


def test_recent_selected_styles_and_visual_modes_are_collected():
    recent_visuals = [
        {"scene_type": "quiet_city_morning", "visual_motifs": {"selected_style": "soft_editorial", "visual_mode": "photo"}},
        {"scene_type": "garden_morning", "visual_motifs": {"selected_style": "dreamy_painterly", "visual_mode": "illustration"}},
        {"scene_type": "garden_morning", "visual_motifs": {"selected_style": "soft_editorial", "visual_mode": "photo"}},
    ]

    context = visual_memory.build_visual_memory_context([], recent_visuals, limit=10)

    assert context["recent_selected_styles"] == ["soft_editorial", "dreamy_painterly"]
    assert context["recent_visual_modes"] == ["photo", "illustration"]


def test_scene_type_counts_are_collected():
    recent_visuals = [
        {"scene_type": "forest_path", "visual_motifs": {}},
        {"scene_type": "forest_path", "visual_motifs": {}},
        {"scene_type": "garden_morning", "visual_motifs": {}},
    ]

    context = visual_memory.build_visual_memory_context([], recent_visuals, limit=10)

    assert context["scene_type_counts"] == {"forest_path": 2, "garden_morning": 1}


def test_get_visual_memory_context_uses_database_functions(monkeypatch):
    async def _fake_generations(user_id, limit=10):
        assert user_id == 123
        assert limit == 5
        return [{"image_prompt": "Beach with mug by the window."}]

    async def _fake_visuals(user_id, limit=10):
        assert user_id == 123
        assert limit == 5
        return [{"scene_type": "forest_path", "visual_motifs": {"selected_style": "soft_editorial", "visual_mode": "photo"}}]

    monkeypatch.setattr(visual_memory, "get_recent_generation_history", _fake_generations)
    monkeypatch.setattr(visual_memory, "get_recent_visual_history", _fake_visuals)

    context = asyncio.run(visual_memory.get_visual_memory_context(123, limit=5))

    assert context["limit"] == 5
    assert context["recent_scene_types"] == ["forest_path"]
    assert "beach" in context["recent_motifs"]
    assert "mug" in context["recent_motifs"]
    assert context["recent_selected_styles"] == ["soft_editorial"]
