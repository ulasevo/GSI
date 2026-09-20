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
  const state = { sections: [] };
  const $ = (selector) => document.querySelector(selector);
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
          <input class="section-title" aria-label="Section title" value="${section.title.replaceAll('"', '&quot;')}" placeholder="Section title">
          <textarea aria-label="Writing for ${section.title || "new section"}" placeholder="${section.prompt}">${section.content}</textarea>
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
      accent: "#444444"
    };
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
      `accent: ${escapeYaml(record.accent)}`,
      "---",
      "",
      `# ${record.track || "Untitled"} — ${record.artist || "Unknown artist"}`,
      "",
      `![cover](../covers/${record.cover})`,
      "",
      `**Album:** ${record.album}`,
      `**Accent:** \`${record.accent}\``,
      "",
      sections
    ];
    return lines.join("\n").replace(/\n{3,}/g, "\n\n").trim() + "\n";
  }

  function updatePreview() {
    const record = currentRecord();
    const validation = $("#validation");
    const issues = [];
    if (!record.artist) issues.push("artist");
    if (!record.track) issues.push("track");
    if (!record.album) issues.push("album");
    if (!record.link) issues.push("provider link");
    if (!state.sections.some((section) => section.title.trim())) issues.push("at least one section");
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
      showArtwork(song.artworkUrl100 || "", `${song.collectionName || "ARTWORK"} / ARTWORK CHECK`);
      setStatus("Metadata resolved. Check the names before exporting.", "success");
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
    if (!record.artist || !record.track || !record.album || !record.link) {
      $("#validation").textContent = "Add the link, artist, track, and album before downloading.";
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

  $("#resolve-link").addEventListener("click", resolveLink);
  $("#add-section").addEventListener("click", () => addSection());
  $("#copy-markdown").addEventListener("click", copyMarkdown);
  $("#download-markdown").addEventListener("click", downloadMarkdown);
  ["provider-link", "artist", "track", "album", "tags"].forEach((id) => $("#" + id).addEventListener("input", updatePreview));
  DEFAULT_SECTIONS.forEach(([title, prompt]) => addSection(title, prompt));
  updatePreview();
})();
