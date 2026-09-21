# Local review tools

These scripts default to review-only artifacts. The authoring commands below
keep source mutation behind an explicit `--write` boundary; generated pages
are always produced by the normal build.

## Provider candidates

Run `python tools/provider_candidates.py` to query Apple Search and, when
`SPOTIFY_ACCESS_TOKEN` is available, Spotify Search. The result is written to
`audit/provider-candidates.json`. Review the top candidate and its confidence
before copying an exact URL into the source catalogue.

Use `--provider apple` or `--provider spotify` to limit a run, and `--output`
to choose another report path.

## New entry drafts

Paste an Apple Music song link to preview a complete source draft:

```text
python tools/new_entry.py "https://music.apple.com/...?...&i=..."
```

Apple's public lookup fills artist, track, album, and artwork metadata. The
draft contains every configured review heading as an empty, prompted section.
Add `--tags dreamy,bassline` and `--section "A new heading"` when needed.
You can also use `--sections "Charge, Sonical Attraction"` or several
space-separated headings. The configured headings remain available by default.

For the guided authoring flow, run:

```text
python tools/new_entry.py --interactive
```

It asks for the raw provider URL, optional metadata overrides, filters,
headings, custom headings, P53 membership, and final write confirmation.

The normal site build copies the browser authoring room into `site/tools/`
automatically. To install or refresh it in an existing generated site without
running the full build, use:

```text
python tools/new_entry.py --install-editor
```

Then open `/tools/new-entry.html`. On the private local server, the loader has
two separate handoff buttons:

- `SAVE DRAFT` writes a reviewable JSON draft into the ignored local inbox.
- `BUILD ENTRY + ROOMS` is the explicit local publish path. After resolving the
  provider URL and filling the writing rooms, it caches the cover, writes the
  Markdown entry and `tracks.csv` row, optionally updates P53, saves the artist
  note and album take, and runs the normal site build. The resulting artist and
  album rooms are created automatically, even when this is their first signal.

The generated Pages copy keeps the export/download controls but never exposes
the local publish endpoint. The local server remains bound to `127.0.0.1`.

If the machine cannot reach Apple's lookup endpoint, supply all three names to
use the link safely offline; the canonical Apple URL is still preserved:

```text
python tools/new_entry.py "https://music.apple.com/...?...&i=..." \
  --artist "Artist" --track "Track" --album "Album"
```

The command is preview-only by default. Add `--write` only after reviewing the
resolved metadata; add `--p53` if the song should also become an explicit P53
history record. Spotify links are accepted with explicit `--artist`, `--track`,
and `--album` values, but Spotify API metadata lookup is intentionally deferred.

A browser draft can be reviewed and committed with:

```text
python tools/new_entry.py --from-draft submissions/drafts/<draft>.json --write
```

The loader's P53 panel writes the `p53` tag, history record, optional
transmission note, and current-transmission pointer together. Its catalogue
room panel makes the downstream artist/album generation visible before you
publish, so `artist note` and `album take` are captured at the same time as the
entry.

Apple Music URLs are fully self-resolving: the loader obtains identity and
artwork from Apple's public lookup, then the local publish step caches the
600px cover. Spotify URLs remain a safe manual-identity path for now because
there is no unauthenticated metadata/artwork lookup in this private tool.

## Private local entry editing

The local server exposes a separate, non-generated editor at
`http://127.0.0.1:8021/__local/editor/edit-entry.html`. It reads source entries,
keeps the public Pages build untouched, and offers both ignored JSON drafts and
an explicit `SAVE + BUILD ENTRY` action. The editor also loads and saves the
artist note and album take associated with the selected signal:

```text
python tools/submission_server.py 8021
```

The route is intentionally bound to `127.0.0.1`; phone/LAN access should wait
until an explicit authentication and opt-in bind layer exists.

## Recommend a Signal intake

The generated `recommend.html` room is public-facing and intentionally weaker
than the private Entry Loader: visitors submit a provider link, a short note,
and an optional signature. It never writes an entry or changes the catalogue.

For a local review loop, build the site and run:

```text
python tools/submission_server.py 8021
```

Then open `http://127.0.0.1:8021/recommend.html`. Valid submissions are saved
as pending JSON under `submissions/inbox/`; invalid or unsupported links are
rejected. A static deployment without the intake process falls back to a
downloadable pending JSON file in the browser.

To inspect pending signals without changing GSI:

```text
python tools/recommendation_to_draft.py
python tools/recommendation_to_draft.py 20260919-123456-000000.json
```

The second command previews a Markdown draft. Add `--write-draft` only after
reviewing it; the file is written to `submissions/drafts/`, never to
`entries/` or `tracks.csv`. Apple links can resolve their identity; Spotify or
other provider links need `--artist`, `--track`, and `--album` overrides.

## Bounded overnight audit

Run the read-only integrity pass before a long local authoring session:

```text
python tools/overnight_audit.py
```

It checks source entry/cover relationships (including Markdown-owned cover
frontmatter), duplicate signal routes, P53 current/history consistency,
generated-route manifests, generated image loading/decoding attributes, and the
shared loader/theme contracts. It does not rewrite sources, download assets, or
touch Git state.
