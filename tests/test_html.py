"""Tests for percona_llmstxt.html."""

from __future__ import annotations

from percona_llmstxt.html import add_alternate, add_hint, hint, mark_human_only

URL = "https://docs.example.com/product/9.7/llms.txt"


def test_mark_human_only() -> None:
    page = (
        '<h2 id="a">A<a class="headerlink" href="#a">¶</a></h2>'
        '<div class="tabbed-labels"><label>X</label></div>'
        '<a class="headerlinks" href="#">kept</a><div class="tabbed-content"></div>'
    )
    assert mark_human_only(page) == (
        '<h2 id="a">A<a data-markdown-ignore class="headerlink" href="#a">¶</a></h2>'
        '<div data-markdown-ignore class="tabbed-labels"><label>X</label></div>'
        '<a class="headerlinks" href="#">kept</a><div class="tabbed-content"></div>'
    )


def test_hint_is_hidden_from_screen_and_screen_readers_and_out_of_tab_order() -> None:
    text = hint(URL)
    assert text.startswith('<div class="agent-hint" aria-hidden="true" style="position:absolute;')
    assert f'<a href="{URL}" tabindex="-1">llms.txt</a>' in text


def test_hint_escapes_the_url() -> None:
    assert 'href="https://x/?a=1&amp;b=&quot;2&quot;"' in hint('https://x/?a=1&b="2"')


def test_add_hint_goes_right_after_body_once() -> None:
    page = '<html><head></head><BODY dir="ltr" class="x"><header>H</header><body></body></BODY></html>'
    result = add_hint(page, URL)
    assert result.startswith('<html><head></head><BODY dir="ltr" class="x"><div class="agent-hint"')
    assert result.count("agent-hint") == 1
    assert result.endswith("<header>H</header><body></body></BODY></html>")


def test_add_hint_leaves_pages_without_body_alone() -> None:
    assert add_hint("<p>fragment</p>", URL) == "<p>fragment</p>"


MD_URL = "https://docs.example.com/product/9.7/install.md"


def test_hint_with_md_url() -> None:
    text = hint(URL, MD_URL)
    assert f'<a href="{URL}" tabindex="-1">llms.txt</a>.' in text
    assert f' This page as markdown: <a href="{MD_URL}" tabindex="-1">{MD_URL}</a>.</div>' in text
    assert hint(URL).count("markdown") == 0


def test_add_hint_passes_md_url_through() -> None:
    assert "This page as markdown" in add_hint("<body>x</body>", URL, MD_URL)


def test_add_alternate() -> None:
    page = "<html><HEAD><title>T</title></HEAD><body><head></head></body></html>"
    result = add_alternate(page, MD_URL)
    link = f'<link rel="alternate" type="text/markdown" href="{MD_URL}">'
    assert result == f"<html><HEAD><title>T</title>{link}</HEAD><body><head></head></body></html>"


def test_add_alternate_no_head() -> None:
    assert add_alternate("<p>fragment</p>", MD_URL) == "<p>fragment</p>"


def test_add_alternate_escapes_url() -> None:
    assert 'href="https://x/?a=1&amp;b=&quot;2&quot;"' in add_alternate("</head>", 'https://x/?a=1&b="2"')
