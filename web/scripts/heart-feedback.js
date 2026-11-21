/*
 * Private Heart Feedback controller for Chaperone (GSI) Entry and Radio P53 pages.
 * Renders album-gradient shimmer animation on press, keeps counts 100% private,
 * offers an optional dismissible micro-note popover, and syncs privately to Firestore.
 */
import {
  createVisitorHeart,
  attachVisitorHeartNote,
  removeVisitorHeart,
} from "./firebase-client.js";

const TOKEN_KEY = "gsi-visitor-token-v1";
const HEARTS_MAP_KEY = "gsi-hearted-signals-v1";

function generateVisitorToken() {
  const bytes = new Uint8Array(18);
  if (window.crypto?.getRandomValues) {
    window.crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < bytes.length; i++) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
  }
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-";
  let token = "";
  for (const b of bytes) {
    token += alphabet[b % alphabet.length];
  }
  return token;
}

function getVisitorToken() {
  try {
    const existing = localStorage.getItem(TOKEN_KEY);
    if (existing && /^[a-zA-Z0-9_-]{12,48}$/.test(existing)) {
      return existing;
    }
    const created = generateVisitorToken();
    localStorage.setItem(TOKEN_KEY, created);
    return created;
  } catch {
    return generateVisitorToken();
  }
}

