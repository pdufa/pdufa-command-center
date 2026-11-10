#!/usr/bin/env node
"use strict";
/** MAIN R80 offline original evidence intake.
 * Does not call networks, archive source records, issue clinical grades, or
 * allow repository-supplied or self-declared signing keys.
 */
const fs=require("node:fs");
const crypto=require("node:crypto");
const path=require("node:path");
const {verifyPacket,NCT,CYCLE,sha}=require("./verify_r79_sap_lock_provenance_packet.cjs");
const PIN_ENV="MAIN_R80_OWNER_APPROVED_TRUST_REGISTRY_SHA256";
const MAX_PACKET=150_000,MAX_TRUST=150_000,MAX_DOC=12_000_000;
const SHA_RE=/^[0-9a-f]{64}$/;
function response(status,details={}){
 return {schema:"MAIN_R80_OFFLINE_AUTHENTIC_SOURCE_INTAKE_RECEIPT",
  nct:NCT,cycleId:CYCLE,status,
  technicalSignatureValidation:"NOT_COMPLETED",
  authenticatedScientificAssessment:false,
  trustedReviewerApprovalsObtained:0,
  validOriginalSourceRecordsRecorded:0,
  sourceFileNamesOrContentsArchived:false,
  reviewerIdentityKeysArchived:false,
  originalSAPProspectivelyLockedCertified:false,
  FDAOutcome:"ABSTAIN",futureFDATiming:"UNKNOWN",
  clinicalGrade:null,calibratedAccuracy:null,
  productionOrModelTrainingWrites:false,...details};
}
function readBounded(file,max){
 const s=fs.statSync(file);
 if(!s.isFile()||s.size<1||s.size>max)throw Error("SOURCE_NOT_A_BOUNDED_FILE");
 return fs.readFileSync(file);
}
function parseArgs(argv){
 const allowed=new Set(["--packet","--sap","--lock","--unblind","--trusted-keys","--report"]);
 const out={};
 for(let i=0;i<argv.length;i+=2){
  const k=argv[i],v=argv[i+1];
  if(!allowed.has(k)||typeof v!=="string"||v.startsWith("--")||out[k])
   throw Error("INVALID_INTAKE_ARGUMENTS");
  out[k]=v;
 }
 return out;
}
function evaluate(args,env=process.env){
 // Required separate owner pin, not a hash supplied by the reviewed packet.
 const expected=env[PIN_ENV];
 if(typeof expected!=="string"||!SHA_RE.test(expected)){
  return response("BLOCKED_OWNER_APPROVED_TRUST_ANCHOR_PIN_MISSING");
 }
 if(!args["--packet"]||!args["--trusted-keys"]||
    !args["--sap"]||!args["--lock"]||!args["--unblind"])
  return response("BLOCKED_ORIGINAL_SOURCE_OR_TRUST_REGISTRY_NOT_SUPPLIED");
 let registry,packet,bytes;
 try{
  const raw=readBounded(args["--trusted-keys"],MAX_TRUST);
  if(sha(raw)!==expected)
   return response("BLOCKED_OWNER_TRUST_REGISTRY_HASH_MISMATCH");
  registry=JSON.parse(raw.toString("utf8"));
  if(registry.schema!=="MAIN_R80_OWNER_APPROVED_EXTERNAL_TRUST_REGISTRY"||
    registry.nct!==NCT||registry.cycleId!==CYCLE||
    !registry.approvedKeys||typeof registry.approvedKeys!=="object"||
    Array.isArray(registry.approvedKeys)||Object.keys(registry.approvedKeys).length!==2)
   return response("BLOCKED_UNTRUSTED_TRUST_REGISTRY_STRUCTURE");
  packet=JSON.parse(readBounded(args["--packet"],MAX_PACKET).toString("utf8"));
  bytes={
   controlledSapBytes:readBounded(args["--sap"],MAX_DOC),
   databaseLockAuditBytes:readBounded(args["--lock"],MAX_DOC),
   unblindAccessAuditBytes:readBounded(args["--unblind"],MAX_DOC)
  };
 }catch(_){
  return response("BLOCKED_MISSING_MALFORMED_OR_UNREADABLE_LOCAL_SOURCE");
 }
 const result=verifyPacket(packet,{sourceFiles:bytes,trustedKeys:registry.approvedKeys});
 return response(result.status,{
  technicalSignatureValidation:result.technicalAttestationCoherent?
    "TWO_EXTERNAL_PINNED_SIGNATURES_AND_THREE_SOURCE_HASHES_MATCH":"REJECTED",
  validOriginalSourceRecordsRecorded:result.technicalAttestationCoherent?3:0,
  // Coherent source packets still need independent clinical review of the
  // underlying event contents, signatures' identity and amendment chain.
  originalSAPProspectivelyLockedCertified:false
 });
}
function main(){
 let args;
 try{args=parseArgs(process.argv.slice(2))}
 catch(_){process.stderr.write("INVALID_INTAKE_ARGUMENTS\n");process.exitCode=2;return;}
 const report=evaluate(args);
 const serialized=JSON.stringify(report,null,2)+"\n";
 if(args["--report"]){
  try{
   const output=path.resolve(args["--report"]);
   fs.mkdirSync(path.dirname(output),{recursive:true});
   fs.writeFileSync(output,serialized,{mode:0o600});
  }catch(_){process.stderr.write("REPORT_WRITE_FAILED\n");process.exitCode=2;return;}
 }
 process.stdout.write(JSON.stringify({status:report.status,
  technicalSignatureValidation:report.technicalSignatureValidation,
  authenticatedScientificAssessment:false,
  originalSAPProspectivelyLockedCertified:false,
  FDAOutcome:"ABSTAIN",productionWrites:false})+"\n");
 // A missing source is a truthful expected research BLOCK, not a completed
 // source verification; CLI exits 0 to preserve the audit receipt.
}
if(require.main===module)main();
module.exports={evaluate,parseArgs,response,PIN_ENV};
