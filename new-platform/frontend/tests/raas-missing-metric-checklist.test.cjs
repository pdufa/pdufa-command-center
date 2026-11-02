"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}
).outputText,file);
const {RAAS_METRIC_CATALOG}=require("../lib/raas-metric-specs.ts");
const {raasMissingMetricChecklist}=require("../lib/raas-missing-metric-checklist.ts");
const ui=fs.readFileSync(require.resolve("../app/TrialRaasDisclosure.tsx"),"utf8");
const ids=stage=>RAAS_METRIC_CATALOG[stage].flatMap(g=>g.metrics.map(m=>m.id));

test("missing RAAS inventory preserves 6 categories, 30 metrics and stage-specific weights",()=>{
 for(const stage of ["pre","post"]){
  const queue=raasMissingMetricChecklist(stage,null,ids(stage));
  assert.equal(queue.total,30);assert.equal(queue.approved,0);assert.equal(queue.missing,30);
  assert.equal(queue.categories.length,6);
  assert.equal(queue.categories.reduce((n,c)=>n+c.weight,0),100);
  assert.ok(queue.categories.every(c=>c.missing.length===5&&c.approved===0));
  assert.ok(queue.categories.some(c=>c.missing.some(m=>m.status==="DEDICATED_SOURCE_REQUIRED")));
  assert.ok(queue.categories.flatMap(c=>c.missing).every(m=>m.relatedVerified===0&&
    m.relatedModeled===0&&m.relatedUnrecorded===m.relatedTotal));
 }
});
test("survey VERIFIED facts create only research leads, not approved RAAS metric grades",()=>{
 const example={facts:{
  clinicalBenefit:{status:"VERIFIED"},
  magnitude:{status:"MODELED"}
 }};
 const list=raasMissingMetricChecklist("pre",example,ids("pre"));
 assert.equal(list.approved,0);
 const metric=list.categories.flatMap(c=>c.missing).find(m=>m.id==="pre-1-1");
 assert.ok(metric);
 assert.equal(metric.relatedVerified,1);
 assert.equal(metric.relatedModeled,1);
 assert.equal(metric.relatedUnrecorded,1);
 assert.equal(metric.status,"PARTIAL_RESEARCH");
 const allVerified={facts:{
  clinicalBenefit:{status:"VERIFIED"},magnitude:{status:"VERIFIED"},meaningfulBenefit:{status:"VERIFIED"}
 }};
 const complete=raasMissingMetricChecklist("pre",allVerified,ids("pre"));
 assert.equal(complete.categories.flatMap(c=>c.missing).find(m=>m.id==="pre-1-1").status,
  "RELATED_RESEARCH_RECORDED");
 assert.equal(complete.approved,0);
});
test("only score-engine accepted grade IDs may remove metrics from the missing list",()=>{
 const missing=ids("post").slice(1);
 const list=raasMissingMetricChecklist("post",null,missing);
 assert.equal(list.approved,1);assert.equal(list.missing,29);
 assert.equal(list.categories[0].approved,1);
 assert.equal(list.categories[0].missing.length,4);
 assert.equal(raasMissingMetricChecklist("post",null,[...missing,missing[0]]),null);
 assert.equal(raasMissingMetricChecklist("post",null,[...missing,"invalid"]),null);
 assert.equal(raasMissingMetricChecklist("post",null,[]).approved,30);
});
test("TOOLS renders missing evidence first, under collapsible group headings, without invented grades",()=>{
 assert.match(ui,/raasMissingMetricChecklist\(bucket,record,grading\.missing\)/);
 assert.match(ui,/Missing RAAS metric grades/);
 assert.match(ui,/missing RAAS metric evidence checklist/);
 assert.match(ui,/20 surveys and 38 research questions provide leads/);
 assert.match(ui,/relatedVerified/);
 assert.match(ui,/NOT GRADED/);
 assert.match(ui,/RAAS is NOT SCORED unless all 30 grades are accepted/);
 assert.ok(ui.indexOf("Missing RAAS metric grades")<ui.indexOf("six weighted ingredients"));
});
