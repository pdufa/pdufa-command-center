const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const app=path.resolve(__dirname,"../app");
const root=path.resolve(__dirname,"../../..");
const read=p=>fs.readFileSync(p,"utf8");

test("FOCUS owns the trial roster instead of re-exporting a retired P3 page",()=>{
  const focus=read(path.join(app,"focus/page.tsx"));
  assert.match(focus,/export default function FocusPage\s*\(/);
  assert.match(focus,/snapshot\.records/);
  assert.doesNotMatch(focus,/from\s+["']\.\.\/p3-post-data\/page/);
});

test("retired P3 POST-DATA public route only redirects to canonical FOCUS",()=>{
  const retired=read(path.join(app,"p3-post-data/page.tsx"));
  assert.match(retired,/permanentRedirect\(["']\/focus["']\)/);
  assert.doesNotMatch(retired,/snapshot\.records|<table|<h1>/);
});

test("top-level trial navigation has POOL and FOCUS, not a retired P3 tab",()=>{
  const nav=read(path.join(app,"GlobalNavigation.tsx"));
  assert.match(nav,/label:"POOL"/);
  assert.match(nav,/label:"FOCUS"/);
  assert.doesNotMatch(nav,/label:"P3(?: POST-DATA)?"/);
});

test("nightly workflows are clearly named for their live POOL and FOCUS destinations",()=>{
  const pool=read(path.join(root,".github/workflows/p3-full-pool-discovery.yml"));
  const focus=read(path.join(root,".github/workflows/p3-post-data-google-sheet-sync.yml"));
  assert.match(pool,/^name: POOL Master Evidence Nightly Discovery/m);
  assert.match(focus,/^name: FOCUS Google Sheets → Website source snapshot/m);
  assert.match(read(path.join(root,"scripts/auto_promote_p3_post_data.py")),/SHEET_NAME = "FOCUS"/);
  const publisher=read(path.join(root,"scripts/sync_p3_post_data_from_google_sheet.py"));
  // FOCUS is the stable sheet identity; its physical schema may widen (28 → 31 columns).
  // Column-width contracts belong to the source extraction/schema tests, not to the retirement guard.
  assert.match(publisher,/RANGE\s*=\s*"FOCUS!A4:[A-Z]{1,2}"/);
  assert.doesNotMatch(publisher,/RANGE\s*=\s*["\x27]P3(?: POST-DATA)?!/);
});
