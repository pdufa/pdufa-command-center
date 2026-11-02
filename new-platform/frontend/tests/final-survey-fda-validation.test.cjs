"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const ts=require("typescript");
const fs=require("node:fs");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>
 mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
 }).outputText,file);
const {auditFinalFdaValidation}=require("../lib/final-survey-fda-validation.ts");
const component=fs.readFileSync(require.resolve("../app/Phase3ReadoutSheets.tsx"),"utf8");
function empty(){
 return {status:"NOT_VALIDATED",total_applications:0,eligible_applications:0,
  number_evaluated:0,number_abstained:0,number_with_known_outcomes:0,
  prediction_records:0,temporally_eligible_predictions:0,
  excluded_for_lookahead_or_missing_outcome:0,unresolved_outcomes:0,
  counts:{correct_predictions:0,scored_predictions:0,abstentions:0},
  data_completeness:{applications:0,verified_outcomes:0},
  accuracy_by_decision:{
   PASS:{evaluated:0,correct:0,accuracy:null},
   CRL:{evaluated:0,correct:0,accuracy:null},
   EXTENSION:{evaluated:0,correct:0,accuracy:null}
  },calibration_metrics:null,verified_at:"2026-11-02T20:00:00+00:00",
  limitation:"Predictions and decisions require independent historical source verification."
 };
}
function ready(){
 const x=empty();
 Object.assign(x,{status:"REVIEW_REQUIRED",total_applications:36,
 eligible_applications:33,number_evaluated:30,number_abstained:3,
 number_with_known_outcomes:33,prediction_records:43,temporally_eligible_predictions:33,
 excluded_for_lookahead_or_missing_outcome:10,unresolved_outcomes:3});
 x.counts={correct_predictions:21,scored_predictions:30,abstentions:3};
 x.data_completeness={applications:36,verified_outcomes:33};
 x.accuracy_by_decision={
  PASS:{evaluated:10,correct:8,accuracy:.8},
  CRL:{evaluated:10,correct:7,accuracy:.7},
  EXTENSION:{evaluated:10,correct:6,accuracy:.6}
 };
 return x;
}
test("zero historical source records cannot produce validation accuracy",()=>{
 const x=auditFinalFdaValidation(empty());
 assert.equal(x.status,"NO_ELIGIBLE_PREDICTIONS");
 assert.equal(x.modelValidated,false);
 assert.equal(x.observedAccuracy,null);
 assert.equal(x.scored,0);
 for(const label of ["PASS","CRL","EXTENSION"])
  assert.equal(x.accuracyByDecision[label].accuracy,null);
});
test("independently scoped pre-decision samples permit descriptive accuracy but not certification",()=>{
 const x=auditFinalFdaValidation(ready());
 assert.equal(x.scored,30);
 assert.equal(x.abstained,3);
 assert.equal(x.lookaheadExcluded,10);
 assert.equal(x.observedAccuracy,.7);
 assert.equal(x.accuracyByDecision.EXTENSION.accuracy,.6);
 assert.equal(x.modelValidated,false);
 assert.equal(x.calibration,null);
 assert.equal(x.status,"REVIEW_REQUIRED_NOT_VALIDATED");
});
test("small samples must not display apparent class or overall performance",()=>{
 const raw=ready();
 raw.number_evaluated=2;raw.number_abstained=3;raw.eligible_applications=5;
 raw.temporally_eligible_predictions=5;raw.prediction_records=15;
 raw.excluded_for_lookahead_or_missing_outcome=10;
 raw.counts={correct_predictions:1,scored_predictions:2,abstentions:3};
 raw.accuracy_by_decision={
  PASS:{evaluated:1,correct:1,accuracy:null},
  CRL:{evaluated:1,correct:0,accuracy:null},
  EXTENSION:{evaluated:0,correct:0,accuracy:null}
 };
 const x=auditFinalFdaValidation(raw);
 assert.equal(x.observedAccuracy,null);
 assert.ok(Object.values(x.accuracyByDecision).every(y=>y.accuracy===null));
});
test("inconsistent class totals, prediction timing and fabricated accuracy are rejected",()=>{
 const source=ready();
 for(const mutate of [
  x=>x.prediction_records++,
  x=>x.eligible_applications++,
  x=>x.number_evaluated++,
  x=>x.number_abstained++,
  x=>x.number_with_known_outcomes++,
  x=>x.unresolved_outcomes++,
  x=>x.counts.correct_predictions++,
  x=>x.accuracy_by_decision.PASS.evaluated++,
  x=>x.accuracy_by_decision.PASS.correct++,
  x=>x.accuracy_by_decision.PASS.accuracy=.99,
  x=>x.calibration_metrics={brier:.03},
  x=>x.status="VALIDATED",
  x=>x.data_completeness.verified_outcomes--,
  x=>x.number_evaluated=-1,
  x=>x.verified_at="not-a-date"
 ]){
  const x=JSON.parse(JSON.stringify(source));mutate(x);
  assert.throws(()=>auditFinalFdaValidation(x),/FDA_HISTORICAL_VALIDATION_INCONSISTENT/);
 }
});
test("class performance requires both 30 scored cases and 10 per decision class",()=>{
 const x=ready();x.accuracy_by_decision.PASS={evaluated:9,correct:7,accuracy:null};
 x.accuracy_by_decision.CRL={evaluated:11,correct:8,accuracy:8/11};
 x.counts.correct_predictions=21;
 const r=auditFinalFdaValidation(x);
 assert.equal(r.accuracyByDecision.PASS.accuracy,null);
 assert.equal(r.accuracyByDecision.CRL.accuracy,8/11);
});
test("final SURVEY uses only authenticated validation and never derives an FDA forecast",()=>{
 assert.match(component,/auditFinalFdaValidation\(await response\.json\(\)\)/);
 assert.match(component,/fetch\("\/api\/phase3-trials\/validation"/);
 assert.match(component,/Historical FDA decision validation audit/);
 assert.match(component,/Only predictions locked before their independently documented FDA decisions/);
 assert.match(component,/Not reportable — fewer than 30/);
 assert.match(component,/Historical validation endpoint is unavailable or its counts did not reconcile/);
 assert.match(component,/Model validation:<\/strong> NOT VALIDATED/);
});
