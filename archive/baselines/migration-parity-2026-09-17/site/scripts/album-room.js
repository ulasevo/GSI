/* Preserve filter/view/format context while travelling through an album room. */
(() => {
  const dataNode = document.querySelector("#album-room-data");
  if (!dataNode) return;

  let roomData;
  try {
    roomData = JSON.parse(dataNode.textContent || "{}");
  } catch (error) {
    return;
  }

  const state = GSIContext.read();
  const filterKeys = Array.isArray(roomData.filterKeys) ? roomData.filterKeys : [];
  const roomParams = GSIContext.archiveParams({ state, filterKeys });
  const artistParams = new URLSearchParams(roomParams);
  const entryParams = new URLSearchParams(roomParams);
  const incomingArtist = state.get("artist");
  if (incomingArtist) {
    artistParams.set("artist", incomingArtist);
    // Keep an artist-origin route alive when a visitor opens a song from the
    // album room. Direct album visits remain free of an artificial artist query.
    entryParams.set("artist", incomingArtist);
  }
  const returnLink = document.querySelector("#album-archive-return");
  if (returnLink) returnLink.href = GSIContext.href("../index.html", roomParams);

  document.querySelectorAll("[data-artist-base-href]").forEach(link => {
    link.href = GSIContext.href(link.dataset.artistBaseHref, artistParams);
  });

  document.querySelectorAll("[data-entry-base-href]").forEach(link => {
    link.href = GSIContext.href(link.dataset.entryBaseHref, entryParams);
  });
})();
