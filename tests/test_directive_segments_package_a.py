"""Hand-authored Package A structural oracle; no production parser oracle."""

from dataclasses import FrozenInstanceError

import pytest

from services.directive_segments import (
    DirectiveSource, SourceKind, segment_directives,
)


# All offsets, kinds and scope identities below are specified independently.
STRUCTURAL_ORACLE = [
    (
        "No plants, wooden tables, and windows",
        [(0, 37, (0, 2), "negative", "negative_command")],
        [(3, 9, 0, "negative", "negative_command"),
         (11, 24, 0, "negative", "negative_list_member"),
         (30, 37, 0, "negative", "negative_list_member")],
    ),
    (
        "No mugs; show a table",
        [(0, 7, (0, 2), "negative", "negative_command"),
         (9, 21, (9, 13), "positive", "positive_command")],
        [(3, 7, 0, "negative", "negative_command"),
         (14, 21, 1, "positive", "positive_command")],
    ),
    (
        "I do not want to show a mug",
        [(0, 27, (0, 21), "negative", "nested_negative")],
        [(22, 27, 0, "negative", "nested_negative")],
    ),
    (
        "No people, a mug please",
        [(0, 23, (0, 2), "negative", "negative_command")],
        [(3, 9, 0, "negative", "negative_command"),
         (11, 23, 0, "unspecified", "ambiguous")],
    ),
    (
        "Море без пляжа",
        [(0, 4, None, "unspecified", "nominal"),
         (5, 14, (5, 8), "negative", "negative_command")],
        [(0, 4, 0, "unspecified", "nominal"),
         (9, 14, 1, "negative", "negative_command")],
    ),
    (
        "No people, ocean",
        [(0, 16, (0, 2), "negative", "negative_command")],
        [(3, 9, 0, "negative", "negative_command"),
         (11, 16, 0, "negative", "negative_list_member")],
    ),
]


@pytest.mark.parametrize("text,scopes,directives", STRUCTURAL_ORACLE)
def test_hand_authored_structural_oracle(text, scopes, directives):
    source = DirectiveSource("request-7", SourceKind.USER_TEXT, text)
    result = segment_directives(source)
    assert result.source is source
    assert [(s.span.start, s.span.end,
             (s.marker_span.start, s.marker_span.end) if s.marker_span else None,
             s.polarity.value, s.kind.value) for s in result.scopes] == scopes
    assert [(d.span.start, d.span.end, d.scope_id, d.polarity.value, d.kind.value)
            for d in result.directives] == directives
    assert [d.directive_id for d in result.directives] == list(range(len(directives)))
    assert [s.scope_id for s in result.scopes] == list(range(len(scopes)))
    assert all(d.source_id == "request-7" for d in result.directives)
    assert all(s.source_id == "request-7" for s in result.scopes)
    assert all(result.scopes[d.scope_id].span.start <= d.span.start < d.span.end
               <= result.scopes[d.scope_id].span.end for d in result.directives)


@pytest.mark.parametrize("text,items", [
    ("No plants, small tables, and windows", ["plants", "small tables", "windows"]),
    ("No mugs, plants, and windows", ["mugs", "plants", "windows"]),
    ("No plants, my notebook, and windows", ["plants", "my notebook", "windows"]),
    ("Без растений, маленьких столов, и окон", ["растений", "маленьких столов", "окон"]),
    ("No mugs, blue lanterns, windows", ["mugs", "blue lanterns", "windows"]),
    ("No mugs, dark lanterns, and windows", ["mugs", "dark lanterns", "windows"]),
    ("No beaches, oceans, and lagoons", ["beaches", "oceans", "lagoons"]),
    ("No plants, beaches, and oceans", ["plants", "beaches", "oceans"]),
    ("Без пляжа, моря, и лагун", ["пляжа", "моря", "лагун"]),
    ("No sandy beach, beach", ["sandy beach", "beach"]),
])
def test_f1_lists_have_one_negative_scope(text, items):
    result = segment_directives(DirectiveSource("s", SourceKind.USER_TEXT, text))
    assert len(result.scopes) == 1
    assert [d.span.extract(text) for d in result.directives] == items
    assert all(d.polarity.value == "negative" and d.scope_id == 0 for d in result.directives)


@pytest.mark.parametrize("text,negative,positive", [
    ("Avoid people, show a mug", ["people"], ["a mug"]),
    ("Avoid people, and show a mug", ["people"], ["a mug"]),
    ("No mug and show a table", ["mug"], ["a table"]),
    ("Never show people; show a window", ["people"], ["a window"]),
    ("Do not show a mug. Show a notebook", ["a mug"], ["a notebook"]),
    ("No plants, small tables, and windows; show a table",
     ["plants", "small tables", "windows"], ["a table"]),
])
def test_positive_boundaries(text, negative, positive):
    result = segment_directives(DirectiveSource("s", SourceKind.USER_TEXT, text))
    assert [d.span.extract(text) for d in result.directives if d.polarity.value == "negative"] == negative
    assert [d.span.extract(text) for d in result.directives if d.polarity.value == "positive"] == positive
    assert len(result.scopes) == 2


