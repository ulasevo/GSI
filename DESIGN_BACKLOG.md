# GSI Design Backlog

This is a discussion backlog, not an implementation plan. GSI v1.15 remains the protected baseline.

## Visual direction to explore

- Treat GSI as a personal signal-processing archive: preserved album art and writing, a clear interface apparatus, and brief interference while state changes.
- Borrow from Marathon's hierarchy, intentional negative space, restrained purposeful color, labels and graphic systems. Do not copy its marks, layouts, type treatments, or assets.
- Keep Material 3 Expressive for tactile, legible controls and responsive shape changes.
- Use MW2005 as intermittent grit, registration error, speed and damage; never let distortion interfere with reading.
- Define three type registers: display type for identity, compact operational type for controls/counts, and quiet reading type for prose.

## Highest-value UX work to consider

1. Preserve archive context: carry active filter and chosen view through an entry and back to the homepage.
2. Give filter transitions one reliable lifecycle so repeated clicks cannot leave stale animation state.
3. Simplify filter rooms to count, title, description, playlist artwork and playlist action; remove `START HERE` and mini cover fragments.
4. Make Radio P53 two clear actions: open the active transmission and open the playlist.
5. Align entry hero and writing sections to one shared grid and shape system.
6. Restore shared `main`/`nav` containment on the P53 landing page; its fallback styling produces a left-edge path bar and an incoherent landing hierarchy.

## Interaction rules

- Album artwork and prose are protected archive matter.
- Controls need clear focus, pressed and active states; reduced-motion must remain complete.
- Use distortion at transitions and state changes, not as a permanent reading effect.
- Prefer small background/decorative motion over full-screen blur or mass card animation.
- Mobile layouts should recompose intentionally rather than shrink desktop arrangements.

## Explorations worth discussing later

- An explicit `ALL SIGNALS` control and visible per-filter counts.
- A persistent, shareable URL for a selected filter/view.
- A compact entry index only for entries with enough written sections to warrant it.
- A `signal receipt` on entry pages: track, album, archive date/order and filter lineage, with no invented personal metadata.
- A lightweight discovery mode that chooses one archived signal without gamifying the writing.
- A more navigable P53 archive: past transmissions grouped as an editorial timeline, not a generic playlist grid.
- Intentional missing-art and offline states that look authored rather than broken.
