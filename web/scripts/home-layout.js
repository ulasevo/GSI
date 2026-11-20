/*
 * Homepage layout control.
 * This module only changes the active layout and the short grid transition;
 * card geometry remains in the homepage stylesheet.
 */
(() => {
  function create({ viewButtons, grid, allowedViews, storeView, syncContext }) {
    let viewSwitchTimer = null;

    function applyView(viewName, animate = true, sync = true) {
      if (!allowedViews.has(viewName)) viewName = "wall";
      const previousView = document.body.dataset.view;
      viewButtons.forEach(button => {
        const isActive = button.dataset.view === viewName;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-pressed", String(isActive));
      });
      storeView(viewName);

      const commitView = () => {
        document.body.dataset.view = viewName;
        if (sync) syncContext();
      };

      const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (animate && !reduced && previousView && previousView !== viewName) {
        window.clearTimeout(viewSwitchTimer);
        grid.classList.add("view-switching");
        viewSwitchTimer = window.setTimeout(() => {
          commitView();
          window.requestAnimationFrame(() => {
            grid.classList.remove("view-switching");
          });
        }, 80);
      } else {
        window.clearTimeout(viewSwitchTimer);
        grid.classList.remove("view-switching");
        commitView();
      }
    }

    viewButtons.forEach(button => {
      button.addEventListener("click", () => applyView(button.dataset.view));
    });

    return Object.freeze({ applyView });
  }

  window.GSIHomeLayout = Object.freeze({ create });
})();
