"use strict";
// Revision 17: pilot researcher handoffs are source leads, NOT signed grades.
// Keep the 800-position scientific method matrix and its live ledger separate.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const pilot=JSON.parse(fs.readFileSync(path.join(root,"data","acacia-pilot-prediction-workup-20261108.json"),"utf8"));
const view=fs.readFileSync(path.join(root,"app","predictions","assessment","PilotPredictionWorkup.tsx"),"utf8");

test("Revision 16 research packet has exactly eighteen unique mapped 40 x 20 leads",()=>{
  assert.equal(pilot.nct,"NCT06081894");
  assert.equal(pilot.protocolCode,"CY 6033");
  assert.equal(pilot.scientificFramework.layers,8);
  assert.equal(pilot.scientificFramework.assessments,40);
  assert.equal(pilot.scientificFramework.methodsPerAssessment,20);
  assert.equal(pilot.scientificFramework.positions,800);
  const mapped=new Set();
  for(const row of pilot.criticalAssessmentEvidence){
    assert.match(row.id,/^[1-8]\.[1-5]$/);
    assert.ok(row.candidateMethodIndices.length>0);
    for(const i of row.candidateMethodIndices){
      assert.ok(Number.isInteger(i)&&i>=1&&i<=20);
      const key=row.id+":"+i;
      assert.ok(!mapped.has(key),"duplicate research position "+key);
      mapped.add(key);
    }
    for(const source of row.sourceLeadIds)assert.ok(Object.hasOwn(pilot.sources,source),"missing source "+source);
  }
  assert.equal(pilot.criticalAssessmentEvidence.length,11);
  assert.equal(mapped.size,18);
  assert.equal(pilot.scientificFramework.mappedCandidateMethodLeads,18);
  assert.equal(pilot.scientificFramework.methodPositionsUnexamined,800-mapped.size);
  for(const id of ["4.3:4","5.4:4","8.2:4"])assert.ok(mapped.has(id));
});
test("source receipts remain attributable without qualifying as scientific grades",()=>{
  const f=pilot.scientificFramework;
  assert.equal(f.researchBoundedFindings,9);
  assert.equal(f.packetSourceReceiptCount,7);
  assert.equal(f.packetBlockedOriginalSourceRequests,1);
  assert.equal(f.currentPhaseReviewSignoffs,0);
  assert.equal(f.independentlyGradedMethodPositions,0);
  assert.equal(f.independentlyCompletedAssessments,0);
  assert.equal(f.methodGradeRecommendations,0);
  assert.equal(pilot.phaseIndependentReviewerVerified,false);
  for(const v of Object.values(pilot.finalDecision).filter(v=>typeof v==="string")){
    if(v==="ABSTAIN")assert.equal(v,"ABSTAIN");
  }
  for(const k of ["approval","crl","reviewDelay"])assert.equal(pilot.finalDecision[k],"ABSTAIN");
  assert.equal(pilot.finalDecision.calibratedAccuracy,null);
  assert.equal(pilot.finalDecision.calibratedProbabilities,null);
  for(const [id,src] of Object.entries(pilot.sources)){
    const url=new URL(src.url);
    assert.equal(url.protocol,"https:",id);
    assert.ok(!url.username&&!url.password);
    if(src.retrieved===true)assert.match(src.sha256,/^[a-f0-9]{64}$/,id);
  }
  assert.equal(pilot.sources.FDA_ORIGINAL_OHCM_2025.retrieved,true);
  assert.equal(pilot.sources.HCMS_CMR_20261106.retrieved,true);
  assert.equal(pilot.sources.HCMS_KCCQ_OSS_20261106.retrieved,true);
});
test("pilot page communicates dated source leads, missing methods and unresolved safety accounting",()=>{
  assert.match(view,/Research source handoff progress/);
  assert.match(view,/methodPositionsUnexamined/);
  assert.match(view,/researchBoundedFindings/);
  assert.match(view,/methodGradeRecommendations/);
  assert.match(view,/revision16Packet/);
  assert.match(view,/Safety discrepancy audit/);
  assert.match(view,/11 treated participants and 1 placebo participant/);
  assert.match(view,/12 and 3/);
  assert.match(view,/not been reconciled/);
  assert.match(view,/not.*(?:a|an) (?:FDA )?prediction/i);
});
