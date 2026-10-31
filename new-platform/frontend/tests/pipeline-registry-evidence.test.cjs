"use strict";
const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const {normalizeRegistryStudy}=require("../lib/pipeline-live-registry.ts");
const {REGISTRY_EVIDENCE_HEADERS,registryEvidenceRow,renderRegistryEvidenceCsv}=require("../lib/pipeline-registry-evidence.ts");
const nctId="NCT12345678",pinned={nctId,ticker:"EXAM",company:"Example Sponsor"};
const registry=normalizeRegistryStudy({protocolSection:{
 identificationModule:{nctId,briefTitle:"Prospective study"},statusModule:{overallStatus:"COMPLETED",lastUpdatePostDateStruct:{date:"2026-10-20"}},
 sponsorCollaboratorsModule:{leadSponsor:{name:"Example Sponsor"}},
 designModule:{phases:["PHASE3"],enrollmentInfo:{count:350}},
 conditionsModule:{conditions:["Disease A"]},
 armsInterventionsModule:{interventions:[{name:"Study Medicine"}]},
},hasResults:true},nctId,"2026-10-31T20:00:00.000Z");
test("evidence CSV has stable A:X 24 field schema and never promotes eligibility",()=>{
 const row=registryEvidenceRow(registry,pinned);
 assert.equal(REGISTRY_EVIDENCE_HEADERS.length,24);assert.equal(row.length,24);
 assert.equal(row[0],nctId);assert.equal(row[1],"EXAM");assert.equal(row[2],"Example Sponsor");
 assert.equal(row[3],"");assert.equal(row[4],"");
 assert.equal(row[8],"YES — REGISTRY ONLY");
 assert.equal(row[17],"https://clinicaltrials.gov/study/"+nctId);
 assert.equal(row[18],"2026-10-31T20:00:00.000Z");
 assert.equal(row[19],"NOT EVALUATED — DRUG NOT VERIFIED");
 assert.equal(row[20],"NOT EVALUATED — INDICATION NOT VERIFIED");
 assert.equal(row[21],"EXACT_NAME_MATCH_ONLY — RIGHTS NOT VERIFIED");
 assert.equal(row[22],"NEEDS_REVIEW — NOT QUALIFIED");assert.equal(row[23],"REVIEW_REQUIRED");
 const csv=renderRegistryEvidenceCsv(registry,pinned);
 assert.equal(csv.trimEnd().split("\r\n").length,2);
 assert.equal((csv.match(/"REVIEW_REQUIRED"/g)||[]).length,1);
});
test("reject mismatched program NCT and missing exact ClinicalTrials.gov provenance",()=>{
 assert.throws(()=>registryEvidenceRow(registry,{...pinned,nctId:"NCT99999999"}),/identity/);
 assert.throws(()=>registryEvidenceRow({...registry,sourceUrl:"https://example.invalid/study/"+nctId},pinned),/identity/);
 assert.throws(()=>registryEvidenceRow({...registry,qualification:"QUALIFIED"},pinned),/identity/);
 assert.throws(()=>registryEvidenceRow({...registry,verifiedAt:"invalid"},pinned),/identity/);
});
test("quotes and spreadsheet formula content from a source cannot execute on CSV import",()=>{
 const weird=renderRegistryEvidenceCsv({...registry,title:'=HYPERLINK("https://bad.invalid","open")',leadSponsor:'+SUM(2,2)',conditions:['"Disease X"']},pinned);
 assert.ok(weird.includes('"\'=HYPERLINK(""https://bad.invalid"",""open"")"'));
 assert.ok(weird.includes('"\'+SUM(2,2)"'));
 assert.ok(weird.includes('"""Disease X"""'));
});
test("download route has authenticated, allowlisted, source-verified CSV with no direct Sheet write",()=>{
 const source=fs.readFileSync(path.join(__dirname,"../app/api/phase3-trial/route.ts"),"utf8");
 assert.ok(source.includes("hasSession(req.cookies.get(COOKIE_NAME)?.value)"));
 assert.ok(source.includes('corpus.rows.find(r=>r.nctId===nct)'));
 assert.ok(source.includes('renderRegistryEvidenceCsv(record,{nctId:nct,ticker:pinned.ticker,company:pinned.company})'));
 assert.ok(source.includes('"Cache-Control":"private, no-store"'));
 assert.ok(source.includes('"X-PDUFA-Evidence-Status":"REVIEW_REQUIRED"'));
 const ui=fs.readFileSync(path.join(__dirname,"../app/LiveRegistryReview.tsx"),"utf8");
 assert.ok(ui.includes('&format=csv'));
 assert.ok(ui.includes('Google Sheets review'));
});
