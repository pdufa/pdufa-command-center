const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),Module=require("node:module"),ts=require("typescript");
const root=path.resolve(__dirname,"../lib"),cache={};
function load(name){if(cache[name])return cache[name].exports;const file=path.join(root,name+".ts");const js=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;const m=new Module(file,module);cache[name]=m;m.filename=file;m.paths=module.paths;m.require=id=>id.startsWith("./")?load(id.slice(2)):require(id);m._compile(js,file);return m.exports;}
const {evaluateChronologicalCalibration}=load("decision-calibration-holdout");
// Synthetic arithmetic/leakage fixtures only. These are not real forecasts or FDA evidence.
const make=(offset,holdout)=>Array.from({length:30},(_,i)=>({programId:"PDUFA-"+(100000+offset+i),applicationNumber:"NDA"+(100000+offset+i),
 predictedAt:holdout?"2025-02-01T00:00:00Z":"2024-01-01T00:00:00Z",
 predictionCapturedAt:holdout?"2025-02-01T00:00:00Z":"2024-01-01T00:00:00Z",
 decisionAt:holdout?"2025-03-01T00:00:00Z":"2024-02-01T00:00:00Z",
 decisionObservedAt:holdout?"2025-03-02T00:00:00Z":"2024-02-02T00:00:00Z",
 predictionSource:"https://example.org/forecast",decisionSource:"https://example.org/action",
 probability:i<6?.8:.2,approved:holdout?i<6:i<24,reviewStatus:"INDEPENDENTLY_VERIFIED",
 modelVersion:"frozen-v1",subgroup:"declared-cohort"}));
const training=make(0,false),holdout=make(30,true);
const plan={modelVersion:"frozen-v1",planSource:"https://example.org/frozen-plan",frozenAt:"2025-01-01T00:00:00Z",
 holdoutStart:"2025-01-01T00:00:00Z",holdoutEnd:"2026-01-01T00:00:00Z",evaluatedAt:"2026-02-01T00:00:00Z",
 trainingProgramIds:training.map(row=>row.programId),holdoutProgramIds:holdout.map(row=>row.programId)};
