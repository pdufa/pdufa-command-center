"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(module,filename)=>{
 const source=fs.readFileSync(filename,"utf8");
 const out=ts.transpileModule(source,{fileName:filename,reportDiagnostics:true,
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText;
 module._compile(out,filename);
};
const engine=require("../lib/raas-score-engine.ts");
const specs=require("../lib/raas-metric-specs.ts");
const feed=engine.parseRaasPilotFeed(require("../data/raas-pilot-observations.json"));
test("clinical and company pilot facts are source-dated and exactly trial identified",()=>{
 assert.equal(feed.records.length,5);
 assert.equal(feed.records.flatMap(r=>r.observations).length,10);
 for(const row of feed.records){
  assert.match(row.nctId,/^NCT\d{8}$/);
  for(const item of row.observations){assert.match(item.sourceUrl,/^https:/);assert.ok(item.assessmentDate<=feed.sourceAsOf);}
 }
 assert.deepEqual(engine.observationsForTrial(feed,{
  nctId:"NCT06445023",ticker:"CLDX",drug:"wrong therapy",indication:"chronic spontaneous urticaria"
 },"post","2026-11-02"),[]);
 assert.deepEqual(engine.observationsForTrial(feed,{
  nctId:"NCT06445023",ticker:"CLDX",drug:"barzolvolimab",indication:"chronic spontaneous urticaria"
 },"pre","2026-11-02"),[]);
 assert.deepEqual(engine.observationsForTrial(feed,{
  nctId:"NCT06445023",ticker:"CLDX",drug:"barzolvolimab",indication:"chronic spontaneous urticaria"
 },"post","2026-09-01"),[]);
});
test("clinical measurements calculate correct placebo-adjusted changes without turning them into grades",()=>{
 const c1=feed.records.find(r=>r.nctId==="NCT06445023");
 const c2=feed.records.find(r=>r.nctId==="NCT06455202");
 assert.ok(c1&&c2);
 assert.equal(engine.observedCalculation(c1.observations[0]).value,9.5);
 assert.equal(engine.observedCalculation(c2.observations[0]).value,8.8);
 assert.equal(engine.observedCalculation(c1.observations[1]).value,33.1);
 const m=feed.records.find(r=>r.ticker==="MLTX");
 assert.ok(m);
 const calc=engine.observedCalculation(m.observations[0]);
 assert.equal(calc.value,42.1);
 assert.match(calc.label,/no comparator available/);
});
test("risk-adjusted grading refuses to invent any 0–100 score from incomplete evidence",()=>{
 for(const stage of ["pre","post"]){
  const result=engine.computeRaasScore({stage,snapshot:"CURRENT",asOf:"2026-11-02",
    trial:{nctId:"NCT06445023",ticker:"CLDX"},ratings:[],gates:[]});
  assert.equal(result.score,null);
  assert.equal(result.graded,0);
  assert.equal(result.missing.length,30);
  assert.equal(result.categories.length,6);
  assert.equal(result.categories.reduce((sum,c)=>sum+c.weight,0),100);
  assert.ok(result.categories.every(c=>c.score===null));
 }
});
test("all thirty complete, dated, verified ratings and passed gates are required",()=>{
 const stage="post",nctId="NCT06445023",ticker="CLDX";
 const metricIds=specs.RAAS_METRIC_CATALOG.post.flatMap(g=>g.metrics.map(m=>m.id));
 const ratings=metricIds.map(metricId=>({
  nctId,ticker,stage,snapshot:"CURRENT",metricId,score:75,
  assessedAt:"2026-11-02",sourceDate:"2026-10-31",
  sourceUrl:"https://example.org/verified-test-input",
  benchmarkId:"hypothetical-test-calibration",method:"Synthetic test only; do not persist to production.",
  evidenceId:"test-"+metricId,status:"VERIFIED"
 }));
 const args={stage,snapshot:"CURRENT",asOf:"2026-11-02",trial:{nctId,ticker},ratings,
  gates:[{name:"All eligibility",status:"PASSED"}]};
 const result=engine.computeRaasScore(args);
 assert.equal(result.score,75);
 assert.equal(result.graded,30);
 assert.ok(result.categories.every(c=>c.score===75));
 assert.equal(engine.computeRaasScore({...args,ratings:ratings.slice(1)}).score,null);
 assert.equal(engine.computeRaasScore({...args,gates:[]}).score,null);
 assert.equal(engine.computeRaasScore({...args,gates:[{name:"FDA window",status:"UNKNOWN"}]}).score,null);
 assert.equal(engine.computeRaasScore({...args,ratings:ratings.map((r,i)=>i===0?{...r,assessedAt:"2026-11-03"}:r)}).score,null);
 const zero=engine.computeRaasScore({...args,ratings:ratings.map((r,i)=>i===0?{...r,score:0}:r)});
 assert.equal(zero.graded,30);
 assert.ok(zero.score<75);
});
test("scenario math is deterministic and rejects unsourced or incoherent examples",()=>{
 const s={entryPrice:10,bearPrice:4,basePrice:11,bullPrice:18,
  bearProbability:.3,baseProbability:.45,bullProbability:.25,
  entryDate:"2026-10-01",exitDate:"2027-04-01",priceSourceDate:"2026-09-30",
  priceSourceUrl:"https://example.org/prices",scenarioSourceUrl:"https://example.org/scenarios",
  scenarioMethod:"Synthetic test, not investment forecast",calibrationId:"hypothetical-test-only"};
 const result=engine.calculateRaasReturn(s,"2026-11-02");
 assert.equal(result.upsidePercent,80);
 assert.equal(result.downsidePercent,60);
 assert.equal(result.probabilityWeightedReturnPercent,6.5);
 assert.equal(engine.calculateRaasReturn({...s,baseProbability:.25},"2026-11-02"),null);
 assert.equal(engine.calculateRaasReturn({...s,priceSourceUrl:"invalid"},"2026-11-02"),null);
 assert.equal(engine.calculateRaasReturn({...s,priceSourceDate:"2026-10-02"},"2026-11-02"),null);
});
test("source, engine and UI TSX transpile and use no fictional persisted score",()=>{
 const files=["lib/raas-metric-specs.ts","lib/raas-score-engine.ts","app/TrialRaasDisclosure.tsx"];
 for(const file of files){
  const source=fs.readFileSync(path.join(root,file),"utf8");
  const out=ts.transpileModule(source,{fileName:file,reportDiagnostics:true,
    compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
      jsx:ts.JsxEmit.ReactJSX}});
  const errors=(out.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error);
  assert.deepEqual(errors.map(d=>ts.flattenDiagnosticMessageText(d.messageText," ")),[],file);
 }
 const ui=fs.readFileSync(path.join(root,"app/TrialRaasDisclosure.tsx"),"utf8");
 assert.match(ui,/computeRaasScore\(/);
 assert.match(ui,/PilotEvidence/);
 assert.match(ui,/ratings:\[\],gates:\[\]/);
});
