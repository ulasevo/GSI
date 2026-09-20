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
      const updateView = () => {
        document.body.dataset.view = viewName;
        viewButtons.forEach(button => {
          const isActive = button.dataset.view === viewName;
          button.classList.toggle("active", isActive);
          button.setAttribute("aria-pressed", String(isActive));
        });
        storeView(viewName);
        if (sync) syncContext();
      };

      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (!animate || reducedMotion) {
        updateView();
        return;
      }

      // Fade only the grid; moving every card made view changes stutter.
      window.clearTimeout(viewSwitchTimer);
      grid.classList.add("view-switching");
      viewSwitchTimer = window.setTimeout(() => {
        updateView();
        requestAnimationFrame(() => requestAnimationFrame(() => {
          grid.classList.remove("view-switching");
        }));
      }, 110);
    }

    viewButtons.forEach(button => {
      button.addEventListener("click", () => applyView(button.dataset.view));
    });

    return Object.freeze({ applyView });
  }

  window.GSIHomeLayout = Object.freeze({ create });
})();
