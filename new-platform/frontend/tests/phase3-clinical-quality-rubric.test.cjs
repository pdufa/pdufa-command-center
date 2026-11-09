"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
const pilot=JSON.parse(fs.readFileSync(path.join(root,"data/acacia-pilot-prediction-workup-20261108.json"),"utf8"));
function load(tsPath){
  const code=fs.readFileSync(path.join(root,tsPath),"utf8");
  const js=ts.transpileModule(code,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}});
  const module={exports:{}};
  vm.runInNewContext(js.outputText,{module,exports:module.exports,URL});
  return module.exports;
}
const signals=load("lib/acacia-quantitative-science.ts");
const rubric=load("lib/phase3-clinical-quality-rubric.ts");
const context=()=>structuredClone(pilot);
const report=()=>signals.evaluatePilotScientificSignals(context());

test("phase-first method rubrics are source-bound and do not fabricate grades for either method",()=>{
  const r=rubric.evaluateClinicalRubricReadiness(report(),context());
  assert.ok(r);
  assert.equal(r.schema,"MAIN_PHASE3_METHOD_RUBRIC_READINESS_V1");
  assert.equal(r.nct,"NCT06081894");
  assert.equal(r.candidateMethodPositionsWithResearch,5);
  assert.equal(r.sourceMappedPositions,18);
  assert.equal(r.unmappedMethodPositions,782);
  assert.equal(r.clinicalMethodGradesWritten,0);
  assert.equal(r.fdaPrediction,"ABSTAIN");
  assert.deepEqual(Array.from(r.methods.map(m=>[m.assessmentId,m.methodIndex])),[["5.1",12],["5.3",19]]);
  for(const m of r.methods){
    assert.equal(m.rubricVersion,"MAIN_PHASE3_METHOD_GRADE_RUBRIC_V1");
    assert.equal(m.eligibility,"NOT_ELIGIBLE_REQUIRES_INDEPENDENT_REVIEW");
    assert.equal(m.numericGrade,null);
    assert.equal(m.confidenceRating,null);
    assert.equal(m.officialGrade,null);
    assert.equal(m.reviewerSignature,null);
    assert.equal(m.documentedPublicChecks,1);
    assert.equal(m.requirementsTotal,6);
    assert.equal(m.requirements.length,6);
    assert.deepEqual(Array.from(m.gradeBands.map(b=>b.grade)),[0,1,2,3,4,5]);
    assert.equal(m.gradeBands.length,6);
    assert.equal(m.requirements.filter(c=>c.state==="DOCUMENTED_PUBLIC").length,1);
    for(const c of m.requirements){
      if(c.state==="DOCUMENTED_PUBLIC")assert.ok(c.sourceUrl.startsWith("https://"));
      else assert.equal(c.sourceUrl,null);
    }
  }
  assert.equal(r.methods[1].requirements.filter(c=>c.state==="UNRESOLVED").length,2);
  assert.equal(r.methods[0].requirements.filter(c=>c.state==="INDEPENDENTLY_UNVERIFIED").length,5);
});
test("method quality rubric is not a hidden clinical strength grade or probability",()=>{
  const r=rubric.evaluateClinicalRubricReadiness(report(),context());
  assert.ok(r);
  assert.ok(r.methods[0].gradeBands[0].meaning.includes("invalidate"));
  assert.ok(r.methods[0].gradeBands[5].meaning.includes("external/independent"));
  assert.ok(r.methods[1].gradeBands[0].meaning.includes("invalid"));
  assert.ok(r.methods[1].gradeBands[5].meaning.includes("consistent"));
  assert.equal(r.methods[0].numericGrade,null);
  assert.equal(r.methods[1].numericGrade,null);
  assert.equal(r.fdaPrediction,"ABSTAIN");
});
test("counterfactual changed source grades or clinical state fail closed",()=>{
  const a=report();
  const changed=[
    r=>{r.nct="NCT00000000";},
    r=>{r.positivePublishedEndpointSignals=1;},
    r=>{r.treatedArmExcessInDescriptiveSafety=1;},
    r=>{r.officialMethodGrade=4;},
    r=>{r.provisionalClinicalGrade=3;},
    r=>{r.independentClinicalReview=true;},
    r=>{r.lockedSapVerified=true;},
    r=>{r.clinicalImportanceVerified=true;},
    r=>{r.seriousHeartFailureReconciliation="RESOLVED";},
    r=>{r.endpoints[0].sourceUrl="https://wrong.example/other";},
    r=>{r.safety[0].sourceUrl="https://wrong.example/other";},
    r=>{r.fdaPrediction="APPROVAL";}
  ];
  for(let i=0;i<changed.length;i++){
    const r=structuredClone(a);changed[i](r);
    assert.equal(rubric.evaluateClinicalRubricReadiness(r,context()),null,"unexpected release for "+i);
  }
  const contexts=[
    x=>{x.phaseReported="PHASE2";},
    x=>{x.phaseIndependentReviewerVerified=true;},
    x=>{x.scientificFramework.positions=400;},
    x=>{x.scientificFramework.mappedCandidateMethodLeads=17;},
    x=>{x.scientificFramework.methodPositionsUnexamined=0;},
    x=>{x.scientificFramework.independentlyGradedMethodPositions=1;},
    x=>{x.scientificFramework.currentPhaseReviewSignoffs=1;},
    x=>{x.finalDecision.approval="APPROVAL";},
    x=>{x.finalDecision.calibratedAccuracy=0.99;}
  ];
  for(let i=0;i<contexts.length;i++){
    const x=context();contexts[i](x);
    assert.equal(rubric.evaluateClinicalRubricReadiness(a,x),null,"unexpected context "+i);
  }
  assert.equal(rubric.evaluateClinicalRubricReadiness(null,context()),null);
});
test("UI has 0–5 anchors, explicitly labels missing evidence as unknown, and leaves ledger unchanged",()=>{
  const ui=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotScientificSignalPanel.tsx"),"utf8");
  const head=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotPredictionWorkup.tsx"),"utf8");
  const ledger=fs.readFileSync(path.join(root,"app/predictions/assessment/ScientificMethodMatrix.tsx"),"utf8");
  assert.match(ui,/evaluateClinicalRubricReadiness\(report,pilot\)/);
  assert.match(ui,/Evidence-quality rubric/);
  assert.match(ui,/Grade 0 does/);
  assert.match(ui,/UNASSIGNED/);
  assert.match(ui,/six independent evidence verification requirements/);
  assert.match(ui,/Show grading anchors for 0, 1, 2, 3, 4, 5/);
  assert.match(ui,/coverage, not a quality score/);
  assert.match(ui,/Current numerical grade: not assigned/);
  assert.match(head,/<PilotScientificSignalPanel nct=\{nct\}/);
  assert.match(ledger,/method.grade === null \? "Unscored"/);
  assert.doesNotMatch(ui,/reviewerSignature\s*=/);
});
