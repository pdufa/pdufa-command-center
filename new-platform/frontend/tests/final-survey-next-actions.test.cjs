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
const {finalSurveyNextActions}=require("../lib/final-survey-next-actions.ts");
const {BENEFIT_GROUPS}=require("../lib/benefit-assessments.ts");
const source=fs.readFileSync(require.resolve("../app/Phase3ReadoutSheets.tsx"),"utf8");
const sections=[["A","Medical Impact",1,5],["B","Competitive Strength",6,8],
 ["C","Market Opportunity",9,14],["D","Revenue Value",15,18],
 ["E","Investment Potential",19,20]];
const gates=["Issuer/readout source","Clinical effect","Safety","Financing"].map(label=>({label,passed:true}));
const questions=BENEFIT_GROUPS.flatMap(s=>s.fields.map(f=>({
 id:f.id,survey:s.number,label:f.label,status:"UNRECORDED"
})));
const groups=sections.map(([key,name])=>({key,name,verified:0}));
const run=(extra={})=>finalSurveyNextActions({
 researchStatus:"ready",exactRecord:true,gates,groups,questions,...extra
});
test("the actionable final SURVEY uses the unmodified 20 surveys and 38 canonical fields",()=>{
 assert.equal(BENEFIT_GROUPS.length,20);
 assert.equal(questions.length,38);
 assert.equal(new Set(questions.map(q=>q.id)).size,38);
 assert.equal(new Set(questions.map(q=>q.survey)).size,20);
});
test("unavailable data produces a source blocker, not fabricated missing clinical findings",()=>{
 const r=run({researchStatus:"unavailable"});
 assert.equal(r.actions.length,1);
 assert.equal(r.actions[0].category,"SOURCE");
 assert.equal(r.unverifiedQuestions,null);
 assert.doesNotMatch(r.actions[0].detail,/failed trial|clinical failure/i);
});
test("a non-unique NCT/ticker/drug/indication match is an identity blocker only",()=>{
 const r=run({exactRecord:false});
 assert.equal(r.actions.length,1);
 assert.equal(r.actions[0].category,"IDENTITY");
 assert.match(r.actions[0].detail,/NCT, ticker, drug\/therapy and indication/);
 assert.equal(r.unverifiedQuestions,null);
});
test("priorities are stage checks, empty groups, then unverified questions",()=>{
 const r=run({gates:gates.map((g,i)=>i<2?{...g,passed:false}:g)});
 assert.deepEqual(r.actions.slice(0,2).map(x=>x.category),["STAGE","STAGE"]);
 assert.deepEqual(r.actions.slice(2,7).map(x=>x.category),
   ["GROUP","GROUP","GROUP","GROUP","GROUP"]);
 assert.equal(r.actions[7].category,"QUESTION");
 assert.equal(r.unverifiedQuestions,38);
 assert.equal(r.actions.length,2+5+38);
});
test("modeled-only inputs require primary-source evidence, not zero or automatic validation",()=>{
 const qs=questions.map((q,i)=>i===0?{...q,status:"MODELED"}:q);
 const r=run({questions:qs});
 assert.equal(r.unverifiedQuestions,38);
 assert.equal(r.actions.find(x=>x.key==="question:"+questions[0].id).category,"QUESTION");
 assert.match(r.actions.find(x=>x.key==="question:"+questions[0].id).detail,/Modeled only/);
 assert.match(r.actions.find(x=>x.key==="question:"+questions[0].id).detail,/cannot count as verified/);
});
test("a full 38/38 verified study with satisfied gates requires zero remaining research tasks",()=>{
 const r=run({
  groups:groups.map(g=>({...g,verified:1})),
  questions:questions.map(q=>({...q,status:"VERIFIED"}))
 });
 assert.equal(r.actions.length,0);
 assert.equal(r.unverifiedQuestions,0);
});
test("a malformed or incomplete question inventory fails closed",()=>{
 for(const qs of [questions.slice(0,37),[...questions.slice(0,37),questions[0]],
  questions.map(q=>({...q,survey:1})),questions.map((q,i)=>i===0?{...q,status:"UNKNOWN"}:q)]){
  const r=run({questions:qs});
  assert.equal(r.actions.length,1);
  assert.equal(r.actions[0].key,"inventory-invalid");
  assert.equal(r.unverifiedQuestions,null);
 }
});
test("final SURVEY dialog exposes the task list and exact-trial source links without grading clinical outcome",()=>{
 assert.match(source,/finalSurveyNextActions\(\{researchStatus,exactRecord:!!record/);
 assert.match(source,/Final SURVEY prioritized research actions/);
 assert.match(source,/Next steps to complete SURVEY/);
 assert.match(source,/Question verification remaining:/);
 assert.match(source,/ClinicalTrials\.gov/);
 assert.match(source,/Dated issuer evidence/);
 assert.match(source,/Show \{nextActions\.actions\.length-6\} additional research tasks/);
 assert.match(source,/Independent scientific scoring validation is still required/);
});
