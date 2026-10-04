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
    const existing = document.querySelector(".signal-cover");
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

    const accent = context.accent || "#ff65ad";
    const trackTitle = (context.track || "SIGNAL").trim();
    const artist = (artistName || context.artistName || "GSI ARCHIVE").trim();
    const album = (context.album || "").trim();
    const signalLabel = (context.signalLabel || "CURRENT TRANSMISSION").trim();
    const transmissionNote = (context.transmissionNote || "").trim();
    const slug = (context.slug || "signal").trim();

    // 1. Background Obsidian Gradient
    const bgGrad = ctx.createLinearGradient(0, 0, 1080, 1920);
    bgGrad.addColorStop(0, "#09060d");
    bgGrad.addColorStop(0.48, "#140c1a");
    bgGrad.addColorStop(1, "#070509");
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, 1080, 1920);

    // 2. Ambient Chromatic Spheres
    const auraAccent = ctx.createRadialGradient(540, 640, 40, 540, 640, 680);
    auraAccent.addColorStop(0, hexToRgba(accent, 0.38));
    auraAccent.addColorStop(0.65, hexToRgba(accent, 0.1));
    auraAccent.addColorStop(1, "transparent");
    ctx.fillStyle = auraAccent;
    ctx.fillRect(0, 0, 1080, 1920);

    const auraCyan = ctx.createRadialGradient(260, 1540, 20, 260, 1540, 480);
    auraCyan.addColorStop(0, "rgba(53, 201, 233, 0.16)");
    auraCyan.addColorStop(0.7, "rgba(53, 201, 233, 0.03)");
    auraCyan.addColorStop(1, "transparent");
    ctx.fillStyle = auraCyan;
    ctx.fillRect(0, 0, 1080, 1920);

    // 3. Cybernetic Scanlines
    ctx.fillStyle = "rgba(255, 255, 255, 0.018)";
    for (let y = 0; y < 1920; y += 12) {
      ctx.fillRect(0, y, 1080, 1.5);
    }

    // 4. Perimeter Frame & Corner Crosshairs
    ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
    ctx.lineWidth = 1;
    ctx.strokeRect(56, 56, 968, 1808);

    // Corner bracket marks
    ctx.strokeStyle = accent;
    ctx.lineWidth = 3;
    const cornerSize = 28;
    // Top-Left
    ctx.beginPath();
    ctx.moveTo(56, 56 + cornerSize);
    ctx.lineTo(56, 56);
    ctx.lineTo(56 + cornerSize, 56);
    ctx.stroke();
    // Top-Right
    ctx.beginPath();
    ctx.moveTo(1024 - cornerSize, 56);
    ctx.lineTo(1024, 56);
    ctx.lineTo(1024, 56 + cornerSize);
    ctx.stroke();
    // Bottom-Left
    ctx.beginPath();
    ctx.moveTo(56, 1864 - cornerSize);
    ctx.lineTo(56, 1864);
    ctx.lineTo(56 + cornerSize, 1864);
    ctx.stroke();
    // Bottom-Right
    ctx.beginPath();
    ctx.moveTo(1024 - cornerSize, 1864);
    ctx.lineTo(1024, 1864);
    ctx.lineTo(1024, 1864 - cornerSize);
    ctx.stroke();

    // 5. Header Area
    ctx.fillStyle = hexToRgba(accent, 0.95);
    ctx.font = "900 20px Arial, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("GENOME STABILITY INDUCERS // ARCHIVE", 96, 136);

    ctx.font = "950 68px Impact, Haettenschweiler, 'Arial Black', sans-serif";
    ctx.fillStyle = "#ffffff";
    ctx.fillText("RADIO P53", 96, 210);

    // Status Pill
    const pillText = (signalLabel === "CURRENT TRANSMISSION" ? "CURRENT SIGNAL" : "ARCHIVED SIGNAL");
    ctx.font = "900 16px Arial, sans-serif";
    const pillWidth = ctx.measureText(pillText).width + 48;
    const pillX = 984 - pillWidth;
    ctx.fillStyle = "rgba(255, 255, 255, 0.08)";
    drawRoundRect(ctx, pillX, 168, pillWidth, 36, 18);
    ctx.fill();
    ctx.strokeStyle = "rgba(255, 255, 255, 0.22)";
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.fillStyle = accent;
    ctx.beginPath();
    ctx.arc(pillX + 20, 186, 5, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#ffffff";
    ctx.fillText(pillText, pillX + 34, 192);

    // 6. Cover Artwork
    const coverSize = 700;
    const coverX = 190;
    const coverY = 270;
    const coverRadius = 14;

    // Offset chromatic shadows
    ctx.fillStyle = "rgba(53, 201, 233, 0.42)";
    drawRoundRect(ctx, coverX + 10, coverY + 10, coverSize, coverSize, coverRadius);
    ctx.fill();

    ctx.fillStyle = hexToRgba(accent, 0.38);
    drawRoundRect(ctx, coverX - 8, coverY - 6, coverSize, coverSize, coverRadius);
    ctx.fill();

    // Load and draw cover image
    const coverImg = await loadCoverImage(context.coverSrc);
    if (coverImg) {
      ctx.save();
      drawRoundRect(ctx, coverX, coverY, coverSize, coverSize, coverRadius);
      ctx.clip();
      ctx.drawImage(coverImg, coverX, coverY, coverSize, coverSize);
      ctx.restore();
    } else {
      ctx.fillStyle = "#191220";
      drawRoundRect(ctx, coverX, coverY, coverSize, coverSize, coverRadius);
      ctx.fill();
      ctx.font = "950 160px Impact, sans-serif";
      ctx.fillStyle = "rgba(255, 255, 255, 0.25)";
      ctx.textAlign = "center";
      ctx.fillText("P53", 540, 680);
      ctx.textAlign = "left";
    }

    // Rim stroke
    ctx.strokeStyle = accent;
    ctx.lineWidth = 3;
    drawRoundRect(ctx, coverX, coverY, coverSize, coverSize, coverRadius);
    ctx.stroke();

    // 7. Track & Artist Typography
    let textY = 1045;
    ctx.textAlign = "left";

    // Adaptive font size for Track Title
    let trackFontSize = 66;
    ctx.font = `950 ${trackFontSize}px Impact, Haettenschweiler, 'Arial Black', sans-serif`;
    while (ctx.measureText(trackTitle).width > 888 && trackFontSize > 44) {
      trackFontSize -= 4;
      ctx.font = `950 ${trackFontSize}px Impact, Haettenschweiler, 'Arial Black', sans-serif`;
    }
    ctx.fillStyle = "#ffffff";
    const heightDrawn = wrapText(ctx, trackTitle, 96, textY, 888, trackFontSize * 1.15, 2);
    textY += (heightDrawn > 0 ? heightDrawn : trackFontSize) + 24;

    // Artist
    ctx.font = "900 38px Arial, sans-serif";
    ctx.fillStyle = accent;
    ctx.fillText(artist.toUpperCase(), 96, textY);
    textY += 46;

    // Album
    if (album) {
      ctx.font = "italic 28px Arial, sans-serif";
      ctx.fillStyle = "rgba(255, 255, 255, 0.68)";
      ctx.fillText(album, 96, textY);
      textY += 48;
    }

    // 8. Transmission Note Box
    const boxY = Math.max(textY + 10, 1260);
    const boxHeight = 220;
    ctx.fillStyle = "rgba(255, 255, 255, 0.045)";
    drawRoundRect(ctx, 96, boxY, 888, boxHeight, 10);
    ctx.fill();

    // Accent line on left edge
    ctx.fillStyle = accent;
    ctx.fillRect(96, boxY, 6, boxHeight);

    ctx.font = "900 18px monospace, Arial, sans-serif";
    ctx.fillStyle = "rgba(255, 255, 255, 0.48)";
    ctx.fillText("TRANSMISSION LOG // INTERCEPT", 124, boxY + 38);

    const noteBody = transmissionNote
      ? `“${transmissionNote}”`
      : "Induced audio signal archived in the GSI core. Lossless listening counterpart available.";
    ctx.font = "500 24px Arial, sans-serif";
    ctx.fillStyle = "#faf6ee";
    wrapText(ctx, noteBody, 124, boxY + 84, 820, 36, 3);

    // 9. Waveform Barcode Graphic
    const barCount = 44;
    const barWidth = 9;
    const totalWaveWidth = 888;
    const barSpacing = (totalWaveWidth - (barCount * barWidth)) / (barCount - 1);
    const waveBaseY = 1600;

    for (let i = 0; i < barCount; i++) {
      const charCode = trackTitle.charCodeAt(i % trackTitle.length) || 64;
      const barH = 14 + Math.abs(Math.sin((i + 1) * 0.45 + (charCode % 7)) * 58);
      const bx = 96 + i * (barWidth + barSpacing);
      const by = waveBaseY - (barH / 2);

      if (i % 6 === 0) {
        ctx.fillStyle = accent;
      } else if (i % 5 === 0) {
        ctx.fillStyle = "#35c9e9";
      } else {
        ctx.fillStyle = "rgba(255, 255, 255, 0.35)";
      }
      drawRoundRect(ctx, bx, by, barWidth, barH, 2);
      ctx.fill();
    }

    // 10. Footer Archive Stamp & Link
    ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(96, 1720);
    ctx.lineTo(984, 1720);
    ctx.stroke();

    ctx.font = "900 19px monospace, Arial, sans-serif";
    ctx.fillStyle = "rgba(255, 255, 255, 0.45)";
    ctx.fillText("GSI // SIGNAL ID: " + slug.toUpperCase(), 96, 1775);

    ctx.textAlign = "right";
    ctx.fillStyle = hexToRgba(accent, 0.9);
    ctx.fillText("GSI.FM/P53", 984, 1775);
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
