"""Independent semantic oracle and ten Package A metamorphic property families."""

from itertools import permutations
import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from services import visual_intent as vi
from services.directive_segments import (
    DirectiveSource, Polarity, SourceKind, Span, segment_directives,
)
from services.visual_safety import resolve_visual_intent, check_interpretation, require_valid_interpretation
from services.visual_safety_types import VisualSafetyFailure


def assert_typed_conflict(interpretation, key, *, style='auto'):
    # SG-01 sections 4.3/5.1: interpretation stays pure, resolution owns conflicts.
    resolution = resolve_visual_intent(interpretation, requested_style=style)
    assert any(c.kind == 'object' and (vi.FactDomain.OBJECT, key) in c.keys
               and c.resolution == 'blocked' for c in resolution.conflicts)
    assert 'OBJECT_CONFLICT' in {i.code for i in check_interpretation(resolution).issues}
    with pytest.raises(VisualSafetyFailure, match='OBJECT_CONFLICT'):
        require_valid_interpretation(resolution)


# Explicitly authored canonical facts, not generated with either parser.
FACT_ORACLE = [
    ("No plants, wooden tables, and windows", set(), {"table", "window"}, set(), set()),
    ("No plants, small tables, and windows", set(), {"table", "window"}, set(), set()),
    ("No mugs, plants, and windows", set(), {"mug", "window"}, set(), set()),
    ("No plants, my notebook, and windows", set(), {"notebook", "window"}, set(), set()),
    ("Без растений, маленьких столов, и окон", set(), {"table", "window"}, set(), set()),
    ("No mugs, blue lanterns, windows", set(), {"mug", "window"}, set(), set()),
    ("No mugs, dark lanterns, and windows", set(), {"mug", "window"}, set(), set()),
    ("No beaches, oceans, and lagoons", set(), set(), set(), {"beach", "water", "lagoon"}),
    ("No plants, beaches, and oceans", set(), set(), set(), {"beach", "water"}),
    ("Без пляжа, моря, и лагун", set(), set(), set(), {"beach", "water", "lagoon"}),
    ("No sandy beach, beach", set(), set(), set(), {"sandy", "beach"}),
    ("Avoid people, show a mug", {"mug"}, {"human"}, set(), set()),
    ("Avoid people, and show a mug", {"mug"}, {"human"}, set(), set()),
    ("No mug and show a table", {"table"}, {"mug"}, set(), set()),
    ("Never show people; show a window", {"window"}, {"human"}, set(), set()),
    ("Do not show a mug. Show a notebook", {"notebook"}, {"mug"}, set(), set()),
    ("I do not want to show a mug", set(), {"mug"}, set(), set()),
    ("Do not ever include a table", set(), {"table"}, set(), set()),
    ("Never show people", set(), {"human"}, set(), set()),
    ("Море без пляжа", set(), set(), {"water"}, {"beach"}),
    ("Show rocky coast without beach", set(), set(), {"rocky"}, {"beach"}),
    ("Ocean view, no sandy beach", set(), set(), {"water"}, {"sandy"}),
    ("I want a tropical beach", set(), set(), {"beach"}, set()),
    ("Хочу океан и пальмы", set(), set(), {"water"}, set()),
    ("No people, ocean", set(), {"human"}, {"water"}, set()),
    ("No people, beach at sunset", set(), {"human"}, {"beach"}, set()),
    ("No people, windows", set(), {"human", "window"}, set(), set()),
    ("No people, ocean, windows", set(), {"human", "window"}, set(), {"water"}),
    ("No humans, ocean", set(), {"human"}, set(), {"water"}),
    ("No mugs, ocean", set(), {"mug"}, set(), {"water"}),
    ("No people, rocky coast", set(), {"human"}, set(), {"rocky"}),
    ("No people, lagoon", set(), {"human"}, set(), {"lagoon"}),
    ("No people, sea", set(), {"human"}, set(), {"water"}),
]


