"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX
 }}).outputText,file);
const saved=require("../data/raas-fda-original-goal-outcome-candidates.json");
const {buildThreeWayFDAFreezePreflightPlan:build}
 =require("../lib/raas-fda-three-way-freeze-preflight.ts");
const {auditRaasFdaOriginalGoalOutcomes:audit,
 currentRaasFdaOriginalGoalOutcomeAudit:current}
 =require("../lib/raas-fda-original-goal-outcome-audit.ts");
const {GET}=require("../app/api/raas-fda-original-goal-outcomes/route.ts");
const plan=build();
const cogt=plan.records.find(x=>x.caseKey==="COGT-BEZUCLASTINIB-GIST-2026");
const capr=plan.records.find(x=>x.ticker==="CAPR");
const phase2=plan.records.find(x=>x.caseKey==="COGT-BEZUCLASTINIB-NONADVSM-2026");
assert.ok(cogt&&capr&&phase2);
const doc=records=>({...saved,records});
const candidate=(p=cogt)=>({
 evidenceId:"synthetic-source-0001",caseKey:p.caseKey,
 sourceFingerprint:p.sourceFingerprint,
 ticker:p.ticker,drug:p.drug,indication:p.indication,
 trialNctId:p.trialNctId,firstAnnouncedGoalDate:p.originalFirstGoalDate,
 exactFdaApplicationNumber:"NDA-TEST-123456",
 exactReviewCycleId:"FDA-CYCLE-TEST-1",
 claimedOriginalGoalOutcome:"PASS",
 claimedActionEffectiveDate:"2026-11-20",
 sourcePublishedDate:"2026-11-21",
 capturedAt:"2026-11-22T10:00:00Z",
 sourceType:"FDA_PRIMARY",
 sourceUrl:"https://www.fda.gov/drugs/resources-information-approved-drugs/example-case",
 sourceDocumentSha256:"f".repeat(64),
 independentAdjudicationArchiveReference:null
});
test("empty, non-sensitive outcome feed tracks all 11 cases but certifies nothing",async()=>{
 assert.equal(saved.records.length,0);
 assert.equal(saved.schemaVersion,1);
 const r=current();
 assert.equal(r.exactReviewCycleResearchCases,11);
 assert.equal(r.pendingNoEvidence,11);
 assert.equal(r.blockedResearchCases,0);
 assert.equal(r.pendingIndependentAdjudication,0);
 assert.equal(r.submittedResearchEvidenceRecords,0);
 assert.equal(r.authenticatedPredecisionForecasts,0);
 assert.equal(r.independentlyAdjudicatedOriginalGoalLabels,0);
 assert.equal(r.qualifiedForecastOutcomePairs,0);
 assert.equal(r.independentThreeWayAccuracy,null);
 assert.equal(r.cases.length,11);
 assert.equal(new Set(r.cases.map(x=>x.caseKey)).size,11);
 assert.ok(r.cases.every(x=>x.status==="NOT_SUBMITTED"&&
  x.verifiedOriginalGoalLabel===null&&x.accuracyPairQualified===false));
 const api=GET(new Request("https://example.test/api/raas-fda-original-goal-outcomes"));
 assert.equal(api.status,200);
 assert.equal(api.headers.get("cache-control"),"no-store");
 assert.equal((await api.json()).independentlyAdjudicatedOriginalGoalLabels,0);
});
test("a plausible FDA-primary synthetic outcome is still only pending adjudication",()=>{
 const a=audit(doc([candidate()]));
 const r=a.cases.find(x=>x.caseKey===cogt.caseKey);
 assert.equal(r.status,"PENDING_INDEPENDENT_ADJUDICATION");
 assert.equal(r.recordedEvidenceCount,1);
 assert.equal(r.verifiedOriginalGoalLabel,null);
 assert.equal(r.verifiedOriginalGoalActionDate,null);
 assert.equal(r.authenticatedPredecisionForecast,null);
 assert.equal(r.accuracyPairQualified,false);
 assert.equal(a.submittedResearchEvidenceRecords,1);
 assert.equal(a.independentlyAdjudicatedOriginalGoalLabels,0);
 assert.equal(a.qualifiedForecastOutcomePairs,0);
});
test("original deadline and exact cycle remain distinct after a formal extension",()=>{
 const c={...candidate(capr),
  claimedOriginalGoalOutcome:"EXTENSION",
  firstAnnouncedGoalDate:capr.originalFirstGoalDate,
  claimedActionEffectiveDate:"2026-11-20"};
 const x=audit(doc([c]));
 const r=x.cases.find(y=>y.caseKey===capr.caseKey);
 assert.equal(r.originalFirstGoalDate,"2026-08-22");
 assert.equal(r.listedTargetDate,"2026-11-22");
 assert.equal(r.status,"BLOCKED_SOURCE_CANDIDATE");
 assert.ok(r.blockers.includes("EXTENSION_NOT_CONFIRMED_BEFORE_ORIGINAL_GOAL"));
 assert.ok(r.blockers.includes("AFTER_ORIGINAL_GOAL_ACTION_NOT_AUTOMATIC_ORIGINAL_DISPOSITION"));
 assert.equal(r.verifiedOriginalGoalLabel,null);
 const replaced=audit(doc([{...c,firstAnnouncedGoalDate:"2026-11-22"}]));
 assert.ok(replaced.cases.find(y=>y.caseKey===capr.caseKey).blockers.includes(
  "EXACT_APPLICATION_SOURCE_OR_ORIGINAL_GOAL_MISMATCH"));
});
test("wrong study, ticker, source, action label, duplicates, and temporal conflicts block",()=>{
 const bad=[
  {sourceFingerprint:"a".repeat(64)},
  {ticker:"ACAD"},
  {drug:"other drug"},
  {trialNctId:"NCT00000001"},
  {firstAnnouncedGoalDate:"2027-11-30"},
  {sourceType:"FDA_PRIMARY",sourceUrl:"https://www.fda.gov.evil.test/fake"},
  {sourceType:"SEC_FILING",sourceUrl:"https://fda.gov/letter"},
  {claimedOriginalGoalOutcome:"OTHER"},
  {sourceDocumentSha256:"not-a-real-hash"},
  {claimedActionEffectiveDate:"2026-12-01"},
  {claimedActionEffectiveDate:"2026-11-23",sourcePublishedDate:"2026-11-22"},
  {capturedAt:"2026-11-19T01:00:00Z"},
  {capturedAt:"2026-11-22T10:00:00"},
  {exactReviewCycleId:""},
 ];
 for(const patch of bad){
  const r=audit(doc([{...candidate(),...patch}]));
  assert.equal(r.blockedResearchCases,1,JSON.stringify(patch));
  assert.equal(r.independentlyAdjudicatedOriginalGoalLabels,0);
 }
 const dup=audit(doc([candidate(),{...candidate(),evidenceId:"synthetic-source-0002"}]));
 assert.equal(dup.blockedResearchCases,1);
 assert.ok(dup.cases.find(x=>x.caseKey===cogt.caseKey)
  .blockers.includes("MULTIPLE_OUTCOME_CANDIDATES_REQUIRE_CYCLE_RECONCILIATION"));
 const duplicateId=audit(doc([candidate(),
  {...candidate(phase2),evidenceId:"synthetic-source-0001"}]));
 assert.ok(duplicateId.cases.some(x=>
  x.blockers.includes("INVALID_OR_DUPLICATE_EVIDENCE_ID")));
 assert.equal(duplicateId.independentlyAdjudicatedOriginalGoalLabels,0);
});
test("sponsor or SEC disclosure alone cannot be certified as an FDA original-cycle decision",()=>{
 const sponsor=audit(doc([{...candidate(),sourceType:"SPONSOR_DISCLOSURE",
  sourceUrl:"https://investors.example.org/press-release"}]));
 assert.ok(sponsor.cases.find(x=>x.caseKey===cogt.caseKey)
  .blockers.includes("SPONSOR_CLAIM_NEEDS_PRIMARY_FDA_CYCLE_CONFIRMATION"));
 const sec=audit(doc([{...candidate(),sourceType:"SEC_FILING",
  sourceUrl:"https://www.sec.gov/Archives/edgar/data/123/456/test.htm"}]));
 assert.ok(sec.cases.find(x=>x.caseKey===cogt.caseKey)
  .blockers.includes("SEC_FILING_NEEDS_INDEPENDENT_FDA_CYCLE_CONFIRMATION"));
});
test("evidence for a separate Phase 2 application is not added to the Phase 3 review",()=>{
 const r=audit(doc([candidate(phase2)]));
 const p=r.cases.find(x=>x.caseKey===phase2.caseKey);
 assert.equal(p.status,"BLOCKED_SOURCE_CANDIDATE");
 assert.ok(p.blockers.includes("PHASE2_EXCLUDED_FROM_PHASE3_PIPELINE"));
 assert.equal(p.verifiedOriginalGoalLabel,null);
 assert.equal(r.qualifiedForecastOutcomePairs,0);
});
test("source ledger rejects malformed structure and orphaned application references",()=>{
 for(const x of [null,{}, {...saved,schemaVersion:3},
  {...saved,scope:"FAKE"},{...saved,note:"short"},
  {...saved,records:{}}]){
  assert.throws(()=>audit(x),/RAAS_FDA_ORIGINAL_GOAL_OUTCOME_FEED_INVALID/);
 }
 assert.throws(()=>audit(doc([{...candidate(),caseKey:"UNKNOWN-APPLICATION"}])),
  /RAAS_FDA_ORIGINAL_GOAL_UNKNOWN_CASE_REFERENCE/);
});
test("download a case-bound seven-step outcome packet without approving a label",async()=>{
 const url="https://example.test/api/raas-fda-original-goal-outcomes?case="+
  encodeURIComponent(cogt.caseKey);
 const response=GET(new Request(url));
 assert.equal(response.status,200);
 assert.equal(response.headers.get("cache-control"),"no-store");
 assert.match(response.headers.get("content-disposition"),/raas-fda-original-goal-review-COGT/);
 const packet=await response.json();
 assert.equal(packet.caseKey,cogt.caseKey);
 assert.equal(packet.sourceFingerprint,cogt.sourceFingerprint);
 assert.equal(packet.originalFirstGoalDate,"2026-11-30");
 assert.equal(packet.requiredEvidence.length,7);
 assert.equal(packet.independentlyVerifiedOutcome,null);
 assert.equal(packet.approvedForecast,null);
 for(const k of ["", "UNSEEN", "\n", "x".repeat(200)]){
  const res=GET(new Request("https://example.test/api/raas-fda-original-goal-outcomes?case="+
   encodeURIComponent(k)));
  assert.ok([400,404].includes(res.status));
  assert.equal(res.headers.get("cache-control"),"no-store");
 }
});
test("Predictions page exposes research-only outcome counter and exact-case link",()=>{
 const page=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
 assert.match(page,/data-raas-fda-original-goal-outcome-audit/);
 assert.match(page,/data-raas-fda-exact-original-goal-outcome/);
 assert.match(page,/currentRaasFdaOriginalGoalOutcomeAudit/);
 assert.match(page,/api\/raas-fda-original-goal-outcomes/);
 assert.match(page,/none adjudicated/);
 assert.match(page,/qualifiedForecastOutcomePairs/);
 const tr=ts.transpileModule(page,{fileName:"predictions.tsx",
  reportDiagnostics:true,compilerOptions:{
   target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,jsx:ts.JsxEmit.ReactJSX
  }});
 assert.equal((tr.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).length,0);
});
