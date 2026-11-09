"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
const pilot=JSON.parse(fs.readFileSync(path.join(root,"data/acacia-pilot-prediction-workup-20261108.json"),"utf8"));
function load(src,imports={}){
  const input=fs.readFileSync(path.join(root,src),"utf8");
  const js=ts.transpileModule(input,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText;
  const mod={exports:{}};
  vm.runInNewContext(js,{module:mod,exports:mod.exports,URL,require:(n)=>{
    if(Object.hasOwn(imports,n))return imports[n];
    throw Error("Unapproved dependency: "+n);
  }},{timeout:1000});
  return mod.exports;
}
const quantitative=load("lib/acacia-quantitative-science.ts");
const rubric=load("lib/phase3-clinical-quality-rubric.ts");
const readiness=load("lib/pilot-research-readiness.ts");
const queueModule=load("lib/acacia-phase3-review-queue.ts",{
  "./acacia-quantitative-science":quantitative,
  "./phase3-clinical-quality-rubric":rubric,
  "./pilot-research-readiness":readiness
});
const evaluate=queueModule.buildPhase3ReviewQueue;
const clone=()=>structuredClone(pilot);

test("all 18 exact Phase III leads are source mapped, uniquely ordered and never clinical grades",()=>{
  const r=evaluate(clone());
  assert.ok(r);
  assert.equal(r.schema,"MAIN_ACACIA_PHASE3_REVIEW_QUEUE_V1");
  assert.equal(r.nct,"NCT06081894");
  assert.equal(r.phaseBasis,"REGISTRY_REPORTED_PHASE3_NOT_INDEPENDENTLY_VERIFIED");
  assert.equal(r.status,"RESEARCH_WORKLIST_NOT_CLINICAL_GRADE");
  assert.equal(r.positions.length,18);
  assert.equal(new Set(r.positions.map(x=>x.id)).size,18);
  assert.deepEqual(Array.from(r.positions.map(x=>x.reviewOrder)),Array.from({length:18},(_,i)=>i+1));
  assert.equal(r.summary.mappedSourceLeads,18);
  assert.equal(r.summary.documentChecklist,3);
  assert.equal(r.summary.quantitativeMethods,2);
  assert.equal(r.summary.sourceLeadOnly,13);
  assert.equal(r.summary.positionsNotSourceMapped,782);
  assert.equal(r.summary.officialClinicalGrades,0);
  assert.equal(r.summary.qualifiedPhaseSignoffs,0);
  assert.equal(r.fdaPrediction,"ABSTAIN");
  assert.equal(r.calibratedAccuracy,null);
  const groupCounts=Object.fromEntries(["DOCUMENT_CHECKLIST",
    "PUBLISHED_NUMERIC_RECALCULATION","SOURCE_LEAD_ONLY"].map(k=>[k,r.positions.filter(x=>x.evidenceStatus===k).length]));
  assert.deepEqual(groupCounts,{
    DOCUMENT_CHECKLIST:3,PUBLISHED_NUMERIC_RECALCULATION:2,SOURCE_LEAD_ONLY:13
  });
  assert.deepEqual(Array.from(r.positions.filter(x=>x.evidenceStatus==="PUBLISHED_NUMERIC_RECALCULATION").map(x=>x.id)),
    ["5.3:L19","5.1:L12"]);
  assert.deepEqual(Array.from(r.positions.filter(x=>x.evidenceStatus==="DOCUMENT_CHECKLIST").map(x=>x.id)).sort(),
    ["4.2:L1","5.1:L1","5.3:L1"]);
  for(const x of r.positions){
    assert.equal(x.reviewPriority,"CRITICAL_PHASE3_RESEARCH");
    assert.equal(x.clinicalGrade,null);
    assert.equal(x.qualifiedReviewerSignoff,false);
    assert.equal(x.fdaProbability,null);
    assert.equal(x.sourceSnapshotAsOf,"2026-11-08");
    assert.ok(x.missingOriginalEvidence.length>19);
    assert.ok(x.sourceUrls.length>0);
    assert.ok(x.sourceUrls.every(u=>u.startsWith("https://")));
    assert.equal(x.sourceUrls.length,x.sourceIds.length);
  }
});
test("review queue is failed closed on replaced trial, corrupt NCT, tampered source and signed clinical data",()=>{
  const modifications=[
    p=>p.nct="NCT00000000",
    p=>p.phaseReported="PHASE2",
    p=>p.phaseIndependentReviewerVerified=true,
    p=>p.scientificFramework.positions=780,
    p=>p.scientificFramework.mappedCandidateMethodLeads=17,
    p=>p.scientificFramework.methodPositionsUnexamined=781,
    p=>p.scientificFramework.independentlyGradedMethodPositions=1,
    p=>p.scientificFramework.currentPhaseReviewSignoffs=1,
    p=>p.scientificFramework.independentlyCompletedAssessments=1,
    p=>p.finalDecision.approval="APPROVAL",
    p=>p.finalDecision.calibratedAccuracy=0.9,
    p=>p.sources.CTIS_AM04.sha256="0".repeat(64),
    p=>p.sources.NEJM_PIVOTAL.url="https://untrusted.example/publication",
    p=>p.sources.HCMS_CMR_20261106.url="https://untrusted.example/secondary",
    p=>p.criticalAssessmentEvidence[0].id="FAKE",
    p=>p.criticalAssessmentEvidence[0].candidateMethodIndices.push(20),
    p=>p.criticalAssessmentEvidence[0].sourceLeadIds=["FAKE"],
    p=>p.criticalAssessmentEvidence[0].sourceLeadIds.push("CTIS_AM04"),
    p=>p.criticalAssessmentEvidence[0].remaining="short",
    p=>p.criticalAssessmentEvidence.pop(),
    p=>p.publishedPrimary.finalSapVerified=true,
    p=>p.descriptiveSafety.find(x=>x.metric==="SPONSOR_REPORTED_SERIOUS_HEART_FAILURE_AE").treated=11,
    p=>p.additionalProvisionalResearchScores[0].reviewerSignedOff=true
  ];
  for(let i=0;i<modifications.length;i++){
    const p=clone();modifications[i](p);
    assert.equal(evaluate(p),null,"unexpected worklist release after modified source "+i);
  }
});
test("CSV preserves exactly 18 research leads, makes gaps transparent and protects spreadsheet formulas",()=>{
  const q=evaluate(clone()),csv=queueModule.reviewQueueCsv(q);
  assert.ok(q);
  const lines=csv.trimEnd().split("\r\n");
  assert.equal(lines.length,19);
  assert.match(lines[0],/Research order/);
  assert.match(lines[0],/Official clinical grade/);
  assert.match(csv,/5\.3:L19/);
  assert.match(csv,/5\.1:L12/);
  assert.match(csv,/UNSCORED/);
  assert.match(csv,/NOT SIGNED/);
  assert.match(csv,/ABSTAIN/);
  assert.doesNotMatch(csv,/PDUFA probability: 60%/);
  const p=clone();
  p.criticalAssessmentEvidence.find(x=>x.id==="4.1").remaining='=HYPERLINK("https://malicious.example","click") still requires source review';
  const formulaQueue=evaluate(p);
  assert.ok(formulaQueue);
  assert.match(queueModule.reviewQueueCsv(formulaQueue),/'=HYPERLINK\(/);
});
test("queue is authenticated, GET-only, and downloadable from the iPhone pilot screen",()=>{
  const api=fs.readFileSync(path.join(root,"app/api/predictions/medical-phase3-review-queue/route.ts"),"utf8");
  const ui=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotResearchReviewQueue.tsx"),"utf8");
  const parent=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotPredictionWorkup.tsx"),"utf8");
  assert.match(api,/hasSession\(/);
  assert.match(api,/authConfigured\(\)/);
  assert.match(api,/getAll\("nct"\)/);
  assert.match(api,/getAll\("format"\)/);
  assert.match(api,/private, no-store/);
  assert.match(api,/text\/csv/);
  assert.match(api,/reviewQueueCsv\(queue\)/);
  assert.doesNotMatch(api,/export async function POST/);
  assert.match(ui,/Open all 18 research method leads/);
  assert.match(ui,/Search scientific research queue/);
  assert.match(ui,/Filter research queue status/);
  assert.match(ui,/Clear filters/);
  assert.match(ui,/Export all 18 source leads as CSV/);
  assert.match(ui,/Open versioned review queue JSON/);
  assert.match(ui,/not a scientific outcome ranking/);
  assert.match(parent,/<PilotResearchReviewQueue nct=\{nct\}\/>/);
});
