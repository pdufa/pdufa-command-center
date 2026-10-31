"use strict";
const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),
 {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const {reconcilePoolPipeline,funnelPage}=require("../lib/pool-pipeline-funnel.ts");
const {parsePhase3CensusCsv}=require("../lib/phase3-census-rows.ts");
const {renderPhase3CensusCsv,CENSUS_CSV_HEADERS}=require("../lib/pipeline-census-csv.ts");
const dir=path.resolve(__dirname,"../public");
const csv=fs.readFileSync(path.join(dir,"phase3-census-2026-10-26.csv"),"utf8");
const sources=JSON.parse(fs.readFileSync(path.join(dir,"phase3-census-sources-2026-10-26.json"),"utf8"));
const census=parsePhase3CensusCsv(csv);
const rows=census.rows.map(x=>({id:"TRIAL|"+x.nctId,ticker:x.ticker,company:x.company,drug:"Not verified",indication:"Not verified"}));
const snapshot={pipeline:rows,sourceHealth:{state:"PARTIAL",clinicalRows:rows.length,regulatoryRows:0,pipelineSourceParity:{exactPrograms:rows.length}}};
const data=reconcilePoolPipeline(snapshot,csv,sources);
test("all 741 pinned Phase 3 records export; no candidate is silently promoted",()=>{
 const text=renderPhase3CensusCsv(data);
 const lines=text.trimEnd().split("\r\n");
 assert.equal(lines.length,742);
 assert.equal(lines[0].split(",").length,CENSUS_CSV_HEADERS.length);
 assert.equal((text.match(/"COMPLETED"/g)||[]).length,375);
 assert.equal((text.match(/"NEEDS_REVIEW"/g)||[]).length,741);
 assert.ok(text.includes("2026-10-26"));
 assert.equal(funnelPage(data,"census-review",0,50,"").total,741);
 assert.equal(funnelPage(data,"pipeline",0,50,"").total,375);
 assert.equal(funnelPage(data,"readout-review",0,50,"").total,366);
 assert.equal(data.overview.qualifiedPrograms,null);
});
test("authenticated export is safe for spreadsheet import and fails closed on corrupt research sources",()=>{
 const injection={...data,reviewRows:data.reviewRows.map((r,i)=>i===0?{...r,company:'=HYPERLINK("https://attacker.invalid","OPEN")'}:r)};
 assert.ok(renderPhase3CensusCsv(injection).includes('"\'=HYPERLINK(""https://attacker.invalid"",""OPEN"")"'));
 const duplicate={...data,reviewRows:data.reviewRows.map((r,i)=>i===1?{...r,nctId:data.reviewRows[0].nctId}:r)};
 assert.throws(()=>renderPhase3CensusCsv(duplicate),/incomplete|changed/);
 const badCap={...data,reviewRows:data.reviewRows.map((r,i)=>i===0?{...r,capUsd:25}:r)};
 assert.throws(()=>renderPhase3CensusCsv(badCap),/source invalid/);
 const falselyQualified={...data,reviewRows:data.reviewRows.map((r,i)=>i===0?{...r,qualification:"QUALIFIED"}:r)};
 assert.throws(()=>renderPhase3CensusCsv(falselyQualified),/source invalid/);
});
test("census view and export require existing dashboard session",()=>{
 const api=fs.readFileSync(path.resolve(__dirname,"../app/api/scope-funnel/route.ts"),"utf8");
 const ui=fs.readFileSync(path.resolve(__dirname,"../app/FunnelWorkspace.tsx"),"utf8");
 assert.ok(api.includes('hasSession(req.cookies.get(COOKIE_NAME)?.value)'));
 assert.ok(api.indexOf('hasSession(req.cookies.get')<api.indexOf('renderPhase3CensusCsv(data)'));
 assert.ok(api.includes('format==="csv" && view!=="census-review"'));
 assert.ok(api.includes('private, no-store'));
 assert.ok(api.includes('X-PDUFA-Source-Version'));
 assert.ok(ui.includes('/api/scope-funnel?view=census-review&format=csv'));
});
