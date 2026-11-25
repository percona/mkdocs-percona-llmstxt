"""Pre-processing for mkdocs-llmstxt, which the plugin sets as its ``preprocess``.

mkdocs-llmstxt's own clean-up drops the labels of content tabs, so the
markdown loses which block is "With Helm" and which is "With kubectl". This
writes each label in bold at the top of its block, keeps the alt text of images, points links at the
markdown copies of pages, then runs that clean-up.

mkdocs-llmstxt imports this file by path and calls ``preprocess`` only, so
what the plugin knows (where the site is built, which pages have a markdown
copy) is passed in with :func:`configure`. mkdocs-llmstxt runs this file as
a fresh copy of the module for every page, so ``preprocess`` reads that state
from the installed module, the one ``configure`` was called on.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path, PurePosixPath

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from mkdocs_llmstxt import autoclean

from percona_llmstxt.links import rewrite_links


@dataclass(frozen=True)
class _State:
    site_dir: str
    md_pages: frozenset[str]


_state: _State | None = None


def configure(site_dir: str, md_pages: frozenset[str]) -> None:
    """Tell ``preprocess`` where the site is built and which pages get a markdown copy."""
    global _state
    _state = _State(site_dir, md_pages)


def _classes(tag: Tag) -> list[str]:
    value = tag.get("class")
    return list(value) if isinstance(value, list) else []


def _children_with_class(tag: Tag, name: str) -> list[Tag]:
    return [child for child in tag.find_all(recursive=False) if name in _classes(child)]


def label_tabs(soup: BeautifulSoup) -> None:
    """Put each tab's label at the top of its block and drop the label bar."""
    for tab_set in soup.find_all(class_="tabbed-set"):
        label_bars = _children_with_class(tab_set, "tabbed-labels")
        contents = _children_with_class(tab_set, "tabbed-content")
        if len(label_bars) != 1 or len(contents) != 1:
            continue
        labels = label_bars[0].find_all("label", recursive=False)
        blocks = _children_with_class(contents[0], "tabbed-block")
        for label, block in zip(labels, blocks, strict=False):
            title = soup.new_tag("p")
            strong = soup.new_tag("strong")
            strong.string = label.get_text(" ", strip=True)
            title.append(strong)
            block.insert(0, title)
        label_bars[0].decompose()


def _is_decorative(img: Tag) -> bool:
    classes = " ".join(_classes(img))
    return "emoji" in classes or "twemoji" in classes


def _holds_only(parent: Tag, child: Tag) -> bool:
    return all(node is child or (isinstance(node, NavigableString) and not node.strip()) for node in parent.contents)


def describe_images(soup: BeautifulSoup) -> None:
    """Replace each content image with its alt text, which clean-up would drop.

    Without this "the following diagram shows" is followed by nothing. Emoji
    and images with an empty alt are decoration and go. A link that holds only
    the image (a click-to-enlarge) goes with it, as a link to a picture says
    nothing in markdown. A link counts as image-only when whitespace is all
    that sits beside the image. Two images with nothing between them get a
    space, or their emphasis marks would run together.
    """
    described: list[Tag] = []
    for img in soup.find_all("img"):
        alt = str(img.get("alt") or "").strip()
        if not alt or _is_decorative(img):
            continue
        target: Tag = img
        parent = img.parent
        if isinstance(parent, Tag) and parent.name == "a" and _holds_only(parent, img):
            target = parent
        if any(target.previous_sibling is earlier for earlier in described):
            target.insert_before(" ")
        description = soup.new_tag("em")
        description.string = f"Image: {alt}"
        described.append(description)
        if target.find_parent("p") is None:
            block = soup.new_tag("p")
            block.append(description)
            description = block
        target.replace_with(description)


def preprocess(soup: BeautifulSoup, output: str) -> None:
    """Called by mkdocs-llmstxt for every page before it becomes markdown."""
    state: _State | None = import_module("percona_llmstxt.preprocess")._state
    if state is not None:
        try:
            page_dir = PurePosixPath(Path(output).relative_to(state.site_dir).parent.as_posix())
        except ValueError:  # not a page of the configured site: leave its links alone
            pass
        else:
            rewrite_links(soup, "" if str(page_dir) == "." else str(page_dir), state.md_pages)
    describe_images(soup)
    label_tabs(soup)
    autoclean(soup)
