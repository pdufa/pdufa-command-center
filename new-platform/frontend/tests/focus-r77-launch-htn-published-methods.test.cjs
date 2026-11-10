"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const x=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  jsx:ts.JsxEmit.ReactJS,esModuleInterop:true
 }});mod._compile(x.outputText,file);
};
const original=require("../data/focus-r77-launch-htn-published-multiplicity-crosswalk.json");
const {FOCUS_R77_LAUNCH_HTN_PUBLISHED_METHODS,buildR77LaunchHtnPublishedMethods}=
 require("../lib/focus-r77-launch-htn-published-methods.ts");

test("Read-only H1-H7 source diagram has one primary, six secondaries and eight exact arrows",()=>{
 const r=FOCUS_R77_LAUNCH_HTN_PUBLISHED_METHODS;
 assert.ok(r);
 assert.equal(r.methodsMapped,7);
 assert.equal(r.graphEdgesMapped,8);
 assert.deepEqual(r.publishedSourceHypotheses.map(x=>x.id),["H1","H2","H3","H4","H5","H6","H7"]);
 assert.equal(r.publishedSourceHypotheses[0].category,"PRIMARY");
 assert.equal(r.publishedSourceHypotheses[6].studyComparison,"WITHIN_PARTICIPANT_NONRANDOMIZED_ESCALATED_SUBSET");
 assert.deepEqual(r.graphEdges.map(e=>e.from+"-"+e.to),[
  "H1-H4","H1-H5","H4-H3","H5-H3","H3-H2","H2-H7","H2-H6","H7-H6"]);
 assert.deepEqual(r.graphEdges.filter(x=>x.sourceDiagramTransferLabel==="HALF").map(x=>x.from+"-"+x.to),
   ["H1-H4","H1-H5","H2-H7","H2-H6"]);
 assert.equal(r.alphaTransferDiagram.fullMultiplicityRecalculationPerformed,false);
 assert.equal(r.reviewSafety.familywiseAlphaRecalculationPerformed,false);
});

test("Original published missingness and safety are distinct, no clinical accuracy or efficacy signoff",()=>{
 const r=FOCUS_R77_LAUNCH_HTN_PUBLISHED_METHODS;
 assert.equal(r.missingness.denominatorSafetyTreated,1078);
 assert.equal(r.missingness.totalTreatmentDiscontinuationOrDeathIntercurrentEvents,24);
 assert.equal(r.missingness.adverseEventRelatedMissingWeek6,10);
 assert.equal(r.missingness.otherMissingMARWeek6,56);
 assert.equal(r.missingness.imputedDatasets,1000);
 assert.deepEqual(r.safetyReview.safetyArmDenominators,[270,538,270]);
 assert.deepEqual(r.safetyReview.serumSodiumBelow130,[11,14,4]);
 assert.deepEqual(r.safetyReview.serumPotassiumObserved5Point6To6Point0,[29,38,3]);
 assert.deepEqual(r.safetyReview.serumPotassiumConfirmed5Point6To6Point0,[24,31,2]);
 assert.equal(r.sensitivityPublished.sensitivity2DifferenceMmHg,-8.6);
 assert.equal(r.reviewSafety.originalPreUnblindingSAPVersionVerified,false);
 assert.equal(r.reviewSafety.signedClinicalReviewerCount,0);
 assert.equal(r.reviewSafety.independentlyValidatedFDAApplicationForecasts,0);
 assert.equal(r.reviewSafety.finalScientificGrade,null);
 assert.equal(r.reviewSafety.regulatoryForecast,"ABSTAIN");
 assert.equal(r.reviewSafety.trainingOrProductionWrites,false);
});

test("Fraudulent arrows, imputation, exposure populations, alpha and FDA grades fail closed",()=>{
 const changes=[
  x=>x.publishedSourceHypotheses.pop(),
  x=>x.publishedSourceHypotheses[6].studyComparison="RANDOMIZED_50MG_VERSUS_PLACEBO",
  x=>x.publishedSourceHypotheses[3].endpoint="some other endpoint",
  x=>x.graphEdges.reverse(),
  x=>x.graphEdges[0].sourceDiagramTransferLabel="UNSPECIFIED",
  x=>x.graphEdges[3].to="H7",
  x=>x.alphaTransferDiagram.fullMultiplicityRecalculationPerformed=true,
  x=>x.primaryPublishedEffect.differenceMmHg=-11.1,
  x=>x.sensitivityPublished.sensitivity2DifferenceMmHg=-8.8,
  x=>x.missingness.imputedDatasets=500,
  x=>x.missingness.adverseEventRelatedMissingWeek6=56,
  x=>x.missingness.imputationCodeAndSeedIndependentlyExecuted=true,
  x=>x.safetyReview.safetyArmDenominators=[808,270,0],
  x=>x.safetyReview.serumSodiumBelow130=[25,0,4],
  x=>x.safetyReview.independentlyReviewed=true,
  x=>x.reviewSafety.originalPreUnblindingSAPVersionVerified=true,
  x=>x.reviewSafety.familywiseAlphaRecalculationPerformed=true,
  x=>x.reviewSafety.independentStatisticalRecalculationPerformed=true,
  x=>x.reviewSafety.signedClinicalReviewerCount=1,
  x=>x.reviewSafety.finalScientificGrade=20,
  x=>x.reviewSafety.regulatoryForecast="APPROVAL",
  x=>x.reviewSafety.independentlyValidatedFDAApplicationForecasts=1,
  x=>x.reviewSafety.trainingOrProductionWrites=true
 ];
 for(let i=0;i<changes.length;i++){
  const modified=structuredClone(original);
  changes[i](modified);
  assert.equal(buildR77LaunchHtnPublishedMethods(modified),null,"tamper case "+i);
 }
});

test("The read-only R77 source-only panel appears for MLYS; no scoring API side effects",()=>{
 const host=fs.readFileSync(path.join(root,"app/predictions/evidence-gaps/ScientificOriginalsIntakeR71.tsx"),"utf8");
 const panel=fs.readFileSync(path.join(root,"app/predictions/evidence-gaps/LaunchHtnMethodsR77.tsx"),"utf8");
 assert.match(host,/nct==="NCT06153693"&&<LaunchHtnMethodsR77\/>/);
 assert.match(panel,/H1–H7 endpoints/);
 assert.match(panel,/WITHIN-PARTICIPANT ANALYSIS/);
 assert.match(panel,/UNASSESSED/);
 assert.match(panel,/ABSTAIN/);
 assert.match(panel,/0\/23/);
 assert.match(panel,/no familywise multiplicity calculation has been independently reproduced/);
 assert.doesNotMatch(panel,/fetch\(|POST\s*\/api|setGrade\(|submitClinicalScore/);
});
