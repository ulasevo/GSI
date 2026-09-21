# GSI overnight audit notes

Date: 2026-09-21  
Scope: bounded local authoring, source integrity, generated-route integrity,
image delivery, and final functional visual coherency pass.  
Release target: v2.0.1 — Full editor and entry loader support.
Release commit: this checkpoint is committed on `codex/gsi-1.6-migration`;
the final commit hash is reported with the release handoff.

## Completed in this pass

- Added transactional rollback to the local `publish_draft` path. If cover
  caching, source writes, P53/catalogue updates, or the local build fails,
  `tracks.csv`, `config.json`, the entry, and the cover boundary are restored;
  a best-effort recovery build is attempted afterward.
- Added a regression test that simulates a failed build and confirms source
  restoration.
- Added `tools/overnight_audit.py`, a read-only integrity command covering:
  - source track/entry relationships;
  - Markdown-owned and CSV-owned cover paths;
  - duplicate signal routes;
  - P53 history/current consistency;
  - generated entry/P53/artist/album manifest routes;
  - theme URL-state, toggle, section-contrast, and loader publish contracts.
- Improved the final bounded visual pass without redesigning the UI:
  - light-mode Matt entry section cards no longer layer the dark artwork rim
    over dark text;
  - the LIT/DIM toggle uses a fixed flex track, centered thumb, and aligned
    label in both modes.
- Tightened generated image delivery without changing artwork or composition:
  - entry, album-room, and permanent-transmission hero covers are eager,
    high-priority, and asynchronously decoded;
  - homepage P53 art is eager while catalogue and historical transmission art
    is lazy and asynchronously decoded;
  - artist-room imagery is lazy/async, while reviewed artist header art stays
    eager/high priority;
  - `tools/overnight_audit.py` now rejects generated `<img>` elements that
    have a network source but no explicit loading/decoding strategy.
- Updated the implementation roadmap and local-tool guide to record the image
  delivery contract and the remaining infrastructure boundaries.
- Documented the audit command and current local authoring boundaries.

## Follow-up catalogue repair

- Added the missing `ulas` tag to Matt Maeson's `Stubborn As Religion` row.
- Added the missing `distortion` tag to Royal Blood's existing `Little Monster`
  row.
- Recovered the saved Ten Tonne Skeleton loader draft after its first publish
  attempt failed while the local process could not fetch the Apple CDN cover.
  The approved cover was cached, then the normal transactional publish path
  succeeded: the entry, catalogue row, shared Royal Blood album room, artist
  room membership, and both supplied room notes were generated.
- Made the homepage P53 filter reorder its cards by descending transmission
  order, including the Albums grouping path, so the newest signal is first
  rather than following CSV order.

## Verification results

- `python build.py --site-only --validate-links`: passed.
- Browser-state contract: passed.
- Python compilation: passed.
- JavaScript syntax check: passed.
- `python -m json.tool config.json`: passed.
- `git diff --check`: passed; only normal CRLF normalization warnings were
  reported by Git.
- `python tools/overnight_audit.py`: passed with zero errors and zero warnings.
- Site-only rebuild after the catalogue repair: passed with generated local-link
  validation.
- Browser-state contract: passed.
- The full Python suite currently reports 36 passing tests and one expected
  migration-parity failure because the authored `entries/metric-empty.md` prose
  was independently changed after the frozen baseline. That writing was
  preserved; no test or source was rewritten to hide the difference.
- Generated image delivery audit: passed; 47 copied site images, approximately
  10.3 MB total. The largest source remains the intentional P53 artwork; no
  lossy recompression was attempted during this functional pass.

Audit inventory at completion:

- 27 catalogue tracks
- 27 source entries
- 18 P53 history records
- 26 generated entry pages
- 20 generated P53 pages
- 28 generated artist pages
- 35 generated album pages
- current P53: `matt-maeson-stubborn-as-religion`

## Deferred deliberately

- Spotify metadata/artwork resolution: not needed for the Apple-first authoring
  path; revisit only as a cross-reference layer.
- Authenticated LAN/phone access: still requires an explicit security design.
- Broader performance work: byte-budget policy and deployment profiling remain
  separate from the completed loading-strategy pass.
- Stable signal IDs and deeper catalogue reconciliation remain future data-model
  work.

## Remaining large-scale work, deliberately not started

1. Authenticated opt-in LAN/phone authoring. The local server remains
   loopback-only; adding a bind flag without an authentication/session design
   would expose the private editor and publish endpoint.
2. Durable signal IDs and P53 appearance records. Current routes remain
   slug-compatible, but title corrections and repeated P53 appearances need a
   migration proposal with aliases and prose-hash rollback checks first.
3. Staging-output publication. A future build should render to a validated
   staging tree, then replace generated output atomically; the current build
   continues to use its established managed-output reconciliation.
4. Byte-budget/deployment profiling. The current pass makes image loading
   intentional, but it does not rewrite artwork or claim a CDN/compression
   policy without a deployment target.
