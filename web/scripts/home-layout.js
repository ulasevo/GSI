/*
 * Homepage layout control.
 * This module only changes the active layout and the short grid transition;
 * card geometry remains in the homepage stylesheet.
 */
(() => {
  function create({ viewButtons, grid, allowedViews, storeView, syncContext }) {
    let viewSwitchTimer = null;

    const cycleBtn = document.querySelector("#view-cycle-btn");
    const cycleValue = document.querySelector("#view-cycle-value");
    const cycleOrder = ["wall", "gallery", "poster"];

    function applyView(viewName, animate = true, sync = true) {
      if (!allowedViews.has(viewName)) viewName = "wall";
      const updateView = () => {
        document.body.dataset.view = viewName;
        viewButtons.forEach(button => {
          const isActive = button.dataset.view === viewName;
          button.classList.toggle("active", isActive);
          button.setAttribute("aria-pressed", String(isActive));
        });
        if (cycleBtn) {
          cycleBtn.dataset.currentView = viewName;
          cycleBtn.setAttribute("aria-label", `Cycle layout view (current: ${viewName.toUpperCase()})`);
        }
        if (cycleValue) {
          cycleValue.textContent = viewName.toUpperCase();
        }
        storeView(viewName);
        if (sync) syncContext();
      };

      if (animate && document.body.dataset.view && document.body.dataset.view !== viewName) {
        window.clearTimeout(viewSwitchTimer);
        grid.classList.add("view-switching");
        viewSwitchTimer = window.setTimeout(() => {
          updateView();
          window.requestAnimationFrame(() => {
            grid.classList.remove("view-switching");
          });
        }, 120);
      } else {
        updateView();
      }
    }

    if (cycleBtn) {
      cycleBtn.addEventListener("click", () => {
        const current = document.body.dataset.view || "wall";
        const nextIndex = (cycleOrder.indexOf(current) + 1) % cycleOrder.length;
        applyView(cycleOrder[nextIndex]);
      });
    }

    viewButtons.forEach(button => {
      button.addEventListener("click", () => applyView(button.dataset.view));
    });

    return Object.freeze({ applyView });
  }

  window.GSIHomeLayout = Object.freeze({ create });
})();
