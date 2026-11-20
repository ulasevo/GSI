# Chaperone (GSI) Full-Stack Code, Visual, Motion & Mobile Audit

- **Baseline Commit:** `0cd1610` (20 November 2026)
- **Mode:** Strictly read-only inspection (0 repo files modified)
- **Skills Applied:** `emil-design-eng`, `improve-animations` (`AUDIT.md`), `review-animations` (`STANDARDS.md`), `mobile-native`, `break-ui` (`CATALOG.md`), `frontend-design` (all verified already installed under `.agents/skills/`), plus `DESIGN.md`, `ROADMAP.md`, `PROJECT_STATE.md`, and `AGENTS.md`.
- **Verification Scope:**
  - 50 live headless Chrome screenshots + DOM telemetry (`1440×900`, `390×844`, `320×640`, DIM & LIT, scroll states, P53 share modal) saved in session scratch (`neon_audit/shots/`).
  - Full read-only static audit of all 19 CSS files (`348.9 kB`), 10 HTML templates, 16 JS files, Python builder (`builder/`, `gsi_*.py`, `tools/`), data (`config.json`, `tracks.csv`, `entries/*.md`), CI (`.github/workflows/deploy-pages.yml`), and `android/`.
  - Executed test suites read-only: `py_compile`, `json.tool`, 52 Python `unittest` cases, 3 Node contract suites (`test_browser_contract.js`, `test_p53_card_render.js`, `test_p53_share.js`), and `tools/overnight_audit.py`.
  - Independent verifier cross-check of all high-severity `file:line` claims and byte measurements.

---

## 1. What Holds Up (Do Not Break or Normalize)

- **Distinctive visual identity (zero SaaS template feel):** Dynamic 32-point cover-rim lighting on cards/rooms, Radio P53 protein-collage landing, Polaroid artist hero, cover-to-field dissolve on mobile entry pages, and the archival paper-sleeve P53 share card (`p53-transmission.js` uses grapheme-safe `Array.from()` wrapping and dynamic WCAG contrast math).
- **Personal voice & data safety (`AGENTS.md`):** Personal taxonomy (`Charge`, `Sonic Attraction`, `Version of ulaş`, `Radio P53`, `DIM/LIT`) lands authentically. HTML escaping (`html.escape()` in Python, `textContent` in main JS) blocks XSS on catalogue text. Zero JS runtime errors across all 50 live Chrome scenarios.
- **Clean baselines:** 0 occurrences of `ease-in` or `scale(0)` on UI, 0 `user-scalable=no` / `maximum-scale=1`, 0 `touchmove + preventDefault()`, balanced CSS braces across all 19 stylesheets, 0 `<img>` missing `alt`, clean heading hierarchy, and all 52 Python + 3 Node tests passing.
- **Intentional choices to respect:** Keeping `GSI` filenames/IDs (`/GSI`, `GSI_favicon.svg`, `gsi-theme`, Android `app_name=GSI`) until the GroEL/GroES logo is ready (`ROADMAP.md:12`); Android `minSdk = 37` (`ROADMAP.md:14,29`); no full CSS modularization pre-1.0 without explicit approval (`AGENTS.md`).

---

## 2. Critical & High-Severity Bugs (Fix Immediately — No Redesign Needed)

