const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

require.extensions[".ts"] = (mod, file) => {
  const source = fs.readFileSync(file, "utf8");
  mod._compile(ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  }).outputText, file);
};
const { validSafetyChronology } = require("../lib/trial-science-safety-chronology.ts");

const NEJM = "https://www.nejm.org/doi/full/10.1056/nejmoa1606774";
const PUBMED = "https://pubmed.ncbi.nlm.nih.gov/27718847/";
const JCO = "https://pubmed.ncbi.nlm.nih.gov/30620668/";

function fixture() {
  const categories = [
    ["treatment_related_any_grade", 113, 135, 73.4, 90],
    ["treatment_related_grade_3_to_5", 41, 80, 26.6, 53.3],
    ["serious_treatment_related_any_grade", 33, 31, 21.4, 20.7],
    ["treatment_related_discontinuation_any_grade", 11, 16, 7.1, 10.7],
    ["treatment_related_death", 1, 3, 0.6, 2],
  ];
  return {
    nctId: "NCT02142738", status: "published_safety_source_reconciliation_only",
    original2016: {
      analysisId: "keynote024_initial_2016",
      publicationDate: "2016-10-08", dataCutoffDate: "2016-05-09",
      sourceUrl: NEJM, sourcePubMed: PUBMED,
      randomized: { pembrolizumab: 154, chemotherapy: 151 },
      asTreated: { pembrolizumab: 154, chemotherapy: 150 },
      unexposedChemotherapyRandomized: 1,
      reportedTreatRelatedSafety: categories.map(([classification, p, c, percentP, percentC]) => ({
        classification,
        pembrolizumab: { affected: p, atRisk: 154, reportedPercent: percentP },
        chemotherapy: { affected: c, atRisk: 150, reportedPercent: percentC },
        sourceUrl: NEJM, sourceLocator: "Table 3: Adverse Events in the As-Treated Population",
        treatmentRelated: true, sourceReportedNotIndependentlyVerified: true,
      })),
      roundingArithmeticChecked: true, patientLevelVerified: false,
      clinicalSafetyAppraisalComplete: false,
    },
    immuneMediated2016: {
      sourceUrl: NEJM, sourceLocator: "Original manuscript Table 3 and Adverse Events narrative",
      causalityDefinition: "regardless_of_investigator_treatment_attribution",
      anyGradePercent: { pembrolizumab: 29.2, chemotherapy: 4.7 },
      grade3to4Percent: { pembrolizumab: 9.7, chemotherapy: 0.7 },
      noGrade5ImmuneMediatedEventsReported: true,
      notEquivalentToTreatmentRelatedAE: true,
    },
    updated2019: {
      sourceId: "30620668", sourceUrl: JCO,
      publicationDate: "2019-01-08", analysisDataCutoff: "2017-07-10",
      randomized: { pembrolizumab: 154, chemotherapy: 151 },
      reportedGrade3to5TreatmentRelatedPercent: { pembrolizumab: 31.2, chemotherapy: 53.3 },
      reportedOnStudyCrossoverPatients: 82,
      intentionToTreatOS: { hazardRatio: 0.63, ci95: [0.47, 0.86] },
      twoStageCrossoverAdjustedOS: { hazardRatio: 0.49, ci95: [0.34, 0.69] },
      crossoverAdjustedInterpretation: "model_based_sensitivity_not_randomized_estimate",
      publishedAEAffectedCountsExtracted: false,
      mustNotOverwriteOriginal2016: true,
    },
    registryReconciliation: {
      archivedGroupsObserved: 5, sourceUrl: "https://clinicaltrials.gov/study/NCT02142738",
      countsPooledAcrossTreatmentCourses: false,
      registryAEGroupMatchesJournalTRAE: false,
      registryUsesDistinctCategoriesAndPossibleCrossover: true,
      publishedSafetyDenominatorsIdentified: true,
      crossSystemAEReconciliationCompleted: false,
      missingOriginalSapStillBlocking: true,
      nextAction: "Verify pre-2016 signed SAP and each source/event population.",
    },
    scientificScore: null, fdaApprovalProbability: null,
    inputReadinessGradeChanged: false, reluctanceGradeChanged: false,
    readOnly: true, tradingActionsEnabled: false,
  };
}

