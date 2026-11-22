"""Bounded object constraints shared by the existing deterministic builders.

Only current user text/custom notes can supply authoritative instructions.
Generated scene prose is inspected for compatibility, never for user intent.
This vocabulary deliberately does not attempt general semantic classification.
"""

import re


_NOUNS = {
    "mug": r"mugs?|cups?|кружек|чашек|кружк(?:а|и|у|ой|е|ами|ах)?|чашк(?:а|и|у|ой|е|ами|ах)?",
    "table": r"tables?|стол(?:ы|а|у|ом|е|ов|ами|ах)?",
    "notebook": r"notebooks?|блокнот(?:ы|а|у|ом|е|ов|ами|ах)?|тетрад(?:ь|и|ью|ей|ями|ях)",
    "window": r"windows?|окн(?:о|а|у|ом|е|ами|ах)|окон",
    "body": r"(?:human\s+)?body\s+parts?|arms?|legs?|feet|foot|faces?|ног(?:а|и|у|ой|е|ами|ах)?|лиц(?:о|а|у|ом|е)?",
    "human": r"human\s+presence|persons?|people|humans?|guests?|(?:distant|seated)\s+figures?|pedestrians?|человек(?:а|у|ом|е)?|люд(?:и|ей|ям|ьми|ях)|гост(?:и|ей|ям|ями|ях)",
    "hands": r"hands?|рук(?:а|и|у|ой|е|ами|ах)?",
}
_OBJECT = re.compile(r"\b(?:" + "|".join(f"(?P<{key}>{value})" for key, value in _NOUNS.items()) + r")\b", re.I)
_MARKER = re.compile(
    # Consume a conjunction only when it joins explicit instruction markers;
    # otherwise it stays within the nominal object list.
    r"(?:\b(?:and|or|и|или)\s+(?:please\s+)?)?(?:"
    r"(?P<negative>\b(?:(?:i\s+)?(?:do\s+not|don['’]t)(?:\s+(?:show|include|want))?|"
    r"i(?:['’]d|\s+would)\s+rather\s+not\s+have|"
    r"avoid|no|without|exclude|excluding|never|not|rather\s+than|instead\s+of|"
    r"без|не\s+хочу(?:\s+видеть)?|не\s+показывай(?:те)?|избегай(?:те)?|исключи(?:те)?)\b)"
    r"|(?P<positive>\b(?:show|include|i\s+want|хочу|покажи(?:те)?|изобрази(?:те)?)\b))"
    r"|(?P<comma>,)|(?P<reset>[.;!?\n]+|\b(?:but|но)\b)", re.I,
)
_NOMINAL_PREFIX = (
    r"^(?:(?:no|avoid|without|exclude|excluding|без)\s+)?"
    r"(?:(?:a|an|the|coffee|tea|ceramic|visible|any|more)\s+)*"
)
_NOMINAL_SUFFIX = r"(?:\s+(?:anywhere|at all|in the (?:image|frame)|whatsoever|please|either))?$"
_ATOM = re.compile(_NOMINAL_PREFIX + "(?:" + "|".join(_NOUNS.values()) + ")" + _NOMINAL_SUFFIX, re.I)
_BARE_SCENE = re.compile(
    r"^(?:(?:a|an|the|one|two|warm|open|small|ceramic|coffee|tea|visible)\s+)*(?:"
    + "|".join(_NOUNS.values()) + r")\b(?:\s+(?:on|by|beside|with|in|на|у|с)\b.*)?$", re.I,
)
# Only these bounded links can connect a negative predicate to a visual verb.
_PREDICATE_LINK = re.compile(r"^(?:ever|(?:you\s+)?to)?$", re.I)
_LEADING_COORDINATOR = re.compile(r"^\s*(?:and|or|и|или)\s+", re.I)
# An unsupported word can carry scope with the same bounded modifiers as a
# known noun. This pattern never extracts or adds canonical object names.
_OPAQUE_LIST_ATOM = re.compile(_NOMINAL_PREFIX + r"[^\W\d_]+(?:-[^\W\d_]+)*" + _NOMINAL_SUFFIX, re.I)
_LABELS = {"mug": "mugs or cups", "table": "tables", "notebook": "notebooks",
           "window": "windows", "human": "people or human presence",
           "hands": "hands", "body": "visible human body parts"}


def _nominal_list_fragment(clause: str) -> bool:
    clause = _LEADING_COORDINATOR.sub("", clause, count=1)
    return bool(clause) and all(
        _ATOM.fullmatch(atom) or _OPAQUE_LIST_ATOM.fullmatch(atom)
        for atom in re.split(r"\s+(?:and|or|и|или)\s+", clause)
    )


def _continues_exclusion_list(text: str, start: int) -> bool:
    next_marker = _MARKER.search(text, start)
    clause = text[start:next_marker.start() if next_marker else len(text)].strip()
    clause = _LEADING_COORDINATOR.sub("", clause, count=1)
    # A fresh article-led phrase is ambiguous, not an implicit object ban.
    # Explicit repeated markers are processed separately by _fragments.
    return not re.match(r"(?:a|an|the)\s+", clause, re.I) and _nominal_list_fragment(clause)


