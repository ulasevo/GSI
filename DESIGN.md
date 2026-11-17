# Chaperone Design & Motion Guidelines

Derived from the project's creative direction, Emil Kowalski's design engineering philosophy (`.agents/skills/emil-design-eng`), and Anthropic's frontend design principles (`.agents/skills/frontend-design-SKILL.md`).

---

## Surfaces
- **Ambient over hard offsets**: Never use hard unblurred offset shadows (`X Y 0 color`) on cards with large or asymmetric border-radii. Use soft, diffused glows (`box-shadow: 0 20px 54px rgba(0,0,0,.36), 0 0 28px color-mix(...)`) to prevent polygonal bleeding at corners.
- **Stable silhouettes**: Never invert or morph `border-radius` on hover across collections (e.g. `24px 8px` to `8px 24px`). Animating border-radius forces continuous GPU rasterization repaints. Use stable contours and elevate with compositor-only properties (`transform` and `box-shadow`).
- **Nested radius discipline**: When placing a button or badge inside a curved container corner, follow the nested radius formula: $R_{\text{inner}} \approx R_{\text{outer}} - \text{padding}$.
- **Materials**: Translucent bars and docks use `backdrop-filter: blur(14px)` with an inset hairline highlight (`inset 0 1px 0 rgba(255, 255, 255, 0.08)`). Never stack translucent layers directly on top of each other.

---

## Color
- **Core palette**:
  - Dark ink: `#0d0d0f`, `#101014`
  - High-contrast text: `#f5f2ec`, `#f8f5ef`
  - Signal accents: Radio pink (`#ff65ad`, `#ff72b5`), Cyan highlight (`#35c9e9`, `#22bce3`)
  - Subdued chrome: `rgba(255, 255, 255, 0.62)` for secondary labels, `rgba(255, 255, 255, 0.12)` for hairlines.
- **Dynamic cover atmosphere**: Page accents and glow tints inherit from album artwork roles (`--art-primary`, `--art-secondary`, `--page-tint`).
- **Restraint**: Never slap neon dots or glow effects everywhere. Reserve vibrant color for active states, playback signals, and filter highlights.

---

## Typography
- **Families**: Space Grotesk for display and UI controls; clear sans-serif for body reading.
- **Tracking by size**:
  - Large headings ($\ge 28\text{px}$): negative tracking (`letter-spacing: -0.03em` to `-0.04em`).
  - Small uppercase badges and labels ($\le 12\text{px}$): positive tracking (`letter-spacing: 0.08em` to `0.12em`).
  - Body text: neutral tracking (`0`) with comfortable leading (`1.5` to `1.6`).
- **Authenticity**: Avoid template chrome such as unnecessary all-caps eyebrows above every paragraph or unstyled monospaced numbers.

---

## Spacing & Layout
- **Dock controls**: The dock (`.layout-format-controls`) is an edge-to-edge instrument dock with backdrop blur. Buttons share uniform proportions.
- **Filter strip**: Uniform 8-box grid (`4×2` on desktop, `2×4` on mobile) with clear signposting (`"Filter to begin:"` and `"Selection"`).
- **Responsive grids**:
  - Desktop: 6-up (`wall`), 4-up (`poster`).
  - Mobile: 3-up (`wall`), 2-up (`poster`).

---

## Motion
- **Performance**: Animate only compositor-friendly properties (`transform` and `opacity`). Never animate `padding`, `margin`, `height`, `width`, or `grid-template-rows`.
- **Duration**: Keep UI interactions under $300\text{ms}$ ($150\text{ms}$–$220\text{ms}$ ideal). Exits should be snappier than entrances.
- **Custom easing curves**:
  - Strong UI interactions: `--ease-out: cubic-bezier(0.23, 1, 0.32, 1);`
  - Smooth on-screen repositioning: `--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);`
  - Sheets and drawers: `--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);`
  - Never use weak default `ease-in` for interactive UI elements.
- **Reduced motion**: Respect `prefers-reduced-motion: reduce` by replacing spatial translates with subtle opacity cross-fades.

---

## Interaction
- **Instant feedback on press**: All pressable elements (filter pills, dock buttons, cards, floating path links) must include:
  ```css
  :active {
    transform: scale(0.97);
    transition: transform 80ms ease-out;
  }
  ```
- **Mobile hover protection**: Always gate hover transformations behind `@media (hover: hover) and (pointer: fine)` so mobile taps do not leave stuck hover highlights on phones.
- **Floating path**: The left-aligned breadcrumb pill (`nav.floating-path`) stays fixed and tactile, omitting the current page title and displaying only ascending parent paths.

---

## Copy
- **Active voice & clarity**: Action names describe what happens simply and clearly (`Selection`, `Share`, `Filter to begin:`).
- **Preserve project identity**: Keep Chaperone's personal language, section headers, and archive terms without homogenizing them into generic review jargon.
