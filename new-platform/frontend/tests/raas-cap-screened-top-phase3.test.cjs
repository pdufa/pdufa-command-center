"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const {parsePhase3CensusCsv}=require("../lib/phase3-census-rows.ts");
const {classifyPhase3Readouts}=require("../lib/phase3-public-readout.ts");
const {parseRaasScreenedPhase3Csv,RAAS_RESTRICTED_TOP_PHASE3_CSV_QUERY}=
 require("../lib/raas-full-universe-roster.ts");
const {splitCapScreenedTopPhase3,capScreenedTopPhase3Csv}=
 require("../lib/raas-cap-screened-top-phase3.ts");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const classified=classifyPhase3Readouts(
 JSON.parse(read("public/phase3-public-readout-evidence-2026-11-01.json")),
 parsePhase3CensusCsv(read("public/phase3-census-2026-10-26.csv")).rows);
const fields=["NCT ID","Ticker","Company","Drug / therapy","Disease / indication",
 "Recorded development stage","Source snapshot as of",
 ...Array.from({length:13},(_,i)=>"Other "+i)];
const line=(nct,ticker,stage="Phase 3")=>[
 nct,ticker,"Example issuer","Drug, Inc.","Disease",stage,
 "2026-11-05T22:15:00.000Z",...Array(13).fill("")];
const quote=s=>'"'+s.replace(/"/g,'""')+'"';
const csv=rows=>"\uFEFF"+[fields,...rows].map(x=>x.map(quote).join(",")).join("\r\n")+"\r\n";
test("TOP cap-screen source fetches only Phase 3 from verified $300M–$10B issuer screen",()=>{
 const url=new URL(RAAS_RESTRICTED_TOP_PHASE3_CSV_QUERY,"https://example.org");
 assert.equal(url.pathname,"/api/scope-funnel");
 assert.equal(url.searchParams.get("stages"),"Phase 3");
 assert.equal(url.searchParams.get("tools"),"1");
 assert.equal(url.searchParams.get("recordKind"),"trials");
 assert.equal(url.searchParams.get("format"),"csv");
 assert.equal(url.searchParams.get("offset"),"0");
 const route=read("app/api/scope-funnel/route.ts");
 const restrict=read("lib/tools-restricted-scope.ts");
 assert.match(route,/restrictedToolsSnapshot\(/);
 assert.match(restrict,/TOOL_MIN_CAP_USD=300_000_000/);
 assert.match(restrict,/TOOL_MAX_CAP_USD=10_000_000_000/);
});
test("TOP cap-screened split removes documented BOTTOM, keeps saved TOP separate and never promotes unknown",()=>{
 const r=parseRaasScreenedPhase3Csv(csv([
  line("NCT07363577","LBRX"), // saved TOP as of source check
  line("NCT06445023","CLDX"), // documented BOTTOM despite registry-stage mismatch
  line("NCT12345678","TEST"),
  line("NCT12345679","TEST")
 ]),classified);
 const report=splitCapScreenedTopPhase3(r,classified);
 assert.equal(report.totalCurrentTopPhase3,3);
 assert.equal(report.alreadyTop.length,1);
 assert.equal(report.alreadyTop[0].nctId,"NCT07363577");
 assert.equal(report.excludedKnownPost,1);
 assert.deepEqual(report.candidates.map(x=>x.nctId),["NCT12345678","NCT12345679"]);
 assert.ok(report.candidates.every(x=>x.evidence===null));
 assert.equal(r.details.get("NCT12345678").drug,"Drug, Inc.");
 const output=capScreenedTopPhase3Csv(r,report);
 assert.equal(output.trim().split(/\r?\n/).length,4);
 assert.match(output,/READOUT_UNVERIFIED/);
 assert.match(output,/TOP_AS_OF_SAVED_ISSUER_CHECK/);
 assert.doesNotMatch(output,/NCT06445023/);
 assert.match(output,/\$300M/);
});
test("Phase 3 Results cannot be slipped into TOP, and no registry posting is treated as issuer verification",()=>{
 const r=parseRaasScreenedPhase3Csv(csv([line("NCT12345678","TEST","Phase 3 Results")]),classified);
 assert.throws(()=>splitCapScreenedTopPhase3(r,classified),
  /TOP_CAP_SCREENED_PHASE3_STAGE_OR_ID_INVALID/);
 const s=read("app/CapScreenedTopPhase3Spreadsheet.tsx");
 assert.doesNotMatch(s,/RaasClinicalFiveCell|RaasTrialHistoryButton/);
 assert.match(s,/excludedKnownPost/);
 assert.match(s,/readout-unverified|not automatically confirmed pre-readout/i);
 const page=read("app/Phase3SourceOnlySheets.tsx");
 assert.match(page,/<CapScreenedTopPhase3Spreadsheet classification=\{data\} query=\{query\}\/>/);
 const original=read("app/raas-top-bottom/page.tsx");
 assert.match(original,/Surveys and ratings cancelled/);
 assert.doesNotMatch(original,/RaasClinicalFiveCompletionPanel/);
});
