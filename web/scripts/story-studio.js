/*
 * Shared 9:16 Interactive Share Card Studio renderer & clipboard/share bridge
 * for Chaperone (GSI) Entry reading rooms.
 * Supports LIT/DIM backgrounds, background gradient intensity & locked cover size sliders,
 * quote section chips + custom quote editor, subtle Chaperone mark, Copy Image, Web Share, and PNG download.
 */
(() => {
  function parseHex(hex, fallback) {
    const clean = String(hex || "").trim().replace(/^#/, "");
    const normalized =
      clean.length === 3
        ? clean
            .split("")
            .map((c) => c + c)
            .join("")
        : clean;
    if (!/^[0-9a-f]{6}$/i.test(normalized)) return fallback;
    return [
      parseInt(normalized.slice(0, 2), 16),
      parseInt(normalized.slice(2, 4), 16),
      parseInt(normalized.slice(4, 6), 16),
    ];
  }

  function rgbToHex(rgb) {
    return (
      "#" +
      rgb
        .map((n) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, "0"))
        .join("")
    );
  }

  function mixRgb(first, second, t) {
    return first.map((c, i) => Math.round(c + (second[i] - c) * t));
  }

  function relativeLuminance(rgb) {
    const [r, g, b] = rgb.map((v) => {
      const c = v / 255;
      return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
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
    for (let step = 1; step <= 12; step++) {
      const candidate = mixRgb(fgRgb, targetRgb, step / 12);
      if (contrastRatio(candidate, bgRgb) >= minRatio) return candidate;
    }
    return targetRgb;
  }

  function mixHex(a, b, t) {
    const ca = parseHex(a, [18, 16, 22]);
    const cb = parseHex(b, [246, 242, 234]);
    return rgbToHex([
      ca[0] + (cb[0] - ca[0]) * t,
      ca[1] + (cb[1] - ca[1]) * t,
      ca[2] + (cb[2] - ca[2]) * t,
    ]);
  }

  function hexToRgba(hex, alpha) {
    const [r, g, b] = parseHex(hex, [255, 101, 173]);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function syncSliderFill(slider) {
    if (!slider || !slider.style?.setProperty) return;
    const min = Number(slider.min ?? 0);
    const max = Number(slider.max ?? 100);
    const val = Number(slider.value ?? min);
    const pct = max > min ? Math.max(0, Math.min(100, ((val - min) / (max - min)) * 100)) : 0;
    slider.style.setProperty("--slider-pct", `${pct.toFixed(1)}%`);
  }

  function drawAsymmRoundRect(ctx, x, y, w, h, tl, tr, br, bl) {
    ctx.beginPath();
    ctx.moveTo(x + tl, y);
    ctx.lineTo(x + w - tr, y);
    ctx.arcTo(x + w, y, x + w, y + tr, tr);
    ctx.lineTo(x + w, y + h - br);
    ctx.arcTo(x + w, y + h, x + w - br, y + h, br);
    ctx.lineTo(x + bl, y + h);
    ctx.arcTo(x, y + h, x, y + h - bl, bl);
    ctx.lineTo(x, y + tl);
    ctx.arcTo(x, y, x + tl, y, tl);
    ctx.closePath();
  }

  function drawRoundRect(ctx, x, y, w, h, r) {
    drawAsymmRoundRect(ctx, x, y, w, h, r, r, r, r);
  }

  function measureWrappedLines(ctx, text, maxWidth, maxLines) {
    const words = String(text || "").trim().split(/\s+/).filter(Boolean);
    const lines = [];
    let line = "";
    for (const word of words) {
      const test = line ? `${line} ${word}` : word;
      if (ctx.measureText(test).width <= maxWidth) {
        line = test;
        continue;
      }
      if (line) {
        lines.push(line);
        line = "";
      }
      if (ctx.measureText(word).width <= maxWidth) {
        line = word;
        continue;
      }
      let remaining = word;
      while (remaining) {
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
      while (last && ctx.measureText(last + "…").width > maxWidth) {
        last = Array.from(last).slice(0, -1).join("");
      }
      visible[visible.length - 1] = last + "…";
    }
    return { lines: visible, truncated };
  }

  function paintLines(ctx, lines, x, y, lineHeight) {
    lines.forEach((value, index) => ctx.fillText(value, x, y + index * lineHeight));
    return lines.length * lineHeight;
  }

  function loadImg(src, selector) {
    if (!src) return Promise.resolve(null);
    const existing = selector ? document.querySelector(selector) : null;
    if (existing && existing.complete && existing.naturalWidth > 0) {
      return Promise.resolve(existing);
    }
    if (typeof Image === "undefined") return Promise.resolve(null);
    return new Promise((resolve) => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = src;
    });
  }

  async function renderEntryStoryCard(canvas, context, options) {
    const ctx = canvas.getContext("2d");
    if (!ctx) return false;

    const mode = options.mode === "paper" ? "paper" : "dark";
    const quote = String(options.quote || "").trim();
    const quoteLabel = String(options.quoteLabel || "").trim();
    const showWatermark = options.watermark !== false;
    const gradientIntensity = Math.max(0, Math.min(1, Number(options.gradientIntensity ?? 65) / 100));
    const coverScale = Math.max(0.6, Math.min(1, Number(options.coverScale ?? 80) / 100));

    const tp = context.trackPalette || {};
    const primary = tp.primary || context.accent || "#ff65ad";
    const secondary = tp.secondary || "#35c9e9";
    const glow = tp.glow || primary;
    const surface = tp.surface || "#16131c";

    const g = gradientIntensity;
    const curve = g > 0 ? Math.pow(g, 0.85) : 0;
    const primaryRgb = parseHex(primary, [255, 101, 173]);
    const secondaryRgb = parseHex(secondary, [53, 201, 233]);
    const glowRgb = parseHex(glow, primaryRgb);
    const surfaceRgb = parseHex(surface, [22, 19, 28]);

    let palette;
    if (mode === "paper") {
      // Lifted light-mode stops so 0% is crisp neutral ivory and 100% is a bold, vivid album wash
      const litPrimary = mixRgb(primaryRgb, [255, 250, 245], 0.2);
      const litGlow = mixRgb(glowRgb, [255, 248, 242], 0.14);
      const litSecondary = mixRgb(secondaryRgb, [252, 248, 244], 0.16);
      const sleeveTopRgb = mixRgb([249, 245, 238], litPrimary, 0.36 * curve);
      const sleeveMidRgb = mixRgb([243, 237, 227], litGlow, 0.48 * curve);
      const sleeveBottomRgb = mixRgb([236, 228, 214], litSecondary, 0.56 * curve);
      const darkFallback = [18, 13, 24];
      const inkPrimaryRgb = ensureContrast(mixRgb(surfaceRgb, darkFallback, 0.82), sleeveMidRgb, darkFallback, 8.2);
      const inkMutedRgb = ensureContrast(mixRgb(inkPrimaryRgb, primaryRgb, 0.24), sleeveMidRgb, inkPrimaryRgb, 5.0);
      const accentRuleRgb = ensureContrast(primaryRgb, sleeveMidRgb, inkPrimaryRgb, 3.6);
      palette = {
        outerTop: rgbToHex(mixRgb([20, 17, 26], primaryRgb, 0.62 * curve)),
        outerBottom: rgbToHex(mixRgb([11, 9, 15], secondaryRgb, 0.52 * curve)),
        sleeveTop: rgbToHex(sleeveTopRgb),
        sleeveMid: rgbToHex(sleeveMidRgb),
        sleeveBottom: rgbToHex(sleeveBottomRgb),
        inkPrimary: rgbToHex(inkPrimaryRgb),
        inkMuted: rgbToHex(inkMutedRgb),
        accentRule: rgbToHex(accentRuleRgb),
        noteBg: "rgba(255, 253, 249, 0.84)",
        grainStroke: "rgba(38, 26, 20, 0.024)",
      };
    } else {
      // Deep obsidian at 0% scaling to lush, unmistakable album-gradient atmosphere at 100%
      const dimTopRgb = mixRgb([20, 17, 26], mixRgb(surfaceRgb, primaryRgb, 0.44), 0.78 * curve);
      const dimMidRgb = mixRgb([15, 13, 21], primaryRgb, 0.54 * curve);
      const dimBottomRgb = mixRgb([10, 9, 15], secondaryRgb, 0.62 * curve);
      const lightInkRgb = [248, 245, 239];
      const mutedLightRgb = ensureContrast(mixRgb(lightInkRgb, primaryRgb, 0.2), dimMidRgb, lightInkRgb, 5.4);
      const accentLightRgb = ensureContrast(primaryRgb, dimMidRgb, [255, 204, 230], 4.4);
      palette = {
        outerTop: rgbToHex(mixRgb([10, 9, 14], primaryRgb, 0.68 * curve)),
        outerBottom: rgbToHex(mixRgb([6, 5, 10], secondaryRgb, 0.56 * curve)),
        sleeveTop: rgbToHex(dimTopRgb),
        sleeveMid: rgbToHex(dimMidRgb),
        sleeveBottom: rgbToHex(dimBottomRgb),
        inkPrimary: rgbToHex(lightInkRgb),
        inkMuted: rgbToHex(mutedLightRgb),
        accentRule: rgbToHex(accentLightRgb),
        noteBg: "rgba(10, 8, 16, 0.36)",
        grainStroke: "rgba(255, 255, 255, 0.022)",
      };
    }

    ctx.clearRect(0, 0, 1080, 1920);
    const outerBg = ctx.createLinearGradient(0, 0, 1080, 1920);
    outerBg.addColorStop(0, palette.outerTop);
    outerBg.addColorStop(1, palette.outerBottom);
    ctx.fillStyle = outerBg;
    ctx.fillRect(0, 0, 1080, 1920);

    if (curve > 0.01) {
      const glowWash = ctx.createRadialGradient(540, 620, 60, 540, 620, 960);
      glowWash.addColorStop(0, hexToRgba(glow, (mode === "dark" ? 0.78 : 0.64) * curve));
      glowWash.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = glowWash;
      ctx.fillRect(0, 0, 1080, 1920);

      const cornerWash = ctx.createRadialGradient(920, 1620, 40, 920, 1620, 820);
      cornerWash.addColorStop(0, hexToRgba(secondary, (mode === "dark" ? 0.62 : 0.48) * curve));
      cornerWash.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = cornerWash;
      ctx.fillRect(0, 0, 1080, 1920);
    }

    const sleeve = { x: 54, y: 76, w: 972, h: 1768 };

    // Offset chromatic registration plates
    ctx.fillStyle = "rgba(0, 0, 0, 0.44)";
    drawAsymmRoundRect(ctx, sleeve.x + 12, sleeve.y + 18, sleeve.w, sleeve.h, 18, 44, 18, 44);
    ctx.fill();

    if (curve > 0.01) {
      ctx.fillStyle = hexToRgba(secondary, 0.62 * Math.max(0.25, curve));
      drawAsymmRoundRect(ctx, sleeve.x + 9, sleeve.y + 9, sleeve.w, sleeve.h, 18, 44, 18, 44);
      ctx.fill();

      ctx.fillStyle = hexToRgba(primary, 0.68 * Math.max(0.25, curve));
      drawAsymmRoundRect(ctx, sleeve.x - 8, sleeve.y - 8, sleeve.w, sleeve.h, 18, 44, 18, 44);
      ctx.fill();
    }

    const [cover, logo] = await Promise.all([
      loadImg(context.coverSrc, ".cover-frame img.cover"),
      loadImg("../covers/GSI_favicon.svg", '.gsi-home-mark-icon img'),
    ]);

    ctx.save();
    drawAsymmRoundRect(ctx, sleeve.x, sleeve.y, sleeve.w, sleeve.h, 18, 44, 18, 44);
    ctx.clip();

    const sleeveGrad = ctx.createLinearGradient(
      sleeve.x,
      sleeve.y,
      sleeve.x + sleeve.w,
      sleeve.y + sleeve.h
    );
    sleeveGrad.addColorStop(0, palette.sleeveTop);
    sleeveGrad.addColorStop(0.52, palette.sleeveMid);
    sleeveGrad.addColorStop(1, palette.sleeveBottom);
    ctx.fillStyle = sleeveGrad;
    ctx.fillRect(sleeve.x, sleeve.y, sleeve.w, sleeve.h);

    if (curve > 0.01) {
      const innerBloom = ctx.createRadialGradient(
        sleeve.x + sleeve.w * 0.82,
        sleeve.y + sleeve.h * 0.14,
        30,
        sleeve.x + sleeve.w * 0.82,
        sleeve.y + sleeve.h * 0.14,
        860
      );
      innerBloom.addColorStop(0, hexToRgba(primary, (mode === "dark" ? 0.54 : 0.44) * curve));
      innerBloom.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = innerBloom;
      ctx.fillRect(sleeve.x, sleeve.y, sleeve.w, sleeve.h);

      const lowerBloom = ctx.createRadialGradient(
        sleeve.x + sleeve.w * 0.2,
        sleeve.y + sleeve.h * 0.86,
        30,
        sleeve.x + sleeve.w * 0.2,
        sleeve.y + sleeve.h * 0.86,
        840
      );
      lowerBloom.addColorStop(0, hexToRgba(secondary, (mode === "dark" ? 0.46 : 0.38) * curve));
      lowerBloom.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = lowerBloom;
      ctx.fillRect(sleeve.x, sleeve.y, sleeve.w, sleeve.h);

      const centerSheen = ctx.createRadialGradient(
        sleeve.x + sleeve.w * 0.52,
        sleeve.y + sleeve.h * 0.48,
        20,
        sleeve.x + sleeve.w * 0.52,
        sleeve.y + sleeve.h * 0.48,
        660
      );
      centerSheen.addColorStop(0, hexToRgba(glow, (mode === "dark" ? 0.3 : 0.24) * curve));
      centerSheen.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = centerSheen;
      ctx.fillRect(sleeve.x, sleeve.y, sleeve.w, sleeve.h);
    }

    // Subtle horizontal texture lines
    ctx.strokeStyle = palette.grainStroke;
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let gy = sleeve.y + 18; gy < sleeve.y + sleeve.h; gy += 18) {
      ctx.moveTo(sleeve.x, gy);
      ctx.lineTo(sleeve.x + sleeve.w, gy);
    }
    ctx.stroke();

    // Narrow tonal spine accent on left
    const spineW = 30;
    const spineGrad = ctx.createLinearGradient(sleeve.x, sleeve.y, sleeve.x, sleeve.y + sleeve.h);
    spineGrad.addColorStop(0, primary);
    spineGrad.addColorStop(0.55, glow);
    spineGrad.addColorStop(1, secondary);
    ctx.fillStyle = spineGrad;
    ctx.fillRect(sleeve.x, sleeve.y, spineW, sleeve.h);

    const contentX = sleeve.x + spineW + 64;
    const contentRight = sleeve.x + sleeve.w - 64;
    const contentW = contentRight - contentX;

    // Header: Chaperone: ulaş's music archive on left + subtle emblem on right + hairline rule
    ctx.fillStyle = primary;
    ctx.fillRect(contentX, 141, 5, 24);
    ctx.fillStyle = secondary;
    ctx.fillRect(contentX + 8, 141, 5, 24);

    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillStyle = palette.inkPrimary;
    ctx.font = '700 26px "Space Grotesk", Arial, sans-serif';
    ctx.fillText("Chaperone: ulaş's music archive", contentX + 24, 161);

    const markW = 30;
    const markH = 36;
    if (logo) {
      ctx.save();
      ctx.globalAlpha = mode === "paper" ? 0.34 : 0.36;
      ctx.drawImage(logo, contentRight - markW, 134, markW, markH);
      ctx.restore();
    }

    ctx.fillStyle = hexToRgba(palette.inkPrimary, 0.16);
    ctx.fillRect(contentX, 194, contentW, 1.5);
    ctx.fillStyle = palette.accentRule;
    ctx.fillRect(contentX, 193, 96, 3.5);

    // Track / Artist / Album with cohesive spacing
    const track = String(context.track || "").trim();
    const artist = String(context.artistName || "").trim();
    const album = String(context.album || "").trim();

    ctx.textAlign = "left";
    ctx.textBaseline = "top";

    let y = 248;
    const trackLen = Array.from(track).length;
    const trackSize = trackLen <= 18 ? 68 : trackLen <= 32 ? 58 : 48;
    const trackLH = trackSize + 12;

    ctx.fillStyle = palette.inkPrimary;
    ctx.font = `800 ${trackSize}px "Space Grotesk", Arial, sans-serif`;
    const trackLines = measureWrappedLines(ctx, track, contentW, 2).lines;
    paintLines(ctx, trackLines, contentX, y, trackLH);
    y += Math.max(1, trackLines.length) * trackLH + 16;

    ctx.fillStyle = palette.inkPrimary;
    ctx.font = '700 36px "Space Grotesk", Arial, sans-serif';
    const artistLines = measureWrappedLines(ctx, artist, contentW, 2).lines;
    paintLines(ctx, artistLines, contentX, y, 46);
    y += Math.max(1, artistLines.length) * 46 + 8;

    if (album) {
      ctx.fillStyle = palette.inkMuted;
      ctx.font = '500 26px "Space Grotesk", Arial, sans-serif';
      const albumLines = measureWrappedLines(ctx, album, contentW, 2).lines;
      paintLines(ctx, albumLines, contentX, y, 36);
      y += Math.max(1, albumLines.length) * 36;
    }

    // Cover artwork strictly locked to Cover Size slider (never auto-enlarges when quote is empty)
    const coverY = y + 48;
    const maxCoverSize = Math.min(contentW, 640);
    const coverSize = Math.round(maxCoverSize * coverScale);
    const coverX = contentX + Math.round((contentW - coverSize) / 2);

    ctx.fillStyle = "rgba(0, 0, 0, 0.26)";
    drawAsymmRoundRect(ctx, coverX + 4, coverY + 14, coverSize, coverSize, 12, 36, 12, 36);
    ctx.fill();

    if (curve > 0.01) {
      ctx.fillStyle = hexToRgba(secondary, 0.48 * Math.max(0.25, curve));
      drawAsymmRoundRect(ctx, coverX + 9, coverY + 9, coverSize, coverSize, 12, 36, 12, 36);
      ctx.fill();
      ctx.fillStyle = hexToRgba(primary, 0.54 * Math.max(0.25, curve));
      drawAsymmRoundRect(ctx, coverX - 7, coverY - 7, coverSize, coverSize, 12, 36, 12, 36);
      ctx.fill();
    }

    if (cover) {
      ctx.save();
      drawAsymmRoundRect(ctx, coverX, coverY, coverSize, coverSize, 12, 36, 12, 36);
      ctx.clip();
      const iw = cover.naturalWidth || cover.width || coverSize;
      const ih = cover.naturalHeight || cover.height || coverSize;
      const crop = Math.min(iw, ih);
      ctx.drawImage(cover, (iw - crop) / 2, (ih - crop) / 2, crop, crop, coverX, coverY, coverSize, coverSize);
      ctx.restore();
    } else {
      ctx.fillStyle = surface;
      drawAsymmRoundRect(ctx, coverX, coverY, coverSize, coverSize, 12, 36, 12, 36);
      ctx.fill();
    }

    ctx.strokeStyle = hexToRgba(palette.inkPrimary, 0.16);
    ctx.lineWidth = 2;
    drawAsymmRoundRect(ctx, coverX, coverY, coverSize, coverSize, 12, 36, 12, 36);
    ctx.stroke();

    // Cohesive, symmetrically padded Quote Block
    let watermarkY = coverY + coverSize + 36;
    if (quote) {
      const noteTop = coverY + coverSize + 48;
      const noteMaxBottom = showWatermark ? sleeve.y + sleeve.h - 148 : sleeve.y + sleeve.h - 72;
      const availH = Math.max(150, noteMaxBottom - noteTop);
      const isLong = Array.from(quote).length > 165;
      const fontSize = isLong ? 34 : 38;
      const lh = isLong ? 48 : 54;
      const padY = 30;
      const labelBlockH = quoteLabel ? 36 : 0;
      const maxLines = Math.max(2, Math.floor((availH - padY * 2 - labelBlockH) / lh));
      const textX = contentX + 36;
      const textW = contentW - 64;

      ctx.font = `500 ${fontSize}px "Space Grotesk", Arial, sans-serif`;
      const measured = measureWrappedLines(ctx, quote, textW, maxLines);
      const linesBlockH = measured.lines.length > 0
        ? (measured.lines.length - 1) * lh + fontSize
        : fontSize;
      const boxH = padY * 2 + labelBlockH + linesBlockH;

      ctx.fillStyle = palette.noteBg;
      drawRoundRect(ctx, contentX, noteTop, contentW, boxH, 16);
      ctx.fill();

      ctx.strokeStyle = hexToRgba(palette.inkPrimary, mode === "dark" ? 0.18 : 0.12);
      ctx.lineWidth = 1.5;
      drawRoundRect(ctx, contentX, noteTop, contentW, boxH, 16);
      ctx.stroke();

      ctx.fillStyle = palette.accentRule;
      drawRoundRect(ctx, contentX + 14, noteTop + padY - 2, 4, boxH - (padY - 2) * 2, 2);
      ctx.fill();

      let textY = noteTop + padY;
      if (quoteLabel) {
        ctx.fillStyle = palette.accentRule;
        ctx.font = '700 20px "Space Grotesk", Arial, sans-serif';
        ctx.fillText(quoteLabel.toUpperCase(), textX, textY);
        textY += labelBlockH;
      }

      ctx.fillStyle = palette.inkPrimary;
      ctx.font = `500 ${fontSize}px "Space Grotesk", Arial, sans-serif`;
      paintLines(ctx, measured.lines, textX, textY, lh);
      watermarkY = noteTop + boxH + 24;
    }

    // Optional faint watermark directly beneath the quote/comment
    if (showWatermark) {
      const clampedY = Math.min(watermarkY, sleeve.y + sleeve.h - 68);
      ctx.fillStyle = hexToRgba(palette.inkPrimary, mode === "paper" ? 0.44 : 0.42);
      ctx.font = '500 22px "Space Grotesk", Arial, sans-serif';
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillText("view now in Chaperone!", contentX + 6, clampedY);
    }

    ctx.textBaseline = "alphabetic";
    ctx.restore();

    ctx.strokeStyle = hexToRgba(palette.inkPrimary, 0.16);
    ctx.lineWidth = 2;
    drawAsymmRoundRect(ctx, sleeve.x, sleeve.y, sleeve.w, sleeve.h, 18, 44, 18, 44);
    ctx.stroke();

    canvas.setAttribute("aria-label", `Chaperone share card: ${track} by ${artist}`);
    return true;
  }

  async function copyCanvasImageToClipboard(canvas) {
    if (!canvas || !navigator.clipboard?.write || typeof ClipboardItem === "undefined") {
      return { ok: false, reason: "Image clipboard copy isn't supported in this browser — use Download or Share." };
    }
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    if (!blob) {
      return { ok: false, reason: "Couldn't encode card image." };
    }
    await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
    return { ok: true };
  }

  function initEntryStoryStudio() {
    const contextNode = document.querySelector("#gsi-entry-context");
    const trigger = document.querySelector("#entry-share-trigger");
    const modal = document.querySelector("#entry-story-modal");
    if (!contextNode || !trigger || !modal) return;

    let context;
    try {
      context = JSON.parse(contextNode.textContent || "{}");
    } catch {
      return;
    }

    const canvas = modal.querySelector("#entry-story-canvas");
    const btnClose = modal.querySelector("#entry-story-close");
    const btnShare = modal.querySelector("#entry-story-btn-share");
    const btnCopyImage = modal.querySelector("#entry-story-btn-copy-image");
    const btnDownload = modal.querySelector("#entry-story-btn-download");
    const btnCopyLink = modal.querySelector("#entry-story-btn-copy-link");
    const statusNode = modal.querySelector("#entry-story-status");
    const chipsWrap = modal.querySelector("#entry-story-quote-chips");
    const quoteInput = modal.querySelector("#entry-story-quote-input");
    const gradientSlider = modal.querySelector("#entry-story-gradient-slider");
    const gradientValue = modal.querySelector("#entry-story-gradient-value");
    const coverSlider = modal.querySelector("#entry-story-cover-slider");
    const coverValue = modal.querySelector("#entry-story-cover-value");
    const watermarkToggle = modal.querySelector("#entry-story-watermark-toggle");
    const modeButtons = [...modal.querySelectorAll("[data-story-mode]")];

    const sections = Array.isArray(context.sections) ? context.sections : [];
    const state = {
      mode: document.documentElement.dataset.gsiTheme === "light" ? "paper" : "dark",
      quote: sections[0]?.excerpt || "",
      quoteLabel: sections[0]?.title || "",
      gradientIntensity: Number(gradientSlider?.value ?? 65),
      coverScale: Number(coverSlider?.value ?? 80),
      watermark: watermarkToggle ? watermarkToggle.getAttribute("aria-checked") !== "false" : true,
    };

    function flash(btn, text) {
      if (statusNode) statusNode.textContent = text;
      if (!btn) return;
      if (!btn.dataset.defaultLabel) btn.dataset.defaultLabel = btn.textContent;
      if (btn._t) window.clearTimeout(btn._t);
      btn.textContent = text;
      btn._t = window.setTimeout(() => {
        btn.textContent = btn.dataset.defaultLabel;
      }, 2200);
    }

    async function redraw() {
      if (!canvas) return;
      const ok = await renderEntryStoryCard(canvas, context, state);
      if (btnShare) btnShare.disabled = !ok;
      if (btnCopyImage) btnCopyImage.disabled = !ok;
      if (btnDownload) btnDownload.disabled = !ok;
    }

    let customChip = null;

    // Build quote section chips + Custom
    if (chipsWrap) {
      chipsWrap.innerHTML = "";
      const choices = [
        ...sections.map((s) => ({ label: s.title, text: s.excerpt || s.content || "", isCustom: false })),
        { label: "Custom", text: "", isCustom: true },
      ];
      choices.forEach((choice, idx) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "story-quote-chip";
        chip.textContent = choice.label;
        chip.setAttribute("aria-pressed", idx === 0 ? "true" : "false");
        if (choice.isCustom) customChip = chip;
        chip.addEventListener("click", () => {
          chipsWrap.querySelectorAll(".story-quote-chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
          chip.setAttribute("aria-pressed", "true");
          if (choice.isCustom) {
            state.quote = "";
            state.quoteLabel = "";
            if (quoteInput) {
              quoteInput.value = "";
              quoteInput.focus();
            }
          } else {
            state.quote = choice.text;
            state.quoteLabel = choice.text ? choice.label : "";
            if (quoteInput) quoteInput.value = choice.text;
          }
          redraw();
        });
        chipsWrap.append(chip);
      });
    }

    if (quoteInput) {
      quoteInput.value = state.quote;
      quoteInput.addEventListener("input", () => {
        state.quote = quoteInput.value;
        state.quoteLabel = "";
        if (chipsWrap && customChip) {
          chipsWrap.querySelectorAll(".story-quote-chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
          customChip.setAttribute("aria-pressed", "true");
        }
        redraw();
      });
    }

    if (gradientSlider) {
      syncSliderFill(gradientSlider);
      const updateGradient = () => {
        state.gradientIntensity = Number(gradientSlider.value);
        if (gradientValue) gradientValue.textContent = `${state.gradientIntensity}%`;
        syncSliderFill(gradientSlider);
        redraw();
      };
      gradientSlider.addEventListener("input", updateGradient);
    }

    if (coverSlider) {
      syncSliderFill(coverSlider);
      const updateCover = () => {
        state.coverScale = Number(coverSlider.value);
        if (coverValue) coverValue.textContent = `${state.coverScale}%`;
        syncSliderFill(coverSlider);
        redraw();
      };
      coverSlider.addEventListener("input", updateCover);
    }

    if (watermarkToggle) {
      watermarkToggle.setAttribute("aria-checked", state.watermark ? "true" : "false");
      watermarkToggle.addEventListener("click", () => {
        state.watermark = !state.watermark;
        watermarkToggle.setAttribute("aria-checked", state.watermark ? "true" : "false");
        redraw();
      });
    }

    modeButtons.forEach((btn) => {
      btn.setAttribute("aria-pressed", btn.dataset.storyMode === state.mode ? "true" : "false");
      btn.addEventListener("click", () => {
        state.mode = btn.dataset.storyMode === "paper" ? "paper" : "dark";
        modeButtons.forEach((b) =>
          b.setAttribute("aria-pressed", b.dataset.storyMode === state.mode ? "true" : "false")
        );
        redraw();
      });
    });

    trigger.addEventListener("click", async () => {
      if (typeof modal.showModal === "function") {
        modal.showModal();
        if (statusNode) statusNode.textContent = "Preparing card…";
        await redraw();
        if (statusNode) statusNode.textContent = "";
      }
    });

    btnClose?.addEventListener("click", () => modal.close());
    modal.addEventListener("click", (ev) => {
      if (ev.target !== modal) return;
      const r = modal.getBoundingClientRect();
      const inside = ev.clientY >= r.top && ev.clientY <= r.bottom && ev.clientX >= r.left && ev.clientX <= r.right;
      if (!inside) modal.close();
    });

    function downloadPng() {
      const slug = context.slug || "signal";
      const a = document.createElement("a");
      a.download = `chaperone-${slug}-story.png`;
      a.href = canvas.toDataURL("image/png");
      a.click();
    }

    btnDownload?.addEventListener("click", () => {
      downloadPng();
      flash(btnDownload, "Card downloaded");
    });

    btnCopyImage?.addEventListener("click", async () => {
      try {
        const res = await copyCanvasImageToClipboard(canvas);
        if (res.ok) {
          flash(btnCopyImage, "Image copied");
        } else if (statusNode) {
          statusNode.textContent = res.reason;
        }
      } catch {
        if (statusNode) {
          statusNode.textContent = "Couldn't copy image to clipboard. Try Download or Share.";
        }
      }
    });

    btnShare?.addEventListener("click", () => {
      canvas.toBlob(async (blob) => {
        if (!blob) {
          downloadPng();
          flash(btnShare, "Card downloaded");
          return;
        }
        const slug = context.slug || "signal";
        const file = new File([blob], `chaperone-${slug}-story.png`, { type: "image/png" });
        const canonical = window.GSIContext?.canonicalHref?.() || window.location.href;
        const shareData = {
          files: [file],
          title: `${context.track || "Signal"} — ${context.artistName || "Chaperone"}`,
          text: `${context.track || ""} by ${context.artistName || ""}`,
          url: canonical,
        };
        if (navigator.canShare && navigator.canShare({ files: [file] })) {
          try {
            const payload = navigator.canShare(shareData)
              ? shareData
              : { files: [file], title: shareData.title, text: shareData.text };
            await navigator.share(payload);
            flash(btnShare, "Share opened");
            return;
          } catch (err) {
            if (err?.name === "AbortError") return;
          }
        }
        downloadPng();
        flash(btnShare, "Card downloaded");
      }, "image/png");
    });

    btnCopyLink?.addEventListener("click", async () => {
      const url = window.GSIContext?.canonicalHref?.() || window.location.href;
      try {
        await navigator.clipboard.writeText(url);
        flash(btnCopyLink, "Link copied");
      } catch {
        flash(btnCopyLink, "Couldn't copy link");
      }
    });
  }

  window.GSIStoryStudio = {
    copyCanvasImageToClipboard,
    initEntryStoryStudio,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initEntryStoryStudio);
  } else {
    initEntryStoryStudio();
  }
})();
