/*
 * Permanent Radio P53 transmission route and sharing behavior.
 * This page receives a small JSON context object; the helper uses it to expose
 * real return paths and the least surprising sharing fallback.
 */
(() => {
  const contextNode = document.querySelector("#p53-transmission-context");
  if (!contextNode || !window.GSIContext) return;

  let context;
  try {
    context = JSON.parse(contextNode.textContent || "{}");
  } catch {
    return;
  }

  // Apply the per-page accent at runtime so the template stays free of
  // page-specific style attributes.
  if (context.accent) document.body.style.setProperty("--accent", context.accent);

  const filterLabels = context.filterLabels || {};
  const expectedArtistRoute = context.expectedArtistRoute || "";
  const artistName = context.artistName || "";

  function setRouteLinks(selector, params) {
    document.querySelectorAll(selector).forEach(link => {
      if (!link) return;
      const rawHref = (typeof link.getAttribute === "function" ? link.getAttribute("href") : "") || link.href || "";
      const baseHref = (link.dataset && link.dataset.routeBaseHref) || String(rawHref).split("?")[0];
      if (!baseHref) return;
      if (link.dataset) link.dataset.routeBaseHref = baseHref;
      link.href = params.size ? `${baseHref}?${params}` : baseHref;
    });
  }

  function syncLinks() {
    const archiveState = GSIContext.read();
    const artistRoute = archiveState.get("artist");
    const archiveParams = GSIContext.archiveParams({ state: archiveState, filterLabels });
    const archiveHref = GSIContext.href("../index.html", archiveParams);

    document.querySelectorAll("#p53-trace-archive").forEach(link => { link.href = archiveHref; });

    const p53IndexLink = document.querySelector("#p53-radio-index");
    if (p53IndexLink) {
      const p53IndexParams = new URLSearchParams(archiveParams);
      if (artistRoute === expectedArtistRoute) p53IndexParams.set("artist", artistRoute);
      p53IndexLink.href = `index.html${p53IndexParams.size ? `?${p53IndexParams}` : ""}`;
    }

    // Filter context stays in #p53-trace-archive and #p53-radio-index links while
    // omitting the filter segment from the factor breadcrumb bar.
    const traceArtist = document.querySelector("#p53-trace-artist");
    const traceArtistSep = document.querySelector("#p53-trace-artist-separator");
    if (artistRoute === expectedArtistRoute) {
      if (traceArtist) {
        traceArtist.textContent = artistName.toUpperCase();
        traceArtist.href = `../artists/${artistRoute}.html${archiveParams.size ? `?${archiveParams}` : ""}`;
        traceArtist.classList.remove("hidden");
        traceArtistSep?.classList.remove("hidden");
      }
    } else if (traceArtist) {
      traceArtist.classList.add("hidden");
      traceArtistSep?.classList.add("hidden");
    }

    const routeParams = new URLSearchParams(archiveParams);
    if (artistRoute === expectedArtistRoute) routeParams.set("artist", artistRoute);
    setRouteLinks(".artist-link", archiveParams);
    setRouteLinks(".entry-counterpart, .album-link", routeParams);
  }

  syncLinks();
  window.addEventListener?.("gsi-theme-change", syncLinks);

  // Story Card generator & native mobile sharing controller.
  const shareButton = document.querySelector("#share-transmission");
  const storyModal = document.querySelector("#story-modal");
  const modalClose = document.querySelector("#story-modal-close");
  const btnShare = document.querySelector("#story-btn-share");
  const btnCopyImage = document.querySelector("#story-btn-copy-image");
  const btnDownload = document.querySelector("#story-btn-download");
  const btnCopy = document.querySelector("#story-btn-copy");
  const stylePaperBtn = document.querySelector("#story-style-paper");
  const styleDarkBtn = document.querySelector("#story-style-dark");
  const quoteChipsWrap = document.querySelector("#story-quote-chips");
  const quoteInput = document.querySelector("#story-quote-input");
  const gradientSlider = document.querySelector("#story-gradient-slider");
  const gradientValue = document.querySelector("#story-gradient-value");
  const coverSlider = document.querySelector("#story-cover-slider");
  const coverValue = document.querySelector("#story-cover-value");
  const watermarkToggle = document.querySelector("#story-watermark-toggle");
  const storyStatus = document.querySelector("#story-status");
  const canvas = document.querySelector("#story-card-canvas");

  let cardRendered = false;
  let studioStyle = "paper";
  let studioNoteOverride = null;
  let studioGradientIntensity = Number(gradientSlider?.value ?? 65);
  let studioCoverScale = Number(coverSlider?.value ?? 80);
  let studioWatermark = watermarkToggle
    ? watermarkToggle.getAttribute?.("aria-checked") !== "false"
    : true;

  function syncSliderFill(slider) {
    if (!slider || !slider.style?.setProperty) return;
    const min = Number(slider.min ?? 0);
    const max = Number(slider.max ?? 100);
    const val = Number(slider.value ?? min);
    const pct = max > min ? Math.max(0, Math.min(100, ((val - min) / (max - min)) * 100)) : 0;
    slider.style.setProperty("--slider-pct", `${pct.toFixed(1)}%`);
  }

  function parseHex(hex, fallback = [255, 101, 173]) {
    if (Array.isArray(hex) && hex.length === 3) return hex;
    if (!hex || typeof hex !== "string") return fallback;
    let clean = hex.replace("#", "").trim();
    if (clean.length === 3) clean = clean.split("").map(c => c + c).join("");
    if (!/^[0-9a-fA-F]{6}$/.test(clean)) return fallback;
    return [
      parseInt(clean.substring(0, 2), 16),
      parseInt(clean.substring(2, 4), 16),
      parseInt(clean.substring(4, 6), 16),
    ];
  }

  function toHex(rgb) {
    return "#" + rgb.map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("");
  }

  function hexToRgba(hex, alpha) {
    const [r, g, b] = parseHex(hex);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function mixRgb(first, second, amount) {
    return first.map((channel, index) => Math.round(channel + (second[index] - channel) * amount));
  }

  function relativeLuminance(rgb) {
    const [r, g, b] = rgb.map(value => {
      const channel = value / 255;
      return channel <= 0.04045 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  function contrastRatio(first, second) {
    const l1 = relativeLuminance(first);
    const l2 = relativeLuminance(second);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  }

  function ensureContrast(fgRgb, bgRgb, targetRgb, minRatio) {
    if (contrastRatio(fgRgb, bgRgb) >= minRatio) return fgRgb;
    for (let step = 1; step <= 10; step++) {
      const candidate = mixRgb(fgRgb, targetRgb, step / 10);
      if (contrastRatio(candidate, bgRgb) >= minRatio) return candidate;
    }
    return targetRgb;
  }

  function deriveSleevePalette(ctxData, styleMode = "paper", gradientScale = 0.65) {
    const g = Math.max(0, Math.min(1, Number(gradientScale)));
    const curve = g > 0 ? Math.pow(g, 0.85) : 0;
    const palette = ctxData.trackPalette || {};
    const primary = parseHex(palette.primary || ctxData.trackAccent || "#ff65ad");
    const secondary = parseHex(palette.secondary || toHex(mixRgb(primary, [86, 74, 102], 0.45)));
    const glow = parseHex(palette.glow || toHex(mixRgb(primary, secondary, 0.35)));
    const field = parseHex(palette.field || toHex(mixRgb(primary, [24, 18, 30], 0.68)));
    const soft = parseHex(palette.soft || toHex(mixRgb(primary, [245, 239, 226], 0.52)));
    const surface = parseHex(palette.surface || toHex(mixRgb(primary, [16, 12, 22], 0.78)));
    const rawInk = palette.ink ? parseHex(palette.ink, [25, 19, 30]) : null;

    if (styleMode === "dark") {
      const darkTopRgb = mixRgb([20, 17, 26], mixRgb(surface, primary, 0.44), 0.78 * curve);
      const darkMidRgb = mixRgb([15, 13, 21], primary, 0.54 * curve);
      const darkBottomRgb = mixRgb([10, 9, 15], secondary, 0.62 * curve);
      const darkNoteRgb = mixRgb([24, 20, 32], surface, 0.45 * curve);
      const lightInk = [248, 245, 239];
      const mutedLight = ensureContrast(mixRgb(lightInk, soft, 0.32), darkMidRgb, lightInk, 5.2);
      const accentLight = ensureContrast(primary, darkMidRgb, [255, 196, 226], 4.4);
      return {
        primary: toHex(primary),
        secondary: toHex(secondary),
        glow: toHex(glow),
        field: toHex(field),
        soft: toHex(soft),
        surface: toHex(surface),
        outerTop: toHex(mixRgb([10, 8, 14], primary, 0.68 * curve)),
        outerBottom: toHex(mixRgb([7, 5, 10], secondary, 0.56 * curve)),
        spineBg: toHex(mixRgb(surface, [24, 15, 32], 0.55)),
        paperTop: toHex(darkTopRgb),
        paperMid: toHex(darkMidRgb),
        paperBottom: toHex(darkBottomRgb),
        noteBg: toHex(darkNoteRgb),
        inkPrimary: toHex(lightInk),
        inkMuted: toHex(mutedLight),
        accentRule: toHex(accentLight),
        p53Accent: toHex(parseHex(ctxData.p53Accent || "#ff58a6")),
        cyanAccent: toHex(parseHex(ctxData.cyanAccent || "#35c9e9")),
      };
    }

    // Expressive LIT sleeve: crisp archival paper at 0%, unmistakable vivid album wash at 100%
    // while keeping top stop luminous so light-mode readability and warmth stay intact.
    const litTopTint = mixRgb(soft, [255, 251, 246], 0.3);
    const litMidTint = mixRgb(primary, [252, 246, 239], 0.24);
    const litBottomTint = mixRgb(mixRgb(field, secondary, 0.48), [248, 242, 234], 0.2);
    const paperTopRgb = mixRgb([249, 245, 238], litTopTint, 0.36 * curve);
    const paperMidRgb = mixRgb([243, 237, 226], litMidTint, 0.48 * curve);
    const paperBottomRgb = mixRgb([236, 228, 214], litBottomTint, 0.56 * curve);
    const noteBgRgb = mixRgb([253, 250, 245], soft, 0.14 * curve);

    const darkFallback = [23, 17, 29];
    const tintedDark = mixRgb(surface, darkFallback, 0.8);
    const inkPrimaryRgb = (rawInk && contrastRatio(rawInk, paperMidRgb) >= 7.0)
      ? rawInk
      : ensureContrast(tintedDark, paperMidRgb, darkFallback, 8.5);
    const inkMutedRgb = ensureContrast(mixRgb(inkPrimaryRgb, primary, 0.24), paperMidRgb, inkPrimaryRgb, 5.2);
    const accentRuleRgb = ensureContrast(primary, paperMidRgb, inkPrimaryRgb, 3.6);

    return {
      primary: toHex(primary),
      secondary: toHex(secondary),
      glow: toHex(glow),
      field: toHex(field),
      soft: toHex(soft),
      surface: toHex(surface),
      outerTop: toHex(mixRgb([16, 12, 21], primary, 0.62 * curve)),
      outerBottom: toHex(mixRgb([11, 8, 16], secondary, 0.52 * curve)),
      spineBg: toHex(mixRgb(surface, [32, 20, 40], 0.45)),
      paperTop: toHex(paperTopRgb),
      paperMid: toHex(paperMidRgb),
      paperBottom: toHex(paperBottomRgb),
      noteBg: toHex(noteBgRgb),
      inkPrimary: toHex(inkPrimaryRgb),
      inkMuted: toHex(inkMutedRgb),
      accentRule: toHex(accentRuleRgb),
      p53Accent: toHex(parseHex(ctxData.p53Accent || "#ff58a6")),
      cyanAccent: toHex(parseHex(ctxData.cyanAccent || "#35c9e9")),
    };
  }

  function drawRoundRect(ctx, x, y, width, height, radius) {
    if (typeof ctx.roundRect === "function") {
      ctx.beginPath();
      ctx.roundRect(x, y, width, height, radius);
      return;
    }
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.arcTo(x + width, y, x + width, y + radius, radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.arcTo(x + width, y + height, x + width - radius, y + height, radius);
    ctx.lineTo(x + radius, y + height);
    ctx.arcTo(x, y + height, x, y + height - radius, radius);
    ctx.lineTo(x, y + radius);
    ctx.arcTo(x, y, x + radius, y, radius);
    ctx.closePath();
  }

  function drawAsymmRoundRect(ctx, x, y, width, height, rTL, rTR, rBR, rBL) {
    ctx.beginPath();
    ctx.moveTo(x + rTL, y);
    ctx.lineTo(x + width - rTR, y);
    ctx.arcTo(x + width, y, x + width, y + rTR, rTR);
    ctx.lineTo(x + width, y + height - rBR);
    ctx.arcTo(x + width, y + height, x + width - rBR, y + height, rBR);
    ctx.lineTo(x + rBL, y + height);
    ctx.arcTo(x, y + height, x, y + height - rBL, rBL);
    ctx.lineTo(x, y + rTL);
    ctx.arcTo(x, y, x + rTL, y, rTL);
    ctx.closePath();
  }

  function measureWrappedLines(ctx, text, maxWidth, maxLines) {
    const words = (text || "").trim().split(/\s+/).filter(Boolean);
    const lines = [];
    let line = "";
    for (const word of words) {
      let remaining = word;
      while (remaining) {
        const candidate = line ? line + " " + remaining : remaining;
        if (ctx.measureText(candidate).width <= maxWidth) {
          line = candidate;
          break;
        }
        if (line) {
          lines.push(line);
          line = "";
          continue;
        }
        let piece = "";
        const chars = Array.from(remaining);
        while (chars.length && ctx.measureText(piece + chars[0]).width <= maxWidth) {
          piece += chars.shift();
        }
        if (!piece) piece = chars.shift() || "";
        lines.push(piece);
        remaining = chars.join("");
      }
    }
    if (line) lines.push(line);
    const truncated = lines.length > maxLines;
    const visible = lines.slice(0, maxLines);
    if (truncated && visible.length) {
      let last = visible[visible.length - 1];
      while (last && ctx.measureText(last + "…").width > maxWidth) last = Array.from(last).slice(0, -1).join("");
      visible[visible.length - 1] = last + "…";
    }
    return { lines: visible, truncated };
  }

  function paintLines(ctx, lines, x, y, lineHeight) {
    lines.forEach((value, index) => ctx.fillText(value, x, y + index * lineHeight));
    return lines.length * lineHeight;
  }

  async function loadCoverImage(src, kind = "cover") {
    if (!src) return null;
    let existing = null;
    if (kind === "protein") {
      existing = document.querySelector(".protein-panel img");
    } else if (kind === "logo") {
      existing = document.querySelector(".gsi-home-mark-icon img");
    } else {
      const filePart = src.startsWith("data:") ? "" : src.split("/").pop().split("?")[0];
      existing = (filePart && document.querySelector(`.signal-cover[src*="${filePart}"]`)) ||
        document.querySelector(".signal-cover");
    }
    if (existing && existing.complete && existing.naturalWidth > 0) {
      return existing;
    }
    if (typeof Image === "undefined") return null;
    return new Promise(resolve => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = src;
    });
  }

  function drawP53SpineStrip(ctx, protein, sleeve, spineW, colors) {
    ctx.save();
    drawRoundRect(ctx, sleeve.x, sleeve.y, spineW, sleeve.h, 0);
    ctx.clip();

    ctx.fillStyle = colors.spineBg;
    ctx.fillRect(sleeve.x, sleeve.y, spineW, sleeve.h);

    if (protein) {
      const iw = protein.naturalWidth || protein.width || 600;
      const ih = protein.naturalHeight || protein.height || 600;
      const sliceCount = 4;
      const sliceH = Math.ceil(sleeve.h / sliceCount);
      const sy = Math.round(ih * 0.045);
      const cropH = Math.max(1, Math.round(ih * 0.91));
      const cropW = Math.max(1, Math.min(iw, Math.round(cropH * (spineW / sliceH))));
      const offsets = [0.12, 0.36, 0.58, 0.24];

      for (let i = 0; i < sliceCount; i++) {
        const sx = Math.round((iw - cropW) * offsets[i]);
        const dy = sleeve.y + i * sliceH;
        ctx.drawImage(protein, sx, sy, cropW, cropH, sleeve.x, dy, spineW, sliceH);
        if (i > 0) {
          ctx.strokeStyle = "rgba(250, 244, 232, 0.22)";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(sleeve.x, dy);
          ctx.lineTo(sleeve.x + spineW, dy);
          ctx.stroke();
        }
      }

      ctx.fillStyle = hexToRgba(colors.primary, 0.14);
      ctx.fillRect(sleeve.x, sleeve.y, spineW, sleeve.h);
    } else {
      const fallbackSpine = ctx.createLinearGradient(sleeve.x, sleeve.y, sleeve.x, sleeve.y + sleeve.h);
      fallbackSpine.addColorStop(0, colors.p53Accent);
      fallbackSpine.addColorStop(0.5, colors.primary);
      fallbackSpine.addColorStop(1, colors.cyanAccent);
      ctx.fillStyle = fallbackSpine;
      ctx.fillRect(sleeve.x, sleeve.y, spineW, sleeve.h);
    }

    // Subtle left edge depth + inner spine fold shadow
    const edgeShade = ctx.createLinearGradient(sleeve.x, 0, sleeve.x + spineW, 0);
    edgeShade.addColorStop(0, "rgba(10, 6, 14, 0.22)");
    edgeShade.addColorStop(0.18, "rgba(0, 0, 0, 0)");
    edgeShade.addColorStop(0.84, "rgba(0, 0, 0, 0)");
    edgeShade.addColorStop(1, "rgba(16, 10, 22, 0.28)");
    ctx.fillStyle = edgeShade;
    ctx.fillRect(sleeve.x, sleeve.y, spineW, sleeve.h);
    ctx.restore();

    // Spine fold crease + P53 cyan/magenta registration trim on the paper face
    const foldX = sleeve.x + spineW;
    ctx.fillStyle = "rgba(255, 252, 246, 0.72)";
    ctx.fillRect(foldX, sleeve.y, 2, sleeve.h);
    ctx.fillStyle = hexToRgba(colors.cyanAccent, 0.8);
    ctx.fillRect(foldX + 3, sleeve.y, 3, sleeve.h);
    ctx.fillStyle = hexToRgba(colors.p53Accent, 0.85);
    ctx.fillRect(foldX + 6, sleeve.y, 3, sleeve.h);
  }

  function drawAlbumWindow(ctx, cover, box, colors) {
    ctx.fillStyle = hexToRgba(colors.cyanAccent, 0.48);
    drawAsymmRoundRect(ctx, box.x + 9, box.y + 9, box.size, box.size, 10, 36, 10, 36);
    ctx.fill();

    ctx.fillStyle = hexToRgba(colors.p53Accent, 0.54);
    drawAsymmRoundRect(ctx, box.x - 7, box.y - 7, box.size, box.size, 10, 36, 10, 36);
    ctx.fill();

    ctx.fillStyle = "rgba(18, 12, 24, 0.22)";
    drawAsymmRoundRect(ctx, box.x + 4, box.y + 12, box.size, box.size, 10, 36, 10, 36);
    ctx.fill();

    if (cover) {
      ctx.save();
      drawAsymmRoundRect(ctx, box.x, box.y, box.size, box.size, 10, 36, 10, 36);
      ctx.clip();
      const imageWidth = cover.naturalWidth || cover.width || box.size;
      const imageHeight = cover.naturalHeight || cover.height || box.size;
      const crop = Math.min(imageWidth, imageHeight);
      ctx.drawImage(
        cover,
        (imageWidth - crop) / 2,
        (imageHeight - crop) / 2,
        crop,
        crop,
        box.x,
        box.y,
        box.size,
        box.size
      );
      ctx.restore();
    } else {
      ctx.fillStyle = colors.surface;
      drawAsymmRoundRect(ctx, box.x, box.y, box.size, box.size, 10, 36, 10, 36);
      ctx.fill();
    }

    ctx.strokeStyle = hexToRgba(colors.inkPrimary, 0.18);
    ctx.lineWidth = 2;
    drawAsymmRoundRect(ctx, box.x, box.y, box.size, box.size, 10, 36, 10, 36);
    ctx.stroke();
  }

  async function renderStoryCard() {
    if (!canvas) return false;
    const ctx = canvas.getContext("2d");
    if (!ctx) return false;

    const g = Math.max(0, Math.min(1, Number(studioGradientIntensity) / 100));
    const curve = g > 0 ? Math.pow(g, 0.85) : 0;
    const coverScale = Math.max(0.6, Math.min(1, Number(studioCoverScale) / 100));
    const colors = deriveSleevePalette(context, studioStyle, g);
    const track = (context.track || "").trim();
    const artist = (artistName || "").trim();
    const album = (context.album || "").trim();
    const note = (studioNoteOverride !== null ? studioNoteOverride : (context.transmissionNote || "")).trim();

    ctx.clearRect(0, 0, 1080, 1920);
    const outerBg = ctx.createLinearGradient(0, 0, 1080, 1920);
    outerBg.addColorStop(0, colors.outerTop);
    outerBg.addColorStop(1, colors.outerBottom);
    ctx.fillStyle = outerBg;
    ctx.fillRect(0, 0, 1080, 1920);

    if (curve > 0.01) {
      const glowWash = ctx.createRadialGradient(600, 640, 60, 600, 640, 940);
      glowWash.addColorStop(0, hexToRgba(colors.glow, (studioStyle === "dark" ? 0.76 : 0.6) * curve));
      glowWash.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = glowWash;
      ctx.fillRect(0, 0, 1080, 1920);

      const p53Mist = ctx.createRadialGradient(140, 260, 40, 140, 260, 640);
      p53Mist.addColorStop(0, hexToRgba(colors.p53Accent, 0.34 * curve));
      p53Mist.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = p53Mist;
      ctx.fillRect(0, 0, 1080, 1080);

      const lowerOuter = ctx.createRadialGradient(920, 1620, 40, 920, 1620, 800);
      lowerOuter.addColorStop(0, hexToRgba(colors.secondary, (studioStyle === "dark" ? 0.56 : 0.44) * curve));
      lowerOuter.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = lowerOuter;
      ctx.fillRect(0, 0, 1080, 1920);
    }

    const sleeve = { x: 54, y: 76, w: 972, h: 1768 };

    // Offset P53 cyan/magenta registration plates + shadow behind the sleeve
    ctx.fillStyle = "rgba(6, 4, 10, 0.44)";
    drawAsymmRoundRect(ctx, sleeve.x + 12, sleeve.y + 18, sleeve.w, sleeve.h, 18, 44, 18, 44);
    ctx.fill();

    ctx.fillStyle = hexToRgba(colors.cyanAccent, 0.62 * Math.max(0.3, curve));
    drawAsymmRoundRect(ctx, sleeve.x + 10, sleeve.y + 10, sleeve.w, sleeve.h, 18, 44, 18, 44);
    ctx.fill();

    ctx.fillStyle = hexToRgba(colors.p53Accent, 0.68 * Math.max(0.3, curve));
    drawAsymmRoundRect(ctx, sleeve.x - 8, sleeve.y - 8, sleeve.w, sleeve.h, 18, 44, 18, 44);
    ctx.fill();

    const [protein, cover, logo] = await Promise.all([
      loadCoverImage(context.p53CoverSrc || "../covers/P53_cover-runtime.webp", "protein"),
      loadCoverImage(context.coverSrc, "cover"),
      loadCoverImage("../covers/GSI_favicon.svg", "logo"),
    ]);

    ctx.save();
    drawAsymmRoundRect(ctx, sleeve.x, sleeve.y, sleeve.w, sleeve.h, 18, 44, 18, 44);
    ctx.clip();

    // Tactile sleeve surface
    const paperGrad = ctx.createLinearGradient(sleeve.x, sleeve.y, sleeve.x + sleeve.w, sleeve.y + sleeve.h);
    paperGrad.addColorStop(0, colors.paperTop);
    paperGrad.addColorStop(0.52, colors.paperMid);
    paperGrad.addColorStop(1, colors.paperBottom);
    ctx.fillStyle = paperGrad;
    ctx.fillRect(sleeve.x, sleeve.y, sleeve.w, sleeve.h);

    if (curve > 0.01) {
      const upperBloom = ctx.createRadialGradient(
        sleeve.x + sleeve.w * 0.84,
        sleeve.y + sleeve.h * 0.14,
        30,
        sleeve.x + sleeve.w * 0.84,
        sleeve.y + sleeve.h * 0.14,
        840
      );
      upperBloom.addColorStop(0, hexToRgba(colors.primary, (studioStyle === "dark" ? 0.5 : 0.4) * curve));
      upperBloom.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = upperBloom;
      ctx.fillRect(sleeve.x, sleeve.y, sleeve.w, sleeve.h);

      const lowerBloom = ctx.createRadialGradient(
        sleeve.x + sleeve.w * 0.28,
        sleeve.y + sleeve.h * 0.86,
        30,
        sleeve.x + sleeve.w * 0.28,
        sleeve.y + sleeve.h * 0.86,
        800
      );
      lowerBloom.addColorStop(0, hexToRgba(colors.secondary, (studioStyle === "dark" ? 0.44 : 0.34) * curve));
      lowerBloom.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = lowerBloom;
      ctx.fillRect(sleeve.x, sleeve.y, sleeve.w, sleeve.h);
    }

    // Subtle horizontal grain lines
    ctx.strokeStyle = studioStyle === "dark" ? "rgba(255, 255, 255, 0.02)" : "rgba(45, 32, 24, 0.024)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let gy = sleeve.y + 16; gy < sleeve.y + sleeve.h; gy += 16) {
      ctx.moveTo(sleeve.x, gy);
      ctx.lineTo(sleeve.x + sleeve.w, gy);
    }
    ctx.stroke();

    const spineW = 132;
    drawP53SpineStrip(ctx, protein, sleeve, spineW, colors);

    const contentX = sleeve.x + spineW + 56;
    const contentRight = sleeve.x + sleeve.w - 56;
    const contentW = contentRight - contentX;

    // Minimal header: Radio P53 mark on left, subtle low-opacity Chaperone emblem on right (no Active/Previous badge)
    ctx.fillStyle = colors.cyanAccent;
    ctx.fillRect(contentX, 141, 5, 24);
    ctx.fillStyle = colors.p53Accent;
    ctx.fillRect(contentX + 8, 141, 5, 24);

    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillStyle = colors.inkPrimary;
    ctx.font = '700 30px "Space Grotesk", Arial, sans-serif';
    ctx.fillText("Radio P53", contentX + 24, 163);

    if (logo) {
      ctx.save();
      ctx.globalAlpha = studioStyle === "dark" ? 0.36 : 0.34;
      const markW = 30;
      const markH = 36;
      ctx.drawImage(logo, contentRight - markW, 134, markW, markH);
      ctx.restore();
    }

    ctx.fillStyle = hexToRgba(colors.inkPrimary, 0.14);
    ctx.fillRect(contentX, 194, contentW, 1.5);
    ctx.fillStyle = colors.accentRule;
    ctx.fillRect(contentX, 193, 96, 3.5);

    // Track title, artist, and album with clean cohesive spacing
    ctx.textBaseline = "top";
    let y = 248;
    const trackLen = Array.from(track).length;
    const trackSize = trackLen <= 20 ? 68 : (trackLen <= 34 ? 58 : 48);
    const trackLineHeight = trackSize + 12;

    ctx.fillStyle = colors.inkPrimary;
    ctx.font = `800 ${trackSize}px "Space Grotesk", Arial, sans-serif`;
    const trackMeasured = measureWrappedLines(ctx, track, contentW, 2);
    paintLines(ctx, trackMeasured.lines, contentX, y, trackLineHeight);
    y += Math.max(1, trackMeasured.lines.length) * trackLineHeight + 16;

    ctx.fillStyle = colors.inkPrimary;
    ctx.font = '700 36px "Space Grotesk", Arial, sans-serif';
    const artistMeasured = measureWrappedLines(ctx, artist, contentW, 2);
    paintLines(ctx, artistMeasured.lines, contentX, y, 46);
    y += Math.max(1, artistMeasured.lines.length) * 46 + 8;

    if (album) {
      ctx.fillStyle = colors.inkMuted;
      ctx.font = '500 26px "Space Grotesk", Arial, sans-serif';
      const albumMeasured = measureWrappedLines(ctx, album, contentW, 2);
      paintLines(ctx, albumMeasured.lines, contentX, y, 36);
      y += Math.max(1, albumMeasured.lines.length) * 36;
    }

    // Album cover strictly locked to Cover Size slider (never auto-enlarges when note is empty)
    const coverY = y + 48;
    const maxCoverSize = Math.min(contentW, 640);
    const coverSize = Math.round(maxCoverSize * coverScale);
    const coverX = contentX + Math.round((contentW - coverSize) / 2);
    drawAlbumWindow(ctx, cover, { x: coverX, y: coverY, size: coverSize }, colors);

    // Symmetrically aligned, readable note block below cover (no footer clutter below)
    let watermarkY = coverY + coverSize + 36;
    if (note) {
      const noteTop = coverY + coverSize + 48;
      const noteMaxBottom = studioWatermark ? sleeve.y + sleeve.h - 150 : sleeve.y + sleeve.h - 72;
      const availH = Math.max(150, noteMaxBottom - noteTop);
      const isLongNote = Array.from(note).length > 165;
      const noteFontSize = isLongNote ? 36 : 40;
      const noteLineHeight = isLongNote ? 50 : 54;
      const padY = 30;
      const maxNoteLines = Math.max(2, Math.floor((availH - padY * 2) / noteLineHeight));
      const noteTextX = contentX + 36;
      const noteTextW = contentW - 64;

      ctx.font = `500 ${noteFontSize}px "Space Grotesk", Arial, sans-serif`;
      const noteMeasured = measureWrappedLines(ctx, note, noteTextW, maxNoteLines);
      const linesBlockH = noteMeasured.lines.length > 0
        ? (noteMeasured.lines.length - 1) * noteLineHeight + noteFontSize
        : noteFontSize;
      const noteBoxH = padY * 2 + linesBlockH;

      ctx.fillStyle = colors.noteBg;
      drawRoundRect(ctx, contentX, noteTop, contentW, noteBoxH, 14);
      ctx.fill();

      ctx.strokeStyle = hexToRgba(colors.inkPrimary, studioStyle === "dark" ? 0.18 : 0.12);
      ctx.lineWidth = 1.5;
      drawRoundRect(ctx, contentX, noteTop, contentW, noteBoxH, 14);
      ctx.stroke();

      ctx.fillStyle = colors.accentRule;
      drawRoundRect(ctx, contentX + 14, noteTop + padY - 2, 4, noteBoxH - (padY - 2) * 2, 2);
      ctx.fill();

      ctx.fillStyle = colors.inkPrimary;
      paintLines(ctx, noteMeasured.lines, noteTextX, noteTop + padY, noteLineHeight);
      watermarkY = noteTop + noteBoxH + 24;
    }

    // Optional faint watermark directly beneath the note/comment
    if (studioWatermark) {
      const clampedY = Math.min(watermarkY, 1680);
      ctx.fillStyle = hexToRgba(colors.inkPrimary, studioStyle === "dark" ? 0.42 : 0.44);
      ctx.font = '500 22px "Space Grotesk", Arial, sans-serif';
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillText("view now in Chaperone!", contentX + 6, clampedY);
    }

    ctx.textBaseline = "alphabetic";
    ctx.restore();

    ctx.strokeStyle = hexToRgba(colors.inkPrimary, 0.14);
    ctx.lineWidth = 2;
    drawAsymmRoundRect(ctx, sleeve.x, sleeve.y, sleeve.w, sleeve.h, 18, 44, 18, 44);
    ctx.stroke();

    canvas.setAttribute("aria-label", "Chaperone share card: " + track + " by " + artist);
    cardRendered = true;
    return true;
  }

  function flashButton(btn, text) {
    if (!btn) return;
    if (storyStatus) storyStatus.textContent = text;
    if (!btn.dataset) btn.dataset = {};
    if (!btn.dataset.defaultLabel) btn.dataset.defaultLabel = btn.textContent;
    if (btn._flashTimer) window.clearTimeout?.(btn._flashTimer);
    const original = btn.dataset.defaultLabel;
    btn.textContent = text;
    btn._flashTimer = window.setTimeout(() => {
      btn.textContent = original;
      btn._flashTimer = null;
    }, 2200);
  }

  function triggerDownload() {
    if (!canvas) return false;
    try {
      const slug = context.slug || "signal";
      const dataUrl = canvas.toDataURL("image/png");
      const link = document.createElement("a");
      link.download = `p53-${slug}-story.png`;
      link.href = dataUrl;
      link.click();
      return true;
    } catch {
      if (storyStatus) storyStatus.textContent = "The card couldn't be saved. You can still copy the link.";
      return false;
    }
  }

  if (shareButton) {
    shareButton.addEventListener("click", async () => {
      if (storyModal && typeof storyModal.showModal === "function") {
        storyModal.showModal();
        if (!cardRendered) {
          if (storyStatus) storyStatus.textContent = "Preparing the card…";
          try {
            const ready = await renderStoryCard();
            if (btnShare) btnShare.disabled = !ready;
            if (btnCopyImage) btnCopyImage.disabled = !ready;
            if (btnDownload) btnDownload.disabled = !ready;
            if (storyStatus) storyStatus.textContent = ready ? "" : "The card couldn't be prepared. You can still copy the link.";
          } catch {
            if (storyStatus) storyStatus.textContent = "The card couldn't be prepared. You can still copy the link.";
          }
        }
        return;
      }

      // Classic fallback if dialog is unavailable
      const shareUrl = GSIContext.canonicalHref();
      const shareData = { title: context.shareTitle || document.title, text: artistName, url: shareUrl };
      try {
        if (navigator.share) {
          await navigator.share(shareData);
          return;
        }
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(shareUrl);
        }
      } catch {
        // quiet fallback
      }
    });
  }

  modalClose?.addEventListener?.("click", () => {
    storyModal?.close?.();
  });

  storyModal?.addEventListener?.("click", event => {
    if (event.target !== storyModal) return;
    if (event.clientX === 0 && event.clientY === 0) return;
    const rect = storyModal.getBoundingClientRect();
    const isInDialog = (
      rect.top <= event.clientY &&
      event.clientY <= rect.top + rect.height &&
      rect.left <= event.clientX &&
      event.clientX <= rect.left + rect.width
    );
    if (!isInDialog) storyModal.close();
  });

  btnShare?.addEventListener("click", async () => {
    if (!canvas) return;
    try {
      canvas.toBlob(async blob => {
        if (!blob) {
          if (triggerDownload()) flashButton(btnShare, "Card downloaded");
          return;
        }
        const slug = context.slug || "signal";
        const fileName = `p53-${slug}-transmission.png`;
        const file = new File([blob], fileName, { type: "image/png" });

        const shareData = {
          files: [file],
          title: context.shareTitle || `Radio P53 — ${context.track || "Transmission"}`,
          text: `Radio P53: ${context.track || ""} by ${artistName}`,
          url: GSIContext.canonicalHref(),
        };
        if (navigator.canShare && navigator.canShare({ files: [file] })) {
          try {
            // Some share targets support image files but reject a URL in the
            // payload. Keep the existing image-only option for those devices.
            const supportedData = navigator.canShare(shareData)
              ? shareData
              : { files: [file], title: shareData.title, text: shareData.text };
            await navigator.share(supportedData);
            flashButton(btnShare, "Share opened");
            return;
          } catch (err) {
            if (err && err.name === "AbortError") return;
          }
        }
        if (triggerDownload()) flashButton(btnShare, "Card downloaded");
      }, "image/png");
    } catch {
      if (storyStatus) storyStatus.textContent = "The card couldn't be shared. You can still copy the link.";
    }
  });

  btnDownload?.addEventListener("click", () => {
    if (triggerDownload()) flashButton(btnDownload, "Card downloaded");
  });

  btnCopyImage?.addEventListener?.("click", async () => {
    if (!canvas) return;
    if (!navigator?.clipboard?.write || typeof ClipboardItem === "undefined") {
      if (storyStatus) storyStatus.textContent = "Image copy isn't supported in this browser — use Download or Share.";
      return;
    }
    try {
      const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
      if (!blob) throw new Error("No image blob");
      await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
      flashButton(btnCopyImage, "Image copied");
    } catch {
      flashButton(btnCopyImage, "Couldn't copy image");
    }
  });

  if (stylePaperBtn && styleDarkBtn) {
    const setSurfaceStyle = async (mode) => {
      studioStyle = mode === "dark" ? "dark" : "paper";
      stylePaperBtn.setAttribute?.("aria-pressed", studioStyle === "paper" ? "true" : "false");
      styleDarkBtn.setAttribute?.("aria-pressed", studioStyle === "dark" ? "true" : "false");
      await renderStoryCard();
    };
    stylePaperBtn.addEventListener?.("click", () => setSurfaceStyle("paper"));
    styleDarkBtn.addEventListener?.("click", () => setSurfaceStyle("dark"));
  }

  let customQuoteChip = null;

  if (quoteChipsWrap && typeof document.createElement === "function") {
    const choices = [];
    if ((context.transmissionNote || "").trim()) {
      choices.push({ label: "Note", text: (context.transmissionNote || "").trim(), isCustom: false });
    }
    if (Array.isArray(context.entrySections)) {
      context.entrySections.forEach((sec) => {
        if (sec?.title && sec?.excerpt) {
          choices.push({ label: sec.title, text: sec.excerpt, isCustom: false });
        }
      });
    }
    choices.push({ label: "Custom", text: "", isCustom: true });
    choices.forEach((choice, idx) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "story-quote-chip";
      chip.textContent = choice.label;
      chip.setAttribute?.("aria-pressed", idx === 0 ? "true" : "false");
      if (choice.isCustom) customQuoteChip = chip;
      chip.addEventListener?.("click", () => {
        quoteChipsWrap.querySelectorAll?.(".story-quote-chip")?.forEach?.((el) =>
          el.setAttribute?.("aria-pressed", "false")
        );
        chip.setAttribute?.("aria-pressed", "true");
        studioNoteOverride = choice.text;
        if (quoteInput) {
          quoteInput.value = choice.text;
          if (choice.isCustom) quoteInput.focus?.();
        }
        renderStoryCard();
      });
      quoteChipsWrap.append?.(chip);
    });
  }

  if (quoteInput) {
    quoteInput.value = (context.transmissionNote || "").trim();
    quoteInput.addEventListener?.("input", () => {
      studioNoteOverride = quoteInput.value;
      if (quoteChipsWrap && customQuoteChip) {
        quoteChipsWrap.querySelectorAll?.(".story-quote-chip")?.forEach?.((el) =>
          el.setAttribute?.("aria-pressed", "false")
        );
        customQuoteChip.setAttribute?.("aria-pressed", "true");
      }
      renderStoryCard();
    });
  }

  if (gradientSlider) {
    syncSliderFill(gradientSlider);
    gradientSlider.addEventListener?.("input", () => {
      studioGradientIntensity = Number(gradientSlider.value);
      if (gradientValue) gradientValue.textContent = `${studioGradientIntensity}%`;
      syncSliderFill(gradientSlider);
      renderStoryCard();
    });
  }

  if (coverSlider) {
    syncSliderFill(coverSlider);
    coverSlider.addEventListener?.("input", () => {
      studioCoverScale = Number(coverSlider.value);
      if (coverValue) coverValue.textContent = `${studioCoverScale}%`;
      syncSliderFill(coverSlider);
      renderStoryCard();
    });
  }

  if (watermarkToggle) {
    watermarkToggle.setAttribute?.("aria-checked", studioWatermark ? "true" : "false");
    watermarkToggle.addEventListener?.("click", () => {
      studioWatermark = !studioWatermark;
      watermarkToggle.setAttribute?.("aria-checked", studioWatermark ? "true" : "false");
      renderStoryCard();
    });
  }

  btnCopy?.addEventListener("click", async () => {
    const shareUrl = GSIContext.canonicalHref();
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareUrl);
      } else {
        const fallback = document.createElement("textarea");
        fallback.value = shareUrl;
        fallback.setAttribute("readonly", "");
        fallback.style.cssText = "position:fixed;opacity:0;pointer-events:none";
        document.body.append(fallback);
        fallback.select();
        const copied = document.execCommand("copy");
        fallback.remove();
        if (!copied) throw new Error("Copy unavailable");
      }
      flashButton(btnCopy, "Link copied");
    } catch {
      flashButton(btnCopy, "Couldn't copy link");
    }
  });

  // 30-Second Signal Audition Controller
  (() => {
    const btn = document.querySelector(".audition-trigger");
    if (!btn) return;
    const url = btn.dataset?.previewUrl;
    if (!url) return;

    const initialLabel = (btn.getAttribute?.("aria-label") || "").trim();
    const labelMatch = initialLabel.match(/^Peek signal of\s+(.+)$/i);
    const trackName = labelMatch ? labelMatch[1].trim() : (context.track || "").trim();

    function labelFor(state) {
      const target = trackName ? ` of ${trackName}` : "";
      if (state === "playing") return `Pause 30-second preview${target}`;
      if (state === "paused") return `Resume 30-second preview${target}`;
      if (state === "ended") return `Replay 30-second preview${target}`;
      if (state === "unavailable") return trackName ? `Preview unavailable for ${trackName}` : "Preview unavailable";
      if (state === "blocked") return trackName ? `Playback blocked for ${trackName}; activate to retry` : "Playback blocked; activate to retry";
      return `Peek 30-second preview${target}`;
    }

    let statusNode = btn.closest?.(".stream-block")?.querySelector(".audition-status") || null;
    if (!statusNode && typeof document.createElement === "function") {
      statusNode = document.createElement("span");
      statusNode.className = "sr-only audition-status";
      statusNode.setAttribute?.("role", "status");
      statusNode.setAttribute?.("aria-live", "polite");
      statusNode.setAttribute?.("aria-atomic", "true");
      (btn.closest?.(".stream-block") || btn.parentElement || document.body).append?.(statusNode);
    }

    let currentState = "";
    function setButtonState(state, announcement = "") {
      if (currentState === state) return;
      currentState = state;
      btn.classList?.remove("is-playing", "is-paused", "is-error");
      if (state === "playing") {
        btn.disabled = false;
        btn.removeAttribute?.("aria-disabled");
        btn.classList?.add("is-playing");
        btn.setAttribute?.("aria-pressed", "true");
        btn.setAttribute?.("aria-label", labelFor("playing"));
        btn.innerHTML = 'PEEKING <span class="peek-icon" aria-hidden="true">⏸</span>';
        document.body.classList?.add("signal-auditioning");
      } else if (state === "paused") {
        btn.disabled = false;
        btn.removeAttribute?.("aria-disabled");
        btn.classList?.add("is-paused");
        btn.setAttribute?.("aria-pressed", "false");
        btn.setAttribute?.("aria-label", labelFor("paused"));
        btn.innerHTML = 'PAUSED <span class="peek-icon" aria-hidden="true">▶</span>';
        document.body.classList?.remove("signal-auditioning");
      } else if (state === "unavailable") {
        btn.classList?.add("is-error");
        btn.setAttribute?.("aria-pressed", "false");
        btn.disabled = true;
        btn.setAttribute?.("aria-disabled", "true");
        btn.textContent = "Preview unavailable";
        btn.setAttribute?.("aria-label", labelFor("unavailable"));
        document.body.classList?.remove("signal-auditioning");
      } else if (state === "blocked") {
        btn.disabled = false;
        btn.removeAttribute?.("aria-disabled");
        btn.classList?.add("is-error");
        btn.setAttribute?.("aria-pressed", "false");
        btn.textContent = "Playback blocked";
        btn.setAttribute?.("aria-label", labelFor("blocked"));
        document.body.classList?.remove("signal-auditioning");
      } else {
        btn.disabled = false;
        btn.removeAttribute?.("aria-disabled");
        btn.setAttribute?.("aria-pressed", "false");
        btn.setAttribute?.("aria-label", labelFor(state === "ended" ? "ended" : "idle"));
        btn.innerHTML = 'PEEK <span class="peek-icon" aria-hidden="true">▶</span>';
        document.body.classList?.remove("signal-auditioning");
      }
      if (announcement && statusNode) statusNode.textContent = announcement;
    }

    setButtonState("idle");

    let audio = null;
    let isStarting = false;

    function onPlay() {
      isStarting = false;
      btn.removeAttribute?.("aria-busy");
      setButtonState("playing", trackName ? `Playing 30-second preview of ${trackName}.` : "Playing 30-second preview.");
    }

    function onPause() {
      isStarting = false;
      btn.removeAttribute?.("aria-busy");
      if (!audio || audio.ended) return;
      setButtonState("paused", "Preview paused.");
    }

    function onEnded() {
      isStarting = false;
      btn.removeAttribute?.("aria-busy");
      if (audio) {
        try { audio.currentTime = 0; } catch { /* ignore seek errors on teardown */ }
      }
      setButtonState("ended", "Preview ended.");
    }

    function cleanupAudio() {
      isStarting = false;
      if (!audio) return;
      const target = audio;
      audio = null;
      target.removeEventListener?.("play", onPlay);
      target.removeEventListener?.("pause", onPause);
      target.removeEventListener?.("ended", onEnded);
      target.removeEventListener?.("error", onError);
      try {
        target.pause();
        target.removeAttribute?.("src");
        target.load?.();
      } catch { /* media cleanup optional in stub environments */ }
    }

    function onError() {
      cleanupAudio();
      btn.removeAttribute?.("aria-busy");
      setButtonState("unavailable", "Audio preview unavailable.");
    }

    btn.addEventListener("click", () => {
      if (isStarting || btn.disabled) return;
      if (!audio) {
        audio = new Audio(url);
        audio.addEventListener?.("play", onPlay);
        audio.addEventListener?.("pause", onPause);
        audio.addEventListener?.("ended", onEnded);
        audio.addEventListener?.("error", onError);
      }
      if (audio.paused) {
        isStarting = true;
        btn.setAttribute?.("aria-busy", "true");
        Promise.resolve(audio.play()).then(() => {
          isStarting = false;
          btn.removeAttribute?.("aria-busy");
          if (audio && !audio.paused) {
            setButtonState("playing", trackName ? `Playing 30-second preview of ${trackName}.` : "Playing 30-second preview.");
          }
        }).catch(err => {
          isStarting = false;
          btn.removeAttribute?.("aria-busy");
          if (err && err.name === "AbortError") return;
          if (err && err.name === "NotSupportedError") {
            cleanupAudio();
            setButtonState("unavailable", "Audio preview unavailable.");
            return;
          }
          setButtonState("blocked", "Audio playback blocked by browser.");
        });
      } else {
        audio.pause();
        setButtonState("paused", "Preview paused.");
      }
    });

    function pauseActiveAudio() {
      if (audio && !audio.paused) {
        audio.pause();
        setButtonState("paused", "Preview paused.");
      }
    }

    document.addEventListener?.("visibilitychange", () => {
      if (document.visibilityState === "hidden") pauseActiveAudio();
    });

    document.querySelectorAll?.(".stream-link:not(.audition-trigger)")?.forEach?.(link => {
      link.addEventListener?.("click", pauseActiveAudio);
    });

    window.addEventListener?.("pagehide", () => {
      cleanupAudio();
      btn.removeAttribute?.("aria-busy");
      if (!btn.classList?.contains("is-error")) {
        setButtonState("idle");
      } else {
        document.body.classList?.remove("signal-auditioning");
      }
    });
  })();

})();
