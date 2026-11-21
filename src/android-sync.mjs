/**
 * Pure Node.js Android asset sync and review exporter for Chaperone (GSI).
 * Replaces legacy Python Gradle hooks (`sync_android_assets.py` and `export_android_reviews.py`).
 *
 * Usage:
 *   node src/android-sync.mjs --sync-assets [--root <dir>]
 *   node src/android-sync.mjs --export-reviews --catalog <path> --entries <path> --output <path>
 */

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  currentP53Slug,
  extractSectionsFromMarkdown,
  loadConfig,
  slugify,
} from "./gsi-core.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
export const BASE = path.resolve(__dirname, "..");

function parseArgs(argv) {
  const args = { mode: "" };
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (token === "--sync-assets") args.mode = "sync-assets";
    else if (token === "--export-reviews") args.mode = "export-reviews";
    else if (token === "--root" && argv[i + 1]) args.root = argv[++i];
    else if (token === "--catalog" && argv[i + 1]) args.catalog = argv[++i];
    else if (token === "--entries" && argv[i + 1]) args.entries = argv[++i];
    else if (token === "--output" && argv[i + 1]) args.output = argv[++i];
  }
  return args;
}

export async function syncAndroidAssets(rootDir = BASE) {
  const siteCatalogPath = path.join(rootDir, "site", "data", "catalog.json");
  const configPath = path.join(rootDir, "config.json");
  const enrichmentPath = path.join(rootDir, "data", "signal_enrichment.json");
  const coversSourceDir = path.join(rootDir, "covers");

  const androidAssetsDir = path.join(rootDir, "android", "app", "src", "main", "assets");
  const androidDataDir = path.join(androidAssetsDir, "data");
  const androidCoversDir = path.join(androidAssetsDir, "covers");

  if (!fs.existsSync(siteCatalogPath)) {
    throw new Error(`Site catalog not found at ${siteCatalogPath}. Run 'npm run build' first.`);
  }

  await fsp.mkdir(androidDataDir, { recursive: true });
  await fsp.mkdir(androidCoversDir, { recursive: true });

  const catalog = JSON.parse(await fsp.readFile(siteCatalogPath, "utf-8"));
  const enrichment = fs.existsSync(enrichmentPath)
    ? JSON.parse(await fsp.readFile(enrichmentPath, "utf-8"))
    : {};
  const config = fs.existsSync(configPath) ? loadConfig(configPath) : {};

  // Enrich catalog signals with 30s PEEK preview URLs and release year for native playback
  const enrichedSignals = (catalog.signals || []).map((signal) => {
    const slug = String(signal.slug || "");
    const enr = enrichment[slug] || {};
    return {
      ...signal,
      preview_url: signal.preview_url || enr.preview_url || "",
      release_year: signal.release_year || enr.release_year || "",
    };
  });

  await fsp.writeFile(
    path.join(androidDataDir, "catalog.json"),
    JSON.stringify({ ...catalog, signals: enrichedSignals }, null, 2) + "\n",
    "utf-8"
  );

  // Sync P53 config for Android Hero, Share Card Studio, and Glance Widget
  const p53History = Array.isArray(config.p53_history) ? config.p53_history : [];
  const p53Payload = {
    p53_current_slug: currentP53Slug(config, p53History) || config.p53_current_slug || "",
    p53_about: config.p53_about || "",
    p53_history: p53History,
    p53_transmission_notes: config.p53_transmission_notes || {},
    site_url: config.site_url || "",
  };
  await fsp.writeFile(
    path.join(androidDataDir, "p53_config.json"),
    JSON.stringify(p53Payload, null, 2) + "\n",
    "utf-8"
  );

  // Copy referenced covers + P53 protein art into Android assets
  const wantedCovers = new Set(["P53_cover.jpg", "P53_cover-runtime.webp"]);
  for (const signal of enrichedSignals) {
    const rawPath = String(signal?.cover?.path || "").trim();
    if (rawPath) wantedCovers.add(path.basename(rawPath));
  }
  for (const item of p53History) {
    if (item?.cover_file) wantedCovers.add(path.basename(item.cover_file));
  }

  let copiedCount = 0;
  for (const coverName of wantedCovers) {
    const src = path.join(coversSourceDir, coverName);
    if (!fs.existsSync(src)) continue;
    const dst = path.join(androidCoversDir, coverName);
    let shouldCopy = true;
    if (fs.existsSync(dst)) {
      const [srcStat, dstStat] = await Promise.all([fsp.stat(src), fsp.stat(dst)]);
      if (srcStat.size === dstStat.size && srcStat.mtimeMs <= dstStat.mtimeMs) {
        shouldCopy = false;
      }
    }
    if (shouldCopy) {
      await fsp.copyFile(src, dst);
      copiedCount++;
    }
  }

  console.log(
    `[Chaperone] Synced Android assets: ${enrichedSignals.length} signals, ${copiedCount} covers updated.`
  );
}

export async function exportAndroidReviews({ catalogPath, entriesDir, outputPath }) {
  if (!fs.existsSync(catalogPath)) {
    throw new Error(`Catalog not found at ${catalogPath}`);
  }
  const catalog = JSON.parse(await fsp.readFile(catalogPath, "utf-8"));
  const reviewsById = {};
  const reviewsBySlug = {};

  for (const signal of catalog.signals || []) {
    const slug = String(signal.slug || slugify(`${signal.artist || ""}-${signal.track || ""}`));
    const signalId = String(signal.signal_id || slug);
    if (!slug) continue;
    const mdPath = path.join(entriesDir, `${slug}.md`);
    if (!fs.existsSync(mdPath)) continue;

    const sections = extractSectionsFromMarkdown(mdPath)
      .filter((s) => String(s.content || "").trim().length > 0)
      .map((s) => ({
        title: String(s.title || "").trim(),
        content: String(s.content || "").trim(),
      }));

    if (sections.length > 0) {
      reviewsById[signalId] = sections;
      reviewsBySlug[slug] = sections;
    }
  }

  await fsp.mkdir(path.dirname(outputPath), { recursive: true });
  await fsp.writeFile(
    outputPath,
    JSON.stringify(
      {
        schema: 1,
        reviews: reviewsById,
        reviewsBySlug,
      },
      null,
      2
    ) + "\n",
    "utf-8"
  );

  console.log(
    `[Chaperone] Exported Android reviews: ${Object.keys(reviewsById).length} entries -> ${outputPath}`
  );
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const rootDir = path.resolve(args.root || BASE);
  if (args.mode === "sync-assets") {
    await syncAndroidAssets(rootDir);
  } else if (args.mode === "export-reviews") {
    const catalogPath = path.resolve(
      args.catalog || path.join(rootDir, "android", "app", "src", "main", "assets", "data", "catalog.json")
    );
    const entriesDir = path.resolve(args.entries || path.join(rootDir, "entries"));
    const outputPath = path.resolve(
      args.output || path.join(rootDir, "android", "app", "src", "main", "assets", "data", "reviews.json")
    );
    await exportAndroidReviews({ catalogPath, entriesDir, outputPath });
  } else {
    // Default: sync both assets and bundled reviews.json
    await syncAndroidAssets(rootDir);
    await exportAndroidReviews({
      catalogPath: path.join(rootDir, "android", "app", "src", "main", "assets", "data", "catalog.json"),
      entriesDir: path.join(rootDir, "entries"),
      outputPath: path.join(rootDir, "android", "app", "src", "main", "assets", "data", "reviews.json"),
    });
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  main().catch((err) => {
    console.error("[Chaperone] Android sync failed:", err);
    process.exit(1);
  });
}