@pytest.mark.parametrize("text", [
    "I do not want to show a mug", "Do not ever include a table", "Never show people",
    "I do not want you to show a table", "I would rather not show a window",
])
def test_nested_predicates_are_one_negative_scope(text):
    result = segment_directives(DirectiveSource("s", SourceKind.USER_TEXT, text))
    assert len(result.scopes) == len(result.directives) == 1
    assert result.scopes[0].kind.value == "nested_negative"
    assert result.directives[0].polarity.value == "negative"


def test_structure_is_immutable_and_source_specific():
    source = DirectiveSource("notes", SourceKind.CUSTOM_NOTES, "No mugs, small tables", active=False)
    result = segment_directives(source)
    with pytest.raises(FrozenInstanceError):
        result.directives[0].scope_id = 9
    with pytest.raises(FrozenInstanceError):
        result.source.active = True
    assert result.source == source
    assert result.directives[1].span.extract(source.text) == "small tables"


@pytest.mark.parametrize("boundary", ["; ", ". ", "! ", "? ", "\n", " but ", " но "])
def test_hard_boundary_resets_to_unspecified_nominal(boundary):
    text = "No glargs" + boundary + "a plimp"
    result = segment_directives(DirectiveSource("s", SourceKind.USER_TEXT, text))
    assert [s.polarity.value for s in result.scopes] == ["negative", "unspecified"]
    assert [d.span.extract(text) for d in result.directives] == ["glargs", "a plimp"]


# A-C1: offsets and meanings are authored independently of the implementation.
@pytest.mark.parametrize("text,scopes,directives", [
    (
        "No windows, no people, ocean",
        [(0, 10, (0, 2), "negative", "negative_command"),
         (12, 28, (12, 14), "negative", "negative_command")],
        [(3, 10, 0, "negative", "negative_command"),
         (15, 21, 1, "negative", "negative_command"),
         (23, 28, 1, "negative", "negative_list_member")],
    ),
    (
        "I want a report about mugs and windows",
        [(0, 38, (0, 6), "positive", "ambiguous")],
        [(7, 26, 0, "positive", "ambiguous"),
         (31, 38, 0, "positive", "ambiguous")],
    ),
    (
        "No report about mugs and windows",
        [(0, 32, (0, 2), "negative", "ambiguous")],
        [(3, 20, 0, "negative", "ambiguous"),
         (25, 32, 0, "negative", "ambiguous")],
    ),
    (
        "Show a b c d e f mugs and windows",
        [(0, 33, (0, 4), "positive", "positive_command")],
        [(5, 21, 0, "positive", "ambiguous"),
         (26, 33, 0, "positive", "positive_command")],
    ),
    (
        "No a b c d e f mugs and windows",
        [(0, 31, (0, 2), "negative", "negative_command")],
        [(3, 19, 0, "negative", "ambiguous"),
         (24, 31, 0, "negative", "negative_list_member")],
    ),
])
def test_c1_structural_oracle(text, scopes, directives):
    test_hand_authored_structural_oracle(text, scopes, directives)


@pytest.mark.parametrize("text,scope_texts,chunk_texts", [
    ("No windows, no people, ocean",
     ["No windows", "no people, ocean"], ["No windows, no people, ocean"] * 2),
    ("No people, ocean, and no windows",
     ["No people, ocean", "no windows"], ["No people, ocean, and no windows"] * 2),
    ("No windows; No people, ocean",
     ["No windows", "No people, ocean"], ["No windows", " No people, ocean"]),
    ("No people, ocean, show a table",
     ["No people, ocean", "show a table"], ["No people, ocean, show a table"] * 2),
])
def test_c1_scopes_retain_enclosing_hard_chunk(text, scope_texts, chunk_texts):
    result = segment_directives(DirectiveSource("s", SourceKind.USER_TEXT, text))
    assert [s.span.extract(text) for s in result.scopes] == scope_texts
    assert [s.chunk_span.extract(text) for s in result.scopes] == chunk_texts
    assert all(s.chunk_span.start <= s.span.start <= s.span.end <= s.chunk_span.end
               for s in result.scopes)
    with pytest.raises(FrozenInstanceError):
        result.scopes[0].chunk_span = result.scopes[-1].span


@pytest.mark.parametrize("command", ["I want", "Show", "No", "Never show", ""])
@pytest.mark.parametrize("members", [
    "a report about glargs and windows",
    "windows and a report about glargs",
    "windows, a report on glargs, tables",
])
def test_c1_narrative_function_blocks_all_siblings(command, members):
    text = (command + " " + members).strip()
    result = segment_directives(DirectiveSource("s", SourceKind.USER_TEXT, text))
    assert len(result.scopes) == 1
    assert result.scopes[0].kind.value == "ambiguous"
    assert all(d.kind.value == "ambiguous" and d.scope_id == 0 for d in result.directives)


@pytest.mark.parametrize("boundary", ["; ", ". ", ", ", " and ", ", and "])
def test_c1_independent_command_ends_narrative_ambiguity(boundary):
    text = "I want a report about mugs and windows" + boundary + "show a table"
    result = segment_directives(DirectiveSource("s", SourceKind.USER_TEXT, text))
    assert [s.kind.value for s in result.scopes] == ["ambiguous", "positive_command"]
    assert [(d.span.extract(text), d.scope_id, d.kind.value) for d in result.directives] == [
        ("a report about mugs", 0, "ambiguous"),
        ("windows", 0, "ambiguous"),
        ("a table", 1, "positive_command"),
    ]
