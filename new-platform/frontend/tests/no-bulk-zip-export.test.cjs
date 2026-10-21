const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const app = path.join(__dirname, "../app");
const read = file => fs.readFileSync(path.join(app, file), "utf8");

test("pipeline has no bulk ZIP download control or legacy layout", () => {
  assert.doesNotMatch(read("Workspace.tsx"), /FullTrialDownload|pipeline-setup-grid/);
  assert.doesNotMatch(read("globals.css"), /pipeline-setup-grid/);
  assert.equal(fs.existsSync(path.join(app, "FullTrialDownload.tsx")), false);
});

test("bulk ZIP download routes are removed, individual trial record access remains", () => {
  assert.equal(fs.existsSync(path.join(app, "api/full-trials/download/route.ts")), false);
  assert.equal(fs.existsSync(path.join(app, "api/full-trials/route.ts")), false);
  assert.equal(fs.existsSync(path.join(app, "api/full-trials/[nctId]/route.ts")), true);
  assert.equal(fs.existsSync(path.join(app, "api/full-trials/rows/route.ts")), true);
});
