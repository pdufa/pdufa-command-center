const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const revision=JSON.parse(fs.readFileSync(path.resolve(__dirname,
  "../../../docs/medical-review-pilot-20261108/cross-trial-sap-and-lvef-audit-revision10-20261108.json"),"utf8"));
const panel=fs.readFileSync(path.resolve(__dirname,
  "../app/predictions/assessment/PhaseVerificationPanel.tsx"),"utf8");

test("CY 6031 obstructive HCM supplemental plan cannot be counted as CY 6033 final SAP",()=>{
  assert.equal(revision.nct,"NCT06081894");
  assert.equal(revision.expected.protocolCode,"CY 6033");
  assert.equal(revision.expected.indication,"NONOBSTRUCTIVE_HCM");
  const rejected=revision.documents.find(x=>x.id==="PUBLIC-CY6031-SSAP");
  assert.ok(rejected);
  assert.equal(rejected.protocolCode,"CY 6031");
  assert.equal(rejected.indication,"OBSTRUCTIVE_HCM");
  assert.equal(rejected.documentKind,"SUPPLEMENTAL_STATISTICAL_ANALYSIS_PLAN");
  assert.equal(rejected.eligibility,"EXCLUDED_WRONG_TRIAL");
  assert.equal(rejected.containsFinalLockedSap,false);
  const correct=revision.documents.find(x=>x.id==="EU-CTIS-CY6033-AM04");
  assert.ok(correct);
  assert.equal(correct.protocolCode,revision.expected.protocolCode);
  assert.equal(correct.eligibility,"CORRECT_TRIAL_SOURCE");
  assert.equal(correct.documentKind,"PHASE_3_PROTOCOL");
  assert.equal(correct.containsFinalLockedSap,false);
});

test("two published LVEF numbers remain distinct and no grade/event produced",()=>{
  const events=revision.observedSafety;
  const responder=events.find(x=>x.id==="RESPONDER_INT");
  const echo=events.find(x=>x.id==="ECHO_INT");
  assert.equal(responder.reportedAficamtenCount,14);
  assert.equal(responder.reportedAficamtenPercent,2.7);
  assert.equal(echo.reportedAficamtenCount,7);
  assert.equal(echo.reportedAficamtenPercent,2.7);
  assert.equal(revision.arithmetic.count14RatePct,5.4);
  assert.equal(revision.arithmetic.count7RatePct,2.7);
  assert.equal(revision.interpretation,"DIFFERENT_SOURCE_DEFINITIONS_POSSIBLE_NOT_ADJUDICATED");
  assert.equal(revision.resolvedQuestions,0);
  assert.equal(revision.unresolvedQuestions,7);
  assert.equal(revision.phaseVerified,false);
  assert.equal(revision.clinicallyGradedMethodCount,0);
  assert.equal(revision.independentlySignedReviews,0);
  assert.deepEqual(revision.fdaPredictions,{APPROVAL:"ABSTAIN",CRL:"ABSTAIN",REVIEW_DELAY:"ABSTAIN"});
  assert.equal(revision.certainty,"NOT_VALIDATED");
});
test("user-facing scientific review clearly marks a different trial SAP as excluded",()=>{
  assert.match(panel,/Trial-specific SAP identity and LVEF site-versus-core audit/);
  assert.match(panel,/WRONG-TRIAL SAP EXCLUDED FROM PILOT RESEARCH/);
  assert.match(panel,/CY 6031 \/ SEQUOIA-HCM/);
  assert.match(panel,/CY 6033 \/ ACACIA-HCM/);
  assert.match(panel,/cross-trial-sap-and-lvef-audit-revision10-20261108\.md/);
});
