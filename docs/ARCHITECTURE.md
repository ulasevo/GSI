# GSI Technical Architecture

This document provides a concise reference for the **Genome Stability Inducers** build pipeline, data relationships, and browser layer.

---

## 1. High-Level Pipeline

The build transforms raw authoring inputs into a pure static website:

```text
tracks.csv + config.json + entries/*.md + covers/ + artist-assets/
                            ↓
               [builder/source_pipeline.py]
    Normalizes metadata, extracts colors, calculates P53 history
                            ↓
                [gsi_data.py & manifests.py]
        Builds route inventory & relationship graphs
                            ↓
               [builder/*_pages.py + templates/]
           Fills HTML skeletons with sanitized markup
                            ↓
        [web/styles/ & web/scripts/ & asset copiers]
       Assembles CSS token layers and browser controllers
                            ↓
                          site/
        (Static HTML, CSS, JS, optimized WebP & JPEGs)
```

---

## 2. Directory Responsibilities

| Directory | Responsibility | Invariants & Editing Rules |
| :--- | :--- | :--- |
| `entries/*.md` | Authentic personal review prose. | **Source of truth.** Never overwrite or delete prose sections. |
| `tracks.csv` | Song catalog metadata and tags. | Preserve title/artist casing and comma quoting. |
| `config.json` | Filter definitions, notes, P53 state. | Validated via `python -m json.tool config.json`. |
| `covers/` | Local album & playlist artwork. | Square or high-res images, optimized during build. |
| `artist-assets/` | High-res 1000×1000 artist portraits. | Managed via `tools/fetch_artist_art.py`. |
| `templates/` | Semantic HTML5 page skeletons. | Contain marker tokens; no data processing logic. |
| `web/styles/` | Modular stylesheets and design tokens. | Assembled into `site/styles/`; strictly tokenized. |
| `web/scripts/` | Client-side reactive JavaScript. | Vanilla ES6+ modules; zero external dependencies. |
| `builder/` | Python build pipeline modules. | Dedicated page renderers and pipeline steps. |
| `tools/` | Private authoring and review scripts. | Local-only tools; never exposed to public deployment. |
| `site/` | Generated build artifact. | **Read-only generated output.** Never edit manually. |

---

## 3. Python Builder Architecture

- **`build.py`**: Stable CLI entry point supporting `--site-only`, `--validate-links`, and `--audit-provider-links`.
- **`builder/source_pipeline.py`**: Reads `tracks.csv`, computes dominant colors and rim gradients, ensures signal IDs, and validates frontmatter.
- **`builder/template_renderer.py`**: High-performance template renderer that populates `templates/*.html` with clean markers.
- **`builder/catalog_pages.py`**: Generates artist listening rooms (`/artists/<slug>.html`) and album shrines (`/albums/<slug>.html`).
- **`builder/entry_pages.py`**: Generates song entry rooms (`/entries/<slug>.html`).
- **`builder/home_page.py`**: Generates the primary index (`/index.html`).
- **`builder/p53_pages.py`**: Generates Radio P53 landing and transmission archives.
- **`gsi_*.py`**: Domain utilities for asset resolution, link normalization, text slugification, and source validation.

---

## 4. Browser Architecture

The browser layer adheres to a strict separation of concerns:
1. **HTML** assigns semantic classes and stable `data-*` attributes (`data-view`, `data-format`, `data-active-filter`).
2. **JavaScript** listens for user actions, updates document state, and synchronizes URL query parameters.
3. **CSS** responds to state attributes on `<body data-view="..." data-format="...">` to recompute layout, visual tints, and animations.

### Layout & View States
- **Views**: `wall` (2×2 dense grid), `poster` (tall cinematic cards), `gallery` (spacious record layout). Handled by `web/scripts/home-layout.js` and styled via `web/styles/home/`.
- **Formats**: `songs` (flat song wall) vs. `albums` (grouped by album disc). Handled by `web/scripts/home-format.js`.
- **Theme Persistence**: Light and dark modes driven by `web/scripts/theme-mode.js` with `localStorage["gsi-theme"]` priority over transient query strings.
- **Art Tint Engine**: Album covers are color-sampled at build time to provide `--art-card-rim-gradient`, `--art-primary`, and `--art-secondary` CSS variables dynamically injected per card.

---

## 5. Security & Isolation Architecture

1. **Static Public Footprint**: GitHub Pages serves only compiled static assets from `site/`. No Python code, API endpoints, or database processes run on the public host.
2. **Authenticated Private Boundary**:
   - `tools/submission_server.py` guards local authoring routes (`/api/local-*` and `/__local/*`).
   - Requests from outside loopback (`127.0.0.1`) strictly require a matching bearer token or query token via constant-time HMAC comparison (`hmac.compare_digest`).
   - Tokens are stored exclusively in the author's local browser `localStorage` or environment variables—never in source control or public manifests.
3. **Transactional Authoring Rollback**:
   - Every authoring publish automatically captures a timestamped snapshot of modified files in `submissions/snapshots/` before writing changes.
