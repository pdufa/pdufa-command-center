const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../../..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const tracker = read("new-platform/frontend/app/LiveScansProgress.tsx");
const published = read("new-platform/frontend/app/PublishedScansPanel.tsx");
const ledger = read("new-platform/frontend/app/VerificationLedgerPanel.tsx");
const workflow = read(".github/workflows/pdufa-nightly-missing-sources.yml");
const orchestrator = read(".github/workflows/pdufa-overnight-sequential.yml");

test("three non-facing source collectors are hidden by their exact job identity only", () => {
  const match = tracker.match(/function backgroundEvidenceJob\(name: string\): boolean \{\s*return (\/[^\n]+\/i)\.test\(name\);\s*\}/);
  assert.ok(match, "visibility must be a testable, exact-job predicate");
  const predicate = vm.runInNewContext(match[1]);
  for (const family of ["FINANCIAL", "MARKET", "ISSUER"]) {
    assert.equal(predicate.test("sources / source_" + family.toLowerCase() + " / Live PDUFA " + family + " source check"), true);
  }
  for (const stage of ["FDA", "SEC"]) {
    assert.equal(predicate.test("sources / source_" + stage.toLowerCase() + " / Live PDUFA " + stage + " source check"), false);
  }
  assert.equal(predicate.test("clinical / phase3_results / FOCUS — published Phase 3 registry results"), false);
  assert.equal(predicate.test("PIPELINE — trial inventory"), false);
});

test("source jobs are hidden from checklist but still counted in all GitHub progress", () => {
  assert.match(tracker, /const data = progress\(jobs, report\?\.totalJobs, report\?\.truncated\)/);
  assert.match(tracker, /const task = currentTask\(jobs\)/);
  assert.match(tracker, /const visibleJobs = jobs\.filter\(job => !backgroundEvidenceJob\(job\.name\)\)/);
  assert.match(tracker, /visibleJobs\.map\(job =>/);
  assert.match(tracker, /jobs\.filter\(j => stageForJob\(j\.name\) === s\.key\)/);
  assert.match(tracker, /const taskName = taskIsBackground/);
  assert.match(tracker, /const taskStepName = taskIsBackground/);
  assert.match(tracker, /backgroundJobCount > 0/);
  assert.match(tracker, /source-audit results/);
});

test("FDA SEC visible cards and complete audit remain; drill-down evidence is retained", () => {
  assert.match(published, /filter\(s => s\.source === "FDA" \|\| s\.source === "SEC"\)/);
  assert.match(published, /sources\?\.findings_verified/);
  assert.match(published, /sources\?\.findings_due/);
  assert.match(published, /sources\?\.required_findings_unresolved/);
  assert.match(published, /<VerificationLedgerPanel \/>/);
  for (const category of ["FINANCIAL", "MARKET", "ISSUER"]) {
    assert.ok(ledger.includes('"' + category + '"'), "Evidence source " + category + " must stay auditable");
  }
});

test("all background data collection and nightly reconciliation remain wired", () => {
  for (const [job, dependency] of [
    ["source_financial", "source_sec"],
    ["source_market", "source_financial"],
    ["source_issuer", "source_market"],
  ]) {
    assert.ok(workflow.includes("  " + job + ":"));
    assert.ok(workflow.includes("    needs: " + dependency));
  }
  assert.match(workflow, /needs: \[source_fda, source_sec, source_financial, source_market, source_issuer\]/);
  assert.match(orchestrator, /pdufa-nightly-missing-sources\.yml/);
  assert.match(orchestrator, /pdufa-shared-enrichment\.yml/);
});
