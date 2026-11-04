"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),Module=require("node:module"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const repo=path.resolve(root,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const historySource=read("lib/raas-trial-score-history.ts");
const ui=read("app/RaasTrialHistoryButton.tsx");
const table=read("app/Phase3ReadoutSheets.tsx");
const css=read("app/RaasTrialHistoryButton.module.css");
const workflow=fs.readFileSync(path.join(repo,".github/workflows/pdufa-nightly-scoring-then-repair.yml"),"utf8");
const capture=require(path.join(repo,"scripts/raas_trial_history_capture.cjs"));
const js=ts.transpileModule(historySource,{fileName:"raas-trial-score-history.ts",
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS},reportDiagnostics:true});
const m=new Module("raas-trial-score-history",module);m.filename="raas-trial-score-history.js";
m.paths=module.paths;m._compile(js.outputText,m.filename);
const history=m.exports;
const empty=()=>({schemaVersion:1,scope:"RAAS_TRIAL_SCORE_HISTORY",note:"Tests",records:[]});
const source=(stage,sourceId,metricId,drug="Drug X")=>({sourceAsOf:"2026-11-03",scope:"RAAS_RESEARCH",
 records:[{nctId:"NCT12345678",ticker:"ABCD",drug,indication:"Condition Y",stage,
 observations:[{id:sourceId,sourceUrl:"https://example.org/"+sourceId,metricIds:[metricId]}]}]});
