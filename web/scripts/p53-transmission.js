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

  // Apply the per-page accent and watermark label at runtime so the template
  // stays free of page-specific style attributes.
  if (context.accent) document.body.style.setProperty("--accent", context.accent);
  if (context.signalLabel) document.body.style.setProperty("--signal-label", JSON.stringify(context.signalLabel));

  const archiveState = GSIContext.read();
  const filterLabels = context.filterLabels || {};
  const filter = archiveState.get("filter");
  const artistRoute = archiveState.get("artist");
  const expectedArtistRoute = context.expectedArtistRoute || "";
  const artistName = context.artistName || "";
  const archiveParams = GSIContext.archiveParams({ state: archiveState, filterLabels });
  const archiveHref = GSIContext.href("../index.html", archiveParams);

  document.querySelectorAll("#p53-trace-archive").forEach(link => { link.href = archiveHref; });

  const p53IndexLink = document.querySelector("#p53-radio-index");
  if (p53IndexLink) {
    const p53IndexParams = new URLSearchParams(archiveParams);
    if (artistRoute === expectedArtistRoute) p53IndexParams.set("artist", artistRoute);
    p53IndexLink.href = `index.html${p53IndexParams.size ? `?${p53IndexParams}` : ""}`;
  }

  if (filter && Object.hasOwn(filterLabels, filter)) {
    const traceFilter = document.querySelector("#p53-trace-filter");
    if (traceFilter) {
      traceFilter.textContent = filterLabels[filter];
      traceFilter.href = archiveHref;
      traceFilter.classList.remove("hidden");
      document.querySelector("#p53-trace-filter-separator")?.classList.remove("hidden");
    }
  }

  if (artistRoute === expectedArtistRoute) {
    const traceArtist = document.querySelector("#p53-trace-artist");
    if (traceArtist) {
      traceArtist.textContent = artistName.toUpperCase();
      traceArtist.href = `../artists/${artistRoute}.html${archiveParams.size ? `?${archiveParams}` : ""}`;
      traceArtist.classList.remove("hidden");
      document.querySelector("#p53-trace-artist-separator")?.classList.remove("hidden");
    }
  }

  const entryCounterpart = document.querySelector(".entry-counterpart");
  if (entryCounterpart) {
    const entryParams = new URLSearchParams(archiveParams);
    if (artistRoute === expectedArtistRoute) entryParams.set("artist", artistRoute);
    entryCounterpart.href = `${entryCounterpart.href}${entryParams.size ? `?${entryParams}` : ""}`;
  }

  // Story Card generator & native mobile sharing controller.
  const shareButton = document.querySelector("#share-transmission");
  const storyModal = document.querySelector("#story-modal");
  const modalClose = document.querySelector("#story-modal-close");
  const btnShare = document.querySelector("#story-btn-share");
  const btnDownload = document.querySelector("#story-btn-download");
  const btnCopy = document.querySelector("#story-btn-copy");
  const canvas = document.querySelector("#story-card-canvas");

  let cardRendered = false;

  function hexToRgba(hex, alpha) {
    if (!hex || typeof hex !== "string") return `rgba(255, 101, 173, ${alpha})`;
    let clean = hex.replace("#", "").trim();
    if (clean.length === 3) {
      clean = clean.split("").map(c => c + c).join("");
    }
    if (clean.length !== 6) return `rgba(255, 101, 173, ${alpha})`;
    const r = parseInt(clean.substring(0, 2), 16);
    const g = parseInt(clean.substring(2, 4), 16);
    const b = parseInt(clean.substring(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
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

  function wrapText(ctx, text, x, y, maxWidth, lineHeight, maxLines) {
    const words = (text || "").split(/\s+/);
    let line = "";
    let linesDrawn = 0;

    for (let n = 0; n < words.length; n++) {
      const testLine = line + (line ? " " : "") + words[n];
      const metrics = ctx.measureText(testLine);
      if (metrics.width > maxWidth && n > 0) {
        ctx.fillText(line, x, y + (linesDrawn * lineHeight));
        line = words[n];
        linesDrawn++;
        if (linesDrawn >= maxLines - 1) {
          let remaining = words.slice(n).join(" ");
          while (ctx.measureText(remaining + "...").width > maxWidth && remaining.length > 0) {
            remaining = remaining.substring(0, remaining.lastIndexOf(" ") || remaining.length - 1);
          }
          ctx.fillText(remaining + "...", x, y + (linesDrawn * lineHeight));
          linesDrawn++;
          return linesDrawn * lineHeight;
        }
      } else {
        line = testLine;
      }
    }
    if (line && linesDrawn < maxLines) {
      ctx.fillText(line, x, y + (linesDrawn * lineHeight));
      linesDrawn++;
    }
    return linesDrawn * lineHeight;
  }

  async function loadCoverImage(src) {
    if (!src) return null;
    const existing = document.querySelector(`.signal-cover[src*="${src.split('/').pop()}"]`) ||
      (src.includes("P53_cover") ? document.querySelector(".protein-panel img") : document.querySelector(".signal-cover"));
    if (existing && existing.complete && existing.naturalWidth > 0) {
      return existing;
    }
    return new Promise(resolve => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = src;
    });
  }

  async function renderStoryCard() {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const trackAccent = context.trackAccent || context.accent || "#ff65ad";
    const p53Accent = context.p53Accent || "#ff65ad";
    const cyanAccent = context.cyanAccent || "#35c9e9";
    const trackPalette = context.trackPalette || {};
    const primaryColor = trackPalette.primary || trackAccent;
    const glowColor = trackPalette.glow || trackAccent;
    const fieldColor = trackPalette.field || "#0c0812";

    const trackTitle = (context.track || "SIGNAL").trim();
    const artist = (artistName || context.artistName || "GSI ARCHIVE").trim();
    const album = (context.album || "").trim();
    const signalLabel = (context.signalLabel || "CURRENT TRANSMISSION").trim();
    const transmissionNote = (context.transmissionNote || "").trim();
    const slug = (context.slug || "signal").trim();

    // 1. Base Atmospheric Obsidian Gradient (tinted with track field color)
    const bgGrad = ctx.createLinearGradient(0, 0, 1080, 1920);
    bgGrad.addColorStop(0, fieldColor);
    bgGrad.addColorStop(0.32, "#130a1b");
    bgGrad.addColorStop(0.78, "#070409");
    bgGrad.addColorStop(1, "#040206");
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, 1080, 1920);

    // 2. Expressive P53 Protein Artwork Fusion Layer
    const p53Img = await loadCoverImage(context.p53CoverSrc || "../covers/P53_cover-runtime.webp");
    if (p53Img) {
      ctx.save();
      ctx.globalAlpha = 0.28;
      ctx.drawImage(p53Img, -50, -20, 1180, 940);
      ctx.restore();

      // Atmospheric gradient fade over protein art to merge into the dark room
      const fadeGrad = ctx.createLinearGradient(0, 80, 0, 960);
      fadeGrad.addColorStop(0, "transparent");
      fadeGrad.addColorStop(0.6, "rgba(9, 6, 13, 0.62)");
      fadeGrad.addColorStop(1, "rgba(7, 4, 9, 0.98)");
      ctx.fillStyle = fadeGrad;
      ctx.fillRect(0, 0, 1080, 960);
    }

    // 3. Colored Ambient Lighting Halos
    // Hero artwork center glow (using track's primary & glow color)
    const heroGlow = ctx.createRadialGradient(540, 680, 60, 540, 680, 640);
    heroGlow.addColorStop(0, hexToRgba(primaryColor, 0.44));
    heroGlow.addColorStop(0.52, hexToRgba(glowColor, 0.16));
    heroGlow.addColorStop(1, "transparent");
    ctx.fillStyle = heroGlow;
    ctx.fillRect(0, 0, 1080, 1920);

    // Bottom cyan counter-glow (P53 signature electric hue)
    const cyanGlow = ctx.createRadialGradient(180, 1500, 20, 180, 1500, 480);
    cyanGlow.addColorStop(0, "rgba(53, 201, 233, 0.15)");
    cyanGlow.addColorStop(1, "transparent");
    ctx.fillStyle = cyanGlow;
    ctx.fillRect(0, 0, 1080, 1920);

    // 4. Subtle Scanlines
    ctx.fillStyle = "rgba(255, 255, 255, 0.016)";
    for (let y = 0; y < 1920; y += 14) {
      ctx.fillRect(0, y, 1080, 1.5);
    }

    // 5. Minimalist Corner Alignment Ticks (within Story safe bounds)
    ctx.strokeStyle = "rgba(255, 255, 255, 0.22)";
    ctx.lineWidth = 1.5;
    const tickLen = 18;
    // Top-Left (72, 140)
    ctx.beginPath();
    ctx.moveTo(72, 140 + tickLen);
    ctx.lineTo(72, 140);
    ctx.lineTo(72 + tickLen, 140);
    ctx.stroke();
    // Top-Right (1008, 140)
    ctx.beginPath();
    ctx.moveTo(1008 - tickLen, 140);
    ctx.lineTo(1008, 140);
    ctx.lineTo(1008, 140 + tickLen);
    ctx.stroke();
    // Bottom-Left (72, 1780)
    ctx.beginPath();
    ctx.moveTo(72, 1780 - tickLen);
    ctx.lineTo(72, 1780);
    ctx.lineTo(72 + tickLen, 1780);
    ctx.stroke();
    // Bottom-Right (1008, 1780)
    ctx.beginPath();
    ctx.moveTo(1008 - tickLen, 1780);
    ctx.lineTo(1008, 1780);
    ctx.lineTo(1008, 1780 - tickLen);
    ctx.stroke();

    // 6. Header: Pure Radio P53 Identity
    ctx.font = "900 18px Arial, sans-serif";
    ctx.fillStyle = "rgba(250, 246, 238, 0.65)";
    ctx.textAlign = "left";
    ctx.fillText("GENOME STABILITY INDUCERS", 96, 156);

    // Chromatic Aberration Title
    ctx.font = "950 64px Impact, Haettenschweiler, 'Arial Black', sans-serif";
    // Cyan shift
    ctx.fillStyle = cyanAccent;
    ctx.fillText("RADIO P53", 96 + 4, 226);
    // Magenta shift
    ctx.fillStyle = p53Accent;
    ctx.fillText("RADIO P53", 96 - 3, 226);
    // Foreground crisp white
    ctx.fillStyle = "#ffffff";
    ctx.fillText("RADIO P53", 96, 226);

    // Status Pill (Right aligned)
    const pillText = (signalLabel === "CURRENT TRANSMISSION" ? "CURRENT SIGNAL" : "ARCHIVED SIGNAL");
    ctx.font = "900 15px Arial, sans-serif";
    const pillWidth = ctx.measureText(pillText).width + 46;
    const pillX = 984 - pillWidth;
    ctx.fillStyle = "rgba(255, 255, 255, 0.07)";
    drawRoundRect(ctx, pillX, 182, pillWidth, 38, 19);
    ctx.fill();
    ctx.strokeStyle = "rgba(255, 255, 255, 0.22)";
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.fillStyle = primaryColor;
    ctx.beginPath();
    ctx.arc(pillX + 18, 201, 5, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#faf6ee";
    ctx.fillText(pillText, pillX + 32, 207);

    // 7. Center Hero Cover Art with Asymmetric Brutalist Framing
    const coverSize = 760;
    const coverX = 160;
    const coverY = 280;
    // GSI's signature asymmetrical brutalist corners (18px 56px 18px 56px)
    const rTL = 18, rTR = 56, rBR = 18, rBL = 56;

    // Offset Chromatic Shadows
    ctx.fillStyle = "rgba(53, 201, 233, 0.44)";
    drawAsymmRoundRect(ctx, coverX + 12, coverY + 12, coverSize, coverSize, rTL, rTR, rBR, rBL);
    ctx.fill();

    ctx.fillStyle = hexToRgba(primaryColor, 0.42);
    drawAsymmRoundRect(ctx, coverX - 8, coverY - 6, coverSize, coverSize, rTL, rTR, rBR, rBL);
    ctx.fill();

    // Draw Cover Art
    const coverImg = await loadCoverImage(context.coverSrc);
    if (coverImg) {
      ctx.save();
      drawAsymmRoundRect(ctx, coverX, coverY, coverSize, coverSize, rTL, rTR, rBR, rBL);
      ctx.clip();
      ctx.drawImage(coverImg, coverX, coverY, coverSize, coverSize);
      ctx.restore();
    } else {
      ctx.fillStyle = "#16111f";
      drawAsymmRoundRect(ctx, coverX, coverY, coverSize, coverSize, rTL, rTR, rBR, rBL);
      ctx.fill();
      ctx.font = "950 160px Impact, sans-serif";
      ctx.fillStyle = "rgba(255, 255, 255, 0.25)";
      ctx.textAlign = "center";
      ctx.fillText("P53", 540, 700);
      ctx.textAlign = "left";
    }

    // Outer Rim Stroke
    ctx.strokeStyle = primaryColor;
    ctx.lineWidth = 2.5;
    drawAsymmRoundRect(ctx, coverX, coverY, coverSize, coverSize, rTL, rTR, rBR, rBL);
    ctx.stroke();

    // 8. Track, Artist & Album Core
    let textY = 1115;
    ctx.textAlign = "left";

    // Dynamic Adaptive Title Sizing
    let trackFontSize = 72;
    ctx.font = `950 ${trackFontSize}px Impact, Haettenschweiler, 'Arial Black', sans-serif`;
    while (ctx.measureText(trackTitle).width > 860 && trackFontSize > 46) {
      trackFontSize -= 4;
      ctx.font = `950 ${trackFontSize}px Impact, Haettenschweiler, 'Arial Black', sans-serif`;
    }
    ctx.fillStyle = "#ffffff";
    const heightDrawn = wrapText(ctx, trackTitle, 160, textY, 760, trackFontSize * 1.12, 2);
    textY += (heightDrawn > 0 ? heightDrawn : trackFontSize) + 24;

    // Artist in vibrant cover accent
    ctx.font = "900 38px Arial, sans-serif";
    ctx.fillStyle = primaryColor;
    ctx.fillText(artist.toUpperCase(), 160, textY);
    textY += 46;

    // Album in soft muted italic
    if (album) {
      ctx.font = "italic 26px Arial, sans-serif";
      ctx.fillStyle = "rgba(250, 246, 238, 0.68)";
      ctx.fillText(album, 160, textY);
      textY += 44;
    }

    // 9. Transmission Note (only rendered if user wrote a note)
    if (transmissionNote) {
      const quoteY = Math.max(textY + 14, 1310);
      const quoteBoxW = 760;
      ctx.font = "500 27px Arial, sans-serif";
      const lines = [];
      const words = transmissionNote.split(/\s+/);
      let curLine = "";
      for (const w of words) {
        const test = curLine ? `${curLine} ${w}` : w;
        if (ctx.measureText(test).width > quoteBoxW - 84 && curLine) {
          lines.push(curLine);
          curLine = w;
          if (lines.length >= 2) break;
        } else {
          curLine = test;
        }
      }
      if (curLine && lines.length < 3) lines.push(curLine);
      const quoteBoxH = Math.max(100, lines.length * 40 + 36);

      // Frosted Quote Card
      ctx.fillStyle = "rgba(255, 255, 255, 0.04)";
      drawRoundRect(ctx, 160, quoteY, quoteBoxW, quoteBoxH, 12);
      ctx.fill();

      // Accent line on left edge
      ctx.fillStyle = primaryColor;
      drawRoundRect(ctx, 160, quoteY, 5, quoteBoxH, 2.5);
      ctx.fill();

      // Expressive quote mark
      ctx.font = "950 50px Impact, sans-serif";
      ctx.fillStyle = hexToRgba(primaryColor, 0.5);
      ctx.fillText("“", 184, quoteY + 48);

      // Quote body
      ctx.font = "500 26px Arial, sans-serif";
      ctx.fillStyle = "#faf6ee";
      for (let i = 0; i < lines.length; i++) {
        ctx.fillText(lines[i], 224, quoteY + 42 + (i * 38));
      }
    }

    // 10. Reserved link zone: clean pill dock for the user's Instagram link sticker
    const dockY = transmissionNote ? 1530 : 1480;
    const dockH = 80;
    const dockW = 760;
    const dockX = 160;

    ctx.fillStyle = "rgba(255, 255, 255, 0.05)";
    drawRoundRect(ctx, dockX, dockY, dockW, dockH, 40);
    ctx.fill();

    ctx.strokeStyle = hexToRgba(primaryColor, 0.6);
    ctx.lineWidth = 1.5;
    ctx.setLineDash([8, 6]);
    drawRoundRect(ctx, dockX, dockY, dockW, dockH, 40);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = "rgba(250, 246, 238, 0.85)";
    ctx.font = "900 22px Arial, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("LISTEN TO TRANSMISSION ↗", 540, dockY + 49);
    ctx.textAlign = "left";

    // 11. Bottom Archival Rule
    ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(96, 1710);
    ctx.lineTo(984, 1710);
    ctx.stroke();

    ctx.font = "900 16px Arial, sans-serif";
    ctx.fillStyle = "rgba(255, 255, 255, 0.38)";
    ctx.fillText("RADIO P53", 96, 1754);

    ctx.textAlign = "right";
    ctx.fillStyle = hexToRgba(primaryColor, 0.85);
    ctx.fillText(slug.toUpperCase(), 984, 1754);
    ctx.textAlign = "left";

    cardRendered = true;
  }

  function flashButton(btn, text) {
    if (!btn) return;
    const original = btn.textContent;
    btn.textContent = text;
    window.setTimeout(() => { btn.textContent = original; }, 2200);
  }

  function triggerDownload() {
    if (!canvas) return;
    const slug = context.slug || "signal";
    const dataUrl = canvas.toDataURL("image/png");
    const link = document.createElement("a");
    link.download = `p53-${slug}-story.png`;
    link.href = dataUrl;
    link.click();
  }

  if (shareButton) {
    shareButton.addEventListener("click", async () => {
      if (storyModal && typeof storyModal.showModal === "function") {
        storyModal.showModal();
        if (!cardRendered) {
          await renderStoryCard();
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

  modalClose?.addEventListener("click", () => {
    storyModal?.close();
  });

  storyModal?.addEventListener("click", event => {
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
    canvas.toBlob(async blob => {
      if (!blob) {
        triggerDownload();
        flashButton(btnShare, "SAVED TO DEVICE ✓");
        return;
      }
      const slug = context.slug || "signal";
      const fileName = `p53-${slug}-transmission.png`;
      const file = new File([blob], fileName, { type: "image/png" });

      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        try {
          await navigator.share({
            files: [file],
            title: context.shareTitle || `Radio P53 — ${context.track || "Transmission"}`,
            text: `Radio P53 transmission: ${context.track || ""} by ${artistName} on GSI`,
          });
          flashButton(btnShare, "SHARED TO APP ✓");
          return;
        } catch (err) {
          if (err.name === "AbortError") return;
        }
      }
      triggerDownload();
      flashButton(btnShare, "CARD DOWNLOADED ✓");
    }, "image/png");
  });

  btnDownload?.addEventListener("click", () => {
    triggerDownload();
    flashButton(btnDownload, "CARD DOWNLOADED ✓");
  });

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
        document.execCommand("copy");
        fallback.remove();
      }
      flashButton(btnCopy, "LINK COPIED ✓");
    } catch {
      flashButton(btnCopy, "COPY FAILED");
    }
  });

  // 30-Second Signal Audition Controller
  (() => {
    const btn = document.querySelector(".audition-trigger");
    if (!btn) return;
    const url = btn.dataset.previewUrl;
    if (!url) return;
    let audio = null;

    btn.addEventListener("click", () => {
      if (!audio) {
        audio = new Audio(url);
        audio.addEventListener("ended", () => {
          btn.classList.remove("is-playing");
          btn.innerHTML = 'PEEK <span class="peek-icon">▶</span>';
          document.body.classList.remove("signal-auditioning");
        });
        audio.addEventListener("error", () => {
          btn.textContent = "Preview unavailable";
          btn.disabled = true;
          document.body.classList.remove("signal-auditioning");
        });
      }
      if (audio.paused) {
        audio.play().then(() => {
          btn.classList.add("is-playing");
          btn.innerHTML = 'PEEKING <span class="peek-icon">⏸</span>';
          document.body.classList.add("signal-auditioning");
        }).catch(() => {
          btn.textContent = "Playback blocked";
        });
      } else {
        audio.pause();
        btn.classList.remove("is-playing");
        btn.innerHTML = 'PEEK <span class="peek-icon">▶</span>';
        document.body.classList.remove("signal-auditioning");
      }
    });

    window.addEventListener("pagehide", () => {
      if (audio) {
        audio.pause();
        audio = null;
      }
    });
  })();

})();