def assert_intent(result, required=(), excluded=(), coastal=(), excluded_coastal=()):
    assert result.required_objects == set(required)
    assert result.excluded_objects == set(excluded)
    assert result.positive_coastal == set(coastal)
    assert result.excluded_coastal == set(excluded_coastal)


@pytest.mark.parametrize("text,required,excluded,coastal,excluded_coastal", FACT_ORACLE)
@pytest.mark.parametrize("custom", [False, True])
def test_hand_authored_fact_oracle(text, required, excluded, coastal, excluded_coastal, custom):
    result = (vi.interpret_visual_intent(style="custom", custom_style_description=text) if custom
              else vi.interpret_visual_intent(text))
    assert_intent(result, required, excluded, coastal, excluded_coastal)


@pytest.mark.parametrize("text,ordinary,custom,excluded", [
    ("No people, a mug please", set(), {"mug"}, {"human"}),
    ("No people, just me and a mug", set(), {"mug"}, {"human"}),
    ("No people, show a mug", {"mug"}, {"mug"}, {"human"}),
    ("No people, windows", set(), set(), {"human", "window"}),
])
def test_source_distinctions(text, ordinary, custom, excluded):
    assert_intent(vi.interpret_visual_intent(text), ordinary, excluded)
    assert_intent(vi.interpret_visual_intent(style="custom", custom_style_description=text), custom, excluded)
    assert_intent(vi.interpret_visual_intent(style="auto", custom_style_description=text))
    assert "human" not in custom


@pytest.mark.parametrize("kind", list(SourceKind))
@pytest.mark.parametrize("active", [False, True])
def test_authority_is_explicit_per_source(kind, active):
    source = DirectiveSource("source-A", kind, "Show a mug; no windows; ocean", active)
    result = vi.interpret_directives((segment_directives(source),))
    authoritative = active and kind in {SourceKind.USER_TEXT, SourceKind.CUSTOM_NOTES}
    assert len(result.facts) == 3
    assert all(f.eligible == authoritative and f.source_id == "source-A" and f.source_kind == kind
               for f in result.facts)
    if authoritative:
        assert_intent(result, {"mug"}, {"window"}, {"water"})
    else:
        assert_intent(result)


def test_hand_authored_fact_provenance_and_eligibility():
    result = vi.interpret_visual_intent("No people, a mug please")
    assert [(f.key, f.polarity.value, f.span, f.source_id, f.directive_id, f.scope_id,
             f.eligible, f.basis.value) for f in result.facts] == [
        ("human", "negative", Span(3, 9), "user_text", 0, 0, True, "grammar"),
        ("mug", "unspecified", Span(13, 16), "user_text", 1, 0, False, "ambiguous"),
    ]
    custom = vi.interpret_visual_intent(style="custom", custom_style_description="No people, a mug please")
    assert [(f.key, f.polarity.value, f.span, f.source_id, f.directive_id, f.scope_id,
             f.eligible, f.basis.value) for f in custom.facts] == [
        ("human", "negative", Span(3, 9), "custom_notes", 0, 0, True, "grammar"),
        ("mug", "positive", Span(13, 16), "custom_notes", 1, 0, True, "custom_nominal"),
    ]


@pytest.mark.parametrize("text,key,span,basis", [
    ("No people, ocean", "water", Span(11, 16), "legacy_d1_a_ocean"),
    ("No people, beach at sunset", "beach", Span(11, 16), "legacy_d1_a_beach_sunset"),
])
def test_hand_authored_legacy_provenance(text, key, span, basis):
    result = vi.interpret_visual_intent(text)
    fact = next(f for f in result.facts if f.domain == vi.FactDomain.COASTAL)
    assert (fact.key, fact.span, fact.polarity.value, fact.eligible, fact.basis.value,
            fact.source_id, fact.scope_id, fact.directive_id) == (
        key, span, "positive", True, basis, "user_text", 0, 1,
    )
    assert not result.excluded_coastal
    assert result.segmentations[0].directives[1].polarity == Polarity.NEGATIVE


