"""Tests for the percona-llmstxt plugin: real MkDocs builds of a small site."""

from __future__ import annotations

from pathlib import Path

import pytest
from mkdocs.commands.build import build
from mkdocs.config import load_config
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.exceptions import PluginError

from percona_llmstxt.plugin import (
    MIKE_VERSION,
    PerconaLlmsTxtPlugin,
    base_url,
    directive,
    qualify_entries,
    versioned_title,
)

SITE_URL = "https://docs.example.com/product/"

NAV = """
nav:
  - Home: index.md
  - Guide:
      - Install: install.md
  - Release notes:
      - notes/1.0.md
  - Archive: https://example.com/archive/
"""

TABS_PAGE = """# Install

=== "With Helm"

    helm install

=== "With kubectl"

    kubectl apply
"""


def make_site(
    tmp_path: Path,
    *,
    llmstxt: str = "  - llmstxt:\n      sections: {}\n",
    percona: str = "  - percona-llmstxt\n",
    extensions: str = "",
    description: str = "Product is a database.",
) -> Path:
    """Write a small MkDocs project and return its config file."""
    docs = tmp_path / "docs"
    (docs / "notes").mkdir(parents=True)
    (docs / "index.md").write_text("# Home\n\nWelcome.\n", encoding="utf-8")
    (docs / "install.md").write_text(TABS_PAGE, encoding="utf-8")
    (docs / "notes" / "1.0.md").write_text("# Release 1.0\n\nFirst.\n", encoding="utf-8")
    (docs / "draft.md").write_text("# Draft\n\nNot in nav.\n", encoding="utf-8")
    config = tmp_path / "mkdocs.yml"
    config.write_text(
        f"""
site_name: Product
site_description: {description!r}
site_url: {SITE_URL}
use_directory_urls: false
markdown_extensions:
  - toc:
      permalink: true
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
{extensions}{NAV}
plugins:
{llmstxt}{percona}""",
        encoding="utf-8",
    )
    return config


def run_build(config_file: Path) -> Path:
    config = load_config(str(config_file))
    build(config)
    return Path(config.site_dir)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def no_mike(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(MIKE_VERSION, raising=False)


# --- helpers -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("site_url", "version", "expected"),
    [
        ("https://d.com/p/", None, "https://d.com/p/"),
        ("https://d.com/p", "", "https://d.com/p/"),
        ("https://d.com/p/", "9.7", "https://d.com/p/9.7/"),
        ("https://d.com/p/9.7", "9.7", "https://d.com/p/9.7/"),  # mike's plugin already added it
        ("https://d.com/p/19.7/", "9.7", "https://d.com/p/19.7/9.7/"),
    ],
)
def test_base_url(site_url: str, version: str | None, expected: str) -> None:
    assert base_url(site_url, version) == expected


def test_directive() -> None:
    assert (
        directive("https://d.com/llms.txt")
        == "> For the complete documentation index, see [llms.txt](https://d.com/llms.txt).\n\n"
    )


# --- builds ------------------------------------------------------------------


def test_build_without_settings(tmp_path: Path) -> None:
    site = run_build(make_site(tmp_path))
    index_url = SITE_URL + "llms.txt"

    index = read(site / "llms.txt")
    assert "## Overview\n\n- [Home](https://docs.example.com/product/index.md)" in index
    assert "## Guide\n\n- [Install](https://docs.example.com/product/install.md)" in index
    assert "## Release notes\n\n- [Release 1.0](https://docs.example.com/product/notes/1.0.md)" in index
    assert index.rstrip().endswith("## Optional\n\n- [Draft](https://docs.example.com/product/draft.md)")
    assert "Archive" not in index

    for page in ("index.md", "install.md", "notes/1.0.md", "draft.md"):
        text = read(site / page)
        assert text.startswith(directive(index_url)), page
        assert text.count("For the complete documentation index") == 1, page

    install_md = read(site / "install.md")
    assert "**With Helm**\n\nhelm install\n\n**With kubectl**\n\nkubectl apply\n" in install_md
    assert "¶" not in install_md

    install_html = read(site / "install.html")
    assert '<a data-markdown-ignore class="headerlink"' in install_html
    assert '<div data-markdown-ignore class="tabbed-labels' in install_html
    assert f'<a href="{index_url}" tabindex="-1">llms.txt</a>' in install_html
    assert install_html.count('class="agent-hint"') == 1


