# GSI Localhost UX & Visual Audit Report

**Date:** 2026-09-22  
**Server Environment:** `tools/submission_server.py` (`http://127.0.0.1:8021`, cleanly terminated post-audit)  
**Browser Engine:** Headless Chromium via Chrome DevTools Protocol (CDP) across `360×800`, `390×844`, `430×932`, `768×1024`, and `1440×900` viewports in both `dark` (`DIM`) and `light` (`LIT`) themes.  
**Mode:** Strictly Read-Only (Zero source, config, or generated files modified).

---

## 1. Automated Integrity & Asset Budget Baseline

Before running the visual/DOM sweep, `tools/overnight_audit.py` was executed against the live repository state:

- **Catalogue & Route Health:** `0` errors, `0` warnings across **27** tracks, **27** Markdown entries, **18** P53 history records (**20** `site/p53/*.html` routes), **28** Artist rooms, and **35** Album rooms.
- **Provider Link Telemetry (`40` total signals):**
  - **Apple Music:** `40 / 40` canonical URLs (`0` search fallbacks).
  - **Spotify:** `0 / 40` canonical URLs (`40` automatic search fallbacks).
- **Runtime Artwork Derivative (`covers/P53_cover-runtime.webp`):**
  - Source master (`covers/P53_cover.jpg`): `3,973,942 bytes` (~3.79 MB).
  - Runtime derivative (`covers/P53_cover-runtime.webp`): `414,416 bytes` (~404.7 KB — **89.6% reduction**, well within the `500 KB` budget).
- **Horizontal Overflow Check:** `documentElement.scrollWidth === documentElement.clientWidth` (`horizontalOverflow: false`) across **all** tested viewports (`360px`, `390px`, `430px`, `768px`, `1440px`) on Homepage, Entry rooms, P53 Landing, and Artist rooms.

---

## 2. Homepage First-Viewport & Filter-Room Telemetry (`index.html`)

