# Astra UI and expressive-direction brief

## Role

You are reviewing GSI as a senior interaction designer and art director.
This document is a place for recommendations only. Do not edit source files,
generate code, or change data.

## Questions to answer

- How can GSI become more expressive without adding clutter, arbitrary effects,
  or generic music-site conventions?
- Which page compositions deserve attention first: home/filter rooms, song
  entries, album rooms, artist rooms, and Radio P53?
- Which hierarchy, typography, color, artwork, motion, and empty-space decisions
  are currently strongest, and which are visually inconsistent?
- How should the future private submission page communicate link, comments,
  optional username, and curation status in GSI's language?
- Which ideas need real Pixel/tablet testing before implementation?

## Constraints

- Treat animation as a deliberate spatial cue, not decoration.
- Do not invent labels, statuses, counts, or chronology that the data cannot
  support.
- Keep mobile behavior intentional and touch-first; hover is supplementary.
- Preserve existing artwork and personal wording unless a rewrite is explicitly
  requested.
- Distinguish a visual experiment from a durable component pattern.

## Repository and visual evidence

Reviewed 17 September 2026. Recommendations only; none of the page changes below
has been implemented or approved by this brief.

Read `PROJECT_STATE.md`, `DESIGN_BACKLOG.md`, the current roadmap/audit/navigation
contract, `config.json`, `build.py`, `web/styles/gsi-tokens.css`, the ordered
`web/styles/home/` parts, and both
P53 stylesheets, and the shared/page browser helpers. Inspected existing generated
home, song and P53 markup and the artist/catalogue manifests. Compared populated
`metric-empty.md` with template-only `michael-jackson-thriller.md` so the advice
does not presume every signal has a review.

This is a source-and-generated-markup audit, not a new visual screenshot or
usability test. Layout judgments below are hypotheses supported by specific CSS
and composition choices; actual clipping, visual balance, contrast, smoothness,
and touch behavior require rendering. Previous documented headless sweeps at
390/768/1440px and across generated pages are useful baseline evidence, not a
fresh device certification. No stock imagery, generated artwork, font download,
or external design reference was added.

### What is already worth protecting

- The home/filter room distinction, whole-album rule, three layout choices, and
  contextual return paths already exist. They are not future features to redesign
  from first principles.
- Artwork-driven color and manual accents let `ASTROWORLD`, `Live It Out`, and
  `Pocket Park` keep distinct atmospheres. The local artist-image contract makes
  absence legitimate instead of forcing stock portraits.
- P53 now uses a continuous native-scroll field with a larger current selection
  and compact past selections. Its current-card grid/radial field is decorative,
  not a reason to restore the removed watermark/status vocabulary.
- Empty entry sections are omitted; help controls work by click; the horizontal
  section index appears only with at least three populated sections. These are
  strong content-dependent choices.
- The shared token file establishes display, operational, and reading type roles
  and a common asymmetric geometry. The next step is selective adoption, not a
  different visual system.

## Recommendations

M denotes a mechanical/interaction improvement that can be proposed with high
confidence. D denotes an authorial or visual decision requiring approval. Each
should be a named small patch, not a combined redesign.

### 1. Set an expressive hierarchy before adding any new effects — D

**Intent.** GSI should feel like a personal archive with an authored interface,
not a dashboard wearing album covers. Keep the archive wall/signal room loud;
let song pages become intimate; give P53 a broadcast identity without turning
all rooms magenta/cyan.

**Direction.** Use three layers: protected matter (artwork and prose), apparatus
(navigation, controls, metadata), and brief interference (state-change motion).
Choose one dominant identity element per composition. On home that can be GSI
and its room field; on an entry, the album cover and song; in P53, the transmission.
Marathon's disciplined spacing and hierarchy, tactile expressive controls, and
occasional MW2005-like damage are existing conceptual influences, not permission
to copy assets or stack all three treatments on every component.

