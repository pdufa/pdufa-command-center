"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
 esModuleInterop:true}}).outputText,file);
const {parsePhase3CensusCsv}=require("../lib/phase3-census-rows.ts");
const {classifyPhase3Readouts}=require("../lib/phase3-public-readout.ts");
const {exactClassifiedRaasComponentGrades:grades}
 =require("../lib/raas-classified-component-grades.ts");
const {buildTopBottomRaasMetricWorklist:exportWorklist}
 =require("../lib/raas-top-bottom-spreadsheet-worklist.ts");
const census=fs.readFileSync(path.join(root,"public/phase3-census-2026-10-26.csv"),"utf8");
const evidence=JSON.parse(fs.readFileSync(path.join(root,
 "public/phase3-public-readout-evidence-2026-11-01.json"),"utf8"));
const result=classifyPhase3Readouts(evidence,parsePhase3CensusCsv(census).rows);

test("all actual source-classified TOP/BOTTOM rows have 30 populated slots, never guessed overall scores",()=>{
 assert.equal(result.total,741);
 assert.equal(result.pre.length,2);
 assert.equal(result.post.length,8);
 assert.equal(result.unverified.length,731);
 let count=0,graded=0,missing=0;
 const byCase=new Map();
 for(const [stage,rows] of [["pre",result.pre],["post",result.post]]){
  let stageGrades=0;
  for(const row of rows){
   const output=grades(stage,row);
   count++;
   assert.equal(output.nctId,row.nctId);
   assert.equal(output.ticker,row.ticker);
   assert.equal(output.stage,stage==="pre"?"TOP":"BOTTOM");
   assert.equal(output.totalMetrics,30);
   assert.equal(output.provisionalGrades.length,30);
   assert.equal(new Set(output.provisionalGrades.map(x=>x.id)).size,30);
   assert.equal(output.gradedMetrics+output.missingMetrics,30);
   assert.equal(output.approvedOverallRaasScore,null);
   assert.equal(output.fdaPassCrlExtensionProbability,null);
   assert.equal(output.independentFullRaasValidation,false);
   assert.ok(output.provisionalGrades.every(x=>x.grade===null||[0,25,50,75,100].includes(x.grade)));
   for(const x of output.provisionalGrades){
    if(x.grade===null){
     assert.equal(x.sourceUrl,null);
     assert.equal(x.reviewClass,null);
     assert.equal(x.assessedAt,null);
     assert.equal(x.benchmarkSourceUrl,null);
    }else{
     assert.match(x.sourceUrl,/^https:\/\//);
     assert.match(x.benchmarkSourceUrl,/^https:\/\//);
     assert.match(x.assessedAt,/^\d{4}-\d\d-\d\d$/);
     assert.equal(x.reviewClass,"AI_SOURCE_CROSSCHECKED");
    }
   }
   byCase.set(row.nctId,output.gradedMetrics);
   graded+=output.gradedMetrics;
   stageGrades+=output.gradedMetrics;
   missing+=output.missingMetrics;
  }
  assert.equal(stageGrades,stage==="pre"?10:20);
  const worklist=exportWorklist(stage,rows);
  assert.equal(worklist.summary.existingProvisionalGrades,stageGrades);
  assert.equal(worklist.summary.reviewMissingRows,rows.length*30-stageGrades);
  assert.equal(worklist.summary.approvedOverallRaasScores,0);
 }
 assert.equal(count,10);
 assert.equal(graded,30);
 assert.equal(missing,270);
 assert.deepEqual(Object.fromEntries(byCase),{
  NCT07363577:5,NCT07671911:5,
  NCT06445023:3,NCT06455202:3,NCT06641076:0,
  NCT05186818:4,NCT05767346:4,NCT06081894:5,
  NCT03697109:1,NCT04308590:0
 });
});
test("NO stage, no issuer source, cross-therapy or cross-NCT identities cannot generate a scorecard",()=>{
 const source=result.pre[0],post=result.post[0],unknown=result.unverified[0];
 assert.throws(()=>grades("pre",unknown),/EXACT_ISSUER_SOURCE_REQUIRED/);
 assert.throws(()=>grades("post",source),/EXACT_ISSUER_SOURCE_REQUIRED/);
 assert.throws(()=>grades("pre",post),/EXACT_ISSUER_SOURCE_REQUIRED/);
 assert.throws(()=>grades("pool",source),/ONLY_SOURCE_CLASSIFIED_TOP_BOTTOM/);
 assert.throws(()=>grades("pre",{...source,nctId:post.nctId}),
  /EXACT_ISSUER_SOURCE_REQUIRED/);
 assert.throws(()=>grades("pre",{...source,ticker:"WRONG"}),
  /EXACT_ISSUER_SOURCE_REQUIRED/);
 const unrelated=grades("pre",{...source,evidence:{
  ...source.evidence,drug:"UNRELATED",indication:"WRONG"
 }});
 assert.equal(unrelated.gradedMetrics,0);
 assert.equal(unrelated.missingMetrics,30);
 assert.ok(unrelated.provisionalGrades.every(x=>x.grade===null));
});
test("the matching therapy cannot borrow another trial's or another stage's provisional grades",()=>{
 const source=result.post.find(x=>x.nctId==="NCT06445023");
 assert.ok(source);
 const wrong={...source,evidence:{...source.evidence,
  drug:"unrelated different therapy",indication:"different disease"}};
 const output=grades("post",wrong);
 assert.equal(output.gradedMetrics,0);
 assert.equal(output.missingMetrics,30);
 assert.ok(output.provisionalGrades.every(x=>x.grade===null));
});
test("the visible TOP/BOTTOM sheets and their exported CSV both populate the exact metrics",()=>{
 const s=fs.readFileSync(path.join(root,"app/Phase3ReadoutSheets.tsx"),"utf8");
 const c=fs.readFileSync(path.join(root,"app/RaasClassifiedComponentsCell.tsx"),"utf8");
 assert.match(s,/<RaasClassifiedComponentsCell row=\{row\} bucket=\{bucket\}\/>/);
 assert.match(s,/documentedRaasStageExportFields\(bucket,row\)/);
 assert.match(s,/report\.provisionalGrades\.map\(metric=>metric\.grade===null\?""\:metric\.grade\)/);
 assert.match(s,/bucket==="unverified"\?\[\]\:documentedRaasStageExportFields/);
 assert.match(c,/data-raas-classified-nct-score-populated/);
 assert.match(c,/data-raas-classified-stage/);
 assert.match(c,/data-raas-metric-grade-expansion/);
 assert.match(c,/m\.grade===null\?"N\/A"\:m\.grade\+"\/100"/);
 assert.match(c,/m\.sourceUrl/);
 assert.match(c,/m\.benchmarkSourceUrl/);
 assert.match(c,/full RAAS: not validated/);
 const compiled=ts.transpileModule(c,{fileName:"RaasClassifiedComponentsCell.tsx",
  reportDiagnostics:true,compilerOptions:{module:ts.ModuleKind.ESNext,
   target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}});
 assert.equal((compiled.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error).length,0);
});
