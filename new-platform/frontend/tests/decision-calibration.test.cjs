const test=require("node:test");const assert=require("node:assert/strict");const fs=require("node:fs");const path=require("node:path");const Module=require("node:module");const ts=require("typescript");const f=path.resolve(__dirname,"../lib/decision-calibration.ts");const js=ts.transpileModule(fs.readFileSync(f,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;const m=new Module(f,module);m.filename=f;m.paths=module.paths;m._compile(js,f);const {summarizeHistoricalCalibration}=m.exports;
const sample=Array.from({length:30},(_,i)=>({programId:"PDUFA-"+String(100000+i),predictedAt:"2025-01-01T00:00:00Z",decisionAt:"2025-02-01T00:00:00Z",approvalProbability:.5,approved:i%2===0,cohort:"historical"}));
test("30 synthetic cases calculate Brier and log loss",()=>{const r=summarizeHistoricalCalibration(sample);assert.equal(r.status,"RESEARCH_ONLY");assert.ok(Math.abs(r.brierScore-.25)<1e-12);assert.ok(Math.abs(r.logLoss-Math.log(2))<1e-12);});
test("underpowered cohort is not validated",()=>assert.equal(summarizeHistoricalCalibration(sample.slice(0,29)).status,"INSUFFICIENT_DATA"));
test("future leakage blocks validation",()=>assert.equal(summarizeHistoricalCalibration(sample.map((x,i)=>i===0?{...x,predictedAt:"2025-03-01T00:00:00Z"}:x)).status,"INSUFFICIENT_DATA"));
test("duplicate program blocks validation",()=>assert.equal(summarizeHistoricalCalibration([...sample.slice(0,29),sample[0]]).status,"INSUFFICIENT_DATA"));
test("invalid probability blocks validation",()=>assert.equal(summarizeHistoricalCalibration(sample.map((x,i)=>i===0?{...x,approvalProbability:1.1}:x)).status,"INSUFFICIENT_DATA"));
test("AUROC is one for perfect ranking and zero for completely reversed ranking",()=>{
 for(const reverse of [false,true]){
  const rows=sample.map(row=>({...row,approvalProbability:row.approved!==reverse?.9:.1}));
  const r=summarizeHistoricalCalibration(rows);assert.equal(r.status,"RESEARCH_ONLY");assert.equal(r.discrimination.auroc,reverse?0:1);
  assert.equal(r.discrimination.approvalCount,15);assert.equal(r.discrimination.nonapprovalCount,15);assert.equal(r.discrimination.unavailableReason,null);
 }
});
test("constant forecasts give tied pairs half credit rather than fabricated discrimination",()=>{
 const r=summarizeHistoricalCalibration(sample);assert.equal(r.discrimination.auroc,.5);
});
test("mixed tied-score ranking has a hand-calculated AUROC of seven eighths",()=>{
 const pattern=[{approvalProbability:.1,approved:false},{approvalProbability:.4,approved:true},{approvalProbability:.4,approved:false},{approvalProbability:.9,approved:true}];
 const rows=Array.from({length:32},(_,i)=>({...sample[0],programId:"PDUFA-"+(200000+i),...pattern[i%4]}));
 const before=structuredClone(rows),r=summarizeHistoricalCalibration(rows);
 assert.equal(r.discrimination.auroc,.875);assert.deepEqual(rows,before);
 assert.deepEqual(summarizeHistoricalCalibration([...rows].reverse()).discrimination,r.discrimination);
});
test("AUROC is invariant under strictly increasing score transforms while calibration changes",()=>{
 const rows=sample.map(row=>({...row,approvalProbability:row.approved?.8:.3}));
 const transformed=rows.map(row=>({...row,approvalProbability:row.approvalProbability**2}));
 const a=summarizeHistoricalCalibration(rows),b=summarizeHistoricalCalibration(transformed);
 assert.equal(a.discrimination.auroc,b.discrimination.auroc);assert.notEqual(a.brierScore,b.brierScore);
});
test("single-class cohorts have no defined AUROC but retain explicit outcome class counts",()=>{
 for(const approved of [true,false]){
  const r=summarizeHistoricalCalibration(sample.map(row=>({...row,approved})));
  assert.equal(r.status,"RESEARCH_ONLY");assert.equal(r.discrimination.auroc,null);assert.equal(r.discrimination.unavailableReason,"SINGLE_OUTCOME_CLASS");
  assert.equal(r.discrimination.approvalCount,approved?30:0);assert.equal(r.discrimination.nonapprovalCount,approved?0:30);
 }
});
test("invalid,duplicate,leaking or underpowered inputs withhold discrimination with all other metrics",()=>{
 for(const rows of [sample.slice(0,29),[...sample.slice(0,29),sample[0]],sample.map((row,i)=>i?row:{...row,approvalProbability:NaN}),sample.map((row,i)=>i?row:{...row,predictedAt:row.decisionAt})]){
  const r=summarizeHistoricalCalibration(rows);assert.equal(r.status,"INSUFFICIENT_DATA");assert.deepEqual(r.discrimination,{auroc:null,approvalCount:null,nonapprovalCount:null,unavailableReason:"INVALID_OR_INSUFFICIENT_DATA"});
 }
});