**Affected source/shape.** Start with token usage and one representative surface
in the relevant `web/styles/home/` part; only propagate a pattern after approval. A quiet background
plus one cut corner/accent line can carry identity without border, glow, grid,
shadow, and motion all competing at the same level. Do not mechanically flatten
the existing aesthetic.

**Risk and success.** Over-standardization can erase the rooms. Compare no-filter
home, Dreamy, Bite, an entry, and P53 together: each should have a clear first
read and recognizably belong to GSI. Success is less competition, not more empty
space or fewer colors by rule.

### 2. Clarify home controls, room counts, and empty Albums results — M/D

**Observed.** The home hero already pairs GSI with a P53 doorway; filter selection
replaces the introduction with room material. The playlist now occupies the
Layout/Format rail rather than the historical large adjacent card. Artists is
disabled. Album summaries appear only for qualifying albums; a filter can show
no album results even while its room count reports matching songs.

**Intent and shape.** Preserve the existing reading order: identity → active room
→ layout/format and optional outbound playlist → archive results. Make controls
look pressable and selected through shape/contrast plus `aria-pressed`, not color
alone. Treat the room's signal count as its song count, not the number of visible
album cards. When Albums has no qualifying result, give a short truthful empty
state and a direct return to Songs; wording needs Ulaş's approval. Do not invent
an album review, fabricate a count, or fill the gap with unrelated music.

**Specific contract mismatch.** `build_index_html()` emits configured
`playlist_cta`, but `setFilter()` replaces it with a hard-coded Apple Music line.
All current playlist URLs are Apple links, but the user's configured wording
is still being ignored. Recommend restoring configuration ownership, with a
separate outbound cue. If art exists without a destination, render it as art,
not an `href="#"` control claiming to be unavailable. Do not rewrite the copy
as part of a layout patch.

**Touchpoints/dependencies.** `build_index_html()`, `web/scripts/home-page.js`, and
the relevant `web/styles/home/` part; retain the structural brief's catalogue contract. Removing or
enabling the disabled Artists choice is a separate design decision. It must not
gain a public “coming soon” promise by inference.

**Responsive/accessibility success.** At 360–430px and tablet widths, controls
remain readable without shrinking labels to solve containment. Selected state,
an outbound playlist, and a metadata label must not be confused. Test no playlist
art (Personal), art plus a long description (Dreamy), zero qualifying Albums, and
rapid room switching. Make a result change available to assistive technology
without announcing the entire card grid.

### 3. Give P53 the next bounded composition review — D with M safeguards

**Observed.** The landing description is already anchored, and current/past
labels are already real. Permanent transmissions use a large protein panel,
song panel, optional notes, and WHY P53? text. At mobile widths, the protein panel
is placed before the song panel with a 360px minimum height; on desktop the
composition has a 650px minimum. These choices can postpone recognition of the
shared song, but that needs a real-device check. A selected historical card's
scroll highlight is visual focus, not keyboard focus or “current” status.

**Intent and shape.** Let a first-time Instagram arrival identify the song and
reach a listening link without interpreting the entire project. Trial one
mobile composition that brings song identity into the first viewport while
retaining authored protein art as a contextual field. Do not simply delete art
or squeeze everything into a generic playlist row. On the landing page retain
the larger current selection and compact past list; tune title/description
alignment and rhythm only after viewing the existing baseline.

Keep transmission notes editorially more immediate than repeat explanatory
copy; an absent note needs no placeholder. Review whether the repeated
CURRENT/PAST text in both path and signal-panel decoration adds useful context.
Keep at least one semantic status, not only generated CSS text. The configured
sequence supports current/past and order, not invented dates or week numbers.

**Actions and dependencies.** The landing currently has transmission links but
no dedicated playlist action. Decide whether one modest outbound playlist link
belongs there, using the existing P53 config; do not add a new control merely to
complete a conventional header. `SHARE` currently shares the browser location,
which may be `latest.html` and may include context. An explicit product decision
should choose the permanent transmission URL for enduring shares; “latest” is a
moving destination. Provide perceivable success/failure feedback without stealing
focus. This depends on the structural brief's identity/route checks.

