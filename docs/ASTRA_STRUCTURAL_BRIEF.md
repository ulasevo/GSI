# Astra structural brief

## Role

You are reviewing GSI as a senior information-architecture and systems designer.
This document is a place for recommendations only. Do not edit source files,
generate code, or change data.

## Questions to answer

- Which structural changes should come next, and in what order?
- How should dynamic entry creation, album/artist growth, and the future private
  submission workflow fit the current source-of-truth model?
- Which parts of the Python builder, metadata contract, URL state, and generated
  page relationships are fragile or unnecessarily coupled?
- What can be improved without a broad pre-1.0 modular rewrite?
- What validation, migration, or rollback safeguards should accompany each step?

## Constraints

- Preserve the personal language and all existing writing in `entries/`.
- Treat `tracks.csv`, `config.json`, the entry Markdown, local artwork, and the
  builder as distinct responsibilities.
- Do not propose generic CMS features unless they directly serve GSI.
- Separate high-confidence mechanical work from decisions that need Ulaş's
  visual or content judgment.

## Repository evidence

Reviewed 17 September 2026. This is a recommendation document, not approval to
implement its proposals. Only this brief and `ASTRA_UI_BRIEF.md` are being edited.

- Intent and accepted contracts: `agents.md`, `PROJECT_STATE.md`,
  `DESIGN_BACKLOG.md`, `docs/AUDIT_2026-09-16.md`,
  `docs/IMPLEMENTATION_ROADMAP.md`, and
  `docs/NAVIGATION_AND_CATALOGUE_CONTRACT.md`.
- Sources: `tracks.csv` (24 rows), `config.json` (17 P53 records), representative
  populated and template-only entry Markdown, and the optional local
  `artist-assets/` contract. Display strings, including album casing, are data.
- Generation: `build.py`, `gsi_data.py`, `gsi_text.py`, `gsi_assets.py`,
  `gsi_links.py`, `gsi_artists.py`, and `gsi_validation.py`; shared and page-specific
  browser helpers under `web/scripts/` and styles under `web/styles/`; `.github/workflows/deploy-pages.yml`.
- Existing generated HTML and manifests: 37 archive signals, seven eligible
  artist rooms, and two album rooms (`Live It Out` and `Bloom`). The observed
  tree contained 54 HTML files; the previous audit's 53-page sweep is historical
  evidence, not proof of this exact output. Generated files were read, not rebuilt.

### Reconciliation with the project notes

The historical approximately 1,000-line monolith and future-only P53 description
are no longer the implementation. The builder is now approximately 2,000 lines,
with contained helper modules and several extracted browser/style files. Filter
rooms, URL state, section help, a populated-section index, deployment workflow,
P53 history, artist rooms, and album rooms already exist. Do not repeat those
phases or reverse their accepted decisions. The roadmap's recent reconciliation
is the better sequence; older `PROJECT_STATE.md` and backlog passages remain
design history.

The core distinction remains sound:

| Source | Owns | Must not become |
| --- | --- | --- |
| `tracks.csv` | Represented song metadata, tags, ordering, exact provider overrides | Review prose or a submissions inbox |
| `entries/*.md` | Irreplaceable personal writing | A disposable cache |
| `config.json` | Room definitions, section explanations, P53 selections/notes, supplied artist/album notes | An unbounded private-message database |
| `covers/`, `artist-assets/` | Reviewed local visual assets | Browser-upload or automatically scraped public storage |
| Python, `templates/`, and `web/` | Generation, presentation, interaction | Editorial authority |
| `site/`, including its manifests | Derived public output | A source to edit or a place for private information |

Actual cover behavior is more precise than the old priority list: an existing
manual local file wins; otherwise an existing slug-named cache is reused unless
refresh is requested; only when downloading is needed does the manual URL take
precedence over iTunes lookup. A changed remote URL does not automatically replace
an existing cache. Manual accent overrides remain authoritative.

