# Changelog

## 0.4.1 - 2026-11-25

- Each markdown page is now also served at its HTML URL plus `.md` (`install.html.md` next to `install.md`), the form the llms.txt convention expects. llms.txt and the alternate links still point to the `.md` files. Turn it off with `html_md: false`.
- Each `llms.txt` entry now ends with a one-line description: the page's `description` front matter, or else the first sentence of its first paragraph. Entries that already have a description keep it. Turn it off with `descriptions: false`.
- Release notes now move into the last `## Optional` section of `llms.txt`, ahead of the pages that are outside the nav. Set `optional_sections` to choose which nav sections move (matched ignoring case; `[]` keeps them where they are). This needs `other_pages` to name a section, and does not apply when `sections` is set by hand.
## 0.4.0 - 2026-11-25

- Code blocks in the markdown pages now start with their language (for example `sql`), when the site uses `pymdownx.highlight`.
- Links from one page to another in the markdown pages now point at the `.md` copy instead of the `.html` page.
- Images keep their alt text in the markdown pages, as `Image: <alt text>`.
- During `mike deploy` (when `MIKE_DOCS_VERSION` is set), the `llms.txt` title and the first line of `llms-full.txt` now include the version being built. A page nested in groups below a section is labelled with those groups, joined by ": ", such as "Audit Log Filter: Install".
- Each HTML page now links to its markdown copy with `<link rel="alternate">` in the `<head>`, and the hidden hint for agents gives the markdown URL.
- The build now logs a warning when `site_description`, the summary line of `llms.txt`, is empty or just `Documentation` or `docs`.
