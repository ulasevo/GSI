# GSI Strategic Roadmap

This document outlines the active operational horizons and future explorations for **Genome Stability Inducers**.

The central philosophy governing this roadmap is:
> *“The machinery must serve the archive. Coding is not supposed to consume the writing permanently, though it is valid for coding and writing to alternate depending on available attention.”*

---

## Current focus — 1 November 2026

Chaperone is the preferred name, but the user is still designing its logo: a quarter note in a capped barrel inspired by GroEL/GroES. Do not replace the existing GSI name or assets until the identity is ready.

- [x] First Android slice: archive → song detail → back; current Radio P53 is independent of selection; listening and website links use catalogue data; cards use semantic clicks and spring motion. A debug APK compiled. API 37 remains intentional. Review prose stays on the website until a native content-export decision.
- [x] First website wording pass: simplify P53, entry and catalogue labels while keeping the user's writing and project terminology. The site was regenerated with internal links validated.
- [x] First P53 share-card redesign: use the real album and note with quieter P53 artwork; remove the simulated image button and slug. Share the canonical URL when supported and retain image-only, download, and copy-link fallbacks. Visual/device review remains open; receiving apps can discard links.
- [x] Export the nonempty authored review sections for songs in the app's bundled catalogue at Android build time, using the website's entry parser. A debug APK builds with the generated reviews included.
- [ ] Try the Android APK on the Pixel: check appearance, native reviews, press and transition feel, links, scroll restoration and back navigation. The app has not been device-tested in this pass.
- [ ] Visually review the redesigned P53 share card and test the actual link handoff in the intended destination apps.
- [ ] Design a reliable catalogue and cover sync: review prose updates at build time, but new songs and covers are not automatically added to the app's existing bundled snapshot.
- [ ] Once the logo and visual direction are ready, revisit the home page and song-room hierarchy on phone and desktop, then decide how Chaperone should appear across the site and app.

The 26 October section below records background and options, not a list of simultaneous priorities.

---

## Design and Android planning — 26 October 2026

These are directions for discussion and experiments, not approval to redesign, rename, or migrate the archive. Keep existing writing, the P53 identity, and album-specific atmospheres intact. The user has installed the Android prototype on a Pixel 10 and intentionally chose API 37 as its minimum; keep that choice.

### Identity: GSI, Chaperone, or Sonome

- GSI / Genome Stability Inducers carries the existing biological metaphor and personal history. Chaperone suggests protection, companionship, and a biological connection; Sonome suggests sound and genome. These are impressions, not final names.
- Naming, a logo, and any eventual rename are separate decisions. P53 and the project's history do not need to disappear if the public-facing name changes. A paired name, such as a new title with GSI as a subtitle, is an option to explore rather than a decision.
- Develop a small set of visibly different identity directions: a typographic archive or label mark; a protective or looping form for Chaperone; and an abstract sound or genome form for Sonome. Avoid treating a generic music note or DNA helix as the only possible answer.
- Compare wordmarks, a monochrome mark, a small favicon, and an Android launcher icon at their real sizes and in both themes. Discuss pronunciation and emotional fit. Check names, domains, handles, and rights before any public rename; availability has not been checked.

### Android: an expressive, complete journey

- First slice: archive → song room → back. A tap should open the selected song, preserve archive position and filter state when returning, and leave the actual P53 current transmission separate from the selected song. The prototype currently hard-codes the P53 selection and reuses the selected song in its hero.
- Motion language: make springy movement visible and purposeful: a quick press and release on cards, a responsive filter selection, and a distinctive but controlled archive-to-entry transition. Explore shape, position, and scale, not vibration alone. Support rapid taps, interrupted gestures, back navigation, and system motion settings; avoid perpetual bounce.
- Material 3 Expressive provides motion schemes and Compose provides interruptible springs. Check the project's resolved Material 3 version before choosing specific APIs. Give the interactions GSI's character instead of applying default effects indiscriminately.
- Use semantic clickable controls and comfortably sized touch targets. Coordinate subtle haptics with meaningful actions and respect system feedback preferences; cancelled gestures should not produce a success response.
- Keep song metadata, writing, cover references, P53 records, and identity tied to the existing authored catalogue. Define an explicit repeatable export/sync path instead of maintaining a second handwritten catalogue. Confirm how and when bundled app content updates before adding network sync.
- Load appropriately sized artwork on demand and bound its cache as the catalogue grows. Profile only when needed and evaluate the experience on the Pixel 10: taps, scroll, transition, back, settings, and actual haptic feel. The current source was inspected, but the app has not been visually evaluated in this planning session.

### Website: hierarchy while keeping the atmosphere

- Mobile homepage: compare two compact compositions that retain the introduction and P53 artwork while bringing an archive card into or close to the first viewport. Check selected and cleared filters, both themes, and desktop before choosing a direction.
- Archive controls: explore a compact direct chooser or a clearer cycling affordance for WALL/GALLERY/POSTER and SONGS/ALBUMS. Make available choices and current state understandable without filling the page with permanent controls.
- Song rooms: compare the existing immersive cover-first composition with one that reveals title and listening controls sooner on desktop and mobile. Preserve the shrine feeling, personal section names, writing, and per-album colour. Review long titles, contrast, section navigation, crosslinks, and touch targets.
- PEEK: make the short-preview function and playing/paused state clear visually and to assistive technology. Verify playback, completion, failure, and navigation away without claiming a browser screenshot proves audio works.