test("original as-treated safety denominator 150 does not equal randomized chemo 151", () => {
  const record = fixture();
  assert.equal(validSafetyChronology(record), true);
  assert.equal(record.original2016.randomized.chemotherapy, 151);
  assert.equal(record.original2016.asTreated.chemotherapy, 150);
  const row = record.original2016.reportedTreatRelatedSafety[1];
  assert.equal(row.pembrolizumab.affected, 41);
  assert.equal(row.chemotherapy.affected, 80);
  assert.equal(row.chemotherapy.atRisk, 150);
  assert.equal(record.updated2019.reportedGrade3to5TreatmentRelatedPercent.pembrolizumab, 31.2);
});

test("reject numeric, source, timeline, interpretation or forecasting tampering", () => {
  const mutations = [
    x => { x.nctId = "NCT87654321"; },
    x => { x.original2016.asTreated.chemotherapy = 151; },
    x => { x.original2016.randomized.chemotherapy = 150; },
    x => { x.original2016.reportedTreatRelatedSafety[1].chemotherapy.affected = 81; },
    x => { x.original2016.reportedTreatRelatedSafety[1].chemotherapy.reportedPercent = 53.0; },
    x => { x.original2016.reportedTreatRelatedSafety[0].sourceUrl = "https://untrusted.invalid"; },
    x => { x.original2016.reportedTreatRelatedSafety.reverse(); },
    x => { x.immuneMediated2016.notEquivalentToTreatmentRelatedAE = false; },
    x => { x.immuneMediated2016.anyGradePercent.pembrolizumab = 26.6; },
    x => { x.updated2019.analysisDataCutoff = "2016-05-09"; },
    x => { x.updated2019.sourceId = "27718847"; },
    x => { x.updated2019.reportedOnStudyCrossoverPatients = 100; },
    x => { x.updated2019.reportedGrade3to5TreatmentRelatedPercent.pembrolizumab = 26.6; },
    x => { x.updated2019.mustNotOverwriteOriginal2016 = false; },
    x => { x.updated2019.twoStageCrossoverAdjustedOS.hazardRatio = 0.63; },
    x => { x.registryReconciliation.countsPooledAcrossTreatmentCourses = true; },
    x => { x.registryReconciliation.crossSystemAEReconciliationCompleted = true; },
    x => { x.registryReconciliation.archivedGroupsObserved = 25; },
    x => { x.scientificScore = 99; },
    x => { x.fdaApprovalProbability = .98; },
    x => { x.inputReadinessGradeChanged = true; },
  ];
  for (const mutate of mutations) {
    const data = fixture();
    mutate(data);
    assert.equal(validSafetyChronology(data), false, String(mutate));
  }
});

test("trial panel keeps original and updated safety snapshots separate", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/TrialSciencePilot.tsx"), "utf8");
  const validator = fs.readFileSync(path.join(__dirname, "../lib/trial-science-pilot.ts"), "utf8");
  assert.match(ui, /Published safety — separate analysis dates and denominators/);
  assert.match(ui, /2016 original publication/);
  assert.match(ui, /2019 published follow-up/);
  assert.match(ui, /as-treated safety analysis included 154 \/ 150/);
  assert.match(ui, /not a new randomized comparison/);
  assert.match(ui, /Input Readiness remains FAIL; Reluctance remains HIGH/);
  assert.match(validator, /validSafetyChronology/);
  assert.match(validator, /archivedGroupsObserved !==/);
  assert.doesNotMatch(ui, /runTrade\(|placeOrder\(/);
});
