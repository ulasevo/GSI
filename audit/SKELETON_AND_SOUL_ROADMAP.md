# GSI — Skeleton & Soul Master Roadmap (`audit/SKELETON_AND_SOUL_ROADMAP.md`)

**Date:** 2026-09-22
**Scope:** Deep architectural & experiential forward plan covering (I) **The Skeleton** (structural, pipeline, template, data, and CSS/JS engineering improvements) and (II) **The Soul** (identity-preserving features that deepen GSI as a personal memory archive, visual listening room, and Radio P53 broadcast).

---

## Part I — The Skeleton (Structural & Engineering Roadmap)

Even after the recent modular split (`builder/*.py`, `gsi_*.py`, `web/scripts/*.js`, `web/styles/**/*.css`), the codebase is halfway between its original monolithic script and a clean 1.0 static-site architecture. Below are the exact structural seams that can be tightened next, ranked by architectural impact.

### S1. Reconcile the `ALBUMS` Eligibility Split Across Homepage vs Catalogue Rooms
- **Where the seam lives:**
  - `builder/catalog_pages.py` (`build_album_pages`, line 154) generates **35 standalone Album Rooms** (`site/albums/*.html`) — one for every album in the archive, including single-signal albums.
  - `builder/catalog_pages.py` (`build_artist_pages`, line 55) groups **all** albums inside Artist Rooms (`grouped_albums = [(album, items) for album, items in albums.items() if items]`).
  - However, `web/scripts/home-format.js` (line 88) still enforces `if (!album || groupCards.length < 2) return;` when the user clicks `ALBUMS` on the Homepage (`index.html?format=albums`), and `renderFilterAlbumGroups` only renders album stacks for 2+ song albums (`Metric — Live It Out` and `Matt Maeson — A Quiet And Harmless Living`), hiding 23 of the 25 albums in the archive.
