"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const bridge=require("../lib/raas-share-bridge.ts");
const parseTop=require("../lib/raas-top-retrospective-intake.ts").parseTopRetrospective;
const parseBottom=require("../lib/raas-retrospective-intake.ts").parseRetrospectiveFeed;
const top=parseTop(require("../data/raas-retrospective-top-cases.json"));
const bottom=parseBottom(require("../data/raas-retrospective-source-cases.json"));
const raw=require("../data/raas-share-bridge-research.json");
test("All dated share counts from SEC cover filings precede vendor close; 5 arithmetical checks are NOT certified prices",()=>{
 const feed=bridge.parseShareBridge(raw,top,bottom);
 const summary=bridge.bridgeSummary(feed,top,bottom);
 assert.equal(feed.records.length,5);
 assert.equal(summary.caseCount,top.records.length+bottom.records.length);
 assert.equal(summary.withSecShareCount,5);
 assert.equal(summary.arithmeticMatches,5);
 assert.equal(summary.separatelyReportedCapMatches,4);
 assert.equal(summary.missingShares,summary.caseCount-5);
 assert.equal(summary.fullyVerifiedPriceCases,0);
 assert.equal(summary.qualifiedRaasForecasts,0);
 for(const r of feed.records){
  const b=bridge.bridgeForCase(feed,top,bottom,r.caseId);
  assert.equal(b.status,"ARITHMETIC_MATCH_REQUIRES_PRICE_AUDIT");
  assert.equal(b.approvedRaasScore,false);
  assert.equal(b.fullyDilutedReconciled,false);
  assert.equal(b.corporateActionsReconciled,false);
  assert.equal(b.entryPriceIndependentlyVerified,false);
  assert.ok(r.sharesSourceUrl.startsWith("https://www.sec.gov/"));
 }
});
test("BridgeBio May 2023 and Geron April 2024 SEC share-cover counts reproduce vendor capitalization close to reported value",()=>{
 const data=bridge.parseShareBridge(raw,top,bottom);
 const bbio=bridge.bridgeForCase(data,top,bottom,"bbio-attribute-cm-pre2023-illustrative");
 const gern=bridge.bridgeForCase(data,top,bottom,"gern-imetelstat-mds-2024-illustrative");
 assert.equal(bbio.quotedSharesEquivalent,160500999);
 assert.equal(gern.quotedSharesEquivalent,593132540);
 assert.ok(Math.abs(bbio.reconstructedEquityCapUsdMillions-2173.18)<.02);
 assert.equal(bbio.capComparisonBasis,"SAME_SHARES_RECONSTRUCTION");
 assert.equal(gern.capComparisonBasis,"VENDOR_REPORTED_CAP_ESTIMATE");
 assert.ok(Math.abs(gern.reconstructedEquityCapUsdMillions-2331.01)<.02);
});
test("2022 GERN and MDGL TOP entry cap arithmetic uses SEC Q3 cover counts known before November 18",()=>{
 const data=bridge.parseShareBridge(raw,top,bottom);
 const gern=bridge.bridgeForCase(data,top,bottom,"gern-imerge-mds-pre2023-illustrative");
 const mdgl=bridge.bridgeForCase(data,top,bottom,"mdgl-resmetirom-maestro-nash-pre2022-illustrative");
 assert.equal(gern.quotedSharesEquivalent,381235046);
 assert.equal(gern.shareCountAsOf,"2022-11-01");
 assert.equal(gern.sharePublishedAt,"2022-11-07");
 assert.equal(gern.observedEntryPrice,2.26);
 assert.ok(Math.abs(gern.reconstructedEquityCapUsdMillions-861.59)<.01);
 assert.equal(mdgl.quotedSharesEquivalent,17103395);
 assert.equal(mdgl.shareCountAsOf,"2022-11-01");
 assert.equal(mdgl.sharePublishedAt,"2022-11-03");
 assert.equal(mdgl.observedEntryPrice,72.8);
 assert.ok(Math.abs(mdgl.reconstructedEquityCapUsdMillions-1245.13)<.02);
 assert.equal(gern.capComparisonBasis,"VENDOR_REPORTED_CAP_ESTIMATE");
 assert.equal(mdgl.capComparisonBasis,"VENDOR_REPORTED_CAP_ESTIMATE");
 for(const audit of [gern,mdgl]){
  assert.equal(audit.status,"ARITHMETIC_MATCH_REQUIRES_PRICE_AUDIT");
  assert.equal(audit.entryPriceIndependentlyVerified,false);
  assert.equal(audit.fullyDilutedReconciled,false);
  assert.equal(audit.approvedRaasScore,false);
 }
});
test("2022 share-count evidence published after entry is rejected",()=>{
 const altered={...raw,records:raw.records.map(r=>r.caseId==="mdgl-resmetirom-maestro-nash-pre2022-illustrative"?
  {...r,sharesPublishedAt:"2022-11-21"}:r)};
 assert.throws(()=>bridge.parseShareBridge(altered,top,bottom),/RAAS_SHARE_BRIDGE_RECORD_INVALID/);
});
test("Verona ordinary shares are divided by eight to compare with USD ADS price, never multiplied by eight",()=>{
 const data=bridge.parseShareBridge(raw,top,bottom);
 const v=bridge.bridgeForCase(data,top,bottom,"vrna-ensifentrine-copd-2024-illustrative");
 assert.equal(v.quotedSharesEquivalent,648654174/8);
 assert.ok(Math.abs(v.reconstructedEquityCapUsdMillions-1204.06)<.02);
 assert.equal(v.sharePublishedAt,"2024-05-10");
 assert.equal(v.capComparisonBasis,"VENDOR_REPORTED_CAP_ESTIMATE");
});
test("No shares disclosed after entry, same-day post-close filing or mismatched ticker can pass",()=>{
 const edit=(caseId,changes)=>({...raw,records:raw.records.map(r=>r.caseId===caseId?{...r,...changes}:r)});
 const caseId="vrna-ensifentrine-copd-2024-illustrative";
 assert.throws(()=>bridge.parseShareBridge(edit(caseId,{sharesPublishedTimeEastern:"16:00:01"}),top,bottom),/SAME_DAY_TIMING_INVALID/);
 assert.throws(()=>bridge.parseShareBridge(edit(caseId,{sharesPublishedTimeEastern:undefined}),top,bottom),/SAME_DAY_TIMING_INVALID/);
 assert.throws(()=>bridge.parseShareBridge(edit(caseId,{sharesPublishedAt:"2024-05-11"}),top,bottom),/RECORD_INVALID/);
 assert.throws(()=>bridge.parseShareBridge(edit(caseId,{ordinarySharesPerQuotedSecurity:1}),top,bottom),/RECORD_INVALID/);
 assert.throws(()=>bridge.parseShareBridge(edit(caseId,{ticker:"GERN"}),top,bottom),/RECORD_INVALID/);
});
test("The SEC price-share bridge cannot make a false market cap match into a validated forecast",()=>{
 const copy={...raw,records:raw.records.filter(r=>r.ticker!=="GERN")};
 const p=bridge.parseShareBridge(copy,top,bottom);
 const s=bridge.bridgeSummary(p,top,bottom);
 assert.equal(s.withSecShareCount,3);
 assert.equal(s.qualifiedRaasForecasts,0);
 assert.equal(bridge.bridgeForCase(p,top,bottom,"gern-imetelstat-mds-2024-illustrative"),null);
});
test("New module and historical page TypeScript compile as syntax-checked TS/TSX",()=>{
 const root=path.resolve(__dirname,"..");
 for(const p of ["lib/raas-share-bridge.ts","app/raas-history/page.tsx"]){
  const ret=ts.transpileModule(fs.readFileSync(path.join(root,p),"utf8"),{
   fileName:p,reportDiagnostics:true,
   compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}});
  assert.equal((ret.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).length,0,p);
 }
});
