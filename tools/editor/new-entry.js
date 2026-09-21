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
  const state = {
    sections: [],
    p53: { enabled: false, current: false, note: "" },
    catalogue: { artist_note: "", album_note: "" },
    artworkUrl: ""
  };
  const $ = (selector) => document.querySelector(selector);
  const escapeHtml = (value) => String(value || "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
  const escapeYaml = (value) => JSON.stringify(value || "");
  const slugify = (value) => (value || "").toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const getValue = (id) => $(`#${id}`).value.trim();

  function setStatus(message, kind = "") {
    const status = $("#resolve-status");
    status.textContent = message;
    status.dataset.kind = kind;
  }

  function addSection(title = "", prompt = "Write what belongs here.", content = "") {
    state.sections.push({ title, prompt, content });
    renderSections();
    updatePreview();
  }

  function renderSections() {
    const list = $("#section-list");
    list.replaceChildren();
    state.sections.forEach((section, index) => {
      const card = document.createElement("article");
      card.className = "section-card";
      card.innerHTML = `
        <span class="section-number">${String(index + 1).padStart(2, "0")}</span>
        <div class="section-fields">
          <input class="section-title" aria-label="Section title" value="${escapeHtml(section.title)}" placeholder="Section title">
          <textarea aria-label="Writing for ${escapeHtml(section.title || "new section")}" placeholder="${escapeHtml(section.prompt)}">${escapeHtml(section.content)}</textarea>
        </div>
        <div class="section-actions">
          <button type="button" data-action="up" aria-label="Move section up">↑</button>
          <button type="button" data-action="down" aria-label="Move section down">↓</button>
          <button type="button" data-action="remove" aria-label="Remove section">×</button>
        </div>`;
      const title = card.querySelector(".section-title");
      const content = card.querySelector("textarea");
      title.addEventListener("input", () => { section.title = title.value; content.setAttribute("aria-label", `Writing for ${section.title || "new section"}`); updatePreview(); });
      content.addEventListener("input", () => { section.content = content.value; updatePreview(); });
      card.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => {
        const action = button.dataset.action;
        if (action === "remove") state.sections.splice(index, 1);
        if (action === "up" && index > 0) [state.sections[index - 1], state.sections[index]] = [state.sections[index], state.sections[index - 1]];
        if (action === "down" && index < state.sections.length - 1) [state.sections[index + 1], state.sections[index]] = [state.sections[index], state.sections[index + 1]];
        renderSections();
        updatePreview();
      }));
      list.append(card);
    });
  }

  function currentRecord() {
    const artist = getValue("artist");
    const track = getValue("track");
    const album = getValue("album");
    return {
      artist, track, album, tags: getValue("tags"),
      link: getValue("provider-link"),
      slug: slugify(`${artist}-${track}`),
      cover: `${slugify(`${artist}-${track}`)}.jpg`,
      cover_url: state.artworkUrl,
      accent: getValue("accent")
    };
  }

  function draftPayload() {
    return {
      schema: 1,
      record: currentRecord(),
      sections: state.sections.map((section) => ({ ...section })),
      p53: { ...state.p53 },
      catalogue: { ...state.catalogue }
    };
  }

  function updateRoomPlan() {
    const plan = $("#room-plan");
    if (!plan) return;
    const artist = getValue("artist");
    const album = getValue("album");
    plan.textContent = artist && album
      ? `This build will create or update the ${artist} artist room and the ${album} album room. Add notes here if you want those rooms to carry authored context.`
      : "Resolve a provider link to see which artist and album rooms this signal will create or update.";
  }

  function validationIssues(record = currentRecord()) {
    const issues = [];
    if (!record.artist) issues.push("artist");
    if (!record.track) issues.push("track");
    if (!record.album) issues.push("album");
    if (!record.link) issues.push("provider link");
    if (record.accent && !/^#[0-9a-f]{6}$/i.test(record.accent)) issues.push("six-digit accent");
    if (!state.sections.some((section) => section.title.trim())) issues.push("at least one section");
    if (state.p53.current && !state.p53.enabled) issues.push("enable P53 before marking current");
    if (state.p53.note.length > 4000) issues.push("P53 note under 4000 characters");
    return issues;
  }

  function markdown() {
    const record = currentRecord();
    const sections = state.sections.filter((section) => section.title.trim()).map((section) => {
      const body = section.content.trim();
      return `## ${section.title.trim()}\n\n${body || `<!-- ${section.prompt} -->`}`;
    }).join("\n\n");
    const lines = [
      "---",
      `artist: ${escapeYaml(record.artist)}`,
      `track: ${escapeYaml(record.track)}`,
      `album: ${escapeYaml(record.album)}`,
      `cover: ${escapeYaml(`../covers/${record.cover}`)}`,
      `accent: ${escapeYaml(record.accent || "#444444")}`,
      "---",
      "",
      `# ${record.track || "Untitled"} — ${record.artist || "Unknown artist"}`,
      "",
      `![cover](../covers/${record.cover})`,
      "",
      `**Album:** ${record.album}`,
      `**Accent:** \`${record.accent || "#444444"}\``,
      "",
      sections
    ];
    return lines.join("\n").replace(/\n{3,}/g, "\n\n").trim() + "\n";
  }

  function updatePreview() {
    const record = currentRecord();
    const validation = $("#validation");
    const issues = validationIssues(record);
    validation.textContent = issues.length ? `Still needed: ${issues.join(", ")}.` : `Ready to export entries/${record.slug}.md`;
    $("#markdown-preview").textContent = markdown();
  }

  function showArtwork(url, caption = "ARTWORK CHECK") {
    const preview = $("#artwork-preview");
    const image = $("#artwork-image");
    if (!preview || !image || !url) return;
    image.src = url.replace("100x100bb", "600x600bb");
    image.onload = () => {
      preview.hidden = false;
      $("#artwork-caption").textContent = caption;
    };
    image.onerror = () => { preview.hidden = true; };
  }

  async function resolveLink() {
    const raw = getValue("provider-link");
    if (!raw) return setStatus("Paste a raw Apple Music or Spotify URL first.", "error");
    let url;
    try { url = new URL(raw); } catch { return setStatus("That is not a valid URL.", "error"); }
    const isApple = ["music.apple.com", "itunes.apple.com"].includes(url.hostname.toLowerCase());
    if (!isApple || !url.searchParams.get("i")) {
      setStatus("Spotify links are accepted, but enter artist, track, and album manually.");
      updatePreview();
      return;
    }
    setStatus("Resolving Apple Music metadata…");
    try {
      const response = await fetch(`https://itunes.apple.com/lookup?id=${encodeURIComponent(url.searchParams.get("i"))}`);
      if (!response.ok) throw new Error(`lookup returned ${response.status}`);
      const payload = await response.json();
      const song = (payload.results || []).find((item) => item.kind === "song");
      if (!song) throw new Error("no song found");
      $("#artist").value = song.artistName || "";
      $("#track").value = song.trackName || "";
      $("#album").value = song.collectionName || "";
      state.artworkUrl = song.artworkUrl100 ? song.artworkUrl100.replace("100x100bb", "600x600bb") : "";
      showArtwork(song.artworkUrl100 || "", `${song.collectionName || "ARTWORK"} / ARTWORK CHECK`);
      setStatus("Metadata resolved. Check the names before exporting.", "success");
      updateRoomPlan();
      updatePreview();
    } catch (error) {
      setStatus("Apple lookup was unavailable. Fill the three identity fields manually; the link can still be preserved.", "error");
    }
  }

  function copyMarkdown() {
    navigator.clipboard.writeText(markdown()).then(() => setStatus("Markdown copied to the clipboard.", "success"));
  }

  function downloadMarkdown() {
    const record = currentRecord();
    const issues = validationIssues(record);
    if (issues.length) {
      $("#validation").textContent = `Still needed: ${issues.join(", ")}.`;
      return;
    }
    const blob = new Blob([markdown()], { type: "text/markdown;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${record.slug || "new-entry"}.md`;
    link.click();
    URL.revokeObjectURL(link.href);
    $("#draft-state").textContent = "EXPORTED / NEW FILE";
  }

  function downloadJson() {
    const issues = validationIssues();
    if (issues.length) {
      $("#validation").textContent = `Still needed: ${issues.join(", ")}.`;
      return;
    }
    const record = currentRecord();
    const blob = new Blob([JSON.stringify(draftPayload(), null, 2) + "\n"], { type: "application/json;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${record.slug || "new-entry"}.gsi-draft.json`;
    link.click();
    URL.revokeObjectURL(link.href);
    $("#draft-state").textContent = "EXPORTED / DRAFT JSON";
  }

  async function saveLocalDraft() {
    if (!["localhost", "127.0.0.1"].includes(location.hostname)) {
      return setStatus("Local handoff is only available on the private local server.", "error");
    }
    const issues = validationIssues();
    if (issues.length) {
      $("#validation").textContent = `Still needed: ${issues.join(", ")}.`;
      return;
    }
    try {
      const response = await fetch("/api/entry-drafts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draftPayload())
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "local handoff failed");
      $("#draft-state").textContent = `DRAFT SAVED / ${payload.filename}`;
      setStatus("Saved to the private local inbox. Review it before writing source files.", "success");
    } catch (error) {
      setStatus(`Local handoff failed: ${error.message}`, "error");
    }
  }

  async function publishLocal() {
    if (!["localhost", "127.0.0.1"].includes(location.hostname)) {
      return setStatus("Local publishing is only available on the private local server.", "error");
    }
    const issues = validationIssues();
    if (issues.length) {
      $("#validation").textContent = `Still needed: ${issues.join(", ")}.`;
      return;
    }
    if (!state.artworkUrl) {
      return setStatus("Resolve an Apple Music link first so the cover can be cached safely.", "error");
    }
    try {
      const response = await fetch("/api/local-entry-publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draftPayload())
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "local build failed");
      $("#draft-state").textContent = `BUILT / ${payload.slug}`;
      setStatus(`Built the entry and rooms. Open ${payload.entry} to review it.`, "success");
    } catch (error) {
      setStatus(`Local build failed: ${error.message}`, "error");
    }
  }

  function toggleP53Fields() {
    state.p53.enabled = $("#p53-enabled").checked;
    $("#p53-fields").hidden = !state.p53.enabled;
    $("#p53-current").disabled = !state.p53.enabled;
    if (!state.p53.enabled) {
      state.p53.current = false;
      $("#p53-current").checked = false;
    }
    updatePreview();
  }

  async function loadSections() {
    try {
      const response = await fetch("editor-config.json", { cache: "no-store" });
      if (!response.ok) throw new Error("config unavailable");
      const config = await response.json();
      const prompts = config.sectionInfo || {};
      const titles = Array.isArray(config.sections) ? config.sections : [];
      if (!titles.length) throw new Error("no sections configured");
      titles.forEach((title) => {
        const fallback = DEFAULT_SECTIONS.find(([candidate]) => candidate === title);
        addSection(title, prompts[title] || (fallback ? fallback[1] : "Write what belongs here."));
      });
    } catch (error) {
      DEFAULT_SECTIONS.forEach(([title, prompt]) => addSection(title, prompt));
    }
    updatePreview();
  }

  $("#resolve-link").addEventListener("click", resolveLink);
  $("#add-section").addEventListener("click", () => addSection());
  $("#copy-markdown").addEventListener("click", copyMarkdown);
  $("#download-markdown").addEventListener("click", downloadMarkdown);
  $("#download-json").addEventListener("click", downloadJson);
  $("#save-local-draft").addEventListener("click", saveLocalDraft);
  $("#p53-enabled").addEventListener("change", toggleP53Fields);
  $("#p53-current").addEventListener("change", () => { state.p53.current = $("#p53-current").checked; updatePreview(); });
  $("#p53-note").addEventListener("input", () => { state.p53.note = $("#p53-note").value; updatePreview(); });
  ["provider-link", "artist", "track", "album", "tags", "accent"].forEach((id) => $("#" + id).addEventListener("input", () => { updateRoomPlan(); updatePreview(); }));
  $("#artist-note").addEventListener("input", () => { state.catalogue.artist_note = $("#artist-note").value; updatePreview(); });
  $("#album-note").addEventListener("input", () => { state.catalogue.album_note = $("#album-note").value; updatePreview(); });
  $("#publish-local").addEventListener("click", publishLocal);
  if (["localhost", "127.0.0.1"].includes(location.hostname)) {
    $("#save-local-draft").hidden = false;
    $("#publish-local").hidden = false;
  }
  loadSections();
})();
