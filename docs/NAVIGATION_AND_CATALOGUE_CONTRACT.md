# GSI navigation and catalogue contract

## URL state

GSI uses only the following optional homepage state:

| Parameter | Valid values | Meaning |
| --- | --- | --- |
| `filter` | configured filter keys | the active signal room |
| `view` | `poster`, `wall`, `gallery` | the selected layout |
| `format` | `albums` only; omission means Songs | the selected catalogue format |
| `artist` | a generated artist slug | an artist-route context, not a homepage control |

Unknown values are ignored. URLs should omit default state where possible.

## Return behavior

- A homepage card carries valid `filter`, `view`, and `format` into the page it opens.
- An entry opened from Albums returns to the same filtered Albums state through its GSI path.
- An album room returns to the same homepage state and passes it to its song links.
- Artist and P53 rooms preserve valid homepage context on their GSI return links. `artist` remains only where it gives a meaningful trace.
- Browser Back remains native. GSI context links supplement it; they never replace it with a session-history feature.

## Catalogue meaning

- Songs are the primary records.
- An album room exists only once two or more represented songs share an artist and displayed album name.
- Filtered Albums use the whole-album rule recorded in `AUDIT_2026-09-16.md`.
- Artist rooms include P53-only signals only when the artist has two or more represented signals. Those records link to their P53 transmission and are visibly labelled as transmissions, not as written entries.
- Album names and user prose are exact source data. No code may normalize their casing or manufacture an interpretation.

## P53 meaning

Radio P53 is a sequence of transmissions, not a second generic catalogue. A P53 page may retain context back to the homepage, but its visual labels must describe a real status or action.
