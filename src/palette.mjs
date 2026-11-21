/**
 * Artwork color extraction, palette generation, image metadata, and asset copying.
 * Ported from gsi_assets.py using sharp for Node.js 22.
 */

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";

export const HOME_STYLE_PARTS = [
  "01-foundation.css",
  "02-hero-and-filter-room.css",
  "03-filter-and-controls.css",
  "04-cards-and-responsive.css",
];

function clampByte(value) {
  return Math.max(0, Math.min(255, Math.round(value)));
}

export function rgbToHex([r, g, b]) {
  return (
    "#" +
    [clampByte(r), clampByte(g), clampByte(b)]
      .map((c) => c.toString(16).padStart(2, "0"))
      .join("")
  );
}

function rgbToHsv(r, g, b) {
  const rn = r / 255;
  const gn = g / 255;
  const bn = b / 255;
  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const delta = max - min;
  let h = 0;
  if (delta !== 0) {
    if (max === rn) h = ((gn - bn) / delta) % 6;
    else if (max === gn) h = (bn - rn) / delta + 2;
    else h = (rn - gn) / delta + 4;
    h /= 6;
    if (h < 0) h += 1;
  }
  const s = max === 0 ? 0 : delta / max;
  return [h, s, max];
}

function mixRgb(first, second, amount) {
  return [
    Math.round(first[0] + (second[0] - first[0]) * amount),
    Math.round(first[1] + (second[1] - first[1]) * amount),
    Math.round(first[2] + (second[2] - first[2]) * amount),
  ];
}

