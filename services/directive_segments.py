"""Isolated Package A grammar. No production caller uses this module yet.

Offsets are half-open Python string offsets into the unmodified source. Scope
owns a complete command/list; directives own its individual nominal members.
Neither segmentation nor nominal classification consults a subject vocabulary.
Unsupported prose retains its scope but is marked ambiguous, never promoted.
"""

from dataclasses import dataclass
from enum import Enum
import re
from typing import Literal

from services.visual_safety_types import immutable_tuple, invalid_evidence

Frame = Literal['nominal', 'render_complement', 'conditional', 'unknown']
Attachment = Literal['frame_level', 'head_local', 'uncertain']


class SourceKind(str, Enum):
    USER_TEXT = "user_text"
    CUSTOM_NOTES = "custom_notes"
    GENERATED_PROSE = "generated_prose"
    SCENE_HINT = "scene_hint"
    SOFT_AVOID = "soft_avoid"
    MEMORY_AVOID = "memory_avoid"


class Polarity(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNSPECIFIED = "unspecified"


class DirectiveKind(str, Enum):
    POSITIVE_COMMAND = "positive_command"
    NEGATIVE_COMMAND = "negative_command"
    NESTED_NEGATIVE = "nested_negative"
    NEGATIVE_LIST_MEMBER = "negative_list_member"
    NOMINAL = "nominal"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class Span:
    start: int
    end: int

    def __post_init__(self):
        if type(self.start) is not int or type(self.end) is not int or not 0 <= self.start <= self.end:
            invalid_evidence()

    def extract(self, text: str) -> str:
        return text[self.start:self.end]


@dataclass(frozen=True, slots=True)
class DirectiveSource:
    source_id: str
    kind: SourceKind
    text: str
    active: bool = True

    def __post_init__(self):
        if (not isinstance(self.source_id, str) or not self.source_id or not isinstance(self.kind, SourceKind)
                or not isinstance(self.text, str) or type(self.active) is not bool):
            invalid_evidence()


@dataclass(frozen=True, slots=True)
class Scope:
    source_id: str
    scope_id: int
    span: Span
    marker_span: Span | None
    polarity: Polarity
    kind: DirectiveKind
    chunk_span: Span


@dataclass(frozen=True, slots=True)
class Directive:
    source_id: str
    directive_id: int
    scope_id: int
    span: Span
    polarity: Polarity
    kind: DirectiveKind


@dataclass(frozen=True, slots=True)
class SegmentedSource:
    source: DirectiveSource
    scopes: tuple[Scope, ...]
    directives: tuple[Directive, ...]
    structure: tuple['DirectiveStructure', ...]

    def __post_init__(self):
        validate_structure(self)


@dataclass(frozen=True, slots=True)
class RelationEvidence:
    marker_span: Span
    dependent_span: Span
    dependent_directive_ids: tuple[int, ...]
    attachment: Attachment

    def __post_init__(self):
        immutable_tuple(self.dependent_directive_ids)
        if self.attachment not in Attachment.__args__:
            invalid_evidence()


@dataclass(frozen=True, slots=True)
class DirectiveStructure:
    directive_id: int
    frame: Frame
    head_span: Span | None
    nominal_span: Span | None
    qualifier_spans: tuple[Span, ...]
    relations: tuple[RelationEvidence, ...]
    governing_directive_id: int | None
    uncertain: bool

    def __post_init__(self):
        immutable_tuple(self.qualifier_spans)
        immutable_tuple(self.relations)
        if self.frame not in Frame.__args__ or type(self.uncertain) is not bool:
            invalid_evidence()


def validate_structure(segmented: SegmentedSource) -> None:
    """Check local identities, original offsets and the single governing graph."""
    if not isinstance(segmented, SegmentedSource) or not isinstance(segmented.source, DirectiveSource):
        invalid_evidence()
    source = segmented.source
    for items in (segmented.scopes, segmented.directives, segmented.structure):
        immutable_tuple(items)
    # Validate record types before field access, including forward graph links.
    if (any(not isinstance(s, Scope) for s in segmented.scopes)
            or any(not isinstance(d, Directive) for d in segmented.directives)
            or any(not isinstance(s, DirectiveStructure) for s in segmented.structure)):
        invalid_evidence()
    if (not isinstance(source.source_id, str) or not source.source_id
            or not isinstance(source.kind, SourceKind) or type(source.active) is not bool
            or not isinstance(source.text, str)):
        invalid_evidence()

    def inside(span, owner):
        if (not isinstance(span, Span) or type(span.start) is not int or type(span.end) is not int
                or not owner.start <= span.start < span.end <= owner.end):
            invalid_evidence()

    whole = Span(0, len(source.text))
    for index, scope in enumerate(segmented.scopes):
        if (scope.source_id != source.source_id or type(scope.scope_id) is not int or scope.scope_id != index
                or not isinstance(scope.polarity, Polarity) or not isinstance(scope.kind, DirectiveKind)):
            invalid_evidence()
        inside(scope.chunk_span, whole)
        inside(scope.span, scope.chunk_span)
        if scope.marker_span is not None:
            inside(scope.marker_span, scope.span)
    if len(segmented.directives) != len(segmented.structure):
        invalid_evidence()
    for index, (directive, structure) in enumerate(zip(segmented.directives, segmented.structure)):
        if (directive.source_id != source.source_id or type(directive.directive_id) is not int or directive.directive_id != index
                or type(directive.scope_id) is not int or not 0 <= directive.scope_id < len(segmented.scopes)
                or not isinstance(directive.polarity, Polarity) or not isinstance(directive.kind, DirectiveKind)
                or type(structure.directive_id) is not int or structure.directive_id != index or structure.frame not in Frame.__args__
                or type(structure.uncertain) is not bool):
            invalid_evidence()
        scope = segmented.scopes[directive.scope_id]
        inside(directive.span, scope.span)
        for spans in (structure.qualifier_spans, structure.relations):
            immutable_tuple(spans)
        if structure.nominal_span is not None:
            inside(structure.nominal_span, directive.span)
        if structure.head_span is not None:
            if structure.nominal_span is None:
                invalid_evidence()
            inside(structure.head_span, structure.nominal_span)
        for span in structure.qualifier_spans:
            inside(span, directive.span)
        governor = structure.governing_directive_id
        if governor is not None:
            if type(governor) is not int or not 0 <= governor < len(segmented.directives) or governor == index:
                invalid_evidence()
            inside(segmented.directives[governor].span, scope.chunk_span)
        for relation in structure.relations:
            if not isinstance(relation, RelationEvidence):
                invalid_evidence()
            immutable_tuple(relation.dependent_directive_ids)
            inside(relation.marker_span, scope.chunk_span)
            inside(relation.dependent_span, scope.chunk_span)
            if relation.attachment not in Attachment.__args__:
                invalid_evidence()
            if relation.marker_span.end > relation.dependent_span.start:
                invalid_evidence()
            for member in relation.dependent_directive_ids:
                if type(member) is not int or not 0 <= member < len(segmented.directives):
                    invalid_evidence()
                inside(segmented.directives[member].span, scope.chunk_span)
                if member != index and segmented.structure[member].governing_directive_id != index:
                    invalid_evidence()
            marker_local = directive.span.start <= relation.marker_span.start < relation.marker_span.end <= directive.span.end
            dependent_local = directive.span.start <= relation.dependent_span.start < relation.dependent_span.end <= directive.span.end
            if not marker_local or not dependent_local:
                linked = [segmented.directives[i] for i in relation.dependent_directive_ids]
                if (not linked or len({d.scope_id for d in linked}) != 1
                        or segmented.scopes[linked[0].scope_id].marker_span != relation.marker_span
                        or relation.dependent_span != Span(min(d.span.start for d in linked), max(d.span.end for d in linked))):
                    invalid_evidence()
        visited = {index}
        while governor is not None:
            if type(governor) is not int or not 0 <= governor < len(segmented.directives) or governor in visited:
                invalid_evidence()
            visited.add(governor)
            governor = segmented.structure[governor].governing_directive_id


_HARD = re.compile(r"[.;!?\n]+|\b(?:but|но)\b", re.I)
_JOIN = re.compile(r",|\b(?:and|or|и|или)\b", re.I)
_COMMA = re.compile(r",")
# A rendering verb is part of the negative predicate only across these bounded
# links. Consuming it here prevents an embedded show/include from resetting scope.
_NEGATIVE = (
    r"(?:(?:i\s+)?(?:do\s+not|don['’]t)(?:\s+ever)?"
    r"(?:\s+want(?:\s+(?:you\s+)?to)?)?"
    r"|i(?:['’]d|\s+would)\s+rather\s+not|never(?:\s+ever)?)"
    r"(?:\s+(?:show|include|have))?"
    r"|avoid|no|without|exclude|excluding|not|rather\s+than|instead\s+of"
    r"|без|нет|не\s+хочу(?:\s+видеть)?|не\s+показывай(?:те)?"
    r"|избегай(?:те)?|исключи(?:те)?"
)
_MARKER = re.compile(
    r"\b(?:(?P<negative>" + _NEGATIVE + r")"
    r"|(?P<positive>show|include|i\s+want|хочу|покажи(?:те)?|изобрази(?:те)?))\b", re.I,
)
_INDEPENDENT_PREFIX = re.compile(
    r"(?:^|,|\b(?:and|or|и|или)\b)\s*(?:please\s+)?$", re.I,
)
_INLINE_NEGATIVE = re.compile(r"^(?:without|без|rather\s+than|instead\s+of)$", re.I)
_NESTED_VERB = re.compile(r"\b(?:show|include|have|видеть)\b", re.I)
_WORD = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", re.UNICODE)
# Closed function-word/predicate fences, not an adjective or subject whitelist.
# A bounded phrase admits up to six opaque lexical words before an optional
# closed suffix. This deliberately does not claim general natural-language parsing.
_NON_NOMINAL = frozenset({
    "i", "you", "he", "she", "we", "they", "me", "it", "if", "when", "because",
    "to", "for", "about", "of", "from", "on", "in", "by", "beside", "with", "at",
    "that", "which", "is", "are", "was", "were",
    "be", "been", "have", "has", "had", "do", "does", "did", "want", "show", "include",
    "discuss", "read", "write", "attended", "removed", "appears", "holding", "no", "not",
    "never", "avoid", "without", "exclude", "please", "either", "whatsoever", "give", "them",
    "я", "ты", "мы", "они", "если", "чтобы", "не", "без", "хочу", "покажи",
})
_SUFFIX = re.compile(
    r"\s+(?:anywhere|at\s+all|in\s+the\s+(?:image|frame)|whatsoever|please|either"
    r"|at\s+(?:sunset|sunrise|dawn|dusk)|на\s+рассвете|на\s+закате)$", re.I,
)
_DETACHED = re.compile(
    r"^(?:(?:a|an|the)\s+.+\s+please|just\s+me\s+and\s+.+)$", re.I,
)

# Grammatical links only. The dependent can be a poster, a story or an opaque
# noun without changing any structural decision. Inline negatives reuse scopes.
_RELATION = re.compile(
    r'\b(?:featuring|with|about|near|beside|under|over|on|in|at|for|of|from|by|про|о|об|на|у|с)\b', re.I,
)
_CONDITIONAL = re.compile(r'\b(?:if|when|если|когда)\b', re.I)
_ARTICLES = frozenset({'a', 'an', 'the', 'my', 'your'})


def _structure(text, scopes, directives, inline_links):
    """Extend this segmentation; never rescan text for polarity or boundaries."""
    from dataclasses import replace

    records = []
    for directive in directives:
        scope = scopes[directive.scope_id]
        span = directive.span
        phrase = span.extract(text)
        conditional = bool(_CONDITIONAL.search(scope.chunk_span.extract(text)))
        links = list(_RELATION.finditer(text, span.start, span.end))
        # Closed image-wide suffixes remain scope qualifiers, not local links.
        links = [link for link in links if not re.fullmatch(
            r'in\s+the\s+(?:image|frame)|at\s+all', text[link.start():span.end], re.I)]
        end = links[0].start() if links else span.end
        nominal = _trim(text, span.start, end)
        # The existing closed custom detached form retains its original span.
        personal = re.match(r'just\s+me\s+and\s+', nominal.extract(text), re.I)
        if personal:
            nominal = Span(nominal.start + personal.end(), nominal.end)
        core = nominal_core(nominal.extract(text))
        if core is not None:
            # nominal_core removes supported suffixes without moving the prefix.
            core_end = nominal.start + len(core)
            words = [m for m in _WORD.finditer(text, nominal.start, core_end)
                     if m.group().casefold() not in _ARTICLES]
        else:
            words = [m for m in _WORD.finditer(text, nominal.start, nominal.end)
                     if m.group().casefold() not in _ARTICLES]
        head = Span(words[-1].start(), words[-1].end()) if words else None
        qualifiers = [Span(m.start(), m.end()) for m in words[:-1]]
        if core is not None and core_end < nominal.end:
            qualifiers.append(_trim(text, core_end, nominal.end))
        relations = []
        uncertain = core is None or conditional
        for index, link in enumerate(links):
            dependent = _trim(text, link.end(), links[index + 1].start() if index + 1 < len(links) else span.end)
            if dependent.start == dependent.end:
                uncertain = True
                continue
            relations.append(RelationEvidence(Span(link.start(), link.end()), dependent, (),
                                               'uncertain' if core is None else 'head_local'))
            if link.group().casefold() in {'at', 'на'}:
                qualifiers.append(dependent)
            uncertain |= nominal_core(dependent.extract(text)) is None
        frame = ('conditional' if conditional else 'render_complement' if scope.marker_span is not None
                 else 'nominal' if core is not None else 'unknown')
        records.append(DirectiveStructure(directive.directive_id, frame, head,
                                         nominal if nominal.start < nominal.end else None,
                                         tuple(qualifiers), tuple(relations), None, uncertain))
    # A relation owns the coordinated complement, including comma siblings.
    for scope in scopes:
        members = [d.directive_id for d in directives if d.scope_id == scope.scope_id]
        owners = [i for i in members if any(r.marker_span.extract(text).casefold() not in {'at', 'на'}
                                          for r in records[i].relations)]
        if owners:
            owner = owners[0]
            for member in members:
                if member > owner:
                    records[member] = replace(records[member], governing_directive_id=owner)
            relations = list(records[owner].relations)
            relations[-1] = replace(relations[-1], dependent_directive_ids=tuple(i for i in members if i > owner))
            records[owner] = replace(records[owner], relations=tuple(relations),
                                     uncertain=records[owner].uncertain or len(owners) > 1)
        elif members:
            for member in members[1:]:
                records[member] = replace(records[member], governing_directive_id=members[0])
    for owner, child, marker in inline_links:
        children = tuple(d.directive_id for d in directives if d.scope_id == directives[child].scope_id)
        for member in children:
            records[member] = replace(records[member], governing_directive_id=owner)
        records[owner] = replace(records[owner], relations=records[owner].relations + (
            RelationEvidence(marker, Span(directives[children[0]].span.start, directives[children[-1]].span.end),
                             children, 'head_local'),
        ))
    return tuple(records)


def nominal_core(text: str) -> str | None:
    """Return a vocabulary-free bounded nominal core, or decline classification."""
    core = _SUFFIX.sub("", text.strip(), count=1)
    words = _WORD.findall(core)
    if not 1 <= len(words) <= 6 or " ".join(words).casefold() != " ".join(core.split()).casefold():
        return None
    if any(word.casefold() in _NON_NOMINAL for word in words):
        return None
    return core


def _has_narrative_function(text: str) -> bool:
    """Detect closed function/predicate fences, separately from phrase length."""
    # Temporal nouns must not decide structural kind. Rich frames below own
    # these relationships; the old coarse kind stays equally conservative for
    # "at sunrise" and an opaque substitution.
    if re.search(r'\b(?:at|на)\s+', text, re.I) and not re.search(r'\bat\s+all$', text, re.I):
        return True
    core = _SUFFIX.sub("", text.strip(), count=1)
    return any(word.casefold() in _NON_NOMINAL for word in _WORD.findall(core))


def _trim(text: str, start: int, end: int) -> Span:
    while start < end and text[start] in " \t\r,:":
        start += 1
    while end > start and text[end - 1] in " \t\r,:":
        end -= 1
    return Span(start, end)


def segment_directives(source: DirectiveSource) -> SegmentedSource:
    """Compute immutable grammatical scopes once, independently of recognition.

    Hard punctuation/contrast resets scope. Commas and conjunctions enumerate;
    they reset only before an independent supported command (optional please).
    Inline without/без starts a negative scope. Every scope retains its enclosing
    hard chunk, including soft-boundary continuations. Narrative-function
    ambiguity applies to the whole command; an explicit command's length-only
    ambiguity stays member-local. Polite detached requests remain ambiguous for
    the interpretation layer's source-specific authority decision.
    """
    text = source.text
    scopes, directives, inline_links = [], [], []

    def emit(start, end, marker=None):
        span = _trim(text, start, end)
        if span.start == span.end:
            return
        negative = marker is not None and marker.lastgroup == "negative"
        polarity = (Polarity.NEGATIVE if negative else
                    Polarity.POSITIVE if marker is not None else Polarity.UNSPECIFIED)
        kind = (DirectiveKind.NESTED_NEGATIVE if negative and _NESTED_VERB.search(marker.group()) else
                DirectiveKind.NEGATIVE_COMMAND if negative else
                DirectiveKind.POSITIVE_COMMAND if marker is not None else DirectiveKind.NOMINAL)
        content_start = marker.end() if marker else span.start
        first_member = _JOIN.split(text[content_start:span.end], maxsplit=1)[0].strip()
        comma_start = content_start
        members = []
        for comma_end in [m.start() for m in _COMMA.finditer(text, content_start, span.end)] + [span.end]:
            clause_span = _trim(text, comma_start, comma_end)
            # Drop an Oxford-comma coordinator, retaining exact member offsets.
            leading = re.match(r"(?:and|or|и|или)\s+", clause_span.extract(text), re.I)
            if leading:
                clause_span = Span(clause_span.start + leading.end(), clause_span.end)
            detached = negative and bool(members) and bool(_DETACHED.fullmatch(clause_span.extract(text)))
            cuts = [] if detached else list(_JOIN.finditer(text, clause_span.start, clause_span.end))
            member_start = clause_span.start
            for member_end, next_start in [(m.start(), m.end()) for m in cuts] + [(clause_span.end, clause_span.end)]:
                member_span = _trim(text, member_start, member_end)
                if member_span.start < member_span.end:
                    members.append((member_span, detached))
                member_start = next_start
            comma_start = comma_end + 1

        # A supported command marker does not make a narrative object visual.
        # Neither a preceding nor a trailing sibling can escape that ambiguity.
        # Detached custom-note forms are handled separately by source policy.
        ambiguous_scope = (marker is None and nominal_core(first_member) is None) or any(
            _has_narrative_function(member_span.extract(text))
            for member_span, detached in members if not detached
        )
        if ambiguous_scope:
            kind = DirectiveKind.AMBIGUOUS
        scope_id = len(scopes)
        scopes.append(Scope(source.source_id, scope_id, span,
                            Span(marker.start(), marker.end()) if marker else None,
                            polarity, kind, chunk_span))
        for member_index, (member_span, detached) in enumerate(members):
            member_kind = kind
            if ambiguous_scope or detached or nominal_core(member_span.extract(text)) is None:
                member_kind = DirectiveKind.AMBIGUOUS
            elif negative and member_index:
                member_kind = DirectiveKind.NEGATIVE_LIST_MEMBER
            directives.append(Directive(
                source.source_id, len(directives), scope_id, member_span,
                Polarity.UNSPECIFIED if detached else polarity, member_kind,
            ))

    chunk_start = 0
    for chunk_end, next_chunk in [(m.start(), m.end()) for m in _HARD.finditer(text)] + [(len(text), len(text))]:
        chunk_span = Span(chunk_start, chunk_end)
        start, current, pending_inline = chunk_start, None, None
        for marker in _MARKER.finditer(text, chunk_start, chunk_end):
            prefix = _INDEPENDENT_PREFIX.search(text[start:marker.start()])
            inline = marker.lastgroup == "negative" and _INLINE_NEGATIVE.fullmatch(marker.group())
            conditional = marker.lastgroup == 'negative' and re.match(
                r'^\s*(?:if|when|если|когда)\b', text[chunk_start:marker.start()], re.I)
            if not prefix and not inline and not conditional:
                continue
            boundary = start + prefix.start() if prefix else marker.start()
            before = len(directives)
            emit(start, boundary, current)
            if pending_inline is not None and len(directives) > before:
                inline_links.append((pending_inline[0], before, pending_inline[1]))
            pending_inline = ((len(directives) - 1, Span(marker.start(), marker.end()))
                              if inline and not prefix and len(directives) > before else None)
            command_start = boundary
            if prefix and (join := _JOIN.match(text, boundary, marker.start())):
                command_start = join.end()
            start = _trim(text, command_start, marker.start()).start
            current = marker
        before = len(directives)
        emit(start, chunk_end, current)
        if pending_inline is not None and len(directives) > before:
            inline_links.append((pending_inline[0], before, pending_inline[1]))
        chunk_start = next_chunk
    return SegmentedSource(source, tuple(scopes), tuple(directives),
                           _structure(text, scopes, directives, inline_links))
