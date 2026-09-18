# Local review tools

These scripts produce audit artifacts. They never edit `tracks.csv`,
`config.json`, entries, covers, or generated pages.

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
