"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX}}).outputText,file);
const {buildRaasIndependentReviewQueue}=
 require("../lib/raas-independent-review-queue.ts");
const {sourceFrozenFingerprint,frozenReviewPacket,
 auditRaasExternalReviewReceipts,currentReviewIntakeAudit}=
 require("../lib/raas-external-review-intake.ts");
const items=buildRaasIndependentReviewQueue().items;
const schema=(records)=>({schemaVersion:1,
 scope:"RAAS_EXTERNAL_REVIEW_RECEIPTS_UNAUTHENTICATED_INTAKE",
 note:"External review intake only",records});
const first=items[0];
const receipt=(item=first)=>({
 receiptId:"source-verified-receipt-0001",
 taskId:item.id,
 sourceFingerprint:sourceFrozenFingerprint(item),
 reviewerReference:"reviewer-public-reference-42",
 reviewerAffiliation:"Independent contracted scientific reviewer",
 reviewedOn:"2026-11-04",
 decision:"CONFIRM",
 proposedFinding:item.provisionalFinding,
 rationale:"Independent reviewer examined the exact study registry, source document, comparator, uncertainty, limitations and competing interpretations. The original provisional band is retained only as a submitted hypothesis subject to external authentication and separate adjudication.",
 conflicts:"NONE_DECLARED",
 signedArtifactSha256:"0".repeat(64),
 artifactReference:"restricted-archive:sample-attestation-document-ref",
 attestation:"I independently checked the provided dated source facts, exact clinical trial, comparator and risk analysis; my signed record is retained in the restricted review archive."
});
test("82 pre-reviewed metrics get unique source-frozen packet hashes, never full scores",()=>{
 const fingerprints=items.map(sourceFrozenFingerprint);
 assert.equal(items.length,82);
 assert.equal(new Set(fingerprints).size,items.length);
 assert.ok(fingerprints.every(x=>/^[a-f0-9]{64}$/.test(x)));
 assert.equal(sourceFrozenFingerprint(first),sourceFrozenFingerprint({...first}));
 assert.notEqual(sourceFrozenFingerprint(first),
  sourceFrozenFingerprint({...first,observedResult:first.observedResult+" CHANGED"}));
 assert.notEqual(sourceFrozenFingerprint(first),
  sourceFrozenFingerprint({...first,benchmarkSourceUrl:"https://example.org/other"}));
 assert.notEqual(sourceFrozenFingerprint(first),
  sourceFrozenFingerprint({...first,nctId:"NCT00000001"}));
});
test("unsigned reviewer packet preserves evidence and exact stage without granting approval",()=>{
 const packet=frozenReviewPacket(first.id);
 assert.ok(packet);
 assert.equal(packet.task.id,first.id);
 assert.equal(packet.task.nctId,first.nctId);
 assert.equal(packet.receiptDraft.taskId,first.id);
 assert.equal(packet.receiptDraft.sourceFingerprint,sourceFrozenFingerprint(first));
 assert.equal(packet.status,"UNSIGNED_TEMPLATE_NOT_VALIDATED");
 assert.equal(packet.approvedRaasScore,null);
 assert.equal(packet.calibratedFdaProbability,null);
 assert.equal(packet.receiptDraft.signedArtifactSha256,"");
 assert.equal(frozenReviewPacket("NCT99999999|FAKE|pre-1-1"),null);
});
test("current ledger is empty and authorizes zero human signoffs",()=>{
 const a=currentReviewIntakeAudit();
 assert.equal(a.submitted,0);
 assert.equal(a.pendingExternalAuthentication,0);
 assert.equal(a.blocked,0);
 assert.equal(a.certifiedIndependentSignoffs,0);
 assert.equal(a.approvedRaasScores,0);
 assert.equal(a.calibratedFdaForecasts,0);
});
test("a complete syntactic receipt is STILL unauthenticated and cannot approve a metric",()=>{
 const a=auditRaasExternalReviewReceipts(schema([receipt()]),items);
 assert.equal(a.submitted,1);
 assert.equal(a.pendingExternalAuthentication,1);
 assert.equal(a.blocked,0);
 assert.equal(a.checks[0].status,"INTAKE_COMPLETE_PENDING_EXTERNAL_AUTHENTICATION");
 assert.equal(a.certifiedIndependentSignoffs,0);
 assert.equal(a.approvedRaasScores,0);
 assert.equal(a.calibratedFdaForecasts,0);
});
test("source changes, ID mixups, duplicates, suspicious dates and missing declarations block receipts",()=>{
 const base=receipt();
 const changes=[
  {sourceFingerprint:"f".repeat(64)},
  {taskId:"NCT00000001|FAKE|post-1-1"},
  {reviewedOn:"2020-01-01"},
  {conflicts:""},
  {signedArtifactSha256:"forged"},
  {rationale:"no"},
  {decision:"CONFIRM",proposedFinding:first.provisionalFinding==="MIXED_EVIDENCE"?
   "ABOVE_BENCHMARK":"MIXED_EVIDENCE"},
  {reviewerReference:""}
 ];
 for(const patch of changes){
  const result=auditRaasExternalReviewReceipts(schema([{...base,...patch}]),items);
  assert.equal(result.blocked,1,JSON.stringify(patch));
  assert.equal(result.certifiedIndependentSignoffs,0);
  assert.equal(result.pendingExternalAuthentication,0);
 }
 const dup=auditRaasExternalReviewReceipts(schema([base,base]),items);
 assert.equal(dup.blocked,1);
 assert.equal(dup.pendingExternalAuthentication,1);
 assert.equal(dup.certifiedIndependentSignoffs,0);
 assert.throws(()=>auditRaasExternalReviewReceipts({records:[]},items),
  /RAAS_REVIEW_RECEIPT_LEDGER_INVALID/);
});
test("download endpoint serves exact requested task and rejects unmatched or oversized keys",async()=>{
 const {GET}=require("../app/api/raas-independent-review-packet/route.ts");
 const res=GET(new Request("https://example.test/api/raas-independent-review-packet?task="+
  encodeURIComponent(first.id)));
 assert.equal(res.status,200);
 assert.match(res.headers.get("Content-Type"),/application\/json/);
 assert.match(res.headers.get("Content-Disposition"),/raas-review-/);
 const data=await res.json();
 assert.equal(data.task.id,first.id);
 assert.equal(data.sourceFingerprint,sourceFrozenFingerprint(first));
 assert.equal(data.approvedRaasScore,null);
 assert.equal(GET(new Request("https://example.test/api/raas-independent-review-packet?task=BAD")).status,404);
 assert.equal(GET(new Request("https://example.test/api/raas-independent-review-packet?task="+
  "x".repeat(750))).status,400);
});
test("mobile review queue exposes exact packet controls and separate receipt status",()=>{
 const client=read("app/raas-review-queue/ReviewQueueClient.tsx");
 const page=read("app/raas-review-queue/page.tsx");
 assert.match(client,/data-raas-source-frozen-packet/);
 assert.match(client,/source-frozen unsigned review packet/);
 assert.match(page,/data-raas-external-review-intake/);
 assert.match(page,/pendingExternalAuthentication/);
 assert.match(page,/certifiedIndependentSignoffs/);
 for(const [p,s] of [["ReviewQueueClient.tsx",client],["page.tsx",page]]){
  const out=ts.transpileModule(s,{fileName:p,reportDiagnostics:true,compilerOptions:{
   target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,jsx:ts.JsxEmit.ReactJSX}});
  assert.deepEqual((out.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).map(d=>d.code),[]);
 }
});