@pytest.mark.parametrize("text", [
    "I read about people and windows", "I do not want to discuss a mug",
    "I do not want to discuss how to show a mug", "I do not want a mug removed",
    "No time for my notebook", "Never discuss people at a table",
    "Never show people in my report", "Avoid people, to show a mug",
    "Avoid people, discuss how to show a mug", "Avoid people please show a mug",
    "If a person appears, give them natural hands", "research", "seasonal", "seated", "берегу себя",
    "tabletop, stable, windowsill, cupping, notebookish",
    "A report on a table", "A story about mugs and windows",
])
def test_unsupported_prose_never_acquires_positive_authority(text):
    result = vi.interpret_visual_intent(text)
    assert not result.required_objects and not result.positive_coastal


# Metamorphic 1/2: changing recognized vocabulary cannot change segmentation.
@pytest.mark.parametrize("opaque", ["plants", "glargs", "blue lanterns", "tiny violet flurbs"])
def test_metamorphic_vocabulary_independence_and_opaque_substitution(monkeypatch, opaque):
    source = DirectiveSource("s", SourceKind.USER_TEXT, f"No mugs, {opaque}, and windows")
    before = segment_directives(source)
    original = vi.interpret_directives((before,))
    monkeypatch.setattr(vi, "recognize_objects", lambda text: ())
    monkeypatch.setattr(vi, "recognize_coastal", lambda text: (
        vi.Recognition("invented", Span(0, len(text))),
    ))
    changed = vi.interpret_directives((before,))
    assert before == segment_directives(source) == changed.segmentations[0]
    assert changed.segmentations[0] is before
    assert_intent(original, excluded={"mug", "window"})
    assert not changed.required_objects and not changed.positive_coastal
    assert changed.excluded_coastal == {"invented"}
    assert all(d.polarity == Polarity.NEGATIVE and d.scope_id == 0 for d in before.directives)


# Metamorphic 3: arbitrary modifiers, without an adjective whitelist.
@pytest.mark.parametrize("modifier", ["", "wooden ", "small ", "my ", "ultraviolet ", "glargish ", "very oddly hued "])
@pytest.mark.parametrize("noun,key", [("tables", "table"), ("notebooks", "notebook"), ("windows", "window")])
def test_metamorphic_modifier_insertion(modifier, noun, key):
    phrase = modifier + noun
    assert_intent(vi.interpret_visual_intent("No plants, " + phrase), excluded={key})
    assert_intent(vi.interpret_visual_intent("Show " + phrase), required={key})


# Metamorphic 4/5: extension, reordering, conjunction/punctuation variants.
@pytest.mark.parametrize("members", list(permutations(["mugs", "blue lanterns", "windows"])))
@pytest.mark.parametrize("separator", [", ", " and ", " or ", ", and ", ", or "])
def test_metamorphic_list_extension_and_reordering(members, separator):
    text = "No " + separator.join(members)
    assert_intent(vi.interpret_visual_intent(text), excluded={"mug", "window"})
    assert_intent(vi.interpret_visual_intent(text + ", small tables"), excluded={"mug", "window", "table"})


@pytest.mark.parametrize("join", [" и ", " или ", ", и ", ", или ", ", "])
def test_metamorphic_russian_conjunctions(join):
    assert_intent(vi.interpret_visual_intent("Без " + join.join(["растений", "маленьких столов", "окон"])),
                  excluded={"table", "window"})


# Metamorphic 6: inserting a supported independent boundary restores positives.
@pytest.mark.parametrize("boundary", [", ", ", and ", " and ", "; ", ". ", "! ", "? ", "\n"])
@pytest.mark.parametrize("command", ["show", "include", "please show", "please include", "покажи", "хочу"])
def test_metamorphic_explicit_positive_boundary(boundary, command):
    assert_intent(vi.interpret_visual_intent("No mugs, dark lanterns" + boundary + command + " a table"),
                  required={"table"}, excluded={"mug"})


