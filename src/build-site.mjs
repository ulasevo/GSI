/**
 * Node.js static site generator for Chaperone (GSI).
 * Ports build.py + builder/*.py into pure Node.js 22 with zero Python runtime dependency.
 */

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  artworkPalette,
  compactRimGradient,
  copyDirFresh,
  copySiteCovers,
  copySiteScripts,
  copySiteStyles,
  dominantColor,
  fallbackPalette,
  imageSizeAttrs,
  localImageMetadata,
  paletteStyle,
  playlistVisuals,
} from "./palette.mjs";

import {
  albumKey,
  artistImageMarkup,
  artistRoomGroups,
  buildGenerationInventory,
  catalogueRecord,
  clearAssetVersionCache,
  currentP53Slug,
  escapeHtml,
  excerptText,
  extractSectionsFromMarkdown,
  loadConfig,
  normalizeProviderUrl,
  orderedTracks,
  readTracks,
  renderTemplate,
  resolveArtistAsset,
  resolveProviderLinks,
  simpleMarkdownToHtml,
  slugify,
  streamingLinkMarkup,
} from "./gsi-core.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
export const BASE = path.resolve(__dirname, "..");

const FILTER_ICONS = {
  bite: '<svg class="filter-icon" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 5.5C4.5 4.5 11.5 4.5 13.5 5.5M5 5.5l1 4.5 1-4.5M9 5.5l1 4.5 1-4.5"/></svg>',
  ulas: '<svg class="filter-icon" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 2.5h8a1 1 0 0 1 1 1v10.5l-5-3.5-5 3.5v-10.5a1 1 0 0 1 1-1Z"/></svg>',
  personal: '<svg class="filter-icon" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="8" cy="5.5" r="3"/><path d="M3 13.5c0-2.5 2.2-4 5-4s5 1.5 5 4"/></svg>',
  distortion: '<svg class="filter-icon" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1.5 8h2l2-4.5h2.5l2 9h2.5l2-4.5h2"/></svg>',
  bassline: '<svg class="filter-icon" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1.5 8c2-5.5 3.5-5.5 5.5 0s3.5 5.5 5.5 0h2"/></svg>',
  dreamy: '<svg class="filter-icon" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 2.5c0 2.5-1.5 4-4 4 2.5 0 4 1.5 4 4 0-2.5 1.5-4 4-4-2.5 0-4-1.5-4-4ZM13 11.5a1.5 1.5 0 1 1-1.2-1.5"/></svg>',
  pop: '<svg class="filter-icon" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 1.5 9.8 6.2 14.5 8 9.8 9.8 8 14.5 6.2 9.8 1.5 8 6.2 6.2Z"/></svg>',
  p53: '<svg class="filter-icon" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="8" cy="11.5" r="1.5" fill="currentColor"/><path d="M4.5 8a5 5 0 0 1 7 0M2 5.5a8.5 8.5 0 0 1 12 0"/></svg>',
};

