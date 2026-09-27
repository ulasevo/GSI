# GSI Project State

This document records project intent, implemented systems, design history, unresolved problems, and the planned roadmap.

The repository files are the authority on what is currently implemented. This document is the authority on why the project was designed this way and where it is intended to go.

If the files and this document disagree, report the discrepancy rather than silently choosing one.

## 2026-09 reconciliation

This document preserves useful design history, but several of its phase labels now describe completed work rather than the current order of operations. In particular, the filter-room transition and Radio P53 landing/permanent pages are implemented in the source tree; P53 is no longer a post-1.0 future feature.

For the current implementation sequence, use the **Current operating ledger** near the end of this file. It replaces the former scattered roadmap, migration, audit, and navigation-note files. The historical sections below should not be treated as a request to undo implemented systems.

The post-1.0 migration is now authorized and underway. `build.py` is the stable
CLI/API facade; source preparation, page renderers, and output manifests live in
named `builder/` modules while `builder/legacy_pipeline.py` contains
orchestration and compatibility exports only. Page templates live in
`templates/`; shared CSS and browser helpers live in `web/styles/` and
`web/scripts/`. The current operating ledger records the remaining parity and
device/deployment checks. For a plain-language map of these boundaries and a
safe editing loop, use [docs/CODE_GUIDE.md](docs/CODE_GUIDE.md).

-What GSI is

GSI began as a place to archive songs that do something more significant than merely sounding good.

“Genome Stability Inducers” is your metaphor for music that stabilizes, mutates, preserves, awakens, distorts, or carries versions of you. The name borrows from genomic stability, but the archive is not pretending to be a scientific resource. It is personal language.

The project has two equally important products:

The archive itself — songs, reviews, notes, memories, classifications, and recurring projects such as P53.
The machinery — the Python builder, metadata system, filters, generated pages, visual logic, and eventually deployment.

The machinery must serve the archive. Coding is not supposed to consume the writing permanently, though it is valid for coding and writing to alternate depending on your available attention.

The site should eventually contain a mixture of:

fully written phenotype-style entries;
shorter signal notes;
sonic observations;
lore/history notes;
songs that are simply important enough to catalogue.

Not every entry needs to resemble the long review for “Empty.” A few dozen short entries plus approximately ten substantial pieces would already give the archive meaningful weight.

- Current folder model

The working structure should approximately be:

GSI/
├── build.py
├── config.json
├── tracks.csv
├── entries/
│   ├── artist-track.md
│   └── ...
├── covers/
│   ├── album-cover.jpg
│   ├── playlist-cover.jpg
│   └── ...
├── site/
│   ├── index.html
│   ├── entries/
│   │   ├── artist-track.html
│   │   └── ...
│   └── ...
├── AGENTS.md
└── PROJECT_STATE.md

The conceptual ownership is:

