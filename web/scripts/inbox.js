/*
 * Private Owner Feedback Inbox controller.
 * Authenticates the archive owner via Google Sign-In, reads private /hearts documents
 * from Firestore, aggregates per-track resonance, and supports 1-click local archive sync.
 */
import {
  OWNER_EMAIL,
  signInOwnerWithGoogle,
  signOutOwner,
  subscribeAuthState,
  listAllHeartsForOwner,
} from "./firebase-client.js";

const signInBtn = document.querySelector("#inbox-signin-btn");
const signOutBtn = document.querySelector("#inbox-signout-btn");
const userEmailEl = document.querySelector("#inbox-user-email");
const statusEl = document.querySelector("#inbox-status");
const gateEl = document.querySelector("#inbox-gate");
const dashboardEl = document.querySelector("#inbox-dashboard");
const totalHeartsEl = document.querySelector("#metric-total-hearts");
const uniqueTracksEl = document.querySelector("#metric-unique-tracks");
const totalNotesEl = document.querySelector("#metric-total-notes");
const trackListEl = document.querySelector("#inbox-track-list");
const notesListEl = document.querySelector("#inbox-notes-list");
const refreshBtn = document.querySelector("#inbox-refresh-btn");
const syncBtn = document.querySelector("#inbox-sync-btn");
const exportBtn = document.querySelector("#inbox-export-btn");

let latestHearts = [];

function setStatus(message, kind = "") {
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.dataset.kind = kind;
}

function escapeText(value) {
  return String(value ?? "");
}