# Metamorphic 7: substituting a bounded negative predicate never opens positives.
@pytest.mark.parametrize("predicate", [
    "I do not want to", "I do not want you to", "Do not ever", "Never", "I would rather not",
])
@pytest.mark.parametrize("verb", ["show", "include"])
@pytest.mark.parametrize("object_phrase,key", [("a mug", "mug"), ("small tables", "table"), ("people", "human")])
def test_metamorphic_nested_negative_substitution(predicate, verb, object_phrase, key):
    assert_intent(vi.interpret_visual_intent(f"{predicate} {verb} {object_phrase}"), excluded={key})


# Metamorphic 8: canonical synonyms and cross-source facts share conflict rules.
@pytest.mark.parametrize("negative,positive,key", [
    ("mugs", "a cup", "mug"), ("small tables", "a table", "table"),
    ("windows", "a window", "window"), ("my notebook", "a notebook", "notebook"),
    ("people", "hands", "hands"), ("people", "a face", "body"),
])
@pytest.mark.parametrize("boundary", ["; ", ". ", ", and "])
def test_metamorphic_same_object_contradiction(negative, positive, key, boundary):
    assert_typed_conflict(vi.interpret_visual_intent("No " + negative + boundary + "Show " + positive), key)
    assert_typed_conflict(vi.interpret_visual_intent("No " + negative, style="custom",
                          custom_style_description="Show " + positive), key, style='custom')


# Metamorphic 9: source substitution changes eligibility, never structural scope.
@pytest.mark.parametrize("text", ["No people, a mug please", "No people, just me and a mug"])
def test_metamorphic_source_authority(text):
    user = segment_directives(DirectiveSource("same-id", SourceKind.USER_TEXT, text))
    notes = segment_directives(DirectiveSource("same-id", SourceKind.CUSTOM_NOTES, text))
    assert user.scopes == notes.scopes and user.directives == notes.directives
    assert_intent(vi.interpret_directives((user,)), excluded={"human"})
    assert_intent(vi.interpret_directives((notes,)), required={"mug"}, excluded={"human"})


# Metamorphic 10: the D1-A whitelist has exactly two complete spellings.
@pytest.mark.parametrize("text", [
    "No people, ocean", "NO PEOPLE, OCEAN!", "  No   people,   ocean. ",
    "No people, beach at sunset", "no PEOPLE,\tbeach at   sunset?",
])
@pytest.mark.parametrize("following", ["", "; show a mug", ". Show a mug", "! Show a mug", "\nShow a mug"])
@pytest.mark.parametrize("custom", [False, True])
def test_metamorphic_legacy_normalization_and_hard_boundary(text, following, custom):
    result = (vi.interpret_visual_intent(style="custom", custom_style_description=text + following) if custom
              else vi.interpret_visual_intent(text + following))
    assert result.positive_coastal == ({"water"} if "ocean" in text.casefold() else {"beach"})
    assert not result.excluded_coastal
    assert result.excluded_objects == {"human"}
    assert result.required_objects == ({"mug"} if following else set())
    coastal = [f for f in result.facts if f.domain == vi.FactDomain.COASTAL]
    assert len(coastal) == 1 and coastal[0].basis.value.startswith("legacy_d1_a_")


@pytest.mark.parametrize("text", [
    "No people, windows", "No people, ocean, windows", "No humans, ocean", "No mugs, ocean",
    "No people, rocky coast", "No people, lagoon", "No people, sea", "No beaches, oceans, and lagoons",
    "No people, oceans", "No people, blue ocean", "No people, ocean and windows",
    "No people, ocean, blue lanterns", "No people, beach at sunset, windows",
    "No people, beach at sunrise", "No people,ocean", "No people , ocean",
    "No people, and ocean", "Please no people, ocean", "No people, ocean please",
    "No people, beach at sunset and glargs", "No people, ocean, just me and a mug",
])
def test_metamorphic_closed_legacy_fences(text):
    result = vi.interpret_visual_intent(text)
    assert not result.positive_coastal
    assert all(not f.basis.value.startswith("legacy_d1_a_") for f in result.facts)


