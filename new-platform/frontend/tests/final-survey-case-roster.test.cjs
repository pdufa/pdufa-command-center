"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}
).outputText,file);
const {auditHistoricalCaseRoster,caseReasonLabel}=require("../lib/final-survey-case-roster.ts");
const ui=fs.readFileSync(require.resolve("../app/Phase3ReadoutSheets.tsx"),"utf8");
function base(){
 return {prediction_records:0,number_with_known_outcomes:1,eligible_applications:0,
  number_evaluated:0,number_abstained:0,
  case_review:{total:1,returned:1,limit:50,
   reason_counts:{VERIFIED_OUTCOME_WITHOUT_LOCKED_PREDECISION_PREDICTION:1},
   records:[{
    prediction_id:null,nct_id:null,application_id:"NDA123456:sample",
    predicted_decision:null,actual_decision:"APPROVED",decision_date:"2026-03-05",
    prediction_created_at:null,evidence_cutoff:null,disposition:"NO_PREDICTION",
    reason:"VERIFIED_OUTCOME_WITHOUT_LOCKED_PREDECISION_PREDICTION",
    fda_source_url:"https://www.fda.gov/drugs/official-decision",correctness:null
   }]}
 };
}
test("older backend with no case roster is unknown rather than zero",()=>{
 const raw={...base()};delete raw.case_review;
 assert.equal(auditHistoricalCaseRoster(raw),null);
});
test("verified FDA application without prospective forecast remains candidate, not measured accuracy",()=>{
 const data=auditHistoricalCaseRoster(base());
 assert.equal(data.total,1);
 assert.equal(data.records.length,1);
 assert.equal(data.records[0].predictionId,null);
 assert.equal(data.records[0].disposition,"NO_PREDICTION");
 assert.equal(data.records[0].fdaSourceUrl,"https://www.fda.gov/drugs/official-decision");
 assert.match(caseReasonLabel(data.records[0].reason),/no eligible predecision forecast/);
});
test("post-decision fake predictions are excluded and never treated as successful",()=>{
 const raw=base();
 raw.prediction_records=1;
 raw.case_review.total=2;
 raw.case_review.returned=2;
 raw.case_review.reason_counts.PREDICTION_NOT_BEFORE_FDA_ACTION=1;
 raw.case_review.records.unshift({
   prediction_id:"after-fda",nct_id:"NCT12345678",
   application_id:"NDA123456:sample",predicted_decision:"PASS",
   actual_decision:"APPROVED",decision_date:"2026-03-05",
   prediction_created_at:"2026-04-01T10:00:00Z",
   evidence_cutoff:"2026-03-31T10:00:00Z",
   disposition:"EXCLUDED",reason:"PREDICTION_NOT_BEFORE_FDA_ACTION",
   fda_source_url:"https://www.fda.gov/drugs/official-decision",correctness:null
 });
 const data=auditHistoricalCaseRoster(raw);
 assert.equal(data.total,2);
 assert.equal(data.reasonCounts.PREDICTION_NOT_BEFORE_FDA_ACTION,1);
 assert.equal(data.records[0].correctness,null);
 assert.equal(data.records[0].disposition,"EXCLUDED");
});
test("a locked pre-action prediction can be evaluated without claiming model calibration",()=>{
 const raw=base();
 raw.prediction_records=1;raw.eligible_applications=1;raw.number_evaluated=1;
 raw.case_review.total=1;raw.case_review.returned=1;
 raw.case_review.reason_counts={LOCKED_PREDICTION_BEFORE_FDA_DECISION:1};
 raw.case_review.records=[{
  prediction_id:"locked",nct_id:"NCT12345678",application_id:"NDA123456:sample",
  predicted_decision:"CRL",actual_decision:"APPROVED",decision_date:"2026-03-05",
  prediction_created_at:"2026-02-01T10:00:00Z",
  evidence_cutoff:"2026-01-31T20:00:00Z",
  disposition:"EVALUATED",reason:"LOCKED_PREDICTION_BEFORE_FDA_DECISION",
  fda_source_url:"https://www.fda.gov/drugs/official-decision",correctness:false
 }];
 const data=auditHistoricalCaseRoster(raw);
 assert.equal(data.records[0].correctness,false);
 assert.equal(data.reasonCounts.LOCKED_PREDICTION_BEFORE_FDA_DECISION,1);
});
test("contradictory counts, duplicate prediction IDs or unsafe source URLs fail closed",()=>{
 const baseValue=base();
 for(const mutate of [
  x=>x.case_review.total++,
  x=>x.case_review.reason_counts.VERIFIED_OUTCOME_WITHOUT_LOCKED_PREDECISION_PREDICTION++,
  x=>x.number_with_known_outcomes=0,
  x=>x.case_review.records[0].disposition="EVALUATED",
  x=>x.case_review.records[0].fda_source_url="https://fda.gov.evil.test/fake",
  x=>x.case_review.records[0].fda_source_url="https://user@fda.gov/drugs/official-decision",
  x=>x.case_review.records[0].decision_date="2026-02-30",
  x=>x.case_review.records[0].predicted_decision="PASS"
 ]){
  const x=JSON.parse(JSON.stringify(baseValue));mutate(x);
  assert.throws(()=>auditHistoricalCaseRoster(x),/HISTORICAL_FDA_CASE_ROSTER_INVALID/);
 }
});
test("combined SURVEY shows verified case audit and source links but no invented prediction",()=>{
 assert.match(ui,/auditHistoricalCaseRoster\(raw\)/);
 assert.match(ui,/Historical FDA application case readiness roster/);
 assert.match(ui,/FDA historical case review/);
 assert.match(ui,/Verified FDA evidence/);
 assert.match(ui,/Case-level diagnostics are not available/);
 assert.match(ui,/a research candidate/);
 assert.match(ui,/caseReasonLabel\(item\.reason\)/);
});

