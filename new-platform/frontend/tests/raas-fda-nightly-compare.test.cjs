"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),os=require("node:os"),path=require("node:path");
const {execFileSync}=require("node:child_process");
const {createHash}=require("node:crypto");
const {buildNightlyRaasFdaAudit:build}=
 require("../scripts/raas-fda-nightly-evidence-report.cjs");
const {compareNightlyReports:compare}=
 require("../scripts/raas-fda-nightly-compare.cjs");
const hash=x=>createHash("sha256").update(JSON.stringify(x)).digest("hex");
const state=x=>({caseKey:x.caseKey,sourceFingerprint:x.sourceFingerprint,
 originalFirstGoalDate:x.originalFirstGoalDate,listedTargetDate:x.listedTargetDate,
 status:x.status,receiptCount:x.researchReceiptCount,
 outcomeCandidates:x.outcomeSourceCandidateCount});
const signature=rows=>hash([...rows].sort((a,b)=>a.caseKey.localeCompare(b.caseKey)).map(state));

test("first nightly report is explicit about missing prior report",()=>{
 const r=build("2026-11-05T20:00:00Z");
 assert.equal(r.sourceChangedSincePreviousRun,null);
 assert.equal(r.savedSourceChanges,null);
 assert.equal(r.previousRunAtUtc,null);
 assert.equal(r.sourceChangeComparisonStatus,"NO_PREVIOUS_RUN_ARTIFACT_PROVIDED");
 assert.match(r.savedSourceEvidenceFingerprint,/^[a-f0-9]{64}$/);
 assert.equal(r.counts.qualifiedForecastOutcomePairs,0);
});
test("rolling day without a saved evidence update cannot be reported as an FDA source change",()=>{
 const prior=build("2026-11-05T20:00:00Z");
 const next=build("2026-11-06T20:00:00Z");
 const compared=compare(next,prior);
 assert.equal(compared.sourceChangeComparisonStatus,
  "COMPARED_SAVED_SOURCE_AND_INTAKE_METADATA_ONLY");
 assert.equal(compared.sourceChangedSincePreviousRun,false);
 assert.deepEqual(compared.savedSourceChanges,[]);
 assert.equal(compared.savedSourceEvidenceFingerprint,prior.savedSourceEvidenceFingerprint);
 assert.equal(compared.previousRunAtUtc,prior.runAtUtc);
 assert.notEqual(compared.auditStateFingerprint.length,0);
 assert.equal(compared.threeWayScorecard.independentValidatedAccuracyPct,null);
 assert.ok(compared.records.every(x=>x.decision==="ABSTAIN"));
});
test("deadline crossing and source staleness are calendar transitions, not new FDA evidence",()=>{
 const before=build("2026-11-13T20:00:00Z");
 const after=build("2026-11-15T20:00:00Z");
 const compared=compare(after,before);
 assert.equal(compared.sourceChangedSincePreviousRun,false);
 assert.deepEqual(compared.savedSourceChanges,[]);
 assert.ok(compared.calendarDeadlineTransitions.length>=1);
 assert.ok(compared.calendarDeadlineTransitions.every(x=>
  x.type==="ORIGINAL_GOAL_CALENDAR_ELAPSED_NOT_OFFICIAL_FDA_OUTCOME"));
 const old=build("2026-12-03T20:00:00Z");
 const later=build("2026-12-06T20:00:00Z");
 const stale=compare(later,old);
 assert.equal(stale.sourceChangedSincePreviousRun,false);
 assert.ok(stale.calendarSnapshotAgeTransitions.length>=1);
 assert.equal(stale.counts.independentlyAdjudicatedOriginalGoalOutcomes,0);
});
test("a revised goal, source URL, or new evidence receipt is a research metadata change only",()=>{
 const prior=build("2026-11-05T20:00:00Z");
 const current=build("2026-11-06T20:00:00Z");
 const key=current.records[0].caseKey;
 const row=current.records[0];
 current.records[0]={...row,sourceUrl:"https://issuer.example.test/review",
  outcomeSourceCandidateCount:1};
 const compared=compare(current,prior);
 assert.equal(compared.sourceChangedSincePreviousRun,true);
 assert.equal(compared.savedSourceChanges.length,1);
 assert.equal(compared.savedSourceChanges[0].caseKey,key);
 assert.deepEqual(compared.savedSourceChanges[0].changedEvidenceFields,
  ["sourceUrl","outcomeSourceCandidateCount"]);
 assert.equal(compared.savedSourceChanges[0].fdaDecisionVerified,false);
 assert.equal(compared.threeWayScorecard.independentValidatedAccuracyPct,null);
 assert.equal(compared.counts.approvedTradingSignals,0);
});
test("one new or removed research case is flagged without inferring FDA action",()=>{
 const prior=build("2026-11-05T20:00:00Z");
 const later=build("2026-11-06T20:00:00Z");
 later.records=[...later.records,{...later.records[0],
  caseKey:"SYNTHETIC-NEW-SOURCE-CASE"}];
 const changed=compare(later,prior);
 assert.ok(changed.savedSourceChanges.some(x=>x.caseKey==="SYNTHETIC-NEW-SOURCE-CASE"&&
  x.type==="SAVED_RESEARCH_CASE_ADDED"));
 assert.ok(changed.savedSourceChanges.every(x=>x.fdaDecisionVerified===false));
 const shrunk=build("2026-11-06T20:00:00Z");
 shrunk.records=shrunk.records.slice(1);
 assert.ok(compare(shrunk,prior).savedSourceChanges.some(x=>
  x.type==="SAVED_RESEARCH_CASE_REMOVED"));
});
test("wrong, corrupt, future or nonmatching prior artifact fails closed as uncomparable",()=>{
 const old=build("2026-11-05T20:00:00Z");
 const next=build("2026-11-06T20:00:00Z");
 for(const prior of [
  {},null===true?old:{...old,scope:"WRONG"},
  {...old,runAtUtc:"2027-01-01T00:00:00Z"},
  {...old,records:[...old.records,old.records[0]]},
  {...old,auditStateFingerprint:"a".repeat(64)},
  {...old,records:old.records.map((r,i)=>i===0?{...r,sourceFingerprint:"wrong"}:r)},
  {...old,counts:{...old.counts,researchApplicationCycles:99}}
 ]){
  const compared=compare(next,prior);
  assert.equal(compared.sourceChangedSincePreviousRun,null);
  assert.equal(compared.savedSourceChanges,null);
  assert.equal(compared.sourceChangeComparisonStatus,
   "PREVIOUS_ARTIFACT_INVALID_NO_COMPARISON");
 }
});
test("strict previous run fingerprint checks use exact case statuses but ignore row order",()=>{
 const old=build("2026-11-05T20:00:00Z");
 old.records.reverse();
 assert.equal(old.auditStateFingerprint,signature(old.records));
 const newer=build("2026-11-06T20:00:00Z");
 const compared=compare(newer,old);
 assert.equal(compared.sourceChangedSincePreviousRun,false);
 assert.equal(compared.previousRunAtUtc,old.runAtUtc);
});
test("CLI compares a cached previous JSON and writes nullable source-change results",()=>{
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),"raas-nightly-diff-"));
 try{
  const oldPath=path.join(folder,"prior.json");
  fs.writeFileSync(oldPath,JSON.stringify(build("2026-11-05T20:00:00Z")));
  const out=path.join(folder,"new.json"),csv=path.join(folder,"new.csv");
  const stdout=execFileSync(process.execPath,[
   path.join(__dirname,"../scripts/raas-fda-nightly-evidence-report.cjs")
  ],{env:{...process.env,
   RAAS_FDA_EVALUATION_AS_OF_UTC:"2026-11-06T20:00:00Z",
   RAAS_FDA_NIGHTLY_PREVIOUS_JSON:oldPath,
   RAAS_FDA_NIGHTLY_REPORT_JSON:out,RAAS_FDA_NIGHTLY_REPORT_CSV:csv
  },encoding:"utf8"});
  const summary=JSON.parse(stdout);
  assert.equal(summary.comparisonStatus,
   "COMPARED_SAVED_SOURCE_AND_INTAKE_METADATA_ONLY");
  assert.equal(summary.changedSavedSourceCases,0);
  assert.equal(JSON.parse(fs.readFileSync(out,"utf8")).sourceChangedSincePreviousRun,false);
  assert.ok(fs.existsSync(csv));
  fs.writeFileSync(oldPath,"{invalid JSON");
  execFileSync(process.execPath,[
   path.join(__dirname,"../scripts/raas-fda-nightly-evidence-report.cjs")
  ],{env:{...process.env,
   RAAS_FDA_EVALUATION_AS_OF_UTC:"2026-11-06T20:00:00Z",
   RAAS_FDA_NIGHTLY_PREVIOUS_JSON:oldPath,
   RAAS_FDA_NIGHTLY_REPORT_JSON:out,RAAS_FDA_NIGHTLY_REPORT_CSV:csv
  },encoding:"utf8"});
  assert.equal(JSON.parse(fs.readFileSync(out,"utf8")).sourceChangedSincePreviousRun,null);
 }finally{fs.rmSync(folder,{recursive:true,force:true});}
});
