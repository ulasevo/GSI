# GSI implementation roadmap

This is deliberately phased so a visual experiment does not destabilize the catalogue underneath it. Each phase should be independently reviewable before a commit.

The next design and systems review is recorded separately in the [Astra
structural brief](ASTRA_STRUCTURAL_BRIEF.md) and [Astra UI brief](ASTRA_UI_BRIEF.md).
Those documents are recommendations only; they do not override this roadmap or
authorize implementation by themselves.

The active post-1.0 architecture work is tracked in the [migration plan](MIGRATION_PLAN.md).

## Phase 1 — reliable reading and travel

**Implemented locally; retain a final device/deployment sweep before release.**

- Fix entry-card grid geometry across desktop and mobile.
- Keep the generator auditable by extracting pure text/data helpers and artwork utilities before moving page markup.
- Keep shared browser state in one generated helper (`web/scripts/gsi-context.js`) so nested pages do not drift in their URL handling.
- Establish shared CSS tokens (`web/styles/gsi-tokens.css`) before migrating page-specific rules, so the Marathon type, spacing, color, and geometry language has one governed source.
- Make `filter`, `view`, and Albums format survive the homepage, entries, album rooms, artist rooms, and P53 return paths.
- Apply the accepted filtered-Album rule.
- Make `--site-only` genuinely avoid P53-cover downloading.
- Run source preflight before entry synchronization: required columns, known tags,
  route collisions, safe asset paths, P53 current membership, and site-only entry
  presence are now checked before the build mutates source files.
- Keep metadata synchronization inside the frontmatter and generated preamble;
  regression fixtures prove that authored lines resembling `Album` or `Accent`
  are preserved and that rerunning synchronization is idempotent.
- Derive route relationships once per build and emit `site/data/generation.json`;
  reconcile only managed generated families, retaining historical P53 slugs as
  permanent links.
- Validate that manifest relationships resolve during generated-link checks; keep
  P53 landing state on the shared sanitizer and preserve artist context from album
  rooms into their song links.

**Acceptance:** no entry-card overlap at the checked breakpoints; reloading a filtered Albums URL retains Albums; opening an album then a song can return to that same state; generated relationship routes agree with the expected output inventory.

## Phase 2 — Radio P53 hierarchy

**Implemented local baseline; revisit only with concrete visual feedback.**

- Remove labels that do not convey useful information.
- Reduce dead space and establish a predictable density between current and previous transmissions.
- Recompose permanent transmission pages so title, art, notes, and sharing are legible on mobile.

**Guardrail:** native scrolling stays; do not reintroduce a forced carousel or decorative sequence numbering.

### Refinement notes held for the next review

- The landing description should feel anchored to the P53 heading rather than
  hanging as an independent paragraph. Any adjustment should clarify the
  landing hierarchy without adding another explanatory label.
- The current-card RADIO / P53 watermark is background texture only. Rework its
  containment and legibility if needed, but do not turn it into a new status
  marker or a competing title.
- P53 landing and permanent transmission paths should expose the same real
  location context. Keep the state vocabulary deliberate: current transmission
  for the live slot, past transmission for historical slots, and no invented
  technical markings.
- The visual direction can become more expressive after the structure settles:
  use authored art, controlled glow, and album/artist imagery as emphasis rather
  than adding ornamental animation. Mobile remains a composition to validate,
  not a shrunken desktop layout.

The first refinement pass now replaces the fragile text watermark with a static
grid/radial field, aligns the landscape description to the landing grid, adds a
real transmission-state crumb to permanent P53 pages, and exposes qualifying
album rooms from entry metadata. These are structural affordances; the broader
art-direction pass remains intentionally small until the next device review.

The bounded delivery audit also found and fixed a 4px no-filter mobile overflow
in the Layout/Format controls. The control row and its optional playlist rail now
share an explicit responsive width and border-box contract.

## Phase 3 — catalogue breadth

**Core source contract implemented; artist imagery has a dormant, local-only contract.**

- P53-only signals are included in qualifying artist rooms as transmission links, without inventing entry prose.
- Artist-room generation and entry-page artist links share one eligibility inventory, so a future hidden transmission cannot create a link to a room that was never generated.
- Add only author-written artist and album context where supplied.
- `site/data/artists.json` now records eligible artist rooms, represented albums,
  and an explicit local-image/fallback state. The disabled Artists format control
  remains unchanged until an image source is reviewed.
- A reviewed local artist image now shares one bounded identity field with the
  artist name on desktop and becomes an unframed image within that field on mobile.

## Phase 4 — reading and orientation

**Section rail implemented; field guide remains intentionally deferred.**

- Signal trace refinements where the source context is real.
- Refine the section rail now that populated entries expose it; keep it limited to real prose.
- A compact field-guide layer only if it explains terminology without restating the homepage.

## Phase 5 — resilient delivery

**In progress.** Generated local-route validation is now available through
`python build.py --site-only --validate-links`, and the homepage presentation is
authored in ordered layers under `web/styles/home/` before being assembled into
`site/styles/gsi-home.css`; state remains in `web/scripts/home-page.js`. The generated
filter data is carried in a small JSON script node, keeping the behavior file
static without changing the query-state contract. The build now also emits
`site/data/catalog.json`, classifying provider links as canonical or search
fallbacks and recording local cover health. Artist/album room navigation now
lives in `web/scripts/artist-room.js` and `web/scripts/album-room.js`. Asset budgeting, broader
tests, and the final device/deployment sweep remain future work. The P53 landing
query-state and focus helper now lives in `web/scripts/p53-landing.js` alongside the
other browser helpers. Permanent transmission routing and sharing now live in
`web/scripts/p53-transmission.js` with a generated context node.

Provider reliability now has two offline-safe checks: `--audit-provider-links`
reports the current canonical/search split, and `tools/provider_candidates.py`
can write review-only candidates from provider search endpoints. Neither tool
edits source data automatically.

- Define a small asset budget for P53 art and defer noncritical images.
- Validate generated links, data attributes, provider URL shape, and manifest cover paths.
- Add an opt-in external availability check only if provider throttling and false
  positives can be bounded.
- Extract the remaining embedded CSS/JavaScript in contained slices and add
  generator tests once each surface has a stable contract.

## Out of scope unless explicitly reopened

- A generic recommendation engine, mood quiz, user accounts, gamification, or automatic interpretations of the writing.
