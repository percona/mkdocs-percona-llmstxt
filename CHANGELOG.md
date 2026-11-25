# Changelog

## 0.4.0 - 2026-11-25

- Code blocks in the markdown pages now start with their language (for example `sql`), when the site uses `pymdownx.highlight`.
- Links from one page to another in the markdown pages now point at the `.md` copy instead of the `.html` page.
- Images keep their alt text in the markdown pages, as `Image: <alt text>`.
- During `mike deploy` (when `MIKE_DOCS_VERSION` is set), the `llms.txt` title and the first line of `llms-full.txt` now include the version being built. A page nested in groups below a section is labelled with those groups, joined by ": ", such as "Audit Log Filter: Install".
- Each HTML page now links to its markdown copy with `<link rel="alternate">` in the `<head>`, and the hidden hint for agents gives the markdown URL.
- The build now logs a warning when `site_description`, the summary line of `llms.txt`, is empty or just `Documentation` or `docs`.