**Touchpoints.** `build_p53_archive()`, `build_p53_page()`, P53 CSS and browser
helpers. No carousel, wheel interception, scroll lock, extra technical markings,
or fabricated chronology.

**Success.** Test current and past transmissions, longest titles, absent notes,
native share cancellation, unavailable clipboard, and an in-app mobile browser.
The song is quickly identifiable; art remains deliberate; ordinary scrolling,
keyboard focus, and return context remain intact.

### 4. Finish the song-page reading contract before new navigation — M/D

**Observed.** The final inline styles use a large cover/metadata hero and a
two-column section grid, collapsing on mobile. Uneven sections deliberately
share row height. The index is a small non-sticky strip, not the old sidebar idea.
The generator already suppresses empty headings and explanatory prompts.

**Intent and shape.** A full entry should reward reading; a metadata-only signal
should remain a valid quiet archive object. Preserve `Charge`, `Sonical Attraction`,
`Lyric/Vocal Detail`, `Version of ulaş`, `Lore`, `Reading`, and `Comment` exactly.
Do not add completion meters, “review coming soon,” or a field guide that repeats
the section help. Keep help available by tap and keyboard.

Trial reading measure and card density using Empty's short Charge and long
Comment together. A useful experiment is roughly 55–75 characters per prose
line, not a mandatory redesign. If empty area dominates a row, test a controlled
single-column long-reading variant separately; do not restore overlapping or
staggered card geometry. Noninteractive prose cards need not morph their corners
on hover: reserve tactile shape changes for actions.

Artist and album links currently look like plain metadata until hover/focus.
Use a restrained persistent link cue where a room exists; do not turn metadata
into pills. The ALSO APPEARS IN area repeats some hero links; keep it only where
it helps onward reading, and do not add another back button alongside the trace.
Provider links should consistently look outbound. Search fallbacks are already
identified in accessible labels/metadata; decide a compact visible indication
without making the page noisy or pretending every click opens the exact song.

**Touchpoints/dependencies.** `build_entry_page()` styles/markup and
`web/scripts/entry-page.js`; shared provider markup for cross-page consistency. Keep a
pure CSS extraction separate from any reading-layout change. Persistent metadata
link cues are a high-confidence affordance improvement; column layout is a
design experiment.

**Success.** Read Empty end-to-end at desktop/tablet/phone and increased text
size; compare Thriller with no written sections. The section strip exposes only
real text, scrolls discoverably when needed, and its targets are not obscured.
Help changes height without overlap; links remain identifiable without hover;
prose never looks like a disabled control.

### 5. Make album and artist rooms truthful, distinct destinations — M/D

**Album intent.** An album room gathers represented signals; it is not a complete
track list or an automatic album review. Keep cover, exact title, artist, optional
author note, and represented-song destinations. The whole-album rule remains
intact even when one song matched the originating filter. `Bloom` should make
entry versus P53 destinations clear; its current generic OPEN treatment lacks
the explicit transmission distinction available in artist rooms. Never invent
“why in Dreamy” copy.

**Artist intent.** Artist rooms should express Ulaş's relationship with an artist
only where he has supplied it. Metric's image/name/note field is a valid authored
case, not a template demanding portraits and biographies for everyone. Compare
image-free rooms with it before enabling Artists format. A portrait is identity,
not a playback button. Allow intentional image composition; no automatic
portrait generation, scraping, or arbitrary cropping.

**Typography/data boundary.** Album headings preserve casing, but the current
album breadcrumb uses `album.upper()`. That conflicts with the source wording
constraint. A future mechanical fix should preserve the exact album string in
that path too; do not “correct” `Live It Out`, `ASTROWORLD`, or edition names.
Operational labels can retain their existing uppercase convention without
rewriting titles.

