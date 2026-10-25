"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

require.extensions[".ts"] = (mod, file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, file
);
const { buildScientificEvidenceRequirementsCsv } =
  require("../lib/scientific-evidence-requirements-csv.ts");

const REQUIREMENT_IDS = [
  "archive_integrity", "indication", "design", "eligibility", "interventions",
  "enrollment", "timeline", "registered_primary", "primary_analysis",
  "safety_denominators", "participant_flow", "baseline", "protocol_sap",
  "published_results", "independent_replication", "official_regulatory",
];

function audit() {
  return {
    nctId: "NCT02142738",
    requirements: REQUIREMENT_IDS.map((id, i) => ({
      id, label: "Check " + id, available: i < 10,
      evidenceLevel: i === 0 ? "archive_verified"
        : i >= 12 ? "independent_review_not_loaded"
        : i < 10 ? "registry_field_present" : "missing_in_archive",
      sourcePath: i >= 12 ? null : "protocolSection." + id,
      nextAction: "Independently inspect source for " + id,
      independentlyVerified: false,
    })),
    missingRequirementIds: REQUIREMENT_IDS.slice(10),
    analysisReadiness: {
      coveragePercent: 63, requirementsCovered: 10, requirementsTotal: 16,
      readyForFullScientificConclusion: false,
      verdict: "NOT_READY", passFail: "FAIL_INCOMPLETE_INPUTS",
    },
    scientificReluctance: {
      grade: "F", level: "CRITICAL", reluctanceToConclude: "MAXIMUM",
      verdict: "WITHHOLD_SCIENTIFIC_CONCLUSION",
    },
    externalEvidenceVerified: false, scientificScore: null, fdaApprovalProbability: null,
  };
}

test("exact-NCT CSV lists 16 checks and distinguishes missing source inputs from blocked external reviews", () => {
  const data = audit();
  const original = JSON.stringify(data);
  const csv = buildScientificEvidenceRequirementsCsv(data);
  const lines = csv.trimEnd().split("\r\n");
  assert.equal(lines.length, 17);
  assert.match(lines[0], /"nct_id","requirement_number","requirement_id"/);
  assert.match(lines[1], /^"NCT02142738","1","archive_integrity"/);
  assert.match(lines[16], /^"NCT02142738","16","official_regulatory"/);
  assert.equal((csv.match(/"ARCHIVE_INPUT_PRESENT_NOT_SCIENTIFICALLY_VERIFIED"/g) || []).length, 10);
  assert.equal((csv.match(/"MISSING_IN_ARCHIVE"/g) || []).length, 2);
  assert.equal((csv.match(/"INDEPENDENT_REVIEW_NOT_COMPLETE"/g) || []).length, 4);
  assert.equal((csv.match(/"FALSE","NOT_ASSIGNED","NOT_ASSIGNED"/g) || []).length, 16);
  assert.equal(JSON.stringify(data), original);
});

test("actions and source fields are CSV-escaped to prevent formulas and row injection", () => {
  const data = audit();
  data.requirements[0].nextAction = '\r\n  =HYPERLINK("https://bad.example","click")';
  data.requirements[1].sourcePath = ' =1+2';
  const csv = buildScientificEvidenceRequirementsCsv(data);
  assert.equal(csv.trimEnd().split("\r\n").length, 17);
  assert.match(csv, /"' +=HYPERLINK\(""https:\/\/bad\.example"",""click""\)"/);
  assert.match(csv, /"' +=1\+2"/);
  assert.doesNotMatch(csv, /\r\n\s*=HYPERLINK/);
});

test("forged evidence verification, grade readiness, identity and incomplete counts block export", () => {
  const mutations = [
    x => { x.nctId = "NCT00000000=W"; },
    x => { x.requirements = x.requirements.slice(1); },
    x => { x.requirements[0].id = "changed"; },
    x => { x.requirements[1].independentlyVerified = true; },
    x => { x.requirements[12].available = true; },
    x => { x.requirements[12].evidenceLevel = "archive_verified"; },
    x => { x.requirements[0].available = false; },
    x => { x.requirements[1].sourcePath = null; },
    x => { x.requirements[1].nextAction = ""; },
    x => { x.missingRequirementIds = []; },
    x => { x.analysisReadiness.coveragePercent = 99; },
    x => { x.analysisReadiness.requirementsCovered = 12; },
    x => { x.analysisReadiness.readyForFullScientificConclusion = true; },
    x => { x.scientificReluctance.grade = "A"; },
    x => { x.externalEvidenceVerified = true; },
    x => { x.scientificScore = 87; },
    x => { x.fdaApprovalProbability = 0.83; },
  ];
  for (const mutate of mutations) {
    const data = audit();
    mutate(data);
    assert.throws(() => buildScientificEvidenceRequirementsCsv(data),
      /Scientific input checklist export blocked/, String(mutate));
  }
});

test("trial UI only exports currently validated exact-NCT evidence inputs, not grades or scans", () => {
  const code = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(code, /Download 16-requirement evidence checklist \(CSV\)/);
  assert.match(code, /buildScientificEvidenceRequirementsCsv\(result\.readinessGrades\)/);
  assert.match(code, /result\.readinessGrades\.nctId \+ "_scientific_16_evidence_requirements\.csv"/);
  assert.match(code, /Independent scientific review is not certified by this download/);
  assert.doesNotMatch(code, /runScan\(|placeTrade\(|saveGrade\(/);
});
