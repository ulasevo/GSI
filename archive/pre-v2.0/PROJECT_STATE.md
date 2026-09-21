# GSI Project State

This document records project intent, implemented systems, design history, unresolved problems, and the planned roadmap.

The repository files are the authority on what is currently implemented. This document is the authority on why the project was designed this way and where it is intended to go.

If the files and this document disagree, report the discrepancy rather than silently choosing one.

-What GSI is

GSI began as a place to archive songs that do something more significant than merely sounding good.

“Genome Stability Inducers” is your metaphor for music that stabilizes, mutates, preserves, awakens, distorts, or carries versions of you. The name borrows from genomic stability, but the archive is not pretending to be a scientific resource. It is personal language.

The project has two equally important products:

The archive itself — songs, reviews, notes, memories, classifications, and recurring projects such as P53.
The machinery — the Python builder, metadata system, filters, generated pages, visual logic, and eventually deployment.

The machinery must serve the archive. Coding is not supposed to consume the writing permanently, though it is valid for coding and writing to alternate depending on your available attention.

The site should eventually contain a mixture of:

fully written phenotype-style entries;
shorter signal notes;
sonic observations;
lore/history notes;
songs that are simply important enough to catalogue.

Not every entry needs to resemble the long review for “Empty.” A few dozen short entries plus approximately ten substantial pieces would already give the archive meaningful weight.

- Current folder model

The working structure should approximately be:

GSI/
├── build.py
├── config.json
├── tracks.csv
├── entries/
│   ├── artist-track.md
│   └── ...
├── covers/
│   ├── album-cover.jpg
│   ├── playlist-cover.jpg
│   └── ...
├── site/
│   ├── index.html
│   ├── entries/
│   │   ├── artist-track.html
│   │   └── ...
│   └── ...
├── AGENTS.md
└── PROJECT_STATE.md

The conceptual ownership is:

tracks.csv contains song-level structured data.
config.json contains site-level and filter-level behavior.
entries/*.md contains your writing.
covers/ contains controllable local visual assets.
build.py transforms sources into the website.
site/ is generated public output.

- Current song data

tracks.csv has grown throughout the project. Codex needs to inspect the real header, but the intended fields are approximately:

order,tags,artist,track,album,cover_file,cover_url,accent,spotify_url,apple_url

The intended rules are:

artist, track, and album are core metadata.
order optionally controls manual display order.
tags accepts one or multiple filters.
Multiple tags must be quoted because CSV commas separate fields:
1,"personal, ulass-selection",Metric,Empty,Live It Out,...
cover_file points to a local image and should be preferred.
cover_url is an optional direct web image URL.
accent is an optional manual hex override.
spotify_url and apple_url are optional exact song URLs.
Blank streaming URLs produce automatic search links.

The cover priority is intended to be roughly:

local cover_file
→ manual cover_url
→ automatic iTunes search/download
→ previously cached cover/fallback

Codex must confirm the exact current order in build.py.

- Configuration model

config.json controls stable site behavior rather than individual songs.

It has included fields such as:

{
  "project_title": "...",
  "page_title": "...",
  "intro": "...",
  "newest_first": true,
  "force_refresh_covers": false,
  "filters": {},
  "sections": []
}

Each filter contains approximately:

"personal": {
  "label": "Personal",
  "description": "Songs that got tangled with memory, body, recovery, desire, or some version of me.",
  "color": "#d64b6a",
  "playlist_url": "...",
  "playlist_cover": "covers/personal-playlist.jpg",
  "playlist_cta": "Want more of the same?"
}

Filter keys must exactly match values used in tracks.csv.

Stable filter identity belongs in config.json. Song-specific information belongs in tracks.csv.

- Builder behavior already implemented

The current builder is approximately 1,000 lines because Python, HTML, CSS, and JavaScript are still combined in one file.

It currently performs most or all of these jobs:

Data loading
Reads tracks.csv.
Reads config.json.
Orders tracks manually when order values exist.
Otherwise respects newest_first.
Cover handling
Uses local cover overrides.
Uses direct cover URLs.
Searches/downloads artwork through iTunes.
Caches images in covers/.
Avoids crashing completely when a remote image fails.
Accent extraction

The first implementation simply picked the most common image color, which frequently produced gray or nearly black accents.

The newer version:

reduces the image to a palette;
converts candidate colors to HSV;
rejects overly dark, overly pale, or desaturated candidates;
scores remaining colors based on saturation, brightness, and frequency;
allows a manual accent value to override the automatic result.

This significantly improved card borders and glows, although hand-picked overrides remain necessary for subjective cases such as ASTROWORLD or Live It Out.

Markdown entry safety

The builder creates a Markdown entry only when one does not already exist.

Existing files should:

retain all written review content;
receive corrected metadata when CSV values change;
receive newly introduced section headings if missing;
never have prose overwritten.

Hidden HTML comments beneath headings act as writing prompts but are stripped before rendering.

Entry-page generation

Each Markdown entry becomes a styled HTML page under:

site/entries/

Entry pages include:

album cover;
song title;
artist;
album;
accent-derived atmosphere;
rendered review sections;
Spotify and Apple Music links;
automatic search fallbacks when exact links are blank.

Streaming links were changed from pill-like controls toward quieter outbound actions:

Have a listen on:
Spotify ↗    Apple Music ↗
Homepage generation

The homepage includes:

GSI wordmark/hero;
project introduction;
filter controls;
active-filter description;
album-card grid;
dynamic show/hide filtering;
accent borders and glow;
playlist module support.

Clicking an active filter again clears it and restores all entries.

- Visual history and current design state

The original homepage was functional but generic.

A first identity pass added:

a large GSI wordmark;
skew;
colored shadow offsets;
a dark textured background;
stronger card glow;
more stylized filter controls.

That attempt drifted toward neon/cyber-grid rather than the intended Need for Speed: Most Wanted 2005 / industrial street / distressed garage language.

The useful parts retained were:

stronger hierarchy;
better filter controls;
more expressive album accents;
improved card hover behavior;
some title shimmer/wobble behavior.

The unresolved visual direction is not supposed to be a literal game replica. The desired vocabulary is closer to:

asphalt;
garage posters;
industrial labels;
stencil/distressed typography;
scratches and cut lines;
speed or scanner-like motion;
layered print misalignment;
loud homepage and intimate entry pages.

The site should not be entirely black/yellow or permanently grungy. Album artwork and filter colors still need room to shape the atmosphere.

- Latest implemented feature: filter playlists

Playlist support was added at the filter level.

A filter can provide:

playlist_url;
playlist_cover;
playlist_cta.

The builder:

loads the local playlist cover;
reuses the accent-extraction algorithm;
generates playlist data for JavaScript;
displays or hides the playlist card according to the selected filter.

The current playlist presentation is approximately:

[ square playlist cover ]
Want more of the same? ↗

It appears to the right of the active filter description.

The feature works, but the layout is unresolved. The large playlist card increases the height of the filter section, leaving substantial unused space beneath the short description and pushing the song grid downward.

You did not necessarily dislike the card’s size or placement. You disliked that the rest of the composition failed to respond to it.

Therefore, the playlist card should not simply be reduced or removed without discussing the surrounding transition.

- Exact current design problem

Default homepage state:

Hero
General GSI introduction
Filter buttons
All entries

Current filtered state:

Hero
General GSI introduction
Filter buttons
Filter description               Large playlist card
                                  Large vertical space
Filtered entries

The next design idea was to turn filter selection into a complete temporary “room.”

Proposed filtered state:

Hero
[general introduction fades/collapses]
Selected filter title + description       Playlist card
Filter-colored atmosphere
Filtered entries move upward

Clearing the filter would reverse the transition:

filter atmosphere fades;
playlist disappears;
filter description collapses;
project introduction returns;
all cards return.

The transition must be smooth and work on mobile. It should use a class such as:

document.body.classList.add("filter-active");

CSS then reacts to that class instead of JavaScript manually animating every property.

This was designated Patch 14 — Filter Room Transition.

It has not yet been completed.

- Likely GSI 1.0 roadmap

The priority list changed several times, but the coherent current route is:

Phase 1 — audit and repair

Codex should first:

compile Python;
validate JSON;
inspect the CSV header;
run the build;
look for malformed generated HTML/CSS;
identify lingering transcription errors;
verify streaming links;
verify playlist show/hide behavior.

No redesign should occur during the audit.

Phase 2 — filter-room transition

Implement:

subtle whole-page tint from active filter color;
general intro fade/collapse;
active filter area expansion;
playlist and filter description composition;
smooth restoration on clear;
reduced-motion fallback if practical.
Phase 3 — mobile integration

Do this only after the filter and playlist layout is structurally settled.

Mobile work must cover:

hero scaling;
filter wrapping;
filter-room layout;
playlist placement;
card grid;
entry hero;
streaming links;
hover-dependent interactions;
section help controls later.
Phase 4 — section information controls

Add small i controls beside section names.

Examples:

Charge ⓘ
Sonical Attraction ⓘ
Version of Ulaş ⓘ

They explain GSI’s private terminology.

These cannot be hover-only because phones do not have reliable hover. They should work with:

hover;
keyboard focus;
click/tap;
accessible text relationships.

Descriptions should be stored centrally, likely in config.json or a section-definition structure.

Phase 5 — deployment

The generated site/ folder should become available through a normal URL.

Python remains private build machinery. Visitors receive static HTML, CSS, JavaScript, and images; they do not need Python.

A stable GSI 1.0 deployment should happen before P53.

Phase 6 — content expansion

Once 1.0 is stable:

add the older P53 selections;
build toward 30–50 entries;
keep a mixture of short and long pieces;
prevent one artist or genre from unintentionally defining the archive.
Phase 7 — refactor

After 1.0, freeze a stable version and refactor on a branch.

Highest-value order:

Extract CSS.
Extract JavaScript.
Introduce templates.
Add input validation.
Add tests.
Split Python where justified.

The current f-string architecture should not remain forever, but rewriting it before 1.0 would risk losing momentum and introducing broad regressions.

Phase 8 — P53

Only after the baseline archive is stable.

- Radio P53 plan

Radio P53 is your weekly Wednesday song-sharing ritual.

The name comes from p53 as “guardian of the genome,” matching your view of music on a smaller, recurring scale.

The future implementation should use the code key:

p53

not radio-p53.

Each weekly selection should:

exist as a normal GSI song entry;
receive the p53 tag;
have a permanent weekly page;
retain a stable Instagram story link;
offer Spotify and Apple Music choices;
connect to the P53 playlist;
remain accessible after the week ends.

Possible permanent URL form:

site/p53/2026-08-05-song-slug.html

Potential convenience URL:

site/p53/latest.html

The weekly workflow should eventually be close to:

Add one song record.
Add a date and short note.
Run the builder.
Copy the generated permanent link.
Share on Instagram.

No weekly coding.

P53 should become a doorway into GSI, not a separate project bolted onto unstable machinery.

- Post-1.0 architecture

A likely cleaner structure:

GSI/
├── build.py
├── builder/
│   ├── config.py
│   ├── tracks.py
│   ├── covers.py
│   ├── markdown.py
│   └── pages.py
├── templates/
│   ├── index.html
│   ├── entry.html
│   └── p53.html
├── assets/
│   ├── css/
│   │   ├── base.css
│   │   ├── homepage.css
│   │   └── entry.css
│   └── js/
│       └── homepage.js
├── entries/
├── covers/
├── tracks.csv
├── config.json
└── site/

This is not an immediate instruction. It is the expected destination.

Templates would eliminate most giant HTML strings.

External CSS and JavaScript would eliminate doubled-brace confusion:

.card {
    display: flex;
}

instead of:

f"""
.card {{
    display: flex;
}}
"""