**Touchpoints/dependencies.** `build_album_pages()`, `build_artist_pages()`,
`gsi_artists.py`, related browser helpers; consult the relationship inventory
before adding links. Decide any album-level art/accent override explicitly,
because the current first-song fallback can change when ordering changes.

**Success.** Test both current album rooms, Metric, Emily Haines & The Soft
Skeleton, and Beach House at phone/tablet widths. Long artist names and notes
must not crowd navigation. Counts mean represented signals; destinations reveal
what kind of page opens; no-art rooms feel intentional, not incomplete.

### 6. Stabilize typography and image treatment across real devices — M/D

**Observed.** The token file names three type roles, but many rules still repeat
Impact/Arial stacks directly; mobile home rules introduce Roboto and synthetic
weight/stroke adjustments. Several display lines use very tight line heights.
Consequently a Pixel may not have the same letterforms or wrapping as desktop.
This is a risk to measure, not a diagnosis that a particular device is broken.

**Direction and shape.** First use the existing font-role tokens consistently in
one surface without changing faces. Then compare long titles, punctuation,
Turkish characters, and small operational labels on actual devices. If a
self-hosted display face is justified, choose it with Ulaş and check rights,
weight, glyph coverage, and transfer cost; no font recommendation is settled by
this brief. Body reading should stay calm, with no distress or tracking effects.

Keep album art as intact source matter; distinguish an intentional poster crop
from the default square cover. P53 list and portrait-style cards use `object-fit:
cover`, so examine whether important source composition is lost. Add intrinsic
image dimensions and measured loading priorities where missing before adding
more images. Lazy-load below-fold art, not the principal entry artwork. Keep a
quiet missing-art state without claiming a nonexistent asset.

**Touchpoints/dependencies.** Shared tokens, page CSS, and image emitters in
`build.py`/`gsi_artists.py`. Artist images already include dimensions; extend that
good pattern where useful. Review file sizes before setting an asset budget.

**Success.** No shifted/truncated title at 200% text scaling, no missing glyphs,
no artificial title-case conversions, and no perceptible layout jump when art
arrives. Verify actual contrast with pale Dreamy, yellow Bite, neutral manual
accents, and bright P53 colors rather than assuming glow guarantees legibility.

### 7. Give motion a purpose and a stopping condition — M safeguards, D restraint

**Observed.** Home already uses a short signal transition and a grid fade instead
of moving every card. It also has ongoing Bassline/Dreamy/POP/Distortion effects;
P53 has a repeating protein-label pulse. Reduced-motion rules are present, but
some pages reduce durations without explicitly stopping infinite iteration.
Album-room CSS has no matching general reduced-motion treatment in its current
inline stylesheet.

**Direction.** Preserve one brief cue when a room or layout changes; do not chain
it to a full-screen blur, mass-card animation, or a delayed interaction. Repeated
selection must cancel the old cue and settle in the latest chosen state. On
reduced motion, render the complete stable composition immediately, with ambient
animations off rather than merely accelerated. Investigate pausing ambient work
offscreen/in inactive tabs only if it is retained after design review.

Decide which room effects genuinely carry character. A bounded static field or
single entrance can be expressive; constant distortion over playlist artwork
conflicts with protected art. Keep decoration outside reading and control text.

**Touchpoints/dependencies.** `web/scripts/home-page.js`, home/P53 CSS, and embedded
album/entry styles. Test state cancellation independently of aesthetic changes.
Do not introduce a new motion-toggle UI unless device evidence and retained
animation actually warrant it.

**Success.** Rapidly switch filters, layouts, and Songs/Albums; resize mid-change;
enable reduced motion; background and restore the tab. No stale hidden content,
wrong pressed state, flashing, focus movement, or trapped scroll. P53's visual
scroll emphasis must not impersonate keyboard focus or current-transmission state.

### 8. Design the future submission page as a private handoff — D, later

**Intent.** A person is suggesting something to Ulaş, not contributing directly
to a public review platform. Reuse a quiet reading/form composition with one
small GSI identity cue; a high-energy filter-room treatment would compete with
typing and the privacy explanation.

