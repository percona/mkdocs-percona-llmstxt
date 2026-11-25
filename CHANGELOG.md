# Changelog

## 0.4.1 - 2026-11-25

- Each markdown page is now also served at its HTML URL plus `.md` (`install.html.md` next to `install.md`), the form the llms.txt convention expects. llms.txt and the alternate links still point to the `.md` files. Turn it off with `html_md: false`.
- Each `llms.txt` entry now ends with a one-line description: the page's `description` front matter, or else the first sentence of its first paragraph. Entries that already have a description keep it. Turn it off with `descriptions: false`. Details:
  - A description shared by 3 or more pages is dropped, front matter included, because it says nothing about any one page.
  - Spacing before punctuation left by inline links is tidied, and HTML escapes (`&lt;`) in front matter are decoded.
  - On a site that fills `description` with the meta-descriptions plugin, that plugin's text is used (capped at 200 characters, not cut to one sentence).
- Release notes now move into the last `## Optional` section of `llms.txt`, ahead of the pages that are outside the nav, and the labels of those that have a nav title start with the section name ("Release notes: Release notes index"). Set `optional_sections` to choose which sections move (matched ignoring case; `[]` keeps them where they are). Only top-level nav sections move, not nested groups. This needs `other_pages` to name a section, and does not apply when `sections` is set by hand. A nav group with the same name as `other_pages` (by default "Optional") now also moves to the end.
- All three changes are on by default. To get the 0.4.0 output back, set `html_md: false`, `descriptions: false` and `optional_sections: []` under `percona-llmstxt:`.

## 0.4.0 - 2026-11-25

- Code blocks in the markdown pages now start with their language (for example `sql`), when the site uses `pymdownx.highlight`.
- Links from one page to another in the markdown pages now point at the `.md` copy instead of the `.html` page.
- Images keep their alt text in the markdown pages, as `Image: <alt text>`.
- During `mike deploy` (when `MIKE_DOCS_VERSION` is set), the `llms.txt` title and the first line of `llms-full.txt` now include the version being built. A page nested in groups below a section is labelled with those groups, joined by ": ", such as "Audit Log Filter: Install".
- Each HTML page now links to its markdown copy with `<link rel="alternate">` in the `<head>`, and the hidden hint for agents gives the markdown URL.
- The build now logs a warning when `site_description`, the summary line of `llms.txt`, is empty or just `Documentation` or `docs`.