### P53 share: art direction and working handoff

- Treat this as a fresh artistic direction, not a polish pass. Compare two or three distinct concepts using real transmission content and real story dimensions; decide the visual direction with the user before replacing the existing screen.
- The current image contains a button-shaped “LISTEN TO TRANSMISSION”, but the image itself cannot be clicked. The normal image-share payload does not include the canonical URL; the fallback link-share path does. Design the card and a working route back to the transmission together, with clear copy-link and download fallbacks.
- Test what the target share sheet and destinations actually preserve: a destination can discard accompanying text or URLs. Do not assume a native share sheet automatically creates a tappable story link. Check cancellation, unsupported sharing, errors, preview legibility, and keyboard/focus behaviour.

### Suggested order and decisions

1. Explore the three names and a few logo directions without changing the brand.
2. Define and try one Android expressive-motion prototype and the archive-to-entry journey; get Pixel 10 feedback before expanding it.
3. Present homepage, controls, and entry-room alternatives for desktop and mobile; choose a direction before implementation.
4. Present P53 share-card art directions and the recipient's link journey; implement and test the chosen flow.
5. Keep archive expansion active alongside this work: the machinery should make it easier to turn existing song notes into entries, not postpone that indefinitely.

Open decisions: which name and relationship to GSI feel right; which mark and share-card direction fit; how much of the intro and P53 hero should be visible on arrival; and how lively the Android transitions should feel. A rename, UI redesign, and any change to the data model require explicit approval under the working instructions.

---

## Active Horizons

### Horizon 1: Repository Sterility & Operational Hygiene *(Completed)*
- [x] **Purge Historical Binaries**: Removed 73+ MB of untracked and redundant legacy snapshots, phone video recordings, and duplicate pre-v2.0 directories from Git.
- [x] **Retire Parity Regression Test**: Retired `test_migration_parity.py` in favor of comprehensive modular tests (`test_catalog_renderers.py`, `test_source_contract.py`, `test_provider_links.py`, `test_submission_server.py`).
- [x] **Public Security Audit**: Verified zero secrets, tokens, or private authoring endpoints are exposed to the public GitHub Pages deployment.
- [x] **Systematic Documentation Suite**:
  - Authored primary root [`README.md`](README.md).
  - Authored [`ROADMAP.md`](ROADMAP.md) (this document).
  - Authored [`docs/AUTHORING_GUIDE.md`](docs/AUTHORING_GUIDE.md).
  - Consolidated [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
  - Hardened [`.gitignore`](.gitignore) against archives, media dumps, and local candidate reports.

---

### Horizon 2: Authoring Workflow & Archive Expansion *(Active Next Focus)*
*Focus: Lowering friction to writing and growing the song catalogue.*

- [ ] **Frictionless Mobile Authoring Over LAN**:
  - Streamline running `tools/submission_server.py` with persistent local authentication tokens (`GSI_LOCAL_AUTH_TOKEN`).
  - Verify phone browser layout for `/tools/editor/private/edit-entry.html` and `new-entry.html` with touch-friendly form fields and tactile submission feedback.
  - Improve real-time cover fetching and fallback handling when authoring directly from a mobile device.
- [ ] **Expanded Phenotype & Entry Formats**:
  - Support varied entry weights beyond long-form reviews:
    - *Phenotype Reviews*: Complete multi-section deep dives (e.g., “Empty”, “Combat Baby”).
    - *Signal Observations*: 1–2 paragraph acoustic reactions focusing on texture, switch, or distortion.
    - *Memory Capsules*: Short vignettes linking a song to a specific personal time, place, or grind.
    - *Catalogue Anchors*: High-importance tracks catalogued with metadata and PEEK audio previews.
- [ ] **Catalogue Additions**:
  - Add queued James Blake entries and expand artist room notes.
  - Expand catalogue towards 35+ tracks while maintaining high curation standards.
- [ ] **Draft Recovery & Resilience**:
  - Harden local storage autosave in `draft-contract.js` to ensure in-progress review prose is never lost on browser refresh or accidental tab closure.

---

## Future Explorations *(Under Discussion)*

*The following horizons represent prospective design and engineering directions to be discussed and prioritized once Horizon 2 is underway.*

### Horizon 3: Radio P53 & Ambient Sonic Experience
- **Continuous Radio Audition**:
  - Optional sequential playback mode for `/p53/`, transforming the history of 18+ transmissions into a continuous ambient radio stream.
- **Reactive Waveform / Signal Canvas**:
  - Ambient visual canvas in the P53 transmission room that oscillates subtly in response to audio playback without introducing heavy third-party audio libraries.
- **Permanent Transmission Receipts**:
  - Distinctive shareable cards / receipts for individual transmissions with custom OpenGraph metadata previewing album art and selected quotes.

### Horizon 4: Fast Discovery & Deep Reading
- **Keyboard Command & Search Overlay (`Ctrl+K` / `/`)**:
  - Instant client-side search overlay to quickly jump to songs, artists, or mood tags without leaving the keyboard.
- **Deep Reading Mode**:
  - Distraction-free typography view on entry pages optimized for deep reading and immersive listening on phones and tablets.
- **Mood / Phenotype Topography**:
  - Subtle visual matrix showing how tags (`bite`, `bassline`, `dreamy`, `personal`, `ulass-selection`, `p53`) connect disparate artists across the archive.