### Confidence and audit limits

Findings below are source-backed; conditional failures are labelled as such.
No browser/device session, fresh build, deployment, or external link probe was
performed for these briefs. The shell's `python` command was unavailable; the
bundled Python runtime was subsequently located for a read-only invocation of
`validate_generated_links(Path('site'))`: zero errors in the existing generated
output. This is not a fresh-build, runtime-navigation, or external-link check. Prior
headless results remain useful but do not cover future data or real Pixel/tablet
behavior.

## Recommendations

The order below is deliberate. M = high-confidence mechanical work, still subject
to an implementation request. D = a decision that Ulaş must approve first.

### 1. Put a preflight gate before any source or output mutation — M

**Problem.** `read_tracks()` and `load_config()` parse syntax but do not enforce
the source contract. `build_entries()` can begin synchronizing files before it
discovers a bad later row. `slugify()` drops non-ASCII characters and punctuation;
different display names can therefore map to the same filename. Empty/duplicate
slugs, mismatched P53 records, unknown tags, malformed colors, and unsafe artwork
paths are not comprehensively rejected. Provider URL checks verify host/scheme,
not whether a URL really identifies the claimed song.

**Direction and likely touchpoints.** Add a bounded preflight to `gsi_validation.py`
and invoke it at the start of `build.py:main()`, before `build_entries()`. Check
required columns/nonblank fields, row shape, unique resolved routes, configured
tags, section-ID collisions, P53 current-slug membership, local-file containment,
and accent shape. Make an invalid explicit link a visible warning or error, not
an unexplained replacement. Distinguish blockers from permissible absences such
as a blank exact provider link or an artist without a portrait. The same safe
path resolver must govern reads/downloads, not only manifest reporting.

**Dependencies/risk.** Freeze current valid values first; do not silently correct
capitalization, edition names, author prose, or ambiguous duplicates. Existing
repeated numeric `order` values are valid ties under the current stable sort;
they are not evidence of dates or a per-filter ranking system.

**Validation.** In isolated fixtures, reject two names that collapse to one slug,
a quote/backslash-containing title, invalid P53 current selection, unknown tag,
and a path leaving its asset directory before *any* write. Confirm all current
sources pass or produce explicitly reviewed warnings. Test decoded image content,
not just a successful download response.

### 2. Make entry creation an explicit authoring operation — M first, D for interface

**Problem.** A normal build creates missing Markdown, rewrites metadata, appends
headings, downloads artwork, and renders pages together. `--site-only` correctly
avoids those source edits/downloads, but still overwrites generated output and
stops on a missing Markdown source. It is not a dry run. Importing `build.py` also
creates directories at module scope. This is a poor foundation for an owner form.

**Direction and likely touchpoints.** Reuse `make_markdown_template()` and
`build_entries()` through a small, explicitly invoked creation path: collect
metadata; resolve/review identity and artwork; show the proposed row, filename,
and source diff; create only the new record; then preview the site. A command-line
helper is the smallest first interface. An owner-only local form can follow if
it saves meaningful effort; a static public page cannot safely write these files.
Do not equate dynamic authoring with a runtime public CMS.

Protect the prose boundary before expanding metadata synchronization.
`sync_entry_metadata()` replaces lines across the whole document, not only a
defined metadata block; `extract_sections_from_markdown()` also strips matching
metadata lines globally. These patterns can affect future legitimate prose.
Existing frontmatter construction does not escape embedded quotes. Separate
metadata from authored section bodies, and compare those bodies byte-for-byte
before/after a synchronization. Missing-section detection should compare complete
headings, not substring matches. Make reruns idempotent: repeating the operation
must not duplicate a row, file, or heading.

**Dependencies/risk.** Requires preflight and a reviewed backup/restore path.
Decide whether adding a metadata-only song is immediately publishable; current
template-only entries are already published without pretending to be reviews.
Do not introduce a draft/published field without a concrete authoring need and
an approved data-model change.

