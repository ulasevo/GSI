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

  // Sharing is progressively enhanced: native share first, clipboard second,
  // and a short-lived textarea only as the final browser fallback.
  const shareButton = document.querySelector("#share-transmission");
  if (!shareButton) return;
  let shareLabelTimer;
  const setShareLabel = label => {
    window.clearTimeout(shareLabelTimer);
    shareButton.textContent = label;
    if (label !== "SHARE") {
      shareLabelTimer = window.setTimeout(() => { shareButton.textContent = "SHARE"; }, 2200);
    }
  };

  shareButton.addEventListener("click", async () => {
    const shareUrl = GSIContext.canonicalHref();
    const shareData = { title: context.shareTitle || document.title, text: artistName, url: shareUrl };
    try {
      if (navigator.share) {
        await navigator.share(shareData);
        setShareLabel("SHARED");
        return;
      }
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
        if (!copied) throw new Error("Copy command unavailable");
      }
      setShareLabel("LINK COPIED");
    } catch (error) {
      if (error?.name !== "AbortError") setShareLabel("COPY UNAVAILABLE");
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
