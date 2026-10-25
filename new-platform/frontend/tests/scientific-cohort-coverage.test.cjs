"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");

require.extensions[".ts"] = (mod, file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
    },
  }).outputText, file
);
const { computePublishedScienceCoverage } = require("../lib/scientific-cohort-coverage.ts");

const trial = (id, programId, nctId) => ({ id: "TRIAL|" + id, programId, nctId: nctId ?? id });
const application = (programId, ticker) => ({
  id: "APPLICATION|" + ticker + "|2026-08-01|example", programId, ticker,
});
const p = (...nums) => "PDUFA-" + String(nums[0]).padStart(6, "0");
function workspace() {
  return {
    asOf: new Date().toISOString().slice(0, 10), mode: "LIVE_READ_ONLY_GITHUB_SOURCE",
    pipeline: [
      application(p(71), "DBVT"),
      application(p(76), "ESPR"),
      trial("NCT02142738", p(101)),
      trial("NCT04280705", p(102)),
    ],
    members: {
      GEM_JR: { rows: [trial("NCT02142738", p(101)), application(p(71), "DBVT")] },
      GEM: { rows: [trial("NCT04280705", p(102)), trial("NCT02142738", p(101))] },
    },
    sourceHealth: {
      state: "COMPLETE_PUBLISHED", pipelineSourceParity: { exactPrograms: 4 },
    },
  };
}

test("published list coverage reflects actual stage membership, exact trial keys and WT applications", () => {
  const report = computePublishedScienceCoverage(workspace(), {
    watch: [p(71)], trade: [p(76), p(101), p(500)],
  });
  assert.equal(report.pipelineRows, 4);
  assert.equal(report.status, "PUBLISHED_SNAPSHOT_AUDIT");
  assert.deepEqual(report.stages.map(stage => [
    stage.list, stage.uniquePrograms, stage.exactNctPrograms, stage.unlinkedPrograms,
    stage.sourceMissingPrograms, stage.conflictingIdentityPrograms,
  ]), [
    ["GEM JR", 2, 1, 1, 0, 0],
    ["GEM", 2, 2, 0, 0, 0],
    ["WT", 4, 1, 2, 1, 0],
  ]);
  assert.equal(report.stages[2].sampleExactNct[0].nctId, "NCT02142738");
  assert.deepEqual(report.stages[2].sampleUnlinkedPrograms.map(item => item.sourceType), [
    "APPLICATION", "APPLICATION",
  ]);
  assert.equal(report.archivedScientificRecordsVerified, null);
  assert.equal(report.scientificFindingsVerified, null);
  assert.equal(report.approvalProbability, null);
  assert.equal(report.importsPerformed, false);
  assert.equal(report.qualificationPresetsChanged, false);
});

test("multiple memberships never double count a permanent Program ID or count a ticker as a trial", () => {
  const snap = workspace();
  snap.members.GEM_JR.rows.push(trial("NCT02142738", p(101)));
  const report = computePublishedScienceCoverage(snap, {
    watch: [p(71), p(71)], trade: [p(71)],
  });
  const jr = report.stages[0];
  assert.equal(jr.publishedRows, 3);
  assert.equal(jr.uniquePrograms, 2);
  assert.equal(jr.exactNctPrograms, 1);
  const wt = report.stages[2];
  assert.equal(wt.uniquePrograms, 1);
  assert.equal(wt.exactNctPrograms, 0);
  assert.equal(wt.unlinkedPrograms, 1);
});

test("contradictory source keys or NCTs are quarantined, never counted as verified links", () => {
  const snap = workspace();
  snap.members.GEM_JR.rows = [
    trial("NCT02142738", p(101)),
    trial("NCT04280705", p(101)),
    trial("NCT04280705", p(102), "NCT02142738"),
  ];
  const report = computePublishedScienceCoverage(snap, { watch: [], trade: [] });
  assert.equal(report.stages[0].conflictingIdentityPrograms, 2);
  assert.equal(report.stages[0].exactNctPrograms, 0);
});

test("application ID with a claimed NCT never becomes a trial without verified source identity", () => {
  const snap = workspace();
  snap.members.GEM_JR.rows = [{
    id: "APPLICATION|DBVT|2026-10-25|viaskin-peanut",
    nctId: "NCT02142738",
    programId: p(71),
  }];
  const r = computePublishedScienceCoverage(snap, { watch: [p(71)], trade: [] });
  assert.equal(r.stages[0].exactNctPrograms, 0);
  assert.equal(r.stages[0].unlinkedPrograms, 1);
  assert.equal(r.stages[2].exactNctPrograms, 0);
});

