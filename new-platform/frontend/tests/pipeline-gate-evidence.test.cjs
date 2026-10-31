"use strict";
const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),
 {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const {pipelineEvidenceGates,pipelineGateCounts}=require("../lib/pipeline-gate-evidence.ts");
const base={nctId:"NCT12345678",ticker:"EXAM",company:"Example Inc",drug:null,indication:null,
 sourceUrl:"https://clinicaltrials.gov/study/NCT12345678",poolStatus:"EXACT_MATCH",
 censusStatus:"COMPLETED",capUsd:350000000,capAsOf:"2026-10-26T10:00:00Z",
 postPhase3Evidence:"REGISTRY_COMPLETED",qualification:"NEEDS_REVIEW",reasons:[],
 timeline:{phase3DataRelease:null,pdufaTarget:null}};
test("every historical research trial shows seven distinct gates, not a qualified program",()=>{
 const gates=pipelineEvidenceGates(base,"2026-10-31");
 const counts=pipelineGateCounts(base,"2026-10-31");
 assert.deepEqual(gates.map(g=>g.id),["pool","registry","listing","readout","therapy","rights","pdufa"]);
 assert.equal(gates[0].status,"HISTORICAL_POINTER");
 assert.equal(gates[1].status,"HISTORICAL_POINTER");
 assert.ok(gates[1].explanation.includes("NOT proof"));
 assert.equal(gates[2].status,"MISSING_EVIDENCE");
 assert.ok(gates[2].explanation.includes("2026-10-26"));
 assert.equal(counts.total,7);assert.equal(counts.missing,5);assert.equal(counts.historical,2);assert.equal(counts.qualified,false);
});
test("a recorded public source or FDA date does not establish clinical, commercial or FDA qualification",()=>{
 const row={...base,drug:"Drug A",indication:"Disease B",
 timeline:{phase3DataRelease:{date:"2026-08-10",sourceUrl:"https://example.org/readout"},pdufaTarget:{date:"2026-12-31",sourceUrl:"https://example.org/fda"}}};
 const gates=pipelineEvidenceGates(row,"2026-10-31");
 assert.equal(gates.find(g=>g.id==="readout").status,"SOURCE_REVIEW_REQUIRED");
 assert.equal(gates.find(g=>g.id==="pdufa").status,"SOURCE_REVIEW_REQUIRED");
 assert.equal(gates.find(g=>g.id==="therapy").status,"SOURCE_REVIEW_REQUIRED");
 assert.equal(gates.find(g=>g.id==="listing").status,"MISSING_EVIDENCE");
 assert.equal(gates.find(g=>g.id==="rights").status,"MISSING_EVIDENCE");
 assert.equal(pipelineGateCounts(row,"2026-10-31").qualified,false);
});
test("an unmatched or future-dated trial cannot earn evidence-complete status",()=>{
 const row={...base,poolStatus:"UNLINKED",drug:"Drug",indication:"Disease",
 timeline:{phase3DataRelease:{date:"2027-02-01",sourceUrl:"https://example.org/results"},pdufaTarget:null}};
 const checks=pipelineEvidenceGates(row,"2026-10-31");
 assert.equal(checks.find(g=>g.id==="pool").status,"IDENTITY_CONFLICT");
 assert.equal(checks.find(g=>g.id==="therapy").status,"MISSING_EVIDENCE");
 assert.equal(checks.find(g=>g.id==="readout").status,"MISSING_EVIDENCE");
 assert.equal(pipelineGateCounts(row,"2026-10-31").qualified,false);
});
test("all 20 assessment dossier views keep a safe separately linked Google Sheet evidence matrix",()=>{
 const component=fs.readFileSync(path.resolve(__dirname,"../app/PipelineEligibilityChecklist.tsx"),"utf8");
 const dossier=fs.readFileSync(path.resolve(__dirname,"../app/PipelineFourViews.tsx"),"utf8");
 const nav=fs.readFileSync(path.resolve(__dirname,"../app/FunnelWorkspace.tsx"),"utf8");
 assert.ok(component.includes("No historical snapshot"));
 assert.ok(component.includes("Site-to-Sheet synchronization is not installed"));
 assert.ok(component.includes("gid=1138168786"));
 assert.ok(dossier.includes("<PipelineEligibilityChecklist row={row} today={today}/>"));
 assert.ok(nav.includes("Eligibility Gate Matrix (Google Sheets)"));
 assert.ok(dossier.includes("RANKED_BENEFIT_ASSESSMENTS.map"));
});
