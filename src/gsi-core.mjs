/**
 * Core text, link, data, template, and artist helpers for Chaperone (GSI).
 * Ported from gsi_text.py, gsi_links.py, gsi_data.py, gsi_artists.py,
 * and builder/template_renderer.py.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { parse as parseCsv } from "csv-parse/sync";
import { HOME_STYLE_PARTS, localImageMetadata } from "./palette.mjs";

export const PROVIDER_HOSTS = {
  spotify: new Set(["open.spotify.com"]),
  apple: new Set(["music.apple.com", "itunes.apple.com"]),
};

export function escapeHtml(value, quote = false) {
  let text = String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  if (quote) {
    text = text.replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
  }
  return text;
}

export function slugify(text) {
  return String(text || "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function simpleMarkdownToHtml(markdownText) {
  let text = escapeHtml(String(markdownText || "").trim());
  text = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  const paragraphs = text
    .split("\n\n")
    .map((p) => p.trim())
    .filter(Boolean);
  return paragraphs.map((p) => `<p>${p.replace(/\n/g, "<br>")}</p>`).join("\n");
}

export function excerptText(rawContent, maxChars = 180) {
  const plain = String(rawContent || "").replace(/\*\*(.*?)\*\*/g, "$1");
  const collapsed = plain.replace(/\s+/g, " ").trim();
  if (collapsed.length <= maxChars) return collapsed;
  const slice = collapsed.slice(0, maxChars);
  const lastSpace = slice.lastIndexOf(" ");
  const clipped = (lastSpace > 0 ? slice.slice(0, lastSpace) : slice).replace(/[ ,;:-]+$/, "");
  return (clipped || slice.trimEnd()) + "…";
}

export function normalizeProviderUrl(value, provider) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  const allowedHosts = PROVIDER_HOSTS[provider] || new Set();
  try {
    const parsed = new URL(raw);
    const hostname = parsed.hostname.toLowerCase();
    if (
      parsed.protocol !== "https:" ||
      !hostname ||
      !allowedHosts.has(hostname) ||
      parsed.username ||
      parsed.password
    ) {
      return "";
    }
    return `https://${hostname}${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return "";
  }
}

export function providerSearchUrl(provider, artist, track, album) {
  const searchText = [artist, track, album]
    .map((part) => String(part || "").trim())
    .filter(Boolean)
    .join(" ");
  if (provider === "spotify") {
    return `https://open.spotify.com/search/${encodeURIComponent(searchText)}`;
  }
  if (provider === "apple") {
    return `https://music.apple.com/search?term=${encodeURIComponent(searchText).replace(/%20/g, "+")}`;
  }
  throw new Error(`Unsupported provider: ${provider}`);
}

export function resolveProviderLinks(item) {
  const links = {};
  for (const [provider, sourceKey] of [
    ["spotify", "spotify_url"],
    ["apple", "apple_url"],
  ]) {
    const explicit = normalizeProviderUrl(item[sourceKey] || "", provider);
    links[provider] = {
      url:
        explicit ||
        providerSearchUrl(provider, item.artist || "", item.track || "", item.album || ""),
      kind: explicit ? "canonical" : "search",
    };
  }
  return links;
}

export function streamingLinkMarkup(item) {
  const links = resolveProviderLinks(item);
  const rawArtist = String(item.artist || "");
  const rawTrack = String(item.track || "");

  const linkMarkup = (provider, label) => {
    const link = links[provider];
    const action = link.kind === "canonical" ? "Open" : "Search";
    const accessibleLabel = `${action} ${label} for ${rawTrack} by ${rawArtist}`;
    return (
      `<a class="stream-link" data-link-kind="${link.kind}" ` +
      `aria-label="${escapeHtml(accessibleLabel, true)}" ` +
      `href="${escapeHtml(link.url, true)}" target="_blank" ` +
      `rel="noopener noreferrer">${label}</a>`
    );
  };

  const previewUrl = String(item.preview_url || "").trim();
  const auditionButton = previewUrl
    ? `<button class="stream-link audition-trigger" type="button" aria-pressed="false" data-preview-url="${escapeHtml(previewUrl, true)}" aria-label="${escapeHtml(`Peek signal of ${rawTrack}`, true)}">PEEK <span class="peek-icon" aria-hidden="true">▶</span></button>`
    : "";

  return `
                <div class="stream-block">
                    <div class="stream-label">Have a listen:</div>
                    <div class="stream-links">
                        ${auditionButton}
                        ${linkMarkup("spotify", "Spotify")}
                        ${linkMarkup("apple", "Apple Music")}
                    </div>
                </div>
`;
}