def test_legacy_override_does_not_erase_independent_exclusion():
    result = vi.interpret_visual_intent("No people, ocean; No ocean")
    coastal = [f for f in result.facts if f.domain == vi.FactDomain.COASTAL]
    assert [(f.polarity.value, f.basis.value, f.scope_id) for f in coastal] == [
        ("positive", "legacy_d1_a_ocean", 0), ("negative", "grammar", 1),
    ]


def test_duplicate_source_ids_rejected():
    source = segment_directives(DirectiveSource("duplicate", SourceKind.USER_TEXT, "ocean"))
    with pytest.raises(VisualSafetyFailure, match='INVALID_EVIDENCE'):
        vi.interpret_directives((source, source))


@pytest.mark.parametrize("text,conflict", [
    ("No plants, small tables, and windows; show a table", "table"),
    ("I do not want to show a mug. Show a cup", "mug"),
    ("Без растений, маленьких столов, и окон; покажи стол", "table"),
])
def test_hand_authored_contradiction_oracle(text, conflict):
    assert_typed_conflict(vi.interpret_visual_intent(text), conflict)


def test_bounded_grammar_declines_long_members_without_releasing_negative_scope():
    result = vi.interpret_visual_intent("No mugs, one two three four five six seven glargs, windows")
    assert_intent(result, excluded={"mug", "window"})
    middle = result.segmentations[0].directives[1]
    assert middle.polarity == Polarity.NEGATIVE and middle.kind.value == "ambiguous"


@pytest.mark.parametrize("text", ["No people, ocean", "No people, beach at sunset"])
@pytest.mark.parametrize("kind", [SourceKind.GENERATED_PROSE, SourceKind.SCENE_HINT,
                                  SourceKind.SOFT_AVOID, SourceKind.MEMORY_AVOID])
def test_legacy_compatibility_never_upgrades_source_authority(text, kind):
    result = vi.interpret_visual_intent(auxiliary_sources=(DirectiveSource("aux", kind, text),))
    assert_intent(result)
    assert result.facts and all(not f.eligible for f in result.facts)


@pytest.mark.parametrize("suffix", [", windows", ", blue lanterns", " and glargs"])
@pytest.mark.parametrize("following", ["", "; show a table", ". Show a table"])
def test_metamorphic_legacy_list_extension_before_hard_boundary(suffix, following):
    result = vi.interpret_visual_intent("No people, ocean" + suffix + following)
    assert not result.positive_coastal and result.excluded_coastal == {"water"}
    assert all(not f.basis.value.startswith("legacy_d1_a_") for f in result.facts)


def test_package_a_has_no_production_imports_or_provider_dependencies():
    root = Path(__file__).resolve().parents[1]
    modules = {"directive_segments", "visual_intent", "visual_safety", "visual_safety_types"}
    paths = list(root.glob("*.py"))
    for directory in ("services", "handlers", "keyboards"):
        paths.extend((root / directory).rglob("*.py"))
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        names = {name for node in imports for name in (
            [node.module or ''] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names])}
        names.update(a.name for node in imports if isinstance(node, ast.ImportFrom)
                     and node.module == 'services' for a in node.names)
        if path.stem == 'visual_semantics':
            assert names <= {'re'}  # neutral registry cannot import consumers
            continue
        if path.stem in modules:
            assert names <= {'dataclasses', 'enum', 're', 'typing', 'hashlib', 'json', 'services',
                             'services.visual_semantics', 'visual_semantics', *(f'services.{m}' for m in modules)}
        else:
            assert not any(name.split(".")[-1] in modules for name in names), path


