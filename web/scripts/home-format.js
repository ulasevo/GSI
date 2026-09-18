/*
 * Homepage format control.
 * Albums format groups represented cards without deleting the original cards;
 * switching back to Songs can therefore restore the exact source grid.
 */
(() => {
  function create({
    state,
    formatButtons,
    formatControl,
    cards,
    grid,
    homeState,
    contextHref,
    syncContext,
  }) {
    function clearFilterAlbumGroups() {
      document.querySelectorAll(".filter-album-group").forEach(group => group.remove());
      cards.forEach(card => card.removeAttribute("data-album-pocket-hidden"));
    }

    function renderFilterAlbumGroups(filterName) {
      // An album appears when any represented song matches the room, but the
      // album page remains whole and still contains all of its songs.
      clearFilterAlbumGroups();
      if (state.activeFormat !== "albums") {
        cards.forEach(card => {
          card.style.display = homeState.cardMatchesFilter(card, filterName) ? "flex" : "none";
        });
        return;
      }

      const byAlbum = new Map();
      cards.forEach(card => {
        const key = `${card.dataset.artist}::${card.dataset.album}`;
        byAlbum.set(key, [...(byAlbum.get(key) || []), card]);
      });
      cards.forEach(card => {
        card.style.display = "none";
        card.dataset.albumPocketHidden = "true";
      });

      byAlbum.forEach(groupCards => {
        const firstMatchingCard = groupCards.find(card => homeState.cardMatchesFilter(card, filterName));
        if (!firstMatchingCard || groupCards.length < 2) return;
        const first = groupCards[0];
        const group = document.createElement("section");
        group.className = "filter-album-group";
        group.setAttribute("data-album-pocket", "true");
        group.setAttribute("aria-label", `${first.dataset.album} by ${first.dataset.artist}`);
        group.dataset.album = first.dataset.album;
        group.dataset.signalCount = String(groupCards.length).padStart(2, "0");
        group.style.setProperty("--album-count", String(groupCards.length));
        group.style.setProperty("--album-columns", String(Math.min(3, groupCards.length)));
        group.style.display = "grid";
        group.style.setProperty("--accent", first.style.getPropertyValue("--accent"));
        grid.insertBefore(group, firstMatchingCard);

        const firstImage = first.querySelector("img");
        const summary = document.createElement("a");
        summary.className = "filter-album-summary";
        summary.dataset.baseHref = first.dataset.albumHref || "";
        summary.href = contextHref(first.dataset.albumHref);
        const summaryImage = document.createElement("img");
        summaryImage.src = firstImage ? firstImage.getAttribute("src") : "";
        summaryImage.alt = `${first.dataset.album} cover`;
        summaryImage.loading = "lazy";
        summaryImage.decoding = "async";

        // Metadata is inserted as text, never interpolated as HTML.
        const summaryCopy = document.createElement("div");
        summaryCopy.className = "filter-album-summary-copy";
        const summaryTitle = document.createElement("strong");
        summaryTitle.textContent = first.dataset.album || "";
        const summaryArtist = document.createElement("em");
        summaryArtist.textContent = first.dataset.artist || "";
        const summaryCount = document.createElement("span");
        summaryCount.textContent = homeState.albumLabel(groupCards.length);
        summaryCopy.append(summaryTitle, summaryArtist, summaryCount);
        summary.append(summaryImage, summaryCopy);
        group.append(summary);
      });
    }

    function applyFormat(formatName, sync = true) {
      state.activeFormat = formatName === "albums" ? "albums" : "songs";
      document.body.dataset.format = state.activeFormat;
      formatControl.dataset.format = state.activeFormat;
      formatButtons.forEach(button => {
        const isActive = button.dataset.formatOption === state.activeFormat;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-pressed", String(isActive));
      });
      renderFilterAlbumGroups(state.activeFilter);
      if (sync) syncContext();
    }

    formatButtons.forEach(button => {
      if (!button.disabled) button.addEventListener("click", () => applyFormat(button.dataset.formatOption));
    });

    return Object.freeze({ applyFormat, renderFilterAlbumGroups });
  }

  window.GSIHomeFormat = Object.freeze({ create });
})();