test("synthetic holdout arithmetic uses the frozen training baseline, not holdout prevalence",()=>{
 const r=evaluateChronologicalCalibration(training,holdout,plan);
 assert.equal(r.status,"RESEARCH_ONLY");assert.equal(r.tradeAuthorized,false);assert.equal(r.validatedPredictionAccuracy,false);
 assert.deepEqual(r.issues,[]);assert.ok(r.warnings.length);
 assert.ok(Math.abs(r.holdout.brierScore-.04)<1e-12);
 assert.ok(Math.abs(r.holdout.trainingBaselineProbability-.8)<1e-12);
 assert.ok(Math.abs(r.holdout.baselineBrier-.52)<1e-12);
 assert.ok(Math.abs(r.holdout.improvementVsTrainingBaseline-.48)<1e-12);
 assert.ok(Math.abs(r.holdout.expectedCalibrationError-.2)<1e-12);
 assert.equal(r.holdout.reliabilityBins.reduce((n,bin)=>n+bin.count,0),30);
 assert.equal(r.holdout.subgroups[0].metrics.status,"RESEARCH_ONLY");
});
test("shuffling input cannot change chronological cohort membership or metrics",()=>{
 const a=evaluateChronologicalCalibration([...training].reverse(),[...holdout].reverse(),plan),b=evaluateChronologicalCalibration(training,holdout,plan);
 assert.equal(a.status,b.status);assert.deepEqual(a.issues,b.issues);assert.deepEqual(a.holdout.reliabilityBins,b.holdout.reliabilityBins);
 for(const name of ["brierScore","logLoss","baselineBrier","improvementVsTrainingBaseline"])
  assert.ok(Math.abs(a.holdout[name]-b.holdout[name])<1e-12);
});
test("training outcomes first observed after the freeze block all holdout metrics",()=>{
 const rows=training.map((row,i)=>i?row:{...row,decisionObservedAt:plan.frozenAt});
 const r=evaluateChronologicalCalibration(rows,holdout,plan);assert.equal(r.status,"NOT_READY");assert.equal(r.holdout,null);
});
test("holdout outcomes observed at or beyond evaluation cutoff block metrics",()=>{
 for(const decisionObservedAt of [plan.evaluatedAt,"2026-03-01T00:00:00Z"]){
  const r=evaluateChronologicalCalibration(training,holdout.map((row,i)=>i?row:{...row,decisionObservedAt}),plan);
  assert.equal(r.status,"NOT_READY");assert.equal(r.holdout,null);
 }
});
test("post-hoc holdout freeze and empty plan provenance are rejected",()=>{
 for(const changes of [{frozenAt:"2025-02-01T00:00:00Z"},{planSource:""},{modelVersion:""},{holdoutEnd:plan.holdoutStart}])
  assert.equal(evaluateChronologicalCalibration(training,holdout,{...plan,...changes}).status,"NOT_READY");
});
test("missing prespecified cases cannot be removed while retaining a large enough sample",()=>{
 const r=evaluateChronologicalCalibration(training,holdout,{...plan,holdoutProgramIds:[...plan.holdoutProgramIds,"PDUFA-999999"]});
 assert.equal(r.status,"NOT_READY");assert.equal(r.holdout,null);assert.match(r.issues.join(" "),/membership/);
});
test("unexpected cases, repeated identities and model changes are rejected",()=>{
 for(const rows of [holdout.map((row,i)=>i?row:{...row,programId:"PDUFA-999999"}),
  holdout.map((row,i)=>i?row:{...row,programId:training[0].programId}),
  holdout.map((row,i)=>i?row:{...row,modelVersion:"retuned-after-holdout"})])
  assert.equal(evaluateChronologicalCalibration(training,rows,plan).status,"NOT_READY");
});
test("one FDA application cannot cross train and holdout under different program IDs",()=>{
 const rows=holdout.map((row,i)=>i?row:{...row,applicationNumber:training[0].applicationNumber});
 assert.notEqual(rows[0].programId,training[0].programId);
 const r=evaluateChronologicalCalibration(training,rows,plan);
 assert.equal(r.status,"NOT_READY");assert.equal(r.holdout,null);assert.match(r.issues.join(" "),/application cannot cross/);
});
test("application identity is mandatory and canonical for NDA and BLA records",()=>{
 for(const applicationNumber of [undefined,"","NDA12345","ANDA123456","nda123456","NDA 123456"]){
  const r=evaluateChronologicalCalibration(training,holdout.map((row,i)=>i?row:{...row,applicationNumber}),plan);
  assert.equal(r.status,"NOT_READY");assert.equal(r.holdout,null);
 }
 const r=evaluateChronologicalCalibration(training,holdout.map((row,i)=>i?row:{...row,applicationNumber:"BLA999999"}),plan);
 assert.equal(r.status,"RESEARCH_ONLY");
});
test("distinct training-cycle program IDs may share an FDA application within training",()=>{
 const rows=training.map((row,i)=>i===1?{...row,applicationNumber:training[0].applicationNumber}:row);
 assert.notEqual(rows[0].programId,rows[1].programId);
 assert.equal(evaluateChronologicalCalibration(rows,holdout,plan).status,"RESEARCH_ONLY");
});
test("out-of-window forecasts and unreviewed sources cannot be evaluated",()=>{
 for(const changes of [{predictedAt:"2024-12-31T00:00:00Z",predictionCapturedAt:"2024-12-31T00:00:00Z"},
  {predictionCapturedAt:holdout[0].decisionAt},{reviewStatus:"PENDING"},{decisionSource:""}])
  assert.equal(evaluateChronologicalCalibration(training,holdout.map((row,i)=>i?row:{...row,...changes}),plan).status,"NOT_READY");
});
test("smaller partitions and attempts to lower the minimum below 30 are rejected",()=>{
 assert.equal(evaluateChronologicalCalibration(training.slice(0,29),holdout,{...plan,trainingProgramIds:plan.trainingProgramIds.slice(0,29)}).status,"NOT_READY");
 assert.equal(evaluateChronologicalCalibration(training,holdout,plan,1).status,"NOT_READY");
});
test("underpowered subgroups stay explicitly unscored",()=>{
 const r=evaluateChronologicalCalibration(training,holdout.map((row,i)=>({...row,subgroup:i<15?"A":"B"})),plan);
 assert.equal(r.status,"RESEARCH_ONLY");assert.equal(r.holdout.subgroups.length,2);
 assert.ok(r.holdout.subgroups.every(group=>group.metrics.status==="INSUFFICIENT_DATA"&&group.metrics.brierScore===null));
});