**Validation.** Add one new fixture, repeat the command, simulate an interrupted
save, and confirm existing writing is unchanged. Preview must not require remote
artwork availability. Keep the previous sources and deployed artifact recoverable.

### 3. Freeze identity before enabling renames or repeated transmissions — D

**Problem.** Song identity is currently `slugify(artist + track)`, so correcting a
title can create a new Markdown file and remove the old generated entry while
leaving its writing stranded. Album identity is the exact `(artist, album)` pair;
artist identity is an exact display name plus a derived route. P53 pages and notes
are keyed by song slug, so selecting the same song twice cannot currently retain
two independent transmission notes/permalinks.

**Direction and likely touchpoints.** First detect collisions without migrating.
Then approve the smallest durable-identity addition: retain each current route
as its stable identifier, with an explicit override for future display edits.
Do not regenerate all slugs or normalize display names. Only if repeated P53
appearances are wanted, give a transmission its own immutable identity referring
to a song; add a date only when Ulaş supplies a real date. Keep existing song-slug
P53 URLs working. Separate “one represented song” from “multiple appearances.”
Likely touchpoints are `tracks.csv`, P53 configuration, `gsi_text.py:slugify()`,
`prepare_p53_history()`, and route-building consumers; these changes need a
separate migration proposal, not an opportunistic extra field in a UI patch.

**Dependencies/risk.** Decide edition/remaster and collaboration identity only
when an actual ambiguity appears. `Humbug (Bonus Track Version)` must not silently
merge with another edition; `mangetout` must not be title-cased. New identities
affect filenames, notes, share URLs, manifests, and preserved external links.

**Validation.** Produce an old-to-new inventory before migration; require one
destination per old URL, unchanged prose hashes, and explicit alias handling.
Test a display-name edit and two transmissions of one song. Rollback restores
both source mappings and the last complete generated artifact.

### 4. Use one generated relationship inventory for every doorway — M, with one D

**Problem.** Shared artist eligibility is a strong improvement, but several
relationships are still inferred independently. P53's entry counterpart checks
whether a Markdown file exists, not whether `main()` will generate that entry.
An orphaned Markdown file can therefore produce a broken link. The landing page
falls back to the first P53 record when the current slug is invalid, while
permanent pages still label by the invalid configured slug; the homepage may
omit the broadcast entirely. Album groups are reconstructed in Python and the
homepage DOM independently. Album appearance also takes the first song's artwork
and accent, so changing song order can change the album room's visual identity.

**Direction and likely touchpoints.** Build a small in-memory inventory in
`main()` after validation: generated entry routes, eligible artist/album routes,
P53 routes, current transmission, and per-signal destination kind. Pass that to
`build_p53_page()`, `build_p53_archive()`, `build_index_html()`,
`build_album_pages()`, and existing manifests instead of using filesystem
existence as semantic evidence. Preserve the whole-album filter rule and
two-represented-signal eligibility. Album pages should identify transmission
destinations as honestly as artist pages already do; `Bloom` is a useful real
mixed entry/P53 example.

**Decision.** Define `show_in_archive` narrowly or broadly. Today it controls
homepage merging and album participation, but `artist_room_groups()` includes
P53 history regardless of this flag, and permanent transmissions remain public.
It is not a privacy switch. Do not change this behavior without choosing whether
the flag means homepage visibility or all public-catalogue visibility. A future
album artwork/accent override should be opt-in and reviewed, not inferred from
an artist's presumed identity.

**Validation.** Test a P53-only artist, orphaned Markdown, one-to-two-song album
threshold, hidden archive selection, invalid current slug, and mixed-destination
album. Every offered route must occur in the expected output inventory. Counts
must describe represented signals, not total discography or completed writing.

### 5. Close the remaining URL-state and output-lifecycle gaps — M

