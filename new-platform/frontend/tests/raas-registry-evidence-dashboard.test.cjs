"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
test("RAAS scan shows official full-source collection without promoting registry data to a grade",()=>{
 const data=JSON.parse(read("data/raas-registry-evidence-status.json"));
 const ui=read("app/raas-scan/page.tsx");
 assert.equal(data.scope,"RAAS_CT_GOV_EVIDENCE_COLLECTION_STATUS");
 assert.equal(data.summary.researchTrials,762);
 assert.equal(data.summary.sourceRecordsStored,762);
 assert.equal(data.summary.missingRecordsRecoveredFromOriginal35,35);
 assert.equal(data.summary.original35StillMissing,0);
 assert.equal(data.summary.approvedOverallRaasScores,0);
 assert.equal(new Set(data.recoveredFromOriginalGaps).size,35);
 for(const text of ["registryEvidence.summary.sourceRecordsStored",
  "registryEvidence.summary.trialsWithPrimaryRegistryAnalyses",
  "registryEvidence.summary.trialsWithSeriousAdverseEventEvidence",
  "registryEvidence.summary.sourceRecordsStillMissing",
  "data-raas-collected-registry-evidence",
  "not as confirmed TOP/BOTTOM","RAAS ratings"]){
  assert.ok(ui.includes(text),"Missing evidence disclosure: "+text);
 }
 const out=ts.transpileModule(ui,{fileName:"page.tsx",reportDiagnostics:true,
  compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
 assert.deepEqual((out.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error),[]);
});
