# GSI Strategic Roadmap

This document outlines the active operational horizons and future explorations for **Genome Stability Inducers**.

The central philosophy governing this roadmap is:
> *“The machinery must serve the archive. Coding is not supposed to consume the writing permanently, though it is valid for coding and writing to alternate depending on available attention.”*

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
