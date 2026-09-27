/* Shared browser-to-local Entry Loader contract. */
(() => {
  const DEFAULT_ARTIST_ARTWORK = () => ({
    data_url: "", mime: "", name: "", alt: "", width: 0, height: 0, bytes: 0
  });

  function slugify(value) {
    return String(value || "").toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  }

  function record(fields = {}) {
    const artist = String(fields.artist || "").trim();
    const track = String(fields.track || "").trim();
    return {
      signal_id: String(fields.signal_id || "").trim(), artist, track,
      album: String(fields.album || "").trim(), tags: String(fields.tags || "").trim(),
      link: String(fields.link || "").trim(),
      slug: String(fields.slug || slugify(`${artist}-${track}`)).trim(),
      cover: String(fields.cover || `${slugify(`${artist}-${track}`)}.jpg`).trim(),
      cover_url: String(fields.cover_url || "").trim(),
      accent: String(fields.accent || "").trim()
    };
  }

  function payload({ record: sourceRecord, sections = [], p53 = {}, catalogue = {}, editOf = "" } = {}) {
    return {
      schema: 1,
      editOf: String(editOf || "").trim(),
      record: record(sourceRecord),
      sections: sections.map((section) => ({
        title: String(section.title || ""),
        prompt: String(section.prompt || "Write what belongs here."),
        content: String(section.content || "")
      })),
      p53: {
        enabled: Boolean(p53.enabled), current: Boolean(p53.current),
        note: String(p53.note || "").trim()
      },
      catalogue: {
        artist_note: String(catalogue.artist_note || "").trim(),
        album_note: String(catalogue.album_note || "").trim(),
        artist_artwork: { ...DEFAULT_ARTIST_ARTWORK(), ...(catalogue.artist_artwork || {}) }
      }
    };
  }

  function validationIssues({ record: currentRecord, sections = [], p53 = {} } = {}) {
    const recordValue = record(currentRecord);
    const issues = [];
    if (!recordValue.artist) issues.push("artist");
    if (!recordValue.track) issues.push("track");
    if (!recordValue.album) issues.push("album");
    if (!recordValue.link) issues.push("provider link");
    if (recordValue.accent && !/^#[0-9a-f]{6}$/i.test(recordValue.accent)) issues.push("six-digit accent");
    if (!sections.some((section) => String(section.title || "").trim())) issues.push("at least one section");
    if (p53.current && !p53.enabled) issues.push("enable P53 before marking current");
    if (String(p53.note || "").length > 4000) issues.push("P53 note under 4000 characters");
    return issues;
  }

  window.GSIDraftContract = Object.freeze({
    defaultArtistArtwork: DEFAULT_ARTIST_ARTWORK, slugify, record, payload, validationIssues
  });
})();