export function loadConfig(configFile) {
  return JSON.parse(fs.readFileSync(configFile, "utf-8"));
}

export function readTracks(tracksFile) {
  const raw = fs.readFileSync(tracksFile, "utf-8");
  return parseCsv(raw, {
    columns: true,
    skip_empty_lines: true,
    bom: true,
  });
}

export function currentP53Record(config, p53History) {
  const currentId = String(config.p53_current_signal_id || "").trim();
  if (currentId) {
    const match = p53History.find(
      (item) => String(item.signal_id || "").trim() === currentId
    );
    if (match) return match;
  }
  const currentSlug = String(config.p53_current_slug || "").trim();
  if (currentSlug) {
    return p53History.find((item) => item.slug === currentSlug) || null;
  }
  return null;
}

export function currentP53Slug(config, p53History) {
  const record = currentP53Record(config, p53History);
  return record ? String(record.slug || "") : "";
}

export function orderedTracks(rows, config) {
  const hasManualOrder = rows.some((row) => /^\d+$/.test(String(row.order || "").trim()));
  if (hasManualOrder) {
    return [...rows].sort((a, b) => {
      const aText = String(a.order || "").trim();
      const bText = String(b.order || "").trim();
      const aVal = /^\d+$/.test(aText) ? parseInt(aText, 10) : 999999;
      const bVal = /^\d+$/.test(bText) ? parseInt(bText, 10) : 999999;
      return aVal - bVal;
    });
  }
  if (config.newest_first) {
    return [...rows].reverse();
  }
  return rows;
}

export function artistRoomGroups(tracks, p53History) {
  const grouped = new Map();
  for (const item of tracks) {
    if (!grouped.has(item.artist)) grouped.set(item.artist, []);
    grouped.get(item.artist).push(item);
  }
  const trackSlugs = new Set(tracks.map((item) => item.slug));
  for (const signal of p53History) {
    if (trackSlugs.has(signal.slug)) continue;
    const p53Item = {
      ...signal,
      p53_only: true,
      page_url: `p53/${signal.slug}.html`,
    };
    if (!grouped.has(signal.artist)) grouped.set(signal.artist, []);
    grouped.get(signal.artist).push(p53Item);
  }
  return grouped;
}

export function albumKey(artist, album) {
  return `${artist}\u001f${album}`;
}

export function buildGenerationInventory(
  tracks,
  p53History,
  archiveTracks,
  artistGroups,
  p53Slug = ""
) {
  const entryRoutes = {};
  for (const item of tracks) {
    if (item.slug && item.html_file) {
      entryRoutes[item.slug] = `entries/${item.html_file}`;
    }
  }
  const p53Routes = {};
  for (const item of p53History) {
    if (item.slug) {
      p53Routes[item.slug] = `p53/${item.slug}.html`;
    }
  }
  const artistRoutes = {};
  for (const artist of artistGroups.keys()) {
    const s = slugify(artist);
    if (s) artistRoutes[artist] = `artists/${s}.html`;
  }

  const albumGroups = new Map();
  for (const item of archiveTracks) {
    const k = albumKey(item.artist, item.album);
    if (!albumGroups.has(k)) albumGroups.set(k, { artist: item.artist, album: item.album, items: [] });
    albumGroups.get(k).items.push(item);
  }
  const albumRoutes = {};
  for (const [k, group] of albumGroups.entries()) {
    const s = slugify(`${group.artist}-${group.album}`);
    if (group.items.length && s) {
      albumRoutes[k] = `albums/${s}.html`;
    }
  }

  const p53PageNames = new Set(p53History.length ? ["index.html"] : []);
  for (const slug of Object.keys(p53Routes)) p53PageNames.add(`${slug}.html`);
  if (p53Slug && p53Routes[p53Slug]) p53PageNames.add("latest.html");

  return {
    entry_routes: entryRoutes,
    p53_routes: p53Routes,
    artist_routes: artistRoutes,
    album_routes: albumRoutes,
    signal_ids: {
      entries: Object.fromEntries(
        tracks.filter((i) => i.slug).map((i) => [i.slug, i.signal_id || ""])
      ),
      p53: Object.fromEntries(
        p53History.filter((i) => i.slug).map((i) => [i.slug, i.signal_id || ""])
      ),
    },
    expected_pages: {
      entries: new Set(tracks.filter((i) => i.html_file).map((i) => i.html_file)),
      p53: p53PageNames,
      artists: new Set(Object.values(artistRoutes).map((r) => path.basename(r))),
      albums: new Set(Object.values(albumRoutes).map((r) => path.basename(r))),
    },
  };
}

