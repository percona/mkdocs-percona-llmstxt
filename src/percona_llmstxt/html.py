"""Changes to the HTML pages: what agents should find, and what they should skip."""

from __future__ import annotations

import html
import re

# Opening tags of Material for MkDocs elements that only make sense on screen:
# the pilcrow link after each heading and the bar of content-tab labels.
_HUMAN_ONLY = re.compile(r'<(a|div) class="(headerlink|tabbed-labels)\b')
_BODY = re.compile(r"<body\b[^>]*>", re.IGNORECASE)
_HEAD_END = re.compile(r"</head>", re.IGNORECASE)

# Visually hidden, the usual way: still in the DOM, so agents that read the
# HTML see it, but it takes no space on screen.
_HIDDEN = (
    "position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap"
)


def mark_human_only(page: str) -> str:
    """Add ``data-markdown-ignore`` to heading anchors and tab-label bars.

    Tools that compare a page's HTML with its markdown skip elements with this
    attribute. The markdown has no pilcrows, and keeps the tab labels in
    another place (see ``preprocess.label_tabs``).
    """
    return _HUMAN_ONLY.sub(r'<\1 data-markdown-ignore class="\2', page)


def hint(index_url: str, md_url: str | None = None) -> str:
    """A link to llms.txt for agents, hidden on screen and from screen readers.

    With ``md_url`` it also points to the markdown copy of the page.
    """
    url = html.escape(index_url, quote=True)
    text = f'For AI agents: an index of this documentation is at <a href="{url}" tabindex="-1">llms.txt</a>.'
    if md_url is not None:
        md = html.escape(md_url, quote=True)
        text += f' This page as markdown: <a href="{md}" tabindex="-1">{md}</a>.'
    return f'<div class="agent-hint" aria-hidden="true" style="{_HIDDEN}">{text}</div>'


def add_hint(page: str, index_url: str, md_url: str | None = None) -> str:
    """Insert the hint right after ``<body>``. Pages without a body are left alone."""
    return _BODY.sub(lambda match: match.group(0) + hint(index_url, md_url), page, count=1)


def add_alternate(page: str, md_url: str) -> str:
    """Point to the page's markdown copy from ``<head>``, where agents and crawlers look for alternates.

    Pages without a ``</head>`` are left alone.
    """
    link = f'<link rel="alternate" type="text/markdown" href="{html.escape(md_url, quote=True)}">'
    return _HEAD_END.sub(lambda match: link + match.group(0), page, count=1)
