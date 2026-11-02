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
const {finalSurveyReadiness}=require("../lib/final-survey-readiness.ts");
const {BENEFIT_GROUPS}=require("../lib/benefit-assessments.ts");
const source=fs.readFileSync(require.resolve("../app/Phase3ReadoutSheets.tsx"),"utf8");
const sections=[["A",1,5],["B",6,8],["C",9,14],["D",15,18],["E",19,20]];
const sizes=sections.map(([key,start,end])=>({
 key,name:"Section "+key,verified:0,modeled:0,
 missing:BENEFIT_GROUPS.filter(s=>s.number>=start&&s.number<=end).flatMap(s=>s.fields).length,
 total:BENEFIT_GROUPS.filter(s=>s.number>=start&&s.number<=end).flatMap(s=>s.fields).length
}));
const gates=["Source classification","Clinical evidence","Safety or competitor","Financial risk"]
 .map(label=>({label,passed:true}));
function assigned(counts,modeled={}){
 return sizes.map((group,i)=>{
  const verified=counts[i]||0,model=modeled[i]||0;
  return {...group,verified,modeled:model,missing:group.total-verified-model};
 });
}
test("the final SURVEY preserves exactly 20 assessments and 38 questions",()=>{
 assert.equal(BENEFIT_GROUPS.length,20);
 assert.equal(sizes.reduce((n,g)=>n+g.total,0),38);
 assert.equal(sizes.length,5);
});
test("full final SURVEY readiness requires all 38 verified inputs AND four gates",()=>{
 const result=finalSurveyReadiness(sizes.map(g=>({...g,verified:g.total,missing:0})),gates,true);
 assert.equal(result.assessable,true);
 assert.equal(result.fullReady,true);
 assert.equal(result.reviewReady,true);
 assert.equal(result.provisionalGrade,"A · PROVISIONAL");
 assert.equal(result.verified,38);
 assert.equal(result.fullReadinessGrade,"READY — 38/38 VERIFIED");
 const blocked=finalSurveyReadiness(sizes.map(g=>({...g,verified:g.total,missing:0})),
  gates.map((g,i)=>i===2?{...g,passed:false}:g),true);
 assert.equal(blocked.fullReady,false);
 assert.equal(blocked.reviewReady,false);
 assert.equal(blocked.provisionalGrade,"A · PROVISIONAL","coverage grade is not a gate or a clinical grade");
 assert.deepEqual(blocked.failedGates,["Safety or competitor"]);
});
test("a five-group preliminary evidence-review pass does not equal a completed final SURVEY",()=>{
 const result=finalSurveyReadiness(assigned([1,1,1,1,1]),gates,true);
 assert.equal(result.reviewReady,true);
 assert.equal(result.fullReady,false);
 assert.equal(result.verified,5);
 assert.equal(result.provisionalGrade,"E · PROVISIONAL");
});
test("verified-coverage grades are transparent and 0 verified is UNGRADABLE, never F",()=>{
 const full=sizes.map(g=>g.total);
 for(const [count,grade] of [[0,"UNGRADABLE"],[10,"D · PROVISIONAL"],
  [20,"C · PROVISIONAL"],[30,"B · PROVISIONAL"],[35,"A · PROVISIONAL"]]){
  let remaining=count;
  const counts=full.map(v=>{const n=Math.min(v,remaining);remaining-=n;return n;});
  assert.equal(finalSurveyReadiness(assigned(counts),gates,true).provisionalGrade,grade);
 }
});
test("modeled questions are unverified, not zero-valued failed outcomes",()=>{
 const result=finalSurveyReadiness(assigned([0,0,0,0,0],{0:1,1:1}),gates,true);
 assert.equal(result.verified,0);
 assert.equal(result.modeled,2);
 assert.equal(result.provisionalGrade,"UNGRADABLE");
 assert.equal(result.fullReady,false);
 assert.equal(result.missingGroups.length,5);
});
test("missing, duplicate, unavailable or malformed source data never produces a grade",()=>{
 const complete=sizes.map(g=>({...g,verified:g.total,missing:0}));
 for(const [groups,rules,sourceOk] of [
  [complete,gates,false],
  [complete.slice(0,4),gates,true],
  [complete,gates.slice(0,3),true],
  [complete.map((g,i)=>i===0?{...g,missing:1}:g),gates,true]
 ]){
  const audit=finalSurveyReadiness(groups,rules,sourceOk);
  assert.equal(audit.assessable,false);
  assert.equal(audit.provisionalGrade,"UNGRADABLE");
  assert.equal(audit.fullReadinessGrade,"NOT ASSESSED");
  assert.equal(audit.fullReady,false);
 }
});
test("final dialog exposes separate grades, exact trial scope and every evidence gap",()=>{
 assert.match(source,/finalSurveyReadiness\(groups,rules,checked&&!!record\)/);
 assert.match(source,/Grade 1 · Full analysis readiness/);
 assert.match(source,/Grade 2 · Reluctant evidence-coverage grade/);
 assert.match(source,/Review outstanding evidence/);
 assert.match(source,/Survey \{q\.survey\} · \{q\.label\}/);
 assert.match(source,/ABSTAIN — this coverage audit cannot establish approval/);
 assert.match(source,/ready=audit\.reviewReady/);
 assert.match(source,/matched research inputs|No unique matching research record/i);
});

test("combined final SURVEY preserves all 20 canonical rows with sourced statuses, not synthetic medical scores",()=>{
 assert.match(source,/const surveyCoverage=BENEFIT_GROUPS\.map\(survey=>/);
 assert.match(source,/data-final-survey-number=\{survey\.number\}/);
 assert.match(source,/Twenty survey evidence coverage matrix/);
 assert.match(source,/All twenty survey evidence coverage/);
 assert.match(source,/survey\.fields\.filter\(field=>record\.facts\[field\.id\]\?\.status==="VERIFIED"\)/);
 assert.match(source,/survey\.fields\.filter\(field=>record\.facts\[field\.id\]\?\.status==="MODELED"\)/);
 assert.match(source,/survey\.fields\.length-verifiedCount-modeledCount/);
 assert.match(source,/Fully verified/);
 assert.match(source,/Partially verified/);
 assert.match(source,/Not assessed/);
 assert.match(source,/not clinical benefit, FDA success, or return probability/);
});
