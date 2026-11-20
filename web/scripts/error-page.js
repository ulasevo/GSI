/*
 * Signal-lost page behavior.
 * The HTML gives us a stable shell; this helper chooses one real catalogue
 * signal and fills its image, links, and text without embedding data in code.
 */
document.addEventListener("DOMContentLoaded", () => {
  const dataNode = document.querySelector("#error-page-data");
  const data = dataNode ? JSON.parse(dataNode.textContent || "{}") : {};
  const tracks = Array.isArray(data.tracks) ? data.tracks : [];
  const deployedRoot = typeof data.deployedRoot === "string" ? data.deployedRoot : "/";
  const root = location.hostname.endsWith("github.io") ? deployedRoot : "/";
  const favicon = document.querySelector("#favicon");
  const homeLink = document.querySelector("#home-link");
  if (favicon) favicon.href = root + "covers/GSI_favicon.svg";

  function syncThemeLinks(readBaseUrl) {
    if (!window.GSIContext) return;
    const params = GSIContext.archiveParams({ state: GSIContext.read() });
    if (homeLink) homeLink.href = GSIContext.href(root, params);
    const read = document.querySelector("#signal-read");
    if (read && readBaseUrl) read.href = GSIContext.href(readBaseUrl, params);
  }

  if (!tracks.length) {
    syncThemeLinks("");
    window.addEventListener("gsi-theme-change", () => syncThemeLinks(""));
    return;
  }

  // A different existing signal on each visit keeps the recovery page alive
  // without inventing a recommendation or storing visitor history.
  const selected = tracks[Math.floor(Math.random() * tracks.length)];
  const card = document.querySelector("#recommendation");
  const cover = document.querySelector("#signal-cover");
  if (card) card.style.setProperty("--accent", selected.accent || "#ff4fa3");
  if (cover) {
    cover.src = root + "covers/" + (selected.cover || "");
    cover.alt = (selected.album || "Signal") + " cover";
  }
  const track = document.querySelector("#signal-track");
  const artist = document.querySelector("#signal-artist");
  const spotify = document.querySelector("#signal-spotify");
  const apple = document.querySelector("#signal-apple");
  const read = document.querySelector("#signal-read");
  if (track) track.textContent = selected.track || "";
  if (artist) artist.textContent = selected.artist || "";
  if (spotify) spotify.href = selected.spotify || "#";
  if (apple) apple.href = selected.apple || "#";
  const readBaseUrl = root + (selected.url || "");
  if (read) read.href = readBaseUrl;
  syncThemeLinks(readBaseUrl);
  window.addEventListener("gsi-theme-change", () => syncThemeLinks(readBaseUrl));
});
