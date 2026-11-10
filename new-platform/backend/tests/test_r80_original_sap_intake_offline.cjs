"use strict";
const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),os=require("node:os"),path=require("node:path");
const {spawnSync}=require("node:child_process"),crypto=require("node:crypto");
const {evaluate,parseArgs,PIN_ENV}=require("../scripts/intake_r80_original_sap_evidence_offline.cjs");
const {NCT,CYCLE,SCHEMA,ROLES,FILES,EVIDENCE,sha,packetMessage}=
 require("../scripts/verify_r79_sap_lock_provenance_packet.cjs");

function setup(){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),"r80-sap-intake-test-"));
 const pair=ROLES.map((role,i)=>({
  role,keyId:"mock-external-"+i,
  organization:i===0?"Mock sponsor custody organization":"Mock external statistics organization",
  ...crypto.generateKeyPairSync("ed25519")
 }));
 const sources=FILES.map((key,i)=>({
  key,file:path.join(dir,key+".bin"),bytes:Buffer.alloc(350+i,65+i)
 }));
 sources.forEach(x=>fs.writeFileSync(x.file,x.bytes));
 const packet={schema:SCHEMA,nct:NCT,cycleId:CYCLE,controlledSapVersion:"3.0 Amendment 2",
  printedDateDiscrepanciesResolved:true,amendmentChainAudited:true,
  events:EVIDENCE.map((eventType,i)=>({
   eventType,atUtc:["2025-02-13T11:00:00Z","2025-02-20T14:00:00Z","2025-02-21T12:00:00Z"][i],
   sourceFileKey:FILES[i],sourceSha256:sha(sources[i].bytes)
  }))};
 packet.attestations=pair.map(p=>({
   keyId:p.keyId,role:p.role,
   signatureBase64:crypto.sign(null,packetMessage(packet),p.privateKey).toString("base64")
 }));
 const registry={schema:"MAIN_R80_OWNER_APPROVED_EXTERNAL_TRUST_REGISTRY",nct:NCT,cycleId:CYCLE,
  approvedKeys:Object.fromEntries(pair.map(p=>[p.keyId,{
   role:p.role,organization:p.organization,
   publicKeyPem:p.publicKey.export({type:"spki",format:"pem"})
  }]))};
 const packetPath=path.join(dir,"packet.json"),trustedPath=path.join(dir,"external-trust.json");
 fs.writeFileSync(packetPath,JSON.stringify(packet));
 fs.writeFileSync(trustedPath,JSON.stringify(registry));
 const args={"--packet":packetPath,"--sap":sources[0].file,"--lock":sources[1].file,
  "--unblind":sources[2].file,"--trusted-keys":trustedPath};
 const env={[PIN_ENV]:sha(fs.readFileSync(trustedPath))};
 return {dir,sources,pair,packet,registry,packetPath,trustedPath,args,env,
  cleanup:()=>fs.rmSync(dir,{recursive:true,force:true})};
}
function remainUncertified(result){
 assert.equal(result.authenticatedScientificAssessment,false);
 assert.equal(result.originalSAPProspectivelyLockedCertified,false);
 assert.equal(result.FDAOutcome,"ABSTAIN");
 assert.equal(result.futureFDATiming,"UNKNOWN");
 assert.equal(result.clinicalGrade,null);
 assert.equal(result.calibratedAccuracy,null);
 assert.equal(result.productionOrModelTrainingWrites,false);
 assert.equal(result.sourceFileNamesOrContentsArchived,false);
 assert.equal(result.reviewerIdentityKeysArchived,false);
}
test("Without owner-pinned trust registry, original data stays blocked even when synthetic packet includes signatures",()=>{
 const t=setup();try{
  const out=evaluate(t.args,{});
  assert.equal(out.status,"BLOCKED_OWNER_APPROVED_TRUST_ANCHOR_PIN_MISSING");
  remainUncertified(out);
 }finally{t.cleanup();}
});
test("Synthetic original bytes, matching SHA, two independent signers and external trust pin do not certify clinical outcome",()=>{
 const t=setup();try{
  const out=evaluate(t.args,t.env);
  assert.equal(out.technicalSignatureValidation,"TWO_EXTERNAL_PINNED_SIGNATURES_AND_THREE_SOURCE_HASHES_MATCH");
  assert.equal(out.validOriginalSourceRecordsRecorded,3);
  assert.equal(out.status,"SIGNED_SOURCE_PACKET_COHERENT_NOT_CLINICALLY_APPROVED");
  remainUncertified(out);
 }finally{t.cleanup();}
});
test("Separate trust anchor byte-hash change blocks every possible signature or source",()=>{
 const t=setup();try{
  const changed={...t.env,[PIN_ENV]:"a".repeat(64)};
  let out=evaluate(t.args,changed);
  assert.equal(out.status,"BLOCKED_OWNER_TRUST_REGISTRY_HASH_MISMATCH");
  remainUncertified(out);
  fs.appendFileSync(t.trustedPath," ");
  out=evaluate(t.args,t.env);
  assert.equal(out.status,"BLOCKED_OWNER_TRUST_REGISTRY_HASH_MISMATCH");
  remainUncertified(out);
 }finally{t.cleanup();}
});
test("Missing or changed actual source byte files cannot be treated as proof",()=>{
 const t=setup();try{
  fs.appendFileSync(t.sources[1].file,"SOURCE_TAMPER");
  let out=evaluate(t.args,t.env);
  assert.equal(out.status,"BLOCKED_SOURCE_BYTES_NOT_INDEPENDENTLY_HASH_MATCHED");
  remainUncertified(out);
  fs.rmSync(t.sources[1].file);
  out=evaluate(t.args,t.env);
  assert.equal(out.status,"BLOCKED_MISSING_MALFORMED_OR_UNREADABLE_LOCAL_SOURCE");
  remainUncertified(out);
 }finally{t.cleanup();}
});
test("Forged event or wrong FDA application cannot inherit genuine digital attestations",()=>{
 const t=setup();try{
  t.packet.events[2].atUtc="2025-02-12T01:00:00Z";
  fs.writeFileSync(t.packetPath,JSON.stringify(t.packet));
  let out=evaluate(t.args,t.env);
  assert.equal(out.status,"BLOCKED_SAP_OR_DATABASE_LOCK_NOT_BEFORE_FIRST_UNBLIND");
  remainUncertified(out);
  t.packet.nct="NCT00000001";
  fs.writeFileSync(t.packetPath,JSON.stringify(t.packet));
  out=evaluate(t.args,t.env);
  assert.equal(out.status,"BLOCKED_MISSING_OR_UNVERIFIED_CONTROLLED_SOURCE");
  remainUncertified(out);
 }finally{t.cleanup();}
});
test("Incomplete flags, wrong CLI params and untrusted self-selected keys cannot authorize a claim",()=>{
 assert.throws(()=>parseArgs(["--sap","/tmp/a","--sap","/tmp/b"]),/INVALID_INTAKE_ARGUMENTS/);
 assert.throws(()=>parseArgs(["--guess","value"]),/INVALID_INTAKE_ARGUMENTS/);
 const t=setup();try{
  let out=evaluate({"--packet":t.packetPath},t.env);
  assert.equal(out.status,"BLOCKED_ORIGINAL_SOURCE_OR_TRUST_REGISTRY_NOT_SUPPLIED");
  remainUncertified(out);
  t.registry.approvedKeys={};
  fs.writeFileSync(t.trustedPath,JSON.stringify(t.registry));
  const pin={[PIN_ENV]:sha(fs.readFileSync(t.trustedPath))};
  out=evaluate(t.args,pin);
  assert.equal(out.status,"BLOCKED_UNTRUSTED_TRUST_REGISTRY_STRUCTURE");
  remainUncertified(out);
 }finally{t.cleanup();}
});
test("No-args CLI writes metadata-only audit receipt with mode 0600, no private records",()=>{
 const t=setup();try{
  const report=path.join(t.dir,"receipt.json");
  const script=path.join(__dirname,"../scripts/intake_r80_original_sap_evidence_offline.cjs");
  const child=spawnSync(process.execPath,[script,"--report",report],{encoding:"utf8",env:{...process.env,[PIN_ENV]:""}});
  assert.equal(child.status,0,child.stderr);
  const out=JSON.parse(fs.readFileSync(report,"utf8"));
  assert.equal(out.status,"BLOCKED_OWNER_APPROVED_TRUST_ANCHOR_PIN_MISSING");
  assert.equal(fs.statSync(report).mode&0o777,0o600);
  assert.doesNotMatch(fs.readFileSync(report,"utf8"),/BEGIN PRIVATE KEY|BEGIN PUBLIC KEY/);
  remainUncertified(out);
 }finally{t.cleanup();}
});

