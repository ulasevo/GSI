// Exercise P53 sharing fallbacks, download/copy actions, and PEEK accessibility state.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "../web/scripts/p53-transmission.js"), "utf8");
const canonical = "https://example.test/p53/song.html";

function makeHarness({ canShare, shareImpl, clipboardWrite, execCommandResult = true, withModal = true, previewUrl = "" } = {}) {
  const handlers = {};
  const downloads = [];
  const copiedViaExec = [];
  let clipboardWritten = null;
  let shared = undefined;
  let modalOpened = false;

  function makeClassList(initial = []) {
    const set = new Set(initial);
    return {
      add: (...cls) => cls.forEach(c => set.add(c)),
      remove: (...cls) => cls.forEach(c => set.delete(c)),
      toggle: (c, force) => (force === undefined ? (set.has(c) ? set.delete(c) : set.add(c)) : (force ? set.add(c) : set.delete(c))),
      contains: (c) => set.has(c),
    };
  }

  function makeElement(tag, initialText = "") {
    const attrs = {};
    const children = [];
    const el = {
      tagName: tag,
      textContent: initialText,
      innerHTML: initialText,
      disabled: false,
      dataset: {},
      style: {},
      classList: makeClassList(),
      children,
      addEventListener: (ev, cb) => {
        if (!el._listeners) el._listeners = {};
        el._listeners[ev] = cb;
      },
      setAttribute: (k, v) => { attrs[k] = String(v); },
      getAttribute: (k) => (Object.hasOwn(attrs, k) ? attrs[k] : null),
      removeAttribute: (k) => { delete attrs[k]; },
      append: (...nodes) => children.push(...nodes),
      closest: () => null,
      querySelector: () => null,
      select: () => {},
      remove: () => {},
      click: () => {
        if (tag === "a") downloads.push({ download: el.download, href: el.href });
      },
    };
    return el;
  }

  const shareTrigger = makeElement("button", "Share");
  const storyModal = withModal
    ? { showModal: () => { modalOpened = true; }, close() {}, addEventListener() {}, getBoundingClientRect: () => ({ top: 0, left: 0, width: 300, height: 500 }) }
    : { addEventListener() {} };
  const btnShare = makeElement("button", "Share card ↗");
  const btnDownload = makeElement("button", "Download card");
  const btnCopy = makeElement("button", "Copy link");
  const storyStatus = makeElement("p", "");

  let auditionBtn = null;
  let streamBlock = null;
  if (previewUrl) {
    auditionBtn = makeElement("button", "PEEK");
    auditionBtn.dataset.previewUrl = previewUrl;
    auditionBtn.setAttribute("aria-label", "Peek signal of Song");
    streamBlock = makeElement("div");
    streamBlock.querySelector = (sel) => (sel === ".audition-status" ? streamBlock.children.find(c => c.className?.includes("audition-status")) || null : null);
    auditionBtn.closest = (sel) => (sel === ".stream-block" ? streamBlock : null);
  }

  const canvas = {
    toBlob(callback) {
      Promise.resolve(callback({})).then(
        () => handlers.blobDone?.(),
        (err) => handlers.blobErr?.(err)
      );
    },
    toDataURL() { return "data:image/png;base64,AA=="; },
    getContext: () => null,
    setAttribute() {},
  };

  const elements = {
    "#p53-transmission-context": { textContent: JSON.stringify({ slug: "song", track: "Song", artistName: "Artist" }) },
    "#share-transmission": shareTrigger,
    "#story-modal": storyModal,
    "#story-btn-share": btnShare,
    "#story-btn-download": btnDownload,
    "#story-btn-copy": btnCopy,
    "#story-status": storyStatus,
    "#story-card-canvas": canvas,
    ".audition-trigger": auditionBtn,
  };

  const contextApi = {
    read: () => new URLSearchParams(),
    archiveParams: () => new URLSearchParams(),
    href: () => "../index.html",
    canonicalHref: () => canonical,
  };

  const body = makeElement("body");
  const document = {
    querySelector: (selector) => elements[selector] || null,
    querySelectorAll: () => [],
    createElement: (tag) => {
      const node = makeElement(tag);
      if (tag === "textarea") {
        const origSelect = node.select;
        node.select = () => {
          origSelect();
          copiedViaExec.push(node.value);
        };
      }
      return node;
    },
    execCommand: (cmd) => (cmd === "copy" ? execCommandResult : false),
    body,
  };

  const navigator = {};
  if (canShare !== undefined) navigator.canShare = canShare;
  if (shareImpl) {
    navigator.share = shareImpl;
  } else if (shareImpl === undefined) {
    navigator.share = async (data) => { shared = data; };
  }
  if (clipboardWrite) {
    navigator.clipboard = { writeText: async (text) => { clipboardWritten = text; } };
  }

  const windowListeners = {};
  const window = {
    GSIContext: contextApi,
    setTimeout() { return 1; },
    clearTimeout() {},
    addEventListener: (ev, cb) => { windowListeners[ev] = cb; },
  };

  const audioInstances = [];
  class FakeAudio {
    constructor(src) {
      this.src = src;
      this.paused = true;
      this.ended = false;
      this.currentTime = 0;
      this._listeners = {};
      audioInstances.push(this);
    }
    addEventListener(ev, cb) { this._listeners[ev] = cb; }
    removeEventListener(ev, cb) { if (this._listeners[ev] === cb) delete this._listeners[ev]; }
    removeAttribute() {}
    load() {}
    async play() {
      this.paused = false;
      this._listeners.play?.();
    }
    pause() {
      this.paused = true;
      this._listeners.pause?.();
    }
  }
  class File { constructor(parts, name, options) { this.name = name; this.type = options.type; } }

  vm.runInNewContext(source, { document, navigator, window, GSIContext: contextApi, URLSearchParams, File, Audio: FakeAudio });

  return {
    shareTrigger,
    btnShare,
    btnDownload,
    btnCopy,
    storyStatus,
    auditionBtn,
    streamBlock,
    audioInstances,
    windowListeners,
    body,
    getModalOpened: () => modalOpened,
    getShared: () => shared,
    getDownloads: () => downloads,
    getClipboardWritten: () => clipboardWritten,
    getCopiedViaExec: () => copiedViaExec,
    async clickShareCard() {
      const p = new Promise((resolve, reject) => { handlers.blobDone = resolve; handlers.blobErr = reject; });
      await btnShare._listeners.click();
      await p;
    },
  };
}