function formatTimestamp(iso) {
  if (!iso) return "";
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function renderDashboard(hearts) {
  latestHearts = hearts;
  const byTrack = new Map();
  const notes = [];

  for (const h of hearts) {
    const key = h.slug || `${h.artist}-${h.track}`;
    if (!byTrack.has(key)) {
      byTrack.set(key, {
        slug: h.slug,
        track: h.track || h.slug,
        artist: h.artist || "",
        entryCount: 0,
        p53Count: 0,
        total: 0,
        noteCount: 0,
      });
    }
    const agg = byTrack.get(key);
    agg.total += 1;
    if (h.pageType === "p53") agg.p53Count += 1;
    else agg.entryCount += 1;
    if ((h.note || "").trim()) {
      agg.noteCount += 1;
      notes.push(h);
    }
  }

  const ranked = [...byTrack.values()].sort(
    (a, b) => b.total - a.total || b.noteCount - a.noteCount || a.track.localeCompare(b.track)
  );

  if (totalHeartsEl) totalHeartsEl.textContent = String(hearts.length);
  if (uniqueTracksEl) uniqueTracksEl.textContent = String(ranked.length);
  if (totalNotesEl) totalNotesEl.textContent = String(notes.length);

  if (trackListEl) {
    trackListEl.innerHTML = "";
    if (!ranked.length) {
      const empty = document.createElement("p");
      empty.className = "inbox-empty";
      empty.textContent = "No hearts recorded yet.";
      trackListEl.append(empty);
    } else {
      for (const item of ranked) {
        const row = document.createElement("div");
        row.className = "inbox-track-row";

        const meta = document.createElement("div");
        meta.className = "inbox-track-meta";
        const link = document.createElement("a");
        link.className = "inbox-track-title";
        link.href = item.entryCount > 0 ? `entries/${encodeURIComponent(item.slug)}.html` : `p53/${encodeURIComponent(item.slug)}.html`;
        link.textContent = escapeText(item.track);
        const sub = document.createElement("span");
        sub.className = "inbox-track-sub";
        const parts = [escapeText(item.artist)];
        if (item.entryCount) parts.push(`${item.entryCount} entry`);
        if (item.p53Count) parts.push(`${item.p53Count} P53`);
        if (item.noteCount) parts.push(`${item.noteCount} note${item.noteCount === 1 ? "" : "s"}`);
        sub.textContent = parts.filter(Boolean).join(" · ");
        meta.append(link, sub);

        const count = document.createElement("strong");
        count.className = "inbox-track-count";
        count.textContent = `${item.total}`;

        row.append(meta, count);
        trackListEl.append(row);
      }
    }
  }

  if (notesListEl) {
    notesListEl.innerHTML = "";
    if (!notes.length) {
      const empty = document.createElement("p");
      empty.className = "inbox-empty";
      empty.textContent = "No listener notes yet.";
      notesListEl.append(empty);
    } else {
      for (const n of notes) {
        const card = document.createElement("article");
        card.className = "inbox-note-card";

        const head = document.createElement("div");
        head.className = "inbox-note-head";
        const title = document.createElement("strong");
        title.textContent = `${escapeText(n.track)} — ${escapeText(n.artist)}`;
        const stamp = document.createElement("span");
        stamp.className = "inbox-note-meta";
        stamp.textContent = [n.pageType === "p53" ? "P53" : "Entry", formatTimestamp(n.updatedAt || n.createdAt)]
          .filter(Boolean)
          .join(" · ");
        head.append(title, stamp);

        const body = document.createElement("p");
        body.className = "inbox-note-body";
        body.textContent = escapeText(n.note);

        card.append(head, body);
        if (n.senderName) {
          const sig = document.createElement("span");
          sig.className = "inbox-note-sender";
          sig.textContent = `— ${escapeText(n.senderName)}`;
          card.append(sig);
        }
        notesListEl.append(card);
      }
    }
  }
}

async function refreshHearts() {
  setStatus("Loading private heart feedback…");
  try {
    const hearts = await listAllHeartsForOwner();
    renderDashboard(hearts);
    setStatus(`Loaded ${hearts.length} private heart record${hearts.length === 1 ? "" : "s"}.`, "success");
  } catch (err) {
    setStatus("Could not load hearts. Ensure you are signed in with the verified owner account.", "error");
    console.error(err);
  }
}

function downloadSnapshotJson() {
  const payload = {
    exportedAt: new Date().toISOString(),
    count: latestHearts.length,
    hearts: latestHearts,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "chaperone-hearts-snapshot.json";
  a.click();
  URL.revokeObjectURL(url);
}

signInBtn?.addEventListener("click", async () => {
  setStatus("Opening Google Sign-In…");
  try {
    await signInOwnerWithGoogle();
  } catch (err) {
    if (err?.code === "auth/popup-closed-by-user") {
      setStatus("Sign-in canceled.");
      return;
    }
    setStatus("Google Sign-In could not complete.", "error");
  }
});

signOutBtn?.addEventListener("click", async () => {
  await signOutOwner();
  setStatus("Signed out.");
});

refreshBtn?.addEventListener("click", refreshHearts);
exportBtn?.addEventListener("click", downloadSnapshotJson);

syncBtn?.addEventListener("click", async () => {
  if (!latestHearts.length) {
    setStatus("Nothing to sync yet.");
    return;
  }
  syncBtn.disabled = true;
  setStatus("Syncing hearts snapshot to local archive…");
  try {
    const res = await fetch("/api/hearts/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        syncedAt: new Date().toISOString(),
        hearts: latestHearts,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const out = await res.json();
    setStatus(`Synced ${out.count} hearts to local archive.`, "success");
  } catch {
    downloadSnapshotJson();
    setStatus("Local sync server isn't running here, so a JSON snapshot was downloaded instead.", "success");
  } finally {
    syncBtn.disabled = false;
  }
});

subscribeAuthState(async (user) => {
  const isOwner = Boolean(user && user.email === OWNER_EMAIL && user.emailVerified);
  if (userEmailEl) {
    userEmailEl.textContent = user?.email || "";
    userEmailEl.hidden = !user;
  }
  if (signInBtn) signInBtn.hidden = Boolean(user);
  if (signOutBtn) signOutBtn.hidden = !user;

  if (!user) {
    if (gateEl) gateEl.hidden = false;
    if (dashboardEl) dashboardEl.hidden = true;
    return;
  }

  if (!isOwner) {
    if (gateEl) gateEl.hidden = false;
    if (dashboardEl) dashboardEl.hidden = true;
    setStatus(`Signed in as ${user.email}, which does not have curator access.`, "error");
    return;
  }

  if (gateEl) gateEl.hidden = true;
  if (dashboardEl) dashboardEl.hidden = false;
  await refreshHearts();
});
