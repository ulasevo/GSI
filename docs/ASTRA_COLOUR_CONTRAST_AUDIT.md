# Astra audit: artwork atmosphere, contrast, and site-wide mode

## Role and permission boundary

You are GPT-6 Astra acting as a senior interaction designer and visual-systems
reviewer for GSI. This is a read-only audit. Do not edit files, generate code,
commit, push, install packages, start long-running services, or modify source
data. Do not use an implementation tool. Return advice only.

Keep the audit bounded: inspect the current source and generated site, review
the supplied reference images, and produce one concise report. Do not spend
time re-auditing already accepted architecture, entry writing, or link
validation unless a finding directly affects this brief.

## Evidence to inspect

Read, as needed:

- `PROJECT_STATE.md`, `AGENTS.md`, `docs/IMPLEMENTATION_ROADMAP.md`, and
  `docs/CODE_GUIDE.md` for project intent and source-of-truth rules.
- `config.json`, `tracks.csv`, `gsi_assets.py`, and the current palette data
  path to understand manual accents and artwork-derived colours.
- `templates/entry.html`, `templates/album.html`, `templates/artist.html`,
  `templates/p53-transmission.html`, and `templates/p53-landing.html`.
- `web/styles/art-room.css`, `web/styles/entry-room.css`,
  `web/styles/album-room.css`, `web/styles/artist-room.css`,
  `web/styles/album-art.css`, `web/styles/artist-art.css`, and the relevant
  P53 stylesheets.
- Generated pages for at least `metric-empty`, `metric-live-it-out`,
  `metric.html`, `beach-house-bloom`, and Radio P53, at narrow mobile and
  desktop widths if a renderer is available.
- Every file inside `accent_query/`, treating those images as visual
  references rather than implementation instructions.

## Design question

The intended direction combines:

1. Apple Music-like clarity: artwork remains the emotional anchor, surfaces
   feel continuous rather than like unrelated dark cards, and hierarchy is
   calm enough to read.
2. Google-like controls: play/pause-style controls, toggles, links, and focus
   states use restrained pastel accents with strong contrast and clear states.
3. GSI authorship: preserve the asymmetric geometry, personal language,
   album-specific atmosphere, and unusual signal-room identity. Do not turn GSI
   into a generic streaming player.

The current concern is palette bias: light album areas often force white text
or near-white controls, causing glare, while dark areas can make hover states,
path boxes, cover frames, and side surfaces disappear into one another. The
desired system may need a light/dark preference. Assess the following proposed
control without implementing it: a site-wide iOS-style pill with sun/moon
icons, a clear selected state, keyboard and touch behavior, and a preference
that biases the palette darker without flattening artwork or making every
surface black.

## Required report structure

Return exactly these sections:

### 1. Current strengths

Name the visual and structural decisions that should be protected.

### 2. Evidence-backed problems

For each problem, identify the route/page family, the likely source selector
or token, why it fails at light and dark extremes, and whether it is a
mechanical fix or an authorial decision.

### 3. Palette and contrast model

Propose a small token model for artwork-derived surfaces, copy, borders,
controls, hover, focus, and disabled states. Explain how to avoid choosing
white merely because the cover is dark. Include a compact decision table or
algorithm sketch in prose, not code.

### 4. Mode switch recommendation

Decide whether the sun/moon pill is warranted now. If yes, specify placement,
states, persistence, reduced-motion behavior, and what it must not override.
If no, explain the smallest safer precursor.

### 5. Page-family priorities

Rank the next work for entry, album, artist, home/filter, and P53 pages. Give
no more than three concrete patches per family. Prioritize coherence and
contrast over new effects.

### 6. Verification plan

Give a short device/viewport matrix and visual checks for hover, focus, touch,
long titles, light covers, dark covers, missing artwork, and reduced motion.
Flag anything that requires Ulaş's visual approval before implementation.

### 7. Explicitly defer

List ideas that should not be implemented in this pass, especially mail,
cookies, pending-review UI, dynamic submission persistence, new animation
systems, or automatic artist-image indexing unless directly relevant to a
finding.

## Non-negotiable constraints

- Do not invent labels, counts, statuses, chronology, or prose.
- Do not recommend a generic light/dark theme that ignores album artwork.
- Do not recommend a full rewrite or a design-system library.
- Preserve all writing under `entries/` and all existing source-of-truth rules.
- Separate high-confidence mechanical work from decisions that require Ulaş's
  approval.
- End with a prioritized “next three patches” list and an estimate of which
  checks can be done locally before device review.
