"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>{
 const code=fs.readFileSync(file,"utf8");
 mod._compile(ts.transpileModule(code,{
  fileName:file,compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
 }).outputText,file);
};
const engine=require("../lib/raas-finance-reconciliation.ts");
const topIntake=require("../lib/raas-top-retrospective-intake.ts");
const bottomIntake=require("../lib/raas-retrospective-intake.ts");
const top=topIntake.parseTopRetrospective(require("../data/raas-retrospective-top-cases.json"));
const bottom=bottomIntake.parseRetrospectiveFeed(require("../data/raas-retrospective-source-cases.json"));
const raw=require("../data/raas-historical-finance-facts.json");
test("all seven TOP/BOTTOM historical examples have on-time issuer/SEC financial observations",()=>{
 const f=engine.parseHistoricalFinance(raw,top,bottom);
 assert.equal(f.records.length,7);
 assert.equal(f.records.reduce((sum,r)=>sum+r.facts.length,0),24);
 const index=new Map([...top.records,...bottom.records].map(x=>[x.id,x]));
 for(const row of f.records){
  const c=index.get(row.caseId);
  assert.ok(c,"Exact historical case identity exists");
  assert.ok(row.publishedAt<=c.entry.date,"No after-entry source may be included");
  assert.ok(row.sourceUrl.startsWith("https://"));
  assert.ok(row.asOf<=row.publishedAt);
  assert.equal(engine.financeReadiness(f,row.caseId,row.stage).usableInApprovedRAAS,false);
  assert.equal(engine.financeReadiness(f,row.caseId,row.stage).fullyDilutedValuationReconciled,false);
  assert.equal(engine.financeReadiness(f,row.caseId,row.stage).cashRunwayCalculated,false);
 }
 assert.equal(engine.financeForCase(f,"gern-imerge-mds-pre2023-illustrative").facts.find(x=>x.type==="OPERATING_EXPENSES_QTR").valueUsdMillions,40.245);
 const mdglRecord=engine.financeForCase(f,"mdgl-resmetirom-nash-2023-2024-illustrative");
 assert.equal(mdglRecord.publishedAt,"2023-08-08");
 assert.equal(mdglRecord.asOf,"2023-06-30");
 assert.ok(mdglRecord.publishedAt<"2023-11-03");
 assert.ok(mdglRecord.facts.some(x=>x.type==="OPERATING_CASH_USED_6M"&&x.valueUsdMillions===159.377));
});
test("November 2022 MDGL going-concern risk was public before TOP entry and is not assigned a RAAS grade",()=>{
 const f=engine.parseHistoricalFinance(raw,top,bottom);
 const mdgl=engine.financeForCase(f,"mdgl-resmetirom-maestro-nash-pre2022-illustrative");
 assert.equal(mdgl.publishedAt,"2022-11-03");
 assert.equal(mdgl.riskDisclosure.risk,"GOING_CONCERN_SUBSTANTIAL_DOUBT");
 assert.equal(mdgl.riskDisclosure.asOf,"2022-09-30");
 assert.equal(mdgl.riskDisclosure.publishedAt,"2022-11-03");
 assert.match(mdgl.riskDisclosure.sourceUrl,/sec.gov\/Archives\/edgar/);
 assert.match(mdgl.riskDisclosure.summary,/substantial doubt/i);
 assert.match(mdgl.riskDisclosure.caveat,/not mean bankruptcy/i);
 const summary=engine.financeReadiness(f,mdgl.caseId,mdgl.stage);
 assert.equal(summary.usableInApprovedRAAS,false);
 assert.equal(summary.cashRunwayCalculated,false);
 const page=fs.readFileSync(path.join(__dirname,"../app/raas-history/page.tsx"),"utf8");
 assert.match(page,/data-historical-preentry-risk/);
 assert.match(page,/finances.riskDisclosure.publishedAt/);
 assert.match(page,/going-concern substantial doubt/i);
});
test("A retrospective financing-risk flag cannot be backfilled using a future filing",()=>{
 const edit=(riskPatch)=>({...raw,records:raw.records.map(r=>r.id==="mdgl-2022-top"?
  {...r,riskDisclosure:{...r.riskDisclosure,...riskPatch}}:r)});
 for(const invalid of [
  {publishedAt:"2022-11-21"},
  {publishedAt:"2026-11-02"},
  {sourceUrl:""},
  {risk:"GOING_CONCERN_RESOLVED"},
  {summary:""},
  {asOf:"2022-12-01"}
 ]){
  assert.throws(()=>engine.parseHistoricalFinance(edit(invalid),top,bottom),
   /RAAS_FINANCE_RISK_TIME_OR_SOURCE_INVALID/);
 }
});
test("Conditional loans, offering proceeds and ATM headroom are not counted twice as cash",()=>{
 const f=engine.parseHistoricalFinance(raw,top,bottom);
 const geron=engine.financeReadiness(f,"gern-imetelstat-mds-2024-illustrative","post");
 assert.equal(geron.cashAmountUsdMillions,465);
 const mdgl=engine.financeReadiness(f,"mdgl-resmetirom-nash-2023-2024-illustrative","post");
 assert.equal(mdgl.cashAmountUsdMillions,298.418);
 const vrna=engine.financeReadiness(f,"vrna-ensifentrine-copd-2024-illustrative","post");
 assert.equal(vrna.cashAmountUsdMillions,254.882);
 assert.ok(vrna.issues.some(x=>/fully diluted valuation/i.test(x)));
 const bbio=engine.financeReadiness(f,"bbio-acoramidis-attrcm-2024-illustrative","post");
 assert.equal(bbio.cashAmountUsdMillions,519.8);
});
test("Later financing, wrong case, repeated cash class, and invalid amounts are rejected",()=>{
 const f=(change)=>({...raw,records:raw.records.map((r,i)=>i===0?{...r,...change}:r)});
 assert.throws(()=>engine.parseHistoricalFinance(f({publishedAt:"2022-12-31"}),top,bottom),/RAAS_FINANCE_ROW_INVALID/);
 assert.throws(()=>engine.parseHistoricalFinance(f({caseId:"unknown-case"}),top,bottom),/RAAS_FINANCE_ROW_INVALID/);
 const futureQ3={...raw,records:raw.records.map(r=>r.id==="mdgl-2023-bottom"?
  {...r,publishedAt:"2023-11-06",asOf:"2023-09-30"}:r)};
 assert.throws(()=>engine.parseHistoricalFinance(futureQ3,top,bottom),/RAAS_FINANCE_ROW_INVALID/);
 const first=raw.records[0];
 assert.throws(()=>engine.parseHistoricalFinance(f({facts:[...first.facts,{type:"CASH_UNRESTRICTED",valueUsdMillions:5,method:"duplicate",caveat:"not valid"}]}),top,bottom),/RAAS_FINANCE_CASH_DOUBLE_COUNT/);
 assert.throws(()=>engine.parseHistoricalFinance(f({facts:first.facts.map((v,i)=>i===0?{...v,valueUsdMillions:-2}:v)}),top,bottom),/RAAS_FINANCE_FACT_INVALID/);
});
test("Hypothetical friction and price shocks calculate deterministically, without historical prediction claims",()=>{
 const r=engine.researchCostReplay(10,14,50,-20);
 assert.equal(r.observedGrossPercent,40);
 assert.equal(r.hypotheticalCostPercent,.5);
 assert.equal(r.hypotheticalAfterCostsPercent,39.5);
 assert.equal(r.hypotheticalShockExitPrice,8);
 assert.equal(r.hypotheticalShockReturnAfterCostsPercent,-20.5);
 assert.equal(r.hasOriginalPrediction,false);
 assert.equal(r.qualifiedForPredictiveAccuracy,false);
 assert.equal(engine.researchCostReplay(0,14,50,-20),null);
 assert.equal(engine.researchCostReplay(10,14,2100,-20),null);
 assert.equal(engine.researchCostReplay(10,14,50,-120),null);
});
test("Finance validator, historical audit page, and client simulation compile as TypeScript/TSX",()=>{
 for(const file of ["lib/raas-finance-reconciliation.ts","app/raas-history/page.tsx","app/raas-history/RaasHistoricalWhatIf.tsx"]){
  const code=fs.readFileSync(path.join(__dirname,"..",file),"utf8");
  const output=ts.transpileModule(code,{fileName:file,reportDiagnostics:true,
   compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}});
  assert.equal((output.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).length,0,file);
 }
});