function readLocalHearts() {
  try {
    const raw = localStorage.getItem(HEARTS_MAP_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeLocalHearts(map) {
  try {
    localStorage.setItem(HEARTS_MAP_KEY, JSON.stringify(map));
  } catch {
    // storage optional in private browsing
  }
}

function readPageSignalContext() {
  const entryNode = document.querySelector("#gsi-entry-context");
  if (entryNode) {
    try {
      const ctx = JSON.parse(entryNode.textContent || "{}");
      if (ctx.slug) {
        return {
          pageType: "entry",
          slug: String(ctx.slug).trim().toLowerCase(),
          track: String(ctx.track || "").trim(),
          artist: String(ctx.artistName || "").trim(),
        };
      }
    } catch {
      // fall through
    }
  }

  const p53Node = document.querySelector("#p53-transmission-context");
  if (p53Node) {
    try {
      const ctx = JSON.parse(p53Node.textContent || "{}");
      if (ctx.slug) {
        return {
          pageType: "p53",
          slug: String(ctx.slug).trim().toLowerCase(),
          track: String(ctx.track || "").trim(),
          artist: String(ctx.artistName || "").trim(),
          trackPalette: ctx.trackPalette || null,
        };
      }
    } catch {
      // fall through
    }
  }

  return null;
}

function initHeartFeedback() {
  const btn = document.querySelector("#heart-trigger");
  if (!btn) return;
  const signal = readPageSignalContext();
  if (!signal || !signal.slug) return;

  // On P53 pages, scope the song's own album palette onto the Heart button so it shimmers
  // with the track's custom album gradient rather than only the P53 cover palette.
  if (signal.pageType === "p53" && signal.trackPalette) {
    const tp = signal.trackPalette;
    if (tp.primary) btn.style.setProperty("--art-primary", tp.primary);
    if (tp.glow) btn.style.setProperty("--art-glow", tp.glow);
    if (tp.secondary) btn.style.setProperty("--art-secondary", tp.secondary);
  }

  const visitorToken = getVisitorToken();
  const storageKey = `${signal.pageType}:${signal.slug}`;
  const heartsMap = readLocalHearts();
  let isHearted = Boolean(heartsMap[storageKey]);
  let savedNote = typeof heartsMap[storageKey] === "object" ? String(heartsMap[storageKey]?.note || "") : "";
  let savedName = typeof heartsMap[storageKey] === "object" ? String(heartsMap[storageKey]?.senderName || "") : "";
  let busy = false;

  // Build compact dismissible micro-note popover dynamically (never shown on load)
  const popover = document.createElement("aside");
  popover.className = "heart-note-popover";
  popover.setAttribute("role", "dialog");
  popover.setAttribute("aria-label", `Leave a note for ${signal.track}`);
  popover.hidden = true;
  popover.innerHTML = `
    <div class="heart-note-head">
      <span class="heart-note-prompt">Resonated with you? Leave a quick note for ulaş</span>
      <button type="button" class="heart-note-close" aria-label="Close note prompt">✕</button>
    </div>
    <form class="heart-note-form" novalidate>
      <input type="text" class="heart-note-hp" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">
      <input type="text" class="heart-note-input" name="note" maxlength="400" placeholder="Optional short note…" aria-label="Optional note for ulaş">
      <div class="heart-note-row">
        <input type="text" class="heart-note-name" name="senderName" maxlength="60" placeholder="Name (optional)" aria-label="Your name (optional)">
        <button type="submit" class="heart-note-submit">Send</button>
      </div>
      <p class="heart-note-status" role="status" aria-live="polite"></p>
    </form>
  `;
  document.body.append(popover);

  const form = popover.querySelector(".heart-note-form");
  const hpInput = popover.querySelector(".heart-note-hp");
  const noteInput = popover.querySelector(".heart-note-input");
  const nameInput = popover.querySelector(".heart-note-name");
  const submitBtn = popover.querySelector(".heart-note-submit");
  const closeBtn = popover.querySelector(".heart-note-close");
  const statusEl = popover.querySelector(".heart-note-status");

  function setButtonState(pressed, animate = false) {
    btn.setAttribute("aria-pressed", pressed ? "true" : "false");
    btn.setAttribute(
      "aria-label",
      pressed
        ? `Remove heart from ${signal.track || "this track"}`
        : `Heart ${signal.track || "this track"}`
    );
    btn.classList.toggle("is-hearted", pressed);
    if (animate && pressed) {
      btn.classList.remove("is-animating");
      // Force reflow so rapid re-toggles replay cleanly
      void btn.offsetWidth;
      btn.classList.add("is-animating");
    } else if (!pressed) {
      btn.classList.remove("is-animating");
    }
  }

  function positionPopover() {
    if (popover.hidden) return;
    const rect = btn.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const popW = Math.min(316, vw - 24);
    popover.style.width = `${popW}px`;

    let left = rect.right - popW;
    if (left < 12) left = Math.max(12, rect.left);
    if (left + popW > vw - 12) left = vw - popW - 12;

    const popH = popover.offsetHeight || 168;
    let top = rect.bottom + 10;
    if (top + popH > vh - 14 && rect.top - popH - 10 > 12) {
      top = rect.top - popH - 10;
    }

    popover.style.left = `${Math.round(left)}px`;
    popover.style.top = `${Math.round(top)}px`;
  }

  function openPopover() {
    noteInput.value = savedNote;
    nameInput.value = savedName;
    statusEl.textContent = "";
    statusEl.dataset.kind = "";
    popover.hidden = false;
    positionPopover();
    requestAnimationFrame(() => {
      popover.classList.add("is-open");
      positionPopover();
    });
  }

  function closePopover() {
    popover.classList.remove("is-open");
    popover.hidden = true;
  }

  setButtonState(isHearted, false);

  window.addEventListener("resize", positionPopover, { passive: true });
  window.addEventListener("scroll", positionPopover, { passive: true });

  document.addEventListener("click", (event) => {
    if (popover.hidden) return;
    if (popover.contains(event.target) || btn.contains(event.target)) return;
    closePopover();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !popover.hidden) {
      closePopover();
      btn.focus();
    }
  });

  closeBtn.addEventListener("click", () => {
    closePopover();
  });

  btn.addEventListener("click", async () => {
    if (busy) return;
    busy = true;
    const nextState = !isHearted;
    isHearted = nextState;
    setButtonState(isHearted, nextState);

    const latestMap = readLocalHearts();
    if (nextState) {
      latestMap[storageKey] = {
        heartedAt: new Date().toISOString(),
        note: savedNote,
        senderName: savedName,
      };
      writeLocalHearts(latestMap);
      openPopover();
      try {
        await createVisitorHeart({
          slug: signal.slug,
          pageType: signal.pageType,
          track: signal.track,
          artist: signal.artist,
          visitorToken,
        });
      } catch {
        // Optimistic UI remains intact even if offline; Firestore error already logged structurally.
      }
    } else {
      delete latestMap[storageKey];
      writeLocalHearts(latestMap);
      savedNote = "";
      savedName = "";
      closePopover();
      try {
        await removeVisitorHeart({
          slug: signal.slug,
          visitorToken,
        });
      } catch {
        // Quiet offline resilience
      }
    }
    busy = false;
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (hpInput.value.trim()) {
      closePopover();
      return;
    }
    const noteText = noteInput.value.trim().slice(0, 400);
    const senderText = nameInput.value.trim().slice(0, 60);
    if (!noteText) {
      statusEl.textContent = "Write a short note first, or close to keep just your heart.";
      statusEl.dataset.kind = "hint";
      noteInput.focus();
      return;
    }

    submitBtn.disabled = true;
    statusEl.textContent = "Sending…";
    statusEl.dataset.kind = "";
    try {
      await attachVisitorHeartNote({
        slug: signal.slug,
        visitorToken,
        note: noteText,
        senderName: senderText,
      });
      savedNote = noteText;
      savedName = senderText;
      const latestMap = readLocalHearts();
      latestMap[storageKey] = {
        heartedAt: latestMap[storageKey]?.heartedAt || new Date().toISOString(),
        note: savedNote,
        senderName: savedName,
      };
      writeLocalHearts(latestMap);
      statusEl.textContent = "Note received — thank you.";
      statusEl.dataset.kind = "success";
      window.setTimeout(() => {
        closePopover();
      }, 1150);
    } catch {
      statusEl.textContent = "Couldn't reach the archive right now — your heart is still saved locally.";
      statusEl.dataset.kind = "error";
    } finally {
      submitBtn.disabled = false;
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initHeartFeedback);
} else {
  initHeartFeedback();
}