# A-C1 semantic fixtures: expected constraints are not obtained from either parser.
@pytest.mark.parametrize("text,coastal", [
    ("No windows, no people, ocean", "water"),
    ("No windows and no people, ocean", "water"),
    ("No people, ocean, no windows", "water"),
    ("No people, ocean, and no windows", "water"),
    ("No windows, no people, beach at sunset", "beach"),
    ("No windows and no people, beach at sunset", "beach"),
    ("No people, beach at sunset, no windows", "beach"),
    ("No people, beach at sunset, and no windows", "beach"),
])
@pytest.mark.parametrize("custom", [False, True])
def test_c1_f_a1_reproductions(text, coastal, custom):
    result = (vi.interpret_visual_intent(style="custom", custom_style_description=text) if custom
              else vi.interpret_visual_intent(text))
    # A qualified negative outside the exact legacy chunk is local (SG-D1).
    # Its evidence remains, but no global beach ban can represent its meaning.
    assert_intent(result, excluded={"human", "window"}, excluded_coastal={coastal} if coastal == 'water' else ())
    if coastal == 'beach':
        assert any(n.detail == 'relational_scope' for n in result.unresolved_negatives)
    assert all(not f.basis.value.startswith("legacy_d1_a_") for f in result.facts)


@pytest.mark.parametrize("legacy,coastal,basis", [
    ("No people, ocean", "water", "legacy_d1_a_ocean"),
    ("No people, beach at sunset", "beach", "legacy_d1_a_beach_sunset"),
])
@pytest.mark.parametrize("boundary", ["; ", ". ", "! ", "? ", "\n", " but ", " но "])
@pytest.mark.parametrize("before,after,required,excluded", [
    ("", "show a notebook", {"notebook"}, {"human"}),
    ("", "no windows", set(), {"human", "window"}),
    ("No windows", "", set(), {"human", "window"}),
])
def test_c1_complete_legacy_instruction_at_hard_boundaries(
        legacy, coastal, basis, boundary, before, after, required, excluded):
    text = (before + boundary if before else "") + legacy + (boundary + after if after else "")
    result = vi.interpret_visual_intent(text)
    assert_intent(result, required=required, excluded=excluded, coastal={coastal})
    facts = [f for f in result.facts if f.domain == vi.FactDomain.COASTAL]
    assert len(facts) == 1
    assert facts[0].eligible and facts[0].basis.value == basis
    assert not result.positive_coastal & result.excluded_coastal
    assert all(d.polarity == Polarity.NEGATIVE for d in result.segmentations[0].directives
               if d.scope_id == facts[0].scope_id)


@pytest.mark.parametrize("subject,coastal", [("ocean", "water"), ("beach at sunset", "beach")])
@pytest.mark.parametrize("join", [", ", " and ", ", and ", " or ", ", or "])
@pytest.mark.parametrize("opaque", ["glargs", "blue lanterns", "tiny violet flurbs"])
@pytest.mark.parametrize("insertion", ["before", "after"])
def test_c1_metamorphic_repeated_negative_marker_insertion(subject, coastal, join, opaque, insertion):
    legacy = "No people, " + subject
    text = ("No " + opaque + join + legacy if insertion == "before"
            else legacy + join + "no " + opaque)
    result = vi.interpret_visual_intent(text)
    assert_intent(result, excluded={"human"}, excluded_coastal={coastal} if coastal == 'water' else ())
    if coastal == 'beach':
        assert any(n.detail == 'relational_scope' for n in result.unresolved_negatives)
    assert all(not f.basis.value.startswith("legacy_d1_a_") for f in result.facts)
    assert all(d.polarity == Polarity.NEGATIVE for d in result.segmentations[0].directives)


