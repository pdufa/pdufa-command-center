const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");
const data = require("../data/focusLevelOneDocumentCoverage20261113.json");

test("32 exact unique Level 1 trial records with source receipts and computed five-component scores", () => {
  assert.equal(data.assessmentLevel, 1);
  assert.equal(data.records.length, 32);
  assert.equal(new Set(data.records.map(r => r.nct)).size, 32);
  assert.equal(data.records.filter(r => r.score === 100).length, 12);
  assert.equal(data.records.filter(r => r.score === 50).length, 20);
  assert.equal(data.approvalProbability, null);
  assert.match(data.definition, /NOT.*FDA probability/i);
  assert.match(data.reviewStatus, /PENDING/);
  for (const row of data.records) {
    assert.match(row.nct, /^NCT[0-9]{8}$/);
    assert.match(row.ticker, /^[A-Z]{2,6}$/);
    assert.match(row.registryLastUpdatePosted, /^\d{4}-\d{2}-\d{2}$/);
    assert.match(row.rawRegistrySourceSha256, /^[0-9a-f]{64}$/);
    assert.equal(
      row.score,
      row.identityPhase + row.designEndpoints + row.protocolSap +
      row.registryResults + row.sourceTraceability,
      "Component score mismatch for " + row.nct
    );
    assert.equal(row.identityPhase, 15);
    assert.equal(row.designEndpoints, 20);
    assert.equal(row.sourceTraceability, 15);
    assert.equal(row.protocolSap, row.protocolLinked && row.sapLinked ? 25 : 0);
    assert.equal(row.registryResults,
      row.primaryOutcomeResultsPosted && row.adverseEventResultsPosted ? 25 : 0);
    assert.ok(row.score >= 0 && row.score <= 100);
  }
});

test("site ASSESMENTS route includes Level 1 score table with evidence and no approval percent", () => {
  const page = fs.readFileSync(path.join(ROOT, "app", "predictions", "assessment", "page.tsx"), "utf8");
  const component = fs.readFileSync(path.join(ROOT, "app", "LevelOneFocusScores.tsx"), "utf8");
  const navigation = fs.readFileSync(path.join(ROOT, "app", "GlobalNavigation.tsx"), "utf8");
  assert.match(navigation, /ASSESMENTS.*\/predictions\/assessment/);
  assert.match(page, /import LevelOneFocusScores from/);
  assert.match(page, /<LevelOneFocusScores\/>/);
  assert.match(component, /data-testid="focus-level1-scores"/);
  assert.match(component, /data-testid="level1-score-row"/);
  assert.match(component, /ClinicalTrials\.gov/);
  assert.match(component, /registry-source SHA-256|Registry-source SHA-256/);
  assert.match(component, /NOT FDA approval probabilities/);
  assert.match(component, /scientific review pending/);
  assert.doesNotMatch(component, /FDA approval probability:\s*\{row\.score\}/);
});

test("Level 1 scores are snapshot bound, not falsely promoted into scientific/PDUFA completion", () => {
  assert.match(data.rosterStatus, /not independently reconciled/i);
  assert.match(data.definition, /NOT scientific PDUFA/i);
  assert.ok(data.sourceRun.startsWith("https://github.com/pdufa/pdufa-command-center/actions/runs/"));
  assert.ok(data.sourceArtifact.includes("/artifacts/"));
  assert.equal(data.records.length, 32);
});
