const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../web/scripts/p53-transmission.js"), "utf8");

function hexLuminance(hex) {
  const m = String(hex || "").match(/^#([0-9a-f]{6})$/i);
  if (!m) return null;
  const channels = [0, 2, 4].map(i => {
    const c = parseInt(m[1].slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

async function render({ track, artistName = "Matt Maeson", album = "A Quiet And Harmless Living", signalLabel = "ACTIVE", note, trackPalette, routeQuery = "" } = {}) {
  const painted = [];
  const drawnImages = [];
  const gradientStops = [];
  const fills = [];
  const listeners = {};
  let currentFont = "";
  let currentFillStyle = "";

  const context2d = {
    get font() { return currentFont; },
    set font(v) { currentFont = v; },
    get fillStyle() { return currentFillStyle; },
    set fillStyle(v) {
      currentFillStyle = v;
      if (typeof v === "string") fills.push(v);
    },
    clearRect() {},
    fillRect() {},
    drawImage(img, ...args) { drawnImages.push({ img, args }); },
    save() {},
    restore() {},
    clip() {},
    beginPath() {},
    moveTo() {},
    lineTo() {},
    arcTo() {},
    closePath() {},
    roundRect() {},
    fill() {},
    stroke() {},
    createLinearGradient: () => ({
      addColorStop(_, color) { gradientStops.push(color); },
    }),
    createRadialGradient: () => ({
      addColorStop(_, color) { gradientStops.push(color); },
    }),
    measureText: (text) => ({ width: Array.from(text).length * 30 }),
    fillText: (text, x, y) => painted.push({ text, x, y, font: currentFont, fillStyle: currentFillStyle }),
  };

  function makeClassList(initial = []) {
    const set = new Set(initial);
    return {
      add: (c) => set.add(c),
      remove: (c) => set.delete(c),
      contains: (c) => set.has(c),
    };
  }

  const proteinImage = { kind: "protein", complete: true, naturalWidth: 1000, naturalHeight: 1000 };
  const albumImage = { kind: "album", complete: true, naturalWidth: 600, naturalHeight: 600 };
  const canvas = { getContext: () => context2d, setAttribute() {} };
  const share = { addEventListener: (_, callback) => { listeners.open = callback; } };
  const modal = { showModal() {}, addEventListener() {} };
  const shareBtn = { disabled: true, addEventListener() {} };
  const downloadBtn = { disabled: true, addEventListener() {} };
  const status = { textContent: "" };
  const archiveMarkHtml = '<span class="gsi-home-mark" data-gsi-mark="favicon-slot"><span class="gsi-home-mark-icon" aria-hidden="true"></span><span class="gsi-home-mark-text">GSI</span></span>';
  const traceArchive = { href: "../index.html", innerHTML: archiveMarkHtml };
  const radioIndex = { href: "index.html" };
  const traceFilter = { href: "../index.html", textContent: "", classList: makeClassList(["hidden"]) };
  const traceFilterSep = { classList: makeClassList(["trace-separator", "hidden"]) };
  const traceArtist = { href: "../index.html", textContent: "", classList: makeClassList(["hidden"]) };
  const traceArtistSep = { classList: makeClassList(["trace-separator", "hidden"]) };
  const entryCounterpart = { href: "../entries/private-test-slug.html" };
  const albumLink = { href: "../albums/matt-maeson-a-quiet-and-harmless-living.html" };
  const artistLink = { href: "../artists/matt-maeson.html" };

  const context = {
    filterLabels: { bassline: "Bassline", p53: "P53" },
    expectedArtistRoute: "matt-maeson",
    accent: "#b84093",
    track,
    artistName,
    album,
    slug: "private-test-slug",
    signalLabel,
    transmissionNote: note,
    coverSrc: "../covers/album.jpg",
    p53CoverSrc: "../covers/P53_cover-runtime.webp",
    p53Accent: "#b84093",
    cyanAccent: "#35c9e9",
  };
  if (trackPalette) context.trackPalette = trackPalette;

  const lookup = {
    "#p53-transmission-context": { textContent: JSON.stringify(context) },
    "#p53-trace-archive": traceArchive,
    "#p53-radio-index": radioIndex,
    "#p53-trace-filter": traceFilter,
    "#p53-trace-filter-separator": traceFilterSep,
    "#p53-trace-artist": traceArtist,
    "#p53-trace-artist-separator": traceArtistSep,
    "#share-transmission": share,
    "#story-modal": modal,
    "#story-btn-share": shareBtn,
    "#story-btn-download": downloadBtn,
    "#story-status": status,
    "#story-card-canvas": canvas,
    ".protein-panel img": proteinImage,
    ".signal-cover": albumImage,
  };
  const lookupAll = {
    "#p53-trace-archive": [traceArchive],
    ".artist-link": [artistLink],
    ".entry-counterpart, .album-link": [entryCounterpart, albumLink],
  };
  const bodyProps = [];
  const document = {
    querySelector: (selector) => lookup[selector] || (selector.includes("album.jpg") ? albumImage : null),
    querySelectorAll: (selector) => lookupAll[selector] || [],
    body: { style: { setProperty: (name, value) => bodyProps.push([name, value]) } },
  };
  const parsedQuery = new URLSearchParams(routeQuery);
  const state = {
    read: () => parsedQuery,
    archiveParams: ({ state: s = parsedQuery, filterLabels = {} } = {}) => {
      const p = new URLSearchParams();
      const f = s.get("filter");
      if (f && Object.hasOwn(filterLabels, f)) p.set("filter", f);
      const t = s.get("theme");
      if (t) p.set("theme", t);
      return p;
    },
    href: (base, p) => `${base}${p.size ? `?${p}` : ""}`,
  };
  const window = { GSIContext: state };
  vm.runInNewContext(source, { document, window, GSIContext: state, URLSearchParams });
  await listeners.open();
  return {
    painted, drawnImages, gradientStops, fills, bodyProps, archiveMarkHtml, shareBtn, downloadBtn, status,
    proteinImage, albumImage, traceArchive, radioIndex, traceFilter, traceFilterSep,
    traceArtist, artistLink, entryCounterpart, albumLink,
  };
}

(async () => {
  const card = await render({
    track: "Stubborn As Religion",
    note: "such a strong vocal, this man",
    routeQuery: "filter=bassline&artist=matt-maeson&theme=dark",
    trackPalette: {
      primary: "#0287ac",
      secondary: "#053655",
      glow: "#036b8e",
      field: "#3aacc0",
      soft: "#5fb5c8",
      surface: "#0b2c3a",
      ink: "#f8f5ef",
    },
  });

  assert.equal(card.shareBtn.disabled, false);
  assert.equal(card.downloadBtn.disabled, false);
  assert.equal(card.status.textContent, "");

  // Factor breadcrumb keeps filter in return hrefs while omitting filter segment on bar
  assert.ok(card.traceArchive.href.includes("filter=bassline"), "GSI return link retains filter state");
  assert.equal(card.traceArchive.innerHTML, card.archiveMarkHtml, "GSI favicon-slot home mark markup is preserved during route hydration");
  assert.ok(card.bodyProps.some(([k, v]) => k === "--accent" && v === "#b84093"), "--accent CSS var is still set on body");
  assert.ok(!card.bodyProps.some(([k]) => k === "--signal-label"), "--signal-label watermark CSS var is no longer injected on body");
  assert.ok(card.radioIndex.href.includes("filter=bassline"), "RADIO P53 return link retains filter state");
  assert.ok(card.traceFilter.classList.contains("hidden"), "filter segment stays hidden on factor trace bar");
  assert.ok(card.traceFilterSep.classList.contains("hidden"), "filter separator stays hidden on factor trace bar");
  assert.ok(!card.traceArtist.classList.contains("hidden"), "artist trace link reveals when matching");
  assert.ok(card.artistLink.href.includes("filter=bassline") && card.artistLink.href.includes("theme=dark"), "artist link preserves active archiveParams");
  assert.ok(!card.artistLink.href.includes("artist="), "artist link avoids redundant artist param");
  assert.ok(card.entryCounterpart.href.includes("filter=bassline") && card.entryCounterpart.href.includes("artist=matt-maeson"), "entry companion card forwards route params");
  assert.ok(card.albumLink.href.includes("filter=bassline") && card.albumLink.href.includes("artist=matt-maeson"), "album link forwards route params");

  // Authentic GSI wording and absence of synthetic boilerplate
  assert.ok(card.painted.some(({ text }) => text === "Radio P53"));
  assert.ok(card.painted.some(({ text }) => text === "Active"));
  assert.ok(card.painted.some(({ text }) => text === "Matt Maeson"));
  const albumEntry = card.painted.find(({ text }) => text.includes("Quiet And Harmless"));
  assert.ok(albumEntry && card.painted.some(({ text }) => text.includes("Living")), "album original casing is preserved across wrapped lines");
  assert.ok(card.painted.some(({ text }) => text.includes("such a strong vocal")));
  assert.ok(
    !card.painted.some(({ text }) => /SIGNAL RECEIPT|STORY CARD|LISTEN TO TRANSMISSION|TAP TO LISTEN|PLACE INSTAGRAM|PRIVATE-TEST-SLUG/i.test(text)),
    "no synthetic receipt/button/slug copy inside card"
  );

  // Paper sleeve warm surface + P53 cyan/magenta edge accents + high-contrast dark ink on paper
  assert.ok(
    card.gradientStops.some(c => {
      const lum = hexLuminance(c);
      return lum !== null && lum > 0.65;
    }),
    "paper sleeve surface uses luminous warm archival paper stops"
  );
  assert.ok(card.fills.some(f => f.includes("53, 201, 233")), "P53 cyan edge accent is painted");
  assert.ok(card.fills.some(f => f.includes("184, 64, 147")), "P53 magenta edge accent is painted");

  const noteEntry = card.painted.find(({ text }) => text.includes("such a strong vocal"));
  assert.ok(noteEntry, "transmission note is painted");
  const noteSizeMatch = noteEntry.font.match(/(\d+)px/);
  assert.ok(noteSizeMatch && Number(noteSizeMatch[1]) >= 40, "transmission note uses enlarged legible typography");
  const noteLum = hexLuminance(noteEntry.fillStyle);
  assert.ok(noteLum !== null && noteLum < 0.15, "note uses dark high-contrast archival ink even when trackPalette.ink is light");

  // Paper sleeve geometry: Track/Artist/Album ABOVE cover; P53 protein in left spine strip; Note BELOW cover; open bottom breathing room
  const coverDraws = card.drawnImages.filter(d => d.img === card.albumImage);
  assert.equal(coverDraws.length, 1, "album cover is drawn once inside the sleeve window");
  const [, , , , coverDx, coverDy, coverDw, coverDh] = coverDraws[0].args;
  const trackEntry = card.painted.find(({ text }) => text.includes("Stubborn"));
  const artistEntry = card.painted.find(({ text }) => text === "Matt Maeson");
  assert.ok(trackEntry.y < coverDy, "track title is anchored above album cover");
  assert.ok(artistEntry.y < coverDy, "artist is anchored above album cover");
  assert.ok(albumEntry.y < coverDy, "album is anchored above album cover");
  assert.ok(noteEntry.y > coverDy + coverDh, "transmission note sits below album cover");

  const spineDraws = card.drawnImages.filter(d => d.img === card.proteinImage);
  assert.ok(spineDraws.length >= 2, "P53 artwork runs down the spine strip in specimen bands");
  for (const draw of spineDraws) {
    const [, , sw, sh, dx, , dw, dh] = draw.args;
    assert.ok(dw <= 180, "P53 protein artwork stays in a narrow edge spine strip, not blurred full-width");
    assert.ok(dx < coverDx, "P53 spine sits along the left edge beside the sleeve face");
    assert.ok(Math.abs((sw / sh) - (dw / dh)) < 0.05, "P53 spine slices preserve natural aspect ratio");
  }

  const footerEntries = card.painted.filter(({ text, y }) => text === "Radio P53" && y > 1700);
  assert.equal(footerEntries.length, 1, "bottom footer Radio P53 mark exists");
  assert.ok(footerEntries[0].y - noteEntry.y >= 300, "quiet open breathing room remains above bottom footer for link sticker");

  // Original lowercase casing preserved & minimal fallback without trackPalette
  const lowercaseCard = await render({
    track: "mangetout",
    artistName: "Wet Leg",
    album: "Moisturizer",
    signalLabel: "PREVIOUS",
    note: "Bienvenue.",
  });
  assert.ok(lowercaseCard.painted.some(({ text }) => text === "mangetout"), "original lowercase track casing is preserved");
  assert.ok(!lowercaseCard.painted.some(({ text }) => text === "MANGETOUT"), "track title is never uppercased");
  assert.ok(lowercaseCard.painted.some(({ text }) => text === "Previous"), "previous factor status label is painted");

  const legacyActiveCard = await render({
    track: "Secret Door",
    artistName: "Arctic Monkeys",
    album: "Humbug",
    signalLabel: "CURRENT TRANSMISSION",
    note: "parade of fools",
  });
  assert.ok(legacyActiveCard.painted.some(({ text }) => text === "Active"), "legacy CURRENT TRANSMISSION maps cleanly to Active");

  // Long text ellipsis & bounds check
  const long = await render({ track: "A".repeat(120), note: "A ".repeat(250) });
  assert.ok(long.painted.some(({ text }) => text.endsWith("…")), "long text is visibly abbreviated");
  assert.ok(long.painted.every(({ y }) => y < 1920), "text remains on the card");

  // Template & vars touch-up invariants
  const landingTpl = fs.readFileSync(path.join(__dirname, "../templates/p53-landing.html"), "utf8");
  const factorTpl = fs.readFileSync(path.join(__dirname, "../templates/p53-transmission.html"), "utf8");
  const varsCss = fs.readFileSync(path.join(__dirname, "../web/styles/p53-transmission-vars.css"), "utf8");
  assert.ok(landingTpl.includes('class="p53-path floating-path"') && landingTpl.includes('data-gsi-mark="favicon-slot"'));
  assert.ok(!landingTpl.includes("→ RADIO P53"));
  assert.ok(factorTpl.includes('class="p53-trace floating-path"') && factorTpl.includes('data-gsi-mark="favicon-slot"'));
  assert.ok(!factorTpl.includes("trace-current") && !factorTpl.includes("@@SIGNAL_LABEL@@"));
  assert.ok(!varsCss.includes("signal-panel::before") && !varsCss.includes("--signal-label"));

  console.log("P53 card: paper-sleeve geometry, palette, casing, long-text and ready-state paths passed");
})().catch((error) => { console.error(error); process.exitCode = 1; });
