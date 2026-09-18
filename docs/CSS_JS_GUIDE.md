# GSI CSS and JavaScript guide

This is the short version of the browser layer. It explains the pieces that
feel scattered when you first open a stylesheet or script.

## The browser layer in one sentence

HTML gives an element a name, JavaScript changes state, and CSS decides what
that state looks like.

```text
template/index.html
        ↓ gives buttons and cards stable class/data names
web/scripts/home-state.js + home-layout.js + home-format.js + home-filters.js
        ↓ describe state and one interaction responsibility each
web/scripts/home-page.js
        ↓ wires the modules and starts them in the right order
web/styles/home/*.css
        ↓ matches those names and changes layout, color, and motion
```

The builder joins the four homepage style parts into the single generated file
`site/styles/gsi-home.css`. The browser-facing URL stays stable while the
source is easier to read.

## One complete example: changing the layout

The layout control is in `templates/index.html`. Each button has a
`data-view` value such as `poster`, `wall`, or `gallery`. The value is the
small label shared by the script and the stylesheet; changing only the visible
word would not change the layout.

`web/scripts/home-layout.js` listens for a click on `.view-btn`. Its
`applyView()` function does four simple things:

1. Rejects a value it does not know and falls back to `wall`.
2. Stores the value on `<body data-view="…">`.
3. Gives the matching button its active state and accessibility state.
4. Keeps the same choice in the URL so a copied link opens the same view.

The assembled homepage stylesheet then uses selectors such as
`body[data-view="gallery"] .grid`. That means the stylesheet is not deciding
which view is active; it is only describing what each active value should look
like.

## The format control follows the same pattern

The format buttons use `data-format-option="songs"` or `"albums"`. The format
module stores the choice as `<body data-format="…">`, and CSS uses that value
for the album grouping rules. The disabled Artists button is intentionally present so
the control has a stable three-part shape before artist-format data exists.

## What the shared script does

`web/scripts/gsi-context.js` is a small library used by several pages. It does
not draw anything. It only:

- reads the current query string;
- keeps valid layout names in one place;
- rebuilds links with filter/view/format context; and
- remembers the last layout when the browser allows local storage.

If a link suddenly loses its filter or view, start there before editing a page
script.

For homepage work specifically, use `home-page.js` as the map rather than the
place to put every new rule: layout belongs in `home-layout.js`, Albums
grouping belongs in `home-format.js`, filter-room copy and playlist behavior
belong in `home-filters.js`, and pure values belong in `home-state.js`.

## How to read a CSS file without getting lost

Start with the top comment, then look for these layers:

1. shared values in `gsi-tokens.css`;
2. the page's main container and large regions;
3. named states such as `.active`, `.hidden`, or `body[data-view=…]`;
4. responsive blocks beginning with `@media`;
5. reduced-motion rules near the end.

The selector on the left says *which element*. The declarations inside the
braces say *what changes*. A later, more specific selector can override an
earlier one, which is why `web/styles/home/04-cards-and-responsive.css`
contains the narrowest mobile fixes.

## Safe browser-layer edits

- Change a label in the template when the wording is wrong.
- Change a state transition in the page script when the URL or active class is
  wrong.
- Change spacing, color, type, or responsive geometry in the owning stylesheet.
- Keep generated `site/` files out of the edit; rebuild instead.
- Prefer adding one clearly named selector over changing a broad `div` rule.
- After a CSS or JavaScript edit, run the build and inspect one desktop and one
  narrow route.

## A practical first exercise

To make the wall cards a little taller, find the `body[data-view="wall"] .card`
rule in `web/styles/home/04-cards-and-responsive.css` and change only its
height-related value.
Rebuild, open `index.html?view=wall`, then compare `poster` and `gallery` so you
can see that the other states stayed separate. This is a safe style-only
change because it does not alter the catalogue or route rules.
