"""Tests for percona_llmstxt.links."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from percona_llmstxt.links import md_href, rewrite_links

MD_PAGES = frozenset({"a.md", "sub/b.md", "sub/index.md"})


@pytest.mark.parametrize(
    ("href", "page_dir", "expected"),
    [
        ("a.html", "", "a.md"),
        ("a.html#x", "", "a.md#x"),
        ("a.html?v=1#x", "", "a.md?v=1#x"),
        ("../a.html", "sub", "../a.md"),
        ("b.html", "sub", "b.md"),
        ("sub/", "", "sub/index.md"),
        ("sub/#top", "", "sub/index.md#top"),
        ("c.html", "", "c.html"),
        ("other/", "", "other/"),
        ("../../a.html", "sub", "../../a.html"),
        ("https://x.org/a.html", "", "https://x.org/a.html"),
        ("//x.org/a.html", "", "//x.org/a.html"),
        ("mailto:a@b", "", "mailto:a@b"),
        ("#top", "", "#top"),
        ("/a.html", "", "/a.html"),
        ("a.png", "", "a.png"),
    ],
)
def test_md_href(href: str, page_dir: str, expected: str) -> None:
    assert md_href(href, page_dir, MD_PAGES) == expected


def test_rewrite_links_changes_anchors_only() -> None:
    soup = BeautifulSoup('<a href="a.html#x">A</a><a>no href</a><a href="c.html">C</a>', "html.parser")
    rewrite_links(soup, "", MD_PAGES)
    assert [a.get("href") for a in soup.find_all("a")] == ["a.md#x", None, "c.html"]