function relativeLuminance(rgb) {
  const channels = rgb.map((value) => {
    const channel = value / 255;
    return channel <= 0.04045
      ? channel / 12.92
      : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(first, second) {
  const l1 = relativeLuminance(first);
  const l2 = relativeLuminance(second);
  const light = Math.max(l1, l2);
  const dark = Math.min(l1, l2);
  return (light + 0.05) / (dark + 0.05);
}

function bestInk(background) {
  const dark = [31, 20, 32];
  const light = [248, 245, 239];
  return contrastRatio(background, dark) >= contrastRatio(background, light)
    ? dark
    : light;
}

function capBrightness(rgb, maximum = 198) {
  const perceived = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000;
  if (perceived <= maximum) return rgb;
  const scale = maximum / perceived;
  return rgb.map((c) => Math.round(c * scale));
}

function parseHexColor(hex, fallback = [68, 68, 68]) {
  const raw = String(hex || "").replace(/^#/, "").trim();
  if (/^[0-9a-fA-F]{6}$/.test(raw)) {
    return [
      parseInt(raw.slice(0, 2), 16),
      parseInt(raw.slice(2, 4), 16),
      parseInt(raw.slice(4, 6), 16),
    ];
  }
  return fallback;
}

/**
 * Quantize an RGB buffer into histogram buckets (5-bit per channel) and return
 * the top `maxColors` average bucket colors with their pixel counts.
 */
function quantizeBuckets(buffer, maxColors = 18) {
  const buckets = new Map();
  for (let i = 0; i + 2 < buffer.length; i += 3) {
    const r = buffer[i];
    const g = buffer[i + 1];
    const b = buffer[i + 2];
    const key = ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3);
    let entry = buckets.get(key);
    if (!entry) {
      entry = { count: 0, r: 0, g: 0, b: 0 };
      buckets.set(key, entry);
    }
    entry.count += 1;
    entry.r += r;
    entry.g += g;
    entry.b += b;
  }
  return [...buckets.values()]
    .sort((a, b) => b.count - a.count)
    .slice(0, maxColors)
    .map((e) => [
      e.count,
      [Math.round(e.r / e.count), Math.round(e.g / e.count), Math.round(e.b / e.count)],
    ]);
}

const _dominantCache = new Map();
const _paletteCache = new Map();
const _metaCache = new Map();

export async function dominantColor(imagePath) {
  if (!imagePath || !fs.existsSync(imagePath)) return "#888888";
  const cacheKey = String(imagePath);
  if (_dominantCache.has(cacheKey)) return _dominantCache.get(cacheKey);
  try {
    const { data } = await sharp(imagePath)
      .resize(120, 120, { fit: "fill" })
      .removeAlpha()
      .raw()
      .toBuffer({ resolveWithObject: true });

    const colors = quantizeBuckets(data, 14);
    if (!colors.length) return "#888888";

    let bestColor = null;
    let bestScore = -1;
    for (const [count, [r, g, b]] of colors) {
      const [, s, v] = rgbToHsv(r, g, b);
      if (v < 0.18) continue;
      if (v > 0.94 && s < 0.25) continue;
      if (s < 0.18) continue;
      const score = (s * 2.4 + v * 0.8) * count ** 0.45;
      if (score > bestScore) {
        bestScore = score;
        bestColor = [r, g, b];
      }
    }
    if (!bestColor) {
      bestColor = colors[0][1];
    }
    const hex = rgbToHex(bestColor);
    _dominantCache.set(cacheKey, hex);
    return hex;
  } catch {
    return "#888888";
  }
}

export async function extractPaletteSwatches(imagePath, count = 5) {
  if (!imagePath || !fs.existsSync(imagePath)) return [];
  try {
    const { data } = await sharp(imagePath)
      .resize(80, 80, { fit: "fill" })
      .removeAlpha()
      .raw()
      .toBuffer({ resolveWithObject: true });
    const colors = quantizeBuckets(data, 16);
    const scored = colors.map(([freq, [r, g, b]]) => {
      const [, s, v] = rgbToHsv(r, g, b);
      const score =
        v > 0.15 && v < 0.95 && s > 0.12
          ? (s * 2.2 + v * 0.8) * freq ** 0.5
          : freq * 0.2;
      return { score, rgb: [r, g, b] };
    });
    scored.sort((a, b) => b.score - a.score);
    const palette = [];
    for (const { rgb } of scored) {
      const [r, g, b] = rgb;
      const hex = rgbToHex(rgb);
      const tooClose = palette.some((p) => {
        const pr = parseInt(p.slice(1, 3), 16);
        const pg = parseInt(p.slice(3, 5), 16);
        const pb = parseInt(p.slice(5, 7), 16);
        return Math.abs(r - pr) + Math.abs(g - pg) + Math.abs(b - pb) < 65;
      });
      if (!tooClose) palette.push(hex);
      if (palette.length >= count) break;
    }
    return palette;
  } catch {
    return [];
  }
}

function sampleRegionBuckets(data, width, height, x0, y0, x1, y1, maxColors = 12) {
  const buckets = new Map();
  const minX = Math.max(0, Math.min(width - 1, Math.floor(x0)));
  const maxX = Math.max(minX + 1, Math.min(width, Math.ceil(x1)));
  const minY = Math.max(0, Math.min(height - 1, Math.floor(y0)));
  const maxY = Math.max(minY + 1, Math.min(height, Math.ceil(y1)));
  for (let y = minY; y < maxY; y++) {
    for (let x = minX; x < maxX; x++) {
      const idx = (y * width + x) * 3;
      const r = data[idx];
      const g = data[idx + 1];
      const b = data[idx + 2];
      const key = ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3);
      let entry = buckets.get(key);
      if (!entry) {
        entry = { count: 0, r: 0, g: 0, b: 0 };
        buckets.set(key, entry);
      }
      entry.count += 1;
      entry.r += r;
      entry.g += g;
      entry.b += b;
    }
  }
  return [...buckets.values()]
    .sort((a, b) => b.count - a.count)
    .slice(0, maxColors)
    .map((e) => [
      e.count,
      [Math.round(e.r / e.count), Math.round(e.g / e.count), Math.round(e.b / e.count)],
    ]);
}

function buildRimGradientFromRaw(data, fallback) {
  const size = 96;
  const getPixel = (x, y) => {
    const cx = Math.max(0, Math.min(size - 1, x));
    const cy = Math.max(0, Math.min(size - 1, y));
    const idx = (cy * size + cx) * 3;
    return [data[idx], data[idx + 1], data[idx + 2]];
  };
  const weights = [0.48, 0.32, 0.2];
  const bandColor = (coords) => {
    const pixels = coords.map(([x, y]) => getPixel(x, y));
    return [0, 1, 2].map((ch) =>
      Math.round(pixels.reduce((acc, px, idx) => acc + px[ch] * weights[idx], 0))
    );
  };
  const points = [];
  for (let index = 0; index < 8; index++) {
    const position = 8 + index * 12;
    const top = bandColor([[position, 2], [position, 8], [position, 16]]);
    const right = bandColor([[93, position], [87, position], [79, position]]);
    const bottom = bandColor([[position, 93], [position, 87], [position, 79]]);
    const left = bandColor([[2, position], [8, position], [16, position]]);
    points.push([position, 3, mixRgb(top, fallback, 0.1)]);
    points.push([97, position, mixRgb(right, fallback, 0.1)]);
    points.push([position, 97, mixRgb(bottom, fallback, 0.1)]);
    points.push([3, position, mixRgb(left, fallback, 0.1)]);
  }
  return points
    .map(
      ([x, y, color]) =>
        `radial-gradient(ellipse at ${x}% ${y}%, color-mix(in srgb, ${rgbToHex(color)}, transparent 62%), transparent 52%)`
    )
    .join(",");
}

export function fallbackPalette(fallback = "#444444") {
  const fallbackRgb = parseHexColor(fallback);
  const primary = fallbackRgb;
  const secondary = mixRgb(primary, [255, 255, 255], 0.28);
  const field = primary;
  const fieldSoft = mixRgb(field, secondary, 0.38);
  const fieldInk = bestInk(field);
  const edges = { top: field, right: field, bottom: field, left: field };
  const rimGradient = `radial-gradient(ellipse at 50% 50%, color-mix(in srgb, ${rgbToHex(field)}, transparent 70%), transparent 58%)`;
  const lightSurface = capBrightness(mixRgb(primary, [255, 255, 255], 0.56));
  const lightSurface2 = capBrightness(mixRgb(secondary, [255, 255, 255], 0.56));
  const darkSurface = mixRgb(primary, [12, 12, 16], 0.62);
  const control = capBrightness(mixRgb(primary, [255, 255, 255], 0.64), 212);
  const controlHover = capBrightness(mixRgb(primary, [255, 255, 255], 0.5), 202);
  const lightInk = bestInk(lightSurface);
  const darkInk = bestInk(darkSurface);
  const sectionBackdrop = mixRgb(mixRgb(edges.left, edges.right, 0.5), field, 0.24);
  const sectionInk = bestInk(sectionBackdrop);
  const controlInk = bestInk(control);
  const focus = contrastRatio(primary, [31, 20, 32]) >= 3 ? [31, 20, 32] : [248, 245, 239];
  return {
    primary: rgbToHex(primary),
    secondary: rgbToHex(secondary),
    field: rgbToHex(field),
    field_soft: rgbToHex(fieldSoft),
    field_ink: rgbToHex(fieldInk),
    edge_top: rgbToHex(edges.top),
    edge_right: rgbToHex(edges.right),
    edge_bottom: rgbToHex(edges.bottom),
    edge_left: rgbToHex(edges.left),
    rim_gradient: rimGradient,
    surface: rgbToHex(mixRgb(primary, [10, 10, 14], 0.78)),
    soft: rgbToHex(mixRgb(primary, [255, 255, 255], 0.38)),
    ink: rgbToHex(darkInk),
    glow: rgbToHex(mixRgb(primary, secondary, 0.35)),
    light_surface: rgbToHex(lightSurface),
    light_surface_2: rgbToHex(lightSurface2),
    dark_surface: rgbToHex(darkSurface),
    light_ink: rgbToHex(lightInk),
    section_ink: rgbToHex(sectionInk),
    dark_ink: rgbToHex(darkInk),
    control: rgbToHex(control),
    control_hover: rgbToHex(controlHover),
    control_ink: rgbToHex(controlInk),
    edge: rgbToHex(mixRgb(primary, [255, 255, 255], 0.28)),
    focus: rgbToHex(focus),
  };
}

export async function artworkPalette(imagePath, fallback = "#444444") {
  if (!imagePath || !fs.existsSync(imagePath)) {
    return fallbackPalette(fallback);
  }
  const cacheKey = `${imagePath}::${fallback}`;
  if (_paletteCache.has(cacheKey)) return _paletteCache.get(cacheKey);

  const fallbackRgb = parseHexColor(fallback);
  let data = null;
  try {
    const res = await sharp(imagePath)
      .resize(96, 96, { fit: "fill" })
      .removeAlpha()
      .raw()
      .toBuffer({ resolveWithObject: true });
    data = res.data;
  } catch {
    return fallbackPalette(fallback);
  }

  const buckets = quantizeBuckets(data, 18);
  const scored = [];
  for (const [count, [r, g, b]] of buckets) {
    const [, saturation, value] = rgbToHsv(r, g, b);
    if (value > 0.95 && saturation < 0.2) continue;
    const score = (saturation * 2.2 + value * 0.7) * count ** 0.42;
    scored.push({ score: Math.round(score * 1000), rgb: [r, g, b] });
  }
  scored.sort((a, b) => b.score - a.score);

  const primary = scored.length ? scored[0].rgb : fallbackRgb;
  const secondaryMatch = scored
    .slice(1)
    .find(
      (entry) =>
        Math.abs(primary[0] - entry.rgb[0]) +
          Math.abs(primary[1] - entry.rgb[1]) +
          Math.abs(primary[2] - entry.rgb[2]) >
        80
    );
  const secondary = secondaryMatch
    ? secondaryMatch.rgb
    : mixRgb(primary, [255, 255, 255], 0.28);

  const lowerBuckets = sampleRegionBuckets(data, 96, 96, 0, Math.round(96 * 0.72), 96, 96, 12);
  const fieldRaw = lowerBuckets.length ? lowerBuckets[0][1] : primary;
  const field = mixRgb(fieldRaw, primary, 0.45);
  const fieldSoft = mixRgb(field, secondary, 0.38);
  const fieldInk = bestInk(field);

  const band = Math.max(1, Math.round(96 * 0.12));
  const edgeSample = (x0, y0, x1, y1) => {
    const b = sampleRegionBuckets(data, 96, 96, x0, y0, x1, y1, 8);
    return b.length ? b[0][1] : field;
  };
  const edges = {
    top: edgeSample(0, 0, 96, band),
    right: edgeSample(96 - band, 0, 96, 96),
    bottom: edgeSample(0, 96 - band, 96, 96),
    left: edgeSample(0, 0, band, 96),
  };

  const rimGradient = buildRimGradientFromRaw(data, field);
  const lightSurface = capBrightness(mixRgb(primary, [255, 255, 255], 0.56));
  const lightSurface2 = capBrightness(mixRgb(secondary, [255, 255, 255], 0.56));
  const darkSurface = mixRgb(primary, [12, 12, 16], 0.62);
  const control = capBrightness(mixRgb(primary, [255, 255, 255], 0.64), 212);
  const controlHover = capBrightness(mixRgb(primary, [255, 255, 255], 0.5), 202);
  const lightInk = bestInk(lightSurface);
  const darkInk = bestInk(darkSurface);
  const sectionBackdrop = mixRgb(mixRgb(edges.left, edges.right, 0.5), field, 0.24);
  const sectionInk = bestInk(sectionBackdrop);
  const controlInk = bestInk(control);
  const focus = contrastRatio(primary, [31, 20, 32]) >= 3 ? [31, 20, 32] : [248, 245, 239];

  const palette = {
    primary: rgbToHex(primary),
    secondary: rgbToHex(secondary),
    field: rgbToHex(field),
    field_soft: rgbToHex(fieldSoft),
    field_ink: rgbToHex(fieldInk),
    edge_top: rgbToHex(edges.top),
    edge_right: rgbToHex(edges.right),
    edge_bottom: rgbToHex(edges.bottom),
    edge_left: rgbToHex(edges.left),
    rim_gradient: rimGradient,
    surface: rgbToHex(mixRgb(primary, [10, 10, 14], 0.78)),
    soft: rgbToHex(mixRgb(primary, [255, 255, 255], 0.38)),
    ink: rgbToHex(darkInk),
    glow: rgbToHex(mixRgb(primary, secondary, 0.35)),
    light_surface: rgbToHex(lightSurface),
    light_surface_2: rgbToHex(lightSurface2),
    dark_surface: rgbToHex(darkSurface),
    light_ink: rgbToHex(lightInk),
    section_ink: rgbToHex(sectionInk),
    dark_ink: rgbToHex(darkInk),
    control: rgbToHex(control),
    control_hover: rgbToHex(controlHover),
    control_ink: rgbToHex(controlInk),
    edge: rgbToHex(mixRgb(primary, [255, 255, 255], 0.28)),
    focus: rgbToHex(focus),
  };
  _paletteCache.set(cacheKey, palette);
  return palette;
}

export function compactRimGradient(palette) {
  const p = palette || {};
  const stops = [
    ["edge_top", "50%", "0%"],
    ["edge_right", "100%", "50%"],
    ["edge_bottom", "50%", "100%"],
    ["edge_left", "0%", "50%"],
  ];
  return stops
    .map(
      ([key, x, y]) =>
        `radial-gradient(ellipse at ${x} ${y}, color-mix(in srgb, ${p[key] || p.field || "#17151b"}, transparent 62%), transparent 52%)`
    )
    .join(",");
}

export function paletteStyle(palette, imageSrc = "", { rimGradient = null } = {}) {
  const p = palette || fallbackPalette();
  const values = {
    "--art-primary": p.primary || "#444444",
    "--art-secondary": p.secondary || "#888888",
    "--art-field": p.field || p.surface || "#17151b",
    "--art-field-soft": p.field_soft || p.secondary || "#888888",
    "--art-field-ink": p.field_ink || p.ink || "#f8f5ef",
    "--art-edge-top": p.edge_top || p.field || "#17151b",
    "--art-edge-right": p.edge_right || p.field || "#17151b",
    "--art-edge-bottom": p.edge_bottom || p.field || "#17151b",
    "--art-edge-left": p.edge_left || p.field || "#17151b",
    "--art-rim-gradient": rimGradient !== null ? rimGradient : p.rim_gradient || "",
    "--art-section-rim-gradient": compactRimGradient(p),
    "--art-card-rim-gradient": compactRimGradient(p),
    "--art-surface": p.surface || "#17151b",
    "--art-soft": p.soft || "#aaaaaa",
    "--art-ink": p.ink || "#f8f5ef",
    "--art-glow": p.glow || "#666666",
    "--art-light-surface": p.light_surface || "#ded9df",
    "--art-light-surface-2": p.light_surface_2 || "#ded9df",
    "--art-dark-surface": p.dark_surface || "#17151b",
    "--art-light-ink": p.light_ink || "#1f1420",
    "--art-section-ink": p.section_ink || p.light_ink || "#1f1420",
    "--art-dark-ink": p.dark_ink || "#f8f5ef",
    "--art-control": p.control || "#c7b0c6",
    "--art-control-hover": p.control_hover || "#b897b5",
    "--art-control-ink": p.control_ink || "#1f1420",
    "--art-edge": p.edge || "#c7b0c6",
    "--art-focus": p.focus || "#f8f5ef",
  };
  if (imageSrc) {
    values["--art-image"] = `url("${String(imageSrc).replace(/"/g, "")}")`;
  }
  return Object.entries(values)
    .map(([k, v]) => `${k}:${v}`)
    .join(";") + ";";
}

export async function localImageMetadata(imagePath) {
  if (!imagePath || !fs.existsSync(imagePath)) {
    return { exists: false, valid: false, width: null, height: null, bytes: null };
  }
  const key = String(imagePath);
  if (_metaCache.has(key)) return _metaCache.get(key);
  try {
    const stat = await fsp.stat(imagePath);
    if (!stat.isFile()) {
      return { exists: false, valid: false, width: null, height: null, bytes: null };
    }
    const meta = await sharp(imagePath).metadata();
    const record = {
      exists: true,
      valid: Boolean(meta.width && meta.height),
      width: meta.width || null,
      height: meta.height || null,
      bytes: stat.size,
    };
    _metaCache.set(key, record);
    return record;
  } catch {
    return { exists: true, valid: false, width: null, height: null, bytes: null };
  }
}

export async function imageSizeAttrs(imagePath, defaultWidth = 600, defaultHeight = 600) {
  if (!imagePath) return `width="${defaultWidth}" height="${defaultHeight}"`;
  const meta = await localImageMetadata(imagePath);
  const w = meta.width || defaultWidth;
  const h = meta.height || defaultHeight;
  return `width="${w}" height="${h}"`;
}

export async function playlistVisuals(playlistCover, fallbackColor, baseDir) {
  const cover = String(playlistCover || "").trim();
  if (!cover) return ["", fallbackColor];
  const coverPath = path.join(baseDir, cover);
  if (!fs.existsSync(coverPath)) return ["", fallbackColor];
  const browserSrc = cover.replace(/\\/g, "/");
  return [browserSrc, await dominantColor(coverPath)];
}

export async function copyDirFresh(srcDir, destDir) {
  if (fs.existsSync(destDir)) {
    await fsp.rm(destDir, { recursive: true, force: true });
  }
  if (fs.existsSync(srcDir)) {
    await fsp.cp(srcDir, destDir, { recursive: true });
  } else {
    await fsp.mkdir(destDir, { recursive: true });
  }
}

export async function copySiteCovers(coversDir, siteCoversDir, referencedFiles = null) {
  if (fs.existsSync(siteCoversDir)) {
    await fsp.rm(siteCoversDir, { recursive: true, force: true });
  }
  await fsp.mkdir(siteCoversDir, { recursive: true });
  if (!fs.existsSync(coversDir)) return;
  const entries = await fsp.readdir(coversDir, { withFileTypes: true });
  for (const entry of entries) {
    if (!entry.isFile()) continue;
    if (referencedFiles && !referencedFiles.has(entry.name)) continue;
    await fsp.copyFile(path.join(coversDir, entry.name), path.join(siteCoversDir, entry.name));
  }
  const p53Source = path.join(coversDir, "P53_cover.jpg");
  if (fs.existsSync(p53Source)) {
    try {
      await sharp(p53Source)
        .resize(1200, 1200, { fit: "inside", withoutEnlargement: true })
        .jpeg({ quality: 84, mozjpeg: false })
        .toFile(path.join(siteCoversDir, "P53_cover-og.jpg"));
    } catch {
      // Non-fatal
    }
  }
}

export async function copySiteScripts(webDir, siteScriptsDir) {
  await fsp.mkdir(siteScriptsDir, { recursive: true });
  const scriptsDir = path.join(webDir, "scripts");
  const expected = new Set();
  if (fs.existsSync(scriptsDir)) {
    for (const file of await fsp.readdir(scriptsDir)) {
      if (file.endsWith(".js")) {
        expected.add(file);
        await fsp.copyFile(path.join(scriptsDir, file), path.join(siteScriptsDir, file));
      }
    }
  }
  for (const file of await fsp.readdir(siteScriptsDir)) {
    if (file.endsWith(".js") && !expected.has(file)) {
      await fsp.unlink(path.join(siteScriptsDir, file));
    }
  }
}

export async function copySiteStyles(webDir, siteStylesDir) {
  await fsp.mkdir(siteStylesDir, { recursive: true });
  const stylesDir = path.join(webDir, "styles");
  const expected = new Set(["gsi-home.css"]);
  if (fs.existsSync(stylesDir)) {
    for (const file of await fsp.readdir(stylesDir)) {
      if (file.endsWith(".css")) {
        expected.add(file);
        await fsp.copyFile(path.join(stylesDir, file), path.join(siteStylesDir, file));
      }
    }
  }
  for (const file of await fsp.readdir(siteStylesDir)) {
    if (file.endsWith(".css") && !expected.has(file)) {
      await fsp.unlink(path.join(siteStylesDir, file));
    }
  }
  const homePartsDir = path.join(stylesDir, "home");
  if (fs.existsSync(homePartsDir)) {
    const parts = [];
    for (const partName of HOME_STYLE_PARTS) {
      const partPath = path.join(homePartsDir, partName);
      if (!fs.existsSync(partPath)) {
        throw new Error(`Missing homepage style part: ${partPath}`);
      }
      parts.push((await fsp.readFile(partPath, "utf-8")).trimEnd());
    }
    const assembled =
      "/* Generated from web/styles/home/*.css in HOME_STYLE_PARTS order. */\n" +
      parts.join("\n\n") +
      "\n";
    await fsp.writeFile(path.join(siteStylesDir, "gsi-home.css"), assembled, "utf-8");
  }
}
