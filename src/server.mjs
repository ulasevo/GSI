/**
 * Express server for Chaperone (GSI) on AI Studio Web Runtime (0.0.0.0:3000).
 * Builds the static site on startup and serves the archive + recommendation intake
 * + local authoring editor routes ported from tools/submission_server.py.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import express from "express";

import { BASE, buildSite } from "./build-site.mjs";
import {
  buildAndroidSyncBundle,
  lookupMusicLink,
  publishSignalsToArchive,
} from "./lan-sync.mjs";
import {
  currentP53Record,
  loadConfig,
  readTracks,
  slugify,
} from "./gsi-core.mjs";
import { extractPaletteSwatches } from "./palette.mjs";

const SITE_DIR = path.join(BASE, "site");
const COVERS_DIR = path.join(BASE, "covers");
const ENTRIES_DIR = path.join(BASE, "entries");
const EDITOR_DIR = path.join(BASE, "tools", "editor");
const INBOX_DIR = path.join(BASE, "submissions", "inbox");
const DRAFTS_DIR = path.join(BASE, "submissions", "drafts");
const HEARTS_SYNC_FILE = path.join(BASE, "submissions", "hearts-sync.json");

const SUPPORTED_PROVIDERS = new Set([
  "music.apple.com",
  "itunes.apple.com",
  "open.spotify.com",
  "spotify.link",
  "youtube.com",
  "music.youtube.com",
  "youtu.be",
  "soundcloud.com",
  "bandcamp.com",
  "deezer.com",
  "tidal.com",
]);

const recommendationsMemory = [];

function validateRecommendation(payload) {
  const link = String(payload?.link || "").trim();
  const note = String(payload?.note || "").trim();
  const name = String(payload?.name || "").trim();
  let parsed;
  try {
    parsed = new URL(link);
  } catch {
    return { error: "Use an HTTPS music link." };
  }
  const host = parsed.hostname.toLowerCase().replace(/^www\./, "");
  if (parsed.protocol !== "https:" || !host) {
    return { error: "Use an HTTPS music link." };
  }
  const allowed =
    SUPPORTED_PROVIDERS.has(host) ||
    [...SUPPORTED_PROVIDERS].some((domain) => host.endsWith(`.${domain}`));
  if (!allowed) {
    return { error: "Use a link from a supported music provider." };
  }
  if (!note || note.length > 4000) {
    return { error: "A note between 1 and 4000 characters is required." };
  }
  if (name.length > 80) {
    return { error: "The optional signature is too long." };
  }
  return {
    clean: {
      link,
      note,
      name,
      receivedAt: new Date().toISOString(),
    },
  };
}

function parseFrontmatterAndBody(text) {
  if (!text.startsWith("---")) return { frontmatter: {}, body: text };
  const sepIdx = text.indexOf("\n---", 3);
  if (sepIdx === -1) return { frontmatter: {}, body: text };
  const fmText = text.slice(4, sepIdx);
  const afterSep = text.slice(sepIdx + 4);
  const newlineIdx = afterSep.indexOf("\n");
  const body = newlineIdx >= 0 ? afterSep.slice(newlineIdx + 1) : "";
  const values = {};
  for (const line of fmText.split(/\r?\n/)) {
    const colonIdx = line.indexOf(":");
    if (colonIdx === -1) continue;
    const key = line.slice(0, colonIdx).trim();
    const raw = line.slice(colonIdx + 1).trim();
    try {
      values[key] = JSON.parse(raw);
    } catch {
      values[key] = raw.replace(/^"|"$/g, "");
    }
  }
  return { frontmatter: values, body };
}

function parseEntrySections(body) {
  const matches = [...body.matchAll(/^##\s+(.+?)\s*$/gm)];
  return matches.map((m, idx) => {
    const start = m.index + m[0].length;
    const end = idx + 1 < matches.length ? matches[idx + 1].index : body.length;
    const cleaned = body.slice(start, end).replace(/<!--[\s\S]*?-->/g, "").trim();
    return {
      title: m[1].trim(),
      prompt: "Write what belongs here.",
      content: cleaned,
    };
  });
}

function localEntryCatalog() {
  const catalog = [];
  const seenSlugs = new Set();
  for (const row of readTracks(path.join(BASE, "tracks.csv"))) {
    const slug = slugify(`${row.artist || ""}-${row.track || ""}`);
    if (!slug || seenSlugs.has(slug)) continue;
    seenSlugs.add(slug);
    const hasEntry = fs.existsSync(path.join(ENTRIES_DIR, `${slug}.md`));
    const tags = String(row.tags || "")
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .filter(Boolean);
    catalog.push({
      signal_id: row.signal_id || "",
      slug,
      artist: row.artist || "",
      track: row.track || "",
      album: row.album || "",
      has_entry: hasEntry,
      is_p53: tags.includes("p53"),
    });
  }
  const configPath = path.join(BASE, "config.json");
  if (fs.existsSync(configPath)) {
    const config = loadConfig(configPath);
    for (const item of config.p53_history || []) {
      if (!item || typeof item !== "object") continue;
      const slug = item.slug || slugify(`${item.artist || ""}-${item.track || ""}`);
      if (!slug || seenSlugs.has(slug)) continue;
      seenSlugs.add(slug);
      catalog.push({
        signal_id: item.signal_id || "",
        slug,
        artist: item.artist || "",
        track: item.track || "",
        album: item.album || "",
        has_entry: fs.existsSync(path.join(ENTRIES_DIR, `${slug}.md`)),
        is_p53: true,
      });
    }
  }
  return catalog;
}

async function localEntryPayload(slug) {
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
    return { error: "invalid entry slug" };
  }
  const entryPath = path.join(ENTRIES_DIR, `${slug}.md`);
  const tracks = readTracks(path.join(BASE, "tracks.csv"));
  const row = tracks.find((item) => slugify(`${item.artist || ""}-${item.track || ""}`) === slug) || {};
  const config = loadConfig(path.join(BASE, "config.json"));
  const p53Records = (config.p53_history || []).filter((i) => i && typeof i === "object");
  const p53Record = p53Records.find((i) => i.slug === slug) || null;
  if (!fs.existsSync(entryPath) && !Object.keys(row).length && !p53Record) {
    return { error: "entry not found" };
  }

  let frontmatter = {};
  let body = "";
  if (fs.existsSync(entryPath)) {
    ({ frontmatter, body } = parseFrontmatterAndBody(fs.readFileSync(entryPath, "utf-8")));
  }
  const source = Object.keys(row).length ? row : p53Record || {};
  const artistName = String(frontmatter.artist || source.artist || "").trim();
  const trackName = String(frontmatter.track || source.track || "").trim();
  const albumName = String(frontmatter.album || source.album || "").trim();
  const signalId = String(source.signal_id || "").trim();
  const tags = String(source.tags || "").trim();
  const link = String(source.apple_url || source.spotify_url || "").trim();
  const rawCover = String(frontmatter.cover || source.cover_file || `${slug}.jpg`).trim();
  const coverName = path.basename(rawCover.replace(/\\/g, "/")) || `${slug}.jpg`;
  const coverUrl = String(source.cover_url || "").trim();
  const accent = String(frontmatter.accent || source.accent || "").trim();
  const sections = body ? parseEntrySections(body) : [];

  let palette = [];
  const candidateCover = [
    path.join(COVERS_DIR, coverName),
    path.join(SITE_DIR, "covers", coverName),
  ].find((p) => fs.existsSync(p));
  if (candidateCover) {
    palette = await extractPaletteSwatches(candidateCover, 5);
  }

  const p53Enabled =
    Boolean(p53Record) ||
    tags
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .includes("p53");
  const currentRecord = currentP53Record(config, p53Records);
  const artistNotes = config.artist_notes || {};
  const albumNotes = config.album_notes || {};

  return {
    payload: {
      schema: 1,
      record: {
        signal_id: signalId,
        artist: artistName,
        track: trackName,
        album: albumName,
        tags,
        link,
        slug,
        cover: coverName,
        cover_file: coverName,
        cover_url: coverUrl,
        accent,
      },
      sections,
      palette,
      p53: {
        enabled: p53Enabled,
        current: Boolean(p53Record && currentRecord && p53Record.slug === currentRecord.slug),
        note: String((config.p53_transmission_notes || {})[slug] || "").trim(),
      },
      catalogue: {
        artist_note: String(artistNotes[artistName] || "").trim(),
        album_note: String((albumNotes[artistName] && albumNotes[artistName][albumName]) || "").trim(),
      },
    },
  };
}

function timingSafeEqualStr(a, b) {
  if (!a || !b) return false;
  const bufA = Buffer.from(a);
  const bufB = Buffer.from(b);
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}

function guardPrivateAuth(req, res, next) {
  const expected = String(process.env.GSI_LOCAL_AUTH_TOKEN || "").trim();
  if (!expected) return next();

  const authHeader = String(req.headers.authorization || "");
  const bearer = authHeader.startsWith("Bearer ") ? authHeader.slice(7).trim() : "";
  if (timingSafeEqualStr(bearer, expected)) return next();

  const queryToken = String(req.query.token || "").trim();
  if (timingSafeEqualStr(queryToken, expected)) return next();

  const cookieHeader = String(req.headers.cookie || "");
  const cookieMatch = cookieHeader.match(/(?:^|;\s*)gsi_auth_token=([^;]+)/);
  if (cookieMatch && timingSafeEqualStr(decodeURIComponent(cookieMatch[1]).trim(), expected)) {
    return next();
  }

  res.setHeader("WWW-Authenticate", "Bearer");
  return res.status(401).json({ error: "private local authoring requires a bearer token" });
}

async function startServer() {
  await buildSite(BASE);

  const app = express();
  app.use(express.json({ limit: "8mb" }));

  // Public recommendation intake
  app.post("/api/recommendations", async (req, res) => {
    const { clean, error } = validateRecommendation(req.body);
    if (error) return res.status(400).json({ error });
    recommendationsMemory.push(clean);
    try {
      await fsp.mkdir(INBOX_DIR, { recursive: true });
      const filename = `${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
      await fsp.writeFile(
        path.join(INBOX_DIR, filename),
        JSON.stringify(clean, null, 2) + "\n",
        "utf-8"
      );
    } catch {
      // In-memory retention remains active even if disk write fails
    }
    return res.status(201).json({ status: "received" });
  });

  // Private local authoring routes
  app.get("/api/local-entry-catalog", guardPrivateAuth, (_req, res) => {
    return res.json({ entries: localEntryCatalog() });
  });

  app.get("/api/local-entry", guardPrivateAuth, (_req, res) => {
    return res.status(400).json({ error: "a slug is required" });
  });

  app.get("/api/local-entry/:slug", guardPrivateAuth, async (req, res) => {
    const { payload, error } = await localEntryPayload(req.params.slug);
    if (error) return res.status(404).json({ error });
    return res.json(payload);
  });

  app.post(["/api/entry-drafts", "/api/local-entry-drafts"], guardPrivateAuth, async (req, res) => {
    const payload = req.body;
    if (!payload || typeof payload !== "object" || !payload.record) {
      return res.status(400).json({ error: "invalid draft payload" });
    }
    const slug =
      slugify(`${payload.record.artist || ""}-${payload.record.track || ""}`) || "new-entry";
    const prefix = req.path === "/api/local-entry-drafts" ? "edit-" : "";
    const filename = `${new Date().toISOString().replace(/[:.]/g, "-")}-${prefix}${slug}.json`;
    try {
      await fsp.mkdir(DRAFTS_DIR, { recursive: true });
      await fsp.writeFile(
        path.join(DRAFTS_DIR, filename),
        JSON.stringify({ ...payload, receivedAt: new Date().toISOString() }, null, 2) + "\n",
        "utf-8"
      );
    } catch {
      // Fallback safely
    }
    return res.status(201).json({ status: "saved", filename });
  });

  app.post("/api/local-entry-publish", guardPrivateAuth, async (req, res) => {
    try {
      const result = await publishSignalsToArchive(BASE, req.body);
      return res.status(200).json(result);
    } catch (err) {
      return res.status(400).json({ error: err?.message || "publish failed" });
    }
  });

  // Private Heart Feedback local sync (from Firebase Owner Inbox -> local submissions/hearts-sync.json)
  app.get("/api/hearts/sync", guardPrivateAuth, async (_req, res) => {
    try {
      if (!fs.existsSync(HEARTS_SYNC_FILE)) {
        return res.json({ schema: 1, syncedAt: null, count: 0, records: [] });
      }
      const raw = JSON.parse(await fsp.readFile(HEARTS_SYNC_FILE, "utf-8"));
      return res.json(raw);
    } catch {
      return res.status(500).json({ error: "Could not read local hearts sync snapshot." });
    }
  });

  app.post("/api/hearts/sync", guardPrivateAuth, async (req, res) => {
    const body = req.body;
    if (!body || typeof body !== "object" || !Array.isArray(body.records)) {
      return res.status(400).json({ error: "Expected a payload with a records array." });
    }
    const cleanRecords = body.records.slice(0, 5000).map((r) => ({
      id: String(r?.id || "").slice(0, 180),
      slug: String(r?.slug || "").slice(0, 160),
      pageKind: r?.pageKind === "p53" ? "p53" : "entry",
      track: String(r?.track || "").slice(0, 180),
      artist: String(r?.artist || "").slice(0, 140),
      note: String(r?.note || "").slice(0, 600),
      senderName: String(r?.senderName || "").slice(0, 80),
      createdAt: r?.createdAt || null,
      updatedAt: r?.updatedAt || null,
    }));
    const snapshot = {
      schema: 1,
      syncedAt: new Date().toISOString(),
      count: cleanRecords.length,
      records: cleanRecords,
    };
    try {
      await fsp.mkdir(path.dirname(HEARTS_SYNC_FILE), { recursive: true });
      await fsp.writeFile(HEARTS_SYNC_FILE, JSON.stringify(snapshot, null, 2) + "\n", "utf-8");
      return res.status(200).json({
        status: "synced",
        count: cleanRecords.length,
        syncedAt: snapshot.syncedAt,
        file: "submissions/hearts-sync.json",
      });
    } catch (err) {
      return res.status(500).json({ error: err?.message || "Could not write local hearts sync file." });
    }
  });

  // Android LAN Sync & Metadata Lookup APIs
  app.get("/api/sync/ping", guardPrivateAuth, (_req, res) => {
    return res.json({
      status: "ok",
      service: "chaperone-lan-sync",
      schema: 2,
      timestamp: new Date().toISOString(),
    });
  });

  app.post("/api/lookup-link", guardPrivateAuth, async (req, res) => {
    const rawUrl = String(req.body?.url || req.body?.link || "").trim();
    if (!rawUrl) {
      return res.status(400).json({ error: "A music provider HTTPS URL is required." });
    }
    try {
      const metadata = await lookupMusicLink(rawUrl);
      return res.json({ status: "ok", metadata });
    } catch (err) {
      return res.status(400).json({ error: err?.message || "Metadata lookup failed." });
    }
  });

  app.get("/api/sync/bundle", guardPrivateAuth, async (_req, res) => {
    try {
      const bundle = await buildAndroidSyncBundle(BASE);
      return res.json(bundle);
    } catch (err) {
      return res.status(500).json({ error: err?.message || "Could not build sync bundle." });
    }
  });

  app.post("/api/sync/push", guardPrivateAuth, async (req, res) => {
    try {
      const result = await publishSignalsToArchive(BASE, req.body);
      return res.status(200).json(result);
    } catch (err) {
      return res.status(400).json({ error: err?.message || "Sync push failed." });
    }
  });

  app.get("/__local/editor/editor-config.json", guardPrivateAuth, (_req, res) => {
    const configPath = path.join(BASE, "config.json");
    const config = fs.existsSync(configPath) ? loadConfig(configPath) : {};
    return res.json({
      sections: config.sections || [],
      sectionInfo: config.section_info || {},
    });
  });

  app.use("/__local/editor", guardPrivateAuth, (req, res, next) => {
    if (req.method !== "GET") return next();
    if (req.originalUrl === "/__local/editor") {
      return res.redirect(301, "/__local/editor/");
    }
    const rel = String(req.path || "").replace(/^\/+/, "") || "edit-entry.html";
    const privateCandidate = path.resolve(EDITOR_DIR, "private", rel);
    const publicCandidate = path.resolve(EDITOR_DIR, rel);
    const resolvedRoot = path.resolve(EDITOR_DIR);
    let target = null;
    if (
      privateCandidate.startsWith(resolvedRoot + path.sep) &&
      fs.existsSync(privateCandidate) &&
      fs.statSync(privateCandidate).isFile()
    ) {
      target = privateCandidate;
    } else if (
      publicCandidate.startsWith(resolvedRoot + path.sep) &&
      fs.existsSync(publicCandidate) &&
      fs.statSync(publicCandidate).isFile()
    ) {
      target = publicCandidate;
    }
    if (!target) return res.status(404).json({ error: "not found" });
    const expected = String(process.env.GSI_LOCAL_AUTH_TOKEN || "").trim();
    if (expected) {
      res.setHeader("Set-Cookie", `gsi_auth_token=${expected}; Path=/; HttpOnly; SameSite=Lax`);
    }
    return res.sendFile(target);
  });

  // Static site serving
  app.use(
    express.static(SITE_DIR, {
      setHeaders: (res, filePath) => {
        if (filePath.endsWith(".html") || filePath.endsWith(".json")) {
          res.setHeader("Cache-Control", "no-cache, must-revalidate");
        }
      },
    })
  );

  // Fallback to source covers directory if a cover was referenced directly
  app.use("/covers", express.static(COVERS_DIR));

  // Custom 404 signal recovery room
  app.use((req, res) => {
    if (req.path.startsWith("/api/")) {
      return res.status(404).json({ error: "not found" });
    }
    const notFoundPath = path.join(SITE_DIR, "404.html");
    if (fs.existsSync(notFoundPath)) {
      return res.status(404).sendFile(notFoundPath);
    }
    return res.status(404).send("Not Found");
  });

  const port = Number(process.env.PORT) || 3000;
  app.listen(port, "0.0.0.0", () => {
    console.log(`[Chaperone] Dev server listening on http://0.0.0.0:${port}`);
  });
}

startServer().catch((err) => {
  console.error("[Chaperone] Failed to start server:", err);
  process.exit(1);
});
