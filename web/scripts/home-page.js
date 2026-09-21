/*
 * Homepage coordinator.
 * The smaller browser modules own one responsibility each; this file wires
 * their shared state and keeps the generated page's public entry point stable.
 */
document.addEventListener("DOMContentLoaded", () => {
  const homeState = window.GSIHomeState;
  const homeLayout = window.GSIHomeLayout;
  const homeFormat = window.GSIHomeFormat;
  const homeFilters = window.GSIHomeFilters;
  if (!homeState || !homeLayout || !homeFormat || !homeFilters || !window.GSIContext) return;

  // Cache the page elements once; individual modules receive only what they own.
  const viewButtons = document.querySelectorAll(".view-btn");
  const formatButtons = document.querySelectorAll(".format-option");
  const formatControl = document.querySelector(".format-control");
  const allowedViews = GSIContext.allowedViews;
  const filterDataNode = document.querySelector("#gsi-filter-data");
  const filterInfo = filterDataNode ? JSON.parse(filterDataNode.textContent || "{}") : {};
  const buttons = document.querySelectorAll(".filter-btn");
  const cards = document.querySelectorAll(".card");
  const grid = document.querySelector(".grid");
  const state = { activeFilter: null, activeFormat: "songs" };

  // This is the one place that mirrors the live state into links and the URL.
  function contextHref(baseHref) {
    return homeState.contextHref({
      baseHref,
      activeFilter: state.activeFilter,
      activeView: document.body.dataset.view,
      activeFormat: state.activeFormat,
      activeTheme: document.documentElement.dataset.gsiTheme,
      allowedViews,
      allowedThemes: GSIContext.allowedThemes,
    });
  }

  function syncContext() {
    document.querySelectorAll("[data-base-href], [data-group-base-href]").forEach(link => {
      link.href = contextHref(link.dataset.baseHref || link.dataset.groupBaseHref);
    });
    const params = new URLSearchParams();
    if (state.activeFilter) params.set("filter", state.activeFilter);
    if (allowedViews.has(document.body.dataset.view)) params.set("view", document.body.dataset.view);
    if (state.activeFormat === "albums") params.set("format", state.activeFormat);
    const activeTheme = GSIContext.currentTheme();
    if (activeTheme) params.set("theme", activeTheme);
    const query = params.size ? `?${params}` : "";
    window.history.replaceState(null, "", `${window.location.pathname}${query}${window.location.hash}`);
  }

  const layout = homeLayout.create({
    viewButtons,
    grid,
    allowedViews,
    storeView: viewName => GSIContext.storeView(viewName),
    syncContext,
  });

  const format = homeFormat.create({
    state,
    formatButtons,
    formatControl,
    cards,
    grid,
    homeState,
    contextHref,
    syncContext,
  });

  const filters = homeFilters.create({
    state,
    filterInfo,
    buttons,
    box: document.querySelector("#filter-description-box"),
    title: document.querySelector("#filter-title"),
    description: document.querySelector("#filter-description"),
    playlistCard: document.querySelector("#playlist-card"),
    playlistCover: document.querySelector("#playlist-cover"),
    playlistCta: document.querySelector("#playlist-cta"),
    layoutFormatControls: document.querySelector(".layout-format-controls"),
    filterCount: document.querySelector("#filter-count"),
    filterRoomLabel: document.querySelector("#filter-room-label"),
    filterDecor: document.querySelector("#filter-decor"),
    homeState,
    renderFilterAlbumGroups: format.renderFilterAlbumGroups,
    syncContext,
  });

  // URL state wins; local storage is only a layout convenience for a bare URL.
  const requestedState = GSIContext.read();
  const requestedView = requestedState.get("view");
  const requestedFilter = requestedState.get("filter");
  const requestedFormat = requestedState.get("format");
  const savedView = GSIContext.loadView("wall");
  layout.applyView(allowedViews.has(requestedView) ? requestedView : savedView, false, false);
  format.applyFormat(requestedFormat === "albums" ? "albums" : "songs", false);
  if (requestedFilter && Object.hasOwn(filterInfo, requestedFilter)) {
    filters.setFilter(requestedFilter, false, false);
  } else {
    filters.clearFilter(false);
  }
  syncContext();
});