test("case pagination returns separate audited pages and keeps global reason totals unchanged",()=>{
 const first=base();
 first.number_with_known_outcomes=51;
 first.case_review.total=51;
 first.case_review.returned=50;
 first.case_review.reason_counts.VERIFIED_OUTCOME_WITHOUT_LOCKED_PREDECISION_PREDICTION=51;
 first.case_review.records=Array.from({length:50},(_,i)=>({
  ...first.case_review.records[0],application_id:"NDA123456:sample-"+i
 }));
 first.case_review.page=1;first.case_review.pages=2;first.case_review.has_more=true;
 const a=auditHistoricalCaseRoster(first,1);
 assert.equal(a.page,1);
 assert.equal(a.pages,2);
 assert.equal(a.hasMore,true);
 assert.equal(a.paginationAvailable,true);
 assert.equal(a.reasonCounts.VERIFIED_OUTCOME_WITHOUT_LOCKED_PREDECISION_PREDICTION,51);
 const second=JSON.parse(JSON.stringify(first));
 second.case_review.page=2;second.case_review.returned=1;
 second.case_review.has_more=false;
 second.case_review.records=[{...first.case_review.records[0],application_id:"NDA123456:sample-50"}];
 const b=auditHistoricalCaseRoster(second,2);
 assert.equal(b.page,2);assert.equal(b.returned,1);assert.equal(b.hasMore,false);
 assert.equal(b.total,a.total);
 assert.throws(()=>auditHistoricalCaseRoster(second,1),/HISTORICAL_FDA_CASE_ROSTER_INVALID/);
 const repeated=JSON.parse(JSON.stringify(second));
 repeated.case_review.page=1;
 assert.throws(()=>auditHistoricalCaseRoster(repeated,1),/HISTORICAL_FDA_CASE_ROSTER_INVALID/);
 const impossible=JSON.parse(JSON.stringify(second));
 impossible.case_review.pages=3;
 assert.throws(()=>auditHistoricalCaseRoster(impossible,2),/HISTORICAL_FDA_CASE_ROSTER_INVALID/);
});
test("legacy first 50 still display without lying about page navigation",()=>{
 const x=base();
 x.number_with_known_outcomes=51;
 x.case_review.total=51;x.case_review.returned=50;
 x.case_review.reason_counts.VERIFIED_OUTCOME_WITHOUT_LOCKED_PREDECISION_PREDICTION=51;
 x.case_review.records=Array.from({length:50},(_,i)=>({
  ...x.case_review.records[0],application_id:"NDA123456:legacy-"+i
 }));
 const legacy=auditHistoricalCaseRoster(x,1);
 assert.equal(legacy.total,51);
 assert.equal(legacy.paginationAvailable,false);
 assert.equal(legacy.pages,2);
 assert.equal(legacy.hasMore,false);
 assert.throws(()=>auditHistoricalCaseRoster(x,2),/HISTORICAL_FDA_CASE_ROSTER_INVALID/);
});
test("SURVEY case page next/previous uses validated, authenticated route and no direct backend requests",()=>{
 const relay=fs.readFileSync(require.resolve("../lib/phase3-trials.ts"),"utf8");
 assert.match(ui,/setCasePage\(page=>Math\.max\(1,page-1\)\)/);
 assert.match(ui,/setCasePage\(page=>Math\.min\(/);
 assert.match(ui,/Historical FDA case review pages/);
 assert.match(ui,/auditHistoricalCaseRoster\(raw,casePage\)/);
 assert.match(relay,/export function validationCaseQuery/);
 assert.match(relay,/\^\[1-9\]/);
 assert.match(relay,/Number\(page\)>1000000/);
 assert.match(relay,/validationCaseQuery\(req\.nextUrl\.searchParams\)/);
});