function safeJsonScript(obj) {
  return JSON.stringify(obj).replace(/<\//g, "<\\/");
}

function formatCount(n) {
  return n >= 1000 ? n.toLocaleString("en-US") : String(n).padStart(2, "0");
}

function loadEnrichment(base) {
  const enrichmentFile = path.join(base, "data", "signal_enrichment.json");
  if (!fs.existsSync(enrichmentFile)) return {};
  try {
    return JSON.parse(fs.readFileSync(enrichmentFile, "utf-8"));
  } catch {
    return {};
  }
}

async function prepareTracks(base, config, enrichment) {
  const tracksFile = path.join(base, "tracks.csv");
  const entriesDir = path.join(base, "entries");
  const coversDir = path.join(base, "covers");
  const siteUrl = String(config.site_url || "").replace(/\/+$/, "");

  const rows = orderedTracks(readTracks(tracksFile), config);
  const built = [];
  for (const row of rows) {
    const artist = String(row.artist || "").trim();
    const track = String(row.track || "").trim();
    const album = String(row.album || "").trim();
    if (!artist || !track) continue;

    const tags = String(row.tags || "").trim();
    const manualAccent = String(row.accent || "").trim();
    const manualCoverFile = String(row.cover_file || "").trim();
    const normalizedSpotifyUrl = normalizeProviderUrl(row.spotify_url || "", "spotify");
    const normalizedAppleUrl = normalizeProviderUrl(row.apple_url || "", "apple");

    const slug = slugify(`${artist}-${track}`);
    const entryPath = path.join(entriesDir, `${slug}.md`);
    let coverPath = path.join(coversDir, `${slug}.jpg`);
    if (manualCoverFile && fs.existsSync(path.join(coversDir, manualCoverFile))) {
      coverPath = path.join(coversDir, manualCoverFile);
    }

    let accent = "#444444";
    let coverFile = "";
    if (fs.existsSync(coverPath)) {
      accent = await dominantColor(coverPath);
      coverFile = path.basename(coverPath);
    }
    if (manualAccent) accent = manualAccent;

    const palette = fs.existsSync(coverPath)
      ? await artworkPalette(coverPath, accent)
      : fallbackPalette(accent);
    const enriched = enrichment[slug] || {};

    built.push({
      signal_id: String(row.signal_id || "").trim(),
      tags,
      artist,
      track,
      album,
      slug,
      entry_file: path.basename(entryPath),
      html_file: `${slug}.html`,
      cover_file: coverFile,
      accent,
      palette,
      site_url: siteUrl,
      spotify_url: normalizedSpotifyUrl,
      apple_url: normalizedAppleUrl,
      preview_url: enriched.preview_url || "",
      release_year: enriched.release_year || "",
      track_number: enriched.track_number ?? null,
      track_count: enriched.track_count ?? null,
    });
  }
  return built;
}

async function prepareP53History(base, config, tracks, enrichment) {
  const coversDir = path.join(base, "covers");
  const tracksBySlug = new Map(tracks.map((t) => [t.slug, t]));
  const prepared = [];

  for (const record of config.p53_history || []) {
    const slug = String(
      record.slug || slugify(`${record.artist || ""} ${record.track || ""}`)
    ).trim();
    const item = { ...(tracksBySlug.get(slug) || {}), ...record, slug };
    item.spotify_url = normalizeProviderUrl(item.spotify_url || "", "spotify");
    item.apple_url = normalizeProviderUrl(item.apple_url || "", "apple");
    const coverFile = String(item.cover_file || `${slug}.jpg`).trim();
    const coverPath = path.join(coversDir, coverFile);
    item.cover_file = fs.existsSync(coverPath) ? coverFile : "";
    if (fs.existsSync(coverPath) && !item.accent) {
      item.accent = await dominantColor(coverPath);
    }
    item.accent = item.accent || "#444444";
    item.palette = fs.existsSync(coverPath)
      ? await artworkPalette(coverPath, item.accent)
      : fallbackPalette(item.accent);
    const enr = enrichment[slug] || {};
    item.preview_url = enr.preview_url || item.preview_url || "";
    item.release_year = enr.release_year || item.release_year || "";
    item.track_number = enr.track_number ?? item.track_number ?? null;
    item.track_count = enr.track_count ?? item.track_count ?? null;
    prepared.push(item);
  }
  return prepared;
}

function mergeP53IntoArchive(tracks, p53History) {
  const merged = tracks.map((item) => ({ ...item }));
  const bySlug = new Map(merged.map((item) => [item.slug, item]));

  p53History.forEach((signal, p53Order) => {
    if (!signal.show_in_archive) return;
    const existing = bySlug.get(signal.slug);
    if (existing) {
      const tags = String(existing.tags || "")
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      if (!tags.some((t) => t.toLowerCase() === "p53")) tags.push("p53");
      existing.tags = tags.join(",");
      existing.page_url = `entries/${existing.html_file}`;
      existing.p53_order = p53Order;
      return;
    }
    const archiveItem = {
      ...signal,
      tags: "p53",
      page_url: `p53/${signal.slug}.html`,
      p53_order: p53Order,
      spotify_url: signal.spotify_url || "",
      apple_url: signal.apple_url || "",
    };
    merged.push(archiveItem);
    bySlug.set(archiveItem.slug, archiveItem);
  });

  for (const item of merged) {
    if (!item.page_url) item.page_url = `entries/${item.html_file}`;
    if (item.p53_order === undefined) item.p53_order = 999;
  }
  return merged;
}

async function p53ArtContext(config, base) {
  const settings = (config.filters && config.filters.p53) || {};
  const coverValue = String(settings.playlist_cover || "covers/P53_cover.jpg").trim();
  const coverPath = coverValue ? path.join(base, coverValue) : "";
  const palette = await artworkPalette(coverPath, "#ff65ad");
  let browserCover = coverValue.replace(/\\/g, "/");
  if (browserCover.startsWith("covers/")) browserCover = "../" + browserCover;
  const primary = palette.primary || "#ff65ad";
  const style =
    `--accent:${primary};--p53-accent:${primary};` +
    paletteStyle(palette, browserCover, { rimGradient: compactRimGradient(palette) });
  return { palette, style };
}

async function buildEntryPage(item, artistCounts, albumPages, { base, config, tplOpts, outputDir }) {
  const entriesDir = path.join(base, "entries");
  const sectionInfo = config.section_info || {};
  const entryPath = path.join(entriesDir, item.entry_file);
  const sections = fs.existsSync(entryPath) ? extractSectionsFromMarkdown(entryPath) : [];

  const pageTitleText = `${item.track} — ${item.artist}`;
  const pageDescriptionText = `${item.track} by ${item.artist}, from ${item.album}, in Chaperone.`;
  const siteUrl = item.site_url || "";
  const entryUrl = siteUrl ? `${siteUrl}/entries/${item.html_file}` : "";
  const coverUrl =
    siteUrl && item.cover_file ? `${siteUrl}/covers/${encodeURIComponent(item.cover_file)}` : "";

  let sharingMeta = "";
  if (entryUrl) {
    sharingMeta += `\n    <link rel="canonical" href="${escapeHtml(entryUrl, true)}">\n    <meta property="og:url" content="${escapeHtml(entryUrl, true)}">\n    `;
  }
  if (coverUrl) {
    sharingMeta += `\n    <meta property="og:image" content="${escapeHtml(coverUrl, true)}">\n    <meta name="twitter:card" content="summary_large_image">\n    `;
  }

  let coverHtml = '<div class="cover-missing cover" aria-hidden="true"></div>';
  let bgStyle = "";
  let artImageSrc = "";
  if (item.cover_file) {
    const coverSrc = `../covers/${item.cover_file}`;
    artImageSrc = coverSrc;
    const sizeAttrs = await imageSizeAttrs(path.join(base, "covers", item.cover_file));
    coverHtml = `<img class="cover" src="${escapeHtml(coverSrc, true)}" alt="${escapeHtml(item.album, true)} cover" loading="eager" fetchpriority="high" decoding="async" ${sizeAttrs}>`;
    bgStyle = escapeHtml(
      `--entry-background:linear-gradient(120deg, rgba(0,0,0,.78), rgba(0,0,0,.96)), url("${coverSrc}");`,
      true
    );
  }

  const sectionCards = [];
  for (const section of sections) {
    if (!String(section.content || "").trim()) continue;
    const sectionTitle = section.title;
    const sectionId = `section-${slugify(sectionTitle)}`;
    const sectionHelp = String(sectionInfo[sectionTitle] || "").trim();
    let helpButton = "";
    let helpPanel = "";
    if (sectionHelp) {
      const helpId = `section-help-${slugify(sectionTitle)}`;
      helpButton = `<button class="section-info-button" type="button" aria-label="${escapeHtml(`About ${sectionTitle}`, true)}" aria-controls="${helpId}" aria-expanded="false">i</button>`;
      helpPanel = `<div class="section-help" id="${helpId}" aria-hidden="true"><div><p>${escapeHtml(sectionHelp)}</p></div></div>`;
    }
    sectionCards.push(`
        <section class="section-card" id="${sectionId}" dir="auto">
            <div class="section-heading">
                <h2>${escapeHtml(sectionTitle)}</h2>
                ${helpButton}
            </div>
            ${helpPanel}
            ${simpleMarkdownToHtml(section.content)}
        </section>`);
  }

  const inP53 = (config.p53_history || []).some((r) => r.slug === item.slug);
  let p53CounterpartHtml = "";
  if (inP53) {
    const p53Note = String((config.p53_transmission_notes || {})[item.slug] || "").trim();
    const noteExcerpt = p53Note ? excerptText(p53Note, 160) : "";
    const noteExcerptHtml = noteExcerpt
      ? `<p class="p53-card-note">${escapeHtml(noteExcerpt)}</p>`
      : "";
    const { palette: p53Palette } = await p53ArtContext(config, base);
    const p53ImgSize = await imageSizeAttrs(path.join(base, "covers", "P53_cover-runtime.webp"));
    const p53Primary = p53Palette.primary || "#ff65ad";
    p53CounterpartHtml =
      `<a class="p53-counterpart p53-card-companion" ` +
      `data-base-href="../p53/${escapeHtml(item.slug, true)}.html" ` +
      `href="../p53/${escapeHtml(item.slug, true)}.html" ` +
      `aria-label="${escapeHtml(`Radio P53: ${item.track}`, true)}" ` +
      `style="--p53-accent:${escapeHtml(p53Primary, true)};">` +
      `<div class="p53-card-art"><img src="../covers/P53_cover-runtime.webp" alt="Radio P53 artwork" loading="lazy" decoding="async" ${p53ImgSize}></div>` +
      `<div class="p53-card-body"><span class="p53-card-kicker">RADIO P53</span><strong class="p53-card-title">${escapeHtml(item.track)}</strong>${noteExcerptHtml}</div>` +
      `<span class="p53-card-cta" aria-hidden="true">↗</span></a>`;
  }

  const filterLabels = Object.fromEntries(
    Object.entries(config.filters || {}).map(([k, v]) => [k, v.label || k])
  );
  const filterKeys = String(item.tags || "")
    .split(",")
    .map((t) => t.trim().toLowerCase())
    .filter((t) => t in filterLabels);
  const filterReceiptLinks = filterKeys
    .filter((k) => k !== "p53")
    .map(
      (k) =>
        `<a data-filter-route="${escapeHtml(k, true)}" href="../index.html?filter=${encodeURIComponent(k)}">${escapeHtml(filterLabels[k])}</a>`
    )
    .join("");

  const artistRoomExists = (artistCounts.get(item.artist) || 0) >= 1;
  const artistSlug = slugify(item.artist);
  const artistHref = `../artists/${artistSlug}.html`;
  const albumHref = albumPages[albumKey(item.artist, item.album)] || "";

  const artistDisplay = artistRoomExists
    ? `<a class="artist-link" data-artist-base-href="${artistHref}" href="${artistHref}">${escapeHtml(item.artist)}</a>`
    : escapeHtml(item.artist);
  const albumDisplay = albumHref
    ? `<a class="album-link" data-album-base-href="${escapeHtml(albumHref, true)}" href="${escapeHtml(albumHref, true)}">${escapeHtml(item.album)}</a>`
    : escapeHtml(item.album);

  const alsoPaths = [];
  if (artistRoomExists) {
    alsoPaths.push(
      `<a data-artist-base-href="${artistHref}" href="${artistHref}">Artist: ${escapeHtml(item.artist)}</a>`
    );
  }
  if (albumHref) {
    alsoPaths.push(
      `<a data-album-base-href="${escapeHtml(albumHref, true)}" href="${escapeHtml(albumHref, true)}">Album: ${escapeHtml(item.album)}</a>`
    );
  }
  if (inP53) alsoPaths.push(`<a href="../p53/${item.slug}.html">Radio P53</a>`);
  if (filterReceiptLinks) alsoPaths.push(filterReceiptLinks);
  const alsoAppearsHtml = alsoPaths.length
    ? `<aside class="also-appears" id="also-appears"><span>Also in</span><div>${alsoPaths.join("")}</div></aside>`
    : "";

  const studioSections = sections
    .filter((s) => String(s.content || "").trim())
    .map((s) => ({
      title: s.title,
      excerpt: excerptText(s.content, 240),
    }));

  const entryPalette = item.palette || fallbackPalette(item.accent);
  const entryContextJson = safeJsonScript({
    filterLabels,
    artistSlug,
    artistName: item.artist,
    hasArtistRoom: artistRoomExists,
    slug: item.slug,
    track: item.track,
    album: item.album,
    coverSrc: artImageSrc,
    accent: item.accent,
    inP53,
    trackPalette: {
      primary: entryPalette.primary || item.accent,
      secondary: entryPalette.secondary || "#35c9e9",
      glow: entryPalette.glow || item.accent,
      surface: entryPalette.surface || "#16111c",
    },
    sections: studioSections,
  });

  const artStyle = escapeHtml(
    paletteStyle(item.palette || fallbackPalette(item.accent), artImageSrc),
    true
  );

  const htmlPage = renderTemplate(
    "entry.html",
    {
      safe_page_description: escapeHtml(pageDescriptionText, true),
      accent: escapeHtml(item.accent, true),
      safe_page_title: escapeHtml(pageTitleText),
      sharing_meta: sharingMeta,
      bg_style: bgStyle,
      art_style: artStyle,
      track: escapeHtml(item.track),
      cover_html: coverHtml,
      artist_display: artistDisplay,
      album_display: albumDisplay,
      p53_counterpart_html: p53CounterpartHtml,
      streaming_links_html: streamingLinkMarkup(item),
      entry_layout_class: "entry-reading-layout",
      entry_index_html: "",
      section_cards_html: sectionCards.join(""),
      also_appears_html: alsoAppearsHtml,
      entry_context_json: entryContextJson,
    },
    tplOpts
  );

  await fsp.mkdir(outputDir, { recursive: true });
  await fsp.writeFile(path.join(outputDir, item.html_file), htmlPage, "utf-8");
}

async function buildP53Page(
  item,
  outputName,
  entrySlugs,
  artistSlugs,
  albumRoutes,
  { base, config, tplOpts, outputDir }
) {
  const { palette: p53Palette, style: p53Style } = await p53ArtContext(config, base);
  const activeSlug = currentP53Slug(config, config.p53_history || []);
  const signalLabel = item.slug === activeSlug ? "ACTIVE" : "PREVIOUS";
  const artistSlug = slugify(item.artist);
  const hasArtistRoom = artistSlugs.has(artistSlug);
  const artistDisplay = hasArtistRoom
    ? `<a class="artist-link" href="../artists/${artistSlug}.html">${escapeHtml(item.artist)}</a>`
    : escapeHtml(item.artist);

  const albumRoute = albumRoutes[albumKey(item.artist || "", item.album || "")];
  const albumDisplay = albumRoute
    ? `<a class="album-link" href="${escapeHtml(albumRoute.startsWith("../") ? albumRoute : `../${albumRoute.replace(/^\/+/, "")}`, true)}">${escapeHtml(item.album)}</a>`
    : escapeHtml(item.album);

  const aboutText = String(config.p53_about || "").trim();
  const transmissionNote = String((config.p53_transmission_notes || {})[item.slug] || "").trim();
  const coverSrc = item.cover_file ? `../covers/${item.cover_file}` : "";
  const trackCoverPath = item.cover_file ? path.join(base, "covers", item.cover_file) : "";
  const trackPalette = item.palette || (await artworkPalette(trackCoverPath, item.accent || "#ff65ad"));
  const trackAccent = String(item.accent || trackPalette.primary || "#ff65ad");
  const p53Accent = String(p53Palette.primary || "#ff65ad");

  const p53EntryPath = path.join(base, "entries", `${item.slug}.md`);
  const p53EntrySections = fs.existsSync(p53EntryPath)
    ? extractSectionsFromMarkdown(p53EntryPath)
        .filter((s) => String(s.content || "").trim())
        .map((s) => ({
          title: s.title,
          excerpt: excerptText(s.content, 240),
        }))
    : [];

  const p53ContextJson = safeJsonScript({
    filterLabels: Object.fromEntries(
      Object.entries(config.filters || {}).map(([k, v]) => [k, v.label || k])
    ),
    expectedArtistRoute: artistSlug,
    artistName: item.artist,
    hasArtistRoom,
    shareTitle: `Radio P53 — ${item.track}`,
    accent: String(p53Palette.primary || item.accent || "#ff65ad"),
    trackAccent,
    p53Accent,
    cyanAccent: "#35c9e9",
    trackPalette: {
      primary: trackPalette.primary || trackAccent,
      secondary: trackPalette.secondary || "#8a8292",
      glow: trackPalette.glow || "#6d6475",
      field: trackPalette.field || "#120c18",
      soft: trackPalette.soft || "#d4c8db",
      surface: trackPalette.surface || "#16111c",
      ink: trackPalette.ink || "#f8f5ef",
    },
    signalLabel,
    track: item.track,
    album: item.album,
    slug: item.slug,
    coverSrc,
    p53CoverSrc: "../covers/P53_cover-runtime.webp",
    transmissionNote,
    entrySections: p53EntrySections,
  });

  const siteUrl = String(config.site_url || "").replace(/\/+$/, "");
  const p53Permalink = siteUrl ? `${siteUrl}/p53/${item.slug}.html` : "";
  const p53Description = `Radio P53 transmission: ${item.track} by ${item.artist}.`;
  let sharingMeta = "";
  if (p53Permalink) {
    const ogAsset = fs.existsSync(path.join(base, "covers", "P53_cover.jpg"))
      ? "/covers/P53_cover-og.jpg"
      : "/covers/P53_cover-runtime.webp";
    sharingMeta =
      `\n    <link rel="canonical" href="${escapeHtml(p53Permalink, true)}">\n` +
      `    <meta property="og:url" content="${escapeHtml(p53Permalink, true)}">\n` +
      `    <meta property="og:type" content="website">\n` +
      `    <meta property="og:site_name" content="Chaperone / Radio P53">\n` +
      `    <meta property="og:title" content="${escapeHtml(`Radio P53 — ${item.track}`, true)}">\n` +
      `    <meta property="og:description" content="${escapeHtml(p53Description, true)}">\n` +
      `    <meta property="og:image" content="${escapeHtml(siteUrl + ogAsset, true)}">\n` +
      `    <meta name="twitter:card" content="summary_large_image">`;
  }

  const coverSizeAttrs = coverSrc ? await imageSizeAttrs(trackCoverPath) : "";
  const coverHtml = coverSrc
    ? `<img class="signal-cover" src="${escapeHtml(coverSrc, true)}" alt="${escapeHtml(item.album, true)} cover" loading="eager" fetchpriority="high" decoding="async" ${coverSizeAttrs}>`
    : '<div class="cover-missing signal-cover" aria-hidden="true"></div>';
  const noteHtml = transmissionNote
    ? `<div class="transmission-note" dir="auto">${simpleMarkdownToHtml(transmissionNote)}</div>`
    : "";

  let entryCounterpartHtml = "";
  const entryPath = path.join(base, "entries", `${item.slug}.md`);
  if (entrySlugs.has(item.slug)) {
    const sections = fs.existsSync(entryPath)
      ? extractSectionsFromMarkdown(entryPath).filter((s) => String(s.content || "").trim())
      : [];
    let sectionsHtml = "";
    let excerptHtml = "";
    if (sections.length) {
      sectionsHtml = `<div class="entry-card-sections">${sections.map((s) => `<span>${escapeHtml(s.title)}</span>`).join("")}</div>`;
      const ex = excerptText(sections[0].content);
      if (ex) excerptHtml = `<p class="entry-card-excerpt">${escapeHtml(ex)}</p>`;
    }
    const trackCardStyle = escapeHtml(
      `--accent:${trackAccent};${paletteStyle(trackPalette, coverSrc)}`,
      true
    );
    entryCounterpartHtml =
      `<a class="entry-counterpart entry-card-companion" ` +
      `href="../entries/${escapeHtml(item.slug, true)}.html" ` +
      `aria-label="${escapeHtml(`Open entry: ${item.track}`, true)}" ` +
      `style="${trackCardStyle}">` +
      `<div class="entry-card-header"><span class="entry-card-kicker">Entry</span><strong class="entry-card-title">${escapeHtml(item.track)}</strong></div>` +
      `${sectionsHtml}${excerptHtml}<span class="entry-card-cta" aria-hidden="true">↗</span></a>`;
  }

  const htmlPage = renderTemplate(
    "p53-transmission.html",
    {
      p53_description: escapeHtml(p53Description, true),
      sharing_meta: sharingMeta,
      p53_title: escapeHtml(`P53 — ${item.track}`),
      signal_label: escapeHtml(signalLabel),
      cover_html: coverHtml,
      track: escapeHtml(item.track),
      artist: artistDisplay,
      album: albumDisplay,
      streaming_links_html: streamingLinkMarkup(item),
      entry_counterpart_html: entryCounterpartHtml,
      about_text: escapeHtml(aboutText),
      note_html: noteHtml,
      p53_context_json: p53ContextJson,
      art_style: escapeHtml(p53Style, true),
    },
    tplOpts
  );

  await fsp.mkdir(outputDir, { recursive: true });
  await fsp.writeFile(path.join(outputDir, outputName), htmlPage, "utf-8");
}

async function buildP53Archive(history, currentSlug, filterLabels, artistSlugs, { base, config, tplOpts, outputDir }) {
  const { style: p53Style } = await p53ArtContext(config, base);
  let current = history.find((item) => item.slug === currentSlug) || null;
  let remaining = history.filter((item) => item.slug !== currentSlug);
  if (!current && remaining.length) {
    current = remaining[remaining.length - 1];
    remaining = remaining.slice(0, -1);
  }
  const transmissions = current ? [current, ...remaining] : remaining;
  const transmissionNotes = config.p53_transmission_notes || {};

  const cards = [];
  for (let index = 0; index < transmissions.length; index++) {
    const item = transmissions[index];
    const number = String(index + 1).padStart(2, "0");
    const state = index === 0 ? "ACTIVE" : "PREVIOUS";
    const currentClass = index === 0 ? " is-current" : "";
    const currentAttr = index === 0 ? 'aria-current="true"' : "";
    const note = String(transmissionNotes[item.slug] || "").trim();
    const noteHtml = note
      ? `<blockquote class="transmission-intercept">“${escapeHtml(note)}”</blockquote>`
      : "";
    let coverHtml = '<div class="cover-missing" aria-hidden="true">P53</div>';
    if (item.cover_file) {
      const loading =
        index === 0
          ? 'loading="eager" fetchpriority="high" decoding="async"'
          : 'loading="lazy" decoding="async"';
      const sizeAttrs = await imageSizeAttrs(path.join(base, "covers", item.cover_file));
      coverHtml = `<img src="../covers/${escapeHtml(item.cover_file, true)}" alt="${escapeHtml(item.album, true)} cover" ${loading} ${sizeAttrs}>`;
    }
    cards.push(`<li class="transmission-card${currentClass}" id="signal-${number}" data-index="${index}">
    <a class="transmission-card-link" ${currentAttr} data-base-href="${escapeHtml(item.slug, true)}.html" href="${escapeHtml(item.slug, true)}.html">
        <div class="transmission-art">${coverHtml}</div>
        <div class="transmission-copy"><span class="transmission-arrow" aria-hidden="true"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 11.5 11.5 4.5M6 4.5h5.5V10"/></svg></span><div class="copy-content"><span class="signal-state">${state}</span><h2>${escapeHtml(item.track)}</h2><p>${escapeHtml(item.artist)}</p><small>${escapeHtml(item.album)}</small>${noteHtml}</div></div>
    </a>
</li>`);
  }

  const landingContext = safeJsonScript({
    filterLabels,
    artistSlugs: [...artistSlugs].sort(),
  });
  const totalFactors = transmissions.length;
  const page = renderTemplate(
    "p53-landing.html",
    {
      transmission_count: formatCount(totalFactors),
      factor_unit: totalFactors === 1 ? "FACTOR" : "FACTORS",
      cards_html: cards.join(""),
      landing_context: landingContext,
      p53_style: escapeHtml(p53Style, true),
    },
    tplOpts
  );
  await fsp.mkdir(outputDir, { recursive: true });
  await fsp.writeFile(path.join(outputDir, "index.html"), page, "utf-8");
}

async function buildArtistPages(artistGroups, { base, config, tplOpts, outputDir }) {
  await fsp.mkdir(outputDir, { recursive: true });
  const assetsDir = path.join(base, "artist-assets");
  const artistNotes = config.artist_notes || {};
  const albumNotes = config.album_notes || {};

  for (const [artist, artistTracks] of artistGroups.entries()) {
    const artistSlug = slugify(artist);
    const artistAsset = await resolveArtistAsset(artist, config, assetsDir);
    const artistImageHtml = artistImageMarkup(artistAsset, artist);
    const artistPalette =
      (artistTracks[0] && artistTracks[0].palette) || fallbackPalette("#49d9ef");
    const artistImageSrc = artistAsset.file ? `../artist-assets/${artistAsset.file}` : "";
    const artistHeadingClass = artistImageHtml
      ? "artist-heading has-artist-image"
      : "artist-heading";
    const note = String(artistNotes[artist] || "").trim();
    const noteHtml = note
      ? `<div class="artist-note" dir="auto">${simpleMarkdownToHtml(note)}</div>`
      : "";

    const albumsMap = new Map();
    for (const item of artistTracks) {
      if (!albumsMap.has(item.album)) albumsMap.set(item.album, []);
      albumsMap.get(item.album).push(item);
    }
    const groupedAlbums = [...albumsMap.entries()].filter(([, items]) => items.length > 0);
    const groupedSlugs = new Set(groupedAlbums.flatMap(([, items]) => items.map((i) => i.slug)));

    const entryHref = (item) =>
      item.p53_only
        ? `../p53/${escapeHtml(item.slug, true)}.html?artist=${artistSlug}`
        : `../entries/${escapeHtml(item.html_file, true)}?artist=${artistSlug}`;
    const entryBaseHref = (item) =>
      item.p53_only
        ? `../p53/${escapeHtml(item.slug, true)}.html`
        : `../entries/${escapeHtml(item.html_file, true)}`;

    const entryTile = async (item, compact = false) => {
      const transmissionLabel = item.p53_only ? "P53 ↗" : "OPEN ↗";
      const entryKind = item.p53_only ? ' data-entry-kind="transmission"' : "";
      const tNum = item.track_number;
      const tCnt = item.track_count;
      const year = item.release_year;
      if (compact) {
        const arcParts = [];
        if (tNum && tCnt) {
          arcParts.push(`TRACK ${String(tNum).padStart(2, "0")} OF ${String(tCnt).padStart(2, "0")}`);
        } else if (tNum) {
          arcParts.push(`TRACK ${String(tNum).padStart(2, "0")}`);
        }
        if (year) arcParts.push(String(year));
        const arcBadge = arcParts.length
          ? `<small class="album-entry-arc">${arcParts.join(" · ")}</small>`
          : "";
        return `<a class="album-entry"${entryKind} data-entry-base-href="${entryBaseHref(item)}" href="${entryHref(item)}" style="--accent:${item.accent}">
                    <span class="album-entry-mark" aria-hidden="true"></span>
                    <div class="album-entry-meta"><h3>${escapeHtml(item.track)}</h3>${arcBadge}</div>
                    <b class="album-entry-chevron" aria-hidden="true">›</b>
                </a>`;
      }
      const metaParts = [];
      if (item.p53_only) metaParts.push("P53 TRANSMISSION");
      else if (item.album) metaParts.push(escapeHtml(item.album.toUpperCase()));
      if (year) metaParts.push(String(year));
      if (tNum && tCnt) {
        metaParts.push(`TRACK ${String(tNum).padStart(2, "0")} OF ${String(tCnt).padStart(2, "0")}`);
      } else if (tNum) {
        metaParts.push(`TRACK ${String(tNum).padStart(2, "0")}`);
      }
      const arcHtml = metaParts.length
        ? `<small class="artist-signal-arc">${metaParts.join(" · ")}</small>`
        : "";
      const signalCover = String(item.cover_file || "").trim();
      const signalCoverHtml = signalCover
        ? `<img src="../covers/${escapeHtml(signalCover, true)}" alt="${escapeHtml(item.album, true)} cover" loading="lazy" decoding="async" ${await imageSizeAttrs(path.join(base, "covers", signalCover))}>`
        : '<div class="cover-missing" aria-hidden="true"></div>';
      return `<a class="artist-signal" data-entry-base-href="${entryBaseHref(item)}" href="${entryHref(item)}" style="--accent:${item.accent}">
                ${signalCoverHtml}
                <div class="artist-signal-meta"><h2 dir="auto">${escapeHtml(item.track)}</h2><p dir="auto">${escapeHtml(item.artist)}</p>${arcHtml}</div>
                <b>${transmissionLabel}</b>
            </a>`;
    };

    const albumSections = [];
    for (const [album, rawItems] of groupedAlbums) {
      const items = [...rawItems].sort(
        (a, b) =>
          (Number(a.track_number) || 999) - (Number(b.track_number) || 999) ||
          String(a.track || "").localeCompare(String(b.track || ""))
      );
      const albumHref = `../albums/${slugify(`${artist}-${album}`)}.html`;
      const albumTitleLink = `<a class="album-title-link" data-context-base-href="${escapeHtml(albumHref, true)}" href="${escapeHtml(albumHref, true)}">${escapeHtml(album)}</a>`;
      const albumNote = String((albumNotes[artist] && albumNotes[artist][album]) || "").trim();
      const albumNoteHtml = albumNote
        ? `<div class="album-note-preview" dir="auto">${simpleMarkdownToHtml(albumNote)}</div>`
        : "";
      const stackCover = String(items[0].cover_file || "").trim();
      const stackCoverHtml = stackCover
        ? `<img src="../covers/${escapeHtml(stackCover, true)}" alt="${escapeHtml(album, true)} cover" loading="lazy" decoding="async" ${await imageSizeAttrs(path.join(base, "covers", stackCover))}>`
        : '<div class="cover-missing" aria-hidden="true"></div>';
      const tiles = [];
      for (const item of items) tiles.push(await entryTile(item, true));
      albumSections.push(`<section class="album-stack" style="--accent:${items[0].accent}">
                <header>${stackCoverHtml}<div style="min-width:0"><span class="album-stack-kicker" style="display:block;margin-bottom:6px;font-size:9px;font-weight:950;letter-spacing:.18em">ALBUM</span><h2 dir="auto">${albumTitleLink}</h2>${albumNoteHtml}</div></header>
                <div>${tiles.join("")}</div>
            </section>`);
    }

    const remainingTiles = [];
    for (const item of artistTracks) {
      if (!groupedSlugs.has(item.slug)) remainingTiles.push(await entryTile(item, false));
    }

    const artistRoomData = safeJsonScript({
      filterKeys: Object.keys(config.filters || {}),
      filterLabels: Object.fromEntries(
        Object.entries(config.filters || {}).map(([k, v]) => [k, v.label || k])
      ),
      artistSlug,
    });

    const page = renderTemplate(
      "artist.html",
      {
        artist: escapeHtml(artist),
        artist_upper: escapeHtml(artist).toUpperCase(),
        artist_heading_class: artistHeadingClass,
        artist_count: String(artistTracks.length).padStart(2, "0"),
        note_html: noteHtml,
        artist_image_html: artistImageHtml,
        albums_html: albumSections.join(""),
        remaining_html: remainingTiles.join(""),
        artist_room_data: artistRoomData,
        art_style: escapeHtml(paletteStyle(artistPalette, artistImageSrc), true),
      },
      tplOpts
    );
    await fsp.writeFile(path.join(outputDir, `${artistSlug}.html`), page, "utf-8");
  }
}

async function buildAlbumPages(archiveTracks, artistGroups, albumRoutes, { base, config, tplOpts, outputDir }) {
  await fsp.mkdir(outputDir, { recursive: true });
  const notes = config.album_notes || {};
  let albumTracklists = {};
  const tracklistsPath = path.join(base, "data", "album_tracklists.json");
  if (fs.existsSync(tracklistsPath)) {
    try {
      albumTracklists = JSON.parse(await fsp.readFile(tracklistsPath, "utf-8"));
    } catch {
      albumTracklists = {};
    }
  }
  const normalizeTrackTitle = (value) =>
    String(value || "")
      .toLowerCase()
      .replace(/\s*\((feat\.|ft\.|with|remaster|bonus|deluxe|edit|version)[^)]*\)/gi, "")
      .replace(/[^a-z0-9]+/g, " ")
      .trim();

  const grouped = new Map();
  for (const item of archiveTracks) {
    const k = albumKey(item.artist, item.album);
    if (!grouped.has(k)) grouped.set(k, { artist: item.artist, album: item.album, items: [] });
    grouped.get(k).items.push(item);
  }

  for (const [k, { artist, album, items: rawItems }] of grouped.entries()) {
    if (!rawItems.length) continue;
    const route = albumRoutes[k];
    if (!route) continue;
    const items = [...rawItems].sort(
      (a, b) =>
        (Number(a.track_number) || 999) - (Number(b.track_number) || 999) ||
        String(a.track || "").localeCompare(String(b.track || ""))
    );
    const accent = items[0].accent;
    const cover = items[0].cover_file || "";
    const artStyle = escapeHtml(
      paletteStyle(items[0].palette || fallbackPalette(accent), cover ? `../covers/${cover}` : ""),
      true
    );
    const artistRoomExists = artistGroups.has(artist);
    const artistHref = `../artists/${slugify(artist)}.html`;
    const artistNav = artistRoomExists
      ? `<a id="album-artist-return" class="artist-link" data-artist-base-href="${escapeHtml(artistHref, true)}" href="${escapeHtml(artistHref, true)}">${escapeHtml(artist.toUpperCase())}</a>`
      : `<strong>${escapeHtml(artist.toUpperCase())}</strong>`;
    const artistDisplay = artistRoomExists
      ? `<a class="artist-link" data-artist-base-href="${escapeHtml(artistHref, true)}" href="${escapeHtml(artistHref, true)}">${escapeHtml(artist)}</a>`
      : escapeHtml(artist);
    const coverHtml = cover
      ? `<img class="album-cover" src="../covers/${escapeHtml(cover, true)}" alt="${escapeHtml(album, true)} cover" loading="eager" fetchpriority="high" decoding="async" ${await imageSizeAttrs(path.join(base, "covers", cover))}>`
      : '<div class="cover-missing album-cover" aria-hidden="true"></div>';

    const cachedTracklist = albumTracklists[`${artist}::${album}`] || null;
    const trackByNum = new Map();
    if (cachedTracklist && Array.isArray(cachedTracklist.tracks)) {
      for (const entry of cachedTracklist.tracks) {
        const num = Number(entry.track_number);
        if (Number.isInteger(num) && num > 0 && !trackByNum.has(num)) {
          trackByNum.set(num, entry);
        }
      }
    }

    const trackCounts = items
      .map((i) => Number(i.track_count))
      .filter((n) => Number.isInteger(n) && n > 0);
    const enrichedMax = trackCounts.length ? Math.max(...trackCounts) : 0;
    const cachedCount = trackByNum.size ? Math.max(Number(cachedTracklist.track_count) || 0, ...trackByNum.keys()) : 0;
    const totalTracks = Math.max(cachedCount, enrichedMax);
    const archivedBadgeHtml =
      totalTracks > 0
        ? ` · <span class="album-archived-badge">${items.length} / ${totalTracks} ARCHIVED</span>`
        : "";

    const reviewedByNum = new Map();
    const unassignedItems = [];
    for (const item of items) {
      const targetNorm = normalizeTrackTitle(item.track);
      let matchedNum = null;
      if (trackByNum.size && targetNorm) {
        for (const [num, entry] of trackByNum.entries()) {
          const entryNorm = normalizeTrackTitle(entry.title);
          if (entryNorm && (entryNorm === targetNorm || entryNorm.startsWith(`${targetNorm} `) || targetNorm.startsWith(`${entryNorm} `))) {
            matchedNum = num;
            break;
          }
        }
      }
      const fallbackNum = Number(item.track_number);
      const resolvedNum = matchedNum || (Number.isInteger(fallbackNum) && fallbackNum > 0 ? fallbackNum : null);
      if (resolvedNum) {
        if (!reviewedByNum.has(resolvedNum)) reviewedByNum.set(resolvedNum, []);
        reviewedByNum.get(resolvedNum).push(item);
      } else {
        unassignedItems.push(item);
      }
    }

    const songLinks = [];
    if (totalTracks > 0) {
      const maxNum = Math.max(totalTracks, ...reviewedByNum.keys(), 0);
      for (let t = 1; t <= maxNum; t++) {
        if (reviewedByNum.has(t)) {
          for (const item of reviewedByNum.get(t)) {
            const target = item.page_url || `entries/${item.html_file}`;
            const arcParts = [
              `TRACK ${String(t).padStart(2, "0")} OF ${String(totalTracks).padStart(2, "0")}`,
            ];
            if (item.release_year) arcParts.push(String(item.release_year));
            const arcBadge = `<small class="album-song-arc">${arcParts.join(" · ")}</small>`;
            songLinks.push(
              `<a class="album-song" data-entry-base-href="../${escapeHtml(target, true)}" href="../${escapeHtml(target, true)}">` +
                `<span class="album-song-mark" aria-hidden="true"></span>` +
                `<div class="album-song-meta"><span>${escapeHtml(item.track)}</span>${arcBadge}</div>` +
                `<b class="album-song-chevron" aria-hidden="true">›</b></a>`
            );
          }
        } else {
          const trackInfo = trackByNum.get(t) || null;
          const missingTitle = trackInfo && trackInfo.title ? trackInfo.title : `Track ${String(t).padStart(2, "0")}`;
          const missingUrl =
            (trackInfo && trackInfo.url) ||
            (cachedTracklist && cachedTracklist.collection_url) ||
            `https://music.apple.com/us/search?term=${encodeURIComponent(`${artist} ${missingTitle}`)}`;
          const requestParams = new URLSearchParams();
          requestParams.set("link", missingUrl);
          requestParams.set("track", `${missingTitle} — ${artist}`);
          const requestHref = `../recommend.html?${requestParams.toString()}`;
          const arcBadge = `<small class="album-song-arc">TRACK ${String(t).padStart(2, "0")} OF ${String(totalTracks).padStart(2, "0")} · NOT YET ARCHIVED</small>`;
          songLinks.push(
            `<div class="album-song album-song--unreviewed">` +
              `<span class="album-song-mark" aria-hidden="true"></span>` +
              `<div class="album-song-meta"><span>${escapeHtml(missingTitle)}</span>${arcBadge}</div>` +
              `<a class="album-request-btn" data-request-base-href="${escapeHtml(requestHref, true)}" href="${escapeHtml(requestHref, true)}" aria-label="${escapeHtml(`Request ${missingTitle} by ${artist}`, true)}">REQUEST</a>` +
              `</div>`
          );
        }
      }
      for (const item of unassignedItems) {
        const target = item.page_url || `entries/${item.html_file}`;
        const arcBadge = item.release_year
          ? `<small class="album-song-arc">${escapeHtml(String(item.release_year))}</small>`
          : "";
        songLinks.push(
          `<a class="album-song" data-entry-base-href="../${escapeHtml(target, true)}" href="../${escapeHtml(target, true)}">` +
            `<span class="album-song-mark" aria-hidden="true"></span>` +
            `<div class="album-song-meta"><span>${escapeHtml(item.track)}</span>${arcBadge}</div>` +
            `<b class="album-song-chevron" aria-hidden="true">›</b></a>`
        );
      }
    } else {
      for (const item of items) {
        const target = item.page_url || `entries/${item.html_file}`;
        const arcParts = [];
        if (item.track_number && item.track_count) {
          arcParts.push(
            `TRACK ${String(item.track_number).padStart(2, "0")} OF ${String(item.track_count).padStart(2, "0")}`
          );
        } else if (item.track_number) {
          arcParts.push(`TRACK ${String(item.track_number).padStart(2, "0")}`);
        }
        if (item.release_year) arcParts.push(String(item.release_year));
        const arcBadge = arcParts.length
          ? `<small class="album-song-arc">${arcParts.join(" · ")}</small>`
          : "";
        songLinks.push(
          `<a class="album-song" data-entry-base-href="../${escapeHtml(target, true)}" href="../${escapeHtml(target, true)}">` +
            `<span class="album-song-mark" aria-hidden="true"></span>` +
            `<div class="album-song-meta"><span>${escapeHtml(item.track)}</span>${arcBadge}</div>` +
            `<b class="album-song-chevron" aria-hidden="true">›</b></a>`
        );
      }
    }

    const note = String((notes[artist] && notes[artist][album]) || "").trim();
    const noteHtml = note
      ? `<section class="album-note" dir="auto"><span>My take</span>${simpleMarkdownToHtml(note)}</section>`
      : "";
    const albumRoomData = safeJsonScript({ filterKeys: Object.keys(config.filters || {}) });
    const page = renderTemplate(
      "album.html",
      {
        album: escapeHtml(album),
        album_upper: escapeHtml(album),
        accent: escapeHtml(accent, true),
        artist_nav: artistNav,
        cover_html: coverHtml,
        signal_count: formatCount(items.length),
        signal_unit: items.length === 1 ? "SIGNAL" : "SIGNALS",
        archived_badge_html: archivedBadgeHtml,
        artist_display: artistDisplay,
        note_html: noteHtml,
        song_links_html: songLinks.join(""),
        album_room_data: albumRoomData,
        art_style: artStyle,
      },
      tplOpts
    );
    await fsp.writeFile(path.join(outputDir, path.basename(route)), page, "utf-8");
  }
}

