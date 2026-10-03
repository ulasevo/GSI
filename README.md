# Genome Stability Inducers (GSI)

> A personal, generated music archive: part review collection, part memory system, part visual listening environment.

Genome Stability Inducers is a metaphor for music that stabilizes, mutates, preserves, awakens, distorts, or carries versions of you. While borrowing terminology from genomics and cellular resilience, GSI is not a generic music database or public review platform—it is an intimate, subjective sonic vault built with deliberate craftsmanship.

The project exists as two equally vital dimensions:
1. **The Archive**: Songs, phenotype classifications, personal memory notes, album shrines, and recurring transmissions such as Radio P53.
2. **The Machinery**: A bespoke Python build pipeline, strict metadata contracts, semantic tokenized CSS/JS, and an authenticated local authoring environment.

---

## The Visual Spaces

- **The Archive Wall (`/`)**: A dynamic signal room displaying the catalogue across three layout modes (**Wall**, **Poster**, **Gallery**) and two collection formats (**Songs** vs. **Albums**). Features live filtering across curated phenotypes (`bite`, `bassline`, `dreamy`, `personal`, `ulass-selection`, `p53`), album-sampled blurred perimeter gradients, and tactile aperture physics.
- **The Listening Rooms & Album Shrines (`/entries/`, `/albums/`, `/artists/`)**: Intimate listening chambers pairing deep review prose with rich track badges, artwork-sampled accent lighting, and 30-second `PEEK ▶` audio previews.
- **Radio P53 (`/p53/`)**: Transmissions representing songs on loop during damage, stress, or periods of intense cellular restoration.
- **Recommend a Signal (`/recommend.html`)**: An ambient submission terminal for queuing song recommendations directly into the local curation inbox.

---

## Technical Architecture

```text
tracks.csv + config.json + entries/*.md + covers/ + artist-assets/
                            ↓
             builder/ (source pipeline & routing)
                            ↓
         templates/ + web/styles/ + web/scripts/
                            ↓
          site/ (pure static HTML, CSS, JS, WebP)
```

- **Zero-Framework Frontend**: Vanilla ES6+, semantic HTML5, and CSS custom properties (`web/styles/gsi-tokens.css`). No build bundlers, npm dependencies, or runtime frameworks.
- **Full Theme Persistence**: Coordinated light and dark themes with tactile controls and cross-page state retention.
- **Strict Separation of Concerns**: Python prepares data and routes; `templates/` own the HTML skeleton; CSS defines layout and state aesthetics; JavaScript manages interaction state and URL query preservation.
- **Zero Public Attack Surface**: The public site deployed to GitHub Pages is strictly static HTML/CSS/JS. All authoring, submission handling, and draft ingestion live behind an authenticated, localhost/LAN-bound local server.

---

## Safe Build & Verification Workflow

```bash
# 1. Verify Python and configuration integrity
python -m py_compile build.py tools/submission_server.py
python -m json.tool config.json

# 2. Run the full unit test suite
python -m unittest discover -s tests

# 3. Run the overnight bounded audit (verifies assets, routes, and links)
python tools/overnight_audit.py

# 4. Build the static site and validate internal link relationships
python build.py --site-only --validate-links
```

---

## Local Authoring & Curation

GSI includes a private local authoring suite for drafting and publishing entries directly from your desktop or phone over local LAN.

```bash
# Start the authenticated local authoring server
python tools/submission_server.py 8021 --auth-token "your-secret-token"
```

For detailed instructions on authoring entries, review schemas, mood tags, and phone authoring, refer to [docs/AUTHORING_GUIDE.md](docs/AUTHORING_GUIDE.md).

For deep pipeline mechanics and browser layer patterns, refer to [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Project Governance

- [AGENTS.md](AGENTS.md): Constitution, invariants, source-of-truth rules, and safety guardrails for AI pair-programming.
- [ROADMAP.md](ROADMAP.md): Forward-looking horizons, active priorities, and milestone tracking.
- [PROJECT_STATE.md](PROJECT_STATE.md): Authoritative system state, data contracts, and design history.
