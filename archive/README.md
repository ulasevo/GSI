# Historical snapshots

These files are retained for rollback and comparison only. They are not read by
the builder and must not be used as runtime source.

- `legacy-builds/` — superseded monolithic builder copies.
- `baselines/` — dated source/config snapshots from visual experiments.
- `snapshots/` — dated ZIP backups.
- `legacy-inputs/` — placeholder or abandoned entry drafts and empty local
  history files kept for reference.
- `snapshots/GSI-backup-empty.zip` — an empty historical ZIP retained for
  provenance; it is not a usable backup.

The active source of truth remains the repository root, `entries/`, `covers/`,
`artist-assets/`, `web/`, and `docs/`. Generated output lives in the ignored
`site/` directory.