def test_build_under_mike_links_to_the_version_being_deployed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MIKE_VERSION, "9.7")
    site = run_build(make_site(tmp_path))
    assert "(https://docs.example.com/product/9.7/install.md)" in read(site / "llms.txt")
    assert read(site / "install.md").startswith(directive("https://docs.example.com/product/9.7/llms.txt"))
    assert 'href="https://docs.example.com/product/9.7/llms.txt"' in read(site / "index.html")


def test_settings_in_mkdocs_yml_are_kept(tmp_path: Path) -> None:
    llmstxt = """  - llmstxt:
      base_url: https://docs.example.com/product/latest/
      sections:
        Only:
          - install.md
"""
    percona = """  - percona-llmstxt:
      hint: false
"""
    site = run_build(make_site(tmp_path, llmstxt=llmstxt, percona=percona))
    index = read(site / "llms.txt")
    assert "## Only\n\n- [Install](https://docs.example.com/product/latest/install.md)" in index
    assert "## Overview" not in index
    assert "## Optional" not in index  # sections set by hand are kept as they are
    assert not (site / "index.md").exists()
    assert read(site / "install.md").startswith(directive("https://docs.example.com/product/latest/llms.txt"))
    assert "agent-hint" not in read(site / "install.html")


def test_pages_outside_nav_can_be_left_out(tmp_path: Path) -> None:
    site = run_build(make_site(tmp_path, percona="  - percona-llmstxt:\n      other_pages: ''\n"))
    assert "Draft" not in read(site / "llms.txt")
    assert not (site / "draft.md").exists()


def test_no_optional_section_when_every_page_is_in_nav(tmp_path: Path) -> None:
    config_file = make_site(tmp_path)
    (tmp_path / "docs" / "draft.md").unlink()
    assert "## Optional" not in read(run_build(config_file) / "llms.txt")


def test_a_nav_group_with_the_same_name_keeps_its_pages(tmp_path: Path) -> None:
    config_file = make_site(tmp_path)
    config_file.write_text(read(config_file).replace("  - Release notes:", "  - Optional:"), encoding="utf-8")
    index = read(run_build(config_file) / "llms.txt")
    assert "## Optional\n\n- [Release 1.0](https://docs.example.com/product/notes/1.0.md)\n- [Draft]" in index


def test_other_pages_section_name(tmp_path: Path) -> None:
    site = run_build(make_site(tmp_path, percona="  - percona-llmstxt:\n      other_pages: More pages\n"))
    assert "## More pages\n\n- [Draft]" in read(site / "llms.txt")


def test_first_section_name(tmp_path: Path) -> None:
    site = run_build(make_site(tmp_path, percona="  - percona-llmstxt:\n      first_section: Start here\n"))
    assert "## Start here\n\n- [Home]" in read(site / "llms.txt")


def test_a_custom_preprocess_is_kept_and_autoclean_left_on(tmp_path: Path) -> None:
    script = tmp_path / "mine.py"
    script.write_text("def preprocess(soup, output):\n    soup.insert(0, 'MINE ')\n", encoding="utf-8")
    llmstxt = f"  - llmstxt:\n      sections: {{}}\n      preprocess: {script.as_posix()}\n"
    site = run_build(make_site(tmp_path, llmstxt=llmstxt))
    text = read(site / "install.md")
    assert "MINE" in text
    assert "**With Helm**" not in text  # the tab labels went with the plugin's own clean-up


def test_needs_the_llmstxt_plugin(tmp_path: Path) -> None:
    config: MkDocsConfig = load_config(str(make_site(tmp_path, llmstxt="")))
    with pytest.raises(PluginError, match="needs the llmstxt plugin"):
        config.plugins["percona-llmstxt"].on_config(config)


@pytest.mark.parametrize("site_url", ["", None], ids=["empty", "missing"])
def test_without_site_url_the_build_is_left_alone(tmp_path: Path, site_url: str | None) -> None:
    """PDF builds often inherit the plugins but have no site_url: they must still build."""
    config_file = make_site(tmp_path)
    line = "" if site_url is None else f"site_url: '{site_url}'\n"
    config_file.write_text(read(config_file).replace(f"site_url: {SITE_URL}\n", line), encoding="utf-8")
    site = run_build(config_file)
    assert not (site / "install.md").exists()
    install_html = read(site / "install.html")
    assert "agent-hint" not in install_html
    assert "data-markdown-ignore" not in install_html


ALTERNATE = 'rel="alternate" type="text/markdown"'


def test_html_pages_link_their_markdown(tmp_path: Path) -> None:
    site = run_build(make_site(tmp_path))
    install_html = read(site / "install.html")
    link = f'<link rel="alternate" type="text/markdown" href="{SITE_URL}install.md">'
    assert install_html.count(link) == 1
    assert install_html.index(link) < install_html.index("</head>")
    assert f'This page as markdown: <a href="{SITE_URL}install.md"' in install_html


