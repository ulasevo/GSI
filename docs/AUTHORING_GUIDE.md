# GSI Authoring & Curation Guide

> *“`entries/*.md` contains irreplaceable user writing. Never overwrite or remove review prose.”* — [AGENTS.md](../AGENTS.md)

This guide documents the data schemas, review structures, filter classifications, and authoring workflows for growing the **Genome Stability Inducers** archive.

---

## 1. Core Source Data Models

The archive relies on two primary authoring surfaces:

### `tracks.csv`
Contains song-level structured metadata and catalogue ordering:
```csv
order,tags,artist,track,album,cover_file,cover_url,accent,spotify_url,apple_url,signal_id
1,"personal, ulass-selection",Metric,Empty,Live It Out,metric-empty.jpg,,#a13838,https://...,https://...,sig-90d16f87452837bc4498
```
- **`artist` / `track` / `album`**: Core metadata (preserve original casing and punctuation).
- **`tags`**: Comma-separated list of active filter tags (must be quoted if multiple tags are set).
- **`cover_file`**: Preferred local image in `covers/` (e.g. `artist-track.jpg`).
- **`cover_url`**: Optional remote image fallback.
- **`accent`**: Hex color code for the song's primary visual aura (sampled from artwork or manually specified).
- **`spotify_url` / `apple_url`**: Exact streaming URLs. If blank, the builder automatically generates search links.
- **`signal_id`**: Durable random identifier (`sig-...`) linking the track across transmissions and manifests.

### `entries/<slug>.md`
Contains the personal review prose:
```markdown
---
artist: Metric
track: Empty
album: Live It Out
cover: covers/metric-empty.jpg
accent: "#a13838"
---

### Charge
What emotional, visceral, or cognitive state does this track trigger?

### Sonical Attraction
What sound detail pulls you in? Rhythm, bass, vocal texture, distortion, switch, silence.

### Lyric/Vocal Detail
Any line, delivery, breath, pronunciation, or vocal moment worth preserving.

### Version of ulaş
What version of me does this song store? Time period, grind, breakup, desire, motion.

### Lore
Any personal history, repeated use, place, habit, person attached to this track.

### Reading
What do I think the song is doing or narrating?

### Comment
Free field. Final take, vibe, joke, conclusion, or whatever does not fit elsewhere.
```

---

## 2. Review Formats & Weights

Not every song requires an exhaustive 7-section dissertation. GSI welcomes varied authoring weights:

1. **Phenotype Deep Dives**: Substantial multi-section reviews for foundational songs (e.g. Metric’s *Empty* or *Combat Baby*).
2. **Signal Observations**: Short 1–2 paragraph acoustic reactions focusing on texture, groove, switch, or distortion (e.g. using only *Charge* and *Sonical Attraction*).
3. **Memory Capsules**: Intimate vignettes linking a song to a specific era, person, or personal grind (e.g. *Version of ulaş* and *Lore*).
4. **Catalogue Anchors**: Vital songs indexed with metadata, artwork, and streaming previews, with prose added later as thoughts mature.

---

## 3. Mood Tags & Phenotypes

- **`bite`**: Sharp, aggressive, distorted, high-tempo, or caustic energy (e.g., *Perhaps Vampires Is A Bit Strong But...*, *Ten Tonne Skeleton*).
- **`bassline`**: Deep low-end groove, physical rhythm pulse, sub-bass pressure (e.g., *Let It Happen*, *Skin Graph*).
- **`dreamy`**: Ethereal, reverbed, shimmering, shoegaze, or atmospheric transport (e.g., *Sugar for the Pill*, *Wishes*).
- **`personal`**: Intimate emotional anchors, private memories, or pivotal personal markers.
- **`ulass-selection`**: Master curator picks defining the core identity of the archive.
- **`p53`**: Tracks on loop during acute stress, damage, or catalytic regeneration.

---

## 4. Authoring Workflows

### Method A: Browser Authoring Suite (Desktop & Phone LAN)

The private authoring suite allows creating or editing entries directly from a browser on your laptop or phone over your home Wi-Fi network.

#### 1. Start the Local Server (1 Command)
```powershell
.\serve.ps1
# or run `serve.cmd` in cmd / double-click from desktop
# or: python tools/serve.py
```
The server will automatically detect your local Wi-Fi / LAN IP, read or generate your persistent auth token in `.env`, and display a direct clickable link in the terminal:
```text
  Desktop:   http://127.0.0.1:8021/__local/editor/
  Phone LAN: http://192.168.1.6:8021/__local/editor/?token=gsi-author-xxxx
```

#### 2. Access the Unified Authoring Room
- Open the printed link on your desktop or phone browser.
- **Bookmark on Phone**: On your phone, bookmark the URL or add it to your home screen. The token is saved in your browser cookie and `localStorage`, so future visits authenticate automatically.
- **Tab 1: ＋ NEW SIGNAL**: Paste any Apple Music or Spotify link, click `RESOLVE ↗`, review the auto-resolved artist/track/album and artwork preview, and fill your review sections.
- **Tab 2: ✎ EDIT EXISTING**: Select any represented song from the catalogue dropdown to update tags, write missing sections, refine artist notes, or adjust P53 settings.
- **SAVE DRAFT**: Backs up your work to `submissions/drafts/`.
- **SAVE + BUILD ENTRY ↗**: Atomically updates `tracks.csv` and `entries/`, captures a recovery snapshot in `submissions/snapshots/`, rebuilds the static site, and provides an immediate button to open your new live room.

---

### Method B: Guided Terminal Workflow

For direct command-line authoring:

```bash
# Preview a draft from an Apple Music URL:
python tools/new_entry.py "https://music.apple.com/us/album/song-name/id?i=..."

# Interactive authoring wizard:
python tools/new_entry.py --interactive
```

---

## 5. Curation & Radio P53 Transmissions

To add or cycle the current active transmission on **Radio P53**:
1. Open [`config.json`](../config.json).
2. Set `"p53_current_slug"` to the slug of the active track (e.g., `"matt-maeson-stubborn-as-religion"`).
3. Update `"p53_current_signal_id"` to match its signal ID.
4. Add a transmission note in `"p53_transmission_notes"`:
   ```json
   "p53_transmission_notes": {
     "your-slug": "Your short transmission thought or quote."
   }
   ```
5. Ensure the track has an entry in `"p53_history"`.
6. Run `python build.py` to regenerate the P53 landing room and transmission page.
