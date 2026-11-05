"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const {parseRegistryEvidenceIndex,registryMetricLeads}=require("../lib/raas-registry-evidence.ts");
const {buildRaasMetricGradebook}=require("../lib/raas-metric-gradebook.ts");
const {RAAS_METRIC_CATALOG}=require("../lib/raas-metric-specs.ts");
const source=parseRegistryEvidenceIndex(JSON.parse(read("public/raas-registry-evidence-index.json")));
const byId=new Map(source.records.map(x=>[x.nctId,x]));

test("all 762 public-source trial identities can open either complete TOP or BOTTOM evidence checklist",()=>{
 assert.equal(source.records.length,762);
 assert.equal(new Set(source.records.map(r=>r.nctId)).size,762);
 let preWithProtocol=0,postWithResults=0;
 for(const r of source.records){
  const trial={nctId:r.nctId,ticker:r.ticker};
  for(const stage of ["pre","post"]){
   const book=buildRaasMetricGradebook(trial,stage,r);
   const metricIds=book.categories.flatMap(g=>g.rows.map(m=>m.id));
   assert.equal(metricIds.length,30);
   assert.equal(new Set(metricIds).size,30);
   assert.equal(book.graded+book.mappedOnly+book.withoutEvidence,30);
   assert.equal(book.approvedOverallScore,null);
   assert.ok(book.categories.every(g=>g.rows.every(m=>m.rubric)));
  }
  const top=registryMetricLeads(r,"pre",trial);
  const bottom=registryMetricLeads(r,"post",trial);
  if(top.some(x=>x.metricIds.includes("pre-1-2")))preWithProtocol++;
  if(bottom.some(x=>x.metricIds.includes("post-1-1")))postWithResults++;
  assert.equal(bottom.length>0?r.postedResults:true,true);
 }
 assert.equal(source.summary.registryRecords,762);
 assert.equal(source.summary.postedRegistryResults,337);
 assert.ok(preWithProtocol>700);
 assert.ok(postWithResults>100);
});

test("verified research source remains independent of stage; unverified never gets numeric overall",()=>{
 for(const nct of ["NCT06445023","NCT06455202","NCT06641076",
                   "NCT07363577","NCT07671911"]){
  const r=byId.get(nct);
  assert.ok(r);assert.ok(Array.isArray(r.registeredInterventions));
 }
 const ml=byId.get("NCT06641076");
 const bottom=buildRaasMetricGradebook({nctId:ml.nctId,ticker:ml.ticker}, "post",ml);
 assert.equal(bottom.approvedOverallScore,null);
 assert.equal(bottom.graded,0);
 assert.equal(bottom.categories.flatMap(g=>g.rows).length,30);
});

test("unverified trials expose five TOP or BOTTOM clinical questions without claiming classification",()=>{
 const ui=read("app/RaasClinicalFiveCell.tsx");
 const page=read("app/RaasFullUniverseScores.tsx");
 assert.match(ui,/const verified=bucket!==null/);
 assert.match(ui,/clinicalFiveForTrial/);
 assert.match(ui,/setSelected\(s\)/);
 assert.match(ui,/stageVerified|stage has not been issuer-classified|status has not been issuer-classified/);
 assert.match(page,/RaasClinicalFiveCell row=\{x\.row\} bucket=\{x\.stage\}/);
 assert.match(page,/RaasTrialHistoryButton row=\{x\.row\} bucket=\{x\.stage\}/);
 assert.match(ui,/Missing ratings are N\/A/);
 assert.match(ui,/five documented grades and verified stage/);
});
