"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
const snapshot=JSON.parse(fs.readFileSync(path.join(root,"data/acacia-pilot-prediction-workup-20261108.json"),"utf8"));
const evaluatorSrc=fs.readFileSync(path.join(root,"lib/acacia-quantitative-science.ts"),"utf8");
const js=ts.transpileModule(evaluatorSrc,{compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS
},reportDiagnostics:true});
assert.ok(!js.diagnostics?.some(d=>d.category===ts.DiagnosticCategory.Error),
  "Quantitative evaluator should transpile without errors");
const mod={exports:{}};
vm.runInNewContext(js.outputText,{module:mod,exports:mod.exports,URL});
const evaluate=mod.exports.evaluatePilotScientificSignals;
const clone=()=>structuredClone(snapshot);

test("first two research methods recalculate real effects and uncertainty without clinical scores",()=>{
  const r=evaluate(clone());
  assert.ok(r,"Expected exact original pilot analysis");
  assert.equal(r.schema,"MAIN_ACACIA_QUANTITATIVE_RESEARCH_V1");
  assert.equal(r.nct,"NCT06081894");
  assert.equal(r.phaseBasis,"REPORTED_PHASE3_NOT_INDEPENDENTLY_SIGNED_OFF");
  assert.deepEqual(Array.from(r.methods.map(x=>[x.assessmentId,x.methodIndex])),
    [["5.1",12],["5.3",19]]);
  assert.equal(r.positivePublishedEndpointSignals,2);
  assert.equal(r.primaryEndpointSignalsOutOf,2);
  assert.deepEqual(Array.from(r.endpoints.map(x=>[x.estimate,...x.ci95,x.reportedP])),
    [[3,0.5,5.5,0.02],[0.67,0.22,1.11,0.003]]);
  assert.equal(r.endpoints[0].approximateStandardError,1.2755);
  assert.equal(r.endpoints[1].approximateStandardError,0.227);
  assert.ok(r.endpoints.every(x=>x.directionalPass===true));
  assert.ok(r.endpoints.every(x=>x.sourceUrl==="https://pubmed.ncbi.nlm.nih.gov/42663312/"));
  assert.equal(r.officialMethodGrade,null);
  assert.equal(r.provisionalClinicalGrade,null);
  assert.equal(r.independentClinicalReview,false);
  assert.equal(r.fdaPrediction,"ABSTAIN");
  assert.equal(r.calibratedAccuracy,null);
  assert.equal(r.probability,null);
});
test("risk arithmetic uses true denominators and avoids HF event-conflicting composite",()=>{
  const r=evaluate(clone());
  assert.ok(r);
  assert.equal(r.treatedArmExcessInDescriptiveSafety,2);
  assert.equal(r.safetyOutOf,2);
  assert.deepEqual(Array.from(r.safety.map(x=>x.id)),
    ["LVEF_BELOW_50_PERCENT","ANY_SERIOUS_ADVERSE_EVENT"]);
  assert.equal(r.safety[0].treatedRatePercent,10.47);
  assert.equal(r.safety[0].controlRatePercent,0.77);
  assert.equal(r.safety[0].absoluteDifferencePp,9.69);
  assert.equal(r.safety[1].treatedRatePercent,20.16);
  assert.equal(r.safety[1].controlRatePercent,14.67);
  assert.equal(r.safety[1].absoluteDifferencePp,5.48);
  assert.equal(r.seriousHeartFailureReconciliation,"UNRESOLVED_11_1_VS_12_3");
  assert.ok(r.limitations.some(x=>x.includes("not independently adjudicated drug causality")));
});
test("partial source, phase, review, effect or missing original analysis change fails closed",()=>{
  const changes=[
    p=>{p.nct="NCT11111111";},
    p=>{p.trial="another trial";},
    p=>{p.phaseReported="PHASE2";},
    p=>{p.phaseIndependentReviewerVerified=true;},
    p=>{p.scientificFramework.positions=20;},
    p=>{p.scientificFramework.independentlyGradedMethodPositions=1;},
    p=>{p.scientificFramework.currentPhaseReviewSignoffs=1;},
    p=>{p.finalDecision.approval="APPROVAL";},
    p=>{p.finalDecision.calibratedAccuracy=0.8;},
    p=>{p.sources.NEJM_PIVOTAL.url="https://untrusted.example/fake";},
    p=>{p.sources.SEC_10Q.url="https://untrusted.example/fake";},
    p=>{p.publishedPrimary.kccq.ci95[0]=-0.5;},
    p=>{p.publishedPrimary.kccq.difference=300;},
    p=>{p.publishedPrimary.kccq.pValueRounded=0.5;},
    p=>{p.publishedPrimary.peakVo2.ci95[1]=1.25;},
    p=>{p.publishedPrimary.peakVo2.pValue=0.5;},
    p=>{p.publishedPrimary.peakVo2.unit="percent";},
    p=>{p.publishedPrimary.randomized.placebo=300;},
    p=>{p.publishedPrimary.finalSapVerified=true;},
    p=>{p.publishedPrimary.clinicalImportanceReviewed=true;},
    p=>{p.publishedPrimary.sponsorReportedInitialAlphaEach=0.05;},
    p=>{p.descriptiveSafety[0].treated=2;},
    p=>{p.descriptiveSafety[1].controlN=0;},
    p=>{p.descriptiveSafety[2].sourceDiscrepancy="RESOLVED";},
    p=>{p.criticalAssessmentEvidence.find(x=>x.id==="5.1").candidateMethodIndices=[1];},
    p=>{p.criticalAssessmentEvidence.find(x=>x.id==="5.3").candidateMethodIndices=[1];},
  ];
  for(let i=0;i<changes.length;i++){
    const p=clone();changes[i](p);
    assert.equal(evaluate(p),null,"Unexpected statistical release with altered input #"+i);
  }
});
test("pilot UI distinguishes scientific reproducible figures from documentary and official grades",()=>{
  const ui=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotScientificSignalPanel.tsx"),"utf8");
  const parent=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotPredictionWorkup.tsx"),"utf8");
  const ledger=fs.readFileSync(path.join(root,"app/predictions/assessment/ScientificMethodMatrix.tsx"),"utf8");
  assert.match(ui,/evaluatePilotScientificSignals\(pilot\)/);
  assert.match(ui,/5\.1 · Scientific method 12/);
  assert.match(ui,/5\.3 · Scientific method 19/);
  assert.match(ui,/official 0–5 scientific grades are still withheld/);
  assert.match(ui,/SOURCE MISMATCH/);
  assert.match(ui,/not a 0–5 efficacy grade/);
  assert.match(ui,/not a causal risk score/);
  assert.match(ui,/FDA prediction: ABSTAIN/);
  assert.match(parent,/<PilotScientificSignalPanel nct=\{nct\}/);
  assert.ok(parent.indexOf("<PilotScientificSignalPanel nct={nct}/>")<
    parent.indexOf('aria-label="First provisional research score"'));
  assert.match(ledger,/method.grade === null \? "Unscored"/);
});
