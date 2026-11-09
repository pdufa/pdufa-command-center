"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
  const js=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true
  }});
  mod._compile(js.outputText,file);
};
const pilot=require("../data/acacia-pilot-prediction-workup-20261108.json");
const history=require("../data/acacia-original-history-revision36.json");
const {buildAcaciaMethodReadiness}=require("../lib/acacia-method-evidence-readiness.ts");
const clone=x=>structuredClone(x);
test("exact ACACIA 40x20 method handoff preserves three documentary sources and 0 clinical grades",()=>{
  const q=buildAcaciaMethodReadiness(clone(pilot),clone(history));
  assert.ok(q);
  assert.equal(q.methodPositions.length,800);
  assert.equal(new Set(q.methodPositions.map(p=>p.id)).size,800);
  assert.equal(q.prioritizedResearchHandoffs.length,18);
  assert.deepEqual(q.counts,{total:800,originalRegistryDocumentaryReferences:3,
    mappedLeadsWithoutNewOriginalRegistryPacket:15,unmapped:782,
    documentaryOrNumericResearchFindings:5,clinicallyGraded:0,
    independentPhaseSignoffs:0,independentClinicalReviews:0,
    verifiedHistoricalFdaCohortCases:0});
  assert.deepEqual(q.prioritizedResearchHandoffs.filter(p=>p.originalDocumentLinks.length).map(p=>p.id).sort(),["4.2:L1","4.4:L1","8.2:L1"]);
  assert.equal(q.methodPositions.filter(p=>p.sourceState==="NO_MAPPED_SOURCE").length,782);
  assert.ok(q.methodPositions.every(p=>p.officialGrade===null&&p.fdaProbability===null&&p.reviewerStatus==="PHASE_AND_METHOD_SIGNOFF_PENDING"));
  assert.equal(q.fdaPrediction,"ABSTAIN");
  assert.equal(q.accuracy,"NOT_CALIBRATED");
  assert.deepEqual(q.originalVersionPublicPostingDates,["2025-01-14","2025-05-20","2026-02-02","2026-08-05"]);
});
test("changed original receipts, forged independent review or other trial fail closed",()=>{
  const cases=[
    (p,h)=>{p.nct="NCT99999999";},
    (p,h)=>{p.scientificFramework.assessments=39;},
    (p,h)=>{p.scientificFramework.independentlyGradedMethodPositions=1;},
    (p,h)=>{p.finalDecision.approval="APPROVAL";},
    (p,h)=>{h.nct="NCT99999999";},
    (p,h)=>{h.versions[0].sourceSha256="fake";},
    (p,h)=>{h.versions[0].posted="2025-01-01";},
    (p,h)=>{h.versions[1].primary=[];},
    (p,h)=>{h.mappedExistingPositions[0]="5.3:L19";},
    (p,h)=>{h.officialClinicalGrades=1;},
    (p,h)=>{h.sourceVersionCompleteness=false;},
  ];
  for(let i=0;i<cases.length;i++){
    const p=clone(pilot),h=clone(history);cases[i](p,h);
    assert.equal(buildAcaciaMethodReadiness(p,h),null,"tamper case "+i);
  }
});
test("method evidence interface must remain a no-write source handoff",()=>{
  const component=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotMethodEvidenceReadiness.tsx"),"utf8");
  const parent=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotResearchReviewQueue.tsx"),"utf8");
  assert.match(component,/Evidence-to-reviewer gates/);
  assert.match(component,/800 methods/);
  assert.match(component,/UNASSIGNED/);
  assert.match(component,/NOT CALIBRATED/);
  assert.ok(parent.includes("<PilotMethodEvidenceReadiness/>"));
  assert.doesNotMatch(component,/fetch\s*\(|POST\s|submitGrade/);
});
