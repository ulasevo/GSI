# GSI Bounded UX & Hierarchy Polish — Execution Record & Plan (`audit/UX_POLISH_PLAN.md`)

**Status:** Completed & Verified (`build.py --site-only --validate-links` + `tools/overnight_audit.py` + 5-viewport headless Chrome visual telemetry)
**Backup Snapshot Location:** `audit/backups/pre-ux-polish/` (exact byte-for-byte pre-edit backups of all 10 modified files)

---

## 1. Confirmed Design Decisions Implemented

1. **Choice 1 — Option B (Compact Cycling View Button with GSI Language):**
   - Replaced the wide 3-button layout bar (`Poster | Wall | Gallery`, `278×52px`) with a single compact cycling button (`#view-cycle-btn`, `146×42px`) displaying a 4-cell geometric grid icon + `VIEW` + current GSI view mode (`WALL` / `GALLERY` / `POSTER`) + `⟳`.
   - Kept hidden `.view-btn` elements synced inside `.sr-only-controls` so existing scripts and tests remain 100% compatible.
   - Merged `#view-cycle-btn`, `.format-control` (`SONGS | ALBUMS | ARTISTS`), and right-aligned `.recommend-link` (`RECOMMEND A SIGNAL ↗`) onto a single `52px`-tall unified control strip (`#layout-format-controls`).

2. **Choice 2 — Option A (`#playlist-card` inside `#filter-description-box` with Clean Mobile Dock):**
   - Moved `#playlist-card` back inside `#filter-description-box` as its 2nd grid column so it only appears when a filter room is open and never collides with the control toolbar.
   - Styled `#playlist-card` on desktop as a tilted horizontal media badge (`60×60px` cover thumbnail + `APPLE MUSIC ↗` eyebrow + `#playlist-cta`) and on mobile (`<= 760px`) as a full-width horizontal dock strip (`42×42px` cover thumbnail + inline copy, `min-height: 58px`), eliminating the awkward giant mobile square.

3. **Filter-Room Hero Fold & Above-the-Fold Grid Visibility:**
   - When `body.filter-active` is active on the homepage, `.site-hero` smoothly folds into a `~118px`-tall Command Header Strip (folding `.hero-copy .intro` via `max-height: 0; opacity: 0;` and arranging `.p53-overlay` into a 3-column horizontal banner `[60px thumb | RADIO P53 | CURRENT TRANSMISSION]`).
   - Tightened `.filter-description` height (`clamp(195px, 21vw, 248px)`), bringing the first row of matching song cards from `Y = 1180px` (280px below the fold) up to `Y = 716px` (**inside the first viewport** on `1440×900`).

4. **Mobile `.theme-toggle` Top-Right Docking:**
   - Moved `.theme-toggle` on `@media (max-width: 760px)` to `top: 12px; right: 12px` (`min-height: 38px`), eliminating its collision with the `BITE` filter button on the homepage and the `SECTIONS` navigation bar on Entry pages.

5. **Entry Shrine Above-the-Fold Proportion & Filter Context Preservation:**
   - Constrained desktop `body.art-room .cover-frame` to `width: min(100%, clamp(320px, 44vh, 450px))` (`396×396px` on `1440×900`), bringing `<h1>` (`Empty`), artist/album links, streaming links (`Spotify ↗`, `Apple Music ↗`), and the `SECTIONS` jump bar (`Charge | Sonical Attraction | Version of ulaş | Comment`) above the fold (`Y = 502px–858px` on `1440×900`).
   - Updated `[data-filter-route]` links in `web/scripts/entry-page.js` to preserve `archiveParams` (`layout`, `format`, `theme`) when jumping from an Entry's `Also appears in` pill back to a Homepage filter room.

6. **Untouched Per User Instruction:**
   - `web/scripts/home-format.js` (`groupCards.length < 2` multi-song album threshold) was left completely untouched.
   - `entries/*.md`, `tracks.csv`, and `config.json` prose/data were left completely untouched.

---

## 2. Modified Files & Backup Manifest

