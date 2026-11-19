const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {createElement} = require("react");
const {renderToStaticMarkup} = require("react-dom/server");
const ts = require("typescript");

require.extensions[".tsx"] = (module, filename) => module._compile(
  ts.transpileModule(readFileSync(filename, "utf8"), {compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    jsx: ts.JsxEmit.ReactJSX,
  }}).outputText, filename
);
const Panel = require("../app/HistoricalScientificBacktest.tsx").default;

const digest = "b".repeat(64);
const evaluation = {
  cohortLabel: "Verified test subset",
  eligibleEvents: 2,
  lockSha256: digest,
  summary: Array.from({length:6}, (_, index) => ({
    level: "L0" + (index + 1),
    events: 2, predicted: 1, abstained: 1, correct: 1, incorrect: 0,
    coverage: 0.5, accuracy: 1, accuracy_ci95_wilson_low: 0.2065, accuracy_ci95_wilson_high: 1,
    protocol: "CANONICAL_HISTORICAL_FDA_DIRECTION_V1",
    rule_set: "SCIENTIFIC_L01_L06_HISTORICAL_DIRECTION_V1", lock_sha256: digest,
  })),
};

const show = (surface, input) => renderToStaticMarkup(createElement(Panel, {surface, evaluation:input}));

test("shows the verified subset and independent level metrics on the assessment surface", () => {
  const html = show("ASSESSMENTS", evaluation);
  assert.match(html, /Verified test subset · 2 eligible FDA actions/);
  assert.match(html, /L06 · Regulatory readiness/);
  assert.match(html, /20.6%–100.0%/);
  assert.match(html, /<td>50.0%<\/td>/);
  assert.match(show("FOCUS", evaluation), /\/past#historical-fda-backtest/);
  assert.match(show("PAST", evaluation), /\/assessments#historical-fda-backtest/);
  assert.doesNotMatch(show("FOCUS", evaluation), /<table>/);
});

test("keeps accuracy unavailable until canonical, receipt-bound rows agree", () => {
  const badInputs = [
    undefined,
    {...evaluation, lockSha256:"c".repeat(64)},
    {...evaluation, eligibleEvents:196},
    {...evaluation, summary:evaluation.summary.map(row => ({...row, rule_set:"EXPERIMENTAL"}))},
    {...evaluation, summary:evaluation.summary.map(row => ({...row, coverage:1}))},
  ];
  for (const input of badInputs) {
    const html = show("ASSESSMENTS", input);
    assert.match(html, /Verified historical accuracy is unavailable/);
    assert.doesNotMatch(html, /<table>/);
  }
});

test("all abstentions retain coverage and leave accuracy unavailable", () => {
  const summary = evaluation.summary.map(row => ({
    ...row, predicted:0, correct:0, abstained:2, coverage:0,
    accuracy:null, accuracy_ci95_wilson_low:null, accuracy_ci95_wilson_high:null,
  }));
  const html = show("ASSESSMENTS", {...evaluation, summary});
  assert.match(html, /<td>0.0%<\/td><td>Unavailable<\/td><td>Unavailable<\/td>/);
});

test("wired surfaces use the one-case prereveal receipt and outcome-free metrics", () => {
  const pilot = require("../data/historicalScientificPilot2026.json");
  const receipt = require("../../../data/backtest/receipts/2026-timing-035-prereveal.json");
  assert.equal(pilot.lockSha256, receipt.lock_sha256);
  assert.equal(pilot.eligibleEvents, receipt.eligible_events);
  assert.doesNotMatch(JSON.stringify(pilot), /actual_|always_approve|fda_source_url/);
  for (const surface of ["POOL", "FOCUS", "PAST", "ASSESSMENTS"]) {
    const page = readFileSync(require.resolve(`../app/${surface.toLowerCase()}/page.tsx`), "utf8");
    assert.ok(page.includes(`surface="${surface}" evaluation={historicalPilot}`));
    assert.match(show(surface, pilot), /Verified one-case pilot · 1 eligible FDA action/);
  }
  assert.equal((show("ASSESSMENTS", pilot).match(/0\.0%<\/td><td>Unavailable<\/td>/g) || []).length, 6);
});
