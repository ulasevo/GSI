(() => {
  const form = document.querySelector("#recommend-form");
  const status = document.querySelector("#recommend-status");
  if (!form || !status) return;

  const supportedProviders = new Map([
    ["music.apple.com", "Apple Music"], ["itunes.apple.com", "Apple Music"],
    ["open.spotify.com", "Spotify"], ["spotify.link", "Spotify"],
    ["youtube.com", "YouTube"], ["music.youtube.com", "YouTube Music"],
    ["youtu.be", "YouTube"], ["soundcloud.com", "SoundCloud"],
    ["bandcamp.com", "Bandcamp"], ["deezer.com", "Deezer"], ["tidal.com", "Tidal"],
  ]);

  const setStatus = (message, kind = "") => { status.textContent = message; status.dataset.kind = kind; };
  const payload = () => ({
    link: document.querySelector("#recommend-link").value.trim(),
    note: document.querySelector("#recommend-note").value.trim(),
    name: document.querySelector("#recommend-name").value.trim(),
    submittedAt: new Date().toISOString(),
  });

  const providerFor = (value) => {
    try {
      const url = new URL(value);
      const host = url.hostname.toLowerCase().replace(/^www\./, "");
      return [...supportedProviders.entries()].find(([domain]) => host === domain || host.endsWith(`.${domain}`))?.[1] || null;
    } catch {
      return null;
    }
  };

  function downloadPendingSignal(data) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "gsi-signal-recommendation.json";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = payload();
    if (!data.link) return setStatus("Paste a link before sending the signal.", "error");
    if (!data.note) return setStatus("Leave a note before sending the signal.", "error");
    if (!providerFor(data.link)) return setStatus("Use a link from a supported music provider.", "error");
    try {
      const response = await fetch("/api/recommendations", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
      if (!response.ok) throw new Error(`submission returned ${response.status}`);
      form.reset();
      setStatus("signal received.", "success");
    } catch (error) {
      downloadPendingSignal(data);
      setStatus("The review room is offline here, so a pending signal file was downloaded instead.", "success");
    }
  });
})();