def _fragments(text: str):
    start, negative, explicit, negative_list = 0, False, False, False
    after_comma = False
    for marker in _MARKER.finditer(text):
        fragment = text[start:marker.start()].strip(" ,:\t")
        kind = marker.lastgroup
        # A comma can keep a negative nominal list open without governing a
        # fresh explicit directive. Only the bounded polite prefix may intervene.
        directive_boundary = after_comma and fragment.lower() in {"", "please"}
        after_comma = kind == "comma"
        if (kind == "positive" and negative and marker.group(kind).lower() in {"show", "include"}
                and marker.start(kind) == marker.start() and not directive_boundary):
            # Without a clause boundary or coordinating conjunction, the verb
            # belongs to the negative predicate, not a new positive directive.
            if _PREDICATE_LINK.fullmatch(fragment):
                start = marker.end()
            # Retain unknown intervening prose so nominal matching rejects it.
            continue
        if fragment:
            yield fragment, negative, explicit
        if kind in {"negative", "positive"}:
            negative, explicit = kind == "negative", True
            negative_list = negative and marker.group(kind).lower() in {"avoid", "exclude", "excluding", "избегай", "избегайте", "исключи", "исключите"}
        elif kind == "reset":
            negative, explicit, negative_list = False, False, False
        elif negative and not negative_list:
            # No/without/без continue only bounded nominal lists; explicit
            # avoid/exclude lists retain their existing open-list semantics.
            # Scope depends on list structure, never on object recognition.
            if not _nominal_list_fragment(fragment) or not _continues_exclusion_list(text, marker.end()):
                negative, explicit, negative_list = False, False, False
        elif not negative and not _OBJECT.search(fragment):
            explicit = False
        start = marker.end()
        if kind == "comma" and negative and _continues_exclusion_list(text, start):
            # Skip an Oxford-comma coordinator only for a bounded nominal list.
            # Explicit directives remain intact for the next marker iteration.
            if coordinator := _LEADING_COORDINATOR.match(text[start:]):
                start += coordinator.end()
    if tail := text[start:].strip(" ,:\t"):
        yield tail, negative, explicit


def positive_objects(text: str | None) -> set[str]:
    # The existing anatomy safeguard is conditional, not a request to add a
    # person or visible limbs. Keep its sentence outside required subjects.
    unconditional = ". ".join(sentence for sentence in re.split(r"[.!?\n]+", text or "")
                              if not re.match(r"\s*if a person appears\b", sentence, re.I))
    return {m.lastgroup for fragment, negative, _ in _fragments(unconditional)
            if not negative for m in _OBJECT.finditer(fragment.replace("_", " "))}


def forbidden_objects(exclusions) -> set[str]:
    result = set(exclusions)
    if "human" in result:
        result.update({"hands", "body"})
    return result


def user_visual_constraints(user_text=None, *, style=None, custom_style_description=None):
    positive, negative = set(), set()
    for custom_source, source in ((False, user_text), (True, custom_style_description if style == "custom" else None)):
        for fragment, excluded, explicit in _fragments(source or ""):
            # Plain isolated object names are requests; incidental narrative is not.
            if excluded:
                # Only nominal object bans are global exclusions. A passing
                # noun in 'no time for my notebook' is not a visual prohibition.
                atoms = re.split(r"\s+(?:and|or|и|или)\s+", fragment)
                negative.update(m.lastgroup for atom in atoms if _ATOM.fullmatch(atom)
                                for m in _OBJECT.finditer(atom))
                continue
            if not explicit and not custom_source and not _BARE_SCENE.fullmatch(fragment):
                continue
            positive.update(m.lastgroup for m in _OBJECT.finditer(fragment))
    conflict = positive & forbidden_objects(negative)
    if conflict:
        raise ValueError("Unresolved explicit visual conflict: " + ", ".join(sorted(conflict)))
    return positive, negative


def exclusion_items(exclusions) -> list[str]:
    return ["no " + _LABELS[key] for key in sorted(exclusions)]


def avoid_fragments(item: str) -> list[str]:
    return re.split(r"\s*[,;]\s*|\s+(?:and|or|и|или)\s+", item)


def suppress_soft_avoids(items, required, *, forbidden=()) -> list[str]:
    """Remove only complete bounded object bans; retain qualified anti-cliches."""
    result = []
    for item in items:
        # Avoiding 'no people anywhere' is itself a request for people.
        if "human" in forbidden and item.lower() in {"no people anywhere", "avoid no people anywhere"}:
            continue
        atoms = avoid_fragments(item)
        retained = [atom for atom in atoms if not (
            _ATOM.fullmatch(atom) and positive_objects(_MARKER.sub("", atom)) & set(required)
        )]
        # Keep qualified prose byte-for-byte unless a complete bounded ban was
        # actually removed; unknown list members retain their original wording.
        for atom in retained if len(retained) != len(atoms) else [item]:
            if atom and atom not in result:
                result.append(atom)
    return result


def compatible_generated_hints(items, forbidden) -> list[str]:
    """Discard optional generated recommendations as units, never rewrite nouns."""
    return [item for item in items if not positive_objects(item) & set(forbidden)
            and not ("human" in forbidden and item.lower() in {"avoid no people anywhere", "no people anywhere"})]


def compatible_custom_style_prose(prose: str, forbidden) -> str:
    """Reconcile coastal-scoped prose with authoritative object exclusions.

    Filter the original fragments separately so independent requests survive.
    The coastal scoper can also leave a coordinator before an explicit directive;
    it carries no visual intent once its neighbouring list members are removed.
    Callers validate genuine user conflicts before rendering this prose.
    """
    fragments = compatible_generated_hints(prose.split("; "), forbidden)
    return "; ".join(
        _LEADING_COORDINATOR.sub("", fragment, count=1)
        for fragment in fragments if fragment.lower() not in {"and", "or", "и", "или"}
    )


def compatible_style_phrase(phrase: str, forbidden) -> str:
    # Existing descriptions contain comma-separated optional object examples.
    # Keep the style's identity clause, suppress conflicting example clauses.
    clauses = phrase.split(", ")
    if positive_objects(clauses[0]) & set(forbidden):
        raise ValueError("Selected style conflicts with explicit visual exclusions")
    return ", ".join(compatible_generated_hints(clauses, forbidden))
