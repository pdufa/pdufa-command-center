"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>
 mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX
 }}).outputText,file);
const {SURVEY_SCORING_PROTOCOLS,surveyScoringAssessments,surveyScoringGateLabel}=
 require("../lib/final-survey-scoring-protocol.ts");
const {BENEFIT_GROUPS}=require("../lib/benefit-assessments.ts");
const source=fs.readFileSync(require.resolve("../app/Phase3ReadoutSheets.tsx"),"utf8");
const fact=(confidence="HIGH",status="VERIFIED")=>({
 status,confidence,value:"Research input recorded",
 sourceUrl:"https://example.org/source",sourceDate:"2026-10-31",method:"Study-specified source review"
});
const record=(facts={})=>({
 nctId:"NCT12345678",ticker:"TEST",drug:"Sample drug",indication:"Sample indication",
 facts,advantages:[]
});
const allFacts=Object.fromEntries(BENEFIT_GROUPS.flatMap(s=>s.fields.map(f=>[f.id,fact()])));
test("canonical 20-survey 38-question inventory maps to 20 distinct scoring protocols",()=>{
 assert.equal(SURVEY_SCORING_PROTOCOLS.length,20);
 assert.equal(BENEFIT_GROUPS.length,20);
 assert.equal(BENEFIT_GROUPS.flatMap(s=>s.fields).length,38);
 assert.deepEqual(SURVEY_SCORING_PROTOCOLS.map(s=>s.number),
  Array.from({length:20},(_,i)=>i+1));
 for(const p of SURVEY_SCORING_PROTOCOLS){
  assert.ok(p.evidenceBasis.length>=60);
  assert.ok(p.comparisonRequired.length>=55);
  assert.ok(p.outcomeCriterion.length>=52);
  assert.equal(typeof p.requiresPublicReadout,"boolean");
 }
});
test("unmatched records never become missing-data failure percentages or numeric scores",()=>{
 const assessments=surveyScoringAssessments(null,false);
 assert.equal(assessments.length,20);
 for(const item of assessments){
  assert.equal(item.gate,item.protocol.requiresPublicReadout?
    "PUBLIC_RESULTS_UNCONFIRMED":"NO_EXACT_RECORD");
  assert.equal(item.numericalScore,null);
  assert.equal(item.verified,null);
  assert.equal(item.modeled,null);
  assert.equal(item.missing,null);
  assert.deepEqual(item.sourceLinks,[]);
 }
});
test("unmatched pre-release trial explicitly blocks all five outcome-dependent scientific surveys before searching for a study record",()=>{
 const pre=surveyScoringAssessments(null,false);
 for(const number of [3,4,5,8,9]){
  assert.equal(pre[number-1].gate,"PUBLIC_RESULTS_UNCONFIRMED");
  assert.equal(pre[number-1].numericalScore,null);
  assert.equal(pre[number-1].verified,null);
 }
 assert.equal(pre[0].gate,"NO_EXACT_RECORD");
 assert.match(surveyScoringGateLabel(pre[2].gate),/Public results not documented as checked/);
});
test("a historical pre-readout source check blocks outcomes dependent on released clinical results",()=>{
 const pre=surveyScoringAssessments(record(allFacts),false);
 const post=surveyScoringAssessments(record(allFacts),true);
 for(const rank of [3,4,5,8,9]){
  assert.equal(pre[rank-1].gate,"PUBLIC_RESULTS_UNCONFIRMED",rank);
  assert.equal(post[rank-1].gate,"METHOD_VALIDATION_REQUIRED",rank);
 }
 assert.equal(pre[0].gate,"METHOD_VALIDATION_REQUIRED");
 assert.equal(pre[5].gate,"METHOD_VALIDATION_REQUIRED");
});
test("modeled and missing fields are not accepted as verified scientific evidence",()=>{
 const field=BENEFIT_GROUPS[2].fields;
 const partial=record({[field[0].id]:fact("HIGH","MODELED"),[field[1].id]:fact()});
 const result=surveyScoringAssessments(partial,true)[2];
 assert.equal(result.gate,"MISSING_VERIFIED_INPUTS");
 assert.equal(result.verified,1);
 assert.equal(result.modeled,1);
 assert.equal(result.missing,field.length-2);
 assert.equal(result.missingInputs.length,field.length-1);
 assert.equal(result.numericalScore,null);
});
test("low confidence source records gate the method even if every question is verified",()=>{
 const first=BENEFIT_GROUPS[0].fields[0].id;
 const testRecord=record({...allFacts,[first]:fact("LOW")});
 const result=surveyScoringAssessments(testRecord,true);
 assert.equal(result[0].gate,"LOW_CONFIDENCE_INPUTS");
 assert.equal(result[0].lowConfidence,1);
 assert.equal(result[0].sourceLinks.length,result[0].required);
 assert.equal(result[0].numericalScore,null);
 assert.equal(result[1].gate,"METHOD_VALIDATION_REQUIRED");
});
test("all inputs complete is not automatically a validated efficacy or FDA grade",()=>{
 const result=surveyScoringAssessments(record(allFacts),true);
 assert.equal(result.filter(x=>x.gate==="METHOD_VALIDATION_REQUIRED").length,20);
 assert.ok(result.every(x=>x.numericalScore===null));
 assert.ok(result.every(x=>x.verified===x.required));
 assert.ok(result.every(x=>x.missing===0));
 assert.match(surveyScoringGateLabel(result[0].gate),/calibration/i);
});
test("final SURVEY exposes method directly to the right and one selected row at a time",()=>{
 assert.match(source,/surveyScoringAssessments\(record,row\.evidence\?\.kind==="POST_PUBLIC_READOUT"\)/);
 assert.match(source,/setSelectedScoringSurvey\(survey\.number\)/);
 assert.match(source,/aria-pressed=\{selectedScoringSurvey===survey\.number\}/);
 assert.match(source,/finalSurveyScoringLayout/);
 assert.match(source,/Selected survey scoring method/);
 assert.match(source,/Numerical scientific grade:/);
 assert.match(source,/Not calibrated · no numerical score assigned/);
 assert.match(source,/selectedScoring\.protocol\.outcomeCriterion/);
 assert.match(source,/selectedScoring\.sourceLinks\.map/);
 assert.match(source,/Even complete source records do not establish comparative efficacy/);
});