tracks.csv contains song-level structured data.
config.json contains site-level and filter-level behavior.
entries/*.md contains your writing.
covers/ contains controllable local visual assets.
build.py transforms sources into the website.
site/ is generated public output.

- Current song data

tracks.csv has grown throughout the project. Codex needs to inspect the real header, but the intended fields are approximately:

order,tags,artist,track,album,cover_file,cover_url,accent,spotify_url,apple_url

The intended rules are:

artist, track, and album are core metadata.
order optionally controls manual display order.
tags accepts one or multiple filters.
Multiple tags must be quoted because CSV commas separate fields:
1,"personal, ulass-selection",Metric,Empty,Live It Out,...
cover_file points to a local image and should be preferred.
cover_url is an optional direct web image URL.
accent is an optional manual hex override.
spotify_url and apple_url are optional exact song URLs.
Blank streaming URLs produce automatic search links.

The cover priority is intended to be roughly:

local cover_file
→ manual cover_url
→ automatic iTunes search/download
→ previously cached cover/fallback

Codex must confirm the exact current order in build.py.

- Configuration model

config.json controls stable site behavior rather than individual songs.

It has included fields such as:

{
  "project_title": "...",
  "page_title": "...",
  "intro": "...",
  "newest_first": true,
  "force_refresh_covers": false,
  "filters": {},
  "sections": []
}

Each filter contains approximately:

"personal": {
  "label": "Personal",
  "description": "Songs that got tangled with memory, body, recovery, desire, or some version of me.",
  "color": "#d64b6a",
  "playlist_url": "...",
  "playlist_cover": "covers/personal-playlist.jpg",
  "playlist_cta": "Want more of the same?"
}

Filter keys must exactly match values used in tracks.csv.

Stable filter identity belongs in config.json. Song-specific information belongs in tracks.csv.

- Builder behavior already implemented

The legacy renderer is still present as a compatibility boundary; the root
`build.py` is now only a compatibility facade. Page markup lives in `templates/`,
CSS and JavaScript live in `web/styles/` and `web/scripts/`, and source
preparation lives in `builder/source_pipeline.py`.

It currently performs most or all of these jobs:

Data loading
Reads tracks.csv.
Reads config.json.
Orders tracks manually when order values exist.
Otherwise respects newest_first.
Cover handling
Uses local cover overrides.
Uses direct cover URLs.
Searches/downloads artwork through iTunes.
Caches images in covers/.
Avoids crashing completely when a remote image fails.
Accent extraction

The first implementation simply picked the most common image color, which frequently produced gray or nearly black accents.

The newer version:

reduces the image to a palette;
converts candidate colors to HSV;
rejects overly dark, overly pale, or desaturated candidates;
scores remaining colors based on saturation, brightness, and frequency;
allows a manual accent value to override the automatic result.

This significantly improved card borders and glows, although hand-picked overrides remain necessary for subjective cases such as ASTROWORLD or Live It Out.

Markdown entry safety

The builder creates a Markdown entry only when one does not already exist.

Existing files should:

retain all written review content;
receive corrected metadata when CSV values change;
receive newly introduced section headings if missing;
never have prose overwritten.

Hidden HTML comments beneath headings act as writing prompts but are stripped before rendering.

Entry-page generation

Each Markdown entry becomes a styled HTML page under:

site/entries/

Entry pages include:

album cover;
song title;
artist;
album;
accent-derived atmosphere;
rendered review sections;
Spotify and Apple Music links;
automatic search fallbacks when exact links are blank.

Streaming links were changed from pill-like controls toward quieter outbound actions:

Have a listen on:
Spotify ↗    Apple Music ↗
Homepage generation

The homepage includes:

GSI wordmark/hero;
project introduction;
filter controls;
active-filter description;
album-card grid;
dynamic show/hide filtering;
accent borders and glow;
playlist module support.

Clicking an active filter again clears it and restores all entries.

- Visual history and current design state

The original homepage was functional but generic.

A first identity pass added:

a large GSI wordmark;
skew;
colored shadow offsets;
a dark textured background;
stronger card glow;
more stylized filter controls.

That attempt drifted toward neon/cyber-grid rather than the intended Need for Speed: Most Wanted 2005 / industrial street / distressed garage language.

The useful parts retained were:

stronger hierarchy;
better filter controls;
more expressive album accents;
improved card hover behavior;
some title shimmer/wobble behavior.

The unresolved visual direction is not supposed to be a literal game replica. The desired vocabulary is closer to:

asphalt;
garage posters;
industrial labels;
stencil/distressed typography;
scratches and cut lines;
speed or scanner-like motion;
layered print misalignment;
loud homepage and intimate entry pages.

The site should not be entirely black/yellow or permanently grungy. Album artwork and filter colors still need room to shape the atmosphere.

- Latest implemented feature: filter playlists

Playlist support was added at the filter level.

A filter can provide:

playlist_url;
playlist_cover;
playlist_cta.

The builder:

loads the local playlist cover;
reuses the accent-extraction algorithm;
generates playlist data for JavaScript;
displays or hides the playlist card according to the selected filter.

The current playlist presentation is approximately:

[ square playlist cover ]
Want more of the same? ↗

It appears to the right of the active filter description.

The feature works, but the layout is unresolved. The large playlist card increases the height of the filter section, leaving substantial unused space beneath the short description and pushing the song grid downward.

You did not necessarily dislike the card’s size or placement. You disliked that the rest of the composition failed to respond to it.

Therefore, the playlist card should not simply be reduced or removed without discussing the surrounding transition.

- Exact current design problem

Default homepage state:

Hero
General GSI introduction
Filter buttons
All entries

Current filtered state:

Hero
General GSI introduction
Filter buttons
Filter description               Large playlist card
                                  Large vertical space
Filtered entries

The next design idea was to turn filter selection into a complete temporary “room.”

Proposed filtered state:

Hero
[general introduction fades/collapses]
Selected filter title + description       Playlist card
Filter-colored atmosphere
Filtered entries move upward

Clearing the filter would reverse the transition:

filter atmosphere fades;
playlist disappears;
filter description collapses;
project introduction returns;
all cards return.

The transition must be smooth and work on mobile. It should use a class such as:

document.body.classList.add("filter-active");

CSS then reacts to that class instead of JavaScript manually animating every property.

This was designated Patch 14 — Filter Room Transition.

It has not yet been completed.

- Likely GSI 1.0 roadmap

The priority list changed several times, but the coherent current route is:

Phase 1 — audit and repair

Codex should first:

compile Python;
validate JSON;
inspect the CSV header;
run the build;
look for malformed generated HTML/CSS;
identify lingering transcription errors;
verify streaming links;
verify playlist show/hide behavior.

No redesign should occur during the audit.

Phase 2 — filter-room transition

Implement:

subtle whole-page tint from active filter color;
general intro fade/collapse;
active filter area expansion;
playlist and filter description composition;
smooth restoration on clear;
reduced-motion fallback if practical.
Phase 3 — mobile integration

Do this only after the filter and playlist layout is structurally settled.

Mobile work must cover:

hero scaling;
filter wrapping;
filter-room layout;
playlist placement;
card grid;
entry hero;
streaming links;
hover-dependent interactions;
section help controls later.
Phase 4 — section information controls

Add small i controls beside section names.

Examples:

Charge ⓘ
Sonical Attraction ⓘ
Version of Ulaş ⓘ

They explain GSI’s private terminology.

These cannot be hover-only because phones do not have reliable hover. They should work with:

hover;
keyboard focus;
click/tap;
accessible text relationships.

Descriptions should be stored centrally, likely in config.json or a section-definition structure.

Phase 5 — deployment

The generated site/ folder should become available through a normal URL.

Python remains private build machinery. Visitors receive static HTML, CSS, JavaScript, and images; they do not need Python.

A stable GSI 1.0 deployment should happen before P53.

Phase 6 — content expansion

Once 1.0 is stable:

add the older P53 selections;
build toward 30–50 entries;
keep a mixture of short and long pieces;
prevent one artist or genre from unintentionally defining the archive.
Phase 7 — refactor

After 1.0, freeze a stable version and refactor on a branch.

Highest-value order:

Extract CSS.
Extract JavaScript.
Introduce templates.
Add input validation.
Add tests.
Split Python where justified.

The current f-string architecture should not remain forever, but rewriting it before 1.0 would risk losing momentum and introducing broad regressions.

Phase 8 — P53

Only after the baseline archive is stable.

- Radio P53 plan

Radio P53 is your weekly Wednesday song-sharing ritual.

The name comes from p53 as “guardian of the genome,” matching your view of music on a smaller, recurring scale.

The future implementation should use the code key:

p53

not radio-p53.

Each weekly selection should:

exist as a normal GSI song entry;
receive the p53 tag;
have a permanent weekly page;
retain a stable Instagram story link;
offer Spotify and Apple Music choices;
connect to the P53 playlist;
remain accessible after the week ends.

Possible permanent URL form:

site/p53/2026-08-05-song-slug.html

Potential convenience URL:

site/p53/latest.html

The weekly workflow should eventually be close to:

Add one song record.
Add a date and short note.
Run the builder.
Copy the generated permanent link.
Share on Instagram.

No weekly coding.

P53 should become a doorway into GSI, not a separate project bolted onto unstable machinery.

- Post-1.0 architecture

A likely cleaner structure:

GSI/
├── build.py
├── builder/
│   ├── config.py
│   ├── tracks.py
│   ├── covers.py
│   ├── markdown.py
│   └── pages.py
├── templates/
│   ├── index.html
│   ├── entry.html
│   └── p53.html
├── assets/
│   ├── css/
│   │   ├── base.css
│   │   ├── homepage.css
│   │   └── entry.css
│   └── js/
│       └── homepage.js
├── entries/
├── covers/
├── tracks.csv
├── config.json
└── site/

This is the expected destination for the active migration. Work remains staged so
the existing CLI, generated routes, and authored writing can be checked after each
boundary rather than replaced in one opaque rewrite.

Templates would eliminate most giant HTML strings.

External CSS and JavaScript would eliminate doubled-brace confusion:

.card {
    display: flex;
}

instead of:

f"""
.card {{
    display: flex;
}}
"""

## Current operating ledger — 2026-09-22

This is the single active project-notes file. It is intentionally separate from
the source files themselves: `entries/*.md`, `tracks.csv`, `config.json`, and
the implementation are the authority for content and behavior. The ledger is
the authority for current work order, release scope, and deliberate deferrals.

### Source map and boundaries

- `tracks.csv` — song-level catalogue metadata, filters/tags, links, cover
  choices, accents, and P53 membership/order.
- `entries/*.md` — irreplaceable authored writing. Never overwrite or remove
  review prose while synchronizing metadata.
- `config.json` — site copy, filter definitions, section definitions, and
  stable site behavior.
- `covers/` and `artist-assets/` — local artwork and reviewed artist assets.
- `builder/`, `gsi_*.py`, and `build.py` — source preparation and rendering;
  `build.py` remains the stable CLI facade.
- `templates/`, `web/styles/`, and `web/scripts/` — generated-page structure,
  styles, and browser behavior.
- `site/` — generated output. It is rebuilt, not hand-edited, and is not a
  source-of-truth workspace.
- `tools/` and `tests/` — local authoring, validation, and regression support.
- `archive/` — historical snapshots and intentionally retained pre-v2.0
  material; it is not active work.

### Implemented and accepted

- The local entry loader/editor can create or update the catalogue row, entry,
  cover boundary, album room, artist room, authored room notes, and optional
  P53 transmission in one transactional publish path.
- Existing authored entries are protected; failed publishing restores source
  files and attempts a recovery build.
- P53 has permanent/current transmission pages, correct latest-first ordering,
  a runtime-sized cover derivative, compact card gradients, and lazy historical
  card work where appropriate.
- Album and artist rooms are generated from represented catalogue signals while
  preserving exact album-title casing and authored notes.
- Theme state persists across raw internal navigation. An explicit `theme=` URL
  value wins; otherwise the saved preference is applied before first paint.
- Entry and P53 mobile overflow/sticky-path issues have bounded fixes. Entry
  cards and P53 cards use compact rim gradients instead of repeated 32-stop
  inline gradients; the large artwork atmosphere remains intentional.
- Album artwork resolution is now quality-checked during download. Dimensioned
  provider URLs are upgraded toward 1200px, invalid/too-small downloads are
  rejected, and catalogue/publish receipts classify the delivered artwork.
- The private Entry Loader accepts a reviewed artist image by file picker or
  drag/drop, validates its type/size/dimensions, stores it in `artist-assets/`,
  and registers it transactionally in `config.json`.
- Every successful local publish now records an ignored, source-only snapshot
  under `submissions/snapshots/`; the receipt carries its ID and
  `tools/restore_snapshot.py` can explicitly restore it before a regeneration.
- The public Entry Loader and private editor now share one browser draft contract
  (`tools/editor/draft-contract.js`), including canonical record fields,
  section shape, P53 state, catalogue notes, artwork metadata, and client-side
  validation. The generated loader copies this helper beside its script.
- The source preflight now requires `p53_current_slug` to identify the final
  `p53_history` record, making the newest-first transmission ordering an
  explicit data contract instead of a renderer assumption.
- Catalogue rows and P53 appearance records now carry durable `signal_id`
  values. `p53_current_signal_id` is the authoritative current-transmission
  pointer while `p53_current_slug` remains a route-compatible mirror; loader
  edits preserve IDs and generated manifests expose them for future joins.
- Generated `catalog.json` records are now checked against
  `generation.json`: every signal must resolve to an entry/P53 route and its
  generated artist and album rooms, preventing loader/catalogue drift.
- The bounded overnight audit now reports canonical-versus-search provider
  link counts, and the private loader returns a versioned receipt containing
  entry, P53, artist, album, cover, and current-transmission routes/state.
- The local authoring server remains localhost-only by default. Its LAN mode is
  opt-in, requires a bearer token, and guards `/__local/` plus `/api/local-*`
  while leaving generated public pages reviewable on the LAN.
- The generated site passes the current read-only overnight audit, browser
  contract, Python compilation, JSON validation, site-only build, and local
  link validation. The one known full-suite exception is the expected frozen
  migration-parity mismatch caused by the user-edited prose in
  `entries/metric-empty.md`; that writing must remain untouched.

### Active work, in order

1. **Release-scope and source hygiene.** Keep this ledger as the only active
   roadmap. Keep operational guides (`agents.md`, `docs/CODE_GUIDE.md`,
   `docs/CSS_JS_GUIDE.md`, `tools/README.md`, and the home-style ownership
   README) because they explain how to work on the source rather than track
   stale plans. Keep `archive/` as history. Do not commit local agent
   attachments, worktrees, inboxes, or generated output unless a Pages release
   explicitly requires it.
2. **Delivery and asset budget.** Measure the generated site and the largest
   delivered images on representative routes; keep P53's visual quality while
   using derivatives and loading priorities where they materially reduce cost.
   Do not recompress authored artwork blindly.
3. **Validation depth.** Extend the bounded audit around provider URL/data
   attributes, manifest routes, duplicate signal IDs, P53 current/history
   consistency, missing artwork, and generated image loading strategy. Keep
   validation read-only and cheap enough for every local publish.
4. **Real-device/deployment sweep.** Check 360/390/430/768/1440 CSS-pixel
   widths, keyboard/focus, reduced motion, blocked storage, slow artwork, and
   the deployed Pages artifact. Test the loader/editor locally on a phone only
   after an authenticated LAN boundary is chosen.
5. **Private authoring boundary.** Design authenticated LAN/phone authoring
   and recoverable draft storage before exposing the editor beyond localhost.
   The first boundary is now implemented: opt-in host binding plus bearer-token
   protection. The next slice is token lifecycle/storage and a phone-friendly
   recovery path; this is not a public submission system and must not place
   credentials or private comments in generated manifests.
6. **Durable identity.** Stable signal IDs and explicit P53 appearance records
   are now in place. Future notification, sharing, or history features should
   use these IDs rather than title/slug heuristics.
7. **Contained extraction.** Continue CSS/JavaScript/template extraction only
   in small named slices with parity tests. Do not undertake a broad rewrite or
   modularize the whole project before the source and deployment contracts are
   stable.

### Deferred ideas retained for later decisions

These came from the retired backlog/audit briefs. They remain visible here so
deleting duplicate notes does not silently delete a product decision:

- optional all-signals/count summaries, a compact entry index, and a quiet
  missing-art/offline state;
- a deliberate share/receipt contract for permanent transmission URLs rather
  than a moving `latest` destination;
- truthful album/artist room counts and destination labels, without invented
  biographies, chronology, or automatic artist portraits;
- a contained reading-layout and typography pass for long titles, Turkish
  characters, 200% text size, and image-free rooms;
- purposeful motion with a stable reduced-motion result and no scroll lock,
  carousel, autoplay, or hover-only interaction;
- a private submission handoff only after storage, authentication, retention,
  and failure semantics are approved. It is not a public review queue.

### Completed: Phase 3 UX alignment and design polish pass (2026-09-22)

Following live visual audits and localhost verification, a 12-item UX alignment, design, and structural polish pass was approved and completed:

1. **Automatic artist portrait pipeline.** Created `tools/fetch_artist_art.py` querying Deezer's public API to automatically fetch and cache high-resolution (1000×1000) portraits for all 28 archive artists in `artist-assets/<slug>.jpg`, registered under `artist_assets` in `config.json`. Metric's bespoke portrait was preserved.
2. **Draft loader and editor metadata resolution.** Hardened `builder/entry_drafts.py`, `tools/new_entry.py`, and `tools/editor/new-entry.js` to parse Apple Music URLs (`?i=` and path formats), add Spotify oEmbed + iTunes metadata fallback resolution, and automatically pull artist art on new draft creation.
3. **Artist room redesign around artist portrait.** Replaced generic grid layouts in `templates/artist.html` and `web/styles/artist-room.css` with an authentic listening shrine layout placing the artist portrait first, harmonizing container widths (`min(980px, calc(100% - 32px))`), card dimensions, typography, and hover transitions with `album-room.css`.
4. **Rich track metadata badges.** Updated `builder/catalog_pages.py` to format `ALBUM · YEAR · TRACK XX` across all songs in artist rooms, establishing visual consistency with album rooms.
5. **PEEK signal audition pill.** Renamed `Audition 0:30` to `PEEK ▶` across `gsi_links.py`, `web/scripts/entry-page.js`, and `web/scripts/p53-transmission.js`. Removed the fixed `0:30` label. Implemented mode-aware active/pressed accent colors matching light/dark hover styles, and refined the cover breathing glow animation.
6. **Compact, optically balanced view toggle.** Redesigned `#view-cycle-btn` into a compact 38px button in `web/styles/home/03-filter-and-controls.css` and `templates/index.html` featuring distinct mini-grid SVGs for `WALL` (2×2), `POSTER` (tall card), and `GALLERY` (3×3), eliminating dead space and aligning with format and recommendation controls.
7. **Instant view switching.** Removed artificial timeout delay (`110ms`) and `.view-switching` transform flicker from `web/scripts/home-layout.js` and `web/styles/home/01-foundation.css` for instantaneous 60fps view switches.
8. **Standardized playlist CTA copy.** Updated all filter definitions in `config.json` to `"playlist_cta": "CHECK OUT THE PLAYLIST"`.
9. **Mobile recommend button.** Made the mobile recommend button compact (`width: auto; min-height: 32px; margin: 4px auto 0; font-size: 9.5px`) on viewports `<= 760px` in `web/styles/home/04-cards-and-responsive.css` to prevent excessive vertical height consumption.
10. **Strict desktop hero and P53 collapse match.** Locked both `.hero-copy` and `.p53-broadcast` in `body.filter-active` to a matching `118px` height in `web/styles/home/02-hero-and-filter-room.css`, eliminating vertical asymmetry when a filter is active.
11. **Harmonized card padding and hover motion.** Aligned `album-room.css` and `artist-room.css` card styling, padding, and subtle `translateX(6px)` hover effects.
12. **Recommend title typography.** Relaxed heading `letter-spacing` in `web/styles/recommend.css` from `-0.065em` to `-0.02em` on `.recommend-header h1`, preventing character collision.

### Completed: Phase 4 & Phase 5 Controls Geometry, Instrument Dock, & Twin Rotating Format (2026-09-23)

1. **Root cause vertical alignment fix.** Discovered that legacy `.view-control` in `web/styles/home/01-foundation.css` retained a 20px bottom margin, which inflated the flex container height to 58px and pushed `.view-control` 10.0px higher than `.format-control` and `.recommend-link`. Zeroed this margin, locking all three controls to an exact 0.0px vertical offset baseline across desktop and mobile.
2. **Unified Edge-to-Edge Instrument Dock.** Replaced isolated floating button islands with a single contiguous glassmorphic toolbar (`.layout-format-controls`) spanning the full content width (1317px on desktop, 354px on mobile) with balanced thirds (`flex: 1 1 0`) and zero dead space.
3. **Twin rotating format cycle button.** Replaced the faux-draggable segmented pill with `#format-cycle-btn`, which speaks the exact visual language of `#view-cycle-btn` (icon, label, value, rotating indicator). Features dynamic track bars SVG for `SONGS` and vinyl record disc SVG for `ALBUMS`, cycling state and cards grid synchronously.
4. **Tightened vertical spacing.** Reduced `.filter-panel` bottom margin from 20px to 12px, eliminating dead vertical air above the controls dock.
5. **Mobile single-line dock.** Kept all three controls on a single unbroken row on mobile (390px) at height 38px, collapsing label words on `<= 440px` to guarantee zero wrapping.

### Completed: Phase 6 Smoothness & Robustness Pass (2026-09-23)

1. **Eliminated forced synchronous layouts (FSL).** Replaced `void document.body.offsetWidth;` and `void box.offsetWidth;` in `web/scripts/home-filters.js` with `window.requestAnimationFrame()` batching, ensuring smooth 60fps filter switching without layout thrashing.
2. **GPU layer promotion for card hover.** Promoted `.card` and `.filter-album-summary` to dedicated compositing layers using `transform: translateZ(0); will-change: transform;` and tuned cubic-bezier transition curves in `web/styles/home/01-foundation.css` to eliminate paint spikes when hovering rapidly.
3. **Subtle album format entrance animation.** Added `@keyframes album-group-fade-in` (220ms ease) to `.filter-album-group`, eliminating the jarring instantaneous pop when toggling from Songs to Albums format.
4. **Clean touch interaction.** Wrapped desktop card hover translations in `@media (hover: hover)` in `01-foundation.css`, preventing mobile touchscreens from leaving cards stuck in an elevated hover state after tapping.
5. **Audio lifecycle teardown on navigation.** Added `pagehide` event listeners in `web/scripts/entry-page.js` and `web/scripts/p53-transmission.js` to immediately pause and release the `Audio` instance when the visitor leaves the page.

### Release and push scope

The repository's Pages workflow builds `site/` from the GSI source and uploads
only that generated directory as the deployment artifact. A future release
commit should therefore include the GSI source needed to reproduce it:
`build.py`, `builder/`, `gsi_*.py`, `config.json`, `tracks.csv`, `entries/`,
`covers/`, `artist-assets/`, `templates/`, `web/`, `tools/`, tests, and the
workflow/configuration that is intentionally part of the project. It should
exclude local `.codex-remote-attachments/`, editor inbox/draft material,
worktree metadata, ignored virtual environments, and other agent-only state.
Existing tracked history is not deleted by this policy; any future removal
must name exact paths and be reviewed before staging.

### Resource note — morning check, 2026-09-22

At the start of this pass there was no listener on port 8021, no running
`submission_server.py`, no active PowerShell job, and no GSI build/test process.
The only live high-CPU application was Opera (about 182 accumulated CPU seconds
at inspection); Codex was about 65 seconds, and no Python worker was running.
The repository is not showing Git-object pressure (`6.43 MiB` loose objects,
`25.27 MiB` packed, `254` loose objects), and `git status` took about `0.15s`.
The ignored `archive/pre-v2.0/.venv` is about `29.8 MB`/1,288 files and the
generated `site/` is about `11.9 MB`/198 files. Neither was removed during this
pass. If the slowdown returns, profile browser/Codex memory and live image
loading first; do not delete source or history as a performance “fix.”

### Housekeeping record

On 2026-09-22 the stale/complete project-note files were folded into this
ledger and removed: the old design backlog, overnight audit note, dated audit,
implementation roadmap, migration plan, navigation/catalogue contract, and the
three Astra recommendation briefs. Operational guides, authored entries, and
the intentional archive remain. No commit or push is part of this cleanup.
