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
  const code=fs.readFileSync(path.join(root,src),"utf8");
  const js=ts.transpileModule(code,{compilerOptions:{
    target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS
  }}).outputText;
  const mod={exports:{}};
  vm.runInNewContext(js,{module:mod,exports:mod.exports,require:(name)=>{
    if(Object.hasOwn(imports,name))return imports[name];
    throw Error("Unapproved module "+name);
  },URL,Date,TextEncoder},{timeout:1500});
  return mod.exports;
}
const quant=load("lib/acacia-quantitative-science.ts");
const rubric=load("lib/phase3-clinical-quality-rubric.ts");
const ready=load("lib/pilot-research-readiness.ts");
const queue=load("lib/acacia-phase3-review-queue.ts",{
  "./acacia-quantitative-science":quant,
  "./phase3-clinical-quality-rubric":rubric,
  "./pilot-research-readiness":ready
});
const acquire=load("lib/acacia-evidence-acquisition-handoff.ts");
const intake=load("lib/acacia-evidence-intake-precheck.ts");
const packet=()=>acquire.buildAcaciaAcquisitionHandoff(
  queue.buildPhase3ReviewQueue(structuredClone(pilot))
);
const candidate=()=>({
  nct:"NCT06081894",requestId:"LOCKED_PRIMARY_SAP",
  documentType:"STATISTICAL_ANALYSIS_PLAN",
  documentTitle:"Original ACACIA HCM statistical analysis plan candidate",
  documentVersion:"Final v1.0",
  documentDate:"2026-11-01",
  sourceUrl:"https://clinicaltrials.gov/study/NCT06081894",
  claimedSha256:"a".repeat(64)
});