**Problem.** `GSIContext` is the right shared layer, but the P53 landing helper
forwards arbitrary `filter`/`artist` values without generated eligibility data.
Permanent P53 pages accept an artist slug matching the song name without checking
that an artist room exists. `album-room.js` forwards incoming artist context to
artist links but drops it on song links. Some secondary entry links still bypass
the context helper. The shared contract says unknown values are ignored and
artist context is retained only when meaningful. A filesystem-link checker
cannot exercise these runtime paths.

Entries and artist rooms remove obsolete generated pages; album and P53 outputs
do not have equivalent cleanup. In-place builds can retain a stale album room or
`latest.html`. Copying all artwork also publishes every file in the source asset
directories, whether used or not.

**Direction and likely touchpoints.** Feed validated relationship data to
`web/scripts/p53-landing.js`, `web/scripts/p53-transmission.js`, `web/scripts/album-room.js`, and the entry
helper. Keep browser Back native. Decide separately whether default `view=wall`
should be omitted; URL state currently includes valid views explicitly, which
also avoids ambiguity with a saved local preference. For output, prefer a fresh
staging directory validated before publication. If a staging change is too large,
start with an expected-output manifest and dry-run stale-file report confined to
generated output. Never delete source Markdown because a record was removed.

**Dependencies/risk.** Relationship inventory first. Removed P53 records need an
explicit retention policy before cleanup: existing shared transmission links
are not ordinary disposable build debris. Do not sweep private messages into
the repository or copied asset trees.

**Validation.** Exercise filter + each view + Albums through home → album → song
→ GSI; artist → album → song; and P53 → entry → GSI. Repeat with fabricated query
values, blocked local storage, direct entry URLs, and native Back. Compare fresh
and repeated builds after a fixture loses album eligibility or current status;
there must be no accidental stale route and no broken promised permalink.

### 6. Keep the future submission workflow private and separate — D before implementation

**Problem.** There is no submission endpoint, private queue, mail integration,
or moderation model in the inspected source. The deployment workflow uploads
`site/` as static output. A public form alone cannot provide private intake or
safe mail delivery, and a suggestion must never become Ulaş's writing by default.

**Recommended minimal flow.** A public-facing suggestion form, if wanted, sends
one music link, a comment, and an optional username to a separate server-side
intake. The meaning of “private submission” should be confirmed: a public form
with a private inbox is different from an invitation-only form. Store a small
private receipt durably, then notify a fixed owner mailbox. Ulaş reviews it and
explicitly invokes the authoring path in item 2. The public archive continues to
be built from curated sources only. Private receipt states are operational
records, not new public GSI labels.

**Decisions required.** Choose who may submit, who receives mail, the hosting/mail
boundary, retention/deletion expectations, whether comments are required, and
whether a username can ever be credited publicly. Do not add an email field just
to support status updates; with only an optional username, no reply channel
exists. Receiving a submission does not promise publication or a response.

**Safety contract.** Keep credentials and private records outside `site/` and
public Git history. Bound field lengths, validate URLs, treat comments/usernames
as text, rate-limit intake, and constrain notification recipients. Do not fetch
arbitrary submitted URLs on the server merely to create previews; that introduces
an unnecessary remote-request attack surface. Escape mail content and prevent
user text from becoming mail headers. Add request deduplication so a retry does
not generate repeated suggestions or messages. A mail-only inbox is a possible
smaller alternative, but it must acknowledge mail acceptance rather than claim
durable storage or guaranteed delivery. `mailto:` is only a clearly labelled
manual fallback, not evidence a submission was received.

**Dependencies/risk.** Requires separate approval for an external service and any
cost; no provider selection or account creation is part of this audit. Private
retention is a product/security decision here, not a claim of legal compliance.

**Validation.** Demonstrate success only after actual intake acceptance; simulate
mail failure after storage, storage failure, repeated clicks, network loss,
invalid links, markup in comments, and rate limits. Preserve entered text on
recoverable failure. Inspect the entire public artifact for private comments,
usernames not approved for credit, inbox identifiers, and credentials. Promotion
must produce a reviewed source diff without copying visitor prose into an
author-owned review section.