def test_html_pages_without_a_markdown_copy_have_no_link(tmp_path: Path) -> None:
    llmstxt = "  - llmstxt:\n      sections:\n        Only:\n          - install.md\n"
    site = run_build(make_site(tmp_path, llmstxt=llmstxt))
    assert ALTERNATE in read(site / "install.html")
    index_html = read(site / "index.html")
    assert ALTERNATE not in index_html
    assert "This page as markdown" not in index_html


def test_alternate_link_does_not_need_the_hint(tmp_path: Path) -> None:
    site = run_build(make_site(tmp_path, percona="  - percona-llmstxt:\n      hint: false\n"))
    install_html = read(site / "install.html")
    assert ALTERNATE in install_html
    assert "agent-hint" not in install_html


def test_alternate_inactive_without_site_url(tmp_path: Path) -> None:
    config_file = make_site(tmp_path)
    config_file.write_text(read(config_file).replace(f"site_url: {SITE_URL}\n", ""), encoding="utf-8")
    assert ALTERNATE not in read(run_build(config_file) / "install.html")


def test_pages_llmstxt_did_not_write_are_skipped(tmp_path: Path) -> None:
    config: MkDocsConfig = load_config(str(make_site(tmp_path)))
    build(config)
    plugin = config.plugins["percona-llmstxt"]
    assert isinstance(plugin, PerconaLlmsTxtPlugin)
    plugin.md_pages.append("gone.md")
    plugin.on_post_build(config=config)
    assert not (Path(config.site_dir) / "gone.md").exists()


# --- code block language -----------------------------------------------------

HIGHLIGHT_YML = "  - pymdownx.highlight\n"

CODE_PAGE = """# Install

```sql
SELECT 1;
```

```bash
echo hi
```

```sql linenums="1"
SELECT 2;
```

=== "With Helm"

    ```sql
    SELECT 3;
    ```
"""


def loaded_config(tmp_path: Path, extensions: str, mdx: str = "") -> MkDocsConfig:
    config: MkDocsConfig = load_config(str(make_site(tmp_path, extensions=extensions)))
    if mdx:
        config.mdx_configs["pymdownx.highlight"] = {"pygments_lang_class": False}
    config.plugins["percona-llmstxt"].on_config(config)
    return config


def test_lang_class_enabled_when_highlight_used(tmp_path: Path) -> None:
    config = loaded_config(tmp_path, HIGHLIGHT_YML)
    assert config.mdx_configs["pymdownx.highlight"]["pygments_lang_class"] is True


def test_lang_class_explicit_false_kept(tmp_path: Path) -> None:
    config = loaded_config(tmp_path, HIGHLIGHT_YML, mdx="off")
    assert config.mdx_configs["pymdownx.highlight"]["pygments_lang_class"] is False


def test_lang_class_no_highlight_extension(tmp_path: Path) -> None:
    config = loaded_config(tmp_path, "")
    assert "pymdownx.highlight" not in config.mdx_configs


def test_lang_class_inactive_without_site_url(tmp_path: Path) -> None:
    config_file = make_site(tmp_path, extensions=HIGHLIGHT_YML)
    config_file.write_text(read(config_file).replace(f"site_url: {SITE_URL}\n", ""), encoding="utf-8")
    config: MkDocsConfig = load_config(str(config_file))
    config.plugins["percona-llmstxt"].on_config(config)
    assert "pygments_lang_class" not in config.mdx_configs.get("pymdownx.highlight", {})


def test_built_markdown_keeps_code_language(tmp_path: Path) -> None:
    config_file = make_site(tmp_path, extensions=HIGHLIGHT_YML)
    (tmp_path / "docs" / "install.md").write_text(CODE_PAGE, encoding="utf-8")
    text = read(run_build(config_file) / "install.md")
    assert text.count("```sql") == 3
    assert text.count("```bash") == 1
    assert "```sql\nSELECT 3;" in text


def test_built_markdown_links_to_markdown(tmp_path: Path) -> None:
    config_file = make_site(tmp_path)
    (tmp_path / "docs" / "index.md").write_text(
        "# Home\n\n[Install](install.md#steps) and [site](https://example.com/page.html).\n", encoding="utf-8"
    )
    text = read(run_build(config_file) / "index.md")
    assert "[Install](https://docs.example.com/product/install.md#steps)" in text
    assert "(https://example.com/page.html)" in text


