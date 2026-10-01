/*
 * Homepage filter-room controller.
 * It owns authored filter copy, playlist visibility, filter-specific decoration,
 * and the active filter button; layout and album grouping are injected helpers.
 */
(() => {
  function create({
    state,
    filterInfo,
    buttons,
    box,
    title,
    description,
    playlistCard,
    playlistCover,
    playlistCta,
    layoutFormatControls,
    filterCount,
    filterRoomLabel,
    filterDecor,
    homeState,
    renderFilterAlbumGroups,
    syncContext,
  }) {
    let basslineResizeFrame = null;
    let signalTransformTimer = null;
    let filterEntranceTimer = null;
    let filterExitTimer = null;

    function renderRoomLabel(info, filterName) {
      // Bassline grows with its room but remains one intentionally unbroken word.
      const lines = filterName === "bassline"
        ? [`BA${"S".repeat(Math.max(5, Math.min(15, Math.round(box.clientWidth / 92))))}LINE`]
        : info.room_label_lines;
      filterRoomLabel.replaceChildren(...lines.map(line => {
        const span = document.createElement("span");
        span.textContent = line;
        return span;
      }));
    }

    window.addEventListener("resize", () => {
      if (state.activeFilter !== "bassline") return;
      window.cancelAnimationFrame(basslineResizeFrame);
      basslineResizeFrame = window.requestAnimationFrame(() => renderRoomLabel(filterInfo.bassline, "bassline"));
    });

    function hidePlaylist() {
      playlistCard.classList.add("hidden");
      box.classList.remove("has-playlist");
      layoutFormatControls.classList.remove("has-playlist");
      playlistCard.removeAttribute("href");
      playlistCover.removeAttribute("src");
      playlistCover.style.display = "none";
      playlistCta.textContent = "";
    }

    function triggerSignalTransform() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      window.clearTimeout(signalTransformTimer);
      document.body.classList.remove("signal-transforming");
      window.requestAnimationFrame(() => {
        document.body.classList.add("signal-transforming");
        signalTransformTimer = window.setTimeout(() => document.body.classList.remove("signal-transforming"), 720);
      });
    }

    function clearFilter(sync = true) {
      const wasActive = Boolean(state.activeFilter);
      state.activeFilter = null;
      document.body.classList.remove("filter-active");
      document.body.removeAttribute("data-active-filter");
      document.documentElement.style.setProperty("--page-tint", "#ffffff");
      buttons.forEach(button => {
        button.classList.remove("active");
        button.setAttribute("aria-pressed", "false");
      });
      renderFilterAlbumGroups(null);
      window.clearTimeout(filterEntranceTimer);
      window.clearTimeout(filterExitTimer);
      box.classList.remove("filter-entering");
      if (wasActive && !box.classList.contains("hidden")) {
        box.classList.add("filter-collapsing");
        filterExitTimer = window.setTimeout(() => {
          box.classList.remove("filter-collapsing");
          box.classList.add("hidden");
          title.textContent = "";
          description.textContent = "";
          box.removeAttribute("data-filter-label");
          box.removeAttribute("data-filter");
          filterRoomLabel.replaceChildren();
          filterDecor.replaceChildren();
          filterCount.textContent = "";
          delete box.dataset.hasPlaylistCover;
          hidePlaylist();
        }, 240);
      } else {
        box.classList.add("hidden");
        title.textContent = "";
        description.textContent = "";
        box.removeAttribute("data-filter-label");
        box.removeAttribute("data-filter");
        filterRoomLabel.replaceChildren();
        filterDecor.replaceChildren();
        filterCount.textContent = "";
        delete box.dataset.hasPlaylistCover;
        hidePlaylist();
      }
      if (sync) syncContext();
    }

    function setFilter(filterName, animate = true, sync = true) {
      if (state.activeFilter === filterName) {
        clearFilter(sync);
        return;
      }
      state.activeFilter = filterName;
      if (animate) triggerSignalTransform();
      document.body.classList.add("filter-active");
      document.body.dataset.activeFilter = filterName;
      const info = filterInfo[filterName];
      document.documentElement.style.setProperty("--page-tint", info.color);
      title.textContent = info.label;
      description.textContent = info.description;
      description.hidden = !info.description;
      box.dataset.filterLabel = info.label;
      box.dataset.filter = filterName;
      box.dataset.hasPlaylistCover = String(Boolean(info.playlist_cover));
      window.clearTimeout(filterExitTimer);
      box.classList.remove("hidden", "filter-entering", "filter-collapsing");
      if (animate) {
        window.clearTimeout(filterEntranceTimer);
        window.requestAnimationFrame(() => {
          box.classList.add("filter-entering");
          filterEntranceTimer = window.setTimeout(() => box.classList.remove("filter-entering"), 1000);
        });
      }
      renderRoomLabel(info, filterName);
      filterDecor.replaceChildren();
      if (filterName === "pop") {
        homeState.popSignals().forEach(([x, y, size, delay, speed]) => {
          const pop = document.createElement("span");
          pop.textContent = "POP";
          pop.style.setProperty("--pop-x", `${x}%`);
          pop.style.setProperty("--pop-y", `${y}%`);
          pop.style.setProperty("--pop-size", `${size}px`);
          pop.style.setProperty("--pop-delay", `${delay}ms`);
          pop.style.setProperty("--pop-speed", `${speed}s`);
          filterDecor.append(pop);
        });
      }
      filterCount.textContent = homeState.signalLabel(info.count);

      if (info.playlist_url || info.playlist_cover) {
        playlistCard.href = info.playlist_url || "#";
        if (info.playlist_url) playlistCard.target = "_blank";
        else playlistCard.removeAttribute("target");
        playlistCard.style.setProperty("--playlist-accent", info.playlist_color || info.color);
        playlistCta.textContent = info.playlist_cta || (info.playlist_url ? "Want more of the same?" : "PLAYLIST UNAVAILABLE");
        if (info.playlist_cover) {
          playlistCover.src = info.playlist_cover;
          playlistCover.style.display = "block";
        } else {
          playlistCover.removeAttribute("src");
          playlistCover.style.display = "none";
        }
        playlistCard.classList.remove("hidden");
        box.classList.add("has-playlist");
        layoutFormatControls.classList.add("has-playlist");
      } else {
        hidePlaylist();
      }
      buttons.forEach(button => {
        const isActive = button.dataset.filter === filterName;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-pressed", String(isActive));
      });
      renderFilterAlbumGroups(filterName);
      if (sync) syncContext();
    }

    buttons.forEach(button => button.addEventListener("click", () => setFilter(button.dataset.filter)));
    return Object.freeze({ clearFilter, setFilter });
  }

  window.GSIHomeFilters = Object.freeze({ create });
})();
