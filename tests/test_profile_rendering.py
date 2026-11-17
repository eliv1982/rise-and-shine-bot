"""FIX-01A: lossless, readable Profile pages with UTF-16 and emoji boundaries."""

import pytest

from handlers import start


def utf16_length(text):
    # Independent oracle: production counts code points, tests count encoded units.
    return len(text.encode("utf-16-le")) // 2


EMOJI_AND_MARKS = [
    "👨‍👩‍👧‍👦",                 # ZWJ family.
    "👩🏽‍💻",                    # Modifier and ZWJ.
    "🇷🇺",                       # Regional indicator pair.
    "✈️",                        # Variation selector 16.
    "a\U000E0100",              # Supplementary variation selector.
    "e\u0301\u0327",            # Combining accents.
    "क\u093e",                  # Spacing mark with combining class zero.
    "1\ufe0f\u20e3",            # Keycap sequence.
    "🏴\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F",  # Tag flag.
]


@pytest.mark.parametrize("sequence", EMOJI_AND_MARKS)
def test_every_cut_inside_complex_sequence_moves_to_cluster_boundary(sequence):
    for offset in range(1, utf16_length(sequence)):
        text = "x" * (4096 - offset) + sequence + "y" * 4100
        chunks = start._split_profile_text(text)
        assert "".join(chunks) == text
        assert sum(sequence in chunk for chunk in chunks) == 1
        assert all(0 < utf16_length(chunk) <= 4096 for chunk in chunks)


def test_adjacent_flags_use_pairs_and_preserve_trailing_regional_indicator():
    text = "🇷🇺🇺🇸🇫🇷🇦"
    assert list(start._profile_clusters(text)) == ["🇷🇺", "🇺🇸", "🇫🇷", "🇦"]
    chunks = start._split_profile_text("x" * 4093 + text)
    assert chunks == ["x" * 4093, text]


@pytest.mark.parametrize("text", ["x" * 18000, "🌿" * 9000, "👨‍👩‍👧‍👦" * 1800], ids=["ascii", "astral", "zwj"])
def test_long_unbroken_values_are_lossless_and_within_limit(text):
    chunks = start._split_profile_text(text)
    assert len(chunks) > 3
    assert "".join(chunks) == text
    assert all(0 < utf16_length(chunk) <= 4096 for chunk in chunks)


@pytest.mark.parametrize("boundary", ["\n\n", "\n", " ", "\t", "\r\n"])
def test_readable_boundaries_are_preferred_without_discarding_whitespace(boundary):
    text = "a" * 25 + boundary + "b" * 30
    chunks = start._split_profile_text(text, limit=40)
    assert chunks == ["a" * 25 + boundary, "b" * 30]
    assert "".join(chunks) == text


def test_paragraph_break_is_preferred_over_a_later_word_break():
    text = "a" * 25 + "\n\n" + "word word word word"
    chunks = start._split_profile_text(text, limit=40)
    assert chunks[0] == "a" * 25 + "\n\n"
    assert "".join(chunks) == text


def test_tiny_header_does_not_make_an_almost_empty_first_chunk():
    text = "header\n\n" + "x" * 9000
    chunks = start._split_profile_text(text)
    assert utf16_length(chunks[0]) == 4096
    assert "".join(chunks) == text


@pytest.mark.parametrize("title", ["👤 Твой профиль", "👤 Your profile"])
def test_page_headers_are_contextual_and_count_toward_utf16_limit(title):
    body = "\n" + " ".join(EMOJI_AND_MARKS) * 600 + "\n\n" + "x" * 9000 + "\n"
    pages = start._profile_pages(title + "\n" + body)
    assert len(pages) > 2
    for index, page in enumerate(pages):
        assert page.startswith(f"{title} ({index + 1}/{len(pages)})\n")
        assert 0 < utf16_length(page) <= 4096
    assert "".join(page.partition("\n")[2] for page in pages) == body
    for sequence in EMOJI_AND_MARKS:
        assert sum(page.count(sequence) for page in pages) == body.count(sequence)


@pytest.mark.parametrize("size", [4095, 4096, 4097])
def test_exact_page_boundary_includes_context_marker_budget(size):
    title = "👤 Your profile"
    text = title + "\n\n" + "x" * (size - utf16_length(title) - 2)
    pages = start._profile_pages(text)
    if size <= 4096:
        assert pages == [text]
    else:
        assert len(pages) == 2
        assert title + "\n" + "".join(page.partition("\n")[2] for page in pages) == text
    assert all(0 < utf16_length(page) <= 4096 for page in pages)


@pytest.mark.parametrize("cluster", [
    "e" + "\u0301" * 9000,
    "👩" + "\u200d💻" * 3000,
    "a" + "\U000E0100" * 4500,
], ids=["combining", "zwj", "astral-marks"])
@pytest.mark.parametrize("limit", [4096, 4064])
def test_oversized_cluster_falls_back_losslessly_to_bounded_code_points(cluster, limit):
    text = "prefix 👩🏽‍💻 " + cluster + " 🇷🇺 suffix"
    chunks = start._split_profile_text(text, limit=limit)
    assert len(chunks) > 2
    assert "".join(chunks) == text
    assert all(0 < utf16_length(chunk) <= limit for chunk in chunks)
    assert sum("👩🏽‍💻" in chunk for chunk in chunks) == 1
    assert sum("🇷🇺" in chunk for chunk in chunks) == 1


def test_large_cluster_that_fits_budget_moves_whole_to_the_next_chunk():
    cluster = "e" + "\u0301" * 63
    assert start._split_profile_text("x" * 63 + cluster + "z", limit=64) == [
        "x" * 63, cluster, "z",
    ]


@pytest.mark.parametrize("title", ["👤 Твой профиль", "👤 Your profile"])
def test_cluster_below_telegram_limit_but_above_page_body_budget_remains_accessible(title):
    body = "e" + "\u0301" * 4090
    assert utf16_length(body) < 4096
    pages = start._profile_pages(title + "\n" + body)
    assert len(pages) == 2
    assert "".join(page.partition("\n")[2] for page in pages) == body
    assert all(0 < utf16_length(page) <= 4096 for page in pages)


def test_empty_split_has_no_empty_telegram_messages():
    assert start._split_profile_text("") == []
