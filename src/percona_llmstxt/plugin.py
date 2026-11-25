"""The ``percona-llmstxt`` MkDocs plugin.

It works with mkdocs-llmstxt (the ``llmstxt`` plugin), which writes llms.txt,
llms-full.txt and the markdown pages, and fills in what Percona's docs need:

* the sections of llms.txt, from ``nav``, so there is no second list of pages;
* ``base_url``, from ``site_url`` and the version mike is deploying, so every
  version branch links to its own pages without per-branch settings;
* a pre-processing step that keeps the labels of content tabs and points links
  between pages at the markdown copies;
* a warning when ``site_description``, the summary line of llms.txt, says nothing;
* the language of code blocks (``pygments_lang_class`` on pymdownx.highlight);
* a link to llms.txt at the top of every markdown page and, hidden, in every
  HTML page;
* ``data-markdown-ignore`` on the parts of the HTML that are for people only.

Anything set explicitly on the ``llmstxt`` plugin in mkdocs.yml is kept.

Without ``site_url`` there is nothing to link to, so the build is left as it
is: this is the case for PDF builds that inherit the plugins from a base config.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from mkdocs.config import config_options as opts
from mkdocs.config.base import Config
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.exceptions import PluginError
from mkdocs.plugins import BasePlugin, event_priority
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

from percona_llmstxt import preprocess
from percona_llmstxt.html import add_alternate, add_hint, mark_human_only
from percona_llmstxt.nav import pages_outside_nav, qualified_titles, sections_from_nav

LLMSTXT = "llmstxt"
HIGHLIGHT = "pymdownx.highlight"
GENERIC_DESCRIPTIONS = frozenset({"", "documentation", "docs"})  # say nothing about the product
MIKE_VERSION = "MIKE_DOCS_VERSION"  # set by `mike deploy` for the build it runs

log = logging.getLogger(f"mkdocs.plugins.{__name__}")


class PerconaLlmsTxtConfig(Config):  # type: ignore[no-untyped-call]  # MkDocs: untyped __init_subclass__
    """Options under ``percona-llmstxt:`` in mkdocs.yml."""

    first_section = opts.Type(str, default="Overview")
    """The llms.txt section for top-level pages that are not in a nav group."""

    other_pages = opts.Type(str, default="Optional")
    """The last llms.txt section, for pages that are built but not in nav; '' leaves them out.

    In llms.txt, "Optional" is the section an agent may skip when it is short of context.
    """

    hint = opts.Type(bool, default=True)
    """Add the hidden link to llms.txt to every HTML page."""

    html_md = opts.Type(bool, default=True)
    """Also serve each markdown page at its HTML URL plus ``.md`` (``install.html.md``)."""


def base_url(site_url: str, version: str | None) -> str:
    """The URL the links in llms.txt start with, ending in ``/``.

    During ``mike deploy 9.7`` it is ``<site_url>9.7/``. mike's own plugin may
    already have added the version to ``site_url``; it is not added twice.
    """
    root = site_url.rstrip("/")
    if version and not root.endswith("/" + version):
        root += "/" + version
    return root + "/"


def directive(index_url: str) -> str:
    """The line that starts every markdown page."""
    return f"> For the complete documentation index, see [llms.txt]({index_url}).\n\n"


def versioned_title(line: str, version: str | None) -> str:
    """Add the version to the ``# Title`` line of llms.txt, so each version's index is told apart."""
    if not version or not line.startswith("# ") or line.endswith(version):
        return line
    return f"{line} {version}"


ENTRY = re.compile(r"^- \[(?P<title>.*?)\]\((?P<url>[^)\s]+)\)(?P<rest>(?::.*)?)$")


def qualify_entries(llms_txt: str, md_url_titles: dict[str, str]) -> str:
    """Give the ``- [Title](url)`` entries whose url is in the map their new title.

    ``[`` and ``]`` in a new title are escaped so they cannot end the link early.
    """

    def rewrite(line: str) -> str:
        match = ENTRY.match(line)
        if match is None or (title := md_url_titles.get(match["url"])) is None:
            return line
        escaped = title.replace("[", "\\[").replace("]", "\\]")
        return f"- [{escaped}]({match['url']}){match['rest']}"

    return "\n".join(rewrite(line) for line in llms_txt.split("\n"))


def html_md_name(name: str) -> str:
    """The ``.html.md`` twin of a markdown page's path: ``a/b.md`` becomes ``a/b.html.md``.

    The llms.txt convention is that a page's markdown lives at its URL with
    ``.md`` appended, and tools that follow it ask for ``install.html.md``.
    """
    return name.removesuffix(".md") + ".html.md"


def enable_lang_class(config: MkDocsConfig) -> None:
    """Make pymdownx.highlight add ``language-<lang>`` to code blocks, unless mkdocs.yml set it.

    Without that class mkdocs-llmstxt cannot tell the language and writes a bare fence.
    """
    if HIGHLIGHT in config.markdown_extensions:
        config.mdx_configs.setdefault(HIGHLIGHT, {}).setdefault("pygments_lang_class", True)


