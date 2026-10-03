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

#### 1. Start the Authenticated Local Server
```powershell
python tools/submission_server.py 8021 --auth-token "your-secret-token"
```

#### 2. Access the Editor
- **Desktop**: Open `http://127.0.0.1:8021/__local/editor/edit-entry.html`
- **Phone / LAN**: Open `http://<your-lan-ip>:8021/__local/editor/edit-entry.html?token=your-secret-token`

#### 3. Authoring Features:
- **Load Existing Entry**: Dropdown selector to edit existing entries, update tags, or add missing sections.
- **Paste Apple Music URL**: Automatically queries public metadata to resolve artist, track title, album name, year, and artwork.
- **Autosave**: Drafts are continuously backed up to your browser's `localStorage`.
- **Publish Entry**: Atomically writes `tracks.csv`, saves `entries/<slug>.md`, creates an automatic source snapshot in `submissions/snapshots/`, and triggers a site rebuild.

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
