/*
 * Artist-room travel helper.
 * It fills in context-aware return links and keeps every song route grounded in
 * the artist room that the visitor just read.
 */
(() => {
  const dataNode = document.querySelector("#artist-room-data");
  if (!dataNode) return;

  let roomData;
  try {
    roomData = JSON.parse(dataNode.textContent || "{}");
  } catch (error) {
    return;
  }

  const filterKeys = Array.isArray(roomData.filterKeys) ? roomData.filterKeys : [];
  const filterLabels = roomData.filterLabels && typeof roomData.filterLabels === "object"
    ? roomData.filterLabels
    : {};

  function syncLinks() {
    const state = GSIContext.read();
    const roomParams = GSIContext.archiveParams({ state, filterKeys });
    const filter = state.get("filter");
    const artistReturn = document.querySelector("#artist-archive-return");
    if (artistReturn) {
      artistReturn.href = GSIContext.href("../index.html", roomParams);
    }

    const filterLink = document.querySelector("#artist-filter-return");
    const contextSeparator = document.querySelector("#artist-context-separator") || document.querySelector("#artist-filter-separator");
    if (filter && Object.hasOwn(filterLabels, filter)) {
      if (filterLink) {
        filterLink.textContent = String(filterLabels[filter]).toUpperCase();
        filterLink.href = GSIContext.href("../index.html", roomParams);
        filterLink.hidden = false;
        if (contextSeparator) contextSeparator.hidden = false;
      }
    } else if (filterLink) {
      filterLink.hidden = true;
      if (contextSeparator) contextSeparator.hidden = true;
    }

    // Both ordinary songs and album-room links use the same context decoration.
    document.querySelectorAll("[data-entry-base-href], [data-context-base-href]").forEach(link => {
      const contextParams = new URLSearchParams(roomParams);
      if (roomData.artistSlug) contextParams.set("artist", roomData.artistSlug);
      const baseHref = link.dataset.entryBaseHref || link.dataset.contextBaseHref;
      link.href = GSIContext.href(baseHref, contextParams);
    });
  }

  syncLinks();
  window.addEventListener("gsi-theme-change", syncLinks);
})();