### 7. Grow artist/album rooms by authored meaning, not inventory pressure — M/D

**Problem.** Artist/album rooms are useful relationships, not complete music
catalogues. Only Metric currently has configured local artist imagery and an
artist note; only `Live It Out` has an album note. The disabled Artists format
control is not evidence of a ready artist-browser design.

**Direction and likely touchpoints.** Retain current eligibility and the explicit
no-image fallback in `gsi_artists.py`. Test image-free rooms as first-class pages.
Keep short supplied notes in the current config while that remains comfortable;
move long-form album/artist writing into separately owned Markdown only when real
content warrants it and with an approved migration. An Artists format is a later
composition/coverage decision, not a reason to scrape portraits or create filler
biographies. Any future album image/accent override should preserve current
behavior by default and never modify song-specific manual overrides.

**Dependencies/risk.** Stable identity before relocating notes. Keep display
metadata distinct from search/provider identity. Do not imply that the represented
signal count measures an artist's importance or the completeness of a discography.

**Validation.** Compare Metric, Emily Haines & The Soft Skeleton (P53-only room),
Beach House (mixed destinations), and a single-signal artist with no room. Each
must remain truthful without invented prose or missing-art error chrome.

### 8. Make delivery tests the next extraction boundary — M

**Problem.** The existing offline validator is valuable but is optional, and the
deployment workflow runs `--site-only` without `--validate-links`. It does not
check generated `data-album-base-href`/`data-album-href` routes, duplicate IDs,
CSS image references, or interactive state. A manifest reporting
`cover.valid=false` is not currently itself a validation error. Large inline
entry/artist/album CSS and repeated overrides still make small edits hard to
reason about, but that does not justify a pre-1.0 rewrite.

**Direction and likely touchpoints.** First wire the existing validator into the
deployment build after its current output has been reviewed. Extend
`gsi_validation.py` with explicitly scoped cases and a few fixture tests. Keep
external provider availability checks optional; canonical/search classification
does not prove the destination song is correct or available. Set artwork budgets
from measured current image sizes before adding derivatives. Then extract one
stable page stylesheet at a time with no simultaneous restyling; templates or
broader Python modules come only after a separate approval and evidence of need.

**Validation and rollback.** Future Python patches must run the instructed
`python -m py_compile build.py`; config patches must run
`python -m json.tool config.json`; relevant implementation patches must run the
prescribed build in a protected source-copy fixture when its source-writing
behavior is under test, plus `python build.py --site-only --validate-links` for
delivery. Compile all changed helper modules too. Compare generated output and
prose hashes, inspect HTML/CSS/JavaScript, and run the UI brief's device matrix.
Deploy only a complete validated artifact; retain the previous artifact. Report
all warnings rather than treating compilation as completion.

### Recommended decision boundary

First implementation proposal: preflight, a small prose-preservation test set,
and existing-link validation in delivery. Review that patch independently. Next:
relationship/route consistency and generated-output ownership. Then choose the
owner entry-creation interface and identity rules. Private submission intake is
a separate later feature, not a prerequisite for writing the next song entry.

## Explicit non-goals

- No source, configuration, writing, artwork, generated-site, deployment, commit,
  or push changes in this audit.
- No broad modularization, template-engine migration, database/CMS replacement,
  SPA conversion, or rewrite of the existing static publishing model.
- No automatic review prose, album-title normalization, invented artist biography,
  inferred personal tags, reconstructed transmission dates, or fabricated status.
- No public submission wall, accounts, voting, recommendation engine, automatic
  publication, public moderation dashboard, or promise of replies.
- No artist-image scraping, provider credential in browser code, arbitrary remote
  URL fetching, or silent migration of existing public URLs.
- No archive/source deletion or bulk cleanup under the guise of output hygiene.
