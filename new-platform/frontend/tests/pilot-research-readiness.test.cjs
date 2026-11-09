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
const evaluateMore=mod.exports.evaluateAdditionalPilotReadiness;
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


test("two additional clinical-domain source checklists produce research 3/5 and 2/5, never clinical scores",()=>{
  const p=clone(),extra=evaluateMore(p);
  assert.ok(extra);
  assert.equal(extra.length,2);
  assert.deepEqual(Array.from(extra.map(x=>[x.assessmentId,x.methodIndex,x.points,x.outOf])),[
    ["4.2",1,3,5],["5.3",1,2,5]
  ]);
  assert.ok(evaluate(p));
  assert.equal(p.scientificFramework.independentlyGradedMethodPositions,0);
  for(const item of extra){
    assert.equal(item.scoreKind,"DOCUMENTARY_RESEARCH_CHECKLIST_NOT_CLINICAL_GRADE");
    assert.equal(item.fdaPrediction,"ABSTAIN");
    assert.equal(item.officialClinicalGrade,null);
    assert.equal(item.checks.length,5);
    assert.ok(p.criticalAssessmentEvidence.find(x=>x.id===item.assessmentId).candidateMethodIndices.includes(item.methodIndex));
  }
});

test("missing SAP, unreconciled HF events and unknown numerical efficacy prevent false score upgrades",()=>{
  const invalid=[
    p=>{p.additionalProvisionalResearchScores[0].gates[3].state="RESEARCH_OBSERVED";},
    p=>{p.additionalProvisionalResearchScores[1].gates[2].state="RESEARCH_OBSERVED";},
    p=>{p.additionalProvisionalResearchScores[1].gates[3].sourceId="SEC_10Q";},
    p=>{p.additionalProvisionalResearchScores[0].gates[0].sourceId="NEJM_PIVOTAL";},
    p=>{p.additionalProvisionalResearchScores[1].gates[1].id="FAKE_SOURCE";},
    p=>{p.additionalProvisionalResearchScores[0].gates[4].state="SCORED";},
    p=>{p.additionalProvisionalResearchScores[1].officialClinicalGrade=2;},
    p=>{p.additionalProvisionalResearchScores[0].reviewerSignedOff=true;},
    p=>{p.additionalProvisionalResearchScores[1].approvalProbability=0.6;},
    p=>{p.additionalProvisionalResearchScores.push(structuredClone(p.additionalProvisionalResearchScores[1]));},
    p=>{p.additionalProvisionalResearchScores.reverse();},
    p=>{p.additionalProvisionalResearchScores[0].gates[2].sourceId=null;},
    p=>{p.sources.SEC_10Q.url="https://untrusted.example/new-10q";},
    p=>{p.sources.ISSUER_MAY_2025.url="https://untrusted.example/claim";},
    p=>{p.sources.CTIS_AM04.sha256="f".repeat(64);},
    p=>{p.publishedPrimary.peakVo2.difference=0.99;},
    p=>{p.publishedPrimary.finalSapVerified=true;},
    p=>{p.descriptiveSafety.find(x=>x.metric==="SPONSOR_REPORTED_SERIOUS_HEART_FAILURE_AE").treated=11;},
    p=>{p.descriptiveSafety.find(x=>x.metric==="SPONSOR_REPORTED_SERIOUS_HEART_FAILURE_AE").sourceDiscrepancy="RESOLVED";},
    p=>{p.scientificFramework.independentlyGradedMethodPositions=1;},
    p=>{p.finalDecision.crl="CRL";},
  ];
  for(let i=0;i<invalid.length;i++){
    const p=clone();invalid[i](p);
    assert.equal(evaluateMore(p),null,"unexpectedly released score for invalid input "+i);
  }
});

test("new preliminary scorecards render with an expandable rubric but cannot fill the 800 clinical-grade slots",()=>{
  const widget=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotPredictionWorkup.tsx"),"utf8");
  assert.match(widget,/evaluateAdditionalPilotReadiness\(pilot\)/);
  assert.match(widget,/Additional preliminary research scores/);
  assert.match(widget,/3 of 18 source-mapped research positions/);
  assert.match(widget,/card.points/);
  assert.match(widget,/View the five documented criteria and source gaps/);
  assert.match(widget,/not official scientific method grades/);
  assert.match(widget,/FDA prediction remains ABSTAIN/);
  assert.match(widget,/additionalReadiness\?additionalReadiness.map/);
});
