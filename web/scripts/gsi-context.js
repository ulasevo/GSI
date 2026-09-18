/*
 * Shared URL and view-state helpers for generated GSI pages.
 * This file does not render cards; it keeps filter, layout, format, and artist
 * context consistent while a visitor moves between generated pages.
 */
(() => {
  // These are the only layouts the homepage and its return links understand.
  const allowedViews = new Set(["poster", "wall", "gallery"]);

  // Read the current URL at the moment a helper is called, not only at load time.
  function read() {
    return new URLSearchParams(window.location.search);
  }

  function archiveParams({ state = read(), filterLabels = {}, filterKeys = [] } = {}) {
    const params = new URLSearchParams();
    const filter = state.get("filter");
    const validFilters = filterKeys.length ? filterKeys : Object.keys(filterLabels);
    if (filter && validFilters.includes(filter)) params.set("filter", filter);
    const view = state.get("view");
    if (allowedViews.has(view)) params.set("view", view);
    if (state.get("format") === "albums") params.set("format", "albums");
    return params;
  }

  // Keep URL construction boring and predictable so callers can add context
  // without hand-writing query-string punctuation.
  function href(baseHref, params) {
    return `${baseHref}${params.size ? `?${params}` : ""}`;
  }

  // A shared link should identify the page itself, not the temporary filter or
  // layout that happened to be active when someone pressed Share.
  function canonicalHref(location = window.location) {
    const url = new URL(location.href);
    url.search = "";
    url.hash = "";
    return url.href;
  }

  // The last layout is a convenience only; a broken storage area falls back to
  // the supplied default and never blocks the page.
  function loadView(fallback = "wall") {
    try {
      return localStorage.getItem("gsi-view") || fallback;
    } catch (error) {
      return fallback;
    }
  }

  function storeView(viewName) {
    try {
      localStorage.setItem("gsi-view", viewName);
    } catch (error) {
      // The view remains usable when storage is unavailable.
    }
  }

  window.GSIContext = Object.freeze({
    allowedViews,
    read,
    archiveParams,
    href,
    canonicalHref,
    loadView,
    storeView,
  });
})();