@pytest.mark.parametrize("legacy,coastal", [
    ("No people, ocean", "water"), ("No people, beach at sunset", "beach"),
])
@pytest.mark.parametrize("prefix,suffix,required", [
    ("", ", windows", set()),
    ("", ", show a table", {"table"}),
    ("Show a table, ", "", {"table"}),
    (",", "", set()),
    (":", "", set()),
    ("", ",", set()),
])
def test_c1_legacy_requires_complete_hard_chunk(legacy, coastal, prefix, suffix, required):
    result = vi.interpret_visual_intent(prefix + legacy + suffix)
    if prefix == ":":
        # A colon is not a supported command introducer; decline the whole prose.
        assert_intent(result)
    else:
        assert_intent(result, required=required,
                      excluded={"human", "window"} if suffix == ", windows" else {"human"},
                      excluded_coastal={coastal} if coastal == 'water' else ())
        if coastal == 'beach':
            assert any(n.detail == 'relational_scope' for n in result.unresolved_negatives)
    assert all(not f.basis.value.startswith("legacy_d1_a_") for f in result.facts)


@pytest.mark.parametrize("text", [
    "I want a report about mugs and windows",
    "I want to read about people and windows",
    "Show a story about mugs and windows",
    "I want a report on tables and windows",
    "No report about mugs and windows",
    "No time for my notebook and windows",
    "Never show people in my report and windows",
    "No report about mugs, a window please",
])
@pytest.mark.parametrize("custom", [False, True])
def test_c1_narrative_siblings_never_become_visual_requests_or_bans(text, custom):
    result = (vi.interpret_visual_intent(style="custom", custom_style_description=text) if custom
              else vi.interpret_visual_intent(text))
    assert_intent(result)
    assert result.facts and all(not f.eligible and f.basis == vi.FactBasis.AMBIGUOUS for f in result.facts)


@pytest.mark.parametrize("text,required,coastal", [
    ("Show a mug and a notebook", {"mug", "notebook"}, set()),
    ("Show a mug, a table, and a window", {"mug", "table", "window"}, set()),
    ("I want an ocean view", set(), {"water"}),
    ("Show a notebook; include a window", {"notebook", "window"}, set()),
    ("I want a report about mugs and windows; show a table", {"table"}, set()),
    ("Show a story about mugs and windows. Show a notebook", {"notebook"}, set()),
    ("I want a report about mugs and windows, show a table", {"table"}, set()),
    ("No report about mugs and windows, show a table", {"table"}, set()),
    ("No time for my notebook and windows; include a window", {"window"}, set()),
])
def test_c1_supported_visual_commands_survive(text, required, coastal):
    result = vi.interpret_visual_intent(text)
    assert_intent(result, required=required, coastal=coastal)
    assert all(f.basis == vi.FactBasis.GRAMMAR for f in result.facts if f.eligible)


@pytest.mark.parametrize("command", ["I want", "Show", "No", "Never show"])
@pytest.mark.parametrize("insertion", [
    "a report about glargs and ",
    "a story on blue lanterns, ",
    "a report about glargs, a discussion about flurbs, and ",
])
@pytest.mark.parametrize("tail", ["windows", "ocean", "a mug and a table"])
def test_c1_metamorphic_unsupported_narrative_member_insertion(command, insertion, tail):
    for members in (insertion + tail, tail + " and " + insertion.rstrip(" ,")):
        result = vi.interpret_visual_intent(command + " " + members)
        assert_intent(result)
        assert all(not f.eligible for f in result.facts)


@pytest.mark.parametrize("noun,domain,key", [
    ("mug", vi.FactDomain.OBJECT, "mug"),
    ("table", vi.FactDomain.OBJECT, "table"),
    ("beach", vi.FactDomain.COASTAL, "beach"),
])
def test_c1_custom_polite_nominals_follow_general_source_policy(noun, domain, key):
    text = "No people, a " + noun + " please"
    user = vi.interpret_visual_intent(text)
    custom = vi.interpret_visual_intent(style="custom", custom_style_description=text)
    assert_intent(user, excluded={"human"})
    assert_intent(custom, required={key} if domain == vi.FactDomain.OBJECT else set(),
                  excluded={"human"}, coastal={key} if domain == vi.FactDomain.COASTAL else set())
    fact = next(f for f in custom.facts if f.key == key)
    assert fact.basis == vi.FactBasis.CUSTOM_NOMINAL and fact.source_kind == SourceKind.CUSTOM_NOTES
    assert not any(f.basis.value.startswith("legacy_d1_a_") for f in custom.facts)


