"""Tests for percona_llmstxt.nav."""

from __future__ import annotations

from typing import Any

import pytest

from percona_llmstxt.nav import move_to_optional, nav_pages, pages_outside_nav, qualified_titles, sections_from_nav


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ("page.md", ["page.md"]),
        ("https://example.com/", []),
        ({"Title": "page.md"}, ["page.md"]),
        ({"Old releases": "https://example.com/"}, []),
        (["a.md", {"B": "b.md"}, {"Group": ["c.md", {"Sub": [{"D": "d.md"}]}]}], ["a.md", "b.md", "c.md", "d.md"]),
        (None, []),
        (42, []),
    ],
)
def test_nav_pages(item: Any, expected: list[str]) -> None:
    assert nav_pages(item) == expected


def test_top_level_groups_become_sections_and_loose_pages_come_first() -> None:
    nav: list[Any] = [
        {"Home": "index.md"},
        {"Install": ["install.md", {"On Kubernetes": [{"GKE": "gke.md"}]}]},
        "get-help.md",
        {"Reference": ["options.md"]},
        {"Archive": "https://example.com/archive/"},
    ]
    assert sections_from_nav(nav, "Overview") == {
        "Overview": ["index.md", "get-help.md"],
        "Install": ["install.md", "gke.md"],
        "Reference": ["options.md"],
    }


def test_a_page_is_listed_once_where_it_first_appears() -> None:
    nav: list[Any] = [
        {"Guide": ["a.md", "b.md", "a.md"]},
        {"Links": ["https://example.com/"]},
        {"Guide": ["c.md"]},
        {"Reference": ["b.md", "d.md"]},
    ]
    assert sections_from_nav(nav, "Start") == {"Guide": ["a.md", "b.md", "c.md"], "Reference": ["d.md"]}


def test_empty_nav() -> None:
    assert sections_from_nav([], "Overview") == {}


def test_pages_outside_nav_keep_their_order_and_skip_the_404_page() -> None:
    sections = {"Overview": ["index.md"], "Guide": ["install.md"]}
    pages = ["index.md", "notes/old.md", "install.md", "404.md", "legal.md"]
    assert pages_outside_nav(pages, sections) == ["notes/old.md", "legal.md"]


def test_no_pages_outside_nav() -> None:
    assert pages_outside_nav(["index.md"], {"Overview": ["index.md"]}) == []


def test_qualified_titles() -> None:
    nav: list[Any] = [{"Security": [{"Audit Log Filter": [{"Install": "alf-install.md"}]}, {"Overview": "sec.md"}]}]
    assert qualified_titles(nav) == {"alf-install.md": "Audit Log Filter: Install"}


def test_qualified_titles_nest_and_skip_unqualified_entries() -> None:
    nav: list[Any] = [
        "top.md",
        {"Home": "index.md"},
        {
            "Security": [
                "bare.md",
                {
                    "Audit Log Filter": [
                        "bare-nested.md",
                        {"Install": "alf-install.md"},
                        {"Link": "https://example.com/"},
                        {"Formats": [{"Overview": "f.md"}]},
                    ]
                },
            ]
        },
    ]
    assert qualified_titles(nav) == {
        "alf-install.md": "Audit Log Filter: Install",
        "f.md": "Audit Log Filter: Formats: Overview",
    }


def test_move_to_optional_puts_matching_sections_last_in_order() -> None:
    sections = {"Overview": ["a.md"], "Release notes": ["r1.md", "r2.md"], "Reference": ["b.md"], "Optional": ["o.md"]}
    assert move_to_optional(sections, ["release NOTES"], "Optional", ["x.md"]) == {
        "Overview": ["a.md"],
        "Reference": ["b.md"],
        "Optional": ["o.md", "r1.md", "r2.md", "x.md"],
    }


def test_move_to_optional_without_matches_only_adds_the_other_pages() -> None:
    sections = {"Overview": ["a.md"]}
    assert move_to_optional(sections, ["Release notes"], "Optional", []) == sections
    assert move_to_optional(sections, [], "Optional", ["x.md"]) == {"Overview": ["a.md"], "Optional": ["x.md"]}


def test_move_to_optional_never_moves_the_target_into_itself() -> None:
    assert move_to_optional({"Optional": ["o.md"]}, ["optional"], "Optional", []) == {"Optional": ["o.md"]}
