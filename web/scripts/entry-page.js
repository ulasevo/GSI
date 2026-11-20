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
    const filterLabels = entryContext.filterLabels || {};
    const expectedArtistRoute = entryContext.artistSlug || "";
    const artistName = entryContext.artistName || "";
    const hasArtistRoom = entryContext.hasArtistRoom === true;

    function syncLinks() {
        const archiveState = GSIContext.read();
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
            if (link.dataset.filterRoute === filter) {
                link.hidden = true;
                return;
            }
            link.hidden = false;
            const filterParams = new URLSearchParams(archiveParams);
            filterParams.set("filter", link.dataset.filterRoute);
            link.href = `../index.html?${filterParams}`;
        });

        const alsoAppears = document.querySelector("#also-appears");
        if (alsoAppears) {
            alsoAppears.querySelectorAll("a[href]:not([data-filter-route]):not([data-artist-base-href]):not([data-album-base-href])").forEach((link) => {
                const rawHref = (typeof link.getAttribute === "function" ? link.getAttribute("href") : "") || link.href || "";
                const baseHref = (link.dataset && link.dataset.routeBaseHref) || String(rawHref).split("?")[0];
                if (!baseHref) return;
                if (link.dataset) link.dataset.routeBaseHref = baseHref;
                link.href = GSIContext.href(baseHref, archiveParams);
            });
            alsoAppears.hidden = !alsoAppears.querySelector("a:not([hidden])");
        }

        document.querySelectorAll(".p53-counterpart[data-base-href]").forEach((link) => {
            const p53Params = new URLSearchParams(archiveParams);
            if (hasArtistRoom && artistRoute === expectedArtistRoute) {
                p53Params.set("artist", artistRoute);
            }
            link.href = `${link.dataset.baseHref}${p53Params.size ? `?${p53Params}` : ""}`;
        });

        const hasFilterSegment = Boolean(filter && Object.hasOwn(filterLabels, filter));
        const hasArtistSegment = Boolean(hasArtistRoom && artistRoute === expectedArtistRoute);
        const contextSeparator = document.querySelector("#trace-context-separator");
        const filterSeparator = document.querySelector("#trace-filter-separator");

        if (contextSeparator) {
            contextSeparator.classList.toggle("hidden", !(hasFilterSegment || hasArtistSegment));
        }
        if (filterSeparator) {
            // Show the second separator only between Filter and Artist so no trailing arrow appears.
            filterSeparator.classList.toggle("hidden", !(hasFilterSegment && hasArtistSegment));
        }

        const traceFilter = document.querySelector("#trace-filter");
        if (traceFilter) {
            if (hasFilterSegment) {
                traceFilter.textContent = filterLabels[filter];
                traceFilter.href = archiveHref;
                traceFilter.classList.remove("hidden");
            } else {
                traceFilter.classList.add("hidden");
            }
        }

        const traceArtist = document.querySelector("#trace-artist");
        if (traceArtist) {
            if (hasArtistSegment) {
                traceArtist.textContent = artistName.toUpperCase();
                traceArtist.href = `../artists/${expectedArtistRoute}.html${archiveParams.size ? `?${archiveParams}` : ""}`;
                traceArtist.classList.remove("hidden");
            } else {
                traceArtist.classList.add("hidden");
            }
        }
    }

    syncLinks();
    window.addEventListener("gsi-theme-change", syncLinks);

  // 30-Second Signal Audition Controller
  (() => {
    const btn = document.querySelector(".audition-trigger");
    if (!btn) return;
    const url = btn.dataset.previewUrl;
    if (!url) return;

    const initialLabel = (btn.getAttribute("aria-label") || "").trim();
    const labelMatch = initialLabel.match(/^Peek signal of\s+(.+)$/i);
    const trackName = labelMatch ? labelMatch[1].trim() : (document.querySelector(".meta h1")?.textContent || "").trim();

    function labelFor(state) {
      const target = trackName ? ` of ${trackName}` : "";
      if (state === "playing") return `Pause 30-second preview${target}`;
      if (state === "paused") return `Resume 30-second preview${target}`;
      if (state === "ended") return `Replay 30-second preview${target}`;
      if (state === "unavailable") return trackName ? `Preview unavailable for ${trackName}` : "Preview unavailable";
      if (state === "blocked") return trackName ? `Playback blocked for ${trackName}; activate to retry` : "Playback blocked; activate to retry";
      return `Peek 30-second preview${target}`;
    }

    let statusNode = btn.closest(".stream-block")?.querySelector(".audition-status");
    if (!statusNode) {
      statusNode = document.createElement("span");
      statusNode.className = "sr-only audition-status";
      statusNode.setAttribute("role", "status");
      statusNode.setAttribute("aria-live", "polite");
      statusNode.setAttribute("aria-atomic", "true");
      (btn.closest(".stream-block") || btn.parentElement || document.body).append(statusNode);
    }

    let currentState = "";
    function setButtonState(state, announcement = "") {
      if (currentState === state) return;
      currentState = state;
      btn.classList.remove("is-playing", "is-paused", "is-error");
      if (state === "playing") {
        btn.disabled = false;
        btn.removeAttribute("aria-disabled");
        btn.classList.add("is-playing");
        btn.setAttribute("aria-pressed", "true");
        btn.setAttribute("aria-label", labelFor("playing"));
        btn.innerHTML = 'PEEKING <span class="peek-icon" aria-hidden="true">⏸</span>';
        document.body.classList.add("signal-auditioning");
      } else if (state === "paused") {
        btn.disabled = false;
        btn.removeAttribute("aria-disabled");
        btn.classList.add("is-paused");
        btn.setAttribute("aria-pressed", "false");
        btn.setAttribute("aria-label", labelFor("paused"));
        btn.innerHTML = 'PAUSED <span class="peek-icon" aria-hidden="true">▶</span>';
        document.body.classList.remove("signal-auditioning");
      } else if (state === "unavailable") {
        btn.classList.add("is-error");
        btn.setAttribute("aria-pressed", "false");
        btn.disabled = true;
        btn.setAttribute("aria-disabled", "true");
        btn.textContent = "Preview unavailable";
        btn.setAttribute("aria-label", labelFor("unavailable"));
        document.body.classList.remove("signal-auditioning");
      } else if (state === "blocked") {
        btn.disabled = false;
        btn.removeAttribute("aria-disabled");
        btn.classList.add("is-error");
        btn.setAttribute("aria-pressed", "false");
        btn.textContent = "Playback blocked";
        btn.setAttribute("aria-label", labelFor("blocked"));
        document.body.classList.remove("signal-auditioning");
      } else {
        btn.disabled = false;
        btn.removeAttribute("aria-disabled");
        btn.setAttribute("aria-pressed", "false");
        btn.setAttribute("aria-label", labelFor(state === "ended" ? "ended" : "idle"));
        btn.innerHTML = 'PEEK <span class="peek-icon" aria-hidden="true">▶</span>';
        document.body.classList.remove("signal-auditioning");
      }
      if (announcement) statusNode.textContent = announcement;
    }

    setButtonState("idle");

    let audio = null;
    let isStarting = false;

    function onPlay() {
      isStarting = false;
      btn.removeAttribute("aria-busy");
      setButtonState("playing", trackName ? `Playing 30-second preview of ${trackName}.` : "Playing 30-second preview.");
    }

    function onPause() {
      isStarting = false;
      btn.removeAttribute("aria-busy");
      if (!audio || audio.ended) return;
      setButtonState("paused", "Preview paused.");
    }

    function onEnded() {
      isStarting = false;
      btn.removeAttribute("aria-busy");
      if (audio) {
        try { audio.currentTime = 0; } catch { /* ignore seek errors on teardown */ }
      }
      setButtonState("ended", "Preview ended.");
    }

    function onError() {
      cleanupAudio();
      btn.removeAttribute("aria-busy");
      setButtonState("unavailable", "Audio preview unavailable.");
    }

    function cleanupAudio() {
      isStarting = false;
      if (!audio) return;
      const target = audio;
      audio = null;
      target.removeEventListener("play", onPlay);
      target.removeEventListener("pause", onPause);
      target.removeEventListener("ended", onEnded);
      target.removeEventListener("error", onError);
      try {
        target.pause();
        target.removeAttribute("src");
        target.load();
      } catch { /* media cleanup optional in stub environments */ }
    }

    btn.addEventListener("click", () => {
      if (isStarting || btn.disabled) return;
      if (!audio) {
        audio = new Audio(url);
        audio.addEventListener("play", onPlay);
        audio.addEventListener("pause", onPause);
        audio.addEventListener("ended", onEnded);
        audio.addEventListener("error", onError);
      }
      if (audio.paused) {
        isStarting = true;
        btn.setAttribute("aria-busy", "true");
        Promise.resolve(audio.play()).then(() => {
          isStarting = false;
          btn.removeAttribute("aria-busy");
          if (audio && !audio.paused) {
            setButtonState("playing", trackName ? `Playing 30-second preview of ${trackName}.` : "Playing 30-second preview.");
          }
        }).catch((err) => {
          isStarting = false;
          btn.removeAttribute("aria-busy");
          if (err && err.name === "AbortError") return;
          if (err && err.name === "NotSupportedError") {
            cleanupAudio();
            setButtonState("unavailable", "Audio preview unavailable.");
            return;
          }
          setButtonState("blocked", "Audio playback blocked by browser.");
        });
      } else {
        audio.pause();
        setButtonState("paused", "Preview paused.");
      }
    });

    function pauseActiveAudio() {
      if (audio && !audio.paused) {
        audio.pause();
        setButtonState("paused", "Preview paused.");
      }
    }

    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") pauseActiveAudio();
    });

    document.querySelectorAll(".stream-link:not(.audition-trigger)").forEach((link) => {
      link.addEventListener("click", pauseActiveAudio);
    });

    window.addEventListener("pagehide", () => {
      cleanupAudio();
      btn.removeAttribute("aria-busy");
      if (!btn.classList.contains("is-error")) {
        setButtonState("idle");
      } else {
        document.body.classList.remove("signal-auditioning");
      }
    });
  })();

})();
