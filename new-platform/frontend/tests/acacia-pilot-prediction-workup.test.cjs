const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const pilot=JSON.parse(fs.readFileSync(path.join(root,"data/acacia-pilot-prediction-workup-20261108.json"),"utf8"));
const catalog=JSON.parse(fs.readFileSync(path.resolve(__dirname,"../../backend/app/data/medical_phase_assessment_catalog.json"),"utf8"));
const widget=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotPredictionWorkup.tsx"),"utf8");
const live=fs.readFileSync(path.join(root,"app/predictions/assessment/LivePredictionMonitor.tsx"),"utf8");
const parent=fs.readFileSync(path.join(root,"app/predictions/assessment/ScientificMethodMatrix.tsx"),"utf8");

test("pilot workup is bound to the exact trial, correct program, and zero validated predictions",()=>{
  assert.equal(pilot.nct,"NCT06081894");
  assert.equal(pilot.protocolCode,"CY 6033");
  assert.match(pilot.indication,/nonobstructive/i);
  assert.equal(pilot.phaseIndependentReviewerVerified,false);
  assert.equal(pilot.scientificFramework.positions,800);
  assert.equal(pilot.scientificFramework.independentlyGradedMethodPositions,0);
  assert.equal(pilot.scientificFramework.independentlyCompletedAssessments,0);
  assert.equal(pilot.finalDecision.approval,"ABSTAIN");
  assert.equal(pilot.finalDecision.crl,"ABSTAIN");
  assert.equal(pilot.finalDecision.reviewDelay,"ABSTAIN");
  assert.equal(pilot.finalDecision.certainty,"NOT_VALIDATED");
  assert.equal(pilot.finalDecision.calibratedAccuracy,null);
  assert.equal(pilot.finalDecision.calibratedProbabilities,null);
  assert.equal(pilot.researchHypothesis.notAProbability,true);
  assert.equal(pilot.researchHypothesis.unvalidated,true);
});

test("all critical phase 3 assessment headings and method leads exist in current catalog",()=>{
  const ids=catalog.phasePriority.critical.PHASE3;
  assert.equal(ids.length,11);
  assert.deepEqual(pilot.criticalAssessmentEvidence.map(x=>x.id),ids);
  assert.equal(pilot.scientificFramework.criticalHeadingsWithSourceLeads,11);
  const expectedMethods=new Set(catalog.methods.map(m=>m.id));
  const unique=new Set();
  for(const a of pilot.criticalAssessmentEvidence){
    assert.ok(a.sourceLeadIds.length>=1);
    assert.ok(a.remaining.length>=20);
    for(const id of a.sourceLeadIds)assert.ok(pilot.sources[id], "unknown source id "+id);
    for(const method of a.candidateMethodIndices){
      assert.ok(expectedMethods.has(method));
      const position=a.id+":L"+method;
      assert.equal(unique.has(position),false,"duplicate "+position);
      unique.add(position);
    }
  }
  assert.equal(unique.size,18);
  assert.equal(pilot.scientificFramework.mappedCandidateMethodLeads,18);
  assert.equal(pilot.scientificFramework.methodPositionsUnexamined,782);
  assert.equal(pilot.scientificFramework.researchBoundedFindings,9);
  assert.match(pilot.scientificFramework.candidateMeaning,/NOT_A_REVIEW_EVENT_OR_GRADE/);
  assert.equal(pilot.scientificFramework.everyMappedMethodGraded,false);
});

test("published endpoint and adverse-event arithmetic is independently reproducible",()=>{
  assert.equal(pilot.publishedPrimary.randomized.aficamten,258);
  assert.equal(pilot.publishedPrimary.randomized.placebo,259);
  assert.equal(pilot.publishedPrimary.kccq.difference,3);
  assert.deepEqual(pilot.publishedPrimary.kccq.ci95,[0.5,5.5]);
  assert.equal(pilot.publishedPrimary.peakVo2.difference,0.67);
  assert.deepEqual(pilot.publishedPrimary.peakVo2.ci95,[0.22,1.11]);
  for(const row of pilot.descriptiveSafety){
    assert.ok(/^https:\/\//.test(row.source));
    assert.equal(Math.round(row.treated/row.treatedN*1000)/10,row.treatedPct);
    assert.equal(Math.round(row.control/row.controlN*1000)/10,row.controlPct);
    assert.equal(Math.round((row.treated/row.treatedN-row.control/row.controlN)*10000)/100,row.unadjustedRiskDifferencePp);
  }
  assert.equal(pilot.fdaCycle.date,null);
  assert.equal(pilot.fdaCycle.otherIndicationPdufaMustNotCopy,true);
});

test("prediction and accuracy appear above installation but never as invented calibrated numbers",()=>{
  assert.match(live,/FDA PREDICTION/);
  assert.match(live,/ACCURACY RATING/);
  assert.match(live,/NOT CALIBRATED/);
  assert.match(widget,/Historical evidence snapshot/);
  assert.match(widget,/Conditional regulatory scenarios/);
  assert.match(widget,/Source leads in/);
  assert.match(widget,/A mapped research handoff is neither an independently examined clinical test nor an FDA prediction/);
  assert.match(widget,/if\(nct!==facts.nct \|\| nct!==pilot.nct\)return null/);
  assert.ok(parent.indexOf("<PilotPredictionWorkup nct={nct} />")<parent.indexOf("<ScientificInstallationStatus />"));
  assert.ok(parent.indexOf("<PilotPredictionWorkup nct={nct} />")<parent.indexOf("<PhaseVerificationPanel nct={nct} />"));
});
