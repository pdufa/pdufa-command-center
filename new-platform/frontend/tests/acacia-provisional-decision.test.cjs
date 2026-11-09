"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const src=fs.readFileSync(path.join(root,"lib/acacia-provisional-decision.ts"),"utf8");
const compiled=ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022},reportDiagnostics:true});
assert.equal((compiled.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error).length,0);
const module={exports:{}};
vm.runInNewContext(compiled.outputText,{module,exports:module.exports});
const evaluate=module.exports.evaluateProvisionalEvidence, simulate=module.exports.simulateHypotheticalPath;
const pilot=JSON.parse(fs.readFileSync(path.join(root,"data/acacia-pilot-prediction-workup-20261108.json"),"utf8"));
const clone=()=>structuredClone(pilot);
test("first exact trial produces source-gated direction but no FDA probability or official grades",()=>{
  const r=evaluate(clone());assert.ok(r);
  assert.equal(r.nct,"NCT06081894");assert.equal(r.positivePrimaryEndpoints,2);
  assert.equal(r.sourceMappedMethods,18);assert.equal(r.officialGrades,0);
  assert.equal(r.findings.length,6);assert.equal(r.uncertainty,"HIGH_UNQUANTIFIED");
  assert.equal(r.approvalProbability,null);assert.equal(r.accuracy,null);
  assert.equal(r.scientificSignoff,false);assert.equal(r.modelKind,"RESEARCH_RULE_NOT_TRAINED");
  assert.equal(r.fdaOutcomes.APPROVAL,"ABSTAIN");
  assert.equal(r.fdaOutcomes.CRL,"ABSTAIN");
  assert.equal(r.fdaOutcomes.REVIEW_DELAY,"ABSTAIN");
});
test("source manipulation or forged review status withholds the preliminary result",()=>{
  const changes=[
    p=>p.nct="NCT00000000",
    p=>p.protocolCode="WRONG",
    p=>p.phaseIndependentReviewerVerified=true,
    p=>p.scientificFramework.independentlyGradedMethodPositions=1,
    p=>p.scientificFramework.mappedCandidateMethodLeads=19,
    p=>p.finalDecision.approval="APPROVAL",
    p=>p.finalDecision.calibratedAccuracy=0.91,
    p=>p.publishedPrimary.kccq.ci95[0]=-1,
    p=>p.publishedPrimary.peakVo2.pValue=0.2,
    p=>p.descriptiveSafety[0].treated=2,
    p=>p.descriptiveSafety[1].controlN=200,
    p=>p.descriptiveSafety[2].sourceDiscrepancy="RECONCILED",
    p=>p.sources.NEJM_PIVOTAL.url="https://invalid.example",
    p=>p.fdaCycle.date="2027-01-01",
    p=>p.criticalAssessmentEvidence[0].candidateMethodIndices[0]=99
  ];
  changes.forEach((fn,i)=>{let p=clone();fn(p);assert.equal(evaluate(p),null,"tampered case "+i)});
});
test("scenario logic is clearly hypothetical, has distinct branches and never releases forecasts",()=>{
  const base={filing:"PLANNED",sap:"UNVERIFIED",safety:"UNRESOLVED",review:"PENDING"};
  const results=[
    [base,"PRE_FILING"],
    [{...base,filing:"FDA_ACCEPTED"},"ADDITIONAL_REVIEW_PATH"],
    [{...base,filing:"FDA_ACCEPTED",sap:"RECONCILED",safety:"MANAGEABLE",review:"SUPPORTIVE"},"CONDITIONAL_APPROVAL_PATH"],
    [{...base,filing:"FDA_ACCEPTED",safety:"MATERIAL_CONCERN"},"REGULATORY_CONCERN_PATH"]
  ];
  for(const [params,expect] of results){
    const r=simulate(params);assert.equal(r.class,expect);
    assert.equal(r.probability,null);assert.equal(r.accuracy,null);
    assert.equal(r.hypothetical,true);assert.equal(r.fdaOutcome,"ABSTAIN");
  }
  assert.equal(simulate({...base,filing:"APPROVED"}),null);
});
test("provisional model appears before quantitative analysis while keeping ABSTAIN prominent",()=>{
  const ui=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotProvisionalResearchModel.tsx"),"utf8");
  const parent=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotPredictionWorkup.tsx"),"utf8");
  assert.match(ui,/Hypothetical FDA pathway simulator/);
  assert.match(ui,/Reset to observed state/);
  assert.match(ui,/Actual FDA prediction: ABSTAIN/);
  assert.match(ui,/NOT CALIBRATED/);
  assert.match(ui,/No numeric probabilities or confidence intervals/);
  const a=parent.indexOf("<PilotProvisionalResearchModel nct={nct}/>");
  const b=parent.indexOf("<PilotScientificSignalPanel nct={nct}/>");
  assert.ok(a>=0&&a<b,"Pilot provisional panel should precede detailed clinical analysis");
});
