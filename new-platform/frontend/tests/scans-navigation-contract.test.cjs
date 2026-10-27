"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const workspace = fs.readFileSync(path.join(__dirname, "../app/Workspace.tsx"), "utf8");

test("active Next.js dashboard exposes one SCANS top-level tab and panel", () => {
  assert.match(workspace, /type TopNav = [^;]*"SCANS"/);
  assert.match(workspace, /requested === "SCANS"\) \{ setTop\("SCANS"\)/);
  assert.match(workspace, /onClick=\{\(\)=>\{setTop\("SCANS"\);setMobileNavOpen\(false\);\}\}>SCANS<\/button>/);
  assert.match(workspace, /top==="SCANS" && <PublishedScansPanel \/>/);
  assert.equal((workspace.match(/>SCANS<\/button>/g) || []).length, 1);
  assert.equal((workspace.match(/top==="SCANS" && <PublishedScansPanel \/>/g) || []).length, 1);
});

test("SCANS tab uses the published scan panel rather than retired Streamlit UI", () => {
  assert.match(workspace, /import PublishedScansPanel from "\.\/PublishedScansPanel";/);
  assert.doesNotMatch(workspace, /render_scans_activity\(embedded=True\)/);
});