async function buildIndexHtml(archiveTracks, albumRoutes, { base, config, tplOpts, outputPath }) {
  const projectTitle = config.project_title || "Chaperone";
  const pageTitle = config.page_title || projectTitle;
  const intro = config.intro || "";
  const filters = config.filters || {};
  const siteUrl = String(config.site_url || "").replace(/\/+$/, "");
  const homepageUrl = siteUrl ? `${siteUrl}/` : "";
  let homepageUrlMeta = "";
  let shareImageMeta = "";
  if (homepageUrl) {
    homepageUrlMeta = `\n    <link rel="canonical" href="${escapeHtml(homepageUrl, true)}">\n    <meta property="og:url" content="${escapeHtml(homepageUrl, true)}">\n    `;
    shareImageMeta = `\n    <meta property="og:image" content="${escapeHtml(`${siteUrl}/covers/GSI_share.png`, true)}">\n    <meta property="og:image:width" content="1200">\n    <meta property="og:image:height" content="630">\n    <meta name="twitter:card" content="summary_large_image">\n    `;
  }

  const cards = [];
  for (const item of archiveTracks) {
    const safeTrack = escapeHtml(item.track);
    const safeArtist = escapeHtml(item.artist);
    const safeAlbum = escapeHtml(item.album);
    const safeCardLabel = escapeHtml(`${item.track} — ${item.artist}`, true);
    let coverHtml = '<div class="cover-missing" aria-hidden="true"></div>';
    if (item.cover_file) {
      const sizeAttrs = await imageSizeAttrs(path.join(base, "covers", item.cover_file));
      coverHtml = `<img src="covers/${escapeHtml(item.cover_file, true)}" alt="${safeAlbum} cover" loading="lazy" decoding="async" ${sizeAttrs}>`;
    }
    const tagsForAttr = String(item.tags || "").toLowerCase().replace(/,/g, " ");
    const p53Order = Number.isInteger(item.p53_order) ? item.p53_order : 999;
    const albumRoute = albumRoutes[albumKey(item.artist, item.album)] || "";
    const cardPalette = item.palette || fallbackPalette(item.accent);
    const cardArtStyle = paletteStyle(
      cardPalette,
      item.cover_file ? `covers/${item.cover_file}` : "",
      { rimGradient: "" }
    );
    const cardStyle = escapeHtml(
      `--accent: ${item.accent}; --p53-order: ${p53Order}; ${cardArtStyle}`,
      true
    );
    cards.push(`
        <a class="card"
            data-tags="${tagsForAttr}"
            data-artist="${escapeHtml(item.artist, true)}"
            data-album="${escapeHtml(item.album, true)}"
            data-album-href="${escapeHtml(albumRoute, true)}"
            data-track-number="${escapeHtml(item.track_number ?? "", true)}"
            data-p53-order="${p53Order}"
            aria-label="${safeCardLabel}"
            title="${safeCardLabel}"
            data-base-href="${escapeHtml(item.page_url, true)}"
            href="${escapeHtml(item.page_url, true)}" style="${cardStyle}">
            ${coverHtml}
            <div class="info">
                <h2 dir="auto">${safeTrack}</h2>
                <p dir="auto">${safeArtist}</p>
                <span dir="auto">${safeAlbum}</span>
            </div>
        </a>`);
  }

  const introHtml = intro.trim() ? `<p class="intro">${escapeHtml(intro)}</p>` : "";
  const filterButtons = [];
  const filterData = {};
  for (const [filterKey, filterSettings] of Object.entries(filters)) {
    const label = filterSettings.label || filterKey;
    const description = filterSettings.description || "";
    const color = filterSettings.color || "#ffffff";
    const playlistUrl = String(filterSettings.playlist_url || "").trim();
    const playlistCover = String(filterSettings.playlist_cover || "").trim();
    const playlistCta = String(filterSettings.playlist_cta || "Want more of the same?").trim();
    const [playlistSrc, playlistColor] = await playlistVisuals(playlistCover, color, base);
    const filterTracks = archiveTracks.filter((item) =>
      String(item.tags || "")
        .split(",")
        .map((t) => t.trim().toLowerCase())
        .includes(filterKey)
    );
    const iconSvg = FILTER_ICONS[filterKey] || "";
    const countLabel = formatCount(filterTracks.length);
    filterButtons.push(
      `<button class="filter-btn filter-${escapeHtml(filterKey, true)}" type="button" data-filter="${escapeHtml(filterKey, true)}" aria-pressed="false" style="--filter-color: ${escapeHtml(String(color).trim() || "#ffffff", true)};">` +
        `<span class="filter-icon-wrapper" aria-hidden="true">${iconSvg}</span>` +
        `<span class="filter-name">${escapeHtml(label)}</span>` +
        `<small class="filter-pill-count" aria-hidden="true">${countLabel}</small>` +
        `</button>`
    );
    filterData[filterKey] = {
      label,
      description,
      color,
      playlist_url: playlistUrl,
      playlist_cover: playlistSrc,
      playlist_color: playlistColor,
      playlist_cta: playlistCta,
      count: filterTracks.length,
      room_label_lines: filterSettings.room_label_lines || [label],
      icon: iconSvg,
    };
  }

  const filtersHtml = `
    <section class="filter-panel filter-panel--collapsed" id="filter-panel" aria-label="Filter archive">
        <div class="filter-panel-head">
            <button class="filter-drawer-toggle" id="filter-drawer-toggle" type="button" aria-expanded="false" aria-controls="filter-drawer-body">
                <span class="filter-drawer-lead">
                    <span class="filter-guide-label">FILTER TO BEGIN</span>
                    <span class="filter-active-pill" id="filter-active-pill" hidden>
                        <span class="filter-active-icon" id="filter-active-icon" aria-hidden="true"></span>
                        <span class="filter-active-text" id="filter-active-text"></span>
                    </span>
                </span>
                <span class="filter-drawer-caret" id="filter-drawer-caret" aria-hidden="true"><svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.5 7.5L10 13L15.5 7.5"/></svg></span>
            </button>
            <button class="filter-clear-quick-btn" id="filter-clear-quick-btn" type="button" aria-label="Clear active filter" hidden>×</button>
        </div>
        <div class="filter-drawer-body" id="filter-drawer-body" hidden>
            <div class="filter-row">
                ${filterButtons.join("")}
            </div>
        </div>
        <div class="filter-description hidden" id="filter-description-box" hidden aria-hidden="true">
            <div class="filter-room-label" id="filter-room-label" aria-hidden="true"></div>
            <div class="filter-decor" id="filter-decor" aria-hidden="true"></div>
            <div class="filter-copy">
                <div class="filter-count" id="filter-count" role="status" aria-live="polite"></div>
                <h2 id="filter-title"></h2>
                <p id="filter-description"></p>
            </div>
            <a class="playlist-card hidden" id="playlist-card" href="#" target="_blank" rel="noopener noreferrer" hidden aria-hidden="true">
                <img id="playlist-cover" alt="Playlist cover" loading="lazy" decoding="async">
                <div class="playlist-card-copy">
                    <span class="playlist-card-eyebrow">APPLE MUSIC ↗</span>
                    <span class="playlist-card-text" id="playlist-cta"></span>
                </div>
            </a>
        </div>
    </section>`;

  const p53Slug = currentP53Slug(config, config.p53_history || []);
  const p53Item = archiveTracks.find((i) => i.slug === p53Slug) || null;
  let p53Html = "";
  if (p53Item) {
    const p53Settings = (config.filters && config.filters.p53) || {};
    const p53CoverValue = String(p53Settings.playlist_cover || "covers/P53_cover.jpg").trim();
    const p53Palette = await artworkPalette(
      path.join(base, p53CoverValue),
      p53Item.accent || "#ff65ad"
    );
    const p53Primary = p53Palette.primary || p53Item.accent || "#ff65ad";
    const p53Style =
      `--signal-accent:${p53Primary};--p53-accent:${p53Primary};` +
      paletteStyle(p53Palette, p53CoverValue, { rimGradient: compactRimGradient(p53Palette) });
    const runtimeImgAttrs = await imageSizeAttrs(path.join(base, "covers", "P53_cover-runtime.webp"));
    const albumImgAttrs = await imageSizeAttrs(path.join(base, "covers", p53Item.cover_file));
    p53Html = `
        <a class="p53-broadcast" data-base-href="p53/index.html" href="p53/index.html" aria-label="Open Radio P53: current and previous transmissions" style="${escapeHtml(p53Style, true)}">
            <div class="p53-art">
                <img src="covers/P53_cover-runtime.webp" alt="P53 protein artwork" loading="eager" fetchpriority="high" decoding="async" ${runtimeImgAttrs}>
            </div>
            <div class="p53-overlay">
                <div class="p53-ribbon-lead">
                    <div class="p53-radio">RADIO P53</div>
                </div>
                <div class="p53-ribbon-track">
                    <img class="p53-album" src="covers/${escapeHtml(p53Item.cover_file, true)}" alt="${escapeHtml(p53Item.album, true)} cover" loading="lazy" decoding="async" ${albumImgAttrs}>
                    <div class="p53-signal-copy">
                        <strong>${escapeHtml(p53Item.track)}</strong>
                        <small>${escapeHtml(p53Item.artist)}</small>
                    </div>
                    <span class="p53-arrow" aria-hidden="true"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 11.5 11.5 4.5M6 4.5h5.5V10"/></svg></span>
                </div>
            </div>
        </a>`;
  }

  const indexHtml = renderTemplate(
    "index.html",
    {
      safe_meta_description: escapeHtml(intro, true),
      safe_page_title: escapeHtml(pageTitle),
      homepage_url_meta: homepageUrlMeta,
      share_image_meta: shareImageMeta,
      safe_project_title: escapeHtml(projectTitle),
      intro_html: introHtml,
      p53_html: p53Html,
      filters_html: filtersHtml,
      cards_html: cards.join(""),
      filter_data_json: safeJsonScript(filterData),
    },
    tplOpts
  );

  await fsp.mkdir(path.dirname(outputPath), { recursive: true });
  await fsp.writeFile(outputPath, indexHtml, "utf-8");
}

