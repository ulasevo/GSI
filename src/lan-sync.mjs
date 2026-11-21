/**
 * LAN Sync, Metadata Lookup, and Direct Authoring Publish pipeline for Chaperone (GSI).
 * Powers Android <-> Node.js bidirectional sync, Share-to-Chaperone link lookup,
 * and atomic archive updates (tracks.csv, entries/<slug>.md, covers/, config.json).
 */

import crypto from "node:crypto";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";

import { buildSite } from "./build-site.mjs";
import { syncAndroidAssets } from "./android-sync.mjs";
import {
  currentP53Slug,
  extractSectionsFromMarkdown,
  loadConfig,
  normalizeProviderUrl,
  readTracks,
  slugify,
} from "./gsi-core.mjs";
import { dominantColor } from "./palette.mjs";

const ALLOWED_LOOKUP_HOSTS = new Set([
  "itunes.apple.com",
  "music.apple.com",
  "open.spotify.com",
]);

const ALLOWED_ARTWORK_HOSTS = new Set([
  "is1-ssl.mzstatic.com",
  "is2-ssl.mzstatic.com",
  "is3-ssl.mzstatic.com",
  "is4-ssl.mzstatic.com",
  "is5-ssl.mzstatic.com",
  "i.scdn.co",
  "mosaic.scdn.co",
]);

const CSV_COLUMNS = [
  "signal_id",
  "order",
  "artist",
  "track",
  "album",
  "tags",
  "spotify_url",
  "apple_url",
  "cover_file",
  "accent",
];

function assertSafePath(rootDir, targetPath) {
  const resolvedRoot = path.resolve(rootDir);
  const resolvedTarget = path.resolve(targetPath);
  if (
    resolvedTarget !== resolvedRoot &&
    !resolvedTarget.startsWith(resolvedRoot + path.sep)
  ) {
    throw new Error("Path escapes archive root");
  }
  return resolvedTarget;
}

function assertAllowedHttpsUrl(rawUrl, allowlist) {
  let parsed;
  try {
    parsed = new URL(String(rawUrl || "").trim());
  } catch {
    throw new Error("Invalid URL");
  }
  if (parsed.protocol !== "https:") {
    throw new Error("Only HTTPS URLs are permitted");
  }
  const host = parsed.hostname.toLowerCase();
  if (!allowlist.has(host)) {
    throw new Error(`Unsupported host: ${host}`);
  }
  if (parsed.username || parsed.password) {
    throw new Error("URLs with credentials are not allowed");
  }
  return parsed;
}

