/*
 * Album-room travel helper.
 * The album page is static; this script adds the visitor's existing URL context
 * to its return, artist, and song links after the page is visible.
 */
(() => {
  const dataNode = document.querySelector("#album-room-data");
  if (!dataNode) return;

  // JSON keeps route facts out of executable markup and is safe to ignore if a
  // hand-edited page contains malformed data.
  let roomData;
  try {
    roomData = JSON.parse(dataNode.textContent || "{}");
  } catch (error) {
    return;
  }

  // Start with only supported query keys, then preserve an artist-origin path
  // when one was present before the album opened.
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
