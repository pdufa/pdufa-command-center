"use strict";
const {test}=require("node:test"),assert=require("node:assert/strict");
const crypto=require("node:crypto");
const {NCT,CYCLE,SCHEMA,ROLES,FILES,EVIDENCE,sha,packetMessage,verifyPacket}=
 require("../scripts/verify_r79_sap_lock_provenance_packet.cjs");

function fixture(){
 const keys=ROLES.map((role,i)=>{
  const pair=crypto.generateKeyPairSync("ed25519");
  return {keyId:"test-independent-"+i,role,
    organization:i===0?"TEST Sponsor Document Custodian":"TEST External Independent Stats",
    publicKeyPem:pair.publicKey.export({type:"spki",format:"pem"}),
    privateKey:pair.privateKey};
 });
 const sourceFiles={
  controlledSapBytes:Buffer.alloc(330,49),
  databaseLockAuditBytes:Buffer.alloc(310,50),
  unblindAccessAuditBytes:Buffer.alloc(305,51)
 };
 const packet={
  schema:SCHEMA,nct:NCT,cycleId:CYCLE,controlledSapVersion:"3.0 Amendment 2",
  printedDateDiscrepanciesResolved:true,amendmentChainAudited:true,
  events:EVIDENCE.map((eventType,i)=>({
   eventType,sourceFileKey:FILES[i],sourceSha256:sha(sourceFiles[FILES[i]]),
   atUtc:["2025-02-13T09:00:00Z","2025-02-20T10:00:00Z",
          "2025-02-21T15:00:00Z"][i]
  }))
 };
 packet.attestations=keys.map(k=>({
  keyId:k.keyId,role:k.role,
  signatureBase64:crypto.sign(null,packetMessage(packet),k.privateKey).toString("base64")
 }));
 const trustedKeys=Object.fromEntries(keys.map(k=>[k.keyId,{
  role:k.role,organization:k.organization,publicKeyPem:k.publicKeyPem
 }]));
 return {packet,sourceFiles,trustedKeys,keys};
}
const blocked=r=>{
 assert.equal(r.technicalAttestationCoherent,false);
 assert.match(r.status,/^BLOCKED_/);
 assert.equal(r.scientificSignedReviewReleased,false);
 assert.equal(r.clinicalGrade,null);
 assert.equal(r.FDAOutcome,"ABSTAIN");
 assert.equal(r.validatedFDAForecasts,0);
 assert.equal(r.productionWrites,false);
};
test("No original evidence or independently approved trust anchors means fail-closed",()=>{
 const t=fixture();
 blocked(verifyPacket(null));
 blocked(verifyPacket(t.packet));
 blocked(verifyPacket(t.packet,{sourceFiles:t.sourceFiles}));
 blocked(verifyPacket(t.packet,{trustedKeys:t.trustedKeys}));
});
test("synthetic signed evidence can show only packet technical coherence, never FDA score",()=>{
 const {packet,sourceFiles,trustedKeys}=fixture();
 const a=verifyPacket(packet,{sourceFiles,trustedKeys});
 assert.equal(a.status,"SIGNED_SOURCE_PACKET_COHERENT_NOT_CLINICALLY_APPROVED");
 assert.equal(a.technicalAttestationCoherent,true);
 assert.equal(a.scientificSignedReviewReleased,false);
 assert.equal(a.clinicalGrade,null);
 assert.equal(a.FDAOutcome,"ABSTAIN");
 assert.equal(a.reviewTiming,"UNKNOWN");
 assert.equal(a.validatedFDAForecasts,0);
 assert.equal(a.productionWrites,false);
});
test("SAP finalized before blind is the ordering constraint; SAP after DB lock is flagged not FDA approved",()=>{
 const t=fixture();
 t.packet.events[0].atUtc="2025-02-20T11:00:00Z";
 t.packet.attestations=t.keys.map(k=>({
  keyId:k.keyId,role:k.role,
  signatureBase64:crypto.sign(null,packetMessage(t.packet),k.privateKey).toString("base64")
 }));
 const out=verifyPacket(t.packet,{sourceFiles:t.sourceFiles,trustedKeys:t.trustedKeys});
 assert.equal(out.status,"SIGNED_SOURCE_PACKET_COHERENT_SAP_AFTER_LOCK_NEEDS_EXPERT_REVIEW");
 assert.equal(out.FDAOutcome,"ABSTAIN");
});
test("SAP approved after first unblinding and lock after unblinding are both rejected",()=>{
 for(const changed of [
  x=>x.events[0].atUtc="2025-02-22T10:00:00Z",
  x=>x.events[1].atUtc="2025-02-22T10:00:00Z",
  x=>x.events[0].atUtc="2025-02-21T15:00:00Z"
 ]){
  const t=fixture();changed(t.packet);
  t.packet.attestations=t.keys.map(k=>({
   keyId:k.keyId,role:k.role,
   signatureBase64:crypto.sign(null,packetMessage(t.packet),k.privateKey).toString("base64")
  }));
  const r=verifyPacket(t.packet,{sourceFiles:t.sourceFiles,trustedKeys:t.trustedKeys});
  assert.equal(r.status,"BLOCKED_SAP_OR_DATABASE_LOCK_NOT_BEFORE_FIRST_UNBLIND");
 }
});
test("Cross-NCT, forged source hashes, missing original bytes, untrusted signers and same-organization reviewers fail closed",()=>{
 const attacks=[
  t=>{t.packet.nct="NCT00000001"},
  t=>{t.packet.cycleId="capr-deramiocel"},
  t=>{t.packet.controlledSapVersion="SAP 4.0"},
  t=>{t.packet.printedDateDiscrepanciesResolved=false},
  t=>{t.packet.amendmentChainAudited=false},
  t=>{t.packet.events[0].sourceSha256="f".repeat(64)},
  t=>{t.packet.events[1].sourceFileKey="controlledSapBytes"},
  t=>{t.packet.events[2].eventType="PLANNED_UNBLIND"},
  t=>{t.packet.events[2].atUtc="not-iso"},
  t=>{t.sourceFiles.controlledSapBytes=Buffer.from("not original document bytes")},
  t=>{t.trustedKeys={}},
  t=>{t.trustedKeys["test-independent-0"].organization=t.trustedKeys["test-independent-1"].organization},
  t=>{t.packet.attestations[1].keyId=t.packet.attestations[0].keyId},
  t=>{t.packet.attestations[1].signatureBase64="Z".repeat(88)},
  t=>{t.packet.attestations[1].role="SPONSOR_RECORD_CUSTODIAN"},
  t=>{t.packet.attestations.pop()},
  t=>{t.packet.clinicalGrade=20},
  t=>{t.packet.events[0].FDAOutcome="APPROVED"},
  t=>{t.packet.attestations[0].sourceIsOfficial=true},
  t=>{t.packet.events[0].atUtc="2025-02-30T09:00:00Z"},
  t=>{t.packet.events[0].atUtc="2025-13-13T09:00:00Z"}
 ];
 attacks.forEach((attack,i)=>{
  const t=fixture();attack(t);
  const r=verifyPacket(t.packet,{sourceFiles:t.sourceFiles,trustedKeys:t.trustedKeys});
  assert.equal(r.technicalAttestationCoherent,false,"attack "+i);
  blocked(r);
 });
});
test("No clinician authorization keys are shipped in the repository test or source bundle",()=>{
 const fs=require("node:fs");
 const x=fs.readFileSync(require("node:path").join(__dirname,"../scripts/verify_r79_sap_lock_provenance_packet.cjs"),"utf8");
 assert.doesNotMatch(x,/-----BEGIN (?:PRIVATE|PUBLIC) KEY-----/);
 assert.match(x,/trustedKeys=\{\}/);
});
