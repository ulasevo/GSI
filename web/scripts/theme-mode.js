/*
 * Persist the visitor's light/dark preference and carry it through shareable URLs.
 * Light is the first-visit default; the control is shared by every generated
 * room rather than being rebuilt per page.
 */
(() => {
  const storageKey = "gsi-theme";
  const root = document.documentElement;
  const requested = (() => {
    try {
      const value = new URL(window.location.href).searchParams.get("theme");
      return value === "light" || value === "dark" ? value : null;
    } catch { return null; }
  })();
  const stored = (() => {
    try { return localStorage.getItem(storageKey); } catch { return null; }
  })();
  const initial = requested || (stored === "light" || stored === "dark" ? stored : "light");
  const SUN_ICON = '<svg viewBox="0 0 24 24" focusable="false" aria-hidden="true"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"></path></svg>';
  const MOON_ICON = '<svg viewBox="0 0 24 24" focusable="false" aria-hidden="true"><path d="M20.4 15.4A8.5 8.5 0 0 1 8.6 3.6 8.5 8.5 0 1 0 20.4 15.4Z"></path></svg>';

  function setTheme(theme, persist = true) {
    const next = theme === "light" ? "light" : "dark";
    root.dataset.gsiTheme = next;
    if (persist) {
      try { localStorage.setItem(storageKey, next); } catch { /* storage is optional */ }
    }
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("theme", next);
      window.history.replaceState(null, "", `${url.pathname}?${url.searchParams}${url.hash}`);
    } catch { /* URL state is optional in non-browser tests */ }
    const toggle = document.querySelector(".theme-toggle");
    if (!toggle) return;
    const light = next === "light";
    toggle.setAttribute("aria-pressed", String(light));
    toggle.setAttribute("aria-label", light ? "Switch to DIM mode" : "Switch to LIT mode");
    const icon = toggle.querySelector(".theme-toggle__icon");
    const label = toggle.querySelector(".theme-toggle__label");
    if (icon) icon.innerHTML = light ? SUN_ICON : MOON_ICON;
    if (label) label.textContent = light ? "LIT" : "DIM";
  }

  // Set the saved mode before the rest of the document can paint. Room
  // styles are dark-first, so waiting for DOMContentLoaded causes a visible
  // dark flash during back/forward navigation.
  setTheme(initial, false);

  function mount() {
    setTheme(initial, false);
    let toggle = document.querySelector(".theme-toggle");
    if (!toggle) {
      toggle = document.createElement("button");
      toggle.className = "theme-toggle";
      toggle.type = "button";
      toggle.innerHTML = '<span class="theme-toggle__track" aria-hidden="true"><span class="theme-toggle__icon"></span></span><span class="theme-toggle__label"></span>';
      document.body.append(toggle);
      setTheme(root.dataset.gsiTheme, false);
    }
    if (!toggle || toggle.dataset.bound === "true") return;
    toggle.dataset.bound = "true";
    toggle.addEventListener("click", () => setTheme(root.dataset.gsiTheme === "light" ? "dark" : "light"));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount, { once: true });
  else mount();
})();