- **Structural fix (when ready):**
  - Align `web/scripts/home-format.js` with `builder/catalog_pages.py` so that when `format === "albums"` is explicitly selected on the Homepage, single-signal albums also render as clickable album cards routing to their already-generated `site/albums/<slug>.html` rooms (while keeping `groupCards.length >= 2` for automatic inline grouping inside `SONGS` filter views so the song wall doesn't get cluttered).

### S2. Finish HTML Extraction from Python Renderers (`builder/*.py` → `templates/`)
- **Where the seam lives:**
  - `builder/template_renderer.py` performs flat `{{key}}` string replacement on `templates/*.html`, which forced `builder/home_page.py`, `builder/entry_pages.py`, `builder/p53_pages.py`, and `builder/catalog_pages.py` to keep ~350 lines of multi-line HTML f-strings inside Python (`cards`, `filters_html`, `section_cards`, `album_sections`, `transmission_card`).
  - Additionally, `builder/catalog_pages.py` (lines 129–133 and 210–214) injects `<link rel="stylesheet" href="../styles/artist-art.css?v=20260919-contrast">` by calling `page.replace("</head>", ...)` after template rendering instead of declaring the stylesheet inside `templates/artist.html` and `templates/album.html`.
- **Structural fix:**
  - Move the `<link rel="stylesheet">` tags directly into `templates/artist.html` and `templates/album.html`.
  - Extract repeatable HTML fragments (`card`, `section-card`, `transmission-card`, `album-stack`) into either small sub-templates in `templates/partials/` or Jinja2 templates (as outlined in `AGENTS.md` for post-1.0), so HTML markup and ARIA attributes live exclusively in `.html` files and Python only prepares dicts.

### S3. Replace Module-Level Global Syncing with an Explicit `BuildContext`
- **Where the seam lives:**
  - `build.py` (lines 68–88, `_sync_stage_globals()`) mutates module-level global variables (`BASE`, `CONFIG_FILE`, `TRACKS_FILE`, `ENTRIES_DIR`, `SITE_DIR`, etc.) across 5 imported modules before every build step to support legacy tests that monkeypatch `build.BASE`.
- **Structural fix:**
  - Introduce a single frozen dataclass `BuildPaths` / `BuildContext` in `gsi_data.py` (holding `base`, `config_file`, `tracks_file`, `entries_dir`, `covers_dir`, `site_dir`) and pass `ctx` explicitly to every `builder/*.py` entrypoint. Keep a thin shim in `build.py` only if legacy tests still mutate `build.BASE`.

### S4. Persistent Build Cache for Artwork Palettes & Canonical Provider URLs
- **Where the seam lives:**
  - `gsi_assets.py` (`artwork_palette`) decodes and samples image pixels for every track, P53 item, artist room, and album room on every build.
  - In `tools/overnight_audit.py`, Spotify links are currently **0/40 canonical** (`"spotify": {"canonical": 0, "search": 40}`), meaning every `Spotify ↗` button on every Entry and P53 page opens a generic Spotify search results page instead of the song itself, whereas Apple Music is **40/40 canonical**.
- **Structural fix:**
  - Add a tracked JSON cache (`data/signal_enrichment.json` or `build_cache.json`) keyed by `signal_id` + cover file SHA/mtime that stores:
    1. Pre-computed `artwork_palette` hex tokens (cutting `--site-only` build time by ~75%).
    2. Canonical Spotify track URLs (resolved once via Odesli / MusicBrainz / Spotify lookup from the existing canonical Apple Music track IDs) and optional Apple `previewUrl` audio snippets.

### S5. Build-Time CSS Concatenation & Automatic Asset Cache-Busting
- **Where the seam lives:**
  - `web/styles/styles.css` uses 5 runtime `@import url("./home/...")` statements, which forces browsers to make sequential waterfall HTTP requests before first paint.
  - Version strings like `?v=20260919-contrast` are hardcoded in templates and Python files, meaning CSS edits can be served stale from browser cache unless manually bumped.
- **Structural fix:**
  - In `build.py` (`copy_static_web_assets`), inline local `@import` files into a single built `site/styles/styles.css` (while keeping `web/styles/home/01..05.css` modular in source!) and automatically append a short 8-char SHA-256 content hash (`?v=a4f91c2b`) to all `<link rel="stylesheet">` and `<script src="...">` URLs during template rendering.

---

## Part II — The Soul (Identity, Memory & Atmosphere Roadmap)

GSI's soul comes from three things that no commercial music platform has:
1. **Unfiltered personal taxonomy** (`Charge`, `Sonical Attraction`, `Lyric/Vocal Detail`, `Version of ulaş`, `Lore`, `Reading`, `Comment`).
2. **Biological / stress-response framing** (*Genome Stability Inducers* + *Radio P53* as the protein upregulated during cellular damage or stress — songs kept on loop to hold the organism together).
3. **Expressive physical rooms** (poster-wall brutalism on the outside; color-field shrines derived from each album's cover palette on the inside).

Here are the highest-leverage implementations that deepen that soul without turning GSI into a generic music site:

### A1. "Read by Lens" — Cross-Archive Section Threads (`Version of ulaş`, `Lore`, `Charge`)
- **The Opportunity:**
  - Right now, your 7 custom sections only exist *vertically* inside a single song's Entry Room. If someone wants to read every `"Version of ulaş"` across all 27 entries (which together form an autobiography in songs), or every `"Sonical Attraction"` production note, they have to click into 27 separate pages.
- **The Soul Implementation:**
  - Make the section titles or a small link inside the `i` info disclosure (`"See all 19 signals with a 'Version of ulaş' ↗"`) open a dedicated **Lens View** (or filter mode) that stacks just that section's cards across the archive, painted in each song's cover palette.
  - Reading all `"Version of ulaş"` cards in chronological or P53 order turns GSI into a living memoir indexed by music.

### A2. Surface `p53_transmission_notes` Directly on the Radio P53 Stream
- **The Opportunity:**
  - In `config.json`, `p53_transmission_notes` contains some of the best voice in the repository:
    - *Mayonaka No Door ~Stay with Me*: `"life is giving main character lately, I'd be wrong not to have this song as my soundtrack for the duration"`
    - *Secret Door*: `"I guess the 'OooOo' by the crowd in the background is supposed to represent the parade of fools singing, fantastic song."`
    - *Too Little Too Late*: `"tie my right hand to the bible"`
    - *Stubborn As Religion*: `"such a strong vocal, this man"`
  - Yet on `/p53/index.html`, every card in the stream hides this note and only renders generic metadata (`PAST TRANSMISSION / Track / Artist / Album / ENTER TRANSMISSION ↗`).
- **The Soul Implementation:**
  - Render `p53_transmission_notes[slug]` directly on the `/p53/index.html` transmission cards as a styled **broadcast intercept quote** (e.g. mono/italic dispatch line right below the album title).
  - Add a lightweight command in `gsi_session.py` / `gsi_Entry.py` to jot down a 1-sentence `p53_transmission_note` whenever rotating or adding a P53 track so the P53 stream reads like a continuous late-night radio logbook.

### A3. Tactile 30-Second "Signal Audition" (Zero-Iframe Audio Preview)
- **The Opportunity:**
  - GSI is a "visual listening environment," yet clicking `Spotify ↗` or `Apple Music ↗` immediately ejects the visitor out of GSI's color-field shrine into an external app. Meanwhile, embedding standard Spotify/Apple iframes would ruin GSI's typography and palette aesthetic.
- **The Soul Implementation:**
  - Because `builder/source_pipeline.py` already queries the iTunes Search API (`https://itunes.apple.com/search?...`), every track response already includes an unauthenticated, high-quality 30-second AAC `previewUrl` from Apple's CDN.
  - Store `preview_url` during source preparation and add a custom GSI pill button next to the streaming links inside Entry and P53 rooms:
    `[ ◉ AUDITION SIGNAL 0:30 ]`
  - Clicking it plays the 30-second stem directly inside the room while subtly pulsing the cover frame's `--art-glow` shadow to the audio amplitude (via Web Audio API `AnalyserNode`), keeping the listener inside the shrine.

### A4. Spatial View Transitions Between the Archive Wall & Entry Shrines
- **The Opportunity:**
  - Moving from `index.html` (the dark signal room) to `entries/<slug>.html` (the color-field shrine) currently triggers a hard browser page reload jump.
- **The Soul Implementation:**
  - Add `@view-transition { navigation: auto; }` in CSS and assign deterministic `view-transition-name` tokens to the clicked card's `<img>` cover and title (`home-state.js` / `entry-page.js`).
  - When a user clicks *Empty* or *Stubborn As Religion* on the Homepage Wall, the album cover physically glides and expands into the Entry Shrine's `.cover-frame` while the dark grid dissolves into the album's extracted `--art-bg-top` / `--art-primary` atmosphere.

### A5. Enriching Album & Artist Shrines (`gsi_Entry.py` Note Authoring + Album Arc Context)
- **The Opportunity:**
  - `config.json` has `artist_notes` (3 of 28 artists populated) and `album_notes` (3 of 35 albums populated). When an Artist or Album room has a note (like *Live It Out*: *"I don't think I repeated an album more in my life, I am it and it is me"*), the room feels deeply personal. When it doesn't, it feels like an automated index page.
- **The Soul Implementation:**
  - Extend `gsi_Entry.py` (your interactive authoring CLI) so after saving a song entry, it optionally prompts: *"Add or update your 1-line take on [Artist] or [Album]? (Enter to skip)"*, saving directly into `config.json`.
  - In Album Rooms (`builder/catalog_pages.py`), display the album's release year and track number for each archived signal (available from the existing iTunes lookup payload: `releaseDate`, `trackNumber`, `trackCount`, e.g. `SIGNAL 02 OF 10 · 2005`) so even a single-song Album Room feels like holding the physical record sleeve.

---

## Summary Priority Matrix

| Tier | Item | Effort | Payoff |
| :--- | :--- | :--- | :--- |
| **Tier 1 (Quick Structural & Soul Wins)** | **A2.** Surface `p53_transmission_notes` on `/p53/index.html` stream cards<br>**S1.** Align `ALBUMS` format view (`home-format.js`) with generated Album Rooms<br>**A4.** Add `artist_notes` / `album_notes` prompt to `gsi_Entry.py` | Small (1–2 files each) | Immediate voice & navigation payoff |
| **Tier 2 (Atmosphere & Listening Experience)** | **A3.** 30-second native `AUDITION SIGNAL` audio player with cover glow pulse<br>**A5.** Cross-document CSS `@view-transition` cover morphing<br>**A1.** "Read by Lens" cross-archive section reader (`Version of ulaş`, `Lore`, etc.) | Medium | Transforms GSI into a true interactive listening & memory room |
| **Tier 3 (1.0 Pipeline Hardening)** | **S4.** Persistent `signal_enrichment.json` cache (palettes + canonical Spotify URLs)<br>**S5.** Build-time CSS `@import` bundling & content-hash `?v=` cache busting<br>**S2/S3.** `BuildContext` dataclass + full HTML partial extraction | Medium | Instant builds, 100% canonical streaming links, zero stale mobile CSS |