test("Existing research receipt and symlink cannot be overwritten or followed",()=>{
 const t=setup();try{
  const report=path.join(t.dir,"immutable-receipt.json");
  const script=path.join(__dirname,"../scripts/intake_r80_original_sap_evidence_offline.cjs");
  fs.writeFileSync(report,"OWNER_EXISTING_ORIGINAL_RECEIPT",{mode:0o600});
  const cmd=[script,"--report",report];
  let child=spawnSync(process.execPath,cmd,{encoding:"utf8",env:{...process.env,[PIN_ENV]:""}});
  assert.equal(child.status,2);
  assert.match(child.stderr,/REPORT_WRITE_FAILED/);
  assert.equal(fs.readFileSync(report,"utf8"),"OWNER_EXISTING_ORIGINAL_RECEIPT");
  const symlink=path.join(t.dir,"linked-receipt.json");
  fs.symlinkSync(report,symlink);
  child=spawnSync(process.execPath,[script,"--report",symlink],{encoding:"utf8",
    env:{...process.env,[PIN_ENV]:""}});
  assert.equal(child.status,2);
  assert.match(child.stderr,/REPORT_WRITE_FAILED/);
  assert.equal(fs.readFileSync(report,"utf8"),"OWNER_EXISTING_ORIGINAL_RECEIPT");
 }finally{t.cleanup();}
});
