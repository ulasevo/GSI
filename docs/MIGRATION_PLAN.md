# GSI architecture migration plan

This is the active post-1.0 migration plan. It is intentionally separate from
the visual backlog: the migration must make the existing site easier to change
without changing the archive’s language or navigation contract.

## Non-negotiable invariants

- `entries/*.md` remains the authoring source and its review prose is preserved.
- `python build.py` remains the supported command during the migration.
- `--site-only` never mutates source entries or performs cover downloads.
- Existing entry, album, artist, and P53 routes remain stable unless a route
  collision is reported before generation.
- Generated link validation and the route inventory remain green after every
  extraction slice.
- No visual redesign is bundled with a mechanical extraction unless its source
  ownership must change for the extraction to work.

## Stages

### 1. Compatibility shell and source pipeline — complete

`build.py` is now a stable facade. The source preparation stages live in
`builder/source_pipeline.py`, while the remaining renderer implementation is
temporarily isolated in `builder/legacy_pipeline.py`. This keeps the command and
test imports stable while the page layer moves.

### 2. Page-rendering boundary — complete

Radio P53 renderers now live in `builder/p53_pages.py`, artist/album rooms live
in `builder/catalog_pages.py`, entry reading rooms live in
`builder/entry_pages.py`, route/media manifests plus managed-output
reconciliation live in `builder/manifests.py`, the homepage renderer lives in
`builder/home_page.py`, and the 404 renderer lives in `builder/error_pages.py`.
Their generated routes and markup remain stable, while output/config/assets can
be supplied explicitly for isolated checks. `builder/legacy_pipeline.py` now
contains orchestration and compatibility exports only.

### 3. Template boundary — complete

Page-family templates now live in `templates/` and are rendered through the
small standard-library `builder/template_renderer.py`. Page builders prepare
escaped values and HTML fragments; templates contain only explicit markers,
page data nodes, and links to shared assets. The renderer fails loudly when a
marker is left unresolved.

### 4. Asset boundary — complete

CSS now lives in `web/styles/` and JavaScript in `web/scripts/`. The asset copy
stage mirrors those directories into `site/styles/` and `site/scripts/`.
Generated pages contain no page-level `<style>` blocks or executable inline
behavior; the remaining inline script nodes are JSON data consumed by external
helpers. A few generated components retain narrowly scoped inline custom
properties for per-record accent values, which are data rather than behavior.

### 5. Verification and release — in progress

`tests/test_migration_parity.py` compares the frozen baseline for route sets,
manifest counts, semantic internal links, image inventory, and preserved entry
prose. The current slice passes the full Python suite, Python compilation,
JavaScript syntax checks, site-only generation, full generation, and generated
link validation. A final device/deployment sweep remains before committing or
pushing the migration.

### 6. Authorship handoff — started

The extracted source now carries short ownership comments and plain-language
module notes. [docs/CODE_GUIDE.md](CODE_GUIDE.md) is the working map for the
next round: make one user-visible change, edit its owning source, rebuild, and
inspect the generated result. This handoff stays separate from the next visual
or feature sprint so the structure can be learned before it is extended.

## Deliberately deferred

- submission/mail workflow;
- public curation UI;
- new P53 motion or expressive art direction;
- automatic artist-image retrieval;
- broad template or dependency changes before the page-rendering boundary is
  proven.
