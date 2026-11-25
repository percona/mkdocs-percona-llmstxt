"""Turn an MkDocs ``nav`` into the sections of llms.txt."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

NOT_FOUND_PAGE = "404.md"


def nav_pages(item: Any) -> list[str]:
    """Return the ``.md`` files in a nav item, in nav order. Links are skipped."""
    if isinstance(item, str):
        return [item] if item.endswith(".md") else []
    if isinstance(item, dict):
        return [page for value in item.values() for page in nav_pages(value)]
    if isinstance(item, list):
        return [page for value in item for page in nav_pages(value)]
    return []


def sections_from_nav(nav: list[Any], first_section: str) -> dict[str, list[str]]:
    """Map each top-level nav group to its pages.

    Top-level pages that are not in a group go into ``first_section``, which
    comes first. A page listed twice is kept where it first appears, and
    groups with no pages (only external links) are left out.
    """
    sections: dict[str, list[str]] = {first_section: []}
    for item in nav:
        if isinstance(item, dict) and len(item) == 1:
            title, value = next(iter(item.items()))
            if isinstance(value, list):
                sections.setdefault(title, []).extend(nav_pages(value))
                continue
        sections[first_section].extend(nav_pages(item))

    seen: set[str] = set()
    result: dict[str, list[str]] = {}
    for title, pages in sections.items():
        unique = [page for page in dict.fromkeys(pages) if page not in seen]
        seen.update(unique)
        if unique:
            result[title] = unique
    return result


def pages_outside_nav(pages: Iterable[str], sections: Mapping[str, list[str]]) -> list[str]:
    """Return the pages, in the order given, that no section lists.

    These are pages that are built and published but left out of ``nav``,
    such as old release notes. Other pages link to them, so they need a
    markdown copy too. The 404 page is not documentation and is skipped.
    """
    listed = {page for section in sections.values() for page in section}
    return [page for page in pages if page not in listed and page != NOT_FOUND_PAGE]


def move_to_optional(
    sections: Mapping[str, list[str]], optional: Iterable[str], name: str, others: Iterable[str]
) -> dict[str, list[str]]:
    """Move the sections called in ``optional`` into the last section, ``name``.

    llms.txt marks what an agent may skip in a section called "Optional", and
    release notes are what that section is for. Names are compared ignoring
    case. The last section lists, in this order, the pages already in a
    section of that name, the moved pages, then ``others``. The section
    ``name`` itself is never moved into itself. Sections left empty are dropped.
    """
    wanted = {title.casefold() for title in optional} - {name.casefold()}
    kept = {title: pages for title, pages in sections.items() if title.casefold() not in wanted}
    moved = [page for title, pages in sections.items() if title.casefold() in wanted for page in pages]
    last = [*kept.pop(name, []), *moved, *others]
    return {**kept, name: last} if last else kept


def qualified_titles(nav: list[Any], prefixed: Iterable[str] = ()) -> dict[str, str]:
    """Map pages nested below a section group to ``"<group>: <nav title>"``.

    Titles such as "Install" or "Overview" repeat across a product, and in
    llms.txt they sit in a flat list. Every group between the section and the
    page is put in front of the title. Pages directly in a section, top-level
    pages, pages without a nav title and external links are left out.
    A page listed twice keeps its first label.

    Sections named in ``prefixed`` (ignoring case) are the exception: their own
    name goes in front too, for every titled page. These are the sections that
    moved under "Optional", where "1.0" alone would lose its context.
    """
    titles: dict[str, str] = {}
    wanted = {name.casefold() for name in prefixed}

    def walk(items: list[Any], groups: tuple[str, ...]) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            for title, value in item.items():
                name = str(title)  # YAML reads a title such as 1.0 as a number
                if isinstance(value, list):
                    walk(value, (*groups, name))
                elif isinstance(value, str) and value.endswith(".md") and groups:
                    titles.setdefault(value, ": ".join((*groups, name)))

    for item in nav:
        if isinstance(item, dict) and len(item) == 1:
            section, value = next(iter(item.items()))
            if isinstance(value, list):
                walk(value, (str(section),) if str(section).casefold() in wanted else ())
    return titles