async function build404Page(archiveTracks, { config, tplOpts, outputPath }) {
  const copy = config.not_found || {};
  const sitePath = "/";
  const recommendations = archiveTracks.map((item) => {
    const links = resolveProviderLinks(item);
    return {
      track: item.track,
      artist: item.artist,
      album: item.album,
      cover: item.cover_file || "",
      url: item.page_url || `entries/${item.html_file}`,
      accent: item.accent,
      spotify: links.spotify.url,
      apple: links.apple.url,
    };
  });
  let notFoundTitle = escapeHtml(copy.title || "THIS FREQUENCY DOES NOT EXIST.");
  notFoundTitle = notFoundTitle.replace(" NOT ", " <em>NOT</em> ");
  const proteinDrops = Array.from({ length: 18 }, (_, index) => {
    const x = (index * 17) % 101;
    const delay = (index * 0.73).toFixed(2);
    const speed = 9 + (index % 7);
    const size = 34 + (index % 5) * 13;
    return `<span style="--x:${x}%;--delay:-${delay}s;--speed:${speed}s;--size:${size}px"></span>`;
  }).join("");

  const page = renderTemplate(
    "404.html",
    {
      error_page_data: safeJsonScript({ tracks: recommendations, deployedRoot: sitePath }),
      site_path: escapeHtml(sitePath, true),
      not_found_title: notFoundTitle,
      protein_drops: proteinDrops,
      eyebrow: escapeHtml(copy.eyebrow || "SIGNAL LOST / 404"),
      message: escapeHtml(copy.message || "The page slipped out of Chaperone."),
      recommendation_label: escapeHtml(copy.recommendation_label || "INTERCEPTED SIGNAL"),
    },
    tplOpts
  );
  await fsp.mkdir(path.dirname(outputPath), { recursive: true });
  await fsp.writeFile(outputPath, page, "utf-8");
}

