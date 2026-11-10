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
  const js=ts.transpileModule(input,{compilerOptions:{
    target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS
  }}).outputText;
  const mod={exports:{}};
  vm.runInNewContext(js,{module:mod,exports:mod.exports,URL,
    require:(name)=>{if(Object.hasOwn(imports,name))return imports[name];
      throw Error("Unapproved require "+name);}
  },{timeout:1000});
  return mod.exports;
}
const quant=load("lib/acacia-quantitative-science.ts");
const rubric=load("lib/phase3-clinical-quality-rubric.ts");
const ready=load("lib/pilot-research-readiness.ts");
const queueLib=load("lib/acacia-phase3-review-queue.ts",{
  "./acacia-quantitative-science":quant,
  "./phase3-clinical-quality-rubric":rubric,
  "./pilot-research-readiness":ready
});
const packetLib=load("lib/acacia-evidence-acquisition-handoff.ts");
const make=()=>packetLib.buildAcaciaAcquisitionHandoff(queueLib.buildPhase3ReviewQueue(structuredClone(pilot)));

test("six precise source requests cover all 18 mapped clinical research positions without grades",()=>{
  const p=make();
  assert.ok(p);
  assert.equal(p.schema,"MAIN_ACACIA_EVIDENCE_ACQUISITION_HANDOFF_V1");
  assert.equal(p.nct,"NCT06081894");
  assert.equal(p.protocol,"CY 6033");
  assert.equal(p.sourceSnapshotAsOf,"2026-11-08");
  assert.equal(p.requests.length,6);
  assert.equal(p.requestCount,6);
  assert.equal(p.mappedMethodPositionsCovered,18);
  assert.equal(p.unmappedPositionsUnreviewed,782);
  assert.equal(p.sourceAuditRuns.safetyAndSap,42555289486);
  assert.equal(p.sourceAuditRuns.alternativePublisher,42556948533);
  const mapped=new Set(queueLib.buildPhase3ReviewQueue(structuredClone(pilot)).positions.map(x=>x.id));
  const covered=new Set(p.requests.flatMap(x=>x.mappedMethodPositions));
  assert.deepEqual(Array.from(covered).sort(),Array.from(mapped).sort());
  assert.equal(new Set(p.requests.map(x=>x.requestId)).size,6);
  for(const request of p.requests){
    assert.equal(request.evidenceState,"NOT_AUTHENTICATED_FOR_CURRENT_REVIEW");
    assert.equal(request.acquisitionState,"DRAFT_NOT_SENT");
    assert.equal(request.independentReviewerSigned,false);
    assert.equal(request.officialClinicalGrade,null);
    assert.ok(request.preciseOriginalEvidenceNeeded.length>50);
    assert.ok(request.howToIndependentlyVerify.length>45);
  }
  assert.equal(p.approvedClinicalGrades,0);
  assert.equal(p.independentPhaseSignoffs,0);
  assert.equal(p.externallyAuthenticatedNewDocuments,0);
  assert.equal(p.requestDeliveryStatus,"DRAFT_ONLY_NOT_SENT");
  assert.equal(p.fdaPrediction,"ABSTAIN");
  assert.equal(p.accuracy,"NOT_CALIBRATED");
  assert.equal(p.noPatientLevelDataStored,true);
});
test("source gaps distinguish locked primary SAP, primary sensitivity and two differing HF SAE reports",()=>{
  const p=make();assert.ok(p);
  const sap=p.requests.find(x=>x.requestId==="LOCKED_PRIMARY_SAP");
  const primary=p.requests.find(x=>x.requestId==="PRIMARY_SENSITIVITY_AND_MISSINGNESS");
  const hf=p.requests.find(x=>x.requestId==="HF_SAE_EVENT_DEFINITION");
  const denominators=p.requests.find(x=>x.requestId==="SAFETY_DENOMINATORS_EXPOSURE");
  const regulatory=p.requests.find(x=>x.requestId==="EXACT_NHCM_REGULATORY_STATUS");
  assert.match(sap.preciseOriginalEvidenceNeeded,/dated\/locked/);
  assert.match(primary.howToIndependentlyVerify,/do not substitute a secondary responder analysis/);
  assert.match(hf.preciseOriginalEvidenceNeeded,/11 treated\/1 placebo/);
  assert.match(hf.preciseOriginalEvidenceNeeded,/12 treated\/3 placebo/);
  assert.match(hf.howToIndependentlyVerify,/does not by itself reconcile 11\/1/);
  assert.match(denominators.preciseOriginalEvidenceNeeded,/time at risk/);
  assert.match(regulatory.title,/nonobstructive HCM/);
  assert.equal(p.recipientForResearchEligibilityInquiry,"medicalaffairs@cytokinetics.com");
  assert.equal(p.dataAccessIsSubjectTo,"SPONSOR_ELIGIBILITY_TIMING_REVIEW_AND_AGREEMENT");
});
test("any changed trial, source access, clinical grade, or roster invalidates handoff",()=>{
  const valid=queueLib.buildPhase3ReviewQueue(structuredClone(pilot));
  assert.ok(valid);
  const changes=[
    x=>{x.nct="NCT00000000";},
    x=>{x.sourceSnapshotAsOf="2025-01-01";},
    x=>{x.status="SIGNED_GRADE";},
    x=>{x.summary.mappedSourceLeads=17;},
    x=>{x.summary.officialClinicalGrades=1;},
    x=>{x.summary.qualifiedPhaseSignoffs=1;},
    x=>{x.fdaPrediction="APPROVAL";},
    x=>{x.calibratedAccuracy=.99;},
    x=>{x.alternativeSourceRecovery.archivedAuditRun=4;},
    x=>{x.alternativeSourceRecovery.sponsorResearchContact="other@example.com";},
    x=>{x.alternativeSourceRecovery.automaticRequestSent=true;},
    x=>{x.alternativeSourceRecovery.finalLockedPrimarySapAuthenticated=true;},
    x=>{x.positions[0].id="FAKE";},
    x=>{x.positions[0].clinicalGrade=4;},
    x=>{x.positions[0].qualifiedReviewerSignoff=true;},
    x=>{x.positions.pop();}
  ];
  for(let i=0;i<changes.length;i++){
    const q=structuredClone(valid);changes[i](q);
    assert.equal(packetLib.buildAcaciaAcquisitionHandoff(q),null,"Unexpected packet after tampered field "+i);
  }
  assert.equal(packetLib.buildAcaciaAcquisitionHandoff(null),null);
});
test("downloadable draft is explicitly unsent, no patient identifiers or external action",()=>{
  const packet=make(),txt=packetLib.acquisitionDraftText(packet);
  assert.match(txt,/DRAFT — NOT SENT/);
  assert.match(txt,/To: medicalaffairs@cytokinetics.com/);
  assert.match(txt,/NCT06081894/);
  assert.match(txt,/CY 6033/);
  assert.match(txt,/not asking for unauthorized participant-level data/);
  assert.match(txt,/1\. Final locked primary/);
  assert.match(txt,/6\. Source-verified FDA status/);
  assert.match(txt,/This draft has not been sent/);
  assert.doesNotMatch(txt,/patient name|date of birth|access token/i);
  const ui=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotEvidenceAcquisitionPacket.tsx"),"utf8");
  const parent=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotPredictionWorkup.tsx"),"utf8");
  const api=fs.readFileSync(path.join(root,"app/api/predictions/medical-evidence-acquisition/route.ts"),"utf8");
  assert.match(ui,/Expand six original evidence requests/);
  assert.match(ui,/Download unsent inquiry draft/);
  assert.match(ui,/Open versioned acquisition packet/);
  assert.match(ui,/No request has been sent/);
  assert.match(parent,/<PilotEvidenceAcquisitionPacket nct=\{nct\}\/>/);
  assert.match(api,/authConfigured\(\)/);
  assert.match(api,/hasSession\(/);
  assert.match(api,/getAll\("nct"\)/);
  assert.match(api,/private, no-store/);
  assert.match(api,/attachment; filename=/);
  assert.match(api,/DRAFT-NOT-SENT/);
  assert.doesNotMatch(api,/export async function POST/);
  assert.doesNotMatch(api,/sendMail|gmail|fetch\(/i);
});
