(() => {
  const TOKEN_KEY = "gsi_local_auth_token";
  const AUTOSAVE_PREFIX = "gsi_edit_autosave_";

  const state = {
    sections: [],
    coverFile: "",
    coverUrl: "",
    signalId: "",
    artistArtwork: GSIDraftContract.defaultArtistArtwork(),
    autosaveTimer: null
  };

  const $ = (id) => document.getElementById(id);
  const setStatus = (message, kind = "") => {
    const el = $("status");
    if (!el) return;
    el.textContent = message;
    el.dataset.kind = kind;
  };

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

  function queueAutosave() {
    clearTimeout(state.autosaveTimer);
    state.autosaveTimer = setTimeout(() => {
      const slug = $("edit-of") ? $("edit-of").value : "";
      if (!slug) return;
      try {
        localStorage.setItem(AUTOSAVE_PREFIX + slug, JSON.stringify(payload()));
      } catch (_) {}
    }, 400);
  }

  function checkAutosave(slug) {
    try {
      const raw = localStorage.getItem(AUTOSAVE_PREFIX + slug);
      if (raw) return JSON.parse(raw);
    } catch (_) {}
    return null;
  }

  function clearAutosave(slug) {
    try {
      localStorage.removeItem(AUTOSAVE_PREFIX + slug);
    } catch (_) {}
  }

  function renderSections() {
    const list = $("section-list");
    list.replaceChildren();
    state.sections.forEach((section, index) => {
      const card = document.createElement("article");
      card.className = "section-card";
      const number = document.createElement("span");
      number.className = "section-number";
      number.textContent = String(index + 1).padStart(2, "0");
      const fields = document.createElement("div");
      const title = document.createElement("input");
      title.value = section.title;
      title.setAttribute("aria-label", "Section title");
      const content = document.createElement("textarea");
      content.value = section.content;
      content.setAttribute("aria-label", `Writing for ${section.title}`);
      title.addEventListener("input", () => {
        section.title = title.value;
        queueAutosave();
      });
      content.addEventListener("input", () => {
        section.content = content.value;
        queueAutosave();
      });
      fields.append(title, content);
      card.append(number, fields);
      list.append(card);
    });
  }

  function record() {
    return GSIDraftContract.record({
      signal_id: state.signalId,
      artist: $("artist").value.trim(),
      track: $("track").value.trim(),
      album: $("album").value.trim(),
      link: $("provider-link").value.trim(),
      tags: $("tags").value.trim(),
      accent: $("accent").value.trim(),
      slug: $("edit-of").value,
      cover: state.coverFile || `${$("edit-of").value}.jpg`,
      cover_url: state.coverUrl
    });
  }

  function payload() {
    return GSIDraftContract.payload({
      editOf: $("edit-of").value,
      record: record(),
      sections: state.sections,
      p53: {
        enabled: $("p53-enabled").checked,
        current: $("p53-current").checked,
        note: $("p53-note").value.trim()
      },
      catalogue: {
        artist_note: $("artist-note").value.trim(),
        album_note: $("album-note").value.trim(),
        artist_artwork: state.artistArtwork
      }
    });
  }

  async function loadCatalog() {
    try {
      const response = await authFetch("/api/local-entry-catalog");
      const data = await response.json();
      $("entry-select").replaceChildren(new Option("Choose an entry…", ""));
      data.entries.forEach((entry) => {
        $("entry-select").append(new Option(`${entry.artist} — ${entry.track}`, entry.slug));
      });
      setStatus(`${data.entries.length} local entries available.`);
    } catch (error) {
      setStatus(`Could not read local entries: ${error.message}`, "error");
    }
  }

  async function loadEntry() {
    const slug = $("entry-select").value;
    if (!slug) return setStatus("Choose an entry first.", "error");
    try {
      const response = await authFetch(`/api/local-entry/${encodeURIComponent(slug)}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "entry unavailable");

      // Check if there was an unsaved local autosave on this device
      const saved = checkAutosave(slug);
      const activeData = (saved && saved.record && saved.record.slug === slug) ? saved : data;

      $("edit-of").value = slug;
      state.signalId = activeData.record.signal_id || data.record.signal_id || "";
      state.coverFile = activeData.record.cover || data.record.cover || `${slug}.jpg`;
      state.coverUrl = activeData.record.cover_url || data.record.cover_url || "";
      state.artistArtwork = {
        ...GSIDraftContract.defaultArtistArtwork(),
        ...((activeData.catalogue && activeData.catalogue.artist_artwork) || (data.catalogue && data.catalogue.artist_artwork) || {})
      };

      for (const field of ["artist", "track", "album", "provider-link", "tags", "accent"]) {
        $(field).value = field === "provider-link" ? (activeData.record.link || "") : (activeData.record[field] || "");
      }

      $("p53-enabled").checked = Boolean(activeData.p53 && activeData.p53.enabled);
      $("p53-current").checked = Boolean(activeData.p53 && activeData.p53.current);
      $("p53-note").value = (activeData.p53 && activeData.p53.note) || "";
      $("artist-note").value = (activeData.catalogue && activeData.catalogue.artist_note) || "";
      $("album-note").value = (activeData.catalogue && activeData.catalogue.album_note) || "";

      state.sections.splice(0, state.sections.length, ...(activeData.sections || []));
      renderSections();
      $("edit-form").hidden = false;

      if (saved) {
        setStatus(`Loaded ${data.record.track} (restored unsaved edits from your device).`, "success");
      } else {
        setStatus(`Loaded ${data.record.track}. Changes remain local until you explicitly apply the draft.`, "success");
      }
    } catch (error) {
      setStatus(`Could not load entry: ${error.message}`, "error");
    }
  }

  async function saveDraft(event) {
    event.preventDefault();
    const draft = payload();
    try {
      const response = await authFetch("/api/local-entry-drafts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft)
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "draft rejected");
      clearAutosave($("edit-of").value);
      setStatus(`Saved ${result.filename} to the private draft inbox.`, "success");
    } catch (error) {
      setStatus(`Could not save draft: ${error.message}`, "error");
    }
  }

  async function buildEntry() {
    const slug = $("edit-of").value;
    if (!slug) return setStatus("Load an entry before building it.", "error");
    try {
      const response = await authFetch("/api/local-entry-publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload())
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "local build rejected");
      clearAutosave(slug);
      setStatus(`Built ${result.slug} and refreshed its catalogue rooms.`, "success");
    } catch (error) {
      setStatus(`Could not build entry: ${error.message}`, "error");
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

  $("load-entry").addEventListener("click", loadEntry);
  $("edit-form").addEventListener("submit", saveDraft);
  $("build-entry").addEventListener("click", buildEntry);

  // Auth panel handlers
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
      setStatus("Token updated. Refreshing local catalog…");
      loadCatalog();
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
  loadCatalog();
})();
