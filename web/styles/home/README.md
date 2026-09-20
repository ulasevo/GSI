# Homepage style parts

These four files are joined in the order named by `HOME_STYLE_PARTS` in
`gsi_assets.py`. The generated site still receives one
`styles/gsi-home.css`, so browsers and existing page links do not change.

- `01-foundation.css` — base page shell and the original stable rules.
- `02-hero-and-filter-room.css` — hero, Radio P53 feature, and filter-room art.
- `03-filter-and-controls.css` — filter descriptions, playlist, and controls.
- `04-cards-and-responsive.css` — cards, responsive layouts, and motion guards.

Keep the order stable. These rules intentionally build on one another, and the
later responsive layer is allowed to refine the earlier desktop rules.