export function extractSectionsFromMarkdown(entryPath) {
  let text = fs.readFileSync(entryPath, "utf-8");
  text = text.replace(/<!--[\s\S]*?-->/g, "");
  if (text.startsWith("---")) {
    const secondIdx = text.indexOf("---", 3);
    if (secondIdx !== -1) {
      text = text.slice(secondIdx + 3);
    }
  }
  text = text.replace(/!\[cover\]\(.*?\)/g, "");
  text = text.replace(/\*\*Album:\*\*.*/g, "");
  text = text.replace(/\*\*Accent:\*\*.*/g, "");
  text = text.replace(/^# .*$/gm, "");

  const regex = /^## (.+)$/gm;
  const matches = [...text.matchAll(regex)];
  if (!matches.length) {
    return [{ title: "Note", content: text.trim() }];
  }
  const sections = [];
  for (let i = 0; i < matches.length; i++) {
    const match = matches[i];
    const title = match[1].trim();
    const start = match.index + match[0].length;
    const end = i + 1 < matches.length ? matches[i + 1].index : text.length;
    sections.push({ title, content: text.slice(start, end).trim() });
  }
  return sections;
}

export async function resolveArtistAsset(artist, config, assetRoot) {
  const configured = (config.artist_assets && config.artist_assets[artist]) || {};
  let imageFile = String(configured.image_file || "").replace(/\\/g, "/").trim();
  let metadata = { exists: false, valid: false, width: null, height: null, bytes: null };
  if (imageFile) {
    const resolvedRoot = path.resolve(assetRoot);
    const candidate = path.resolve(resolvedRoot, imageFile);
    if (candidate.startsWith(resolvedRoot + path.sep) || candidate === resolvedRoot) {
      metadata = await localImageMetadata(candidate);
      if (!metadata.valid) {
        imageFile = "";
      }
    } else {
      imageFile = "";
    }
  }
  return {
    file: imageFile,
    alt: String(configured.alt || `${artist} artist image`).trim(),
    source: String(configured.source || "manual").trim() || "manual",
    source_url: String(configured.source_url || "").trim(),
    metadata: imageFile
      ? metadata
      : { exists: false, valid: false, width: null, height: null, bytes: null },
    status: imageFile ? "local" : "fallback",
  };
}

export function artistImageMarkup(asset, artist) {
  if (asset.status !== "local" || !asset.file) return "";
  const { width, height } = asset.metadata || {};
  const dims =
    Number.isInteger(width) && Number.isInteger(height) && width > 0 && height > 0
      ? ` width="${width}" height="${height}"`
      : "";
  return (
    `<figure class="artist-image-header"><img class="artist-image" ` +
    `src="../artist-assets/${escapeHtml(asset.file, true)}" ` +
    `alt="${escapeHtml(asset.alt || `${artist} artist image`, true)}"` +
    `${dims} loading="eager" fetchpriority="high" decoding="async"></figure>`
  );
}

export function catalogueRecord(item, coversDir, coverMetadata) {
  const coverFile = String(item.cover_file || "").replace(/\\/g, "/");
  const validPath = Boolean(coverFile && !coverFile.includes(".."));
  const metadata = validPath
    ? coverMetadata
    : { exists: false, valid: false, width: null, height: null, bytes: null };
  const minDim = Math.min(metadata.width || 0, metadata.height || 0);
  const quality = !metadata.valid
    ? "missing"
    : minDim < 600
      ? "too-small"
      : minDim < 1200
        ? "usable-low-resolution"
        : "preferred";

  const cleanPalette = {};
  for (const [k, v] of Object.entries(item.palette || {})) {
    if (k !== "rim_gradient") cleanPalette[k] = v;
  }

  const record = {
    signal_id: item.signal_id || "",
    slug: item.slug || "",
    artist: item.artist || "",
    track: item.track || "",
    album: item.album || "",
    tags: String(item.tags || "")
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean),
    page_url: item.page_url || `entries/${item.html_file || ""}`,
    links: resolveProviderLinks(item),
    cover: {
      path: coverFile ? `covers/${coverFile}` : "",
      ...metadata,
      quality,
    },
    palette: cleanPalette,
  };
  if (item.p53_order !== undefined && item.p53_order !== null && item.p53_order !== 999) {
    record.p53_order = item.p53_order;
  }
  return record;
}

