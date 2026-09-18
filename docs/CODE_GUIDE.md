# GSI code guide

This is a short map for taking authorship back. The source tree is the thing to
edit; `site/` is generated output and should not be edited by hand.

For the browser layer specifically, continue with
[docs/CSS_JS_GUIDE.md](CSS_JS_GUIDE.md).

## The build in one sentence

`build.py` reads the editable catalogue and config, prepares stable records,
passes those records to page builders, and writes the generated site.

```text
tracks.csv + config.json + entries/*.md + covers/
        ↓
source preparation and route relationships
        ↓
page builders + templates/
        ↓
site/ (HTML, styles, scripts, images, manifests)
```

## Where a change belongs

| If you want to change… | Start here | What it owns |
| --- | --- | --- |
| A song, tag, album, provider link, or order | `tracks.csv` | The editable catalogue row |
| Filter wording, colors, playlists, P53 settings | `config.json` | Site-wide authored configuration |
| Review writing or section content | `entries/*.md` | Irreplaceable personal prose |
| How source records are prepared | `builder/source_pipeline.py` | Covers, metadata, and P53 records |
| Which routes exist | `gsi_data.py` and `builder/manifests.py` | Shared route relationships and counts |
| Entry, artist, album, home, or P53 markup | The matching file in `builder/` | Data preparation for one page family |
| Page shape and marker placement | `templates/*.html` | The HTML skeleton, not the data rules |
| Browser behavior | `web/scripts/*.js` | State, links, and small interactions |
| Appearance | `web/styles/*.css` | Layout, color, type, and responsive rules |
| Build checks | `gsi_validation.py` and `tests/` | Rules that catch broken sources or output |

## The page path

1. `build.py` chooses the source and output directories and starts the build.
2. `builder/source_pipeline.py` turns CSV/config/source files into prepared song
   records. It may update metadata when doing a normal build; `--site-only`
   reads sources without changing them.
3. `gsi_data.py` groups records and derives the shared route inventory. The page
   builders use this same inventory, so links and generated filenames agree.
4. A page builder prepares escaped text and small HTML fragments, then calls
   `builder/template_renderer.py` with a named template and explicit markers.
5. The browser receives HTML plus JSON data nodes. External scripts read those
   nodes and preserve query state or add small interactions.
6. `gsi_assets.py` copies images, styles, and scripts into `site/`; validators
   then check that the generated relationships and local files resolve.

## Plain-language comment rules

Comments should help a future reader answer one of these questions:

- What does this file or section own?
- What shape of information comes in and goes out?
- Why is this guardrail or fallback necessary?
- Which user-facing promise must not change?

Do not comment obvious syntax. Prefer one useful explanation before a group of
related lines over a comment on every assignment. Keep the wording concrete:
“Keep the album visible when any represented song matches the filter” is more
useful than “Apply album filtering logic.”

Python uses `#`, JavaScript and CSS use `/* … */`, and templates use
`<!-- … -->`. Comments must not contain secrets or private review writing.

## A safe editing loop

1. Write down the user-visible change in one sentence.
2. Find the owning source file from the table above.
3. Read the surrounding function or selector before editing it.
4. Make the smallest named change and add a “why” comment only if the choice is
   not obvious.
5. Run the focused test first, then `python -m py_compile`, the full tests, and
   `python build.py --site-only --validate-links`. For browser-state changes,
   also run `node tests/test_browser_contract.js`.
6. Inspect the generated HTML/CSS/JavaScript when those layers changed.
7. Check the diff before committing; never use generated `site/` files as the
   source of a lasting feature.

## What is intentionally separate

The migration keeps the build, page templates, browser behavior, and visual
rules in separate homes without turning GSI into a large framework. The next
visual or feature change should therefore be understandable as a small chain:
source/config → prepared record → template or script/style → generated check.
