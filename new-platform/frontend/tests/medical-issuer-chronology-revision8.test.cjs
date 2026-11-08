const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const facts=JSON.parse(fs.readFileSync(path.resolve(__dirname,"../../../docs/medical-review-pilot-20261108/issuer-design-chronology-revision8-20261108.json"),"utf8"));
const panel=fs.readFileSync(path.resolve(__dirname,"../app/predictions/assessment/PhaseVerificationPanel.tsx"),"utf8");
test("independent source chronology is explicit about issuer's earlier endpoint and later redesign",()=>{
  assert.equal(facts.nct,"NCT06081894");
  const poster=facts.historicalSources.find(x=>x.id==="ISSUER_2023_HFSA");
  assert.equal(poster.plannedEnrollment,420);
  assert.equal(poster.singlePrimaryKccq,true);
  assert.equal(poster.pvo2PartOfSecondary,true);
  assert.equal(poster.sourceVisualReviewed,true);
  const earnings=facts.historicalSources.find(x=>x.id==="ISSUER_Q1_2025_EXECUTIVE_REMARKS");
  assert.equal(earnings.date,"2025-05-06");
  assert.equal(earnings.claimIndependentRegulatorVerified,false);
  assert.equal(earnings.alphaPerPrimary,0.025);
  const registry=facts.historicalSources.find(x=>x.id==="NCT_REGISTRY_V27_METADATA");
  assert.equal(registry.outcomeMeasuresChanged,true);
  assert.equal(registry.studyDesignChanged,true);
  assert.equal(registry.originalVersionBodyCaptured,false);
});
test("official historical API denial does not magically become an authenticated version diff",()=>{
  assert.equal(facts.historicalApiAttempt.overview, "HTTP_403");
  assert.equal(facts.historicalApiAttempt.originalVersionBodiesCaptured,0);
  assert.equal(facts.historicalApiAttempt.sourceUnretrieved,true);
  assert.equal(facts.historicalApiAttempt.individualVersionHttpStatuses,"NOT_VERIFIED_FROM_LOG");
  assert.equal(facts.timingOfRegulatoryApprovalConfirmed,false);
  assert.equal(facts.regulatoryFeedbackIndependentlyVerified,false);
  assert.equal(facts.finalSapObtained,false);
  assert.equal(facts.clinicalIntegrityAdjudicated,false);
  assert.equal(facts.methodGrades,0);
  assert.equal(facts.phaseVerified,false);
  assert.deepEqual(facts.approvalPredictions,{APPROVAL:"ABSTAIN",CRL:"ABSTAIN",REVIEW_DELAY:"ABSTAIN"});
  assert.equal(facts.certainty,"NOT_VALIDATED");
});
test("review panel retains data/source versus medical grade distinction",()=>{
  assert.match(panel,/Endpoint redesign chronology · original 2023/);
  assert.match(panel,/ORIGINAL VERSION DIFF PENDING · FINAL SAP MISSING · 0 SCIENTIFIC GRADES/);
  assert.match(panel,/issuer-design-chronology-revision8-20261108\.md/);
  assert.match(panel,/Automated access to full original registry versions was unsuccessful/);
});