async function writeManifests(archiveTracks, artistGroups, inventory, { base, config, siteDataDir }) {
  await fsp.mkdir(siteDataDir, { recursive: true });
  const coversDir = path.join(base, "covers");
  const artistAssetsDir = path.join(base, "artist-assets");

  const catalogRecords = [];
  for (const item of archiveTracks) {
    const coverFile = String(item.cover_file || "").replace(/\\/g, "/");
    const coverPath = coverFile ? path.join(coversDir, coverFile) : "";
    const meta = await localImageMetadata(coverPath);
    catalogRecords.push(catalogueRecord(item, coversDir, meta));
  }
  await fsp.writeFile(
    path.join(siteDataDir, "catalog.json"),
    JSON.stringify(
      {
        schema: 1,
        description: "Generated GSI media-link and local-art inventory; review prose is never included.",
        signals: catalogRecords,
      },
      null,
      2
    ) + "\n",
    "utf-8"
  );

  const artistRecords = [];
  for (const artist of [...artistGroups.keys()].sort((a, b) =>
    a.toLowerCase().localeCompare(b.toLowerCase())
  )) {
    const items = artistGroups.get(artist);
    artistRecords.push({
      artist,
      slug: slugify(artist),
      page_url: `artists/${slugify(artist)}.html`,
      signal_count: items.length,
      albums: [...new Set(items.map((i) => i.album).filter(Boolean))].sort((a, b) =>
        a.toLowerCase().localeCompare(b.toLowerCase())
      ),
      image: await resolveArtistAsset(artist, config, artistAssetsDir),
    });
  }
  await fsp.writeFile(
    path.join(siteDataDir, "artists.json"),
    JSON.stringify(
      {
        schema: 1,
        description: "Generated artist inventory; review prose is never included.",
        artists: artistRecords,
      },
      null,
      2
    ) + "\n",
    "utf-8"
  );

  await fsp.writeFile(
    path.join(siteDataDir, "generation.json"),
    JSON.stringify(
      {
        schema: 1,
        description: "Generated GSI route relationships and expected outputs; review prose is never included.",
        relationships: {
          entries: Object.entries(inventory.entry_routes)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([slug, href]) => ({
              slug,
              signal_id: inventory.signal_ids.entries[slug] || "",
              href,
            })),
          p53: Object.entries(inventory.p53_routes)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([slug, href]) => ({
              slug,
              signal_id: inventory.signal_ids.p53[slug] || "",
              href,
            })),
          artists: Object.entries(inventory.artist_routes)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([artist, href]) => ({ artist, href })),
          albums: Object.entries(inventory.album_routes)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([k, href]) => {
              const [artist, album] = k.split("\u001f");
              return { artist, album, href };
            }),
        },
        expected_pages: Object.fromEntries(
          Object.entries(inventory.expected_pages).map(([family, names]) => [
            family,
            [...names].sort(),
          ])
        ),
      },
      null,
      2
    ) + "\n",
    "utf-8"
  );

  // Copy public Firebase web client configuration into site/data/firebase-config.json
  const fbConfigSrc = path.join(base, "firebase-applet-config.json");
  if (fs.existsSync(fbConfigSrc)) {
    try {
      const raw = JSON.parse(await fsp.readFile(fbConfigSrc, "utf-8"));
      const publicConfig = {
        projectId: raw.projectId || "",
        appId: raw.appId || "",
        apiKey: raw.apiKey || "",
        authDomain: raw.authDomain || "",
        storageBucket: raw.storageBucket || "",
        messagingSenderId: raw.messagingSenderId || "",
        firestoreDatabaseId: raw.firestoreDatabaseId || "",
      };
      await fsp.writeFile(
        path.join(siteDataDir, "firebase-config.json"),
        JSON.stringify(publicConfig, null, 2) + "\n",
        "utf-8"
      );
    } catch {
      // Skip if firebase-applet-config.json is unreadable
    }
  }
}

