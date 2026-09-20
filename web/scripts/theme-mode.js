/*
 * Persist the visitor's light/dark preference without changing the URL.
 * Light is the first-visit default; the control is intentionally small and
 * shared by every generated room rather than being rebuilt per page.
 */
(() => {
  const storageKey = "gsi-theme";
  const root = document.documentElement;
  const stored = (() => {
    try { return localStorage.getItem(storageKey); } catch { return null; }
  })();
  const initial = stored === "light" || stored === "dark" ? stored : "light";

  function setTheme(theme, persist = true) {
    const next = theme === "light" ? "light" : "dark";
    root.dataset.gsiTheme = next;
    if (persist) {
      try { localStorage.setItem(storageKey, next); } catch { /* storage is optional */ }
    }
    const toggle = document.querySelector(".theme-toggle");
    if (!toggle) return;
    const light = next === "light";
    toggle.setAttribute("aria-pressed", String(light));
    toggle.setAttribute("aria-label", light ? "Switch to dark mode" : "Switch to light mode");
    const icon = toggle.querySelector(".theme-toggle__icon");
    const label = toggle.querySelector(".theme-toggle__label");
    if (icon) icon.textContent = light ? "☼" : "☾";
    if (label) label.textContent = light ? "LIGHT" : "DARK";
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
      toggle.innerHTML = '<span class="theme-toggle__icon" aria-hidden="true"></span><span class="theme-toggle__label"></span>';
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
