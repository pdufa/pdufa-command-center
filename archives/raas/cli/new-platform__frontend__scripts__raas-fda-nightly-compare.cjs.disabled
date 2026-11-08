"use strict";
/** Compare SAVED FDA research evidence and intake metadata across nightly
 * artifacts. This cannot establish new official FDA events or prove a past
 * forecast was timestamped independently. Calendar passage is a separate
 * dimension and must never trigger a claimed "FDA source change".
 */
const {createHash}=require("node:crypto");
const hash=x=>createHash("sha256").update(JSON.stringify(x)).digest("hex");
const fields=["sourceFingerprint","sourceUrl","savedSnapshotAsOf",
 "originalFirstGoalDate","listedTargetDate","formalGoalRevisionPresent",
 "trialNctId","phase3SourceEligibility","researchReceiptCount",
 "structurallyCompleteReceiptCount","blockedReceiptCount",
 "outcomeSourceCandidateCount","outcomeReviewState",
 "outstandingEvidenceProofIds"];
const sorted=xs=>[...xs].sort((a,b)=>a.caseKey.localeCompare(b.caseKey));
const evidence=x=>Object.fromEntries(fields.map(key=>[key,x[key]]));
const state=x=>({caseKey:x.caseKey,sourceFingerprint:x.sourceFingerprint,
 originalFirstGoalDate:x.originalFirstGoalDate,listedTargetDate:x.listedTargetDate,
 status:x.status,receiptCount:x.researchReceiptCount,
 outcomeCandidates:x.outcomeSourceCandidateCount});
const validRows=xs=>Array.isArray(xs)&&xs.length<=10000&&
 xs.every(x=>x&&typeof x.caseKey==="string"&&
 x.caseKey.length>0&&x.caseKey.length<=160&&
 typeof x.sourceFingerprint==="string"&&
 /^[a-f0-9]{64}$/.test(x.sourceFingerprint)&&
 typeof x.originalFirstGoalDate==="string")&&
 new Set(xs.map(x=>x.caseKey)).size===xs.length;
const iso=x=>typeof x==="string"&&
 /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/.test(x)&&
 Number.isFinite(Date.parse(x));

function compareNightlyReports(current,previous){
 if(!current||current.schemaVersion!==1||
  current.scope!=="RAAS_NIGHTLY_FDA_THREE_WAY_EVIDENCE_READINESS_RESEARCH_ONLY"||
  !validRows(current.records)||!iso(current.runAtUtc))
  throw Error("RAAS_FDA_NIGHTLY_CURRENT_REPORT_INVALID");
 const baseline={
  savedSourceEvidenceFingerprint:hash(sorted(current.records).map(r=>({
   caseKey:r.caseKey,...evidence(r)
  }))),
  previousRunAtUtc:null,
  savedSourceChanges:null,
  calendarDeadlineTransitions:null,
  calendarSnapshotAgeTransitions:null,
  sourceChangedSincePreviousRun:null,
  sourceChangeComparisonStatus:"NO_PREVIOUS_RUN_ARTIFACT_PROVIDED"
 };
 const report={...current,...baseline};
 if(previous===undefined||previous===null)return report;
 if(!previous||typeof previous!=="object"||Array.isArray(previous)||
  previous.schemaVersion!==1||
  previous.scope!==current.scope||
  !iso(previous.runAtUtc)||
  Date.parse(previous.runAtUtc)>=Date.parse(current.runAtUtc)||
  !validRows(previous.records)||
  previous.counts?.researchApplicationCycles!==previous.records.length||
  previous.auditStateFingerprint!==hash(sorted(previous.records).map(state))
 ){
  report.sourceChangeComparisonStatus="PREVIOUS_ARTIFACT_INVALID_NO_COMPARISON";
  return report;
 }
 const prior=new Map(previous.records.map(x=>[x.caseKey,x]));
 const now=new Map(current.records.map(x=>[x.caseKey,x]));
 const keys=[...new Set([...prior.keys(),...now.keys()])].sort();
 const changes=[],deadlines=[],stale=[];
 for(const caseKey of keys){
  const old=prior.get(caseKey),cur=now.get(caseKey);
  if(!old||!cur){
   changes.push({caseKey,
    type:old?"SAVED_RESEARCH_CASE_REMOVED":"SAVED_RESEARCH_CASE_ADDED",
    changedEvidenceFields:["caseKey"],fdaDecisionVerified:false});
   continue;
  }
  const changedEvidenceFields=fields.filter(k=>
   JSON.stringify(evidence(old)[k])!==JSON.stringify(evidence(cur)[k]));
  if(changedEvidenceFields.length)
   changes.push({caseKey,type:"SAVED_SOURCE_OR_INTAKE_METADATA_CHANGED",
    changedEvidenceFields,fdaDecisionVerified:false});
  if(old.daysUntilOriginalGoal>0&&cur.daysUntilOriginalGoal<=0)
   deadlines.push({caseKey,firstGoalDate:cur.originalFirstGoalDate,
    type:"ORIGINAL_GOAL_CALENDAR_ELAPSED_NOT_OFFICIAL_FDA_OUTCOME"});
  if(old.savedSourceSnapshotStaleOver30Days===false&&
   cur.savedSourceSnapshotStaleOver30Days===true)
   stale.push({caseKey,sourceAsOf:cur.savedSnapshotAsOf,
    type:"SAVED_RESEARCH_SOURCE_AGE_EXCEEDED_30_DAYS"});
 }
 report.previousRunAtUtc=previous.runAtUtc;
 report.savedSourceChanges=changes;
 report.calendarDeadlineTransitions=deadlines;
 report.calendarSnapshotAgeTransitions=stale;
 report.sourceChangedSincePreviousRun=changes.length>0;
 report.sourceChangeComparisonStatus="COMPARED_SAVED_SOURCE_AND_INTAKE_METADATA_ONLY";
 return report;
}
module.exports={compareNightlyReports};