(async () => {
  // 1. Canonical URL + PNG file when device supports both
  const both = makeHarness({ canShare: () => true });
  await both.clickShareCard();
  assert.equal(both.getShared().url, canonical);
  assert.equal(both.getShared().files[0].name, "p53-song-transmission.png");

  // 2. Image-only fallback when URL in payload is rejected
  const fileOnly = makeHarness({ canShare: (data) => !data.url });
  await fileOnly.clickShareCard();
  assert.equal(fileOnly.getShared().url, undefined);
  assert.equal(fileOnly.getShared().files[0].name, "p53-song-transmission.png");

  // 3. Download fallback when Web Share with files is unavailable
  const unavailable = makeHarness({ canShare: () => false });
  await unavailable.clickShareCard();
  assert.equal(unavailable.getShared(), undefined);
  assert.equal(unavailable.getDownloads().length, 1);
  assert.equal(unavailable.getDownloads()[0].download, "p53-song-story.png");

  // 4. User cancels native share (AbortError) -> do NOT trigger unintended download
  const aborted = makeHarness({
    canShare: () => true,
    shareImpl: async () => { throw Object.assign(new Error("User cancelled"), { name: "AbortError" }); },
  });
  await aborted.clickShareCard();
  assert.equal(aborted.getDownloads().length, 0);

  // 5. Non-abort share error falls back cleanly to card download
  const errored = makeHarness({
    canShare: () => true,
    shareImpl: async () => { throw new Error("Share target failed"); },
  });
  await errored.clickShareCard();
  assert.equal(errored.getDownloads().length, 1);

  // 6. Explicit Download card button
  const dl = makeHarness();
  dl.btnDownload._listeners.click();
  assert.equal(dl.getDownloads().length, 1);
  assert.equal(dl.getDownloads()[0].download, "p53-song-story.png");
  assert.equal(dl.storyStatus.textContent, "Card downloaded");

  // 7. Copy link button (Clipboard API + execCommand fallback + copy failure)
  const clip = makeHarness({ clipboardWrite: true });
  await clip.btnCopy._listeners.click();
  assert.equal(clip.getClipboardWritten(), canonical);
  assert.equal(clip.storyStatus.textContent, "Link copied");

  const execCopy = makeHarness({ clipboardWrite: false, execCommandResult: true });
  await execCopy.btnCopy._listeners.click();
  assert.deepEqual(execCopy.getCopiedViaExec(), [canonical]);
  assert.equal(execCopy.storyStatus.textContent, "Link copied");

  const execFail = makeHarness({ clipboardWrite: false, execCommandResult: false });
  await execFail.btnCopy._listeners.click();
  assert.equal(execFail.storyStatus.textContent, "Couldn't copy link");

  // 8. Classic share fallback when <dialog>.showModal is unavailable
  const noModal = makeHarness({ withModal: false });
  await noModal.shareTrigger._listeners.click();
  assert.equal(noModal.getModalOpened(), false);
  assert.equal(noModal.getShared().url, canonical);

  // 9. Accessible PEEK preview state transitions (idle -> playing -> paused -> ended -> error -> pagehide)
  const peek = makeHarness({ previewUrl: "https://example.test/preview.m4a" });
  assert.equal(peek.auditionBtn.getAttribute("aria-pressed"), "false");
  assert.match(peek.auditionBtn.getAttribute("aria-label"), /Peek 30-second preview of Song/);

  await peek.auditionBtn._listeners.click();
  assert.equal(peek.auditionBtn.getAttribute("aria-pressed"), "true");
  assert.ok(peek.auditionBtn.classList.contains("is-playing"));
  assert.ok(peek.body.classList.contains("signal-auditioning"));
  assert.match(peek.auditionBtn.getAttribute("aria-label"), /Pause 30-second preview of Song/);

  await peek.auditionBtn._listeners.click();
  assert.equal(peek.auditionBtn.getAttribute("aria-pressed"), "false");
  assert.ok(peek.auditionBtn.classList.contains("is-paused"));
  assert.ok(!peek.body.classList.contains("signal-auditioning"));
  assert.match(peek.auditionBtn.getAttribute("aria-label"), /Resume 30-second preview of Song/);

  await peek.auditionBtn._listeners.click();
  assert.equal(peek.auditionBtn.getAttribute("aria-pressed"), "true");
  peek.audioInstances[0].ended = true;
  peek.audioInstances[0].paused = true;
  peek.audioInstances[0]._listeners.ended();
  assert.equal(peek.auditionBtn.getAttribute("aria-pressed"), "false");
  assert.ok(!peek.body.classList.contains("signal-auditioning"));
  assert.match(peek.auditionBtn.getAttribute("aria-label"), /Replay 30-second preview of Song/);

  peek.windowListeners.pagehide();
  assert.equal(peek.auditionBtn.getAttribute("aria-pressed"), "false");

  peek.auditionBtn._listeners.click();
  peek.audioInstances[1]._listeners.error();
  assert.equal(peek.auditionBtn.disabled, true);
  assert.equal(peek.auditionBtn.getAttribute("aria-pressed"), "false");
  assert.ok(peek.auditionBtn.classList.contains("is-error"));

  console.log("P53 share: URL, image-only, abort/error, download, copy-link and PEEK accessibility paths passed");
})().catch((error) => { console.error(error); process.exitCode = 1; });
