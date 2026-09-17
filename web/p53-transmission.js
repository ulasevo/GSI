/* Permanent Radio P53 transmission route and sharing behavior. */
(() => {
  const contextNode = document.querySelector("#p53-transmission-context");
  if (!contextNode || !window.GSIContext) return;

  let context;
  try {
    context = JSON.parse(contextNode.textContent || "{}");
  } catch {
    return;
  }

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
    const shareData = { title: context.shareTitle || document.title, text: artistName, url: window.location.href };
    try {
      if (navigator.share) {
        await navigator.share(shareData);
        setShareLabel("SHARED");
        return;
      }
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(window.location.href);
      } else {
        const fallback = document.createElement("textarea");
        fallback.value = window.location.href;
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
})();