def test_built_markdown_keeps_image_alt(tmp_path: Path) -> None:
    config_file = make_site(tmp_path, extensions="  - attr_list\n  - pymdownx.emoji\n")
    (tmp_path / "docs" / "install.md").write_text(
        "# Install\n\nDiagram:\n\n![Audit flow](flow.png)\n\n![](blank.png) :warning: done\n",
        encoding="utf-8",
    )
    text = read(run_build(config_file) / "install.md")
    assert [line for line in text.splitlines() if "Image: " in line] == ["*Image: Audit flow*"]


# --- title and labels --------------------------------------------------------


@pytest.mark.parametrize(
    ("line", "version", "expected"),
    [
        ("# PS", "8.4", "# PS 8.4"),
        ("# PS 8.4", "8.4", "# PS 8.4"),
        ("# PS", None, "# PS"),
        ("# PS", "", "# PS"),
        ("## Section", "8.4", "## Section"),
        ("text", "8.4", "text"),
    ],
)
def test_versioned_title(line: str, version: str | None, expected: str) -> None:
    assert versioned_title(line, version) == expected


def test_qualify_entries() -> None:
    text = (
        "# T\n\n## S\n\n- [Install](https://d/a.md)\n- [Other](https://d/b.md): About b\n"
        "- [Install](https://d/c.md)\nplain [Install](https://d/a.md)\n"
    )
    out = qualify_entries(text, {"https://d/a.md": "ALF: Install", "https://d/b.md": "X [1]: Other"})
    assert out == (
        "# T\n\n## S\n\n- [ALF: Install](https://d/a.md)\n- [X \\[1\\]: Other](https://d/b.md): About b\n"
        "- [Install](https://d/c.md)\nplain [Install](https://d/a.md)\n"
    )


NESTED_NAV = """
nav:
  - Home: index.md
  - Guide:
      - Audit Log Filter:
          - Install: install.md
      - Notes: notes/1.0.md
"""


def nested_site(tmp_path: Path, extra: str = "") -> Path:
    config_file = make_site(tmp_path, llmstxt=f"  - llmstxt:\n      sections: {{}}\n{extra}")
    text = read(config_file)
    start = text.index("nav:")
    end = text.index("plugins:")
    config_file.write_text(text[:start] + NESTED_NAV.strip() + "\n" + text[end:], encoding="utf-8")
    return config_file


def test_llms_txt_title_and_labels(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MIKE_VERSION, "8.4")
    site = run_build(nested_site(tmp_path))
    index = read(site / "llms.txt")
    assert index.splitlines()[0] == "# Product 8.4"
    assert "- [Audit Log Filter: Install](https://docs.example.com/product/8.4/install.md)" in index
    assert "- [Notes](https://docs.example.com/product/8.4/notes/1.0.md)" in index


def test_llms_full_txt_title(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MIKE_VERSION, "8.4")
    site = run_build(nested_site(tmp_path, "      full_output: llms-full.txt\n"))
    assert read(site / "llms-full.txt").splitlines()[0] == "# Product 8.4"


def test_missing_llms_files_are_skipped(tmp_path: Path) -> None:
    config: MkDocsConfig = load_config(str(nested_site(tmp_path, "      full_output: llms-full.txt\n")))
    build(config)
    (Path(config.site_dir) / "llms.txt").unlink()
    (Path(config.site_dir) / "llms-full.txt").unlink()
    config.plugins["percona-llmstxt"].on_post_build(config=config)
    assert not (Path(config.site_dir) / "llms.txt").exists()


def test_titles_inactive_without_site_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MIKE_VERSION, "8.4")
    config_file = nested_site(tmp_path)
    config_file.write_text(read(config_file).replace(f"site_url: {SITE_URL}\n", ""), encoding="utf-8")
    site = run_build(config_file)
    assert "8.4" not in read(site / "llms.txt")


# --- empty summary -----------------------------------------------------------


@pytest.mark.parametrize("description", ["", "Documentation", " docs "])
def test_warns_on_generic_site_description(tmp_path: Path, caplog: pytest.LogCaptureFixture, description: str) -> None:
    site = run_build(make_site(tmp_path, description=description))
    assert "site_description is the summary line of llms.txt" in caplog.text
    assert read(site / "llms.txt").startswith("# Product\n")  # the build goes on


def test_warns_when_site_description_is_missing(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    config_file = make_site(tmp_path)
    config_file.write_text(
        config_file.read_text(encoding="utf-8").replace("site_description: 'Product is a database.'\n", "")
    )
    run_build(config_file)
    assert "site_description is the summary line of llms.txt" in caplog.text


def test_no_warning_for_real_description(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    run_build(make_site(tmp_path))
    assert "site_description" not in caplog.text