async function fetchJsonStrict(rawUrl, allowlist, timeoutMs = 8000) {
  const parsed = assertAllowedHttpsUrl(rawUrl, allowlist);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(parsed.toString(), {
      method: "GET",
      headers: { Accept: "application/json", "User-Agent": "Chaperone-Archive/1.0" },
      redirect: "manual",
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`Upstream HTTP ${res.status}`);
    }
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

function upscaleItunesArt(url) {
  return String(url || "").replace(/\/\d+x\d+bb\.(jpg|png|webp)$/i, "/600x600bb.$1");
}

function parseItunesTrack(item, fallbackAppleUrl = "", fallbackSpotifyUrl = "") {
  if (!item || typeof item !== "object") return null;
  const track = String(item.trackName || "").trim();
  const artist = String(item.artistName || "").trim();
  if (!track || !artist) return null;
  const releaseDate = String(item.releaseDate || "");
  const releaseYear = /^\d{4}/.test(releaseDate) ? releaseDate.slice(0, 4) : "";
  return {
    track,
    artist,
    album: String(item.collectionName || "").trim(),
    coverUrl: upscaleItunesArt(item.artworkUrl100 || item.artworkUrl60 || ""),
    previewUrl: String(item.previewUrl || "").trim(),
    appleUrl:
      normalizeProviderUrl(item.trackViewUrl || fallbackAppleUrl, "apple") ||
      normalizeProviderUrl(fallbackAppleUrl, "apple"),
    spotifyUrl: normalizeProviderUrl(fallbackSpotifyUrl, "spotify"),
    releaseYear,
    trackNumber: Number.isInteger(item.trackNumber) ? item.trackNumber : null,
    trackCount: Number.isInteger(item.trackCount) ? item.trackCount : null,
  };
}

/**
 * Resolves metadata (track, artist, album, coverUrl, previewUrl) from an allowlisted
 * Apple Music or Spotify HTTPS link.
 */
export async function lookupMusicLink(rawUrl) {
  const parsed = assertAllowedHttpsUrl(rawUrl, ALLOWED_LOOKUP_HOSTS);
  const host = parsed.hostname.toLowerCase();

  if (host === "music.apple.com" || host === "itunes.apple.com") {
    const trackIdParam = parsed.searchParams.get("i");
    const songMatch = parsed.pathname.match(/\/(?:song|album)\/[^/]+\/(\d+)/i);
    const lookupId =
      (trackIdParam && /^\d+$/.test(trackIdParam) && trackIdParam) ||
      (songMatch && songMatch[1]) ||
      "";

    if (lookupId) {
      const data = await fetchJsonStrict(
        `https://itunes.apple.com/lookup?id=${encodeURIComponent(lookupId)}&entity=song`,
        ALLOWED_LOOKUP_HOSTS
      );
      const match = (data.results || []).find(
        (r) => r.wrapperType === "track" || r.kind === "song"
      );
      const parsedTrack = parseItunesTrack(match, parsed.toString(), "");
      if (parsedTrack) return parsedTrack;
    }

    // Fallback search from URL path slug
    const pathSegments = parsed.pathname
      .split("/")
      .map((s) => decodeURIComponent(s))
      .filter((s) => s && !/^(us|tr|gb|ca|album|song|\d+)$/i.test(s));
    const searchTerm = pathSegments.join(" ").replace(/[-_]+/g, " ").trim();
    if (searchTerm) {
      const data = await fetchJsonStrict(
        `https://itunes.apple.com/search?term=${encodeURIComponent(searchTerm)}&entity=song&limit=3`,
        ALLOWED_LOOKUP_HOSTS
      );
      const match = (data.results || [])[0];
      const parsedTrack = parseItunesTrack(match, parsed.toString(), "");
      if (parsedTrack) return parsedTrack;
    }

    throw new Error("Could not resolve track metadata from Apple Music link");
  }

  if (host === "open.spotify.com") {
    const oembedUrl = `https://open.spotify.com/oembed?url=${encodeURIComponent(parsed.toString())}`;
    const oembed = await fetchJsonStrict(oembedUrl, ALLOWED_LOOKUP_HOSTS);
    const rawTitle = String(oembed.title || "").trim();
    const thumbnailUrl = String(oembed.thumbnail_url || "").trim();

    if (rawTitle) {
      try {
        const searchData = await fetchJsonStrict(
          `https://itunes.apple.com/search?term=${encodeURIComponent(rawTitle)}&entity=song&limit=3`,
          ALLOWED_LOOKUP_HOSTS
        );
        const match = (searchData.results || [])[0];
        const parsedTrack = parseItunesTrack(match, "", parsed.toString());
        if (parsedTrack) {
          if (!parsedTrack.coverUrl && thumbnailUrl) {
            parsedTrack.coverUrl = thumbnailUrl;
          }
          return parsedTrack;
        }
      } catch {
        // Fall back to Spotify oEmbed title/thumbnail
      }
    }

    return {
      track: rawTitle || "Untitled Track",
      artist: "",
      album: "",
      coverUrl: thumbnailUrl,
      previewUrl: "",
      appleUrl: "",
      spotifyUrl: normalizeProviderUrl(parsed.toString(), "spotify"),
      releaseYear: "",
      trackNumber: null,
      trackCount: null,
    };
  }

  throw new Error("Unsupported provider");
}

function escapeCsvCell(value) {
  const str = String(value ?? "");
  if (/[",\r\n]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function serializeTracksCsv(rows) {
  const header = CSV_COLUMNS.join(",");
  const lines = rows.map((row) =>
    CSV_COLUMNS.map((col) => escapeCsvCell(row[col] ?? "")).join(",")
  );
  return [header, ...lines].join("\n") + "\n";
}

function generateSignalId(slug) {
  const digest = crypto.createHash("sha256").update(slug).digest("hex").slice(0, 20);
  return `sig-${digest}`;
}

function buildEntryMarkdown({ signalId, artist, track, album, coverFile, accent, sections }) {
  const frontmatter = [
    "---",
    `signal_id: ${JSON.stringify(signalId)}`,
    `artist: ${JSON.stringify(artist)}`,
    `track: ${JSON.stringify(track)}`,
    `album: ${JSON.stringify(album)}`,
    `cover: ${JSON.stringify(coverFile)}`,
    `accent: ${JSON.stringify(accent || "")}`,
    "---",
  ].join("\n");

  const bodyBlocks = (sections || [])
    .filter((s) => s && String(s.title || "").trim() && String(s.content || "").trim())
    .map(
      (s) =>
        `## ${String(s.title).trim().replace(/\r?\n/g, " ")}\n\n${String(s.content).trim()}`
    );

  return `${frontmatter}\n\n${bodyBlocks.join("\n\n")}\n`;
}

async function persistCoverImage(baseDir, slug, { coverBase64, coverUrl }) {
  const coversDir = assertSafePath(baseDir, path.join(baseDir, "covers"));
  const fileName = `${slug}.jpg`;
  const targetPath = assertSafePath(coversDir, path.join(coversDir, fileName));

  let rawBuffer = null;
  if (coverBase64 && typeof coverBase64 === "string") {
    const cleaned = coverBase64.replace(/^data:image\/[a-z0-9.+-]+;base64,/i, "").trim();
    if (cleaned.length > 6 * 1024 * 1024) {
      throw new Error("Cover image exceeds 4MB limit");
    }
    rawBuffer = Buffer.from(cleaned, "base64");
  } else if (coverUrl && typeof coverUrl === "string") {
    const parsed = assertAllowedHttpsUrl(coverUrl, ALLOWED_ARTWORK_HOSTS);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    try {
      const res = await fetch(parsed.toString(), {
        method: "GET",
        redirect: "manual",
        signal: controller.signal,
      });
      if (res.ok) {
        const arr = await res.arrayBuffer();
        if (arr.byteLength > 0 && arr.byteLength <= 6 * 1024 * 1024) {
          rawBuffer = Buffer.from(arr);
        }
      }
    } finally {
      clearTimeout(timer);
    }
  }

  if (!rawBuffer) return fs.existsSync(targetPath) ? fileName : "";

  await fsp.mkdir(coversDir, { recursive: true });
  await sharp(rawBuffer)
    .resize(1000, 1000, { fit: "inside", withoutEnlargement: true })
    .jpeg({ quality: 90, mozjpeg: true })
    .toFile(targetPath);

  return fileName;
}

/**
 * Builds the complete Android sync bundle served by GET /api/sync/bundle.
 */
export async function buildAndroidSyncBundle(baseDir) {
  const catalogPath = assertSafePath(baseDir, path.join(baseDir, "site", "data", "catalog.json"));
  const configPath = assertSafePath(baseDir, path.join(baseDir, "config.json"));
  const entriesDir = assertSafePath(baseDir, path.join(baseDir, "entries"));
  const enrichmentPath = assertSafePath(baseDir, path.join(baseDir, "data", "signal_enrichment.json"));

  const catalog = fs.existsSync(catalogPath)
    ? JSON.parse(await fsp.readFile(catalogPath, "utf-8"))
    : { signals: [] };
  const config = fs.existsSync(configPath) ? loadConfig(configPath) : {};
  const enrichment = fs.existsSync(enrichmentPath)
    ? JSON.parse(await fsp.readFile(enrichmentPath, "utf-8"))
    : {};

  const p53History = Array.isArray(config.p53_history) ? config.p53_history : [];
  const p53Slugs = new Set(p53History.map((item) => item?.slug).filter(Boolean));
  const p53Notes = config.p53_transmission_notes || {};
  const activeP53Slug = currentP53Slug(config, p53History) || config.p53_current_slug || "";

  const signals = (catalog.signals || []).map((item) => {
    const slug = String(item.slug || "");
    const mdPath = path.join(entriesDir, `${slug}.md`);
    const reviewSections = fs.existsSync(mdPath)
      ? extractSectionsFromMarkdown(mdPath)
          .filter((s) => String(s.content || "").trim())
          .map((s) => ({ title: s.title, content: s.content }))
      : [];
    const coverPath = String(item?.cover?.path || "");
    const coverFileName = coverPath ? path.basename(coverPath) : `${slug}.jpg`;
    const enr = enrichment[slug] || {};

    return {
      id: String(item.signal_id || generateSignalId(slug)),
      slug,
      artist: String(item.artist || ""),
      track: String(item.track || ""),
      album: String(item.album || ""),
      tags: Array.isArray(item.tags) ? item.tags : [],
      coverFileName,
      coverUrl: coverFileName ? `/covers/${encodeURIComponent(coverFileName)}` : "",
      primaryHex: String(item?.palette?.primary || "#FFAE00"),
      surfaceHex: String(item?.palette?.surface || "#141414"),
      glowHex: String(item?.palette?.glow || "#FFAE00"),
      transmissionNote: String(p53Notes[slug] || "").trim() || null,
      spotifyUrl: item?.links?.spotify?.url || null,
      appleUrl: item?.links?.apple?.url || null,
      previewUrl: String(enr.preview_url || "").trim() || null,
      releaseYear: String(enr.release_year || "").trim() || null,
      websitePath: item.page_url || null,
      isP53: p53Slugs.has(slug) || (Array.isArray(item.tags) && item.tags.includes("p53")),
      reviewSections,
    };
  });

  return {
    schema: 2,
    generatedAt: new Date().toISOString(),
    siteUrl: String(config.site_url || "").replace(/\/+$/, ""),
    p53CurrentSlug: activeP53Slug,
    p53About: String(config.p53_about || ""),
    sections: Array.isArray(config.sections) ? config.sections : [],
    signals,
  };
}

/**
 * Validates and publishes one or more signals pushed from Android or the local editor.
 * Atomically updates tracks.csv, entries/<slug>.md, covers/, data/signal_enrichment.json,
 * and config.json, then rebuilds the static site and Android bundled assets.
 */
export async function publishSignalsToArchive(baseDir, payload) {
  const incomingList = Array.isArray(payload?.signals)
    ? payload.signals
    : payload?.record
      ? [
          {
            ...payload.record,
            reviewSections: payload.sections || [],
            isP53: Boolean(payload.p53?.enabled),
            makeActiveP53: Boolean(payload.p53?.current),
            transmissionNote: payload.p53?.note || "",
          },
        ]
      : payload && typeof payload === "object" && payload.track && payload.artist
        ? [payload]
        : [];

  if (incomingList.length === 0) {
    throw new Error("No valid signals provided in sync payload");
  }
  if (incomingList.length > 50) {
    throw new Error("Batch limit exceeded (max 50 signals per push)");
  }

  const tracksFile = assertSafePath(baseDir, path.join(baseDir, "tracks.csv"));
  const entriesDir = assertSafePath(baseDir, path.join(baseDir, "entries"));
  const configPath = assertSafePath(baseDir, path.join(baseDir, "config.json"));
  const enrichmentPath = assertSafePath(baseDir, path.join(baseDir, "data", "signal_enrichment.json"));

  const existingRows = fs.existsSync(tracksFile) ? readTracks(tracksFile) : [];
  const config = fs.existsSync(configPath) ? loadConfig(configPath) : {};
  const enrichment = fs.existsSync(enrichmentPath)
    ? JSON.parse(await fsp.readFile(enrichmentPath, "utf-8"))
    : {};

  if (!Array.isArray(config.p53_history)) config.p53_history = [];
  if (!config.p53_transmission_notes || typeof config.p53_transmission_notes !== "object") {
    config.p53_transmission_notes = {};
  }

  await fsp.mkdir(entriesDir, { recursive: true });
  const publishedSlugs = [];

  for (const raw of incomingList) {
    const artist = String(raw.artist || "").trim().slice(0, 140);
    const track = String(raw.track || "").trim().slice(0, 180);
    const album = String(raw.album || "").trim().slice(0, 180);
    if (!artist || !track) {
      throw new Error("Each signal requires both artist and track");
    }

    const slug = slugify(raw.slug || `${artist}-${track}`);
    if (!slug || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
      throw new Error(`Invalid slug generated for ${artist} - ${track}`);
    }

    const rawTags = Array.isArray(raw.tags)
      ? raw.tags
      : String(raw.tags || "")
          .split(",")
          .map((t) => t.trim());
    const cleanTags = [...new Set(rawTags.map((t) => String(t).trim().toLowerCase()).filter(Boolean))];
    const isP53 = Boolean(raw.isP53) || cleanTags.includes("p53");
    if (isP53 && !cleanTags.includes("p53")) cleanTags.push("p53");

    const appleUrl = normalizeProviderUrl(raw.appleUrl || raw.apple_url || raw.link || "", "apple");
    const spotifyUrl = normalizeProviderUrl(raw.spotifyUrl || raw.spotify_url || raw.link || "", "spotify");

    const coverFile = await persistCoverImage(baseDir, slug, {
      coverBase64: raw.coverBase64 || "",
      coverUrl: raw.coverUrl || raw.cover_url || "",
    });

    let accent = String(raw.accent || raw.primaryHex || "").trim();
    if (!/^#[0-9a-f]{6}$/i.test(accent)) {
      accent = "";
    }
    if (!accent && coverFile) {
      const coverAbs = assertSafePath(baseDir, path.join(baseDir, "covers", coverFile));
      if (fs.existsSync(coverAbs)) {
        accent = await dominantColor(coverAbs);
      }
    }

    const rowIndex = existingRows.findIndex(
      (r) => slugify(`${r.artist || ""}-${r.track || ""}`) === slug
    );
    const signalId =
      (rowIndex >= 0 && existingRows[rowIndex].signal_id) ||
      String(raw.signal_id || raw.id || "").trim() ||
      generateSignalId(slug);

    const updatedRow = {
      signal_id: signalId,
      order: rowIndex >= 0 ? existingRows[rowIndex].order || "" : "",
      artist,
      track,
      album,
      tags: cleanTags.join(","),
      spotify_url: spotifyUrl || (rowIndex >= 0 ? existingRows[rowIndex].spotify_url || "" : ""),
      apple_url: appleUrl || (rowIndex >= 0 ? existingRows[rowIndex].apple_url || "" : ""),
      cover_file: coverFile || (rowIndex >= 0 ? existingRows[rowIndex].cover_file || "" : ""),
      accent: accent || (rowIndex >= 0 ? existingRows[rowIndex].accent || "" : ""),
    };

    if (rowIndex >= 0) {
      existingRows[rowIndex] = updatedRow;
    } else {
      existingRows.push(updatedRow);
    }

    // Write Markdown entry when sections are supplied
    const sections = Array.isArray(raw.reviewSections || raw.sections)
      ? (raw.reviewSections || raw.sections)
          .map((s) => ({
            title: String(s?.title || "").trim().slice(0, 80),
            content: String(s?.content || "").trim().slice(0, 12000),
          }))
          .filter((s) => s.title && s.content)
      : [];

    if (sections.length > 0) {
      const mdPath = assertSafePath(entriesDir, path.join(entriesDir, `${slug}.md`));
      const mdContent = buildEntryMarkdown({
        signalId,
        artist,
        track,
        album,
        coverFile: updatedRow.cover_file || `${slug}.jpg`,
        accent: updatedRow.accent,
        sections,
      });
      await fsp.writeFile(mdPath, mdContent, "utf-8");
    }

    // Save preview URL / release year enrichment if provided
    const previewUrl = String(raw.previewUrl || raw.preview_url || "").trim();
    const releaseYear = String(raw.releaseYear || raw.release_year || "").trim();
    if (previewUrl || releaseYear) {
      enrichment[slug] = {
        ...(enrichment[slug] || {}),
        ...(previewUrl ? { preview_url: previewUrl } : {}),
        ...(releaseYear ? { release_year: releaseYear } : {}),
      };
    }

    // Update P53 history & transmission note if requested
    const transmissionNote = String(raw.transmissionNote || "").trim().slice(0, 2000);
    if (isP53) {
      const existingP53Idx = config.p53_history.findIndex((p) => p?.slug === slug);
      const p53Entry = {
        artist,
        track,
        album,
        slug,
        signal_id: signalId,
        cover_file: updatedRow.cover_file || `${slug}.jpg`,
        ...(updatedRow.apple_url ? { apple_url: updatedRow.apple_url } : {}),
        ...(updatedRow.spotify_url ? { spotify_url: updatedRow.spotify_url } : {}),
        show_in_archive: true,
      };
      if (existingP53Idx >= 0) {
        config.p53_history[existingP53Idx] = { ...config.p53_history[existingP53Idx], ...p53Entry };
      } else {
        config.p53_history.push(p53Entry);
      }
      if (transmissionNote) {
        config.p53_transmission_notes[slug] = transmissionNote;
      }
      if (raw.makeActiveP53) {
        config.p53_current_slug = slug;
        config.p53_current_signal_id = signalId;
      }
    }

    publishedSlugs.push(slug);
  }

  if (payload?.p53CurrentSlug && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(payload.p53CurrentSlug)) {
    config.p53_current_slug = payload.p53CurrentSlug;
  }

  // Write tracks.csv, config.json, and signal_enrichment.json
  await fsp.writeFile(tracksFile, serializeTracksCsv(existingRows), "utf-8");
  await fsp.writeFile(configPath, JSON.stringify(config, null, 2) + "\n", "utf-8");
  await fsp.mkdir(path.dirname(enrichmentPath), { recursive: true });
  await fsp.writeFile(enrichmentPath, JSON.stringify(enrichment, null, 2) + "\n", "utf-8");

  // Rebuild static site & refresh Android assets
  await buildSite(baseDir);
  try {
    await syncAndroidAssets(baseDir);
  } catch {
    // Non-fatal if android dir is absent in minimal deployments
  }

  return {
    status: "published",
    slugs: publishedSlugs,
    p53CurrentSlug: config.p53_current_slug || "",
  };
}
