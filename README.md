# mkdocs-percona-llmstxt

An MkDocs plugin that makes Percona documentation sites easy for AI agents and assistants to read. It works together with [mkdocs-llmstxt](https://github.com/pawamoy/mkdocs-llmstxt), which writes the files, and fills in everything a Percona docs repo would otherwise have to configure and maintain by hand.

A site built with both plugins gets:

- **`llms.txt`**, an index of every page in `nav`, grouped by the top-level nav sections, with links to the markdown pages ([llms.txt proposal](https://llmstxt.org/)).
- **`llms-full.txt`**, all pages in one file (if `full_output` is set).
- **A markdown copy of every page** next to its HTML: `backups.html` and `backups.md`. Each starts with a link to `llms.txt`. Content tabs keep their labels: each block starts with its label in bold.
- **Code blocks with their language**: ```` ```sql ```` instead of a bare fence, so an agent knows what it is reading.
- **Links between pages that stay in markdown**: a link to `other.html` in a markdown page points at `other.md`.
- **Images keep their alt text**: each image is replaced by `Image: <alt text>`.
- **The version in the `llms.txt` title** (`# Percona Server for MySQL 8.4`) (during `mike deploy`; the first line of `llms-full.txt` gets it too) and the groups in the label of a page nested below a section ("Audit Log Filter: Install").
- **A link to `llms.txt` in every HTML page**, hidden on screen and from screen readers, and out of the tab order. The hidden text also gives the URL of the page's markdown copy, and the `<head>` has `<link rel="alternate" type="text/markdown">` to it.
- **`data-markdown-ignore`** on the heading anchors (¶) and tab-label bars in the HTML. They are for people only; tools that compare a page's HTML with its markdown skip such elements.

Nothing changes for people reading the site.

## Use

Python 3.11 or later. Add to `requirements.txt`:

```
mkdocs-llmstxt>=0.5.1,<0.6
mkdocs-percona-llmstxt>=0.4.0,<0.5
```

The plugin sets some of mkdocs-llmstxt's settings, so it supports one minor version of it at a time.

Add both plugins to `mkdocs.yml` (or `mkdocs-base.yml`):

```yaml
plugins:
  llmstxt:
    full_output: llms-full.txt
    markdown_description: >-
      Each page below is also available as markdown. For the documentation
      of all Percona products, see https://docs.percona.com/llms.txt.
    sections: {}  # mkdocs-llmstxt requires the key; percona-llmstxt fills it from nav
  percona-llmstxt: {}
```

That's all. The links in `llms.txt` are built from `site_url`. A build without `site_url`, such as a PDF build that inherits the plugins from `mkdocs-base.yml`, is left as it is: no markdown pages and no changes to the HTML.

## What it fills in

On the `llmstxt` plugin, unless `mkdocs.yml` already sets it:

| Setting | Value |
|---|---|
| `sections` | When empty (`{}`): one section per top-level nav group, in nav order. Top-level pages outside a group go into a first section, "Overview". External links are skipped. A page added to `nav` shows up in `llms.txt` with no other change. Pages that are built but not in `nav`, such as old release notes, go into a last section, "Optional": other pages link to them, so they get a markdown copy too, and in `llms.txt` "Optional" is the section an agent may skip when it is short of context. |
| `base_url` | `site_url`, plus the version during `mike deploy`. `mike deploy 9.7` builds with `MIKE_DOCS_VERSION=9.7`, so `https://docs.percona.com/percona-server/` becomes `https://docs.percona.com/percona-server/9.7/`. Each version branch links to its own pages, with no per-branch settings. |
| `preprocess` | Keeps the labels of content tabs, rewrites links to `.md` and keeps image alt text, then runs the plugin's usual clean-up (`autoclean` is turned off so that it does not run twice). Setting your own `preprocess` turns all three off. |

## Markdown fidelity

- **Code languages.** The plugin turns on `pygments_lang_class` for `pymdownx.highlight` (if you set it to `false` yourself, that is kept), so each fenced block in the markdown copy starts with its language.
- **Links.** A link from one page to another in the site is rewritten to the markdown copy, with its `#anchor` kept. Links to pages without a markdown copy are left alone.
- **Images.** The images are removed from the markdown copy, as before, but their alt text stays as `Image: <alt text>`; images with no alt text are dropped.
- **Version and labels.** During `mike deploy`, the version is added to the `llms.txt` title and to the first line of `llms-full.txt`. In `llms.txt`, a page nested in one or more groups below its section is labelled with those groups, joined by ": ", such as "Audit Log Filter: Install". Pages directly in a section, top-level pages and nav entries without a title keep their own title.
- **`.html.md` copies.** Each markdown page is also written at its HTML URL plus `.md` (`install.html.md` next to `install.md`, `foo/index.html.md` with directory URLs), with the same content. llms.txt and the alternate link keep pointing to the `.md` files. `html_md: false` turns it off.
- **Descriptions.** Each entry of `llms.txt` gets `: <description>` unless it has one: the `description` in the page's front matter, or else the first sentence of the first paragraph that is directly in the page (not in an admonition, tab, table or list), cut at 200 characters with `…`. Descriptions under 15 characters are left out. `descriptions: false` turns it off.
- **Optional section.** With sections taken from `nav`, the sections named in `optional_sections` (default `Release notes`, matched ignoring case) are moved into the last section (`other_pages`, "Optional"), in nav order and ahead of the pages outside nav. With `other_pages: ''` or `sections` set by hand, nothing moves.
- **Alternate link.** Each HTML page has `<link rel="alternate" type="text/markdown" href="...">` in its `<head>`, and its hidden hint names the markdown URL.

## Empty summary

`site_description` in `mkdocs.yml` becomes the `> summary` line of `llms.txt`. If it is empty or just says `Documentation` or `docs`, the build logs this warning and carries on (with `--strict` the build stops):

```
WARNING - site_description is the summary line of llms.txt; describe the product in one sentence
```

## Options

```yaml
  percona-llmstxt:
    first_section: Overview  # section for top-level pages outside a nav group
    other_pages: Optional    # section for pages outside nav; '' leaves them out
    hint: true               # the hidden link to llms.txt in every HTML page
    html_md: true            # also write each markdown page as <page>.html.md
    descriptions: true       # add a one-line description to each llms.txt entry
    optional_sections: [Release notes]  # nav sections moved under the other_pages section; [] keeps them
```

## Check a site

[AFDocs](https://agentdocsspec.com/) scores a site against the Agent-Friendly Documentation spec:

```
npx afdocs check https://docs.percona.com/percona-operator-for-postgresql/latest/ --format scorecard
```

## Develop

```
python -m pip install --require-hashes --no-deps -r requirements-dev.txt
python -m pip install --no-deps --no-build-isolation .
ruff check . && ruff format --check . && mypy && pytest
```

`requirements-dev.txt` pins the tools and their hashes. To update it, edit `requirements-dev.in` and follow the command at its top.

## Release

1. Set the new `version` in `pyproject.toml` and merge it to `main`.
2. Tag that commit and push the tag: `git tag -a v0.4.1 -m v0.4.1 && git push origin v0.4.1`.

The Release workflow builds the package, checks that the tag matches the version, publishes it to TestPyPI and then, once a maintainer approves the `pypi` environment, to PyPI. Both use [trusted publishing](https://docs.pypi.org/trusted-publishers/), so the repo stores no PyPI tokens. Running the workflow by hand publishes to TestPyPI only.

## License

Apache License 2.0.
