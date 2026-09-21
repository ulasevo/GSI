/*
 * Homepage state helpers.
 * These functions do not touch the DOM. They turn the current filter, layout,
 * and format into predictable values that home-page.js can apply to the page.
 */
(() => {
  const POP_SIGNALS = Object.freeze([
    [12, 16, 26, -900, 3.7],
    [72, 12, 52, -2400, 5.1],
    [42, 36, 34, -600, 4.3],
    [82, 58, 24, -3100, 5.7],
    [18, 70, 58, -1700, 4.9],
    [58, 78, 30, -3800, 6.2],
    [34, 8, 20, -1200, 3.4],
  ]);

  // Keep query-string rules in one place so every generated link carries the
  // same state and never invents an unsupported view or format.
  function contextHref({ baseHref, activeFilter, activeView, activeFormat, activeTheme, allowedViews, allowedThemes = new Set(["light", "dark"]) }) {
    const params = new URLSearchParams();
    if (activeFilter) params.set("filter", activeFilter);
    if (allowedViews.has(activeView)) params.set("view", activeView);
    if (activeFormat === "albums") params.set("format", activeFormat);
    if (allowedThemes.has(activeTheme)) params.set("theme", activeTheme);
    return `${baseHref}${params.size ? `?${params}` : ""}`;
  }

  // Cards keep their tags in data attributes; matching them here keeps album
  // grouping and ordinary song filtering on the same rule.
  function cardMatchesFilter(card, filterName) {
    if (!filterName) return true;
    return (card.dataset.tags || "").split(" ").includes(filterName);
  }

  function signalLabel(count) {
    const amount = Number(count) || 0;
    return `${String(amount).padStart(2, "0")} SIGNAL${amount === 1 ? "" : "S"}`;
  }

  function albumLabel(count) {
    return `${String(Number(count) || 0).padStart(2, "0")} signals`;
  }

  // Return fresh arrays so a decoration pass cannot mutate the source list.
  function popSignals() {
    return POP_SIGNALS.map(signal => [...signal]);
  }

  window.GSIHomeState = Object.freeze({
    contextHref,
    cardMatchesFilter,
    signalLabel,
    albumLabel,
    popSignals,
  });
})();
