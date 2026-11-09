"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
const pilot=JSON.parse(fs.readFileSync(path.join(root,"data","acacia-pilot-prediction-workup-20261108.json"),"utf8"));
const source=fs.readFileSync(path.join(root,"lib","pilot-research-readiness.ts"),"utf8");
const compiled=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText;
const mod={exports:{}};
vm.runInNewContext(compiled,{module:mod,exports:mod.exports,URL});
const evaluate=mod.exports.evaluatePilotReadiness;
const clone=()=>structuredClone(pilot);

test("first pilot result is reproducible 3/5 source-readiness points, not an official grade",()=>{
  const r=evaluate(clone());
  assert.ok(r);
  assert.equal(r.points,3);
  assert.equal(r.outOf,5);
  assert.equal(r.assessmentId,"5.1");
  assert.equal(r.methodIndex,1);
  assert.equal(r.scoreKind,"DOCUMENTARY_RESEARCH_CHECKLIST_NOT_CLINICAL_GRADE");
  assert.equal(r.officialClinicalGrade,null);
  assert.equal(r.fdaPrediction,"ABSTAIN");
  assert.equal(r.checks.length,5);
  assert.deepEqual(Array.from(r.checks.map(x=>x.state)),[
    "RESEARCH_OBSERVED","RESEARCH_OBSERVED","RESEARCH_OBSERVED",
    "NOT_VERIFIED","NOT_VERIFIED"
  ]);
});
test("source readiness never asserts an authorized human clinical score",()=>{
  const p=clone();
  assert.equal(p.scientificFramework.independentlyGradedMethodPositions,0);
  assert.equal(p.provisionalResearchScore.officialClinicalGrade,null);
  assert.equal(p.provisionalResearchScore.reviewerSignedOff,false);
  assert.equal(p.provisionalResearchScore.approvalProbability,null);
  assert.equal(p.finalDecision.calibratedAccuracy,null);
  assert.equal(p.finalDecision.calibratedProbabilities,null);
});
test("pinned source identity, protocol hash, unknown gates and clinical events fail closed",()=>{
  const edits=[
    p=>{p.nct="NCT99999999";},
    p=>{p.sources.CTIS_AM04.sha256="0".repeat(64);},
    p=>{p.sources.REGISTRY.url="https://evil.example/pretend-registry";},
    p=>{p.sources.NEJM_PIVOTAL.url="https://evil.example/pretend-publication";},
    p=>{p.sources.CTIS_AM04.retrieved=false;},
    p=>{p.provisionalResearchScore.gates[1].sourceId="REGISTRY";},
    p=>{p.provisionalResearchScore.gates[3].state="RESEARCH_OBSERVED";},
    p=>{p.provisionalResearchScore.gates[4].state="WRONG_STATUS";},
    p=>{p.provisionalResearchScore.gates[4].sourceId="NEJM_PIVOTAL";},
    p=>{p.provisionalResearchScore.gates[0].id="FAKE";},
    p=>{p.provisionalResearchScore.gates.pop();},
    p=>{p.scientificFramework.independentlyGradedMethodPositions=1;},
    p=>{p.phaseIndependentReviewerVerified=true;},
    p=>{p.finalDecision.approval="APPROVAL";},
    p=>{p.provisionalResearchScore.officialClinicalGrade=3;},
  ];
  for(const edit of edits){const p=clone();edit(p);assert.equal(evaluate(p),null);}
});
test("a newly unverified document drops research readiness, not a zero clinical method grade",()=>{
  const p=clone(),gate=p.provisionalResearchScore.gates[1];
  gate.state="NOT_VERIFIED";gate.sourceId=null;
  const r=evaluate(p);
  assert.ok(r);
  assert.equal(r.points,2);
  assert.equal(r.officialClinicalGrade,null);
});
test("pilot page renders explanation before full matrix, and labels static research not live grades",()=>{
  const widget=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotPredictionWorkup.tsx"),"utf8");
  const parent=fs.readFileSync(path.join(root,"app/predictions/assessment/ScientificMethodMatrix.tsx"),"utf8");
  assert.match(widget,/FIRST PRELIMINARY RESEARCH SCORE/);
  assert.match(widget,/evaluatePilotReadiness\(pilot\)/);
  assert.match(widget,/readiness\.points/);
  assert.match(widget,/Show five scoring rules, sources and missing evidence/);
  assert.match(widget,/not.*official 0–5 scientific grade/);
  assert.match(widget,/WITHHELD/);
  assert.ok(widget.indexOf("FIRST PRELIMINARY RESEARCH SCORE")<widget.indexOf("Phase 3 evidence:"));
  assert.ok(parent.indexOf("<PilotPredictionWorkup nct={nct} />")<parent.indexOf("<ScientificInstallationStatus />"));
});