test("an invalid, stale, or mismatched published source fails closed or states not verified", () => {
  const snap = workspace();
  snap.sourceHealth.pipelineSourceParity.exactPrograms = 3;
  assert.throws(() => computePublishedScienceCoverage(snap, { watch: [], trade: [] }),
    /parity totals disagree/);
  snap.sourceHealth.pipelineSourceParity.exactPrograms = 4;
  snap.sourceHealth.state = "STALE";
  assert.equal(computePublishedScienceCoverage(snap, { watch: [], trade: [] }).status,
    "SOURCE_NOT_FRESHLY_VERIFIED");
  snap.sourceHealth.state = "PARTIAL";
  assert.equal(computePublishedScienceCoverage(snap, { watch: [], trade: [] }).status,
    "SOURCE_NOT_FRESHLY_VERIFIED");
  snap.sourceHealth.state = "FULL";
  snap.mode = "FALLBACK_SOURCE";
  assert.equal(computePublishedScienceCoverage(snap, { watch: [], trade: [] }).status,
    "SOURCE_NOT_FRESHLY_VERIFIED");
  assert.throws(() => computePublishedScienceCoverage({}, { watch: [], trade: [] }));
  assert.throws(() => computePublishedScienceCoverage(workspace(), { watch: ["DBVT"], trade: [] }));
  assert.throws(() => computePublishedScienceCoverage(workspace(), { watch: [], trade: ["PDUFA-XXX"] }));
});

test("large or malformed snapshots never produce scientific membership or grades", () => {
  const snap = workspace();
  snap.members.GEM.rows[0].nctId = 123;
  assert.throws(() => computePublishedScienceCoverage(snap, { watch: [], trade: [] }));
  assert.throws(() => computePublishedScienceCoverage(workspace(), { watch: [], trade: Array(501).fill(p(71)) }));
});

test("coverage page requires an explicit click and refuses scientific score claims", () => {
  const page = fs.readFileSync(require("node:path").join(__dirname, "../app/science/coverage/page.tsx"), "utf8");
  assert.match(page, /Check current list coverage/);
  assert.match(page, /onClick=\{\(\) => void audit\(\)\}/);
  assert.match(page, /\/api\/scientific-cohort\/coverage/);
  assert.match(page, /No scientific records imported/);
  assert.match(page, /No readiness grade or approval probability assigned/);
  assert.doesNotMatch(page, /runScan\(|placeOrder\(|startBatchImport\(/);
  const home = fs.readFileSync(require("node:path").join(__dirname, "../app/page.tsx"), "utf8");
  assert.match(home, /href="\/science\/coverage"/);
});

test("source health reflects real COMPLETE_PUBLISHED semantics, not invented FULL", () => {
  const snap = workspace();
  assert.equal(computePublishedScienceCoverage(snap, { watch: [], trade: [] }).status,
    "PUBLISHED_SNAPSHOT_AUDIT");
  for (const state of ["FULL", "PARTIAL", "STALE", "UNKNOWN", "BROKEN"]) {
    snap.sourceHealth.state = state;
    assert.equal(computePublishedScienceCoverage(snap, { watch: [], trade: [] }).status,
      "SOURCE_NOT_FRESHLY_VERIFIED", state);
  }
  snap.sourceHealth.state = "COMPLETE_PUBLISHED";
  snap.sourceHealth.issues = ["source temporarily incomplete"];
  assert.equal(computePublishedScienceCoverage(snap, { watch: [], trade: [] }).status,
    "SOURCE_NOT_FRESHLY_VERIFIED");
});

test("stale or future published dates cannot claim current NCT coverage", () => {
  const snap = workspace();
  snap.asOf = new Date(Date.now() - 6 * 86400000).toISOString().slice(0, 10);
  assert.equal(computePublishedScienceCoverage(snap, { watch: [], trade: [] }).status,
    "SOURCE_NOT_FRESHLY_VERIFIED");
  snap.asOf = new Date(Date.now() + 4 * 86400000).toISOString().slice(0, 10);
  assert.equal(computePublishedScienceCoverage(snap, { watch: [], trade: [] }).status,
    "SOURCE_NOT_FRESHLY_VERIFIED");
  for (const invalid of ["garbage", "2026-02-30", "2026-13-11", "2026/10/25"]) {
    snap.asOf = invalid;
    assert.throws(() => computePublishedScienceCoverage(snap, { watch: [], trade: [] }),
      /Published source date/);
  }
});
