"""Tests for percona_llmstxt.preprocess."""

from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from percona_llmstxt import preprocess as llmstxt_preprocess

TABS = """
<div class="tabbed-set tabbed-alternate" data-tabs="1:2">
  <input checked id="__tabbed_1_1" type="radio"><input id="__tabbed_1_2" type="radio">
  <div class="tabbed-labels">
    <label for="__tabbed_1_1">With <em>Helm</em></label><label for="__tabbed_1_2">With kubectl</label>
  </div>
  <div class="tabbed-content">
    <div class="tabbed-block"><p>helm install</p></div>
    <div class="tabbed-block"><p>kubectl apply</p></div>
  </div>
</div>
"""


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_each_block_starts_with_its_label_and_the_label_bar_goes() -> None:
    soup = soup_of(TABS)
    llmstxt_preprocess.label_tabs(soup)
    blocks = soup.find_all(class_="tabbed-block")
    assert [str(block.p) for block in blocks] == [
        "<p><strong>With Helm</strong></p>",
        "<p><strong>With kubectl</strong></p>",
    ]
    assert [block.get_text(" ", strip=True) for block in blocks] == [
        "With Helm helm install",
        "With kubectl kubectl apply",
    ]
    assert soup.find(class_="tabbed-labels") is None


def test_nested_tabs_are_labelled_too() -> None:
    inner = TABS.replace("Helm", "Inner").replace("kubectl", "Other")
    soup = soup_of(TABS.replace("<p>helm install</p>", inner))
    llmstxt_preprocess.label_tabs(soup)
    labels = [strong.get_text() for strong in soup.find_all("strong")]
    assert labels == ["With Helm", "With Inner", "With Other", "With kubectl"]


def test_unexpected_markup_is_left_alone() -> None:
    html = '<div class="tabbed-set"><div class="tabbed-labels"><label>A</label></div></div>'
    soup = soup_of(html)
    llmstxt_preprocess.label_tabs(soup)
    assert str(soup) == html


def test_preprocess_labels_tabs_then_cleans_up() -> None:
    soup = soup_of('<h2>Install<a class="headerlink" href="#install">¶</a></h2>' + TABS)
    llmstxt_preprocess.preprocess(soup, "install.md")
    assert soup.find(class_="headerlink") is None
    assert soup.find("strong") is not None
    assert soup.find(class_="tabbed-labels") is None


def test_preprocess_rewrites_links_after_configure(tmp_path: Path) -> None:
    llmstxt_preprocess.configure(str(tmp_path), frozenset({"a.md"}))
    soup = soup_of('<p><a href="a.html#x">A</a></p>')
    llmstxt_preprocess.preprocess(soup, f"{tmp_path}/index.md")
    assert soup.a is not None
    assert soup.a["href"] == "a.md#x"


def test_preprocess_without_configure_leaves_links(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(llmstxt_preprocess, "_state", None)
    soup = soup_of('<p><a href="a.html#x">A</a></p>')
    llmstxt_preprocess.preprocess(soup, f"{tmp_path}/index.md")
    assert soup.a is not None
    assert soup.a["href"] == "a.html#x"


def test_preprocess_leaves_links_when_output_is_outside_site_dir(tmp_path: Path) -> None:
    llmstxt_preprocess.configure(str(tmp_path / "site"), frozenset({"a.md"}))
    soup = soup_of('<p><a href="a.html">A</a></p>')
    llmstxt_preprocess.preprocess(soup, f"{tmp_path}/elsewhere/index.md")
    assert soup.a is not None
    assert soup.a["href"] == "a.html"


def described(html: str) -> BeautifulSoup:
    soup = soup_of(html)
    llmstxt_preprocess.describe_images(soup)
    return soup


def test_image_alt_kept() -> None:
    soup = described('<p>Diagram:</p><img alt="Audit flow" src="x.png">')
    assert str(soup) == "<p>Diagram:</p><p><em>Image: Audit flow</em></p>"
    assert soup.img is None


def test_image_inside_a_paragraph_is_described_inline() -> None:
    soup = described('<p>See <img alt=" Audit flow " src="x.png"> here.</p>')
    assert str(soup) == "<p>See <em>Image: Audit flow</em> here.</p>"


def test_image_without_alt_dropped() -> None:
    for alt in ('alt=""', 'alt="  "', ""):
        assert "Image:" not in described(f'<p>A</p><img {alt} src="x.png">').get_text()


def test_emoji_images_dropped() -> None:
    soup = described('<p><img class="twemoji" alt="⚠"><img class="emoji" alt=":x:"></p>')
    assert "Image:" not in soup.get_text()


def test_image_inside_link_keeps_alt_drops_link() -> None:
    soup = described('<a href="big.png"><img alt="Topology" src="s.png"></a>')
    assert str(soup) == "<p><em>Image: Topology</em></p>"
    assert soup.a is None


def test_image_inside_link_in_paragraph_is_inline() -> None:
    soup = described('<p><a href="big.png"><img alt="Topology"></a></p>')
    assert str(soup) == "<p><em>Image: Topology</em></p>"


def test_link_with_text_besides_the_image_is_kept() -> None:
    soup = described('<p><a href="b.html">Big <img alt="Topology"></a></p>')
    assert soup.a is not None
    assert soup.a.get_text() == "Big Image: Topology"


def test_figcaption_is_kept() -> None:
    soup = described('<figure><img alt="Flow"><figcaption>Fig 1</figcaption></figure>')
    assert soup.figcaption is not None
    assert "Image: Flow" in soup.get_text()


def test_preprocess_describes_images_before_autoclean_drops_them() -> None:
    soup = soup_of('<p>Diagram:</p><img alt="Audit flow" src="x.png">')
    llmstxt_preprocess.preprocess(soup, "install.md")
    assert "Image: Audit flow" in soup.get_text()


def test_adjacent_images_are_separated_by_a_space() -> None:
    soup = described('<p><img alt="a" src="1.png"><img alt="b" src="2.png"></p>')
    assert str(soup) == "<p><em>Image: a</em> <em>Image: b</em></p>"


def test_link_holding_only_whitespace_and_the_image_is_image_only() -> None:
    soup = described('<p><a href="big.png">\n<img alt="Topology" src="s.png">\n</a></p>')
    assert str(soup) == "<p><em>Image: Topology</em></p>"
    assert soup.a is None
