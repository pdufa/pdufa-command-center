"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
test("live registry collection receipt is exact-cohort, complete and non-predictive",()=>{
 const receipt=JSON.parse(read("data/raas-registry-evidence-status.json"));
 assert.equal(receipt.schemaVersion,1);
 assert.equal(receipt.scope,"RAAS_CT_GOV_EVIDENCE_COLLECTION_STATUS");
 const s=receipt.summary;
 assert.equal(s.researchTrials,762);
 assert.equal(s.sourceRecordsStored,762);
 assert.equal(s.sourceRecordsStillMissing,0);
 assert.equal(s.original35StillMissing,0);
 assert.equal(s.missingRecordsRecoveredFromOriginal35,35);
 assert.equal(s.postedRegistryResults+s.protocolOnly,s.sourceRecordsStored);
 assert.ok(s.trialsWithPrimaryRegistryAnalyses<=s.postedRegistryResults);
 assert.equal(s.approvedOverallRaasScores,0);
});
test("RAAS site displays source recovery without interpreting missing results as scores",()=>{
 const page=read("app/raas-scan/page.tsx");
 assert.match(page,/import registryEvidenceReceipt/);
 assert.match(page,/data-raas-registry-source-coverage/);
 assert.match(page,/registry.missingRecordsRecoveredFromOriginal35/);
 assert.match(page,/registry.trialsWithSeriousAdverseEventEvidence/);
 assert.match(page,/registry.sourceRecordsStillMissing/);
 assert.match(page,/Additional SEC, FDA, market and independent clinical reference evidence remains necessary/);
 const out=ts.transpileModule(page,{fileName:"page.tsx",reportDiagnostics:true,
  compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
 assert.deepEqual((out.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error),[]);
});
