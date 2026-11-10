const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const v7=JSON.parse(fs.readFileSync(path.resolve(__dirname,"../../../docs/medical-review-pilot-20261108/version-and-safety-crosscheck-revision7-20261108.json"),"utf8"));
const panel=fs.readFileSync(path.resolve(__dirname,"../app/predictions/assessment/PhaseVerificationPanel.tsx"),"utf8");
test("official amendment history states exact dated fields only and avoids unverified version diff",()=>{
  assert.equal(v7.nct,"NCT06081894");
  assert.equal(v7.officialHistory.totalVersions,31);
  assert.equal(v7.officialHistory.officialFullHistoricalValuesRetrieved,false);
  const version=v7.officialHistory.versions.find(x=>x.v===27);
  assert.equal(version.date,"2025-05-15");
  assert.ok(version.categories.includes("Outcome Measures"));
  assert.ok(version.categories.includes("Study Design"));
  assert.equal(v7.secondaryIndexedChange.previousPrimaryEndpointCount,1);
  assert.equal(v7.secondaryIndexedChange.nextPrimaryEndpointCount,2);
  assert.equal(v7.secondaryIndexedChange.officialBeforeAfterRecordVerified,false);
  assert.equal(v7.unresolvedIssues.find(x=>x.id==="REV7-VERSION").mayInferProtocolManipulation,false);
});
test("safety numerator disagreements remain unresolved, not scores",()=>{
  const issues=v7.unresolvedIssues;
  assert.equal(issues.length,6);
  assert.equal(issues.find(x=>x.id==="REV7-COUNT").needsPopulationReconciliation,true);
  assert.equal(issues.find(x=>x.id==="REV7-HF-SAE").needsEventListing,true);
  assert.equal(v7.sourceProtocol.lockedSapObtained,false);
  assert.equal(v7.phaseVerificationAuthorized,false);
  assert.equal(v7.independentlyGradedMethods,0);
  assert.equal(v7.independentClinicalSignoff,false);
  assert.deepEqual(v7.fdaPredictions,{APPROVAL:"ABSTAIN",CRL:"ABSTAIN",REVIEW_DELAY:"ABSTAIN"});
  assert.equal(v7.certainty,"NOT_VALIDATED");
});
test("preview links version review to original registry and labels evidence not graded",()=>{
  assert.match(panel,/Trial amendment history and unresolved safety counts/);
  assert.match(panel,/clinicaltrials\.gov\/study\/NCT06081894\?tab=history/);
  assert.match(panel,/NO VERIFIED SAP · NO REVIEWER SIGNOFF · NO SCORES OR FDA PREDICTIONS/);
  assert.match(panel,/version-and-safety-crosscheck-revision7-20261108\.md/);
});