### A. Authoring Crashes, Silent Data Corruption & LAN Security (Horizon 2)
1. **`NameError` crash editing P53-only signals** (`tools/new_entry.py:268`): `_replace_track()` calls undefined `_append_tracks_row(root, record)` instead of `_append_track` (`tools/new_entry.py:249`).
2. **`AttributeError` crash in CLI `--write`** (`tools/new_entry.py:720-725`): References `args.artist_note` and `args.album_note`, neither defined in `_parse_args()` (`147-187`) nor `_interactive_namespace()` (`209-236`), crashing *after* mutating `entries/<slug>.md` and `tracks.csv`.
3. **Silent field cross-contamination in LAN mobile editor** (`tools/editor/private/private-entry.js:297-305, 345-385, 492-525`): `loadEntry()` and `setMode("new")` never call `clearFormFields()` before `restoreFormData()`, which skips blank fields (`if (r.accent) ...`, `if (r.tags) ...`). Switching from Track A to Track B leaks Track A's accent/tags/link into Track B and saves them.
4. **`Sonical Attraction` vs `Sonic Attraction` drift** (`tools/editor/private/private-entry.js:4`, `tools/editor/new-entry.js:4`): Both hardcode `"Sonical Attraction"` while `config.json:297` and all `28/28` `entries/*.md` use `"Sonic Attraction"`. `private-entry.js` never fetches `editor-config.json`, so every phone-authored entry creates `## Sonical Attraction`, causing `builder/source_pipeline.py:268` to append a duplicate empty `## Sonic Attraction`.
5. **P53 `current=True` edit breaks build preflight** (`tools/new_entry.py:337-339`): `_update_p53()` updates `p53_current_slug` without moving the record to the tail of `p53_history`, violating `gsi_validation.py:309`.
6. **LAN editor autosave & UX holes:** `private-entry.js:191-204` has no `pagehide`/`visibilitychange` flush (drops edits within 400ms on mobile close) and no "discard local draft / reload from disk" button (`505-511` silently overwrite newer server edits); `submission_server.py:104-114` leaves raw `<!-- prompt -->` HTML comments inside edit textareas; `private-entry.js:651` compares `rgb(...)` to `#hex` (never matches); `new-entry.html:68-77` artist artwork uploader has zero JS listeners; `tools/new_entry.py:351-363` cannot clear notes and leaves empty `{}` dicts in `config.json`.
7. **LAN server security & concurrency** (`tools/submission_server.py`, `tools/serve.py`):
   - `/api/entry-drafts` and `/api/recommendations` sit outside `PRIVATE_PATH_PREFIXES` (`submission_server.py:41`), emit `Access-Control-Allow-Origin: *` (`307-308`), and allow unauthenticated 100 KB disk writes on the LAN (`318-359`).
   - `tools/serve.py:52,70,84` generates a 32-bit token (`secrets.token_hex(4)`) and passes `?token=` in URLs; `Set-Cookie` (`submission_server.py:400`) omits `HttpOnly` and uses `Path=/` (note: `SameSite=Lax` already blocks cross-site `POST` cookies, but adding `HttpOnly`, `Origin` validation, and `secrets.token_urlsafe(24)` closes the rest).
   - `ThreadingHTTPServer` (`447`) lacks a publish lock for concurrent phone taps; rollback (`new_entry.py:463-465`) misses downloaded artist portraits; `submission_server.py:221,229-233` only splits on `/` (Windows `\` path guard gap).
   - `site/tools/` (`43.5 KiB`) deploys the client-side Entry Loader publicly (`deploy-pages.yml:39-41`, `test_catalog_renderers.py:207-225`), shipping `🔑` auth UI and `/api/local-entry-publish` strings to public Pages (contradicting `docs/ARCHITECTURE.md:45` and `ROADMAP.md:77`).

### B. Broken Visuals, Routing, Theme Persistence & Failing Audits
8. **Album LIT mode unreadable (`1.04:1` contrast)** (`web/styles/album-room.css:43-55, 72-79`, missing rules in `web/styles/theme-mode.css`): `.album-archived-badge` renders pink-on-pink and `.album-song--unreviewed .album-song-meta span` (`rgba(255,255,255,.6)` at `opacity: 0.38`) is invisible on light album surfaces (verified in Chrome: `album_liveitout_desktop_lit.png`).
9. **320px Masthead Wordmark Collision** (`web/styles/home/02-hero-and-filter-room.css:34-82`, `04-cards-and-responsive.css:83-110`): `Recommend ↗` literally overlaps `"Chaperone"` and `"Interactive music"` at 320px (`home_narrow320_dim.png`).
10. **404 Page Broken LIT Mode, HTTP 404 Asset & Overflow Clip** (`templates/404.html`, `web/styles/error-page.css:4,7,14,16-18,25-28`):
    - Zero LIT rules in `theme-mode.css` → white LIT toggle over dark `#0d0d0f` page (`404_desktop_lit.png`).
    - `error-page.css:7` requests `url("covers/P53_cover-runtime.webp")` → **HTTP 404** at `/GSI/styles/covers/...` (should be `../covers/P53_cover-runtime.webp`).
    - Omits `gsi-tokens.css` (falls back to `Arial`); `overflow: hidden` clips content on short/zoomed screens; mobile `h1 em` overlaps `"EXIST"`; hard offset shadow + `border-radius` hover inversion violate `DESIGN.md:8-9`.
11. **Broken Radio P53 archive chronology** (`builder/p53_pages.py:224-228`): `site/p53/index.html` puts #18 (`Matt Maeson`, ACTIVE) at `signal-01`, then jumps to #1 OLDEST (`Miki Matsubara`) at `signal-02` ascending to #17 (`Emily Haines`) at `signal-18` — contradicting `"scroll down to travel back in time"` (`templates/p53-landing.html:17`) and homepage P53 newest-first order (`web/scripts/home-format.js:28`).
12. **Cross-page theme toggle reverts & overwrites `localStorage`** (`web/scripts/entry-page.js`, `artist-room.js`, `album-room.js`, `p53-landing.js`, `p53-transmission.js`, `recommend.js` vs `theme-mode.js:25,57`): Only `home-page.js:104` listens for `gsi-theme-change`. Toggling DIM↔LIT on any sub-page leaves stale `?theme=` on outbound links; clicking back lets the stale URL param override and overwrite `localStorage["gsi-theme"]`. *(Guardrail: `tools/overnight_audit.py:192-195` asserts `searchParams.set("theme"` and `setTheme(initial, true)` remain in `theme-mode.js`, so fix by wiring `gsi-theme-change` listeners into all sub-page scripts + loading `gsi-context.js` on `recommend.html`.)*
13. **Double HTML escaping in `aria-label`** (`gsi_links.py:138-147`): Emits literal `&amp;amp;` / `&amp;#x27;` on 4 P53 transmission pages (`emily-haines-*-doctor-blind`, `*-minefield-of-memory`, `mitski-shouldve-been-me`, `peter-murphy-the-prince-old-lady-shade`).
14. **`tools/overnight_audit.py` fails with 229 errors & CI never runs tests**:
    - 228 errors: `.floating-path` favicon `<img src="../covers/GSI_favicon.svg" alt="">` lacks `loading` and `decoding` across 114 sub-pages (`templates/entry.html:36`, `artist.html:14`, `album.html:13`, `p53-landing.html:17`, `p53-transmission.html:33`, `recommend.html:27`).
    - 1 error: `--art-section-ink` contrast contract missing from `theme-mode.css` (`tools/overnight_audit.py:198-199`).
    - `.github/workflows/deploy-pages.yml:30-39` deploys without running `--validate-links`, `unittest`, the 3 Node suites, or `overnight_audit.py`.
15. **All 16 `env(safe-area-inset-*)` rules on public site evaluate to `0px`** (`templates/*.html`, `tools/editor/new-entry.html`): Every public template omits `viewport-fit=cover` in `<meta name="viewport">` (only `edit-entry.html:5` has it).
16. **Reduced-motion defeated by `!important` specificity** (`web/styles/home/03-filter-and-controls.css:283-295` vs `04-cards-and-responsive.css:344-351`): `.filter-collapsing` `transition: ... !important` `(0,2,0)` beats `* { transition-duration: .01ms !important }` `(0,0,0)`.
17. **Recommend mobile `+4px` horizontal overflow** (`web/styles/recommend.css:48`): `.recommend-main-grid::before { inset: 3% -5% 4% }` overflows `390px` viewports to `394px` (`recommend_mobile_dim.png`).
18. **DIM active segmented dock tab nearly invisible** (`web/styles/home/03-filter-and-controls.css:571`, `theme-mode.css:35`): `--gsi-mode-surface-strong` resolves in dark mode to `rgba(15,13,19,.94)` on `rgba(0,0,0,.22)` (`home_desktop_dim.png`).
19. **Active filter pill ignores `--filter-color`** (`web/scripts/home-filters.js:171,182-186`, `03-filter-and-controls.css:77-78`): Always falls back to purple `#8c5de8` instead of active filter's tint (`home_filter_personal_desktop_lit.png`).
20. **Desktop Entry `<h1>` smeared by bottom `html::after` blur** (`web/styles/entry-room.css:1069-1070`, `theme-mode.css:1780-1786`): 760px square cover pushes `<h1>` squarely into the fixed 44px bottom blur strip at `1440×900` (`entry_empty_desktop_dim.png`). Also `html::after` blurs homepage cards unnecessarily despite homepage having no bottom pills (`home_desktop_dim.png`), and P53 transmission `.floating-path` overlaps bottom-left `"P53"` watermark (`p53_miki_desktop_dim.png`).

---

## 3. Emil Design-Eng Review Table (Before / After / Why)

| Before | After | Why |
| --- | --- | --- |
| `p53-transmission.css:729`, `new-entry.css:46`, `private-entry.css:53,83,156,185`: `transition: all 0.2s ease` / `all 180ms ease` | `transition: transform 160ms var(--ease-out), background-color 180ms ease, border-color 180ms ease, color 180ms ease;` | Specify exact properties; `transition: all` animates unintended layout/paint properties. |
| `03-filter-and-controls.css:10,266-290`: `padding`/`margin`/`max-height`/`min-height` transitions + `!important` | Drop no-op `padding` transition; animate filter room via `transform` + `opacity` (`220ms` in / `160ms` out, no `!important`) | Layout transitions trigger reflow every frame (`DESIGN.md:46`); `!important` defeats `prefers-reduced-motion`. |
| `entry-room.css:514` (`.section-help`): `grid-template-rows 420ms` + `margin 420ms` | `opacity` + `transform: translateY(-4px)` (`220ms var(--ease-out)` open / `150ms` close) | `DESIGN.md:46` bans `grid-template-rows`/`margin` transitions; `420ms` exceeds 300ms UI budget. |
| `error-page.css:16-17,25-26` & `entry-room.css:312,487,500`: `border-radius` morphing on hover/toggle + `720ms` `info-orbit` | Stable `border-radius`; animate only `transform` (`180ms var(--ease-out)`) + border/color | `DESIGN.md:9` forbids `border-radius` morphing (continuous GPU raster repaints). |
| `entry-room.css:924-927`: `body.art-room .section-card:active { transform: scale(0.995); }` | Delete rule | `.section-card` is static review prose (`builder/entry_pages.py:172`); shrinking text on selection feels broken. |
| Missing `:active` on `.album-song`, `.album-entry`, `.artist-signal`, `.p53-card-companion`, P53 `.stream-link`/`.story-btn`, `.filter-drawer-toggle`, `recommend.css:17-19` (also missing `transition`), `error-page.css`, `new-entry.css` | Add `:active { transform: scale(0.97); transition: transform 80ms ease-out; }` (`0.985` for wide cards) | Pressable controls need immediate press-down feedback (`DESIGN.md:58`, `mobile-native` §5). |
| **128** ungated `:hover` rules + **2** partial `(hover: hover)` rules across 15 CSS files | Wrap all `:hover` rules in `@media (hover: hover) and (pointer: fine)` and delete earlier ungated fallbacks | Earlier ungated rules in `01-foundation.css` & later rules in `theme-mode.css` cause sticky touch hover on phones. |
| 6 files: `*, *::before, *::after { transition-duration: .01ms !important; }` & `entry-room.css:1161`: `.cover { mask-image: none; }` under reduced motion | Disable spatial transforms/loops under reduced motion while keeping `150ms` `opacity`/`color` fades; keep static `.cover` `mask-image`; respect reduced motion in `home-layout.js:23` & `home-filters.js:127` | Reduced motion means gentler motion, not zero state feedback (`DESIGN.md:53`); removing static mask breaks art. |
| `02-hero:210` (`700ms`), `p53-landing.css:156,174,214` (`320-420ms`), `p53-transmission.css:261` (`360ms`), `entry-room.css:1478` (`320ms`) | Clamp non-modal interactive transitions to `160-240ms var(--ease-out)` | UI animations > 300ms feel sluggish (`AUDIT.md:36`). |
| `03-filter:146-153` (`@keyframes drawerReveal`) & `p53-transmission.css:660-675` (`@keyframes story-modal-in`) with instant snap-close | CSS transitions + `@starting-style` (`transform-origin: top` on drawer; centered `scale(0.96)` + `::backdrop` fade on `<dialog>`, faster exit) | Keyframes restart from zero on rapid re-trigger; transitions are interruptible with matching exits. |
| `01-foundation.css:438`: `.card { will-change: transform; }` | Remove permanent `will-change` from idle cards | Permanently promoting 41 cards wastes mobile GPU memory. |
| Stacked `backdrop-filter`: `html::before/after` under `.theme-toggle`/`floating-path`; `.filter-panel` wrapping `.playlist-card`; `.edit-actions` over `.panel`; full-screen `blur(36px)` on album/artist rooms (`art-room.css:17`) | Unstack nested blurs (`DESIGN.md:11`), add missing `-webkit-backdrop-filter` (`theme-mode.css:64`, `03-filter:451`), cap/replace `blur(36px)` ≤ `16-20px` | Double backdrop readback + >20px full-viewport blur tanks mobile/Safari scroll FPS. |
| `entry-room.css:1388,1418`, `p53-transmission.css:441,608,631`, `error-page.css:10`, `03-filter:373`: keyframes animating `box-shadow` & `filter: blur()/saturate()` | Move PEEK pulse to a `::before` layer animating `opacity`; keep ambient keyframes `transform`/`opacity`-only | Animating `box-shadow`/`filter` every frame forces continuous CPU/GPU repaints. |
| `home-layout.js:23-31`: `120ms` blackout delaying `.view-btn.active`/`aria-pressed` | Update button active/`aria-pressed` synchronously; trim/skip blackout (instant under reduced motion) | High-frequency layout switcher feels delayed when its own button waits `120ms`. |
| 37 hand-typed `cubic-bezier(.2,.8,.2,1)` across 9 CSS files vs unused `--ease-in-out` | Consolidate onto `--ease-out`, `--ease-in-out`, `--ease-drawer`; load `gsi-tokens.css` on `404.html` & editors | Eliminates token/curve drift (`DESIGN.md:49-51`). |

---

## 4. Prioritized Animation Audit & Missed Opportunities (`AUDIT.md`)

| # | Severity | Category | Location | Finding | Fix summary |
| --- | --- | --- | --- | --- | --- |
| 1 | **HIGH** | Accessibility | `03-filter:272-295`, `04-cards:344-351`, `entry-room.css:1161`, `recommend.css`, editors, `home-layout.js:23`, `home-filters.js:127` | `.filter-collapsing !important` beats reduced-motion; 6 files nuke all opacity/color fades; `.cover` mask stripped; `recommend`/editors/JS timers ignore reduced motion | Drop `!important`, preserve `150ms` opacity/color fades, restore `.cover` mask, check `matchMedia` in JS |
| 2 | **HIGH** | Performance | `03-filter:10,266-290`, `01-foundation:172`, `entry-room.css:514` | `padding`/`margin`/`max-height`/`grid-template-rows` transitions | Replace with compositor-only `transform`/`opacity` under `220ms` |
| 3 | **HIGH** | Accessibility | 15 CSS files (`theme-mode.css` 29×, `entry-room.css` 25×, `p53-transmission.css` 22×, etc.) | 128 ungated `:hover` + 2 partial `(hover: hover)` rules leak onto touch | Gate all `:hover` with `@media (hover: hover) and (pointer: fine)` |
| 4 | **HIGH** | Physicality | `entry-room.css:924-927` + 9 stylesheets | Static prose `.section-card` shrinks on `:active`; 9+ real buttons/cards lack `:active` | Remove `.section-card:active`; standardize `:active` scale (`0.97` / `0.985`, `80ms`) |
| 5 | **HIGH** | Performance | `error-page.css:10,16-18`, `entry-room.css:312,487,1418`, `p53-transmission.css:441,631`, `03-filter:373` | `border-radius` morphing + continuous `box-shadow`/`filter` keyframes | Freeze radius; move glow pulse to pseudo-element `opacity` |
| 6 | **HIGH** | Performance | `theme-mode.css:64,1754-1764`, `03-filter:8,451`, `private-entry.css:246,587`, `art-room.css:17`, `01-foundation:438`, `entry-room.css:16` | 3 stacked `backdrop-filter` pairs; `blur(36px)`; permanent `will-change` on 41 cards; `background-attachment: fixed` on mobile | Unstack blurs, cap blur ≤ 20px, drop idle `will-change`, reset `background-attachment: scroll` ≤ 1024px |
| 7 | **MEDIUM** | Purpose / Freq | `home-layout.js:23-31`, `home-filters.js:104,193`, `entry-page.js:149`, `p53-transmission.js:801` | `120ms` view-switch button delay; dead JS animation classes (`.signal-transforming`, `.filter-entering`; note `test_p53_share.js:271` asserts `.signal-auditioning`) | Sync button state immediately; prune dead timers/classes (keep or update test for `.signal-auditioning`) |
| 8 | **MEDIUM** | Easing / Duration | 6 `transition: all`, 13 transitions `> 300ms`, 15+ bare `ease` | Sluggish durations (up to `700ms`/`720ms`) and `transition: all` | Explicit properties, `150–250ms var(--ease-out)` |
| 9 | **MEDIUM** | Interruptibility | `03-filter:146-153`, `p53-transmission.css:660-675`, `01-foundation:356-372`, `entry-room.css:503-534` | Keyframes on drawer, modal, and album groups; abrupt snap-close; symmetric enter/exit | Transitions + `@starting-style` with ~30% snappier exit |
| 10 | **LOW** | Cohesion | `gsi-tokens.css:24-28` vs 37 hand-typed curves | Token drift & 8 inconsistent `:active` scales (`0.92`–`0.995`) | Standardize on token curves + 2 press scales |

**4 Grounded Missed Opportunities:**
1. **P53 `<dialog id="story-modal">` exit & `::backdrop` fade** (`p53-transmission.css:638-675`): Use `@starting-style` + `transition-behavior: allow-discrete` (`220ms` in / `150ms` out).
2. **Filter drawer (`#filter-drawer-body`) origin-anchored close** (`03-filter-and-controls.css:146-153`, `home-filters.js:49`): `transform-origin: top` + `150ms` exit instead of snapping via `hidden = true`.
3. **PEEK button state crossfade** (`entry-page.js:148-180`, `p53-transmission.js:800-832`): Stable `min-width` + `150ms` `opacity`/`blur(2px)` label transition between `PEEK ▶` / `PEEKING ⏸` / `PAUSED ▶`.
4. **Theme toggle icon & segmented dock indicator polish** (`theme-mode.js:48`, `03-filter-and-controls.css:525-574`): Brief sun/moon crossfade and smooth sliding active pill indicator.

---

## 5. Mobile-Native Checklist (`mobile-native/SKILL.md`)

| # | Check | Status | Code Evidence | Hardware Verification Note |
| --- | --- | --- | --- | --- |
| 1 | Sticky hover gating | **FAIL** | 128 ungated + 2 partial `:hover` rules across 15 CSS files | Must confirm on real Pixel/iOS |
| 2 | Tap highlight (`-webkit-tap-highlight-color: transparent`) | **FAIL** | 0 occurrences anywhere | Must confirm on real Pixel/iOS |
| 3 | Viewport height (`100dvh` / `100svh`) | **PARTIAL** | 19 `vh` vs 4 `dvh`/`svh` (all 9 `body` rules + desktop `.story-modal` use `vh`) | Must confirm URL bar show/hide on hardware |
| 4 | Input `>= 16px` & mobile keyboard attrs | **PARTIAL** | `recommend.css:13` PASSES (`16px`). **FAILS** above `680px`/`768px` (landscape phones/tablets) in `new-entry.css:71,113` (`12.3px` textarea!) & `private-entry.css:264,275,506` (`14.4px`); missing `@media (pointer: coarse)` & `enterkeyhint`/`interactive-widget=resizes-content` | Must confirm Safari auto-zoom & Pixel keyboard-vs-dock |
| 5 | `touch-action: manipulation` & `>= 44px` targets | **FAIL** | 0 `touch-action: manipulation`. Sub-44px Chrome-measured targets on `390×844`: `.floating-path a` (`23×23px`, `43×16px`), dock buttons (`26px` tall), `#filter-drawer-toggle` (`28px`), `#filter-clear-quick-btn` (`28×28px`), `.filter-btn` / `.recommend-link` / `.theme-toggle` (`38px`), `.also-appears a` (`14px`) | Code-verified sizes; confirm 300ms delay & tap feel on hardware |
| 6 | Overscroll (`overscroll-behavior`) | **FAIL** | 0 occurrences; `.story-modal-body` (`p53-transmission.css:745`) & `.markdown-preview` (`new-entry.css:117`) need `overscroll-behavior: contain` | Must confirm scroll chaining on hardware |
| 7 | Safe areas (`viewport-fit=cover` + `env()`) | **FAIL (CRITICAL)** | 16 `env(safe-area-inset-*)` in `web/styles/` + 1 in `private-entry.css`, but **0 of 8 `templates/*.html`** and `new-entry.html` include `viewport-fit=cover` | Code-verified; test notch/gesture bar after adding meta |
| 8 | `user-select: none` + `-webkit-touch-callout: none` on controls | **FAIL** | 0 occurrences anywhere (correctly absent on prose, missing on buttons/pills/tabs) | Must confirm long-press on iOS/Android |
| 9 | Horizontal gesture surfaces | **PASS (N/A)** | No carousels or `touch-action: none` traps | Code-verified |
| 10 | Dynamic `<meta name="theme-color">` & `color-scheme` | **FAIL** | `theme-mode.js` never updates `theme-color`; 4 templates omit it; `theme-mode.css:7-8` sets `:root { color-scheme: light }` while default is `dark` | Code-verified; confirm status bar tint on Pixel/iOS |
| 11 | `-webkit-text-size-adjust: 100%` | **FAIL** | 0 occurrences anywhere | Must confirm landscape iOS |

---

## 6. `break-ui` Adversarial Stress-Test Report

*(Rows marked **[Chrome]** verified in live Chrome captures/built HTML; rows marked **[Source]** verified statically from CSS/JS/Python.)*

### Part 1 — What Broke

| # | Severity | Field | Worst-case value | What happens | Fix (`file:line`) |
| --- | --- | --- | --- | --- | --- |
| 1 | **Broken** | Masthead at narrow width **[Chrome]** | `320px` + `Chaperone` / `Recommend ↗` | `Recommend ↗` overlaps wordmark & subtitle (`home_narrow320_dim.png`) | Allow wrap or compact actions `< 420px` (`02-hero-and-filter-room.css:34-82`, `04-cards-and-responsive.css:83-110`) |
| 2 | **Broken** | Album LIT unreviewed & badge **[Chrome]** | LIT mode on `Live It Out` / `Currents` | `Track 02..10` drops to **1.04:1** contrast; `3 / 10 ARCHIVED` pink-on-pink (`album_liveitout_desktop_lit.png`) | Add `:root[data-gsi-theme="light"]` ink overrides (`album-room.css:43-79`, `theme-mode.css:1048`) |
| 3 | **Broken** | 404 overflow/height **[Source]** | `1440×720` or `200%` zoom + long track | `body { overflow: hidden }` clips card & actions completely | `overflow-x: hidden; overflow-y: auto;` (`error-page.css:4`) |
| 4 | **Broken** | Active filter pill (`#filter-active-pill`) **[Source]** | 40-char filter label at `320px` | `.filter-drawer-lead` lacks `min-width: 0; overflow: hidden`; pushes caret/clear button or overflows fixed `28px` height | Add `min-width: 0; overflow: hidden;`, ellipsis on `#filter-active-text`, use `min-height: 44px` (`03-filter-and-controls.css:34-82`) |
| 5 | **Broken** | Fixed-height chrome at 200% zoom **[Source]** | Root font-size `200%` | Fixed `height`/`max-height` (`38px`, `28px`, `42px`) on recommend, filter bar, filter buttons, and dock clip text; `px` fonts ignore root zoom | Use `min-height` + vertical padding; migrate core type scale to `rem` (`02-hero:112`, `03-filter:34,166,513`, `04-cards:72,146`) |
| 6 | **Broken** | Empty filter (`0` items) **[Source]** | Filter with `0` matching tracks | `.grid` collapses to blank void with no empty state or clear CTA | Render empty-state panel + "Clear filter" button when `visibleCount === 0` (`home-format.js:44-49`, `home-filters.js:211`) |
| 7 | **Ugly** | Count `= 1` plurals **[Chrome]** | `1` signal (`Currents`, `ASTROWORLD`, `Slowdive`) | Built HTML renders `"ALBUM / 01 SIGNALS"`, JS `"01 signals"`, P53 `"01 FACTORS"` | Singularize at `count === 1` (`home-state.js:40-42`, `templates/album.html:13`, `catalog_pages.py:290`, `p53-landing.html:17`, `p53_pages.py:259`) |
| 8 | **Ugly** | Broken/missing cover (`404` or `""`) **[Source]** | Missing cover JPEG or empty `cover_file` | Broken-image icon; homepage omits `<img>` on empty `cover_file` (collapsed card) | Add `.cover-missing` aspect-square fallback + `onerror` handler (`home_page.py:64-66`, `entry_pages.py:148`, `catalog_pages.py:199`) |
| 9 | **Ugly** | Unbreakable long string **[Source]** | Long URL / compound German title | `.info h2`, desktop `.info p`, Entry `.meta h1`, P53 `.artist`/`.album`, 404 `#signal-track` lack `overflow-wrap: anywhere` | Add `overflow-wrap: anywhere; min-width: 0;` (`01-foundation.css:491-502`, `entry-room.css:245-255`, `p53-transmission.css:202-218`, `error-page.css:22-23`) |
| 10 | **Ugly** | Long mobile breadcrumb **[Source]** | Long artist + filter name at `320–390px` | `.floating-path` wraps 3–4 lines, exceeding `70px` top clearance and covering hero | Clamp single-line with segment truncation (`theme-mode.css:1916-1928`) |
| 11 | **Ugly** | Stacked diacritics (`Đặng Thị Ngọc Hân`) **[Source]** | Tight `line-height: 0.78–0.86` + clamp | Clips tall ascenders/descenders (`p53-landing.css:113`, `album-room.css:2`, `01-foundation.css:393-400`) | Display `line-height >= 0.96`; card title `>= 1.22` |
| 12 | **Ugly** | Large counts (`1,284`) **[Source]** | `1284` tracks | Unformatted raw integer (`1284`) without locale separator | Format `>= 1000` with `Intl.NumberFormat` / `{n:,}` (`home-state.js:35-42`, `home_page.py:144`, `catalog_pages.py:207`) |
| 13 | **Ugly** | RTL / Arabic titles **[Source]** | `نور الهدى عبد الرحمن` | Arrows & `border-left` notes don't mirror; bidi punctuation shifts | Add `dir="auto"` on user/catalogue text & `border-inline-start` (`p53-transmission.css:225`, `artist-room.css:134`, `album-room.css:2`) |
| 14 | **Fragile** | Ultrawide `2560px` homepage **[Source]** | `2560×1440` | Full-bleed stretch across 2480px (`01-foundation.css:7-26`) | Optional `max-width: 1600px; margin-inline: auto;` (`02-hero-and-filter-room.css:2`) |
| 15 | **Fragile** | 12+ tags on `.also-appears` **[Source]** | 12 tags + 44-char tag | Dense wall of 14px-tall tap targets (`entry-room.css:673-685`) | Pill spacing (`min-height: 36px`) or `+N` overflow |
| 16 | **Fragile** | Unbounded schema/form lengths **[Source]** | Uncapped fields | No max lengths in `gsi_validation.py:173-343`; `recommend.html:34-36` only caps `name` | Add matching length limits in validator & form |

### Part 2 — Design Decisions Needing User Sign-Off (`AGENTS.md` / `ROADMAP.md`)
1. **Desktop Entry Hero Layout:** Cap `.cover-frame` at `min(100%, 540px, 60vh)` OR return to a 2-column cover-left / meta-right hero `>= 1024px` so song title + artist + PEEK/streaming controls sit above the fold instead of hitting `html::after`. *(Recommend capped `520px` or 2-column `>= 1024px`.)*
2. **Homepage `2560px` Ultrawide Cap:** Keep edge-to-edge archive wall OR cap homepage container at `1600px` centered. *(Recommend `1600px` cap so P53 bar & filter dock stay scannable.)*
3. **Homepage Card Truncated Title Tooltip:** Add `title="Track — Artist"` on `.card` so 2-line clamped titles remain readable on desktop hover.
4. **Desktop Entry Section Grid Void (`Charge` vs `Sonic Attraction`):** Switch `.sections` to `align-items: start` (or masonry/single-column editorial stack for short notes) so a 1-line `Charge` card doesn't stretch to a giant empty box beside a 10-line card.
5. **Public `site/tools/` Policy:** Keep Entry Loader public (stripping private auth UI/route strings) OR exclude `site/tools/` from public Pages (updating `deploy-pages.yml:39-41` and `test_catalog_renderers.py:207-225`).

### Part 3 — What Held Up in `break-ui`
- Escaping (`<script>alert(1)</script>`, `**bold**`) stays literal across Python & JS.
- P53 Story Card canvas (`p53-transmission.js:205-241`) handles grapheme splitting, long unbroken words, and dynamic contrast.
- Mobile homepage grids use `minmax(0, 1fr)`; covers use `aspect-ratio: 1; object-fit: cover;`; filter pill counts use `font-variant-numeric: tabular-nums`.

---

## 7. Performance, Asset Payload, CSS Debt & Accessibility

### A. Measured `site/` Payload (`17.73 MB` across 233 files) & High-ROI Wins
- **Inline `--art-rim-gradient` bloat:** `130,262 B` (**52.2%**) of `site/index.html` (`243.5 KiB`) and `129,109 B` (**64.5%**) of `site/data/catalog.json` (`195.4 KiB`) are unused 32-stop `radial-gradient()` inline variables (`builder/home_page.py:75` fails to pass `rim_gradient=""`, while `.card` always uses `--art-card-rim-gradient` first). Stripping it cuts `index.html` by >50% and `catalog.json` by ~65% immediately.
- **Render-blocking `<head>` script:** `<script src="scripts/theme-mode.js">` lacks `defer` on all 8 templates despite the inline FOUC IIFE above it.
- **Raw TTF font:** `SpaceGrotesk-VariableFont_wght.ttf` (`131.0 KB`) is ~60% larger than WOFF2 and lacks `<link rel="preload" as="font">`.
- **Oversized & orphaned images:** `covers/P53_cover.jpg` (`3.79 MB`, OG-only), `covers/GSI_share.png` (`1.42 MB`), unused root `P53_icon.png` (`1.39 MB`), orphan `covers/royal-blood-ten-tonne-skeleton.jpg` (`738.3 KB`), `artist-assets/metric.webp` (`654.8 KB`), `covers/k-flay-time-for-you.jpg` (`431.1 KB`), `covers/P53_cover-runtime.webp` (`404.7 KB` LCP), plus duplicate Metric/Matt Maeson/Beach House JPEGs copied verbatim into `site/covers/`.
- **Image attributes:** 320/349 `<img>` (91.7%) lack `width`/`height`; 114/349 lack `loading`/`decoding`.
- **Dead View Transitions markup:** 41 homepage + 28 entry `<img>` emit inline `view-transition-name: cover-<slug>` with 0 `@view-transition` rules or `startViewTransition()` calls (41 unnecessary stacking contexts).
- **Redundant build I/O:** `signal_enrichment.json` parsed 46×/build; `config.json` parsed ~48×/build; `artwork_palette()` opens each image 4× and re-quantizes `P53_cover-runtime.webp` ~24×/build; `copy_site_scripts`/`copy_site_styles` never purge deleted files; `catalog_pages.py:299` ignores `output_dir` when `album_routes` is passed.

### B. CSS Architecture & Cascade Debt (`348.9 kB` total across 19 files)
- `theme-mode.css` (`2,038 lines`, `92.4 kB / 90.3 KiB`) and `entry-room.css` (`1,583 lines`, `65.4 kB / 63.9 KiB`) represent **45.2%** of all CSS, stacking up to 12 chronological redesign passes without removing superseded rules (e.g., `.meta` 37 blocks, `.playlist-card` 27 blocks, light P53 transmission 47 blocks).
- **84 `!important` declarations** (`theme-mode.css: 31`, `03-filter: 20`), causing active conflicts (`03-filter:181,238,247` kills 5 light-mode box-shadows in `theme-mode.css`; `03-filter:289` defeats `prefers-reduced-motion`).
- **22+ dead CSS selector families** (0 production references), including `.entry-index` (25 rules), `.view-cycle-*`/`.format-cycle-*`/`.cycle-dots` (24 rules), `.hero-copy`/`.hero-architecture` (15 rules), `.recommend-line-1/2` (9 rules).
- *Note:* Per `AGENTS.md`, full CSS consolidation/tokenization is scheduled post-1.0; only conflicting rules and dead bugs should be touched pre-1.0 unless approved.

### C. Accessibility Gaps (WCAG / ARIA / Keyboard)
- Missing `<main>` landmark on `templates/index.html` and no skip-to-content link on any template.
- Keyboard focus drops to `<body>` when clicking/activating `#filter-clear-quick-btn` (`×`) (`home-filters.js:63,118`).
- `#filter-count` lacks `aria-live="polite"` / `role="status"` announcements (`builder/home_page.py:185`).
- `templates/p53-transmission.html:67`: `<canvas id="story-card-canvas">` lacks `role="img"`.
- Breadcrumb `→` separators (`<span class="trace-separator">`) lack `aria-hidden="true"`.
- `recommend.css:13`: `outline: none` on inputs + zero `:focus-visible` rules on buttons/links.
- `.filter-btn` missing `type="button"` (`home_page.py:141`); SSR PEEK button omits `aria-pressed="false"` & `aria-hidden="true"` on `.peek-icon` (`gsi_links.py:155`); `edit-entry.html:33-36` tablist lacks `aria-controls`/`role="tabpanel"`/Arrow navigation.
- 4 mid-luminance covers dip to `4.08–4.49:1` on `field` vs `field_ink` (`coffee-bean`, `this-briefest-kiss`, `november`, `combat-baby`).

### D. Data & Runtime Hygiene
- **PEEK audio duplication (`173` verbatim lines)** across `entry-page.js:106-278` and `p53-transmission.js:758-930`; misreports network failures as `"Audio playback blocked by browser"`; doesn't pause on `visibilitychange` or outbound Spotify/Apple click.
- **Data quirks:** Duplicate `order` values in `tracks.csv` (`1` on rows 2 & 14; `2` on rows 5 & 15) + `gsi_data.py:53-62` silently ignores `newest_first: true` for all 22 unordered rows; `personal`/`bassline`/`ulas` share one Apple playlist URL (`config.json:211,222,233`); `pop` includes `?a=join&it=...`; `signal_enrichment.json` missing 2/41 signals (`minefield-of-memory`, `10-lovers`); 0/41 canonical Spotify URLs; 18/28 entries have 0 authored prose sections; `PROJECT_STATE.md:522-528` has mangled `\t`/`\b`/`\a` escapes.
- **Minor font/copy leaks:** `recommend.html` `<h1>` uses `Trebuchet MS` + white text-shadow halo (`recommend.css:114`); `.story-btn` & canvas story card hardcode `Arial` (`p53-transmission.css:785`, `p53-transmission.js:502-596`) instead of `Space Grotesk`.

### E. Android Companion Sync (`android/`, `tools/export_android_reviews.py`)
- `preBuild` review export works cleanly, **but** `android/app/src/main/assets/data/catalog.json` (`202.5 KB`, including `129 KB` of unused CSS `rim_gradient`) and `p53_config.json` are stale manual snapshots (**4 slugs already diverge** on covers/metadata).
- `android/app/src/main/assets/covers/` is **`12.20 MiB` (51 files)**, of which **`7.07 MiB` (10 files)** are unreferenced by Android's bundled data/Kotlin (`P53_cover.jpg` 3.79 MB, `GSI_share.png` 1.42 MB, `P53_icon.png` 1.39 MB, etc.).
- `GsiRepository.kt:14,128-145` uses an unbounded, unsynchronized `mutableMapOf<String, ImageBitmap>()` decoding full-res bitmaps on the caller thread (`ROADMAP.md:45`).

---

## 8. Recommended Implementation Roadmap & New Ideas

### Phase A — Stabilization & Quick Wins (Safe, High-ROI, Zero Redesign)
1. **Horizon 2 Authoring Bug & LAN Security Pack:** Fix `_append_tracks_row`, CLI `artist_note`/`album_note`, `loadEntry()` `clearFormFields()`, `Sonical→Sonic` + `editor-config.json` fetch, `pagehide` autosave flush + reload-from-disk button, `_update_p53` tail move, publish lock, `secrets.token_urlsafe(24)` + `HttpOnly` + `Origin` + auth on `/api/entry-drafts`.
2. **Broken Visual & A11y Patch:** Album LIT ink overrides, 320px masthead wrap/compact, 404 LIT mode + `../covers/` path + `gsi-tokens.css` + `overflow-y: auto`, DIM active dock contrast, `#filter-active-pill` `--filter-color`, `recommend.css` `+4px` overflow + `Space Grotesk` + `:focus-visible`, `p53/index.html` reverse-chronological sort, `gsi_links.py` double-escape fix, sub-page `gsi-theme-change` listeners, `<main>` + skip link + `#filter-count` `aria-live` + quick-clear focus return + `role="img"` on canvas.
3. **Mobile-Native Baseline & Motion Cleanup:** Add `viewport-fit=cover` to all 8 templates, `-webkit-tap-highlight-color: transparent`, `touch-action: manipulation`, `user-select: none` on controls, `overscroll-behavior: contain` on modal/preview, dynamic `<meta name="theme-color">` in `theme-mode.js`, remove `.section-card:active`, lift mobile tap targets to `>= 44px`, fix `.filter-collapsing !important` reduced-motion conflict, gate all 128 `:hover` rules behind `@media (hover: hover) and (pointer: fine)`, and fix `overnight_audit.py` (229 errors → 0) + gate GitHub Actions CI on all tests & `--validate-links`.

### Phase B — Performance & Cross-Platform Sync (~70% Lighter)
4. **Payload Diet:** Strip unused `rim_gradient` from homepage cards & `catalog.json` (`index.html` `243 KB → ~115 KB`, `catalog.json` `195 KB → ~71 KB`), convert `Space Grotesk` to WOFF2 + preload, add `defer` to `theme-mode.js`, generate sized WebP cover derivatives + `width`/`height` on `<img>`, exclude raw 3.79 MB `P53_cover.jpg` and 3 orphans from `site/covers/`, and remove dead `view-transition-name` attributes (or opt in properly with `@view-transition { navigation: auto; }` scoped to the clicked card).
5. **Unified Web → Android Sync (`ROADMAP.md:20,44-45`):** Add a Gradle `syncAndroidArchive` task exporting slim `catalog.json`, live `p53_config.json`, and downsized WebP covers for referenced tracks only (**12.2 MiB → ~1.5–2 MiB**), plus `LruCache` + `inSampleSize` in `GsiRepository.kt`.

### Phase C — High-Leverage New Implementations (Requires Approval per `AGENTS.md`)
6. **Shared `peek-player.js` + Continuous Radio P53 Audition (Horizon 3):** Deduplicate the 173-line PEEK player into one module, add tab-hide pause & better network error recovery, fill the 2 missing `signal_enrichment.json` previews, and enable optional sequential playback across all 18 Radio P53 transmissions.
7. **Instant Keyboard Jump Overlay (`Ctrl+K` / `/`, Horizon 4):** Zero-animation (per Emil's high-frequency rule!), instant client-side search across all 41 songs, 29 artists, 36 albums, and 8 mood tags powered by the slimmed `catalog.json`.
8. **Flexible Entry Weights (Horizon 2):** Support compact *Signal Observations* / *Memory Capsules* (1–2 paragraphs without 7-section boilerplate) so the 18 currently empty entries can carry quick notes without feeling unfinished — and optionally add a personal non-generic rating/intensity scale if desired.
9. **Post-1.0 CSS Consolidation:** Collapse `theme-mode.css` (`92.4 kB`) and `entry-room.css` (`65.4 kB`) into clean semantic dark/light tokens, removing the 12 historical override layers and 22+ dead selector families.

---

## 9. Hidden Test/Audit Contracts (Watch Before Editing)
- `tools/overnight_audit.py:192-195` asserts `searchParams.set("theme"` and `setTheme(initial, true)` exist in `theme-mode.js`.
- `tests/test_p53_share.js:271,277,286` asserts `body.classList.contains("signal-auditioning")`.
- `.github/workflows/deploy-pages.yml:39-41` and `tests/test_catalog_renderers.py:207-225` assert `site/tools/new-entry.{html,css,js}` exist.
