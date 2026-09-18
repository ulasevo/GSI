# GSI migration parity baseline

This snapshot freezes the generated `site/` output immediately before the
template/styles/scripts migration sprint. It is reference material only; the
live build still writes to the repository's top-level `site/` directory.

- Captured: 2026-09-17
- Source command: `python build.py --validate-links`
- Files: 114
- Bytes: 11,044,555
- Compare routes, links, counts, assets, and authored prose against this copy
  after each migration boundary.

The snapshot is not a replacement for source data. `entries/*.md`, `tracks.csv`,
and `config.json` remain authoritative and must never be edited through this
directory.
