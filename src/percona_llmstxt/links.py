"""Point links between pages at the markdown copies.

An agent that reads ``install.md`` and follows ``[Upgrade](upgrade.html)`` lands
on HTML. When the target page has a markdown copy, the link goes there instead.
"""

from __future__ import annotations

import posixpath
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup


def md_href(href: str, page_dir: str, md_pages: frozenset[str]) -> str:
    """The href of the markdown copy of the page ``href`` points to, or ``href`` as it was.

    ``page_dir`` is the directory of the page the link is on, relative to the
    site root; ``md_pages`` are the site-relative paths of the pages that have
    a markdown copy. The query string and the ``#fragment`` are kept.
    """
    parts = urlsplit(href)
    path = parts.path
    if parts.scheme or parts.netloc or href.startswith(("#", "/")):
        return href
    if path.endswith(".html"):
        new_path = path.removesuffix(".html") + ".md"
        target = posixpath.normpath(posixpath.join(page_dir, new_path))
    elif path.endswith("/"):
        new_path = path + "index.md"
        target = posixpath.normpath(posixpath.join(page_dir, new_path))
    else:
        return href
    if target not in md_pages:
        return href
    return urlunsplit(parts._replace(path=new_path))


def rewrite_links(soup: BeautifulSoup, page_dir: str, md_pages: frozenset[str]) -> None:
    """Rewrite the ``href`` of every link in ``soup`` with :func:`md_href`."""
    for anchor in soup.find_all("a", href=True):
        anchor["href"] = md_href(str(anchor["href"]), page_dir, md_pages)
