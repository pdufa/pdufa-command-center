const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

require.extensions[".ts"] = (mod, filename) => mod._compile(
  ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
    },
  }).outputText,
  filename,
);

const { validSourceEvidenceAudit } = require("../lib/trial-science-evidence-audit.ts");

const refs = [
  ["2015-05-20", "contemporaneous_trial_design",
    "https://ascopubs.org/doi/10.1200/jco.2015.33.15_suppl.tps8103",
    "public_description_before_cutoff"],
  ["2016-05-09", "primary_analysis_cutoff",
    "https://pubmed.ncbi.nlm.nih.gov/27718847/",
    "cutoff_reported_retrospectively"],
  ["2016-10-08", "original_results_published",
    "https://pubmed.ncbi.nlm.nih.gov/27718847/",
    "published_results"],
  ["2016-10-08", "supplementary_protocol_listed",
    "https://doi.org/10.1056/NEJMoa1606774",
    "linked_document_not_content_reviewed"],
  ["2017-12-20", "later_protocol_date",
    "https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf",
    "document_date_reported"],
  ["2020-06-01", "long_term_followup_cutoff",
    "https://pubmed.ncbi.nlm.nih.gov/33872070/",
    "cutoff_reported_retrospectively"],
  ["2021-04-19", "long_term_analysis_published",
    "https://pubmed.ncbi.nlm.nih.gov/33872070/",
    "published_results"],
];

function group(i = 0) {
  const locator = `resultsSection.adverseEventsModule.eventGroups[${i}]`;
  const count = (category, affected, risk) => ({
    numAffected: 4, numAtRisk: 10,
    population: "registry_event_group_as_reported",
    sourceFields: [locator + "." + affected, locator + "." + risk],
  });
  return {
    groupId: "EG00" + i,
    title: i ? "Synthetic treatment switch-over" : "Synthetic first course",
    sourceLocator: locator,
    counts: {
      seriousEvents: count("seriousEvents", "seriousNumAffected", "seriousNumAtRisk"),
      otherEvents: count("otherEvents", "otherNumAffected", "otherNumAtRisk"),
      deaths: count("deaths", "deathsNumAffected", "deathsNumAtRisk"),
    },
    independentlyVerified: false,
  };
}

function fixture() {
  return {
    nctId: "NCT02142738",
    assessmentStatus: "historical_evidence_crosswalk_only",
    timeline: refs.map(([date, id, sourceUrl, evidenceStatus]) => ({
      date, id, sourceUrl, evidenceStatus, title: id,
      sourceLocator: "Public source section", finding: "Source-only historical report",
      limitation: "No full signed original SAP review",
      proofOfOriginalSap: false,
    })),
    earlyDesignEvidence: {
      status: "public_trial_design_reported_pre_cutoff",
      sourceUrl: refs[0][2],
      publicationDate: "2015-05-20",
      primaryEndpoint: "progression_free_survival_by_central_RECIST1_1",
      secondaryEndpoints: ["objective_response_rate", "overall_survival", "safety"],
      preinterimDocumentVerified: false,
      signedSapVerified: false,
      originalMultiplicityVerified: false,
    },
    registrySafety: {
      sourceUrl: "https://clinicaltrials.gov/study/NCT02142738",
      sourceType: "checksum_verified_archive_registry_posting",
      status: "groups_reported",
      groups: [group(0), group(1)],
      groupCount: 2,
      treatmentSwitchGroupsMayExist: true,
      randomizedArmComparisonValidated: false,
      publishedTreatmentRelatedAeRatesReconciled: false,
      missingGroupsDoNotImplyZeroEvents: true,
      note: "No pooling permitted",
    },
    readOnly: true,
    scientificScore: null,
    fdaApprovalProbability: null,
    inputReadinessGradeChanged: false,
    reluctanceGradeChanged: false,
    independentProtocolSapReviewComplete: false,
    tradingActionsEnabled: false,
  };
}

test("timeline validates 2015 public study design but refuses to call it a signed SAP", () => {
  const data = fixture();
  assert.equal(validSourceEvidenceAudit(data), true);
  assert.equal(data.timeline[0].date, "2015-05-20");
  assert.equal(data.earlyDesignEvidence.signedSapVerified, false);
  assert.equal(data.timeline[3].evidenceStatus, "linked_document_not_content_reviewed");
  assert.equal(data.timeline[4].date, "2017-12-20");
  assert.equal(data.inputReadinessGradeChanged, false);
  assert.equal(data.reluctanceGradeChanged, false);
});

test("no registry event groups does not falsely mean zero events", () => {
  const data = fixture();
  data.registrySafety.groups = [];
  data.registrySafety.groupCount = 0;
  data.registrySafety.status = "no_groups_documented_in_snapshot";
  assert.equal(validSourceEvidenceAudit(data), true);
  assert.equal(data.registrySafety.missingGroupsDoNotImplyZeroEvents, true);
});

test("reject swapped sources, false signed SAP, invented score, malformed group counts", () => {
  const tamper = [
    x => { x.nctId = "NCT00000001"; },
    x => { x.timeline[0].sourceUrl = "https://evil.invalid/"; },
    x => { x.timeline[3].evidenceStatus = "document_content_verified"; },
    x => { x.timeline[4].date = "2016-01-01"; },
    x => { x.timeline[2].proofOfOriginalSap = true; },
    x => { x.earlyDesignEvidence.signedSapVerified = true; },
    x => { x.registrySafety.groupCount = 0; },
    x => { x.registrySafety.groups[0].counts.seriousEvents.numAffected = 50; },
    x => { x.registrySafety.groups[0].counts.seriousEvents.numAtRisk = -1; },
    x => { x.registrySafety.groups[0].counts.seriousEvents.numAffected = true; },
    x => { x.registrySafety.groups[1].groupId = "EG000"; },
    x => { x.registrySafety.groups[0].sourceLocator = "resultsSection.bad[0]"; },
    x => { x.registrySafety.randomizedArmComparisonValidated = true; },
    x => { x.registrySafety.publishedTreatmentRelatedAeRatesReconciled = true; },
    x => { x.inputReadinessGradeChanged = true; },
    x => { x.reluctanceGradeChanged = true; },
    x => { x.scientificScore = 95; },
    x => { x.fdaApprovalProbability = .95; },
    x => { x.tradingActionsEnabled = true; },
  ];
  for (const modify of tamper) {
    const data = fixture();
    modify(data);
    assert.equal(validSourceEvidenceAudit(data), false, String(modify));
  }
});

test("dashboard panel displays dated chronology and grouped AE denominators only", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/TrialSciencePilot.tsx"), "utf8");
  assert.match(ui, /Trial evidence timeline/);
  assert.match(ui, /View dated evidence and source references/);
  assert.match(ui, /Registry adverse-event denominators/);
  assert.match(ui, /numAffected/);
  assert.match(ui, /numAtRisk/);
  assert.match(ui, /must not be pooled/);
  assert.match(ui, /Input readiness and reluctance grades have not changed/);
  assert.doesNotMatch(ui, /runTrade\(|placeOrder\(/);
});
