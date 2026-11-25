"""Tests for percona_llmstxt.descriptions."""

from __future__ import annotations

from typing import Any

import pytest

from percona_llmstxt.descriptions import MAX_LENGTH, drop_repeated, pick_description, shorten


def test_meta_description_wins() -> None:
    html = "<p>The first paragraph says something else.</p>"
    assert pick_description({"description": "  From the\n front matter. "}, html) == "From the front matter."


@pytest.mark.parametrize(
    "meta", [{}, {"description": ""}, {"description": "   "}, {"description": 5}, {"description": None}]
)
def test_unusable_meta_falls_back_to_the_first_paragraph(meta: dict[str, Any]) -> None:
    assert pick_description(meta, "<h1>T</h1><p>Percona Server is a database.</p>") == "Percona Server is a database."


def test_paragraphs_inside_admonitions_tabs_and_tables_are_skipped() -> None:
    html = (
        "<h1>Title</h1>"
        '<div class="admonition note"><p class="admonition-title">Note</p><p>Admonition text is long enough.</p></div>'
        "<details><summary>More</summary><p>Details text is long enough.</p></details>"
        '<div class="tabbed-set"><div class="tabbed-content"><p>Tab text is long enough.</p></div></div>'
        "<table><tr><td><p>Cell text is long enough.</p></td></tr></table>"
        "<p>The real first paragraph.</p>"
    )
    assert pick_description({}, html) == "The real first paragraph."


def test_no_paragraph_means_no_description() -> None:
    assert pick_description({}, "<h1>Title</h1><ul><li><p>Item that is long enough.</p></li></ul>") is None


def test_whitespace_collapsed_and_inline_markup_flattened() -> None:
    html = "<p>Use <code>SET\n  GLOBAL</code>, then\n restart.</p>"
    assert pick_description({}, html) == "Use SET GLOBAL, then restart."


def test_template_and_markdown_characters_are_kept_as_text() -> None:
    html = "<p>Set {{ var }} to *on* and [skip] `this`.</p>"
    assert pick_description({}, html) == "Set {{ var }} to *on* and [skip] `this`."


def test_too_short_description_is_skipped() -> None:
    assert pick_description({}, "<p>Too short.</p>") is None
    assert pick_description({"description": "Short"}, "<p>Too short.</p>") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("One sentence. Another one.", "One sentence."),
        ("Is it? Yes it is.", "Is it?"),
        ("Wow! Great stuff.", "Wow!"),
        ("Version 8.4 is out. Read on.", "Version 8.4 is out."),
        ("Use mysql.cnf or my.cnf. then restart. Done.", "Use mysql.cnf or my.cnf. then restart."),
        ("No end punctuation here", "No end punctuation here"),
    ],
)
def test_shorten_keeps_the_first_sentence(text: str, expected: str) -> None:
    assert shorten(text) == expected


def test_shorten_cuts_a_long_sentence_at_a_word_boundary() -> None:
    text = " ".join(["word"] * 100)
    out = shorten(text)
    assert out.endswith("…")
    assert len(out) <= MAX_LENGTH + 1
    assert out[:-1].split(" ")[-1] == "word"


def test_shorten_cuts_a_long_unbroken_string_at_the_limit() -> None:
    assert shorten("x" * 300) == "x" * MAX_LENGTH + "…"


def test_space_before_punctuation_and_after_opening_bracket_is_removed() -> None:
    html = '<p>Percona <a href="x">Support</a> is here to <strong>help</strong> .</p>'
    assert pick_description({}, html) == "Percona Support is here to help."
    assert (
        pick_description({}, "<p>Call ( now ) , then wait ; ok : yes ! no ?</p>")
        == "Call (now), then wait; ok: yes! no?"
    )
    assert pick_description({}, '<p>Percona <a href="x">Support</a> is here to <strong>help</strong>.</p>') == (
        "Percona Support is here to help."
    )


def test_a_description_on_three_pages_is_dropped_unless_authored() -> None:
    found = {
        "a": "Same text on pages.",
        "b": "Same text on pages.",
        "c": "Same text on pages.",
        "d": "Unique text here.",
    }
    assert drop_repeated(found, authored=set()) == {"d": "Unique text here."}


def test_a_description_on_two_pages_is_kept() -> None:
    found = {"a": "Shared by a pair.", "b": "Shared by a pair."}
    assert drop_repeated(found, authored=set()) == found


def test_authored_descriptions_are_kept_even_when_repeated() -> None:
    found = {"a": "Chosen by hand.", "b": "Chosen by hand.", "c": "Chosen by hand.", "d": "Chosen by hand."}
    assert drop_repeated(found, authored={"a", "b", "c"}) == {
        "a": "Chosen by hand.",
        "b": "Chosen by hand.",
        "c": "Chosen by hand.",
    }
