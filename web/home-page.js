    document.addEventListener("DOMContentLoaded", () => { // wait until the page exists before selecting buttons/cards
        const viewButtons = document.querySelectorAll(".view-btn");
        const formatButtons = document.querySelectorAll(".format-option");
        const formatControl = document.querySelector(".format-control");
        const allowedViews = GSIContext.allowedViews;
        const filterDataNode = document.querySelector("#gsi-filter-data");
        const filterInfo = filterDataNode ? JSON.parse(filterDataNode.textContent || "{}") : {};
        const buttons = document.querySelectorAll(".filter-btn"); // all clickable filter buttons
        const cards = document.querySelectorAll(".card"); // all song cards
        const grid = document.querySelector(".grid");
        const box = document.querySelector("#filter-description-box"); // whole description box
        const title = document.querySelector("#filter-title"); // filter description title
        const description = document.querySelector("#filter-description"); // filter description text
        const playlistCard = document.querySelector("#playlist-card");
        const playlistCover = document.querySelector("#playlist-cover");
        const playlistCta = document.querySelector("#playlist-cta");
        const layoutFormatControls = document.querySelector(".layout-format-controls");
        const filterCount = document.querySelector("#filter-count");
        const filterRoomLabel = document.querySelector("#filter-room-label");
        const filterDecor = document.querySelector("#filter-decor");

        let activeFilter = null; // no filter is active when page first loads
        let activeFormat = "songs";
        let basslineResizeFrame = null;
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
            if (activeFilter !== "bassline") return;
            window.cancelAnimationFrame(basslineResizeFrame);
            basslineResizeFrame = window.requestAnimationFrame(() => renderRoomLabel(filterInfo.bassline, "bassline"));
        });
        function archiveContextHref(baseHref) {
            const params = new URLSearchParams();
            if (activeFilter) params.set("filter", activeFilter);
            const activeView = document.body.dataset.view;
            if (allowedViews.has(activeView)) params.set("view", activeView);
            if (activeFormat === "albums") params.set("format", activeFormat);
            return `${baseHref}${params.size ? `?${params}` : ""}`;
        }
        function syncArchiveContext() {
            document.querySelectorAll("[data-base-href], [data-group-base-href]").forEach(link => {
                link.href = archiveContextHref(link.dataset.baseHref || link.dataset.groupBaseHref);
            });
            const params = new URLSearchParams();
            if (activeFilter) params.set("filter", activeFilter);
            const activeView = document.body.dataset.view;
            if (allowedViews.has(activeView)) params.set("view", activeView);
            if (activeFormat === "albums") params.set("format", activeFormat);
            const query = params.size ? `?${params}` : "";
            window.history.replaceState(null, "", `${window.location.pathname}${query}${window.location.hash}`);
        }
        function storeView(viewName) {
            GSIContext.storeView(viewName);
        }
        let viewSwitchTimer = null;
        function applyView(viewName, animate = true, sync = true) {
            if (!allowedViews.has(viewName)) {
                viewName = "wall"; // default view
            }
            const updateView = () => {
                document.body.dataset.view = viewName;
                viewButtons.forEach(button => {
                    const isActive = button.dataset.view === viewName;
                    button.classList.toggle("active", isActive);
                    button.setAttribute("aria-pressed", String(isActive));
                });
                storeView(viewName);
                if (sync) syncArchiveContext();
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
            button.addEventListener("click", () => {
                applyView(button.dataset.view);
            });
        });
        function hidePlaylist() {
            playlistCard.classList.add("hidden");
            layoutFormatControls.classList.remove("has-playlist");
            playlistCard.removeAttribute("href");
            playlistCover.removeAttribute("src");
            playlistCover.style.display = "none";
            playlistCta.textContent = "";
        }
        let signalTransformTimer = null;
        let filterEntranceTimer = null;
        function triggerSignalTransform() {
            if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
            window.clearTimeout(signalTransformTimer);
            document.body.classList.remove("signal-transforming");
            void document.body.offsetWidth; // restart the short transformation on repeated filter changes
            document.body.classList.add("signal-transforming");
            signalTransformTimer = window.setTimeout(() => document.body.classList.remove("signal-transforming"), 720);
        }
        function applyFormat(formatName, sync = true) {
            activeFormat = formatName === "albums" ? "albums" : "songs";
            document.body.dataset.format = activeFormat;
            formatControl.dataset.format = activeFormat;
            formatButtons.forEach(button => {
                const isActive = button.dataset.formatOption === activeFormat;
                button.classList.toggle("active", isActive);
                button.setAttribute("aria-pressed", String(isActive));
            });
            renderFilterAlbumGroups(activeFilter);
            if (sync) syncArchiveContext();
        }
        formatButtons.forEach(button => {
            if (button.disabled) return;
            button.addEventListener("click", () => applyFormat(button.dataset.formatOption));
        });
        function clearFilterAlbumGroups() {
            document.querySelectorAll(".filter-album-group").forEach(group => {
                group.remove();
            });
            cards.forEach(card => {
                card.removeAttribute("data-album-pocket-hidden");
            });
        }
        function renderFilterAlbumGroups(filterName) {
            // Album format shows each represented album once. A filter may reveal an album
            // when only one of its songs belongs to that room; the album page stays whole.
            clearFilterAlbumGroups();
            const cardMatchesFilter = card => {
                if (!filterName) return true;
                return (card.dataset.tags || "").split(" ").includes(filterName);
            };
            if (activeFormat !== "albums") {
                cards.forEach(card => {
                    card.style.display = cardMatchesFilter(card) ? "flex" : "none";
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
                const firstMatchingCard = groupCards.find(cardMatchesFilter);
                if (!firstMatchingCard) return;
                if (groupCards.length < 2) return;
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
                const imageSrc = firstImage ? firstImage.getAttribute("src") : "";
                const albumHref = archiveContextHref(first.dataset.albumHref);
                // Build the summary with DOM APIs so metadata remains text, never markup.
                // Album/artist names originate in editable source data and must not be
                // interpolated into HTML, even though the generated cards are escaped.
                const summary = document.createElement("a");
                summary.className = "filter-album-summary";
                summary.dataset.baseHref = first.dataset.albumHref || "";
                summary.href = albumHref;
                const summaryImage = document.createElement("img");
                summaryImage.src = imageSrc;
                summaryImage.alt = `${first.dataset.album} cover`;
                summaryImage.loading = "lazy";
                summaryImage.decoding = "async";
                const summaryCopy = document.createElement("div");
                summaryCopy.className = "filter-album-summary-copy";
                const summaryTitle = document.createElement("strong");
                summaryTitle.textContent = first.dataset.album || "";
                const summaryArtist = document.createElement("em");
                summaryArtist.textContent = first.dataset.artist || "";
                const summaryCount = document.createElement("span");
                summaryCount.textContent = `${String(groupCards.length).padStart(2, "0")} signals`;
                summaryCopy.append(summaryTitle, summaryArtist, summaryCount);
                summary.append(summaryImage, summaryCopy);
                group.append(summary);
            });
            // Albums format is deliberately sparse: single-song albums do not appear yet.
        }
        function clearFilter(sync = true) { // return to default homepage state
            activeFilter = null; // forget active filter
            document.body.classList.remove("filter-active");
            document.body.removeAttribute("data-active-filter");
            document.documentElement.style.setProperty("--page-tint", "#ffffff"); // reset tint/glow

            buttons.forEach(button => { // remove active look from every button
                button.classList.remove("active");
                button.setAttribute("aria-pressed", "false");
            });

            renderFilterAlbumGroups(null);

            box.classList.add("hidden"); // hide description panel
            title.textContent = ""; // clear title
            description.textContent = ""; // clear text
            box.removeAttribute("data-filter-label");
            box.removeAttribute("data-filter");
            window.clearTimeout(filterEntranceTimer);
            box.classList.remove("filter-entering");
            filterRoomLabel.replaceChildren();
            filterDecor.replaceChildren();
            filterCount.textContent = "";
            delete box.dataset.hasPlaylistCover;
            hidePlaylist();
            if (sync) syncArchiveContext();
        }

        function setFilter(filterName, animate = true, sync = true) { // activate a filter
            if (activeFilter === filterName) { // clicking same filter again clears it
                clearFilter(sync);
                return;
            }

            activeFilter = filterName; // remember active filter
            if (animate) triggerSignalTransform();
            document.body.classList.add("filter-active"); // we attach and remove a CSS class whose appearance is controlled by javascript
            document.body.dataset.activeFilter = filterName;
            const info = filterInfo[filterName]; // get label/description/color from config.json

            document.documentElement.style.setProperty("--page-tint", info.color); // update glow/tint
            title.textContent = info.label; // update panel title
            description.textContent = info.description; // update panel text
            description.hidden = !info.description;
            box.dataset.filterLabel = info.label;
            box.dataset.filter = filterName;
            box.dataset.hasPlaylistCover = String(Boolean(info.playlist_cover));
            box.classList.remove("hidden"); // reveal before restarting entrance animations
            box.classList.remove("filter-entering");
            if (animate) {
                window.clearTimeout(filterEntranceTimer);
                void box.offsetWidth; // restart filter-specific entrance effects
                box.classList.add("filter-entering");
                filterEntranceTimer = window.setTimeout(() => box.classList.remove("filter-entering"), 1000);
            }
            renderRoomLabel(info, filterName);
            filterDecor.replaceChildren();
            if (filterName === "pop") {
                const popSignals = [
                    [12, 16, 26, -900, 3.7], [72, 12, 52, -2400, 5.1], [42, 36, 34, -600, 4.3],
                    [82, 58, 24, -3100, 5.7], [18, 70, 58, -1700, 4.9], [58, 78, 30, -3800, 6.2], [34, 8, 20, -1200, 3.4]
                ];
                popSignals.forEach(([x, y, size, delay, speed]) => {
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
            filterCount.textContent = `${String(info.count).padStart(2, "0")} SIGNAL${info.count === 1 ? "" : "S"}`;
            box.classList.remove("hidden"); // show description panel
            if (info.playlist_url || info.playlist_cover) {
                playlistCard.href = info.playlist_url || "#";
                if (info.playlist_url) {
                    playlistCard.target = "_blank";
                } else {
                    playlistCard.removeAttribute("target");
                }
                playlistCard.style.setProperty("--playlist-accent", info.playlist_color || info.color);
                playlistCta.textContent = info.playlist_url ? "FOLLOW THE SIGNAL / ON APPLE MUSIC ↗" : "PLAYLIST UNAVAILABLE";
                if (info.playlist_cover) {
                    playlistCover.src = info.playlist_cover;
                    playlistCover.style.display = "block";
                } else {
                    playlistCover.removeAttribute("src");
                    playlistCover.style.display = "none";
                }
                playlistCard.classList.remove("hidden");
                layoutFormatControls.classList.add("has-playlist");
            } else {
                hidePlaylist();
            }
            buttons.forEach(button => { // update active button style
                const isActive = button.dataset.filter === filterName; // === checks exact equality
                button.classList.toggle("active", isActive);
                button.setAttribute("aria-pressed", String(isActive)); // converts boolean true/false into text
            });

            renderFilterAlbumGroups(filterName);
            if (sync) syncArchiveContext();
        }

        buttons.forEach(button => { // attach click behavior to every filter button
            button.addEventListener("click", () => {
                setFilter(button.dataset.filter);
            });
        });
        const savedView = GSIContext.loadView("wall");
        const requestedState = GSIContext.read();
        const requestedView = requestedState.get("view");
        const requestedFilter = requestedState.get("filter");
        const requestedFormat = requestedState.get("format");
        applyView(allowedViews.has(requestedView) ? requestedView : savedView, false, false);
        applyFormat(requestedFormat === "albums" ? "albums" : "songs", false);
        if (requestedFilter && Object.hasOwn(filterInfo, requestedFilter)) {
            setFilter(requestedFilter, false, false);
        } else {
            clearFilter(false);
        }
        syncArchiveContext(); // normalize a shared link after all state is in place
    });
