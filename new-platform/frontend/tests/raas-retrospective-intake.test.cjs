"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(module,filename)=>{
 const js=ts.transpileModule(fs.readFileSync(filename,"utf8"),{
  fileName:filename,reportDiagnostics:true,
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
 }).outputText;
 module._compile(js,filename);
};
const intake=require("../lib/raas-retrospective-intake.ts");
const raw=require("../data/raas-retrospective-source-cases.json");
test("three independently sourced historical post-Phase3 windows are NOT treated as predictions",()=>{
 const feed=intake.parseRetrospectiveFeed(raw);
 assert.equal(feed.records.length,5);
 const record=feed.records[0];
 assert.equal(record.ticker,"VRNA");
 assert.equal(record.stage,"post");
 assert.deepEqual(record.nctIds,["NCT04535986","NCT04542057"]);
 assert.equal(record.entryDecisionArchiveAvailable,false);
 assert.equal(record.eventQuality.eligibleForValidatedRAAS,false);
 assert.equal(record.eventQuality.priceCorporateActionChecked,false);
 assert.equal(record.entry.close,14.85);
 assert.equal(record.exit.close,15);
 assert.equal(record.pdufaDate,"2024-06-26");
 assert.equal(record.marketCapAtEntry.usdMillions,1204);
 assert.ok(record.verifiedBeforeEntry.every(e=>e.date<=record.entry.date));
 const outcomes=intake.retrospectiveResults(feed);
 assert.equal(outcomes.length,5);
 assert.equal(outcomes[0].observedGrossChangePercent,1.01);
 assert.equal(outcomes[0].calendarCutoff,"2024-06-23");
 assert.equal(outcomes[0].status,"RESEARCH_ONLY_NOT_CALIBRATED");
 assert.equal(outcomes[0].forecastScore,null);
 assert.equal(outcomes[0].forecastError,null);
 const urgn=outcomes.find(o=>o.ticker==="URGN");
 assert.ok(urgn);
 assert.equal(urgn.observedGrossChangePercent,-33.42);
 assert.equal(urgn.calendarCutoff,"2025-06-10");
 assert.equal(urgn.marketCapUsdMillions,510.264);
 assert.equal(urgn.forecastScore,null);
 assert.equal(urgn.forecastError,null);
 assert.notEqual(urgn.programKey,outcomes[0].programKey);
 const gern=outcomes.find(o=>o.ticker==="GERN");
 assert.ok(gern);
 assert.equal(gern.observedGrossChangePercent,-9.67);
 assert.equal(gern.calendarCutoff,"2024-06-13");
 assert.equal(gern.marketCapUsdMillions,2331);
 assert.notEqual(gern.programKey,urgn.programKey);
 assert.equal(feed.records.find(r=>r.ticker==="GERN").realizedFDAAction.date,"2024-06-06");
 assert.ok(gern.exitDate<feed.records.find(r=>r.ticker==="GERN").realizedFDAAction.date);
 const mdgl=outcomes.find(o=>o.ticker==="MDGL");
 assert.ok(mdgl);
 assert.equal(mdgl.entryClose,146.89);
 assert.equal(mdgl.exitClose,255.32);
 assert.equal(mdgl.marketCapUsdMillions,2900);
 assert.equal(mdgl.observedGrossChangePercent,73.82);
 assert.equal(mdgl.calendarCutoff,"2024-03-11");
 assert.equal(mdgl.forecastScore,null);
 assert.equal(mdgl.forecastError,null);
 assert.equal(new Set(outcomes.map(x=>x.programKey)).size,5);
 const bbio=outcomes.find(x=>x.ticker==="BBIO");
 assert.ok(bbio);
 assert.equal(bbio.entryClose,29.1);
 assert.equal(bbio.exitClose,23.72);
 assert.equal(bbio.observedGrossChangePercent,-18.49);
 assert.equal(bbio.marketCapUsdMillions,5208);
 assert.equal(bbio.calendarCutoff,"2024-11-26");
 assert.equal(feed.records.find(r=>r.ticker==="BBIO").realizedFDAAction.date,"2024-11-22");
 assert.ok(bbio.exitDate<feed.records.find(r=>r.ticker==="BBIO").realizedFDAAction.date);
 assert.equal(bbio.forecastScore,null);

 const trial=feed.records.find(x=>x.ticker==="MDGL");
 assert.equal(trial.clinicalReadouts.length,2);
 assert.equal(intake.observedClinicalRateDifference(trial.clinicalReadouts[0]),20);
 assert.equal(intake.observedClinicalRateDifference(trial.clinicalReadouts[1]),12);
 assert.ok(trial.clinicalReadouts.every(x=>x.reportedAt<trial.entry.date));


});
test("research-only feed can never masquerade as pre-committed trade predictions or validated RAAS",()=>{
 const mutate=(changes)=>({...raw,records:[{...raw.records[0],...changes}]});
 assert.throws(()=>intake.parseRetrospectiveFeed(mutate({
  entryDecisionArchiveAvailable:true
 })),/RAAS_RETROSPECTIVE_IDENTITY_INVALID/);
 assert.throws(()=>intake.parseRetrospectiveFeed(mutate({
  eventQuality:{...raw.records[0].eventQuality,eligibleForValidatedRAAS:true}
 })),/RAAS_RETROSPECTIVE_IDENTITY_INVALID/);
 assert.throws(()=>intake.parseRetrospectiveFeed(mutate({
  entry:{...raw.records[0].entry,date:"2024-05-11"}
 })),/RAAS_RETROSPECTIVE_PRICE_INVALID/);
});
test("impossible cutoff, post-entry source and incorrect historical market cap are rejected",()=>{
 const base=raw.records[0];
 const mutate=(changes)=>({...raw,records:[{...base,...changes}]});
 assert.throws(()=>intake.parseRetrospectiveFeed(mutate({
  exit:{...base.exit,date:"2024-06-24"}
 })),/RAAS_RETROSPECTIVE_WINDOW_INVALID/);
 assert.throws(()=>intake.parseRetrospectiveFeed(mutate({
  verifiedBeforeEntry:[...base.verifiedBeforeEntry,{kind:"PHASE3_PUBLIC_READOUT",date:"2024-05-14",sourceUrl:"https://example.org/later",notes:"Late"}]
 })),/RAAS_RETROSPECTIVE_SOURCE_INVALID/);
 assert.throws(()=>intake.parseRetrospectiveFeed(mutate({
  exit:{...base.exit,date:"2024-06-26"}
 })),/RAAS_RETROSPECTIVE_WINDOW_INVALID/);
 assert.throws(()=>intake.parseRetrospectiveFeed(mutate({
  marketCapAtEntry:{...base.marketCapAtEntry,usdMillions:10001}
 })),/RAAS_RETROSPECTIVE_MARKET_CAP_INVALID/);
});
test("late or invalid historical efficacy is rejected rather than backfilled",()=>{
 const base=raw.records.find(r=>r.ticker==="MDGL");
 const amended={...base,clinicalReadouts:[{...base.clinicalReadouts[0],reportedAt:"2024-04-01"}]};
 assert.throws(()=>intake.parseRetrospectiveFeed({...raw,records:raw.records.map(r=>r.id===base.id?amended:r)}),/RAAS_RETROSPECTIVE_CLINICAL_INVALID/);
 const invalid={...base,clinicalReadouts:[{...base.clinicalReadouts[0],activeRatePct:105}]};
 assert.throws(()=>intake.parseRetrospectiveFeed({...raw,records:raw.records.map(r=>r.id===base.id?invalid:r)}),/RAAS_RETROSPECTIVE_CLINICAL_INVALID/);
});
test("research intake can coexist with zero approved historical RAAS outcomes",()=>{
 const actualHistorical=require("../data/raas-historical-cases.json");
 const approved=require("../data/raas-approved-calibrations.json");
 const reviewed=require("../data/raas-reviewed-snapshots.json");
 assert.equal(actualHistorical.cases.length,0);
 assert.equal(approved.entries.length,0);
 assert.equal(reviewed.records.length,0);
});
test("validator and RAAS disclosure TSX parse without errors",()=>{
 const root=path.resolve(__dirname,"..");
 for(const file of ["lib/raas-retrospective-intake.ts","app/TrialRaasDisclosure.tsx"]){
  const result=ts.transpileModule(fs.readFileSync(path.join(root,file),"utf8"),{
   fileName:file,reportDiagnostics:true,
   compilerOptions:{module:ts.ModuleKind.ESNext,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}
  });
  assert.deepEqual((result.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error)
   .map(d=>ts.flattenDiagnosticMessageText(d.messageText," ")),[],file);
 }
});
