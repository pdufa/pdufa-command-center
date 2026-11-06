"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),Module=require("node:module"),ts=require("typescript");
const frontend=path.resolve(__dirname,".."),repo=path.resolve(frontend,"../..");
const read=p=>fs.readFileSync(path.join(frontend,p),"utf8");
const get=n=>JSON.parse(read("data/"+n));
const emptyHistory=()=>({...get("raas-trial-score-history.json"),records:[]});
const score=require(path.join(repo,"scripts/raas_trial_provisional_metric_capture.cjs"));
const historySource=read("lib/raas-trial-score-history.ts");
const out=ts.transpileModule(historySource,{fileName:"raas-trial-score-history.ts",reportDiagnostics:true,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}});
const m=new Module("history-test",module);m.filename="raas-trial-score-history.js";m.paths=module.paths;
m._compile(out.outputText,m.filename);
const history=m.exports;
const candidates=()=>score.deriveCandidates(get("raas-pilot-observations.json"),
 get("raas-prospective-source-baselines.json"));
const time1="2026-11-04T05:20:00.000Z",time2="2026-11-04T05:21:00.000Z";
test("persisted RAAS history retains real source captures and experimental grades",()=>{
 const ledger=history.parseRaasTrialHistory(get("raas-trial-score-history.json"));
 assert.ok(ledger.records.length>=7);
 assert.ok(ledger.records.filter(x=>x.kind==="METRIC_SCORE_UPDATED").length>=2);
 assert.ok(ledger.records.every(x=>x.score===null&&x.scoreKind==="UNSCORED"));
});
test("two TOP trial timing-only grades are calculated from actual saved research, not arbitrary overall RAAS",()=>{
 const c=candidates();
 assert.equal(c.length,2);
 assert.deepEqual(c.map(x=>[x.ticker,x.nctId,x.score,x.inputs]),[
  ["LBRX","NCT07363577",50,"First half of 2027"],
  ["TRVI","NCT07671911",50,"first half of 2028"]
 ]);
 assert.ok(c.every(x=>x.stage==="pre"&&x.sourceDate<=
   get("raas-pilot-observations.json").sourceAsOf));
 assert.equal(c.some(x=>["MLTX","CLDX"].includes(x.ticker)),false);
});
test("first-sentence parser excludes another trial's OCEAN-2 timing",()=>{
 const source=get("raas-prospective-source-baselines.json");
 const fact=source.records.find(x=>x.ticker==="TRVI").observations.find(x=>x.id==="trvi-ocean1-readout-guidance");
 assert.equal(score.windowFromSource(fact.valueText),"first half of 2028");
 assert.equal(score.timingGrade("first half of 2028"),50);
 assert.equal(score.windowFromSource("Readout in Q1 2027 and Q2 2027"),null);
 assert.equal(score.timingGrade("Unspecified 2027"),null);
});
test("history stores 1/30 experimental metric scores without overall composite",()=>{
 const initial=emptyHistory();
 const a=score.appendProvisionalMetricEvents(initial,candidates(),time1,"2026-11-02");
 assert.equal(a.added,2);
 const h=history.parseRaasTrialHistory(a.ledger);
 assert.equal(h.records.length,initial.records.length+2);
 assert.equal(h.records.filter(x=>x.kind==="METRIC_SCORE_UPDATED").length,2);
 for(const r of h.records){
  assert.equal(r.scoreKind,"UNSCORED");
  assert.equal(r.score,null);
  assert.equal(r.scoreVersion,null);
  assert.equal(r.metricGrades.length,1);
  assert.equal(r.metricGrades[0].score,50);
  assert.equal(r.metricGrades[0].metricId,"pre-4-1");
  assert.equal(r.recordedAt,time1);
  assert.equal(r.sourceAsOf,"2026-11-02");
  const linked=history.historyForTrial(h,{nctId:r.nctId,ticker:r.ticker,
   drug:r.drug,indication:r.indication});
  assert.equal(history.currentHistoryScore(linked,"pre"),null);
  assert.equal(history.currentResearchMetricGrade(linked,"pre","pre-4-1")?.grade.score,50);
 }
});
test("same facts do not append duplicate ratings; new source timing appends",()=>{
 const initial=emptyHistory();
 const a=score.appendProvisionalMetricEvents(initial,candidates(),time1,"2026-11-02");
 const b=score.appendProvisionalMetricEvents(a.ledger,candidates(),time2,"2026-11-02");
 assert.equal(b.added,0);
 assert.deepEqual(b.ledger.records,a.ledger.records);
 const changed=candidates().map(x=>x.ticker==="LBRX"?{...x,inputs:"Q2 2027",score:75}:x);
 const c=score.appendProvisionalMetricEvents(b.ledger,changed,time2,"2026-11-02");
 assert.equal(c.added,1);
 assert.equal(c.ledger.records.at(-1).metricGrades[0].score,75);
 assert.equal(history.parseRaasTrialHistory(c.ledger).records.length,3);
});
test("malformed metric events cannot be mistaken for validated overall scores",()=>{
 const a=score.appendProvisionalMetricEvents(emptyHistory(),candidates(),time1,"2026-11-02");
 const ev=a.ledger.records[0];
 for(const patch of [{score:50},{scoreKind:"VALIDATED"},{metricGrades:[]},
  {metricGrades:[{...ev.metricGrades[0],sourceDate:"2027-01-01"}]}]){
  assert.throws(()=>history.parseRaasTrialHistory({...a.ledger,records:[{...ev,...patch},a.ledger.records[1]]}),/INVALID/);
 }
});
test("nightly source audit remains idempotent after metric grade was appended",()=>{
 const sources=require(path.join(repo,"scripts/raas_trial_history_capture.cjs"));
 const readout=sources.collectSourceCandidates([get("raas-pilot-observations.json"),
  get("raas-prospective-source-baselines.json")]);
 const sourceHistory=sources.appendSourceCaptures(emptyHistory(),
  readout,time1).ledger;
 const grades=score.appendProvisionalMetricEvents(sourceHistory,candidates(),
  time2,"2026-11-02").ledger;
 const reread=sources.appendSourceCaptures(grades,readout,"2026-11-04T05:22:00.000Z");
 assert.equal(reread.added,0);
 assert.deepEqual(reread.ledger.records,grades.records);
 history.parseRaasTrialHistory(reread.ledger);
});
test("legacy pilot score UI is historically preserved while nightly scoring capture remains cancelled",()=>{
 const scoreSource=read("lib/raas-provisional-trial-scores.ts");
 const summary=read("app/TrialRaasDisclosure.tsx");
 const button=read("app/RaasTrialHistoryButton.tsx");
 const workflow=fs.readFileSync(path.join(repo,".github/workflows/pdufa-nightly-scoring-then-repair.yml"),"utf8");
 assert.match(scoreSource,/overallScore:null/);
 assert.match(scoreSource,/provisionalTimingSpecificity/);
 assert.match(scoreSource,/firstSentenceReadoutWindow/);
 assert.match(summary,/data-raas-provisional-component/);
 assert.match(button,/data-raas-current-provisional-metric/);
 assert.match(button,/Overall RAAS remains —\/100/);
 assert.match(workflow,/Surveys and ratings cancelled/);
 assert.doesNotMatch(workflow,/node scripts\/raas_trial_provisional_metric_capture\.cjs/);
 for(const [source,name] of [[scoreSource,"raas-provisional-trial-scores.ts"],
  [summary,"TrialRaasDisclosure.tsx"],[button,"RaasTrialHistoryButton.tsx"]]){
  const result=ts.transpileModule(source,{fileName:name,reportDiagnostics:true,
   compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}});
  assert.deepEqual((result.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).map(d=>d.code),[]);
 }
});
