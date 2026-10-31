"use strict";
const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,"utf8"),
 {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const {normalizeRegistryStudy}=require("../lib/pipeline-live-registry.ts");
const {renderRegistryEvidenceBatchCsv,REGISTRY_EVIDENCE_HEADERS}=require("../lib/pipeline-registry-evidence.ts");
const make=(n,id)=>({
 pinned:{nctId:id,ticker:"EXAM",company:"Example Sponsor"},
 review:normalizeRegistryStudy({protocolSection:{
  identificationModule:{nctId:id,briefTitle:n===0?'=HYPERLINK("https://bad.invalid","fake")':"Source trial "+n},
  statusModule:{overallStatus:n%2?"RECRUITING":"COMPLETED",lastUpdatePostDateStruct:{date:"2026-10-23"}},
  sponsorCollaboratorsModule:{leadSponsor:{name:"Example Sponsor"}},
  designModule:{phases:["PHASE3"],enrollmentInfo:{count:230+n}},
  conditionsModule:{conditions:["Fictitious disease"]},armsInterventionsModule:{interventions:[{name:"Investigational agent"}]}
 }},id,"2026-10-31T22:00:00.000Z")
});
const records=Array.from({length:25},(_,i)=>make(i,"NCT"+String(i+1).padStart(8,"0")));
test("batch uses exactly 24 columns, one CSV header and up to 25 provenance-preserved records",()=>{
 const csv=renderRegistryEvidenceBatchCsv(records);
 const lines=csv.trimEnd().split("\r\n");
 assert.equal(lines.length,26);
 assert.equal(REGISTRY_EVIDENCE_HEADERS.length,24);
 assert.equal((csv.match(/"REVIEW_REQUIRED"/g)||[]).length,25);
 assert.equal((csv.match(/"NEEDS_REVIEW — NOT QUALIFIED"/g)||[]).length,25);
 assert.ok(csv.includes('"\'=HYPERLINK(""https://bad.invalid"",""fake"")"'));
 assert.ok(csv.includes('"NCT00000001"'));assert.ok(csv.includes('"NCT00000025"'));
});
test("wrong NCT, duplicates, empty and oversized batches are rejected",()=>{
 assert.throws(()=>renderRegistryEvidenceBatchCsv([]),/1–25/);
 assert.throws(()=>renderRegistryEvidenceBatchCsv(records.concat(records[0])),/1–25/);
 assert.throws(()=>renderRegistryEvidenceBatchCsv([records[0],records[0]]),/Duplicate/);
 assert.throws(()=>renderRegistryEvidenceBatchCsv([{...records[0],pinned:{...records[0].pinned,nctId:"NCT99999999"}}]),/identity/);
 assert.throws(()=>renderRegistryEvidenceBatchCsv([{...records[0],review:{...records[0].review,qualification:"QUALIFIED"}}]),/identity/);
});
test("API uses one official exact-ID batch, verified full response and forbids partial exports",()=>{
 const route=fs.readFileSync(path.resolve(__dirname,"../app/api/phase3-batch/route.ts"),"utf8");
 assert.ok(route.includes('hasSession(req.cookies.get(COOKIE_NAME)?.value)'));
 assert.ok(route.includes('parsePhase3CensusCsv(original)'));
 assert.ok(route.includes('url.searchParams.set("filter.ids",ids.join(","))'));
 assert.ok(route.includes('url.searchParams.set("pageSize",String(current.length))'));
 assert.ok(route.includes('result.studies.length!==current.length||result.nextPageToken'));
 assert.ok(route.includes('!wanted.has(id)||byNct.has(id)'));
 assert.ok(route.includes('if(byNct.size!==ids.length)'));
 assert.ok(route.includes('renderRegistryEvidenceBatchCsv(records)'));
 assert.ok(route.includes('No rows were exported or qualified'));
 assert.ok(route.includes('private, no-store'));
});
test("Pipeline has explicit user-triggered, bounded batch controls; no auto-Sheets write",()=>{
 const ui=fs.readFileSync(path.resolve(__dirname,"../app/BatchRegistryExport.tsx"),"utf8");
 const page=fs.readFileSync(path.resolve(__dirname,"../app/FunnelWorkspace.tsx"),"utf8");
 assert.ok(ui.includes("CENSUS_TOTAL=741"));
 assert.ok(ui.includes('type BatchSize=5|10|25'));
 assert.ok(ui.includes('"/api/phase3-batch?offset="'));
 assert.ok(ui.includes('download'));
 assert.ok(ui.includes("Automatic website-to-Sheets synchronization remains unconfigured"));
 assert.ok(page.includes('{section==="pipeline"&&<BatchRegistryExport/>}'));
});