def llmstxt_full_output(config: MkDocsConfig) -> str | None:
    """The ``full_output`` file name set on the llmstxt plugin, if any."""
    output: str | None = config.plugins[LLMSTXT].config.full_output
    return output


class PerconaLlmsTxtPlugin(BasePlugin[PerconaLlmsTxtConfig]):  # type: ignore[no-untyped-call]  # same
    """Fills in the ``llmstxt`` plugin's settings and adds the links to llms.txt."""

    def __init__(self) -> None:
        self.active = False
        self.index_url = ""
        self.md_pages: list[str] = []
        self.md_urls: dict[str, str] = {}
        self.llms_titles: dict[str, str] = {}
        self.sections_from_nav = False

    @event_priority(50)  # before the llmstxt plugin reads its settings
    def on_config(self, config: MkDocsConfig) -> MkDocsConfig:
        llmstxt: BasePlugin[Any] | None = config.plugins.get(LLMSTXT)
        if llmstxt is None:
            raise PluginError("percona-llmstxt needs the llmstxt plugin (mkdocs-llmstxt) in 'plugins'")
        settings = llmstxt.config
        self.active = bool(config.site_url)
        if not config.site_url:
            log.info("No 'site_url', so no llms.txt links or markdown pages are added to this build")
            settings.sections = {}  # llmstxt writes no markdown pages
            if config.site_url is None:
                config.site_url = ""  # llmstxt stops the build when site_url is None
            return config

        if (config.site_description or "").strip().lower() in GENERIC_DESCRIPTIONS:
            log.warning("site_description is the summary line of llms.txt; describe the product in one sentence")
        enable_lang_class(config)
        self.sections_from_nav = not settings.sections
        if self.sections_from_nav:
            settings.sections = sections_from_nav(config.nav or [], self.config.first_section)
        if not settings.base_url:
            settings.base_url = base_url(config.site_url, os.environ.get(MIKE_VERSION))
        if not settings.preprocess:
            settings.preprocess = preprocess.__file__
            settings.autoclean = False  # preprocess() runs it after labelling the tabs

        self.index_url = settings.base_url.rstrip("/") + "/llms.txt"
        return config

    @event_priority(50)  # before the llmstxt plugin reads the sections
    def on_files(self, files: Files, *, config: MkDocsConfig) -> Files:
        """List the pages outside nav, and remember where llmstxt will write the markdown pages."""
        if not self.active:
            return files
        llmstxt: BasePlugin[Any] = config.plugins[LLMSTXT]
        sections = llmstxt.config.sections
        if self.sections_from_nav and (name := self.config.other_pages):
            pages = [file.src_uri for file in files.documentation_pages()]
            if others := pages_outside_nav(pages, sections):
                sections = {**sections, name: [*sections.get(name, []), *others]}
                llmstxt.config.sections = sections
        wanted = {page for pages in sections.values() for page in pages}
        md_files = {
            file.src_uri: Path(file.dest_uri).with_suffix(".md").as_posix()
            for file in files.documentation_pages()
            if file.src_uri in wanted
        }
        self.md_pages = list(md_files.values())
        self.md_urls = {src: urljoin(llmstxt.config.base_url, dest) for src, dest in md_files.items()}
        labels = qualified_titles(config.nav or [])
        self.llms_titles = {self.md_urls[src]: label for src, label in labels.items() if src in self.md_urls}
        preprocess.configure(config.site_dir, frozenset(self.md_pages))
        return files

    def on_post_page(self, output: str, *, page: Page, config: MkDocsConfig) -> str:
        if not self.active:
            return output
        output = mark_human_only(output)
        md_url = self.md_urls.get(page.file.src_uri)
        if md_url:
            output = add_alternate(output, md_url)
        return add_hint(output, self.index_url, md_url) if self.config.hint else output

    @event_priority(-100)  # after llmstxt has written the markdown pages
    def on_post_build(self, *, config: MkDocsConfig) -> None:
        if not self.active:
            return
        line = directive(self.index_url)
        site_dir = Path(config.site_dir)
        for name in self.md_pages:
            path = site_dir / name
            if path.is_file():
                text = line + path.read_text(encoding="utf-8")
                path.write_text(text, encoding="utf-8")
                if self.config.html_md:
                    (site_dir / html_md_name(name)).write_text(text, encoding="utf-8")
        self.retitle(site_dir / "llms.txt", qualify=True)
        if full_output := llmstxt_full_output(config):
            self.retitle(site_dir / full_output, qualify=False)

    def retitle(self, path: Path, *, qualify: bool) -> None:
        """Put the version in the first line of an llms file and, for llms.txt, qualify the labels."""
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8")
        first, newline, rest = text.partition("\n")
        text = versioned_title(first, os.environ.get(MIKE_VERSION)) + newline + rest
        if qualify:
            text = qualify_entries(text, self.llms_titles)
        path.write_text(text, encoding="utf-8")
