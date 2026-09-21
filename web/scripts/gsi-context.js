/*
 * Shared URL and view-state helpers for generated GSI pages.
 * This file does not render cards; it keeps filter, layout, format, and artist
 * context consistent while a visitor moves between generated pages.
 */
(() => {
  // These are the only layouts the homepage and its return links understand.
  const allowedViews = new Set(["poster", "wall", "gallery"]);
  const allowedThemes = new Set(["light", "dark"]);

  // Read the current URL at the moment a helper is called, not only at load time.
  function read() {
    return new URLSearchParams(window.location.search);
  }

  function currentTheme(state = read()) {
    const queryTheme = state.get("theme");
    if (allowedThemes.has(queryTheme)) return queryTheme;
    const documentTheme = typeof document !== "undefined" ? document.documentElement.dataset.gsiTheme : "";
    return allowedThemes.has(documentTheme) ? documentTheme : "";
  }

  function archiveParams({ state = read(), filterLabels = {}, filterKeys = [] } = {}) {
    const params = new URLSearchParams();
    const filter = state.get("filter");
    const validFilters = filterKeys.length ? filterKeys : Object.keys(filterLabels);
    if (filter && validFilters.includes(filter)) params.set("filter", filter);
    const view = state.get("view");
    if (allowedViews.has(view)) params.set("view", view);
    if (state.get("format") === "albums") params.set("format", "albums");
    const theme = currentTheme(state);
    if (theme) params.set("theme", theme);
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
    const theme = currentTheme(url.searchParams);
    url.search = "";
    url.hash = "";
    if (theme) url.searchParams.set("theme", theme);
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
    allowedThemes,
    currentTheme,
    read,
    archiveParams,
    href,
    canonicalHref,
    loadView,
    storeView,
  });
})();
