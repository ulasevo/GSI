/*
 * Entry reading-room behavior.
 * The source Markdown is already rendered by Python; this file only opens help
 * notes and repairs links so the route that led to the entry can be retraced.
 */
(() => {
    const contextNode = document.querySelector("#gsi-entry-context");
    if (!contextNode || !window.GSIContext) return;

    let entryContext;
    try {
        entryContext = JSON.parse(contextNode.textContent || "{}");
    } catch {
        return;
    }

    // Section help is progressive disclosure: it starts closed and never moves
    // the visitor away from the prose they are reading.
    document.querySelectorAll(".section-info-button").forEach((button) => {
        button.addEventListener("click", () => {
            const help = button.closest(".section-card")?.querySelector(".section-help");
            if (!help) return;
            const willOpen = button.getAttribute("aria-expanded") !== "true";
            help.classList.toggle("open", willOpen);
            help.setAttribute("aria-hidden", String(!willOpen));
            button.setAttribute("aria-expanded", String(willOpen));
        });
    });

    // Preserve the route that led here without replacing native browser Back.
    const archiveState = GSIContext.read();
    const filterLabels = entryContext.filterLabels || {};
    const expectedArtistRoute = entryContext.artistSlug || "";
    const artistName = entryContext.artistName || "";
    const hasArtistRoom = entryContext.hasArtistRoom === true;
    const filter = archiveState.get("filter");
    const artistRoute = archiveState.get("artist");
    const archiveParams = GSIContext.archiveParams({ state: archiveState, filterLabels });
    const archiveHref = GSIContext.href("../index.html", archiveParams);

    document.querySelectorAll("#trace-archive").forEach((link) => {
        link.href = archiveHref;
    });
    document.querySelectorAll("[data-artist-base-href], [data-album-base-href]").forEach((link) => {
        const contextParams = new URLSearchParams(archiveParams);
        if (link.dataset.albumBaseHref && hasArtistRoom && artistRoute === expectedArtistRoute) {
            contextParams.set("artist", artistRoute);
        }
        const baseHref = link.dataset.artistBaseHref || link.dataset.albumBaseHref;
        link.href = `${baseHref}${contextParams.size ? `?${contextParams}` : ""}`;
    });
    document.querySelectorAll("[data-filter-route]").forEach((link) => {
        if (link.dataset.filterRoute === filter) link.hidden = true;
    });

    const alsoAppears = document.querySelector("#also-appears");
    if (alsoAppears && !alsoAppears.querySelector("a:not([hidden])")) {
        alsoAppears.hidden = true;
    }

    document.querySelectorAll(".p53-counterpart[data-base-href]").forEach((link) => {
        const p53Params = new URLSearchParams(archiveParams);
        if (hasArtistRoom && artistRoute === expectedArtistRoute) {
            p53Params.set("artist", artistRoute);
        }
        link.href = `${link.dataset.baseHref}${p53Params.size ? `?${p53Params}` : ""}`;
    });

    if (filter && Object.hasOwn(filterLabels, filter)) {
        const traceFilter = document.querySelector("#trace-filter");
        if (traceFilter) {
            traceFilter.textContent = filterLabels[filter];
            traceFilter.href = archiveHref;
            traceFilter.classList.remove("hidden");
            document.querySelector("#trace-context-separator")?.classList.remove("hidden");
            // The entry separator already follows the filter when no artist
            // room is in the path. Show a second separator only for GSI →
            // filter → artist → entry.
            const filterSeparator = document.querySelector("#trace-filter-separator");
            if (filterSeparator) {
                const hasArtistSegment = hasArtistRoom && artistRoute === expectedArtistRoute;
                if (hasArtistSegment) {
                    filterSeparator.classList.remove("hidden");
                } else {
                    filterSeparator.classList.add("hidden");
                }
            }
        }
    }

    if (hasArtistRoom && artistRoute === expectedArtistRoute) {
        const traceArtist = document.querySelector("#trace-artist");
        if (traceArtist) {
            traceArtist.textContent = artistName.toUpperCase();
            traceArtist.href = `../artists/${expectedArtistRoute}.html${archiveParams.size ? `?${archiveParams}` : ""}`;
            traceArtist.classList.remove("hidden");
            document.querySelector("#trace-context-separator")?.classList.remove("hidden");
        }
    }
})();