| Modified File | Backup Copy in `audit/backups/pre-ux-polish/` | Summary of Changes |
| :--- | :--- | :--- |
| `builder/home_page.py` | `audit/backups/pre-ux-polish/builder/home_page.py` | Moved `#playlist-card` into `#filter-description-box`; added `#view-cycle-btn` + `.sr-only-controls` inside `#layout-format-controls` |
| `templates/index.html` | `audit/backups/pre-ux-polish/templates/index.html` | Added `.recommend-link` inside `#layout-format-controls` and removed redundant `.archive-utility-bar` wrapper |
| `web/scripts/home-layout.js` | `audit/backups/pre-ux-polish/web/scripts/home-layout.js` | Wired `#view-cycle-btn` (`WALL` → `GALLERY` → `POSTER` → `WALL`) and label synchronization in `setLayout()` |
| `web/scripts/home-filters.js` | `audit/backups/pre-ux-polish/web/scripts/home-filters.js` | Added `box.classList.add/remove("has-playlist")` alongside `layoutFormatControls` |
| `web/scripts/entry-page.js` | `audit/backups/pre-ux-polish/web/scripts/entry-page.js` | Preserved `archiveParams` (`layout`, `format`, `theme`) on `[data-filter-route]` links |
| `web/styles/home/02-hero-and-filter-room.css` | `audit/backups/pre-ux-polish/web/styles/home/02-hero-and-filter-room.css` | Added `body.filter-active` command-header fold for `.site-hero`, `.hero-copy`, and horizontal `.p53-overlay` banner |
| `web/styles/home/03-filter-and-controls.css` | `audit/backups/pre-ux-polish/web/styles/home/03-filter-and-controls.css` | Styled `#view-cycle-btn`, single-row `#layout-format-controls`, and horizontal `#playlist-card` inside `#filter-description-box` |
| `web/styles/home/04-cards-and-responsive.css` | `audit/backups/pre-ux-polish/web/styles/home/04-cards-and-responsive.css` | Added mobile horizontal dock styling for `#playlist-card`, compact mobile `.site-hero` fold, and single-row mobile toolbar |
| `web/styles/entry-room.css` | `audit/backups/pre-ux-polish/web/styles/entry-room.css` | Constrained desktop `body.art-room .cover-frame` to `clamp(320px, 44vh, 450px)` so `<h1>` and streaming links sit above the fold |
| `web/styles/theme-mode.css` | `audit/backups/pre-ux-polish/web/styles/theme-mode.css` | Docked mobile `.theme-toggle` at `top: 12px; right: 12px` (`min-height: 38px`) and added light-mode styling for `.view-cycle-btn` |

---

## 3. Before / After Telemetry Comparison (`1440×900` Desktop & `390×844` Mobile)

| Metric | Before UX Polish | After UX Polish | Delta / Result |
| :--- | :--- | :--- | :--- |
| **Layout Control Width (`1440×900`)** | `278 × 52px` (3-button pill bar) | `146 × 42px` (`#view-cycle-btn`) | **-47.5% width**; unified on 1 row |
| **Control Rows Between Filters & Grid** | 2 separate rows (`100px` vertical height) | 1 unified row (`52px` vertical height) | **-48px vertical chrome** |
| **First Card Row `Y` (Default Home `1440×900`)** | `Y = 744px` (`156px` visible) | `Y = 648px` (`252px` visible) | **+96px more grid visible above fold** |
| **First Card Row `Y` (`?filter=bassline` `1440×900`)** | `Y = 1180px` (**0 cards visible**; `280px` below fold) | `Y = 716px` (**6 cards visible** above fold) | **+464px higher**; first row immediately visible |
| **Entry `<h1>` (`Empty`) `Y` (`1440×900`)** | `Y = 824px`, bottom `952px` (clipped off-screen) | `Y = 502px`, bottom `598px` (fully visible) | **+322px higher**; `<h1>`, streaming links, and `SECTIONS` bar all above fold |
| **Mobile `.theme-toggle` Overlap (`390×844`)** | Overlapped `BITE` filter button & Entry `SECTIONS` | Docked at `top: 12px; right: 12px` (`90×38px`) | **0 collisions** across all mobile routes |
| **Mobile `#playlist-card` Shape (`390×844`)** | Awkward square / 3rd toolbar item | Full-width `58px`-tall horizontal media strip (`42×42px` cover) | Clean horizontal media dock inside `#filter-description-box` |
