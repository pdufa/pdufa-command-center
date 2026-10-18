const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");
for (const extension of [".ts", ".tsx"]) require.extensions[extension] = (loaded, file) => {
  const result = ts.transpileModule(fs.readFileSync(file, "utf8"), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  } });
  loaded._compile(result.outputText, file);
};
const { EMPTY_TRIAL_FILTERS, matchesTrialFilters, withCriterion, activeTrialFilters } = require("../lib/trial-filters.ts");
const { filterPipelineRows, pipelineAvailability } = require("../lib/pipeline-data.ts");
const qualified = { id: "APPLICATION|AAA|DRUG_A", ticker: "AAA", stage: "PDUFA Decision", band: "+90 DAYS", drug: "Drug A",
  trialFilters: { registeredPhase: "Phase 3", resultsReleased: true, primaryOutcome: "SUCCESS", secondFinancingClosed: true,
    firstFinancingClosed: true, resultsDate: "2026-09-01", secondClose: "2026-10-01", evidence: ["VERIFIED", "STALE"], lists: ["GEM", "PIPELINE"], runwayMonths: 18 } };
const rows = [qualified,
  { id: "TRIAL|NCT00000001", ticker: "AAA", stage: "Phase 3", band: "NO PDUFA YET", drug: "Other drug",
    trialFilters: { registeredPhase: "Phase 3", resultsReleased: false, primaryOutcome: "UNKNOWN", lists: ["PIPELINE"] } },
  { id: "TRIAL|NCT00000002", ticker: "BBB", stage: "Phase 3 Results", band: "NO PDUFA YET",
    trialFilters: { registeredPhase: "Phase 2/3", resultsReleased: false, primaryOutcome: "UNKNOWN" } },
  { id: "TRIAL|NCT00000003", ticker: "CCC", stage: "Phase 3 Results", band: "NO PDUFA YET",
    trialFilters: { registeredPhase: "Phase 3", resultsReleased: true, primaryOutcome: "FAILED", secondFinancingClosed: false } },
  { id: "TRIAL|NCT00000004", ticker: "DDD", stage: "Unknown", band: "NO PDUFA YET" },
];
const select = trial => filterPipelineRows(rows, { trial, asOf: "2026-10-18" }, row => row.band);

test("all four criteria narrow by AND and keep Phase 3 programs at later regulatory stages", () => {
  assert.equal(select(EMPTY_TRIAL_FILTERS).length, 5);
  let values = withCriterion(EMPTY_TRIAL_FILTERS, "phase3", true);
  assert.equal(select(values).length, 3);
  values = withCriterion(values, "released", true);
  assert.equal(select(values).length, 2);
  values = withCriterion(values, "successful", true);
  assert.deepEqual(select(values), [qualified]);
  values = withCriterion(values, "financed", true);
  assert.deepEqual(select(values), [qualified]);
  assert.equal(activeTrialFilters(values), 4);
  assert.equal(activeTrialFilters(EMPTY_TRIAL_FILTERS), 0);
});

test("trial, current-stage, date, and identity filters intersect without ticker evidence leakage", () => {
  const trial = { ...EMPTY_TRIAL_FILTERS, secondFinancingClosed: true };
  assert.deepEqual(filterPipelineRows(rows, { trial, stages: ["PDUFA Decision"], dates: ["+90 DAYS"] }, row => row.band), [qualified]);
  assert.equal(filterPipelineRows(rows, { trial, stages: ["Phase 3"] }, row => row.band).length, 0);
  assert.equal(select({ ...EMPTY_TRIAL_FILTERS, company: "AAA", registeredPhase: "Phase 3" }).length, 2);
  assert.equal(select({ ...EMPTY_TRIAL_FILTERS, company: "AAA", drug: "other", secondFinancingClosed: true }).length, 0);
});

test("date, cash and missing-evidence dropdowns preserve unknown rather than treating it as a pass", () => {
  assert.equal(matchesTrialFilters(qualified, { ...EMPTY_TRIAL_FILTERS, resultsWindow: "30" }, "2026-10-18"), false);
  assert.equal(matchesTrialFilters(qualified, { ...EMPTY_TRIAL_FILTERS, resultsWindow: "90", runway: "18" }, "2026-10-18"), true);
  assert.equal(select({ ...EMPTY_TRIAL_FILTERS, runway: "24" }).length, 0);
  assert.equal(select({ ...EMPTY_TRIAL_FILTERS, runway: "UNKNOWN" }).length, 4);
  assert.equal(select({ ...EMPTY_TRIAL_FILTERS, evidence: "MISSING" }).length, 1);
  assert.deepEqual(select({ ...EMPTY_TRIAL_FILTERS, evidence: "STALE" }), [qualified]);
  assert.deepEqual(select({ ...EMPTY_TRIAL_FILTERS, membership: "GEM" }), [qualified]);
});

test("stage/date availability totals use the same trial filter as displayed results", () => {
  const trial = withCriterion(EMPTY_TRIAL_FILTERS, "released", true);
  const availability = pipelineAvailability(rows, { trial }, row => row.band, ["Phase 3", "Phase 3 Results", "PDUFA Decision"], ["NO PDUFA YET", "+90 DAYS"]);
  assert.deepEqual(availability.stageCounts.map(item => item.count), [0, 1, 1]);
  assert.deepEqual(availability.dateCounts.map(item => item.count), [1, 1]);
  assert.equal(availability.rows.length, select(trial).length);
});

test("the new filter section renders four accessible qualification checkboxes with evidence help", () => {
  const React = require("react");
  const { renderToStaticMarkup } = require("react-dom/server");
  const Filters = require("../app/TrialQualificationFilters.tsx").default;
  const html = renderToStaticMarkup(React.createElement(Filters, { rows, countRows: rows, value: EMPTY_TRIAL_FILTERS, onChange() {} }));
  assert.match(html, /TRIAL FILTERS/);
  assert.equal((html.match(/type="checkbox"/g) || []).length, 4);
  assert.match(html, /More trial filters/);
  assert.match(html, /Unknown evidence does not pass/);
  assert.doesNotMatch(html, / disabled=""/);
});


test("GEM JR two-trial option requires two distinct valid NCT IDs", () => {
  const { normalizeTrialId, twoTrialInputError } = require("../lib/two-trial-programs.ts");
  assert.equal(twoTrialInputError(["", ""]), "Enter both Trial 1 and Trial 2 NCT IDs.");
  assert.match(twoTrialInputError(["NCT12345678", ""] ), /Enter both/);
  assert.match(twoTrialInputError(["NCT12345678", "trial-B"]), /valid ClinicalTrials/);
  assert.match(twoTrialInputError(["NCT12345678", "NCT12345678"]), /different registered/);
  assert.equal(normalizeTrialId(" nct12345678 "), "NCT12345678");
  assert.equal(twoTrialInputError(["NCT12345678", "nct87654321"]), null);
});
