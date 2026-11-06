"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const read=name=>JSON.parse(fs.readFileSync(path.join(root,name),"utf8"));
const roster=read("data/alks34ClinicalScorecard20261106.json");
const audit=read("../../reports/alks-34-clinical-factor-dispositions-2026-11-06.json");
const supplement=read("data/raas-clinical-five-reviewed-increment.json");
const scoreValues=new Set([0,25,50,75,100]);
test("Alkermes 34 exact NCT records and 170 five-factor audit cells reconcile",()=>{
 assert.equal(roster.records.length,34);
 assert.equal(new Set(roster.records.map(r=>r.nctId)).size,34);
 assert.equal(audit.records.length,170);
 assert.deepEqual(audit.summary,{GRADED:115,NOT_APPLICABLE:55,PENDING_SOURCE:0});
 assert.equal(audit.records.filter(r=>r.status==="GRADED").length,115);
 assert.equal(audit.records.filter(r=>r.status==="NOT_APPLICABLE").length,55);
 assert.equal(audit.records.filter(r=>r.status==="PENDING_SOURCE").length,0);
 for(const r of roster.records){
  const factors=audit.records.filter(x=>x.nctId===r.nctId);
  assert.equal(factors.length,5,r.nctId);
  assert.equal(new Set(factors.map(x=>x.metricId)).size,5,r.nctId);
  assert.equal(factors.filter(x=>x.status==="NOT_APPLICABLE").length,r.notApplicableClinicalFactors.length,r.nctId);
 }
});
test("All 19 efficacy-primary trials have five source-backed research grades, while safety-only studies do not receive fake efficacy",()=>{
 const efficacy=roster.records.filter(r=>r.studyPurpose!=="SAFETY_PRIMARY");
 const safety=roster.records.filter(r=>r.studyPurpose==="SAFETY_PRIMARY");
 assert.equal(efficacy.length,19);
 assert.equal(safety.length,15);
 for(const r of efficacy){
  const a=audit.records.filter(x=>x.nctId===r.nctId);
  assert.equal(a.filter(x=>x.status==="GRADED").length,5,r.nctId);
  assert.equal(a.filter(x=>x.status==="NOT_APPLICABLE").length,0,r.nctId);
  assert.equal(r.clinicalStageVerified,true,r.nctId);
 }
 for(const r of safety){
  const a=audit.records.filter(x=>x.nctId===r.nctId);
  const forbidden=new Set(r.clinicalStage==="pre"?["pre-1-1","pre-1-5","pre-1-2"]:["post-1-1","post-1-2","post-1-3"]);
  for(const item of a.filter(x=>forbidden.has(x.metricId))){
   assert.equal(item.status,"NOT_APPLICABLE",r.nctId+":"+item.metricId);
   assert.equal(item.grade,null,r.nctId+":"+item.metricId);
  }
 }
});
test("Every numeric grade has a true exact-trial source and retains distinct N/A status",()=>{
 const records=supplement.records.filter(r=>r.ticker==="ALKS");
 assert.equal(records.length,115);
 const ids=new Set();
 for(const row of records){
  const key=[row.nctId,row.stage,row.metricId].join("|");
  assert.equal(ids.has(key),false,key);
  ids.add(key);
  assert.match(row.sourceUrl,/^https:\/\//);
  assert.match(row.benchmarkSourceUrl,/^https:\/\//);
  assert.notEqual(row.sourceUrl,row.benchmarkSourceUrl);
  assert.ok(row.observedResult.length>20);
 }
 for(const item of audit.records){
  if(item.status==="GRADED"){
   assert.ok(scoreValues.has(item.grade),item.nctId+":"+item.metricId);
   assert.match(item.sourceUrl,/^https:\/\//);
  }else{
   assert.equal(item.grade,null);
   assert.equal(item.sourceUrl,null);
  }
 }
});
test("N1539 original drug corrected and exploratory outcome not a pivotal pass",()=>{
 const t=roster.records.find(r=>r.nctId==="NCT01436032");
 assert.ok(t);
 assert.match(t.clinicalProgramDrug,/meloxicam/i);
 assert.doesNotMatch(t.clinicalProgramDrug,/ketorolac/i);
 assert.equal(t.historicalPrimaryOutcome,"NO_BINARY_PASS_FAIL");
 assert.match(t.historicalOutcomeExplanation,/post hoc|exploratory/i);
 assert.equal(t.clinicalStage,"post");
 assert.equal(audit.records.filter(r=>r.nctId===t.nctId&&r.status==="GRADED").length,5);
});
