/*
 * Browser-state contract test.
 * This runs the small shared helper without a browser so URL-state regressions
 * fail before they become confusing broken return links.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "..", "web", "scripts", "gsi-context.js"),
  "utf8",
);

const stored = new Map();
const storage = {
  getItem(key) { return stored.get(key) ?? null; },
  setItem(key, value) { stored.set(key, value); },
};
const sandbox = {
  URL,
  URLSearchParams,
  Object,
  Set,
  localStorage: storage,
  window: {
    location: {
      href: "https://gsi.test/p53/secret-door.html?filter=dreamy&view=gallery&format=albums#signal",
      search: "?filter=dreamy&view=gallery&format=albums",
    },
    localStorage: storage,
  },
};

vm.runInNewContext(source, sandbox, { filename: "gsi-context.js" });
const context = sandbox.window.GSIContext;
assert.ok(context, "the shared context helper should expose its public API");
assert.deepEqual([...context.allowedViews], ["poster", "wall", "gallery"]);

const state = context.read();
const valid = context.archiveParams({
  state,
  filterLabels: { dreamy: "Dreamy" },
});
assert.equal(valid.toString(), "filter=dreamy&view=gallery&format=albums");
assert.equal(context.href("../index.html", valid), "../index.html?filter=dreamy&view=gallery&format=albums");
assert.equal(context.canonicalHref(), "https://gsi.test/p53/secret-door.html");

const cleaned = context.archiveParams({
  state: new URLSearchParams("filter=unknown&view=sideways&format=artists"),
  filterLabels: { dreamy: "Dreamy" },
});
assert.equal(cleaned.toString(), "");

context.storeView("poster");
assert.equal(context.loadView(), "poster");
assert.equal(context.loadView("wall"), "poster");

const homeStateSource = fs.readFileSync(
  path.join(__dirname, "..", "web", "scripts", "home-state.js"),
  "utf8",
);
vm.runInNewContext(homeStateSource, sandbox, { filename: "home-state.js" });
const homeState = sandbox.window.GSIHomeState;
assert.ok(homeState, "the homepage should expose its pure state helpers");
assert.equal(
  homeState.contextHref({
    baseHref: "../index.html",
    activeFilter: "dreamy",
    activeView: "gallery",
    activeFormat: "albums",
    allowedViews: context.allowedViews,
  }),
  "../index.html?filter=dreamy&view=gallery&format=albums",
);
assert.equal(homeState.signalLabel(3), "03 SIGNALS");
assert.equal(homeState.albumLabel(2), "02 signals");
assert.equal(
  homeState.cardMatchesFilter({ dataset: { tags: "dreamy p53" } }, "dreamy"),
  true,
);
assert.equal(
  homeState.cardMatchesFilter({ dataset: { tags: "dreamy p53" } }, "bite"),
  false,
);

console.log("browser-state-contract=passed");
