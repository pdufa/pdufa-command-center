"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,".."),read=p=>fs.readFileSync(path.join(root,p),"utf8");
const snapshot=JSON.parse(read("data/raas-registry-evidence-census.json"));
test("762 retained source identities and no registry results presented as RAAS",()=>{
 assert.equal(snapshot.scope,"RAAS_REGISTRY_EVIDENCE_SOURCE_CENSUS");
 assert.equal(snapshot.counts.total,762);
 assert.equal(new Set(snapshot.records.map(r=>r.nctId)).size,762);
 assert.equal(snapshot.records.filter(r=>r.captureStatus!=="REGISTRY_NOT_IN_CACHE").length,snapshot.counts.cachedRegistry);
 assert.equal(snapshot.records.filter(r=>r.hasPostedResults===true).length,snapshot.counts.postedResults);
 assert.ok(snapshot.records.every(r=>r.issuerReadoutStage===null&&r.approvedRaasScore===null));
});
test("UI shows per-trial source provenance, results status and missing sources",()=>{
 const screen=read("app/RaasFullUniverseScores.tsx");
 const route=read("app/api/raas-registry-evidence/route.ts");
 assert.match(screen,/registryByNct.get/);
 assert.match(screen,/Registry evidence missing/);
 assert.match(screen,/NOT issuer-readout classification/);
 assert.match(route,/issuerReadoutStage:null,approvedRaasScore:null/);
 for(const [source,file] of [[screen,"RaasFullUniverseScores.tsx"],[route,"route.ts"]]){
  const res=ts.transpileModule(source,{fileName:file,reportDiagnostics:true,compilerOptions:{
   jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
  assert.deepEqual((res.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error),[]);
 }
});
