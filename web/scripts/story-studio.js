/*
 * Shared 9:16 Interactive Share Card Studio renderer & clipboard/share bridge
 * for Chaperone (GSI) Entry reading rooms.
 * Supports Archival Paper and Dark Room sleeves, quote section chips,
 * custom quote editing, Image-to-Clipboard (ClipboardItem), Web Share, and PNG download.
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
    const tp = context.trackPalette || {};
    const primary = tp.primary || context.accent || "#ff65ad";
    const secondary = tp.secondary || "#35c9e9";
    const glow = tp.glow || primary;
    const surface = tp.surface || "#16131c";

    const palette =
      mode === "paper"
        ? {
            outerTop: mixHex("#14101a", surface, 0.45),
            outerBottom: mixHex("#09070d", primary, 0.14),
            sleeveTop: mixHex("#faf5eb", primary, 0.03),
            sleeveMid: mixHex("#f2eadc", primary, 0.05),
            sleeveBottom: mixHex("#e7decb", secondary, 0.06),
            inkPrimary: "#18131d",
            inkMuted: "#54495d",
            accentRule: mixHex(primary, "#18131d", 0.28),
            noteBg: "rgba(255, 253, 249, 0.72)",
            grainStroke: "rgba(45, 32, 24, 0.03)",
          }
        : {
            outerTop: mixHex("#09080d", surface, 0.52),
            outerBottom: mixHex("#050408", primary, 0.12),
            sleeveTop: mixHex("#18151f", surface, 0.55),
            sleeveMid: mixHex("#121018", primary, 0.14),
            sleeveBottom: mixHex("#0d0b12", secondary, 0.14),
            inkPrimary: "#f7f3ec",
            inkMuted: "rgba(247, 243, 236, 0.72)",
            accentRule: mixHex(primary, "#ffffff", 0.18),
            noteBg: "rgba(255, 255, 255, 0.07)",
            grainStroke: "rgba(255, 255, 255, 0.025)",
          };

    ctx.clearRect(0, 0, 1080, 1920);
    const outerBg = ctx.createLinearGradient(0, 0, 1080, 1920);
    outerBg.addColorStop(0, palette.outerTop);
    outerBg.addColorStop(1, palette.outerBottom);
    ctx.fillStyle = outerBg;
    ctx.fillRect(0, 0, 1080, 1920);

    const glowWash = ctx.createRadialGradient(540, 680, 80, 540, 680, 880);
    glowWash.addColorStop(0, hexToRgba(glow, mode === "dark" ? 0.42 : 0.28));
    glowWash.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = glowWash;
    ctx.fillRect(0, 0, 1080, 1920);

    const sleeve = { x: 54, y: 76, w: 972, h: 1768 };

    // Offset chromatic registration plates
    ctx.fillStyle = "rgba(0, 0, 0, 0.48)";
    drawAsymmRoundRect(ctx, sleeve.x + 12, sleeve.y + 18, sleeve.w, sleeve.h, 18, 44, 18, 44);
    ctx.fill();

    ctx.fillStyle = hexToRgba(secondary, 0.48);
    drawAsymmRoundRect(ctx, sleeve.x + 9, sleeve.y + 9, sleeve.w, sleeve.h, 18, 44, 18, 44);
    ctx.fill();

    ctx.fillStyle = hexToRgba(primary, 0.56);
    drawAsymmRoundRect(ctx, sleeve.x - 8, sleeve.y - 8, sleeve.w, sleeve.h, 18, 44, 18, 44);
    ctx.fill();

    const cover = await loadImg(context.coverSrc, ".cover-frame img.cover");

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
    sleeveGrad.addColorStop(0.55, palette.sleeveMid);
    sleeveGrad.addColorStop(1, palette.sleeveBottom);
    ctx.fillStyle = sleeveGrad;
    ctx.fillRect(sleeve.x, sleeve.y, sleeve.w, sleeve.h);

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
    const spineW = 34;
    const spineGrad = ctx.createLinearGradient(sleeve.x, sleeve.y, sleeve.x, sleeve.y + sleeve.h);
    spineGrad.addColorStop(0, primary);
    spineGrad.addColorStop(0.55, glow);
    spineGrad.addColorStop(1, secondary);
    ctx.fillStyle = spineGrad;
    ctx.fillRect(sleeve.x, sleeve.y, spineW, sleeve.h);

    const contentX = sleeve.x + spineW + 56;
    const contentRight = sleeve.x + sleeve.w - 58;
    const contentW = contentRight - contentX;

    // Header bar
    ctx.fillStyle = primary;
    ctx.fillRect(contentX, 142, 6, 24);
    ctx.fillStyle = secondary;
    ctx.fillRect(contentX + 10, 142, 6, 24);

    ctx.textAlign = "left";
    ctx.fillStyle = palette.inkPrimary;
    ctx.font = '700 30px "Space Grotesk", Arial, sans-serif';
    ctx.fillText("Chaperone", contentX + 28, 165);

    ctx.textAlign = "right";
    ctx.fillStyle = palette.inkMuted;
    ctx.font = '600 22px "Space Grotesk", Arial, sans-serif';
    ctx.fillText(context.inP53 ? "Archive · Radio P53" : "Archive Entry", contentRight, 163);
    ctx.textAlign = "left";

    ctx.fillStyle = hexToRgba(palette.inkPrimary, 0.16);
    ctx.fillRect(contentX, 192, contentW, 2);
    ctx.fillStyle = palette.accentRule;
    ctx.fillRect(contentX, 191, 118, 4);

    // Track / Artist / Album
    const track = String(context.track || "").trim();
    const artist = String(context.artistName || "").trim();
    const album = String(context.album || "").trim();

    let y = 266;
    const trackLen = Array.from(track).length;
    const trackSize = trackLen <= 18 ? 76 : trackLen <= 32 ? 64 : 54;
    const trackLH = trackSize + 8;

    ctx.fillStyle = palette.inkPrimary;
    ctx.font = `800 ${trackSize}px "Space Grotesk", Arial, sans-serif`;
    const trackLines = measureWrappedLines(ctx, track, contentW, 2).lines;
    paintLines(ctx, trackLines, contentX, y, trackLH);
    y += Math.max(1, trackLines.length) * trackLH - 2;

    ctx.fillStyle = palette.inkPrimary;
    ctx.font = '700 38px "Space Grotesk", Arial, sans-serif';
    const artistLines = measureWrappedLines(ctx, artist, contentW, 2).lines;
    paintLines(ctx, artistLines, contentX, y, 46);
    y += Math.max(1, artistLines.length) * 46 + 2;

    if (album) {
      ctx.fillStyle = palette.inkMuted;
      ctx.font = '500 28px "Space Grotesk", Arial, sans-serif';
      const albumLines = measureWrappedLines(ctx, album, contentW, 2).lines;
      paintLines(ctx, albumLines, contentX, y, 36);
      y += Math.max(1, albumLines.length) * 36;
    }

    // Cover artwork in asymmetric Chaperone window
    const coverY = y + 26;
    const coverMaxBottom = quote ? 1046 : 1380;
    const coverSize = Math.min(quote ? 560 : 720, Math.max(quote ? 400 : 520, coverMaxBottom - coverY));
    const coverX = contentX + Math.round((contentW - coverSize) / 2);

    ctx.fillStyle = hexToRgba(secondary, 0.42);
    drawAsymmRoundRect(ctx, coverX + 10, coverY + 10, coverSize, coverSize, 12, 38, 12, 38);
    ctx.fill();
    ctx.fillStyle = hexToRgba(primary, 0.5);
    drawAsymmRoundRect(ctx, coverX - 7, coverY - 7, coverSize, coverSize, 12, 38, 12, 38);
    ctx.fill();

    if (cover) {
      ctx.save();
      drawAsymmRoundRect(ctx, coverX, coverY, coverSize, coverSize, 12, 38, 12, 38);
      ctx.clip();
      const iw = cover.naturalWidth || cover.width || coverSize;
      const ih = cover.naturalHeight || cover.height || coverSize;
      const crop = Math.min(iw, ih);
      ctx.drawImage(cover, (iw - crop) / 2, (ih - crop) / 2, crop, crop, coverX, coverY, coverSize, coverSize);
      ctx.restore();
    } else {
      ctx.fillStyle = surface;
      drawAsymmRoundRect(ctx, coverX, coverY, coverSize, coverSize, 12, 38, 12, 38);
      ctx.fill();
    }

    // Selected Review Excerpt Block
    if (quote) {
      const noteTop = coverY + coverSize + 40;
      const noteMaxBottom = 1520;
      const availH = Math.max(160, noteMaxBottom - noteTop);
      const isLong = Array.from(quote).length > 175;
      const fontSize = isLong ? 38 : 42;
      const lh = isLong ? 52 : 56;
      const headerOffset = quoteLabel ? 46 : 16;
      const maxLines = Math.max(3, Math.floor((availH - headerOffset - 36) / lh));
      const textX = contentX + 32;
      const textW = contentW - 56;

      ctx.font = `500 ${fontSize}px "Space Grotesk", Arial, sans-serif`;
      const measured = measureWrappedLines(ctx, quote, textW, maxLines);
      const boxH = headerOffset + measured.lines.length * lh + 32;

      ctx.fillStyle = palette.noteBg;
      drawRoundRect(ctx, contentX, noteTop, contentW, boxH, 14);
      ctx.fill();

      ctx.strokeStyle = hexToRgba(palette.inkPrimary, 0.14);
      ctx.lineWidth = 1.5;
      drawRoundRect(ctx, contentX, noteTop, contentW, boxH, 14);
      ctx.stroke();

      ctx.fillStyle = palette.accentRule;
      drawRoundRect(ctx, contentX + 12, noteTop + 14, 5, boxH - 28, 2.5);
      ctx.fill();

      if (quoteLabel) {
        ctx.fillStyle = palette.accentRule;
        ctx.font = '700 22px "Space Grotesk", Arial, sans-serif';
        ctx.fillText(quoteLabel.toUpperCase(), textX, noteTop + 36);
      }

      ctx.fillStyle = palette.inkPrimary;
      ctx.font = `500 ${fontSize}px "Space Grotesk", Arial, sans-serif`;
      paintLines(
        ctx,
        measured.lines,
        textX,
        noteTop + headerOffset + Math.round(fontSize * 0.85),
        lh
      );
    }

    // Open breathing room for link sticker + editorial footer
    ctx.fillStyle = hexToRgba(palette.inkPrimary, 0.18);
    ctx.fillRect(contentX, 1744, contentW, 1.5);

    ctx.font = '600 23px "Space Grotesk", Arial, sans-serif';
    ctx.fillStyle = palette.inkMuted;
    ctx.textAlign = "left";
    ctx.fillText("Genome Stability Inducer", contentX, 1790);

    ctx.font = '700 24px "Space Grotesk", Arial, sans-serif';
    ctx.textAlign = "right";
    ctx.fillText("Chaperone", contentRight, 1790);
    ctx.textAlign = "left";

    ctx.restore();

    ctx.strokeStyle = hexToRgba(palette.inkPrimary, 0.16);
    ctx.lineWidth = 2;
    drawAsymmRoundRect(ctx, sleeve.x, sleeve.y, sleeve.w, sleeve.h, 18, 44, 18, 44);
    ctx.stroke();

    canvas.setAttribute("aria-label", `Chaperone story card: ${track} by ${artist}`);
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
    const modeButtons = [...modal.querySelectorAll("[data-story-mode]")];

    const sections = Array.isArray(context.sections) ? context.sections : [];
    const state = {
      mode: document.documentElement.dataset.gsiTheme === "light" ? "paper" : "dark",
      quote: sections[0]?.excerpt || "",
      quoteLabel: sections[0]?.title || "",
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

    // Build quote section chips
    if (chipsWrap) {
      chipsWrap.innerHTML = "";
      const choices = [
        ...sections.map((s) => ({ label: s.title, text: s.excerpt || s.content || "" })),
        { label: "No quote", text: "" },
      ];
      choices.forEach((choice, idx) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "story-quote-chip";
        chip.textContent = choice.label;
        chip.setAttribute("aria-pressed", idx === 0 ? "true" : "false");
        chip.addEventListener("click", () => {
          chipsWrap.querySelectorAll(".story-quote-chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
          chip.setAttribute("aria-pressed", "true");
          state.quote = choice.text;
          state.quoteLabel = choice.text ? choice.label : "";
          if (quoteInput) quoteInput.value = choice.text;
          redraw();
        });
        chipsWrap.append(chip);
      });
    }

    if (quoteInput) {
      quoteInput.value = state.quote;
      quoteInput.addEventListener("input", () => {
        state.quote = quoteInput.value;
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
        if (statusNode) statusNode.textContent = "Rendering 9:16 card…";
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
