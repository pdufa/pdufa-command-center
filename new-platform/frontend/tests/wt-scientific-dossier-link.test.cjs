"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

test("WT exact-program cards link to trial evidence only when exact NCT is mapped", () => {
  const source = fs.readFileSync(path.join(__dirname, "../app/Workspace.tsx"), "utf8");
  const wt = source.slice(source.indexOf('nav==="WT" && <div className="wt-page">'));
  assert.ok(wt.startsWith('nav==="WT"'));
  assert.match(wt, /selectedRecord && trialSheetUrl\(selectedRecord\) && <a href=\{trialSheetUrl\(selectedRecord\)\}/);
  assert.match(wt, /20 levels \/ 40 assessments \/ two evidence-readiness grades/);
  assert.match(wt, /selectedRecord && !trialSheetUrl\(selectedRecord\)/);
  assert.match(wt, /no exact NCT linked/);
});

test("WT remains independent of existing GEM JR, GEM and FS\/FA scoring", () => {
  const src = fs.readFileSync(path.join(__dirname, "../app/Workspace.tsx"), "utf8");
  const start = src.indexOf('nav==="WT" && <div className="wt-page">');
  const end = src.indexOf('Legacy ticker-only selections',start);
  assert.ok(end>start);
  const snippet=src.slice(start,end);
  assert.match(snippet, /wtTrialPreferences\[programId\]/);
  assert.match(snippet, /presetFlags=\{preference.presets\[selectedStage\]\}/);
  assert.match(snippet, /onPresetToggle=/);
  assert.match(snippet, /Open exact program checklist/);
  assert.doesNotMatch(snippet, /onClick=\{\(\)=>\s*(?:runScientificScore|setGemFsFa)/);
});
