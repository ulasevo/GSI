/* Shared URL and view-state helpers for generated GSI pages. */
(() => {
  const allowedViews = new Set(["poster", "wall", "gallery"]);

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

  function href(baseHref, params) {
    return `${baseHref}${params.size ? `?${params}` : ""}`;
  }

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

  window.GSIContext = Object.freeze({ allowedViews, read, archiveParams, href, loadView, storeView });
})();