To answer the filed investigation in [PROJECT_STATE.md](file:///c:/Users/Kane/Desktop/Metu_Undergrad/Y3/GSI/PROJECT_STATE.md#L656-L673), exact bounding-box Y-coordinates (`getBoundingClientRect().top` and `.height`) were captured for every structural band above `.grid` across all five target viewports.

### 2.1 Unfiltered Homepage (`index.html`)
| Viewport | `.site-hero` Height | `.filter-panel` Height | `.layout-format-controls` Height | First `.card` Top (`Y`) | First Card Visible Above Fold? | Scroll Needed to Reveal First Row | Position in Viewports |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`360×800`** | `619px` | `328px` | `105px` | **`1182px`** | ❌ No | `462px` | **`1.48×`** |
| **`390×844`** | `602px` | `328px` | `105px` | **`1165px`** | ❌ No | `401px` | **`1.38×`** |
| **`430×932`** | `586px` | `328px` | `50px` | **`1094px`** | ❌ No | `242px` | **`1.17×`** |
| **`768×1024`** | `605px` | `199px` | `50px` | **`996px`** | ⚠️ Barely (`28px` peek) | `52px` | **`0.97×`** |
| **`1440×900`** | `428px` | `110px` | `50px` | **`754px`** | ✅ Yes (`146px` visible) | `0px` | **`0.84×`** |

### 2.2 Filter-Active State (`?filter=personal` & `?filter=bassline`)
| Viewport | State | `.site-hero` Height | `.filter-panel` Height (incl. `#filter-description-box`) | `.layout-format-controls` Height (incl. `#playlist-card`) | First `.card` Top (`Y`) | First Card Visible Above Fold? | Scroll Needed to Reveal First Row | Position in Viewports |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`360×800`** | `personal` | `627px` | `563px` (`219px` desc) | `162px` (`50px` playlist) | **`1482px`** | ❌ No | `762px` | **`1.85×`** |
| **`390×844`** | `personal` | `610px` | `567px` (`223px` desc) | `162px` (`50px` playlist) | **`1468px`** | ❌ No | `704px` | **`1.74×`** |
| **`430×932`** | `personal` | `594px` | `547px` (`203px` desc) | `107px` (`50px` playlist) | **`1377px`** | ❌ No | `525px` | **`1.48×`** |
| **`768×1024`** | `personal` | `605px` | `408px` (`193px` desc) | `108px` (`50px` playlist) | **`1264px`** | ❌ No | `320px` | **`1.23×`** |
| **`1440×900`** | `personal` | `428px` | `536px` (`410px` desc) | `50px` (`501px` wide inline) | **`1180px`** | ❌ No | `360px` | **`1.31×`** |

### Key Finding 1: Filter Rooms Push Content Downward Rather Than Collapsing the Hero
- **What Happens Visually:** When a user clicks a filter button (e.g., `PERSONAL` or `BASSLINE`) on a `1440×900` desktop screen, `.site-hero` (`428px` tall) dims its `.intro` paragraph opacity in [web/styles/home/02-hero-and-filter-room.css](file:///c:/Users/Kane/Desktop/Metu_Undergrad/Y3/GSI/web/styles/home/02-hero-and-filter-room.css), **but its geometric height remains `428px`** (increasing slightly to `610px` on `390px` mobile). Simultaneously, `#filter-description-box` expands to **`410px` tall** on desktop (`223px` on mobile), pushing the first song card from `Y = 754px` (visible) down to **`Y = 1180px`** (`280px` below the bottom of the `900px` screen).
- **UX Consequence:** Clicking any filter button on desktop or mobile results in **zero matching song cards visible in the viewport**—the user only sees the dimmed hero, the filter buttons, and the oversized filter description box until they scroll down `360px–786px`.

---

## 3. Interactive Controls, Format Switching & Mobile Occlusion Findings

### Key Finding 2: Fixed Bottom-Right `.theme-toggle` Occludes Interactive Controls on Mobile
- **Where:** `position: fixed` `.theme-toggle` pill (`DIM` / `LIT` switch) rendered by [web/scripts/theme-mode.js](file:///c:/Users/Kane/Desktop/Metu_Undergrad/Y3/GSI/web/scripts/theme-mode.js) and styled in [web/styles/theme-mode.css](file:///c:/Users/Kane/Desktop/Metu_Undergrad/Y3/GSI/web/styles/theme-mode.css).
- **Visual Evidence (`390×844` Mobile):**
  - On `index.html`, the floating `DIM` pill sits directly over the **`BITE`** filter button in the two-column mobile filter grid, covering the word `BITE` so only a fragment of the `I` is visible.
  - On `entries/metric-empty.html`, the floating `DIM` pill collides with the right end of the horizontal `SECTIONS` pill bar (partially covering `"Version of ulaş"`) and hovers over the top-right corner of the first `.section-card` where the `i` (`section-info-button`) lives.

### Key Finding 3: Homepage `ALBUMS` Format Displays Only 4 of 35 Represented Albums
- **Where:** [web/scripts/home-format.js](file:///c:/Users/Kane/Desktop/Metu_Undergrad/Y3/GSI/web/scripts/home-format.js#L51-L63) (`if (!firstMatchingCard || groupCards.length < 2) return;`).
- **Live DOM Verification (`index.html?format=albums`):**
  - Total signal cards in DOM: `40`.
  - Standalone `.card` items visible when `ALBUMS` is active: **`0`**.
  - `.filter-album-group` pockets rendered: **`4`** (*Live It Out* [`03 signals`], *Bloom* [`02 signals`], *A Quiet And Harmless Living* [`02 signals`], *Royal Blood (10th Anniversary Edition)* [`02 signals`]).
- **UX Consequence:** The remaining **31 albums** in the archive (which each have 1 represented track) vanish completely when the user clicks `ALBUMS`, making the archive appear to contain only 4 albums instead of 35.

### Key Finding 4: Sub-44px Touch Targets on Layout, Format & Section-Info Controls
- Across all mobile viewports (`360px`, `390px`, `430px`), the `.filter-btn` buttons have comfortable touch heights (`~56px–68px`), but three secondary control sets fall below the `44×44px` mobile accessibility threshold:
  - `.view-btn` (`Poster`, `Wall`, `Gallery`): **`41×38px`** at `430px` width (`87×38px` at `360px` where the row wraps).
  - `.format-option` (`SONGS`, `ALBUMS`, `ARTISTS`): **`61×40px`** at `430px` width (`105×38px` at `360px`).
  - `.section-info-button` (`i` button on Entry section headings): **`34×34px`** on mobile (`390×844`).

---

## 4. Intimate Reading Shrines (`entries/*.html`), P53 & Catalogue Rooms

### Key Finding 5: Entry Room Desktop Hero Artwork Pushes Song Title Across the Fold (`1440×900`)
- **Where:** [web/styles/entry-room.css](file:///c:/Users/Kane/Desktop/Metu_Undergrad/Y3/GSI/web/styles/entry-room.css) (`entries/metric-empty.html` at `1440×900`).
- **Visual Evidence:** On `1440×900` desktop, the centered square `.cover` artwork renders at ~`760×760px`. Because of top breadcrumb margin + cover height, the `<h1>` song title (`Empty`) begins at `Y ≈ 865px` and is sliced horizontally in half by the bottom edge of the `900px` viewport.
- **Mobile vs. Desktop Contrast:** Ironically, on `390×844` mobile, the `354×354px` cover leaves comfortable vertical room so the entire `Empty` title, `Metric` artist link, `Live It Out` album link, `Spotify ↗` / `Apple Music ↗` outbound buttons, and the `SECTIONS` jump bar are all visible in the initial viewport! Constraining the desktop `.cover` max-dimension (e.g. `clamp(320px, 46vh, 480px)`) would give desktop the same cohesive above-the-fold shrine composition that mobile already achieves.

### Key Finding 6: Incomplete URL Context Propagation in Entry `#also-appears` Links
- **Where:** [web/scripts/entry-page.js](file:///c:/Users/Kane/Desktop/Metu_Undergrad/Y3/GSI/web/scripts/entry-page.js#L44-L67).
- **Live DOM Telemetry (`entries/metric-empty.html?theme=light`):**
  - `ARTIST PAGE : Metric` → `../artists/metric.html?theme=light` (preserves context ✅)
  - `ALBUM PAGE : Live It Out` → `../albums/metric-live-it-out.html?theme=light` (preserves context ✅)
  - `Personal` (`[data-filter-route="personal"]`) → `../index.html?filter=personal` (**drops `?theme=light` and `?view=...`** ⚠️)
  - `RADIO P53` link inside `#also-appears` (`../p53/<slug>.html`) also lacks `[data-base-href]` context rewriting.

### Key Finding 7: Palette & Theme Contrast Success (`dark` vs `light`)
- Both `dark` (`DIM`) and `light` (`LIT`) themes render with strong legibility across `index.html`, `entries/metric-empty.html`, `p53/index.html`, `artists/metric.html`, and `albums/metric-live-it-out.html`:
  - Dark mode `.section-card` copy resolves to `rgb(248, 245, 239)` over the deep magenta-tinted surface.
  - Light mode `.section-card` copy resolves to `rgb(31, 20, 32)` (`#1f1420`) over the soft rose-tinted surface (`linear-gradient(135deg, #f9f8f7, #e9ccd7 52%, #faf9f8)`).
- Artist room (`artists/metric.html`) and Album room (`albums/metric-live-it-out.html`) compositions look cohesive, with the Polaroid-style `xo metric` portrait and `MY TAKE` callout card preserving personal voice and album-title casing.

---

## 5. Summary Matrix of Actionable Recommendations (Awaiting Approval)

> [!IMPORTANT]
> Per `AGENTS.md` and `PROJECT_STATE.md`, **no code or stylesheet changes have been made**. Each item below is scoped to a small, named file boundary if and when you choose to authorize patches:

| Priority | Issue | Owning File(s) | Proposed Small-Slice Fix |
| :---: | :--- | :--- | :--- |
| **P1** | Filter activation on desktop (`1440×900`) and mobile leaves **0 cards visible** in the viewport (`Y = 1180px–1506px`). | `web/styles/home/02-hero-and-filter-room.css` | Collapse `.site-hero` height (or smoothly fold `.hero-copy` + `.p53-broadcast` into a compact header strip) when `body.filter-active` is set, and tighten `#filter-description-box` vertical padding (`410px` → `~180px`) so the first row of filtered cards moves upward into the first viewport. |
| **P1** | Homepage `ALBUMS` format hides **31 of 35** albums because `groupCards.length < 2` returns early after hiding all `.card` elements. | `web/scripts/home-format.js` | Either change the grouping threshold in `renderFilterAlbumGroups()` from `groupCards.length < 2` to `groupCards.length < 1` (so all 35 album rooms appear as album cards in `ALBUMS` mode), or keep 1-signal cards visible beneath multi-signal pockets. |
| **P2** | Floating `.theme-toggle` (`DIM`/`LIT`) overlaps the `BITE` filter button and Entry `SECTIONS` / `i` controls on mobile (`360–430px`). | `web/styles/theme-mode.css` | Dock `.theme-toggle` into the top utility/header row on narrow viewports (`@media (max-width: 768px)`) or reserve bottom/right safe-area inset and reduce its mobile footprint so it cannot cover interactive buttons. |
| **P2** | Desktop Entry room (`1440×900`) `.cover` (`~760px` square) pushes `<h1>` (`Empty`) across the bottom fold of the screen. | `web/styles/entry-room.css` | Cap `.entry-hero .cover` width/height with viewport-aware sizing (`max-width: min(460px, 48vh)`) on desktop so the cover, song title, artist/album links, and streaming links sit together above the fold. |
| **P3** | Entry `#also-appears` `[data-filter-route]` links drop `?theme=` and `?view=` query context. | `web/scripts/entry-page.js` | Append `archiveParams` (`view`, `format`, `theme`) when rewriting `[data-filter-route]` links in `entry-page.js` (`lines 52–54`). |
| **P3** | Sub-`44px` touch height on `.view-btn` (`38px`), `.format-option` (`38–40px`), and `.section-info-button` (`34×34px`). | `web/styles/home/03-filter-and-controls.css`, `web/styles/entry-room.css` | Increase `min-height` to `44px` on `.view-btn` / `.format-option` and expand `.section-info-button` hit area to `44×44px` (via `min-width`/`min-height` or transparent padding). |
