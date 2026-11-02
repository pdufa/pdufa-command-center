"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
 module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJS,esModuleInterop:true
 }}).outputText,file);
const {discoverRegistryPeerLeads}=require("../lib/registry-competitor-leads.ts");
const item=(nctId,interventions,conditions,resultsPosted=false)=>({
 nctId,sourceUrl:"https://clinicaltrials.gov/study/"+nctId,
 retrievedAt:"2026-11-01T17:11:02Z",interventions,conditionNames:conditions,resultsPosted
});
test("only exact recorded conditions and distinct interventions create unverified competitor leads",()=>{
 const a=item("NCT12345678",["Drug Alpha","Placebo"],[" Ulcerative   colitis "],true);
 const b=item("NCT12345679",["Drug Beta","Placebo"],["ulcerative colitis"],true);
 const c=item("NCT12345680",["Drug Alpha","Placebo"],["ulcerative colitis"],true);
 const d=item("NCT12345681",["Drug Gamma"],["Crohn disease"],true);
 const e=item("NCT12345682",["Placebo"],["ulcerative colitis"],true);
 const res=discoverRegistryPeerLeads([a,b,c,d,e]);
 assert.equal(res[a.nctId].status,"RESEARCH_LEADS_ONLY");
 assert.equal(res[a.nctId].totalCandidates,1);
 assert.equal(res[a.nctId].displayed[0].nctId,b.nctId);
 assert.equal(res[d.nctId].totalCandidates,0);
 assert.ok(res[a.nctId].displayed.every(x=>x.sourceUrl.startsWith("https://clinicaltrials.gov/study/")));
 assert.throws(()=>discoverRegistryPeerLeads([a,a]),/PEER_IDENTITY_INVALID/);
 assert.throws(()=>discoverRegistryPeerLeads([a,b],100),/INVALID_PEER_LEAD_LIMIT/);
});
test("peer lead lists cannot masquerade as current approved drugs or clinical efficacy scores",()=>{
 const a=item("NCT12345678",["Drug Alpha"],["Condition X"],true);
 const b=item("NCT12345679",["Drug Beta"],["Condition X"],false);
 const res=discoverRegistryPeerLeads([a,b],1);
 assert.equal(res[a.nctId].displayed[0].resultsPosted,false);
 assert.equal(res[a.nctId].displayed[0].sharedConditions[0],"Condition X");
 assert.ok(!Object.hasOwn(res[a.nctId],"rank"));
 assert.ok(!Object.hasOwn(res[a.nctId],"approvalStatus"));
});
