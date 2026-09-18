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
