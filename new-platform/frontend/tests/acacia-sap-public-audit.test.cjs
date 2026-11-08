const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");

const report=JSON.parse(fs.readFileSync(path.resolve(__dirname,
  "../../../docs/medical-review-pilot-20261108/locked-sap-public-audit-revision6-20261108.json"),"utf8"));
const ui=fs.readFileSync(path.resolve(__dirname,
  "../app/predictions/assessment/PhaseVerificationPanel.tsx"),"utf8");

test("official registry SAP discovery is reported narrowly, not as missing from the world",()=>{
  assert.equal(report.study.nct,"NCT06081894");
  assert.equal(report.audit.currentNctIdentityMatched,true);
  assert.equal(report.audit.publicResultsSectionPresent,false);
  assert.equal(report.audit.publicLargeDocumentCount,0);
  assert.equal(report.audit.publicSapRecordListed,false);
  assert.equal(report.audit.definitiveNoSapAnywhereClaim,false);
  assert.equal(report.audit.finalSignedSapCaptured,false);
  assert.equal(report.audit.historicalIntEndpoint,"UNAVAILABLE_HTTP_ERROR_UNDOCUMENTED_ENDPOINT");
  assert.equal(report.timelineLead.originalVersionVerified,false);
  assert.equal(report.timelineLead.allegesProtocolManipulation,false);
});

test("published significant endpoints and hierarchy limitations cannot become grades",()=>{
  const kccq=report.efficacy.find(x=>x.endpoint==="KCCQ_CSS_36W");
  const vo2=report.efficacy.find(x=>x.endpoint==="PEAK_VO2_36W");
  assert.equal(kccq.pValue,0.021);
  assert.equal(vo2.pValue,0.003);
  for(const e of [kccq,vo2]){
    assert.equal(e.primary,true);
    assert.equal(e.reportingAlpha,0.025);
    assert.equal(e.reportedPrimaryCriterionMet,true);
    assert.ok(e.pValue<=e.reportingAlpha);
    assert.equal(e.designAssumptionIsFdaClinicalThreshold,false);
  }
  for(const e of report.efficacy.filter(x=>!x.primary)){
    assert.equal(e.notConfirmatory,true);
    assert.equal(e.reportedPrimaryCriterionMet,null);
  }
  assert.equal(report.pending.clinicalReviewerSignoff,false);
  assert.equal(report.pending.phaseVerified,false);
  assert.equal(report.pending.independentlyGradedMethods,0);
  assert.equal(report.pending.sapHashAndLockVerified,false);
  assert.deepEqual(report.fdaPredictions,{APPROVAL:"ABSTAIN",CRL:"ABSTAIN",REVIEW_DELAY:"ABSTAIN"});
  assert.equal(report.certainty,"NOT_VALIDATED");
});
test("science matrix clearly labels public audit as not regulatory validation",()=>{
  assert.match(ui,/Final SAP audit · public registry checked/);
  assert.match(ui,/FINAL SAP NOT OBTAINED · INDEPENDENT PHASE REVIEW 0 · METHOD GRADES 0 · FDA ABSTAIN/);
  assert.match(ui,/locked-sap-public-audit-revision6-20261108\.md/);
});
