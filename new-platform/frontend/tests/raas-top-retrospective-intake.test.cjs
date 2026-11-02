"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(module,filename)=>{
 const source=fs.readFileSync(filename,"utf8");
 const output=ts.transpileModule(source,{
  fileName:filename,reportDiagnostics:true,
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
 }).outputText;
 module._compile(output,filename);
};
const stage=require("../lib/raas-top-retrospective-intake.ts");
const source=require("../data/raas-retrospective-top-cases.json");
test("historical TOP pre-readout GERN window is sourced, stage separated, and never called a forecast",()=>{
 const feed=stage.parseTopRetrospective(source);
 assert.equal(feed.records.length,2);
 const record=feed.records[0];
 assert.equal(record.ticker,"GERN");
 assert.deepEqual(record.nctIds,["NCT02598661"]);
 assert.equal(record.priorGuidanceDate,"2022-11-03");
 assert.equal(record.entryDecisionArchiveAvailable,false);
 assert.equal(record.eventQuality.eligibleForValidatedRAAS,false);
 assert.equal(record.publicReadoutDate,"2023-01-04");
 const out=stage.topRetrospectiveResults(feed)[0];
 assert.equal(out.entryClose,2.26);
 assert.equal(out.exitClose,2.42);
 assert.equal(out.observedGrossChangePercent,7.08);
 assert.equal(out.marketCapUsdMillions,861.591);
 assert.equal(out.forecastScore,null);
 assert.equal(out.forecastError,null);
 const mdgl=stage.topRetrospectiveResults(feed).find(x=>x.ticker==="MDGL");
 assert.ok(mdgl);
 assert.equal(mdgl.entryClose,72.8);
 assert.equal(mdgl.exitClose,63.8);
 assert.equal(mdgl.marketCapUsdMillions,1245);
 assert.equal(mdgl.observedGrossChangePercent,-12.36);
 assert.equal(mdgl.readoutDate,"2022-12-19");
 assert.equal(mdgl.forecastScore,null);
 assert.equal(mdgl.forecastError,null);

});
test("TOP research examples cannot cross trial readout or borrow later sponsor guidance",()=>{
 const base=source.records[0];
 const changed=(extra)=>({...source,records:[{...base,...extra}]});
 assert.throws(()=>stage.parseTopRetrospective(changed({
  priorGuidanceDate:"2023-01-05"
 })),/RAAS_TOP_HISTORY_WINDOW_INVALID/);
 assert.throws(()=>stage.parseTopRetrospective(changed({
  exit:{...base.exit,date:"2023-01-06"}
 })),/RAAS_TOP_HISTORY_WINDOW_INVALID/);
 assert.throws(()=>stage.parseTopRetrospective(changed({
  entryDecisionArchiveAvailable:true
 })),/RAAS_TOP_HISTORY_IDENTITY_INVALID/);
 assert.throws(()=>stage.parseTopRetrospective(changed({
  marketCapAtEntry:{...base.marketCapAtEntry,usdMillions:10001}
 })),/RAAS_TOP_HISTORY_MARKET_CAP_INVALID/);
});
test("TOP and BOTTOM retrospective ledgers cannot enter actual RAAS predictive-performance registry",()=>{
 const official=require("../data/raas-historical-cases.json");
 const scores=require("../data/raas-reviewed-snapshots.json");
 assert.equal(official.cases.length,0);
 assert.equal(scores.records.length,0);
});
test("TOP parser and TSX disclosure parse without syntax errors",()=>{
 const root=path.resolve(__dirname,"..");
 for(const p of ["lib/raas-top-retrospective-intake.ts","app/TrialRaasDisclosure.tsx"]){
  const result=ts.transpileModule(fs.readFileSync(path.join(root,p),"utf8"),{
   fileName:p,reportDiagnostics:true,compilerOptions:{
    target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,jsx:ts.JsxEmit.ReactJSX
   }
  });
  assert.equal((result.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).length,0,p);
 }
});
