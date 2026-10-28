const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

require.extensions[".ts"] = (mod, filename) =>
  mod._compile(ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
    },
  }).outputText, filename);
const { validEuProtocolCrosscheck } = require("../lib/trial-science-eu-crosscheck.ts");

const EU = "https://www.clinicaltrialsregister.eu/ctr-search/trial/2014-000323-25/NL";
const NCI = "https://www.cancer.gov/research/participate/clinical-trials-search/v?id=NCT02142738";
const ASCO = "https://ascopubs.org/doi/10.1200/jco.2015.33.15_suppl.tps8103";
function fixture() {
  const checks = [
    ["primary_pfs", "E.5.1", "PFS per RECIST 1.1 by blinded central review",
      "progression_free_survival", null],
    ["planned_pfs_events", "E.5.1.1", "Approximately 175 PFS events",
      "progression_free_survival", 175],
    ["planned_os_first", "E.5.2.1", "Approximately 110 deaths",
      "overall_survival", 110],
    ["planned_os_second", "E.5.2.1", "Approximately 170 deaths",
      "overall_survival", 170],
    ["secondary_os_orr", "E.5.2", "OS and centrally reviewed ORR are secondary",
      "secondary_endpoints", null],
    ["monitoring_and_design", "E.8.1 and E.8.7",
      "Open-label randomized Phase 3 with data monitoring committee", "trial_design", null],
  ];
  return {
    nctId: "NCT02142738",
    schemaVersion: "historical-eu-registered-plan-crosscheck-v1",
    status: "cross_source_description_agrees_without_sap_verification",
    registry: {
      eudractNumber: "2014-000323-25",
      sponsorProtocolCode: "MK-3475-024",
      recordCountry: "Netherlands",
      sourceUrl: EU,
      firstRecordEnteredDate: "2014-06-19",
      competentAuthorityDecisionDate: "2014-06-19",
      recordFirstEnteredBeforeInterim: true,
      individualEndpointFieldVersionDated: false,
      original2014FieldContentAuthenticated: false,
      signed2016SAPAvailable: false,
      authoredBySeparateOrganization: false,
      explanation: "Sponsor supplied regulatory posting; not independently dated each field.",
    },
    identityBridge: {
      nciSourceUrl: NCI,
      nciTrialId: "NCT02142738",
      nciSecondaryId: "2014-000323-25",
      protocolCode: "MK-3475-024",
      separateClinicalTrial: false,
      identityCrosscheckOnly: true,
    },
    comparisons: checks.map(([key, euSection, euReportedFinding,
                              mappedPublishedConcept, reportedPlannedCount]) => ({
      key, euSection, euReportedFinding, mappedPublishedConcept, reportedPlannedCount,
      crossSourceAgreement: true,
      euSourceUrl: EU,
      revisionHistoryVerified: false,
      independentSignedSAPConfirmation: false,
    })),
    eventTiming: {
      euPfsEventsTargetApprox: 175, reportedPfsEventsObserved: 189,
      euOsFirstDeathsTargetApprox: 110, reportedOsInterimDeathsObserved: 108,
      euOsLaterDeathsTargetApprox: 170,
      euAllowsPfsTimingDelayIfOsUnder110: true,
      euSourceSection: "E.5.1.1",
      actualDataMonitoringCommitteeTimingReconciled: false,
      eventDifferenceNotAutomaticProtocolDeviation: true,
      nextAction: "Reconcile original signed SAP and DMC timing, do not call an approximate count a violation.",
    },
    earlierPublicDescription: {
      sourceUrl: ASCO, publicationDate: "2015-05-20",
      supportsPrimaryEndpointAndCentralReview: true, originalSapAuthenticated: false,
    },
    researchConclusions: {
      primaryPfsDesignCorroboratedAcrossSources: true,
      approximateEventTargetsAgreeAcrossSources: true,
      alphaSpendingInEuRegistryVerified: false,
      originalEffectiveProtocolAmendmentsVerified: false,
      preInterimSignedSapVerified: false,
      independentReplicationCompleted: false,
      safetyBenefitRiskAdjudicated: false,
      inputReadinessGradeChanged: false,
      reluctanceGradeChanged: false,
      canBeUsedToAssignClinicalSuccessGrade: false,
    },
    scientificScore: null,
    fdaApprovalProbability: null,
    readOnly: true,
    tradingActionsEnabled: false,
    fsFaModified: false,
  };
}
test("2014 EU register dates are NOT original field/SAP authenticated dates", () => {
  const x = fixture();
  assert.equal(validEuProtocolCrosscheck(x), true);
  assert.equal(x.registry.firstRecordEnteredDate, "2014-06-19");
  assert.equal(x.registry.individualEndpointFieldVersionDated, false);
  assert.equal(x.researchConclusions.preInterimSignedSapVerified, false);
  assert.equal(x.eventTiming.euPfsEventsTargetApprox, 175);
  assert.equal(x.eventTiming.reportedPfsEventsObserved, 189);
  assert.equal(x.eventTiming.reportedOsInterimDeathsObserved, 108);
  assert.equal(x.scientificScore, null);
});
test("no fake independent replication, signed SAP, score, sponsor source or event count", () => {
  const attacks = [
    x => { x.nctId = "NCT00000000"; },
    x => { x.registry.sourceUrl = "https://untrusted.example"; },
    x => { x.registry.firstRecordEnteredDate = "2016-01-01"; },
    x => { x.registry.individualEndpointFieldVersionDated = true; },
    x => { x.registry.original2014FieldContentAuthenticated = true; },
    x => { x.registry.signed2016SAPAvailable = true; },
    x => { x.registry.authoredBySeparateOrganization = true; },
    x => { x.identityBridge.nciTrialId = "NCT99999999"; },
    x => { x.identityBridge.separateClinicalTrial = true; },
    x => { x.comparisons[1].reportedPlannedCount = 189; },
    x => { x.comparisons[2].euSourceUrl = "https://untrusted.example"; },
    x => { x.comparisons[3].revisionHistoryVerified = true; },
    x => { x.comparisons[4].independentSignedSAPConfirmation = true; },
    x => { x.eventTiming.euPfsEventsTargetApprox = 189; },
    x => { x.eventTiming.reportedOsInterimDeathsObserved = 110; },
    x => { x.eventTiming.actualDataMonitoringCommitteeTimingReconciled = true; },
    x => { x.eventTiming.eventDifferenceNotAutomaticProtocolDeviation = false; },
    x => { x.earlierPublicDescription.originalSapAuthenticated = true; },
    x => { x.researchConclusions.alphaSpendingInEuRegistryVerified = true; },
    x => { x.researchConclusions.preInterimSignedSapVerified = true; },
    x => { x.researchConclusions.independentReplicationCompleted = true; },
    x => { x.researchConclusions.inputReadinessGradeChanged = true; },
    x => { x.researchConclusions.reluctanceGradeChanged = true; },
    x => { x.researchConclusions.canBeUsedToAssignClinicalSuccessGrade = true; },
    x => { x.scientificScore = 94; },
    x => { x.fdaApprovalProbability = .91; },
    x => { x.tradingActionsEnabled = true; },
  ];
  for (const attack of attacks) {
    const x = fixture();
    attack(x);
    assert.equal(validEuProtocolCrosscheck(x), false, String(attack));
  }
});
test("pilot display is date-qualified and never upgrades grades", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/TrialSciencePilot.tsx"), "utf8");
  const gate = fs.readFileSync(path.join(__dirname, "../lib/trial-science-pilot.ts"), "utf8");
  assert.match(ui, /Early European registry crosscheck/);
  assert.match(ui, /first entered/);
  assert.match(ui, /does not establish the version\/effective date/);
  assert.match(ui, /Input Readiness remains FAIL; Reluctance remains HIGH/);
  assert.match(ui, /Differences from approximate targets are not automatically protocol deviations/);
  assert.match(gate, /validEuProtocolCrosscheck/);
  assert.match(gate, /input\.scientificReadiness\.inputReadiness\.grade !== "FAIL"/);
  assert.doesNotMatch(ui, /placeOrder\(|runTrade\(/);
});
