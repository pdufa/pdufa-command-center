"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const {parseRegistryEvidenceIndex}=require("../lib/raas-registry-evidence.ts");
const {rawRaasRegistryDesignDiagnostic:grade}=require("../lib/raas-raw-registry-design.ts");
const index=parseRegistryEvidenceIndex(JSON.parse(read("public/raas-registry-evidence-index.json")));
test("all 762 research NCTs have a raw design calculation or an explicit evidence-missing grade",()=>{
 assert.equal(index.records.length,762);
 const ids=new Set(),data=[];
 for(const r of index.records){
  assert.ok(!ids.has(r.nctId));
  ids.add(r.nctId);
  const g=grade(r,{nctId:r.nctId,ticker:r.ticker});
  assert.ok(g);
  assert.equal(g.nctId,r.nctId);
  assert.equal(g.overallRaasScore,null);
  assert.ok(g.score===null||[0,25,50,75,100].includes(g.score));
  if(g.score!==null){
   assert.ok(g.knownFacets>=3);
   assert.ok(g.lowerBound<=g.upperBound);
  }
  data.push(g);
 }
 assert.ok(data.filter(x=>x.score!==null).length>=700);
});
test("all-source roster is explicitly selected, not silently treated as qualified PIPELINE",()=>{
 const ui=read("app/RaasFullUniverseScores.tsx");
 assert.match(ui,/data-raas-full-source-roster="true"/);
 assert.match(ui,/data-raas-roster-scope=\{scope==="registry"\?"registry-762-research"/);
 assert.match(ui,/All 762 registry research trials/);
 assert.match(ui,/not independently confirmed to be current/);
 assert.match(ui,/stage names alone do not establish public results/);
 assert.match(ui,/rawRaasRegistryDesignDiagnostic\(registry,trial\)/);
 const output=ts.transpileModule(ui,{fileName:"RaasFullUniverseScores.tsx",
 reportDiagnostics:true,compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
 assert.deepEqual((output.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error),[]);
});
