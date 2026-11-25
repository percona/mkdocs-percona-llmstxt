"""One-line descriptions of pages for the entries of llms.txt.

An agent that reads ``- [Install](url)`` cannot tell which page answers its
question without opening each one. A line of text after the link lets it choose.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from bs4 import BeautifulSoup, Tag

MAX_LENGTH = 200
MIN_LENGTH = 15  # shorter text ("Overview.") says nothing the title does not
ELLIPSIS = "…"
SENTENCE_END = (". ", "? ", "! ")


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _cut(text: str) -> str:
    """Cut ``text`` to at most ``MAX_LENGTH`` characters, at a space, and mark the cut."""
    if len(text) <= MAX_LENGTH:
        return text
    head = text[:MAX_LENGTH]
    space = head.rfind(" ")
    return head[: space if space > 0 else MAX_LENGTH].rstrip(" ,;:") + ELLIPSIS


def shorten(text: str) -> str:
    """Keep the first sentence of ``text``, cut to ``MAX_LENGTH`` characters.

    A sentence ends at ``.``, ``?`` or ``!`` followed by a space and an uppercase
    letter, so "my.cnf. then" and "8.4 is" do not end it.
    """
    end = len(text)
    for index, char in enumerate(text[:-2]):
        if char in ".?!" and text[index + 1] == " " and text[index + 2].isupper():
            end = index + 1
            break
    return _cut(text[:end])


def first_paragraph(html: str) -> str:
    """The text of the first ``<p>`` that is directly in the page content.

    Paragraphs inside admonitions, details, tabs, tables and lists are notes,
    examples or data, not what the page is about, so only the top level counts.
    """
    soup = BeautifulSoup(html, "html.parser")
    for child in soup.find_all(recursive=False):
        if isinstance(child, Tag) and child.name == "p":
            return _collapse(child.get_text())
    return ""


def pick_description(meta: Mapping[str, Any], html: str) -> str | None:
    """The description of a page for llms.txt, or ``None`` when there is nothing useful.

    The ``description`` in the page's front matter is written by hand for this
    purpose, so it wins; it is only cut when it is too long. Otherwise the
    first sentence of the first paragraph is used.
    """
    meta_description = meta.get("description")
    if isinstance(meta_description, str) and (text := _collapse(meta_description)):
        description = _cut(text)
    else:
        description = shorten(first_paragraph(html))
    return description if len(description) >= MIN_LENGTH else None