def test_c1_custom_eligibility_does_not_consult_subject_vocabulary(monkeypatch):
    monkeypatch.setattr(vi, "recognize_objects", lambda text: (
        (vi.Recognition("flurb", Span(2, 7)),) if text == "a flurb please" else ()
    ))
    assert_intent(vi.interpret_visual_intent("No glargs, a flurb please"))
    result = vi.interpret_visual_intent(style="custom", custom_style_description="No glargs, a flurb please")
    assert_intent(result, required={"flurb"})
    assert result.facts[0].basis == vi.FactBasis.CUSTOM_NOMINAL


@pytest.mark.parametrize("noun,domain,key", [
    ("tables", vi.FactDomain.OBJECT, "table"),
    ("windows", vi.FactDomain.OBJECT, "window"),
    ("beaches", vi.FactDomain.COASTAL, "beach"),
    ("oceans", vi.FactDomain.COASTAL, "water"),
])
@pytest.mark.parametrize("suffix", ["", " in the image"])
def test_c1_six_word_limit_retains_unresolved_exclusion(noun, domain, key, suffix):
    six_words = "tiny old bright polished wooden " + noun + suffix
    assert vi.interpret_visual_intent("No " + six_words).facts[0].eligible
    seven_words = "unusually " + six_words
    text = "No " + seven_words + ", notebooks"
    result = vi.interpret_visual_intent(text)
    assert_intent(result, excluded={"notebook"})
    segmented = result.segmentations[0]
    scope, directive = segmented.scopes[0], segmented.directives[0]
    assert scope.polarity == directive.polarity == Polarity.NEGATIVE
    assert scope.span.extract(text) == text
    assert scope.marker_span.extract(text) == "No"
    assert directive.span.extract(text) == seven_words
    assert directive.kind.value == "ambiguous"
    fact = next(f for f in result.facts if f.domain == domain and f.key == key)
    assert fact.polarity == Polarity.NEGATIVE and not fact.eligible
    assert fact.basis == vi.FactBasis.AMBIGUOUS and fact.span.extract(text) == noun
    assert fact.source_id == "user_text" and fact.scope_id == fact.directive_id == 0
    verdict = check_interpretation(resolve_visual_intent(result))
    assert verdict.outcome == 'blocked'
    assert [(i.code, i.detail) for i in verdict.issues] == [('UNRESOLVED_EXCLUSION', 'unsupported_structure')]


def test_c1_length_ambiguity_is_local_but_unresolved_exclusion_blocks():
    text = "No unusually tiny old bright polished wooden tables; show a table and windows"
    result = vi.interpret_visual_intent(text)
    # Evidence projections preserve +table; the verdict still blocks on the ban.
    assert_intent(result, required={"table", "window"})
    assert [(f.key, f.polarity.value, f.eligible, f.basis.value) for f in result.facts] == [
        ("table", "negative", False, "ambiguous"),
        ("table", "positive", True, "grammar"),
        ("window", "positive", True, "grammar"),
    ]
    verdict = check_interpretation(resolve_visual_intent(result))
    assert [(i.code, i.detail) for i in verdict.issues] == [('UNRESOLVED_EXCLUSION', 'unsupported_structure')]
    assert_typed_conflict(vi.interpret_visual_intent("No tiny old bright polished wooden tables; show a table"), 'table')


@pytest.mark.parametrize("text", ["No windows, no people, ocean", "I want a report about mugs and windows"])
def test_c1_corrected_facts_and_context_are_immutable(text):
    result = vi.interpret_visual_intent(text)
    with pytest.raises(FrozenInstanceError):
        result.facts[-1].eligible = True
    with pytest.raises(FrozenInstanceError):
        result.segmentations[0].scopes[0].chunk_span.end = 0
    assert result.segmentations[0].source.text == text
