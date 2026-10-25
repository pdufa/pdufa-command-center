const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
require.extensions[".ts"] = (module, filename) => {
  module._compile(ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
    },
  }).outputText, filename);
};

const {validPublishedInterimDesign} = require("../lib/trial-science-interim-design.ts");
const JOURNAL = "https://www.nejm.org/doi/abs/10.1056/NEJMoa1606774";
function sample() {
  return {
    nctId: "NCT02142738",
    status: "published_design_not_authenticated_original_sap",
    sourceDateContext: {
      originalInterimDataCutoff: "2016-05-09", journalSourceUrl: JOURNAL,
      journalLocator: "Methods/Statistical Analysis; Discussion",
      fdaStaffSourceUrl: "https://pmc.ncbi.nlm.nih.gov/articles/PMC5679831/",
      fdaStaffLocator: "KEYNOTE-024 summary efficacy table, footnote b",
      originalSupplementSourceUrl: "https://www.nejm.org/doi/full/10.1056/nejmoa1606774",
      originalSupplementFilename: "nejmoa1606774_protocol.pdf",
      originalSupplementRead: false, contemporaneousSapAuthenticated: false,
    },
    reportedDesign: {
      overallOneSidedAlphaPercent: 2.5,
      firstInterim: {
        plannedMinimumRandomized: 191, plannedMinimumFollowupMonths: 6,
        testingEndpoint: "objective_response_rate",
        reportedAllocatedOneSidedAlphaPercent: 0.5,
        sourceUrl: JOURNAL, sourceLocator: "Discussion: first interim analysis",
        prespecificationIndependentlyConfirmed: false,
      },
      secondInterim: {
        plannedApproximatePfsEvents: 175, testingEndpoint: "progression_free_survival",
        reportedAllocatedOneSidedAlphaPercent: 2.0, sourceUrl: JOURNAL,
        sourceLocator: "Discussion: second interim analysis",
        prespecificationIndependentlyConfirmed: false,
      },
      osGroupSequential: {
        plannedApproximateDeaths: [110, 170], sourceUrl: JOURNAL,
        sourceLocator: "Discussion: group sequential overall survival analyses",
        prespecificationIndependentlyConfirmed: false,
      },
      descriptionPublishedAfterCutoff: true, signedOriginalPlanAuthenticated: false,
    },
    observedInterim: {
      reportedPfsEvents: 189, reportedDeaths: 108,
      pfsHR: 0.50, pfsCi95: [0.37,0.68],
      reportedPfsPValue: "<0.001",
      osHR: 0.60, osCi95: [0.41,0.89],
      reportedOsPValue: 0.005, fdaStaffReportedOsAllocatedAlpha: 0.0118,
      comparisonStatus: "source_reported_not_recalculated",
      fdaStaffArticleIsNotFullAgencyClinicalReview: true,
    },
    reconciliation: {
      historicalResultsSourceChecked: true,
      independentOriginalSAPReviewComplete: false,
      alphaSpendingRecomputedFromSignedSAP: false,
      patientLevelReanalysisComplete: false,
      scientificConclusionAuthorized: false,
      inputReadinessGradeChanged: false, reluctanceGradeChanged: false,
      missingCriticalSources: [
        "Original effective 2016-or-earlier protocol amendments",
        "Original signed and dated statistical analysis plan",
        "Complete interim decision/alpha-spending and censoring audit",
      ],
      nextAction: "Obtain original supplement; authenticate version/effective date.",
    },
    scientificScore: null, fdaApprovalProbability: null,
    readOnly: true, tradingActionsEnabled: false, fsFaModified: false,
  };
}
test("show planned first/second interim without calling it signed SAP", () => {
  const s=sample();
  assert.equal(validPublishedInterimDesign(s),true);
  assert.equal(s.reportedDesign.overallOneSidedAlphaPercent,2.5);
  assert.equal(s.reportedDesign.secondInterim.reportedAllocatedOneSidedAlphaPercent,2);
  assert.equal(s.observedInterim.reportedPfsEvents,189);
  assert.equal(s.observedInterim.reportedDeaths,108);
  assert.equal(s.reconciliation.independentOriginalSAPReviewComplete,false);
  assert.equal(s.scientificScore,null);
});
test("reject forged signed verification, alpha, cutoff, source or PDUFA probability", () => {
  const tamper=[
    x=>{x.nctId="NCT12345678";},
    x=>{x.sourceDateContext.originalInterimDataCutoff="2017-07-10";},
    x=>{x.sourceDateContext.contemporaneousSapAuthenticated=true;},
    x=>{x.sourceDateContext.originalSupplementRead=true;},
    x=>{x.sourceDateContext.fdaStaffSourceUrl="https://attacker.invalid";},
    x=>{x.reportedDesign.overallOneSidedAlphaPercent=5;},
    x=>{x.reportedDesign.firstInterim.reportedAllocatedOneSidedAlphaPercent=2;},
    x=>{x.reportedDesign.secondInterim.prespecificationIndependentlyConfirmed=true;},
    x=>{x.reportedDesign.osGroupSequential.plannedApproximateDeaths=[110,190];},
    x=>{x.observedInterim.reportedPfsEvents=500;},
    x=>{x.observedInterim.reportedOsPValue=0.0005;},
    x=>{x.reconciliation.independentOriginalSAPReviewComplete=true;},
    x=>{x.reconciliation.alphaSpendingRecomputedFromSignedSAP=true;},
    x=>{x.reconciliation.inputReadinessGradeChanged=true;},
    x=>{x.scientificScore=90;},
    x=>{x.fdaApprovalProbability=.92;},
    x=>{x.tradingActionsEnabled=true;},
  ];
  for(const mutate of tamper){const x=sample();mutate(x);assert.equal(validPublishedInterimDesign(x),false,String(mutate));}
});
test("UI keeps published design distinct from original signed SAP",()=>{
  const jsx=fs.readFileSync(path.join(__dirname,"../app/TrialSciencePilot.tsx"),"utf8");
  const guard=fs.readFileSync(path.join(__dirname,"../lib/trial-science-pilot.ts"),"utf8");
  assert.match(jsx,/2016 interim statistical design/);
  assert.match(jsx,/planned testing rules/);
  assert.match(jsx,/signed, prospectively effective protocol/);
  assert.match(jsx,/One-sided/);
  assert.match(jsx,/No scientific score or FDA approval forecast/);
  assert.match(guard,/validPublishedInterimDesign/);
  assert.doesNotMatch(jsx,/placeOrder\(|runTrade\(/);
});
