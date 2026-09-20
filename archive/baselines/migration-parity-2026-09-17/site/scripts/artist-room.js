/* Preserve filter/view/format context while travelling through an artist room. */
(() => {
  const dataNode = document.querySelector("#artist-room-data");
  if (!dataNode) return;

  let roomData;
  try {
    roomData = JSON.parse(dataNode.textContent || "{}");
  } catch (error) {
    return;
  }

  const state = GSIContext.read();
  const filterKeys = Array.isArray(roomData.filterKeys) ? roomData.filterKeys : [];
  const filterLabels = roomData.filterLabels && typeof roomData.filterLabels === "object"
    ? roomData.filterLabels
    : {};
  const roomParams = GSIContext.archiveParams({ state, filterKeys });
  const filter = state.get("filter");
  const artistReturn = document.querySelector("#artist-archive-return");
  if (artistReturn) {
    artistReturn.href = GSIContext.href("../index.html", roomParams);
    artistReturn.textContent = "GSI";
  }

  if (filter && Object.hasOwn(filterLabels, filter)) {
    const filterLink = document.querySelector("#artist-filter-return");
    const separator = document.querySelector("#artist-filter-separator");
    if (filterLink && separator) {
      filterLink.textContent = String(filterLabels[filter]).toUpperCase();
      filterLink.href = GSIContext.href("../index.html", roomParams);
      filterLink.hidden = false;
      separator.hidden = false;
    }
  }

  document.querySelectorAll("[data-entry-base-href], [data-context-base-href]").forEach(link => {
    const contextParams = new URLSearchParams(roomParams);
    if (roomData.artistSlug) contextParams.set("artist", roomData.artistSlug);
    const baseHref = link.dataset.entryBaseHref || link.dataset.contextBaseHref;
    link.href = GSIContext.href(baseHref, contextParams);
  });
})();