export async function buildSite(base = BASE) {
  clearAssetVersionCache();
  const config = loadConfig(path.join(base, "config.json"));
  const enrichment = loadEnrichment(base);
  const siteDir = path.join(base, "site");
  const webDir = path.join(base, "web");
  const tplOpts = { templateDir: path.join(base, "templates"), webDir };

  const tracks = await prepareTracks(base, config, enrichment);
  const p53History = await prepareP53History(base, config, tracks, enrichment);
  const archiveTracks = mergeP53IntoArchive(tracks, p53History);
  const artistGroups = artistRoomGroups(tracks, p53History);
  const p53Slug = currentP53Slug(config, p53History);
  const inventory = buildGenerationInventory(
    tracks,
    p53History,
    archiveTracks,
    artistGroups,
    p53Slug
  );

  const artistCounts = new Map(
    [...artistGroups.entries()].map(([artist, items]) => [artist, items.length])
  );

  const referencedCovers = new Set([
    "GSI_favicon.svg",
    "GSI_share.png",
    "P53_cover-runtime.webp",
  ]);
  for (const item of [...archiveTracks, ...tracks, ...p53History]) {
    if (item.cover_file) referencedCovers.add(path.basename(item.cover_file));
  }
  for (const settings of Object.values(config.filters || {})) {
    const pc = String(settings.playlist_cover || "").replace(/\\/g, "/").trim();
    if (pc) referencedCovers.add(path.basename(pc));
  }

  await copySiteCovers(path.join(base, "covers"), path.join(siteDir, "covers"), referencedCovers);
  await copyDirFresh(path.join(base, "artist-assets"), path.join(siteDir, "artist-assets"));
  await copySiteScripts(webDir, path.join(siteDir, "scripts"));
  await copyDirFresh(path.join(webDir, "fonts"), path.join(siteDir, "fonts"));
  await copySiteStyles(webDir, path.join(siteDir, "styles"));

  await writeManifests(archiveTracks, artistGroups, inventory, {
    base,
    config,
    siteDataDir: path.join(siteDir, "data"),
  });

  const albumPages = Object.fromEntries(
    Object.entries(inventory.album_routes).map(([k, route]) => [k, `../${route}`])
  );
  const entrySlugs = new Set(Object.keys(inventory.entry_routes));
  const artistSlugs = new Set([...artistGroups.keys()].map((a) => slugify(a)));

  for (const item of tracks) {
    await buildEntryPage(item, artistCounts, albumPages, {
      base,
      config,
      tplOpts,
      outputDir: path.join(siteDir, "entries"),
    });
  }

  for (const item of p53History) {
    await buildP53Page(item, `${item.slug}.html`, entrySlugs, artistSlugs, inventory.album_routes, {
      base,
      config,
      tplOpts,
      outputDir: path.join(siteDir, "p53"),
    });
  }

  const currentP53Item = p53History.find((i) => i.slug === p53Slug) || null;
  if (currentP53Item) {
    await buildP53Page(
      currentP53Item,
      "latest.html",
      entrySlugs,
      artistSlugs,
      inventory.album_routes,
      {
        base,
        config,
        tplOpts,
        outputDir: path.join(siteDir, "p53"),
      }
    );
  }

  if (p53History.length) {
    const filterLabels = Object.fromEntries(
      Object.entries(config.filters || {}).map(([k, v]) => [k, v.label || k])
    );
    await buildP53Archive(p53History, p53Slug, filterLabels, artistSlugs, {
      base,
      config,
      tplOpts,
      outputDir: path.join(siteDir, "p53"),
    });
  }

  await buildArtistPages(artistGroups, {
    base,
    config,
    tplOpts,
    outputDir: path.join(siteDir, "artists"),
  });

  await buildAlbumPages(archiveTracks, artistGroups, inventory.album_routes, {
    base,
    config,
    tplOpts,
    outputDir: path.join(siteDir, "albums"),
  });

  await buildIndexHtml(archiveTracks, inventory.album_routes, {
    base,
    config,
    tplOpts,
    outputPath: path.join(siteDir, "index.html"),
  });

  await build404Page(archiveTracks, {
    config,
    tplOpts,
    outputPath: path.join(siteDir, "404.html"),
  });

  await fsp.writeFile(
    path.join(siteDir, "recommend.html"),
    renderTemplate("recommend.html", {}, tplOpts),
    "utf-8"
  );

  const inboxTplPath = path.join(base, "templates", "inbox.html");
  if (fs.existsSync(inboxTplPath)) {
    await fsp.writeFile(
      path.join(siteDir, "inbox.html"),
      renderTemplate("inbox.html", {}, tplOpts),
      "utf-8"
    );
  }

  console.log(
    `[Chaperone] Built site: ${archiveTracks.length} archive signals, ${tracks.length} entries, ${artistGroups.size} artists, ${Object.keys(inventory.album_routes).length} albums, ${p53History.length} P53 transmissions.`
  );
}

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  buildSite().catch((err) => {
    console.error("[Chaperone] Build failed:", err);
    process.exit(1);
  });
}
