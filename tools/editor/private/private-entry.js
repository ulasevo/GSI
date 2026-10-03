(() => {
  const DEFAULT_SECTIONS = [
    ["Charge", "What state does this song trigger?"],
    ["Sonical Attraction", "What sound detail pulls you in? Rhythm, bass, vocal texture, distortion, switch, silence."],
    ["Lyric/Vocal Detail", "Any line, delivery, breath, pronunciation, or vocal moment worth preserving?"],
    ["Version of ulaş", "What version of me does this song store? Time period, grind, breakup, desire, motion."],
    ["Lore", "Any personal history, repeated use, place, habit, person attached to this track?"],
    ["Reading", "What do I think the song is doing or narrating?"],
    ["Comment", "Free field. Final take, vibe, joke, conclusion, or whatever does not fit elsewhere."]
  ];

  const TOKEN_KEY = "gsi_local_auth_token";
  const AUTOSAVE_NEW_KEY = "gsi_new_entry_draft";
  const AUTOSAVE_EDIT_PREFIX = "gsi_edit_autosave_";

  const state = {
    mode: "new", // "new" | "edit"
    sections: [],
    artworkUrl: "",
    coverFile: "",
    signalId: "",
    autosaveTimer: null
  };

  const $ = (id) => document.getElementById(id);
  const escapeHtml = (val) => String(val || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function setStatus(message, kind = "") {
    const card = $("status-card");
    const el = $("status");
    if (!el || !card) return;
    el.textContent = message;
    card.dataset.kind = kind;
  }

  function getToken() {
    return (localStorage.getItem(TOKEN_KEY) || "").trim();
  }

  function setToken(val) {
    const clean = (val || "").trim();
    if (clean) {
      localStorage.setItem(TOKEN_KEY, clean);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
    updateAuthUI();
  }

  function updateAuthUI() {
    const token = getToken();
    const ind = $("auth-indicator");
    if (ind) {
      const isLoopback = ["localhost", "127.0.0.1", "::1"].includes(location.hostname);
      ind.textContent = token ? "TOKEN ACTIVE" : (isLoopback ? "LOCAL" : "AUTH REQUIRED");
      ind.dataset.active = token ? "true" : "false";
    }
    const input = $("auth-token-input");
    if (input && token) {
      input.value = token;
    }
  }

  function authHeaders(existing = {}) {
    const token = getToken();
    return token ? { ...existing, "Authorization": `Bearer ${token}` } : existing;
  }

  async function authFetch(url, options = {}) {
    const headers = authHeaders(options.headers || {});
    const resp = await fetch(url, { ...options, headers });
    if (resp.status === 401) {
      const panel = $("auth-panel");
      if (panel) panel.hidden = false;
      setStatus("LAN access requires your local authorization token.", "error");
      throw new Error("401 Unauthorized — Please enter your local auth token.");
    }
    return resp;
  }

  function renderPalette(colors) {
    const container = $("accent-palette");
    if (!container) return;
    container.replaceChildren();
    if (!Array.isArray(colors) || colors.length === 0) return;

    const currentAccent = ($("accent").value || "").trim().toLowerCase();
    colors.forEach((hex) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "palette-chip";
      chip.style.backgroundColor = hex;
      chip.title = `Use accent ${hex}`;
      chip.setAttribute("aria-label", `Select accent color ${hex}`);
      if (hex.toLowerCase() === currentAccent) {
        chip.classList.add("active");
      }
      chip.addEventListener("click", () => {
        $("accent").value = hex;
        const swatch = $("artwork-swatch");
        if (swatch) swatch.style.background = hex;
        container.querySelectorAll(".palette-chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        queueAutosave();
      });
      container.appendChild(chip);
    });
  }

  function extractCanvasPalette(imgEl) {
    try {
      const canvas = document.createElement("canvas");
      canvas.width = 40;
      canvas.height = 40;
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (!ctx) return;
      ctx.drawImage(imgEl, 0, 0, 40, 40);
      const imgData = ctx.getImageData(0, 0, 40, 40).data;
      const buckets = {};
      for (let i = 0; i < imgData.length; i += 16) {
        const r = imgData[i];
        const g = imgData[i + 1];
        const b = imgData[i + 2];
        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        const sat = max === 0 ? 0 : (max - min) / max;
        const val = max / 255;
        if (val < 0.18 || (val > 0.92 && sat < 0.15)) continue;
        const qr = Math.round(r / 32) * 32;
        const qg = Math.round(g / 32) * 32;
        const qb = Math.round(b / 32) * 32;
        const key = `${Math.min(255, qr)},${Math.min(255, qg)},${Math.min(255, qb)}`;
        buckets[key] = (buckets[key] || 0) + (1 + sat * 2);
      }
      const sorted = Object.entries(buckets).sort((a, b) => b[1] - a[1]);
      const colors = [];
      for (const [key] of sorted) {
        const [r, g, b] = key.split(",").map(Number);
        const hex = `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
        if (!colors.some((c) => {
          const cr = parseInt(c.slice(1, 3), 16);
          const cg = parseInt(c.slice(3, 5), 16);
          const cb = parseInt(c.slice(5, 7), 16);
          return Math.abs(r - cr) + Math.abs(g - cg) + Math.abs(b - cb) < 60;
        })) {
          colors.push(hex);
        }
        if (colors.length >= 5) break;
      }
      if (colors.length > 0) {
        renderPalette(colors);
        if (!$("accent").value && colors[0]) {
          $("accent").value = colors[0];
          const swatch = $("artwork-swatch");
          if (swatch) swatch.style.background = colors[0];
        }
      }
    } catch (_) {
      // CORS safe: ignore if tainted
    }
  }

  function showArtwork(src, caption = "ARTWORK CHECK", accent = "") {
    const preview = $("artwork-preview");
    const image = $("artwork-image");
    const captionEl = $("artwork-caption");
    const swatch = $("artwork-swatch");
    if (!preview || !image) return;

    if (!src) {
      preview.hidden = true;
      image.src = "";
      renderPalette([]);
      return;
    }
    image.crossOrigin = "anonymous";
    image.onload = () => {
      const paletteContainer = $("accent-palette");
      if (paletteContainer && paletteContainer.children.length === 0) {
        extractCanvasPalette(image);
      }
    };
    image.src = src;
    captionEl.textContent = caption;
    if (swatch) {
      swatch.style.background = accent || $("accent").value || "#444";
    }
    preview.hidden = false;
  }

  function queueAutosave() {
    clearTimeout(state.autosaveTimer);
    state.autosaveTimer = setTimeout(() => {
      try {
        const payloadData = buildPayload();
        if (state.mode === "new") {
          localStorage.setItem(AUTOSAVE_NEW_KEY, JSON.stringify(payloadData));
        } else {
          const slug = $("edit-of").value;
          if (slug) localStorage.setItem(AUTOSAVE_EDIT_PREFIX + slug, JSON.stringify(payloadData));
        }
      } catch (_) {}
    }, 400);
  }

  function clearCurrentAutosave() {
    try {
      if (state.mode === "new") {
        localStorage.removeItem(AUTOSAVE_NEW_KEY);
      } else {
        const slug = $("edit-of").value;
        if (slug) localStorage.removeItem(AUTOSAVE_EDIT_PREFIX + slug);
      }
    } catch (_) {}
  }

  function renderSections() {
    const list = $("section-list");
    list.replaceChildren();
    state.sections.forEach((section, index) => {
      const card = document.createElement("article");
      card.className = "section-card";
      card.innerHTML = `
        <span class="section-number">${String(index + 1).padStart(2, "0")}</span>
        <div class="section-fields">
          <input class="section-title" aria-label="Section title" value="${escapeHtml(section.title)}" placeholder="Section title">
          <textarea aria-label="Writing for ${escapeHtml(section.title || "section")}" placeholder="${escapeHtml(section.prompt || "Write what belongs here...")}">${escapeHtml(section.content || "")}</textarea>
        </div>
        <div class="section-actions">
          <button type="button" data-action="up" aria-label="Move section up" title="Move up">↑</button>
          <button type="button" data-action="down" aria-label="Move section down" title="Move down">↓</button>
          <button type="button" class="remove-btn" data-action="remove" aria-label="Remove section" title="Remove">×</button>
        </div>`;

      const titleInput = card.querySelector(".section-title");
      const contentInput = card.querySelector("textarea");

      titleInput.addEventListener("input", () => {
        section.title = titleInput.value;
        queueAutosave();
      });
      contentInput.addEventListener("input", () => {
        section.content = contentInput.value;
        queueAutosave();
      });

      card.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
          const action = btn.dataset.action;
          if (action === "remove") state.sections.splice(index, 1);
          if (action === "up" && index > 0) [state.sections[index - 1], state.sections[index]] = [state.sections[index], state.sections[index - 1]];
          if (action === "down" && index < state.sections.length - 1) [state.sections[index + 1], state.sections[index]] = [state.sections[index], state.sections[index + 1]];
          renderSections();
          queueAutosave();
        });
      });

      list.appendChild(card);
    });
  }

  function addSection(title = "", prompt = "Write what belongs here.", content = "") {
    state.sections.push({ title, prompt, content });
    renderSections();
    queueAutosave();
  }

  function initDefaultSections() {
    state.sections = DEFAULT_SECTIONS.map(([title, prompt]) => ({ title, prompt, content: "" }));
    renderSections();
  }

  function setMode(mode) {
    state.mode = mode;
    const tabNew = $("tab-new");
    const tabEdit = $("tab-edit");
    const resolverPanel = $("resolver-panel");
    const chooserSection = $("chooser-section");
    const heading = $("page-heading");
    const intro = $("page-intro");
    const resultContainer = $("result-link-container");

    if (resultContainer) resultContainer.hidden = true;

    if (mode === "new") {
      tabNew.classList.add("active");
      tabNew.setAttribute("aria-selected", "true");
      tabEdit.classList.remove("active");
      tabEdit.setAttribute("aria-selected", "false");
      resolverPanel.hidden = false;
      chooserSection.hidden = true;
      heading.textContent = "Give a song a place to stay.";
      intro.textContent = "Paste an Apple Music or Spotify link, shape the review sections, and publish a new entry directly on this machine.";
      $("edit-of").value = "";

      // Check if we have autosaved new draft
      const autosaved = localStorage.getItem(AUTOSAVE_NEW_KEY);
      if (autosaved) {
        try {
          const data = JSON.parse(autosaved);
          restoreFormData(data);
          setStatus("Restored your unsaved new signal draft.", "success");
          return;
        } catch (_) {}
      }

      // Default blank new state
      clearFormFields();
      initDefaultSections();
      setStatus("Paste an Apple Music or Spotify song link to begin.");
    } else {
      tabEdit.classList.add("active");
      tabEdit.setAttribute("aria-selected", "true");
      tabNew.classList.remove("active");
      tabNew.setAttribute("aria-selected", "false");
      resolverPanel.hidden = true;
      chooserSection.hidden = false;
      heading.textContent = "Refine an existing signal.";
      intro.textContent = "Select any represented track to refine its review sections, artist notes, album takes, or P53 status.";
      setStatus("Select a signal from the list below.");
      loadCatalog();
    }
  }

  function clearFormFields() {
    $("edit-of").value = "";
    $("provider-link").value = "";
    $("artist").value = "";
    $("track").value = "";
    $("album").value = "";
    $("tags").value = "";
    $("accent").value = "";
    $("p53-enabled").checked = false;
    $("p53-current").checked = false;
    $("p53-note").value = "";
    $("artist-note").value = "";
    $("album-note").value = "";
    state.artworkUrl = "";
    state.coverFile = "";
    state.signalId = "";
    showArtwork("");
    renderPalette([]);
  }

  function restoreFormData(data) {
    if (!data || !data.record) return;
    const r = data.record;
    $("edit-of").value = data.editOf || "";
    if (r.link) $("provider-link").value = r.link;
    if (r.artist) $("artist").value = r.artist;
    if (r.track) $("track").value = r.track;
    if (r.album) $("album").value = r.album;
    if (r.tags) $("tags").value = r.tags;
    if (r.accent) $("accent").value = r.accent;
    state.signalId = r.signal_id || "";
    state.coverFile = r.cover_file || r.cover || (data.editOf ? `${data.editOf}.jpg` : "");
    state.artworkUrl = r.cover_url || "";

    if (Array.isArray(data.palette) && data.palette.length > 0) {
      renderPalette(data.palette);
    } else {
      renderPalette([]);
    }

    const coverSrc = state.artworkUrl || (state.coverFile ? `/covers/${state.coverFile}` : "");
    if (coverSrc) {
      showArtwork(coverSrc, `${r.album || r.track || "SIGNAL"} / ARTWORK`, r.accent);
    } else {
      showArtwork("");
    }

    if (data.p53) {
      $("p53-enabled").checked = Boolean(data.p53.enabled);
      $("p53-current").checked = Boolean(data.p53.current);
      $("p53-note").value = data.p53.note || "";
    }
    if (data.catalogue) {
      $("artist-note").value = data.catalogue.artist_note || "";
      $("album-note").value = data.catalogue.album_note || "";
    }
    if (Array.isArray(data.sections) && data.sections.length > 0) {
      state.sections = data.sections;
      renderSections();
    }
  }

  async function resolveLink() {
    const raw = ($("provider-link").value || "").trim();
    if (!raw) return setStatus("Paste an Apple Music or Spotify link first.", "error");

    let url;
    try { url = new URL(raw); } catch { return setStatus("That is not a valid URL.", "error"); }

    const host = url.hostname.toLowerCase();
    const isApple = ["music.apple.com", "itunes.apple.com"].includes(host) || host.endsWith(".apple.com");
    const isSpotify = ["open.spotify.com", "spotify.link"].includes(host) || host.endsWith(".spotify.com");

    if (isApple) {
      let trackId = url.searchParams.get("i");
      if (!trackId) {
        const segments = url.pathname.split("/").filter((s) => /^\d+$/.test(s));
        if (segments.length > 0) trackId = segments[segments.length - 1];
      }
      if (!trackId) return setStatus("Could not find track ID in Apple Music URL. Enter fields manually.", "error");

      setStatus("Resolving Apple Music metadata…");
      try {
        const resp = await fetch(`https://itunes.apple.com/lookup?id=${encodeURIComponent(trackId)}`);
        if (!resp.ok) throw new Error(`Lookup status ${resp.status}`);
        const payload = await resp.json();
        const song = (payload.results || []).find((item) => item.kind === "song");
        if (!song) throw new Error("No song found");

        $("artist").value = song.artistName || "";
        $("track").value = song.trackName || "";
        $("album").value = song.collectionName || "";
        state.artworkUrl = song.artworkUrl100 ? song.artworkUrl100.replace(/\b\d{2,4}x\d{2,4}bb\b/, "1200x1200bb") : "";
        showArtwork(song.artworkUrl100 || "", `${song.collectionName || "ARTWORK"} / APPLE MUSIC`);
        setStatus("Metadata resolved from Apple Music. Check details and fill review sections.", "success");
        queueAutosave();
      } catch (err) {
        setStatus("Apple lookup was unavailable. Enter song details manually.", "error");
      }
    } else if (isSpotify) {
      setStatus("Resolving Spotify metadata…");
      try {
        const oembedUrl = `https://open.spotify.com/oembed?url=${encodeURIComponent(raw)}`;
        const oembedResp = await fetch(oembedUrl);
        if (!oembedResp.ok) throw new Error("Spotify oEmbed error");
        const oembed = await oembedResp.json();
        const title = (oembed.title || "").trim();
        const thumb = (oembed.thumbnail_url || "").replace("ab67616d00001e02", "ab67616d0000b273");

        let resolved = false;
        if (title) {
          try {
            const itunesSearch = await fetch(`https://itunes.apple.com/search?term=${encodeURIComponent(title)}&entity=song&limit=5`);
            if (itunesSearch.ok) {
              const data = await itunesSearch.json();
              const song = (data.results || []).find((item) => item.kind === "song");
              if (song) {
                $("artist").value = song.artistName || "";
                $("track").value = song.trackName || "";
                $("album").value = song.collectionName || "";
                state.artworkUrl = song.artworkUrl100 ? song.artworkUrl100.replace(/\b\d{2,4}x\d{2,4}bb\b/, "1200x1200bb") : thumb;
                showArtwork(song.artworkUrl100 || thumb, `${song.collectionName || title} / SPOTIFY RESOLVE`);
                resolved = true;
              }
            }
          } catch (_) {}
        }
        if (!resolved) {
          if (title) $("track").value = title;
          state.artworkUrl = thumb;
          if (thumb) showArtwork(thumb, `${title || "SPOTIFY ARTWORK"} / SPOTIFY`);
        }
        setStatus("Spotify metadata resolved. Check details and fill review sections.", "success");
        queueAutosave();
      } catch (err) {
        setStatus("Spotify lookup unavailable. Fill song details manually.", "error");
      }
    } else {
      setStatus("Please use an Apple Music or Spotify song link.", "error");
    }
  }

  async function loadCatalog() {
    try {
      const resp = await authFetch("/api/local-entry-catalog");
      if (!resp.ok) throw new Error(`Status ${resp.status}`);
      const data = await resp.json();
      const select = $("entry-select");
      select.replaceChildren();

      const defaultOpt = document.createElement("option");
      defaultOpt.value = "";
      defaultOpt.textContent = "— Select an existing signal —";
      select.appendChild(defaultOpt);

      (data.entries || []).forEach((item) => {
        const opt = document.createElement("option");
        opt.value = item.slug;
        const tag = item.has_entry ? "" : (item.is_p53 ? " [Radio P53]" : " [Signal]");
        opt.textContent = `${item.artist} — ${item.track} (${item.album})${tag}`;
        select.appendChild(opt);
      });
    } catch (err) {
      setStatus(`Could not load catalogue: ${err.message}`, "error");
    }
  }

  async function loadEntry() {
    const slug = ($("entry-select").value || "").trim();
    if (!slug) return setStatus("Select a signal first.", "error");

    setStatus(`Loading ${slug}…`);
    try {
      const resp = await authFetch(`/api/local-entry/${encodeURIComponent(slug)}`);
      if (!resp.ok) throw new Error(`Status ${resp.status}`);
      const data = await resp.json();

      // Check if there is an autosaved edit draft for this slug
      let activeData = data;
      let restored = false;
      try {
        const raw = localStorage.getItem(AUTOSAVE_EDIT_PREFIX + slug);
        if (raw) {
          activeData = JSON.parse(raw);
          restored = true;
        }
      } catch (_) {}

      activeData.editOf = slug;
      restoreFormData(activeData);

      setStatus(
        restored
          ? `Loaded ${activeData.record.track} (restored unsaved edits from your device).`
          : `Loaded ${activeData.record.track}. Edit fields and click Save + Build.`,
        "success"
      );
    } catch (err) {
      setStatus(`Could not load entry: ${err.message}`, "error");
    }
  }

  function buildPayload() {
    const artist = ($("artist").value || "").trim();
    const track = ($("track").value || "").trim();
    const album = ($("album").value || "").trim();
    const link = ($("provider-link").value || "").trim();
    const tags = ($("tags").value || "").trim();
    const accent = ($("accent").value || "").trim();
    const editOf = state.mode === "edit" ? ($("edit-of").value || "").trim() : "";

    const recordObj = {
      signal_id: state.signalId || "",
      artist,
      track,
      album,
      link,
      tags,
      accent,
      cover_file: state.coverFile || "",
      cover_url: state.artworkUrl || ""
    };

    return GSIDraftContract.payload({
      record: recordObj,
      sections: state.sections,
      p53: {
        enabled: $("p53-enabled").checked,
        current: $("p53-current").checked,
        note: ($("p53-note").value || "").trim()
      },
      catalogue: {
        artist_note: ($("artist-note").value || "").trim(),
        album_note: ($("album-note").value || "").trim()
      },
      editOf
    });
  }

  async function saveDraft() {
    const payloadData = buildPayload();
    const issues = GSIDraftContract.validationIssues(payloadData);
    if (issues.length) {
      return setStatus(`Missing required fields: ${issues.join(", ")}`, "error");
    }

    const endpoint = payloadData.editOf ? "/api/local-entry-drafts" : "/api/entry-drafts";
    setStatus("Saving draft to local inbox…");
    try {
      const resp = await authFetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payloadData)
      });
      const result = await resp.json();
      if (!resp.ok) throw new Error(result.error || "Draft rejected");
      clearCurrentAutosave();
      setStatus(`Saved draft (${result.filename || "received"}) to submissions inbox.`, "success");
    } catch (err) {
      setStatus(`Could not save draft: ${err.message}`, "error");
    }
  }

  async function buildEntry() {
    const payloadData = buildPayload();
    const issues = GSIDraftContract.validationIssues(payloadData);
    if (issues.length) {
      return setStatus(`Missing required fields: ${issues.join(", ")}`, "error");
    }

    const buildBtn = $("build-entry-btn");
    const saveBtn = $("save-draft-btn");
    buildBtn.disabled = true;
    saveBtn.disabled = true;
    buildBtn.textContent = "BUILDING ROOMS…";
    setStatus("Publishing entry, updating catalogue, and generating site…");

    try {
      const resp = await authFetch("/api/local-entry-publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payloadData)
      });
      const result = await resp.json();
      if (!resp.ok) throw new Error(result.error || "Publish rejected");

      clearCurrentAutosave();
      const slug = result.slug || GSIDraftContract.slugify(`${payloadData.record.artist}-${payloadData.record.track}`);

      setStatus(`✓ Successfully built ${payloadData.record.track} by ${payloadData.record.artist}!`, "success");

      const linkContainer = $("result-link-container");
      const resultLink = $("result-link");
      if (linkContainer && resultLink) {
        resultLink.href = `/entries/${slug}.html`;
        resultLink.textContent = `OPEN GENERATED ROOM: /entries/${slug}.html ↗`;
        linkContainer.hidden = false;
      }
    } catch (err) {
      setStatus(`Build failed: ${err.message}`, "error");
    } finally {
      buildBtn.disabled = false;
      saveBtn.disabled = false;
      buildBtn.textContent = "SAVE + BUILD ENTRY ↗";
    }
  }

  // Hook input events for autosaving
  ["artist", "track", "album", "provider-link", "tags", "accent", "p53-note", "artist-note", "album-note"].forEach((id) => {
    const el = $(id);
    if (el) el.addEventListener("input", queueAutosave);
  });
  ["p53-enabled", "p53-current"].forEach((id) => {
    const el = $(id);
    if (el) el.addEventListener("change", queueAutosave);
  });

  const accentInput = $("accent");
  if (accentInput) {
    accentInput.addEventListener("input", () => {
      const val = accentInput.value.trim();
      const swatch = $("artwork-swatch");
      if (swatch) swatch.style.background = val || "#444";
      const paletteContainer = $("accent-palette");
      if (paletteContainer) {
        paletteContainer.querySelectorAll(".palette-chip").forEach((chip) => {
          chip.classList.toggle("active", chip.style.backgroundColor.toLowerCase() === val.toLowerCase());
        });
      }
    });
  }

  // Tab listeners
  $("tab-new").addEventListener("click", () => setMode("new"));
  $("tab-edit").addEventListener("click", () => setMode("edit"));

  // Resolver & chooser listeners
  $("resolve-link").addEventListener("click", resolveLink);
  $("load-entry").addEventListener("click", loadEntry);
  $("entry-select").addEventListener("change", loadEntry);
  $("add-section-btn").addEventListener("click", () => addSection("Custom Heading", "Write what belongs here."));

  // Action button listeners
  $("save-draft-btn").addEventListener("click", saveDraft);
  $("build-entry-btn").addEventListener("click", buildEntry);

  // Auth toggle & token saving
  const authToggle = $("auth-toggle-btn");
  if (authToggle) {
    authToggle.addEventListener("click", () => {
      const panel = $("auth-panel");
      if (panel) panel.hidden = !panel.hidden;
    });
  }
  const saveTokenBtn = $("save-token-btn");
  if (saveTokenBtn) {
    saveTokenBtn.addEventListener("click", () => {
      const input = $("auth-token-input");
      setToken(input ? input.value : "");
      const panel = $("auth-panel");
      if (panel) panel.hidden = true;
      setStatus("Token updated.", "success");
      if (state.mode === "edit") loadCatalog();
    });
  }
  const clearTokenBtn = $("clear-token-btn");
  if (clearTokenBtn) {
    clearTokenBtn.addEventListener("click", () => {
      setToken("");
      const input = $("auth-token-input");
      if (input) input.value = "";
      const panel = $("auth-panel");
      if (panel) panel.hidden = true;
      setStatus("Token cleared.");
    });
  }

  // Read URL token param if supplied on initial visit
  const urlParams = new URLSearchParams(window.location.search);
  const tokenFromUrl = urlParams.get("token");
  if (tokenFromUrl) {
    setToken(tokenFromUrl);
    urlParams.delete("token");
    const cleanSearch = urlParams.toString();
    const cleanUrl = window.location.pathname + (cleanSearch ? "?" + cleanSearch : "") + window.location.hash;
    window.history.replaceState({}, document.title, cleanUrl);
  }

  updateAuthUI();
  setMode("new");
})();