**Proposed hierarchy, not approved copy.** Brief purpose/privacy statement;
music-link field; comment field; explicitly optional username; one send action;
then a durable inline outcome. Explain that suggestions remain private and that
inclusion is curated. Do not call it anonymous if the eventual service logs
identifying information. No username directory, sign-up, public queue, fabricated
“under review” status, promise of replies, or publication deadline.

**Interaction shape.** Use visible labels, paste-friendly link input, generous
multiline comments, and an optional field that looks optional before submission.
Keep entered text on recoverable failure; associate errors with the affected
field; preserve keyboard focus; prevent duplicate sends without leaving a stuck
button. The success message must describe what the actual intake confirms, not
pretend that mail delivery or editorial acceptance has occurred. With no email
field, do not offer emailed status updates. Any public credit needs a separate
consent decision; a username is not automatic permission to publish it.

**Dependencies/risks.** No implementation until the structural brief's private
intake, storage/mail failure, retention, and access choices are approved. Agree
what “private” means before writing the interface text. No embedded credentials
or visitor comments in generated manifests. Do not design a status dashboard
ahead of a real workflow.

**Success.** On a Pixel with its keyboard open, a visitor can paste a link,
understand optionality/privacy, correct an error, submit once, and distinguish
receipt from acceptance. Test slow/offline requests, rejected links, duplicate
clicks, and a receiver failure. No task ends with a decorative success animation
standing in for actual receipt.

### 9. Use a compact release matrix, not another generalized redesign — M

Before approving durable visual patterns, check the following against the
current baseline and the intended changed surface only:

| Surface/state | Important evidence |
| --- | --- |
| Home: no filter; Personal; Dreamy; Bite; POP/Distortion | Control containment, selected state, art/no-art playlist, motion, real counts |
| Albums: eligible and zero-result filter; all three layouts | Whole-album count meaning, sparse-state clarity, consistent return context |
| Empty and Thriller | Long prose versus no prose; actual section-strip eligibility; help expansion |
| Live It Out and Bloom | Exact casing, represented-song scope, entry/P53 destination distinction |
| Metric and image-free/P53-only artist rooms | Long names, portrait/no-portrait balance, truthful counts and notes |
| P53 landing/current/past/absent note | Native scroll, first-viewport identity, sharing and status semantics |

Start at 390, 768, and 1440 CSS pixels to compare with prior evidence, then add
360/430px phones, tablet portrait/landscape, and widths just either side of the
680/700/760/820/850px breakpoints that different surfaces currently use. Verify
on an actual Pixel and tablet before claiming mobile completion. Use keyboard,
screen-reader spot checks, 200% text size, reduced motion, slow artwork loading,
and blocked storage. Check clipped descendants and focus rings, not merely
document width: `overflow-x:hidden` can conceal defects.

Approval sequence: first validate current orientation and P53 mobile priorities;
then trial one visual change; then compare the matrix; only then adopt a shared
pattern. A screenshot of one attractive state is not a component contract.

## Explicit non-goals

- No redesign, implementation, generated-site modification, artwork replacement,
  font installation, commit, push, or deployment in this audit.
- No global neon/grunge skin, literal Marathon/MW2005 copy, Metric-specific site
  identity, or decorative technical language without factual meaning.
- No restored P53 carousel, forced scrolling, autoplay music, hover-only access,
  full-screen transitions, or new motion system before device evidence.
- No ratings, popularity badges, invented chronology, completion scores,
  biographies, “coming soon” promises, or auto-written interpretation.
- No Artists format rollout before its composition and image-free states are
  reviewed; no removal of the existing disabled control without a design decision.
- No generic search/account/recommendation features, submission feed, status
  dashboard, extra field-guide layer, or habitual extra navigation.
- No broad CSS cleanup mixed with an art-direction experiment; preserve baseline
  output during extraction and judge visual changes separately.