test("valid metadata NEVER proves original source bytes, ownership, reviewer approval, grades or FDA odds",()=>{
  const p=packet(),r=intake.validateAcaciaIntakeCandidate(candidate(),p);
  assert.ok(r);
  assert.equal(r.schema,"MAIN_ACACIA_EVIDENCE_INTAKE_PRECHECK_V1");
  assert.equal(r.nct,"NCT06081894");
  assert.equal(r.requestId,"LOCKED_PRIMARY_SAP");
  assert.equal(r.inputCheck,"METADATA_FORMAT_CHECKED_ONLY");
  assert.deepEqual(Array.from(r.issueCodes),[]);
  assert.deepEqual(Array.from(r.linkedMethodPositions),Array.from(
    p.requests.find(x=>x.requestId==="LOCKED_PRIMARY_SAP").mappedMethodPositions));
  assert.equal(r.sourceUrlHostAllowlisted,true);
  for(const k of ["sourceContentRetrieved","claimedDocumentHashVerifiedFromOriginalBytes",
    "documentVersionAuthenticated","sourceOwnershipIndependentlyVerified",
    "sponsorDataSharingAuthorizationVerified","clinicalReviewerSignedOff",
    "acceptedForClinicalScoring","persisted","emailSent"])assert.equal(r[k],false,k);
  assert.equal(r.clinicalGrade,null);
  assert.equal(r.gradeEventsWritten,0);
  assert.equal(r.uploadsReceived,0);
  assert.equal(r.fdaPrediction,"ABSTAIN");
  assert.equal(r.accuracy,"NOT_CALIBRATED");
  assert.equal(r.reviewerActionRequired.length,5);
  assert.match(r.nextStage,/ORIGINAL_BYTES/);
});
test("all six document categories map precisely to original acquisition request scope",()=>{
  const p=packet();assert.ok(p);
  const types=intake.intakeDocumentTypes();
  assert.equal(types.length,6);
  for(const item of types){
    const c=candidate();
    c.requestId=item.requestId;c.documentType=item.documentType;
    const r=intake.validateAcaciaIntakeCandidate(c,p);
    assert.equal(r.inputCheck,"METADATA_FORMAT_CHECKED_ONLY",item.requestId);
    assert.deepEqual(Array.from(r.linkedMethodPositions),Array.from(
      p.requests.find(x=>x.requestId===item.requestId).mappedMethodPositions
    ));
    assert.equal(r.acceptedForClinicalScoring,false);
  }
});
test("reject all metadata spoofing, empty digest and unsafe source URLs without clinical event",()=>{
  const edits=[
    c=>{c.nct="NCT00000000";},
    c=>{c.requestId="OTHER_STUDY";},
    c=>{c.documentType="REGULATORY_SOURCE";},
    c=>{c.documentTitle="<script>alert(1)</script>";},
    c=>{c.documentTitle="Short";},
    c=>{c.documentVersion="";},
    c=>{c.documentDate="2026-02-30";},
    c=>{c.documentDate="tomorrow";},
    c=>{c.sourceUrl="http://clinicaltrials.gov/study/NCT06081894";},
    c=>{c.sourceUrl="https://clinicaltrials.gov.evil.example/study/NCT06081894";},
    c=>{c.sourceUrl="https://127.0.0.1/source";},
    c=>{c.sourceUrl="https://other.example/source";},
    c=>{c.sourceUrl="https://clinicaltrials.gov/study/NCT06081894?token=secret";},
    c=>{c.sourceUrl="https://user:pass@clinicaltrials.gov/study/NCT06081894";},
    c=>{c.sourceUrl="https://clinicaltrials.gov:5555/study/NCT06081894";},
    c=>{c.claimedSha256="";},
    c=>{c.claimedSha256="not-a-hash";},
    c=>{c.claimedSha256="A".repeat(64);},
    c=>{c.patientName="Sensitive Person";},
  ];
  for(let i=0;i<edits.length;i++){
    const c=candidate();edits[i](c);
    const r=intake.validateAcaciaIntakeCandidate(c,packet());
    assert.ok(r,"precheck should give reason codes "+i);
    assert.equal(r.inputCheck,"REJECTED_METADATA","unexpected metadata accepted "+i);
    assert.ok(r.issueCodes.length>=1);
    assert.equal(r.gradeEventsWritten,0);
    assert.equal(r.sourceContentRetrieved,false);
    assert.equal(r.acceptedForClinicalScoring,false);
    assert.equal(r.persisted,false);
  }
});
test("unknown inputs, tampered packet and clinical grade state never pass",()=>{
  assert.equal(intake.validateAcaciaIntakeCandidate(null,packet()),null);
  assert.equal(intake.validateAcaciaIntakeCandidate([],packet()),null);
  assert.equal(intake.validateAcaciaIntakeCandidate(candidate(),null),null);
  const p=packet();assert.ok(p);
  const updates=[
    q=>{q.nct="NCT99999999";},
    q=>{q.requestDeliveryStatus="SENT";},
    q=>{q.approvedClinicalGrades=1;},
    q=>{q.independentPhaseSignoffs=1;},
    q=>{q.externallyAuthenticatedNewDocuments=1;},
    q=>{q.fdaPrediction="APPROVAL";},
    q=>{q.accuracy="CALIBRATED";},
    q=>{q.requestCount=5;},
    q=>{q.requests[0].independentReviewerSigned=true;},
    q=>{q.requests[0].officialClinicalGrade=5;}
  ];
  for(let i=0;i<updates.length;i++){
    const q=structuredClone(p);updates[i](q);
    assert.equal(intake.validateAcaciaIntakeCandidate(candidate(),q),null,
      "tampered existing clinical state must withhold "+i);
  }
});
test("UI hashes locally but sends JSON metadata only; API enforces origin, session, cap and no persistence",()=>{
  const ui=fs.readFileSync(path.join(root,
    "app/predictions/assessment/PilotEvidenceIntakePrecheck.tsx"),"utf8");
  const parent=fs.readFileSync(path.join(root,
    "app/predictions/assessment/PilotPredictionWorkup.tsx"),"utf8");
  const api=fs.readFileSync(path.join(root,
    "app/api/predictions/medical-evidence-intake-precheck/route.ts"),"utf8");
  assert.match(ui,/Original document intake/);
  assert.match(ui,/crypto\.subtle\.digest\("SHA-256",bytes\)/);
  assert.match(ui,/selected file/);
  assert.match(ui,/JSON\.stringify\(candidate\)/);
  assert.match(ui,/metadata—not file contents/);
  assert.match(ui,/Check metadata only — do not save/);
  assert.match(parent,/<PilotEvidenceIntakePrecheck nct=\{nct\}\/>/);
  assert.match(api,/authConfigured\(\)/);
  assert.match(api,/hasSession\(/);
  assert.match(api,/req\.headers\.get\("origin"\)!==req\.nextUrl\.origin/);
  assert.match(api,/MAX_BODY=12_000/);
  assert.match(api,/application/);
  assert.match(api,/private, no-store/);
  assert.match(api,/export async function POST/);
  assert.doesNotMatch(api,/export async function (PUT|PATCH|DELETE)/);
  assert.doesNotMatch(api,/sendMail|gmail|writeFile|INSERT INTO|update_file|medical_ledger|fetch\(/i);
});

test("encrypted vault is accurately labeled staged-only and never falsely claims active storage",()=>{
  const ui=fs.readFileSync(path.join(root,
    "app/predictions/assessment/PilotEncryptedEvidenceVaultStatus.tsx"),"utf8");
  const parent=fs.readFileSync(path.join(root,
    "app/predictions/assessment/PilotPredictionWorkup.tsx"),"utf8");
  assert.match(ui,/STAGED IN BACKEND CODE — NOT ACTIVATED/);
  assert.match(ui,/Disposable PostgreSQL 16 acceptance: PASSED/);
  assert.match(ui,/offline synthetic key-recovery drill/);
  assert.match(ui,/42562929833/);
  assert.match(ui,/not a deployment, offsite key backup/);
  assert.match(ui,/AES-256-GCM/);
  assert.match(ui,/not connected to this browser or storing documents yet/);
  assert.match(ui,/NOT ACTIVE/);
  assert.match(ui,/Original documents deposited:/);
  assert.match(ui,/0\/800/);
  assert.match(ui,/FDA prediction/);
  assert.match(ui,/does not support Neon branchable object storage/);
  assert.match(ui,/No keys are stored/);
  assert.match(parent,/<PilotEncryptedEvidenceVaultStatus nct=\{nct\}\/\>/);
});
