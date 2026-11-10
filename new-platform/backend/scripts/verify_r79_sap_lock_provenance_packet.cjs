"use strict";
/** MAIN R79 — research-only signed SAP/DB lock/first-unblind evidence packet.
 * Technical packet integrity, NOT FDA acceptance, clinical signoff or forecast.
 * Public keys are supplied by a separately approved external trust store;
 * NONE are auto-inferred from an uploaded file or case JSON.
 */
const crypto=require("node:crypto");
const NCT="NCT06153693";
const CYCLE="mlys-lorundrostat";
const SCHEMA="MAIN_R79_SAP_LOCK_SOURCE_ATTESTATION_PACKET_RESEARCH_ONLY";
const EVIDENCE=["SAP_FINALIZED","FINAL_DATABASE_LOCK","FIRST_UNBLINDED_ACCESS"];
const FILES=["controlledSapBytes","databaseLockAuditBytes","unblindAccessAuditBytes"];
const ROLES=["SPONSOR_RECORD_CUSTODIAN","INDEPENDENT_STATISTICAL_REVIEWER"];
const HASH=/^[a-f0-9]{64}$/;
const ISO=/^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,3})?Z$/;
function sha(data){return crypto.createHash("sha256").update(data).digest("hex");}
function fail(code){return {status:"BLOCKED_"+code,technicalAttestationCoherent:false,
  scientificSignedReviewReleased:false,clinicalGrade:null,FDAOutcome:"ABSTAIN",
  reviewTiming:"UNKNOWN",validatedFDAForecasts:0,productionWrites:false};}
function packetMessage(packet){
  // Fixed, bounded, deterministic canonical message; no attacker-controlled
  // extra claims or user-provided public-key strings are signed implicitly.
  return Buffer.from(JSON.stringify({
    schema:packet.schema,nct:packet.nct,cycleId:packet.cycleId,
    controlledSapVersion:packet.controlledSapVersion,
    events:packet.events.map(x=>({
      eventType:x.eventType,atUtc:x.atUtc,
      sourceFileKey:x.sourceFileKey,sourceSha256:x.sourceSha256
    })),
    printedDateDiscrepanciesResolved:packet.printedDateDiscrepanciesResolved,
    amendmentChainAudited:packet.amendmentChainAudited
  }),"utf8");
}
function verifyPacket(packet,{sourceFiles={},trustedKeys={}}={}){
  try{
    if(!packet||typeof packet!=="object"||Array.isArray(packet)||
      packet.schema!==SCHEMA||packet.nct!==NCT||packet.cycleId!==CYCLE||
      packet.controlledSapVersion!=="3.0 Amendment 2"||
      packet.printedDateDiscrepanciesResolved!==true||
      packet.amendmentChainAudited!==true||
      !Array.isArray(packet.events)||packet.events.length!==3||
      !Array.isArray(packet.attestations)||packet.attestations.length!==2)
      return fail("MISSING_OR_UNVERIFIED_CONTROLLED_SOURCE");
    const times=[];
    for(let i=0;i<3;i++){
      const e=packet.events[i];
      if(!e||e.eventType!==EVIDENCE[i]||e.sourceFileKey!==FILES[i]||
         typeof e.sourceSha256!=="string"||!HASH.test(e.sourceSha256)||
         typeof e.atUtc!=="string"||!ISO.test(e.atUtc))
        return fail("EVENT_SCHEMA_OR_SOURCE_PROVENANCE");
      const time=Date.parse(e.atUtc);
      if(!Number.isFinite(time)||new Date(time).toISOString().slice(0,19)!==
           new Date(e.atUtc).toISOString().slice(0,19))
        return fail("INVALID_AUDIT_TIMESTAMP");
      times.push(time);
      const bytes=sourceFiles[e.sourceFileKey];
      if(!Buffer.isBuffer(bytes)||bytes.length<100||bytes.length>12_000_000||
         sha(bytes)!==e.sourceSha256)
        return fail("SOURCE_BYTES_NOT_INDEPENDENTLY_HASH_MATCHED");
    }
    if(times[0]>=times[2]||times[1]>=times[2]){
      return fail("SAP_OR_DATABASE_LOCK_NOT_BEFORE_FIRST_UNBLIND");
    }
    const message=packetMessage(packet);
    const signers=new Set(),orgs=new Set();
    for(let i=0;i<ROLES.length;i++){
      const att=packet.attestations[i];
      if(!att||att.role!==ROLES[i]||typeof att.keyId!=="string"||
        typeof att.signatureBase64!=="string"||att.signatureBase64.length<60)
        return fail("INDEPENDENT_ATTESTATION_MISSING");
      const anchor=Object.prototype.hasOwnProperty.call(trustedKeys,att.keyId)?
        trustedKeys[att.keyId]:null;
      if(!anchor||anchor.role!==att.role||
         typeof anchor.publicKeyPem!=="string"||typeof anchor.organization!=="string"||
         anchor.organization.length<3||signers.has(att.keyId)||
         orgs.has(anchor.organization))
        return fail("TRUST_ANCHOR_NOT_INDEPENDENTLY_APPROVED");
      signers.add(att.keyId);orgs.add(anchor.organization);
      const signature=Buffer.from(att.signatureBase64,"base64");
      if(signature.length!==64||signature.toString("base64")!==att.signatureBase64||
         !crypto.verify(null,message,anchor.publicKeyPem,signature))
        return fail("INVALID_ATTESTATION_SIGNATURE");
    }
    return {status:times[0]>times[1]?
       "SIGNED_SOURCE_PACKET_COHERENT_SAP_AFTER_LOCK_NEEDS_EXPERT_REVIEW":
       "SIGNED_SOURCE_PACKET_COHERENT_NOT_CLINICALLY_APPROVED",
      technicalAttestationCoherent:true,
      scientificSignedReviewReleased:false,clinicalGrade:null,
      FDAOutcome:"ABSTAIN",reviewTiming:"UNKNOWN",
      validatedFDAForecasts:0,productionWrites:false};
  }catch(_err){return fail("UNTRUSTED_PACKET_REJECTED");}
}
module.exports={SCHEMA,NCT,CYCLE,EVIDENCE,FILES,ROLES,packetMessage,verifyPacket,sha};
