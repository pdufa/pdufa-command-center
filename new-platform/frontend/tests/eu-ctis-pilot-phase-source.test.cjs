const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const data=JSON.parse(fs.readFileSync(path.resolve(__dirname,
  "../../../docs/medical-review-pilot-20261108/eu-ctis-phase-protocol-discovery-revision4-20261108.json"),"utf8"));
const component=fs.readFileSync(path.resolve(__dirname,"../app/predictions/assessment/PhaseVerificationPanel.tsx"),"utf8");

test("EU phase crosswalk matches exact pilot NCT and does not imply globally completed trial",()=>{
  assert.equal(data.nct,"NCT06081894");
  assert.equal(data.euTrialNumber,"2023-505797-15-00");
  assert.equal(data.protocolCode,"CY 6033");
  assert.equal(data.phaseScope.europeanUnion.scope,"EU_MEMBER_STATES");
  assert.equal(data.phaseScope.unitedStates.scope,"GLOBAL_STUDY");
  assert.equal(data.phaseScope.europeanUnion.trialStatus,"ENDED");
  assert.equal(data.phaseScope.unitedStates.trialStatus,"ACTIVE_NOT_RECRUITING");
  assert.equal(data.phaseScope.statusComparison,"DIFFERENT_SCOPE_NO_AUTOMATIC_CONTRADICTION");
  assert.equal(data.populationScope.interpretation,"NOT_DIRECTLY_COMPARABLE_SCOPE_AND_STAGE");
});

test("Public protocol listings never count as an examined or graded source",()=>{
  assert.equal(data.sourceState,"PUBLIC_PROTOCOL_LISTED_NOT_RETRIEVED");
  assert.equal(data.publicDocuments.length,3);
  assert.ok(data.publicDocuments.some(doc=>doc.name.endsWith("Protocol_FP")&&doc.version==="AM4"));
  assert.ok(data.publicDocuments.every(doc=>doc.retrieved===false&&doc.contentsExamined===false&&doc.verifiedSha256===null));
  assert.equal(data.gates.originalProtocolBytesVerified,false);
  assert.equal(data.gates.finalSapObtained,false);
  assert.equal(data.gates.independentReviewerIdentified,false);
  assert.equal(data.clinicalPhaseCertified,false);
  assert.equal(data.reviewerSignoff,false);
  assert.equal(data.phaseGradeEvents,0);
  assert.equal(data.methodGradeEvents,0);
  assert.deepEqual(data.fdaPredictions,{APPROVAL:"ABSTAIN",CRL:"ABSTAIN",REVIEW_DELAY:"ABSTAIN"});
  assert.equal(data.certainty,"NOT_VALIDATED");
});

test("UI displays official EU trial source with explicit review caveat and no fake phase event",()=>{
  assert.match(component,/euclinicaltrials\.eu\/ctis-public\/view\/2023-505797-15-00/);
  assert.match(component,/NOT DOWNLOADED · NOT CLINICALLY GRADED/);
  assert.match(component,/does not override the global registry/);
  assert.doesNotMatch(component,/phaseVerified\s*:\s*true/);
});
