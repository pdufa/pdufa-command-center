"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const {buildRaasMetricGradebook}=require("../lib/raas-metric-gradebook.ts");
const get=(nct,ticker,stage,drug,indication)=>buildRaasMetricGradebook(
 {nctId:nct,ticker,drug,indication},stage);
const byId=(book,id)=>book.categories.flatMap(c=>c.rows).find(x=>x.id===id);

test("all 30 metrics and six categories are audited separately for both stages",()=>{
 const top=get("NCT07363577","LBRX","pre");
 const bottom=get("NCT06445023","CLDX","post");
 for(const book of [top,bottom]){
  assert.equal(book.total,30);assert.equal(book.categories.length,6);
  assert.ok(book.categories.every(g=>g.rows.length===5));
  assert.equal(new Set(book.categories.flatMap(g=>g.rows.map(x=>x.id))).size,30);
  assert.equal(book.approvedOverallScore,null);
  assert.equal(book.graded+book.mappedOnly+book.withoutEvidence,30);
  assert.ok(book.categories.every(c=>c.rows.every(r=>
   r.requiredEvidence&&r.scoreRule&&r.criticalRisk)));
 }
 assert.equal(top.graded,1);
 assert.equal(byId(top,"pre-4-1").grade.score,50);
 assert.equal(byId(top,"pre-4-1").status,"EXPERIMENTAL_GRADE");
 assert.equal(byId(top,"pre-3-2").status,"SOURCE_LEADS_ONLY");
 assert.equal(byId(top,"pre-1-1").status,"EVIDENCE_MISSING");
 assert.equal(bottom.graded,2);
 assert.equal(byId(bottom,"post-1-1").status,"EXPERIMENTAL_GRADE");
 assert.equal(byId(bottom,"post-1-1").grade.score,75);
 assert.equal(byId(bottom,"post-1-2").grade.score,100);
 assert.equal(byId(bottom,"post-3-5").status,"EVIDENCE_MISSING");
});
test("trial-specific BOTTOM clinical measurements are visible but NEVER called RAAS scores",()=>{
 const c1=get("NCT06445023","CLDX","post","barzolvolimab","chronic spontaneous urticaria");
 const c2=get("NCT06455202","CLDX","post","barzolvolimab","chronic spontaneous urticaria");
 const m=get("NCT06641076","MLTX","post","sonelokimab","psoriatic arthritis");
 const measured=(book,id)=>byId(book,id).evidence.flatMap(e=>e.measurement?[e.measurement.value]:[]);
 assert.deepEqual(measured(c1,"post-1-1"),[9.5]);
 assert.deepEqual(measured(c2,"post-1-1"),[8.8]);
 assert.deepEqual(measured(c1,"post-1-2"),[9.5,33.1]);
 assert.deepEqual(measured(c2,"post-1-2"),[8.8,33.1]);
 assert.deepEqual(measured(m,"post-1-1"),[42.1]);
 assert.deepEqual(measured(m,"post-4-2"),[537]);
 assert.equal(m.graded,0);assert.equal(c1.graded,2);assert.equal(c2.graded,2);
 assert.equal(c1.approvedOverallScore,null);assert.equal(c2.approvedOverallScore,null);
 assert.equal(c1.provisionalDiagnostic.fullyCoveredProvisionalScore,null);
});
test("wrong NCT, ticker or therapy cannot inherit other trial evidence",()=>{
 const exact=get("NCT07363577","LBRX","pre","LB-102 (100 mg tablet) | LB-102 (50 mg tablet)","Schizophrenia");
 assert.equal(exact.graded,1);
 const spoof=get("NCT07363577","LBRX","pre","unrelated therapy","Schizophrenia");
 assert.equal(spoof.categories.flatMap(x=>x.rows).filter(x=>x.evidence.length).length,0);
 assert.equal(spoof.graded,0);
 assert.equal(get("NCT07363577","FAKE","pre").graded,0);
 assert.equal(get("NCT99999999","LBRX","pre").graded,0);
 assert.throws(()=>get("BAD","LBRX","pre"),/IDENTITY_INVALID/);
 assert.throws(()=>get("NCT07363577","LBRX","invalid"),/STAGE_REQUIRED/);
});
test("full-universe trial table integrates lazy expandable TOP/BOTTOM scorecards",()=>{
 const ui=read("app/RaasFullUniverseScores.tsx");
 const detail=read("app/RaasMetricGradebook.tsx");
 assert.match(ui,/import RaasMetricGradebook/);
 assert.match(ui,/RaasMetricGradebook row=\{x\.row\} bucket=\{x\.stage\}/);
 assert.match(ui,/RaasTrialHistoryButton row=\{x\.row\} bucket=\{x\.stage\}/);
 assert.match(detail,/data-raas-metric-gradebook=\{row\.nctId\}/);
 assert.match(detail,/aria-expanded=\{open\}/);
 assert.match(detail,/buildRaasMetricGradebook/);
 assert.match(detail,/Source dates identify publications/);
 assert.match(detail,/Overall RAAS: N\/A/);
 for(const [text,file] of [[ui,"RaasFullUniverseScores.tsx"],[detail,"RaasMetricGradebook.tsx"]]){
  const result=ts.transpileModule(text,{fileName:file,reportDiagnostics:true,
   compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
  assert.deepEqual((result.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error),[]);
 }
});
