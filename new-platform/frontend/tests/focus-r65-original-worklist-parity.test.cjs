"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
  const source=ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
      jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
  mod._compile(source.outputText,file);
};
const {FOCUS_R65_REVIEW_GATES,R65_DOMAIN_QUESTIONS,R65_REQUIRED_REVIEW_FIELDS}=
 require("../lib/focus-r65-independent-review-gates.ts");
const originalPath=process.env.R65_ORIGINAL_OUTPUT;
test("Read-only 29-NCT development checklist is exactly the original source-locked unsigned R65 docket",
 {skip:!originalPath},()=>{
 const doc=JSON.parse(fs.readFileSync(originalPath,"utf8"));
 const ui=FOCUS_R65_REVIEW_GATES;
 assert.ok(ui);
 assert.equal(doc.schema,"MAIN_R65_ORIGINAL_SOURCE_HUMAN_ADJUDICATION_INTAKE_ONLY");
 assert.equal(doc.originalR63Sha256,"b39028e972c45949147d405c447af45ef8ceab7089d8e89247cacd1d2cef6a18");
 assert.equal(ui.originalSourceSha256,process.env.R65_ORIGINAL_SHA);
 assert.equal(doc.sourceResearchRunId,42713443428);
 assert.equal(doc.sourceResearchArtifactId,13717655352);
 assert.equal(ui.uniqueTrials,doc.exactNctCount);
 assert.equal(ui.provisionalApplications,doc.provisionalApplicationCount);
 assert.equal(ui.requiredMethodReviews,doc.scientificReviewerTasks);
 assert.equal(ui.originalMachinePageLeads,doc.originalMachinePdfPageLeads);
 assert.equal(ui.records.length,doc.trialIndependentReviewPackets.length);
 assert.deepEqual([...R65_REQUIRED_REVIEW_FIELDS],doc.reviewerRecordRequiredFields);
 const originals=new Map(doc.trialIndependentReviewPackets.map(t=>[t.nct,t]));
 for(const trial of ui.records){
  const old=originals.get(trial.nct);
  assert.ok(old,trial.nct);
  assert.deepEqual(trial.applicationCycles,old.applicationCycleIds);
  assert.equal(trial.reviewedPhaseVerified,old.phaseVerifiedByIndependentReviewer);
  assert.equal(trial.qualifiedSignedGrades,old.completedClinicalMethodScores);
  assert.equal(trial.sourceLeads,old.trialReviewSlots.reduce((n,d)=>n+d.exactOriginalPageLeads.length,0));
  for(let i=0;i<8;i++){
   const domain=trial.methodTasks[i],o=old.trialReviewSlots[i];
   assert.equal(domain.id,o.intakeId);
   assert.equal(domain.domain,o.domain);
   assert.equal(domain.sourcePageLeads,o.exactOriginalPageLeads.length);
   assert.deepEqual(domain.requiredQuestions,o.requiredIndependentReviewQuestions);
   assert.deepEqual(domain.evidenceFields,o.requiredEvidenceAndSignoffFields);
   assert.deepEqual(domain.requiredQuestions,[...R65_DOMAIN_QUESTIONS[i]]);
   assert.equal(domain.grade,o.grade);
   assert.equal(o.reviewerId,null);
   assert.equal(o.reviewerAttestation,null);
   assert.equal(o.secondIndependentVerifier,null);
   assert.equal(domain.clinicalDisposition,o.finalDisposition);
   assert.equal(domain.failureOrSuccess,o.studySuccessOrFailure);
  }
 }
 assert.equal(doc.qualfiedReviewerAttestationsRecorded,undefined);
 assert.equal(doc.qualifiedReviewerAttestationsRecorded,0);
 assert.equal(doc.independentlyCompletedMethodGrades,0);
 assert.equal(doc.independentlyValidatedFDAApplicationPredictions,0);
 assert.equal(doc.measuredOutOfTimeForecastAccuracy,null);
 assert.equal(doc.officialFDAOutcome,"ABSTAIN");
 assert.equal(doc.reviewWritesEnabled,false);
 assert.equal(doc.productionOrLedgerWrites,false);
 assert.equal(doc.historicalOutcomeDataAccessed,false);
});