const _assetVersionCache = new Map();

function assetPayload(assetRelPath, webRoot) {
  const normalized = String(assetRelPath || "").trim();
  if (!normalized || normalized.includes("\\") || normalized.startsWith("/")) return null;
  const parts = normalized.split("/");
  if (!parts.length || !["styles", "scripts"].includes(parts[0]) || parts.includes("..")) {
    return null;
  }
  const resolvedRoot = path.resolve(webRoot);
  const candidate = path.resolve(resolvedRoot, normalized);
  if (!candidate.startsWith(resolvedRoot + path.sep)) return null;
  if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
    return fs.readFileSync(candidate);
  }
  if (normalized === "styles/gsi-home.css") {
    const homeDir = path.join(resolvedRoot, "styles", "home");
    if (fs.existsSync(homeDir)) {
      const chunks = [];
      for (const partName of HOME_STYLE_PARTS) {
        const partPath = path.join(homeDir, partName);
        if (!fs.existsSync(partPath)) return null;
        chunks.push(fs.readFileSync(partPath, "utf-8").trimEnd());
      }
      return Buffer.from(
        "/* Generated from web/styles/home/*.css in HOME_STYLE_PARTS order. */\n" +
          chunks.join("\n\n") +
          "\n",
        "utf-8"
      );
    }
  }
  return null;
}

function assetVersion(assetRelPath, webRoot) {
  const key = `${webRoot}::${assetRelPath}`;
  if (_assetVersionCache.has(key)) return _assetVersionCache.get(key);
  const payload = assetPayload(assetRelPath, webRoot);
  if (!payload) return null;
  const digest = crypto.createHash("sha256").update(payload).digest("hex").slice(0, 10);
  _assetVersionCache.set(key, digest);
  return digest;
}

export function clearAssetVersionCache() {
  _assetVersionCache.clear();
}

const LOCAL_ASSET_ATTR_RE =
  /(\b(?:href|src)\s*=\s*)(["'])((?:\.\.\/)*(?:styles\/[^"'?#]+\.css|scripts\/[^"'?#]+\.js)(?:\?[^"'#]*)?(?:#[^"']*)?)\2/g;

export function renderTemplate(templateName, values, { templateDir, webDir }) {
  const templatePath = path.join(templateDir, templateName);
  let template = fs.readFileSync(templatePath, "utf-8");

  template = template.replace(LOCAL_ASSET_ATTR_RE, (_full, prefix, quote, url) => {
    const hashIdx = url.indexOf("#");
    const hash = hashIdx >= 0 ? url.slice(hashIdx) : "";
    const withoutHash = hashIdx >= 0 ? url.slice(0, hashIdx) : url;
    const qIdx = withoutHash.indexOf("?");
    const pathname = qIdx >= 0 ? withoutHash.slice(0, qIdx) : withoutHash;
    const query = qIdx >= 0 ? withoutHash.slice(qIdx + 1) : "";

    let normalized = pathname;
    while (normalized.startsWith("../")) normalized = normalized.slice(3);
    const digest = assetVersion(normalized, webDir);
    if (!digest) return `${prefix}${quote}${url}${quote}`;
    const params = new URLSearchParams(query);
    params.delete("v");
    params.append("v", digest);
    return `${prefix}${quote}${pathname}?${params.toString()}${hash}${quote}`;
  });

  let rendered = template;
  for (const [key, value] of Object.entries(values)) {
    rendered = rendered.split(`@@${key.toUpperCase()}@@`).join(String(value ?? ""));
  }
  const unresolved = rendered.match(/@@[A-Z0-9_]+@@/g);
  if (unresolved && unresolved.length) {
    throw new Error(
      `Unresolved template markers in ${templatePath}: ${[...new Set(unresolved)].sort().join(", ")}`
    );
  }
  return rendered;
}