const date1="2026-11-03T21:00:00.000Z",date2="2026-11-03T22:00:00.000Z";
test("saved history schema starts empty; no fictitious RAAS score",()=>{
 const d=JSON.parse(read("data/raas-trial-score-history.json"));
 assert.equal(d.records.length,0);
 assert.equal(history.parseRaasTrialHistory(d).records.length,0);
});
test("first saved evidence event is timestamped and not numeric",()=>{
 const candidates=capture.collectSourceCandidates([source("pre","a","pre-1-1")]);
 const result=capture.appendSourceCaptures(empty(),candidates,date1);
 assert.equal(result.added,1);
 const e=result.ledger.records[0];
 assert.equal(e.nctId,"NCT12345678");
 assert.equal(e.recordedAt,date1);assert.equal(e.sourceAsOf,"2026-11-03");
 assert.equal(e.stage,"pre");assert.equal(e.kind,"FIRST_CAPTURE");
 assert.equal(e.scoreKind,"UNSCORED");assert.equal(e.score,null);
 assert.equal(e.metricCoverage,1);
 history.parseRaasTrialHistory(result.ledger);
 const retry=capture.appendSourceCaptures(result.ledger,candidates,date2);
 assert.equal(retry.added,0);assert.deepEqual(retry.ledger.records,result.ledger.records);
});
test("post-readout transfer keeps prior TOP event under one identity, no re-score",()=>{
 const a=capture.collectSourceCandidates([source("pre","a","pre-1-1")]);
 const first=capture.appendSourceCaptures(empty(),a,date1);
 const b=capture.collectSourceCandidates([source("post","b","post-1-1")]);
 const after=capture.appendSourceCaptures(first.ledger,b,date2);
 assert.equal(after.added,1);
 assert.deepEqual(after.ledger.records.map(e=>e.stage),["pre","post"]);
 assert.equal(after.ledger.records[1].kind,"STAGE_ADDED");
 const linked=history.historyForTrial(history.parseRaasTrialHistory(after.ledger),{
  nctId:"NCT12345678",ticker:"ABCD",drug:"Drug X",indication:"Condition Y"
 });
 assert.equal(linked.length,2);
 assert.deepEqual(linked.map(e=>e.stage),["pre","post"]);
 assert.equal(history.currentHistoryScore(linked,"post"),null);
 assert.equal(history.currentHistoryScore(linked,"pre"),null);
});
test("ticker changes may preserve exact trial; different therapy never merges",()=>{
 const a=capture.appendSourceCaptures(empty(),capture.collectSourceCandidates([source("pre","a","pre-1-1")]),date1);
 assert.equal(history.historyForTrial(a.ledger,{nctId:"NCT12345678",ticker:"NEW",
  drug:"Drug X",indication:"Condition Y"}).length,1);
 assert.equal(history.historyForTrial(a.ledger,{nctId:"NCT12345678",ticker:"ABCD",
  drug:"Drug Z",indication:"Condition Y"}).length,0);
 assert.equal(history.historyForTrial(a.ledger,{nctId:"NCT87654321",ticker:"ABCD",
  drug:"Drug X",indication:"Condition Y"}).length,0);
});
test("source updates append, never overwrite earlier fingerprints",()=>{
 const a=capture.appendSourceCaptures(empty(),capture.collectSourceCandidates([source("pre","a","pre-1-1")]),date1);
 const next=capture.collectSourceCandidates([source("pre","new","pre-4-1")]);
 const b=capture.appendSourceCaptures(a.ledger,next,date2);
 assert.equal(b.added,1);assert.equal(b.ledger.records.length,2);
 assert.equal(b.ledger.records[1].kind,"EVIDENCE_UPDATED");
 assert.equal(b.ledger.records[0].summary,a.ledger.records[0].summary);
 assert.notEqual(b.ledger.records[0].evidenceFingerprint,b.ledger.records[1].evidenceFingerprint);
});
test("numerical score history is strictly stage+model+kind comparable",()=>{
 const base=capture.appendSourceCaptures(empty(),capture.collectSourceCandidates([source("pre","a","pre-1-1")]),date1).ledger;
 const proto=base.records[0];
 const scored=(id,stage,kind,version,score,t)=>({...proto,
  eventId:id,stage,kind:"SCORE_UPDATED",scoreKind:kind,score,scoreVersion:version,recordedAt:t,
  metricIds:[stage+"-1-1"],metricCoverage:1});
 const list=[...base.records,
  scored("a","pre","PROVISIONAL","v1",70,"2026-11-03T22:01:00.000Z"),
  scored("b","pre","PROVISIONAL","v1",73,"2026-11-03T22:02:00.000Z"),
  scored("c","post","PROVISIONAL","v1",91,"2026-11-03T22:03:00.000Z"),
  scored("d","post","PROVISIONAL","v2",80,"2026-11-03T22:04:00.000Z")];
 const l=history.parseRaasTrialHistory({...base,records:list});
 const hist=history.historyForTrial(l,{nctId:"NCT12345678",ticker:"ABCD",
   drug:"Drug X",indication:"Condition Y"});
 assert.equal(history.comparableScoreDelta(hist,list[2]),3);
 assert.equal(history.comparableScoreDelta(hist,list[3]),null);
 assert.equal(history.comparableScoreDelta(hist,list[4]),null);
 assert.equal(history.currentHistoryScore(hist,"pre")?.score,73);
 assert.equal(history.currentHistoryScore(hist,"post")?.score,80);
});
test("invalid or look-ahead snapshots fail validation",()=>{
 const b=capture.appendSourceCaptures(empty(),capture.collectSourceCandidates([source("pre","a","pre-1-1")]),date1).ledger;
 assert.throws(()=>history.parseRaasTrialHistory({...b,records:[{...b.records[0],score:0}]}),/INVALID/);
 assert.throws(()=>history.parseRaasTrialHistory({...b,records:[{...b.records[0],sourceAsOf:"2026-11-04"}]}),/INVALID/);
});
test("all TOP and BOTTOM rows receive the same history control; overlay opens right",()=>{
 assert.match(table,/import RaasTrialHistoryButton from "\.\/RaasTrialHistoryButton"/);
 assert.equal(table.split("<RaasTrialHistoryButton row={row} bucket={bucket}/>").length-1,1);
 assert.match(ui,/historyForTrial\(ledger,\{nctId:row\.nctId/);
 assert.match(ui,/data-raas-unified-history=\{row\.nctId\}/);
 assert.match(ui,/stageName\(e\.stage\)/);
 assert.match(ui,/aria-expanded=\{open\}/);
 assert.match(ui,/createPortal\(/);
 assert.match(css,/\.expanded\{display:flex;min-width:760px/);
 assert.match(css,/\.left\{flex:0 0 185px/);
 assert.match(css,/\.right\{flex:1/);
 assert.match(workflow,/node scripts\/raas_trial_history_capture\.cjs/);
 assert.match(workflow,/git add data\/nightly_scoring_audit\.json new-platform\/frontend\/data\/raas-trial-score-history\.json/);
});
test("new TSX history control parses without syntax diagnostics",()=>{
 for(const [source,name] of [[ui,"RaasTrialHistoryButton.tsx"],[table,"Phase3ReadoutSheets.tsx"]]){
  const result=ts.transpileModule(source,{fileName:name,reportDiagnostics:true,
   compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}});
  assert.deepEqual((result.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error)
   .map(d=>ts.flattenDiagnosticMessageText(d.messageText," ")),[]);
 }
});
