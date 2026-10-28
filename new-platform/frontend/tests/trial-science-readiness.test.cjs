const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");

require.extensions[".ts"] = (mod, filename) => {
  const source = fs.readFileSync(filename, "utf8");
  mod._compile(ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
    },
  }).outputText, filename);
};

const { validScientificReadiness } = require("../lib/trial-science-pilot.ts");

const REGISTRY = "https://clinicaltrials.gov/study/NCT02142738";
const PROTOCOL = "https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf";

function readiness() {
  const spec = [
    ["archive_identity", "SOURCE_SUPPORTED", true],
    ["primary_pfs", "SOURCE_SUPPORTED", true],
    ["interim_os", "SOURCE_SUPPORTED", false],
    ["reported_trae", "SOURCE_SUPPORTED", false],
    ["pre_cutoff_protocol", "BLOCKED", true],
    ["multiplicity_alpha", "REVIEW_REQUIRED", true],
    ["safety_population", "REVIEW_REQUIRED", true],
    ["longterm_crossover", "REVIEW_REQUIRED", true],
    ["patient_flow_missingness", "REVIEW_REQUIRED", true],
    ["patient_reported_outcomes", "REVIEW_REQUIRED", false],
    ["historical_fda_basis", "SOURCE_SUPPORTED", false],
    ["full_regulatory_cmc", "BLOCKED", true],
  ];
  return {
    modelVersion: "scientific-readiness-two-grade-v1",
    nctId: "NCT02142738",
    protocol: {
      url: PROTOCOL, documentDate: "2017-12-20",
      interimDataCutoff: "2016-05-09", amendment: "024-11",
      regionalScope: "Japan-only amendment (cover note)",
      afterInterimDataCutoff: true, notProofOf2016Prespecification: true,
    },
    inputReadiness: {
      grade: "FAIL", status: "NOT_READY_FOR_FULL_ANALYSIS",
      criteriaTotal: 12, sourceSupported: 5, unresolved: 7,
      unresolvedIds: spec.filter(x => x[1] !== "SOURCE_SUPPORTED").map(x => x[0]),
      meaning: "Input completeness only",
    },
    reluctance: {
      grade: "HIGH", status: "CONCLUSIONS_WITHHELD",
      criticalBlockedIds: ["pre_cutoff_protocol", "full_regulatory_cmc"],
      criticalReviewIds: ["multiplicity_alpha", "safety_population",
                          "longterm_crossover", "patient_flow_missingness"],
      meaning: "Caution about conclusions, not chance of clinical failure",
    },
    checks: spec.map(([id, status, critical]) => ({
      id, status, critical,
      title: id, finding: "Source supported or explicit evidence gap",
      next_action: "Review original source",
      sources: [{ url: id === "pre_cutoff_protocol" ? PROTOCOL : REGISTRY,
                  locator: id + " record" }],
    })),
    readOnly: true, scientificScore: null, fdaApprovalProbability: null,
    fullTwentyLevelAnalysisCompleted: false, preliminarySourceReviewAllowed: true,
    independentReanalysisPerformed: false, approvalForecastProduced: false,
    fsFaModified: false, tradingActionsEnabled: false,
    disclaimer: "Evidence completeness only",
  };
}

test("two grades validate only dated source-linked unscored evidence", () => {
  const obj = readiness();
  assert.equal(validScientificReadiness(obj), true);
  assert.equal(obj.inputReadiness.grade, "FAIL");
  assert.equal(obj.reluctance.grade, "HIGH");
  assert.equal(obj.inputReadiness.criteriaTotal, 12);
});

test("tampered grades, sources, protocol dates, blocked checks and scoring fail closed", () => {
  const change = [
    x => { x.nctId = "NCT87654321"; },
    x => { x.inputReadiness.grade = "PASS"; },
    x => { x.reluctance.grade = "LOW"; },
    x => { x.inputReadiness.sourceSupported = 11; },
    x => { x.inputReadiness.unresolvedIds = []; },
    x => { x.protocol.documentDate = "2016-04-01"; },
    x => { x.protocol.afterInterimDataCutoff = false; },
    x => { x.protocol.notProofOf2016Prespecification = false; },
    x => { x.checks.find(c => c.id === "pre_cutoff_protocol").status = "SOURCE_SUPPORTED"; },
    x => { x.checks.find(c => c.id === "pre_cutoff_protocol").sources[0].url = "https://attacker.invalid/any"; },
    x => { x.checks[0].sources[0].locator = ""; },
    x => { x.checks.pop(); },
    x => { x.scientificScore = 98; },
    x => { x.fdaApprovalProbability = .98; },
    x => { x.fsFaModified = true; },
    x => { x.approvalForecastProduced = true; },
  ];
  for (const mutate of change) {
    const bad = readiness();
    mutate(bad);
    assert.equal(validScientificReadiness(bad), false, String(mutate));
  }
});

test("frontend renders input and reluctance grades only with sourced caveats", () => {
  const ui = fs.readFileSync(require("node:path").join(
    __dirname, "../app/TrialSciencePilot.tsx"), "utf8");
  assert.match(ui, /Scientific analysis readiness/);
  assert.match(ui, /Input readiness/);
  assert.match(ui, /Reluctance to conclude/);
  assert.match(ui, /not clinical-trial success or FDA approval probability/);
  assert.match(ui, /criticalBlockedIds/);
  assert.match(ui, /not establish the original analysis plan/);
  assert.match(ui, /validTrialSciencePilot/);
  assert.doesNotMatch(ui, /placeOrder\(|runScan\(/);
});
