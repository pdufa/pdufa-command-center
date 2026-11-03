"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
 module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}
 ).outputText,file);
const primary=require("../data/raas-active-2024-2025-primary-source-leads.json");
const earlier=require("../data/raas-active-2024-2025-preentry-sec-share-leads.json");
const later=require("../data/raas-active-2024-2025-sec-cover-share-leads.json");
const {activePdufaGoalAsOfAudit}=require("../lib/raas-pdufa-goal-asof-metric-audit.ts");
const {activeSECAsOfEntryShares,auditSECAsOfEntryShares}=
 require("../lib/raas-historical-sec-entry-bridge.ts");
const {csv}=require("../scripts/raas-historical-sec-entry-bridge.cjs");
const clone=x=>structuredClone(x);
const run=(p=primary,a=earlier,b=later,g=activePdufaGoalAsOfAudit())=>
 auditSECAsOfEntryShares(p,a,b,g);

test("All nine original 2024/25 source records have a dated SEC source, but zero verified caps or adjusted price returns",()=>{
 const x=activeSECAsOfEntryShares();
 assert.equal(x.scope,"RAAS_2024_2025_SEC_SHARES_ASOF_T79_SESSION_RESEARCH");
 assert.equal(x.caseCount,9);
 assert.equal(x.coverFactsPublicAtProposedEntry,9);
 assert.equal(x.coverFactsMissingAtProposedEntry,0);
 assert.equal(x.laterSnapshotsUnavailableAtEntry,8);
 assert.equal(x.independentlyValidatedEntryMarketCaps,0);
 assert.equal(x.independentlyVerifiedPricePairs,0);
 assert.equal(x.calibratedRaasScores,0);
 for(const r of x.rows){
  assert.ok(r.currentSECSourceUrl?.startsWith("https://www.sec.gov/Archives/"));
  assert.ok(r.currentSECFirstConservativeUse<=r.proposedEntrySession);
  assert.ok(r.currentSECDisclosureAgeDays>=0);
  assert.equal(r.underlyingSharesContinuousVerified,false);
  assert.equal(r.corporateActionsVerified,false);
  assert.equal(r.entryMarketCapUsdMillions,null);
  assert.equal(r.entryMarketCap300Mto10BValidated,false);
  assert.equal(r.adjustedHistoricalReturnPct,null);
  assert.equal(r.validatedRaasScore,null);
 }
 assert.equal(x.rows.find(r=>r.ticker==="AXSM").currentSECShares,48462376);
 assert.equal(x.rows.find(r=>r.ticker==="GERN").proposedEntrySession,"2024-04-01");
 assert.equal(x.rows.find(r=>r.ticker==="ARQT").currentSECShares,96813363);
 assert.equal(x.rows.find(r=>r.ticker==="SLNO").currentSECShares,43117432);
});
test("A SEC filing first public AFTER T-79 cannot backfill original entry shares",()=>{
 const a=clone(earlier),b=clone(later);
 b.records.find(r=>r.ticker==="AXSM").firstConservativeEntryDate="2024-11-14";
 const r=run(clone(primary),a,b).rows.find(r=>r.ticker==="AXSM");
 assert.equal(r.currentSECShares,48000205);
 assert.equal(r.laterCoverWasNotYetPublicAtEntry,true);
 assert.equal(r.currentSECSourceUrl,a.records.find(z=>z.ticker==="AXSM").sourceUrl);
 assert.equal(r.entryMarketCapUsdMillions,null);
});
test("Case identity, SEC source chronology and unsafe share count must fail closed",()=>{
 const candidates=[
  ()=>{const a=clone(earlier);a.records[0].sharesOutstanding=-50;return [primary,a,later]},
  ()=>{const a=clone(earlier);a.records[0].sourceUrl="https://evil.invalid/forged";return [primary,a,later]},
  ()=>{const a=clone(earlier);a.records[0].cik="0000000000";return [primary,a,later]},
  ()=>{const a=clone(earlier);a.records[1].caseId=a.records[0].caseId;return [primary,a,later]},
  ()=>{const p=clone(primary);p.records[0].ticker="OTHER";return [p,earlier,later]},
  ()=>{const b=clone(later);b.records[0].filedDate="2023-01-01";return [primary,earlier,b]},
 ];
 for(const fn of candidates){
  const args=fn();assert.throws(()=>run(...args),/RAAS_SEC_ASOF_/);
 }
});
test("No original FDA action or postdecision label leaks into this source-time bridge",()=>{
 const s=JSON.stringify(activeSECAsOfEntryShares());
 assert.doesNotMatch(s,/actualFDAOutcome|actualFDAActionDate|APPROVED|COMPLETE_RESPONSE_LETTER/);
 const c=csv(activeSECAsOfEntryShares());
 assert.equal(c.trim().split("\n").length,10);
 assert.match(c,/AXSM/);
 assert.match(c,/currentSECShares/);
 assert.doesNotMatch(c,/APPROVED|CRL/);
});
test("Mobile worklist shows individual SEC as-of source links, missing cap/price and no fabricated score",()=>{
 const root=path.join(__dirname,"..");
 const c=fs.readFileSync(path.join(root,"app/raas-worklist/page.tsx"),"utf8");
 assert.match(c,/SECAsOfHistory/);
 assert.match(c,/data-raas-sec-entry-case/);
 assert.match(c,/currentSECShares/);
 assert.match(c,/market cap eligibility/i);
 assert.match(c,/independent adjusted/i);
 const file=fs.readFileSync(path.join(root,"lib/raas-historical-sec-entry-bridge.ts"),"utf8");
 for(const raw of [file,c]){
  const o=ts.transpileModule(raw,{reportDiagnostics:true,compilerOptions:{
   target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,jsx:ts.JsxEmit.ReactJSX}});
  assert.deepEqual((o.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error)
   .map(x=>ts.flattenDiagnosticMessageText(x.messageText," ")),[]);
 }
});
