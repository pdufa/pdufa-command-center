"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const intake=require("../lib/raas-retrospective-intake.ts");
const obs=require("../lib/raas-retrospective-asof-evidence.ts");
const cases=intake.parseRetrospectiveFeed(require("../data/raas-retrospective-source-cases.json"));
const raw=require("../data/raas-retrospective-asof-evidence.json");
test("nine exact-case clinical/finance facts were published before retrospectively selected BOTTOM entry",()=>{
 const feed=obs.parseAsOfEvidence(raw,cases);
 assert.equal(feed.records.length,4);
 assert.equal(feed.records.flatMap(r=>r.facts).length,9);
 for(const entry of feed.records){
   const match=cases.records.find(c=>c.id===entry.caseId);
   assert.ok(match);
   for(const fact of entry.facts){
     assert.ok(fact.sourcePublishedAt<=match.entry.date);
     assert.ok(fact.sourceUrl.startsWith("https://"));
   }
 }
});
test("randomized responses preserve actual comparator and never become a 0–100 RAAS grade",()=>{
 const feed=obs.parseAsOfEvidence(raw,cases);
 const gern=obs.factsForRetrospectiveCase(feed,"gern-imetelstat-mds-2024-illustrative");
 assert.equal(gern.length,2);
 assert.equal(obs.measureAsOfFact(gern[0]).value,24.8);
 assert.equal(obs.measureAsOfFact(gern[1]).value,24.7);
 const vrna=obs.factsForRetrospectiveCase(feed,"vrna-ensifentrine-copd-2024-illustrative");
 assert.equal(obs.measureAsOfFact(vrna[0]).value,94);
 assert.equal(obs.measureAsOfFact(vrna[1]).value,87);
});
test("single-arm clinical response is not falsely converted to placebo-adjusted treatment effect",()=>{
 const feed=obs.parseAsOfEvidence(raw,cases);
 const urgn=obs.factsForRetrospectiveCase(feed,"urgn-ugn102-nmibc-2025-illustrative");
 assert.equal(urgn.length,3);
 assert.equal(urgn[0].kind,"SINGLE_ARM_RESPONSE");
 assert.match(obs.measureAsOfFact(urgn[0]).interpretation,/must NOT be inferred/);
 assert.equal(urgn[1].kind,"CONDITIONAL_DURABILITY");
 assert.match(obs.measureAsOfFact(urgn[1]).interpretation,/already achieved response/);
 assert.equal(urgn[2].kind,"CASH_BALANCE");
 assert.equal(obs.measureAsOfFact(urgn[2]).value,241.7);
});
test("future release, wrong trial identity and invalid placebo rates are rejected",()=>{
 const original=raw.records[0];
 const replace=(patch)=>({...raw,records:[{...original,facts:original.facts.map((f,i)=>i===0?{...f,...patch}:f)},...raw.records.slice(1)]});
 assert.throws(()=>obs.parseAsOfEvidence(replace({sourcePublishedAt:"2025-01-01"}),cases),/RAAS_ASOF_FACT_INVALID/);
 assert.throws(()=>obs.parseAsOfEvidence(replace({studyNctId:"NCT99999999"}),cases),/RAAS_ASOF_FACT_INVALID/);
 const randomized=raw.records.find(x=>x.caseId==="gern-imetelstat-mds-2024-illustrative");
 const altered={...raw,records:raw.records.map(r=>r.caseId===randomized.caseId?{...r,
  facts:r.facts.map((f,i)=>i===0?{...f,comparatorPercent:101}:f)}:r)};
 assert.throws(()=>obs.parseAsOfEvidence(altered,cases),/RAAS_ASOF_RANDOMIZED_INVALID/);
});
test("new TypeScript parser and RAAS history page parse cleanly",()=>{
 const root=path.resolve(__dirname,"..");
 for(const p of ["lib/raas-retrospective-asof-evidence.ts","app/raas-history/page.tsx"]){
  const transpiled=ts.transpileModule(fs.readFileSync(path.join(root,p),"utf8"),{
   fileName:p,reportDiagnostics:true,compilerOptions:{module:ts.ModuleKind.ESNext,
    target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}
  });
  assert.deepEqual((transpiled.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error)
   .map(d=>ts.flattenDiagnosticMessageText(d.messageText," ")),[]);
 }
});
