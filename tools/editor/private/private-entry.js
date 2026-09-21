(() => {
  const state = { sections: [], coverFile: "" };
  const $ = (id) => document.getElementById(id);
  const setStatus = (message, kind = "") => { $("status").textContent = message; $("status").dataset.kind = kind; };

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
      title.addEventListener("input", () => { section.title = title.value; });
      content.addEventListener("input", () => { section.content = content.value; });
      fields.append(title, content);
      card.append(number, fields);
      list.append(card);
    });
  }

  function record() {
    return {
      artist: $("artist").value.trim(), track: $("track").value.trim(), album: $("album").value.trim(),
      link: $("provider-link").value.trim(), tags: $("tags").value.trim(), accent: $("accent").value.trim(),
      slug: $("edit-of").value, cover: state.coverFile || `${$("edit-of").value}.jpg`
    };
  }

  function payload() {
    return {
      schema: 1, editOf: $("edit-of").value, record: record(), sections: state.sections,
      p53: { enabled: $("p53-enabled").checked, current: $("p53-current").checked, note: $("p53-note").value.trim() },
      catalogue: { artist_note: $("artist-note").value.trim(), album_note: $("album-note").value.trim() },
    };
  }

  async function loadCatalog() {
    try {
      const response = await fetch("/api/local-entry-catalog");
      const payload = await response.json();
      $("entry-select").replaceChildren(new Option("Choose an entry…", ""));
      payload.entries.forEach((entry) => $("entry-select").append(new Option(`${entry.artist} — ${entry.track}`, entry.slug)));
      setStatus(`${payload.entries.length} local entries available.`);
    } catch (error) { setStatus(`Could not read local entries: ${error.message}`, "error"); }
  }

  async function loadEntry() {
    const slug = $("entry-select").value;
    if (!slug) return setStatus("Choose an entry first.", "error");
    try {
      const response = await fetch(`/api/local-entry/${encodeURIComponent(slug)}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "entry unavailable");
      $("edit-of").value = slug;
      state.coverFile = payload.record.cover || `${slug}.jpg`;
      for (const field of ["artist", "track", "album", "provider-link", "tags", "accent"]) $(field).value = field === "provider-link" ? payload.record.link : payload.record[field];
      $("p53-enabled").checked = Boolean(payload.p53.enabled);
      $("p53-current").checked = Boolean(payload.p53.current);
      $("p53-note").value = payload.p53.note || "";
      $("artist-note").value = payload.catalogue?.artist_note || "";
      $("album-note").value = payload.catalogue?.album_note || "";
      state.sections.splice(0, state.sections.length, ...payload.sections);
      renderSections();
      $("edit-form").hidden = false;
      setStatus(`Loaded ${payload.record.track}. Changes remain local until you explicitly apply the draft.`, "success");
    } catch (error) { setStatus(`Could not load entry: ${error.message}`, "error"); }
  }

  async function saveDraft(event) {
    event.preventDefault();
    const draft = payload();
    try {
      const response = await fetch("/api/local-entry-drafts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(draft) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "draft rejected");
      setStatus(`Saved ${result.filename} to the private draft inbox.`, "success");
    } catch (error) { setStatus(`Could not save draft: ${error.message}`, "error"); }
  }

  async function buildEntry() {
    if (!$("edit-of").value) return setStatus("Load an entry before building it.", "error");
    try {
      const response = await fetch("/api/local-entry-publish", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload()) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "local build rejected");
      setStatus(`Built ${result.slug} and refreshed its catalogue rooms.`, "success");
    } catch (error) { setStatus(`Could not build entry: ${error.message}`, "error"); }
  }

  $("load-entry").addEventListener("click", loadEntry);
  $("edit-form").addEventListener("submit", saveDraft);
  $("build-entry").addEventListener("click", buildEntry);
  loadCatalog();
})();
