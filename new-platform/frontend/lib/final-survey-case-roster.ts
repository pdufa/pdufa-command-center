/** Authenticated prospective FDA case roster, with validation of the
 * application-level historical audit. Missing roster support is unknown,
 * never a zero. All externally cited URLs are persisted FDA evidence.
 */
export type HistoricalCaseReason=
 "APPLICATION_RELATION_NOT_VERIFIED_AT_CUTOFF"|
 "FDA_OUTCOME_NOT_VERIFIED"|"PREDICTION_NOT_BEFORE_FDA_ACTION"|
 "EVIDENCE_CUTOFF_AFTER_PREDICTION"|"PREDICTION_SOURCE_NOT_VERIFIED_AT_CUTOFF"|
 "LATER_PREDICTION_FOR_SAME_APPLICATION"|
 "LOCKED_PREDICTION_ABSTAINED"|
 "LOCKED_PREDICTION_BEFORE_FDA_DECISION"|
 "VERIFIED_OUTCOME_WITHOUT_LOCKED_PREDECISION_PREDICTION";
export type HistoricalCaseDisposition="EXCLUDED"|"NO_PREDICTION"|"ABSTAIN"|"EVALUATED";
export type HistoricalCase={
 predictionId:string|null;nctId:string|null;applicationId:string;
 predictedDecision:"PASS"|"CRL"|"EXTENSION"|"ABSTAIN"|null;
 actualDecision:"APPROVED"|"CRL"|"EXTENDED"|"PENDING";
 decisionDate:string|null;predictionCreatedAt:string|null;
 evidenceCutoff:string|null;disposition:HistoricalCaseDisposition;
 reason:HistoricalCaseReason;fdaSourceUrl:string|null;correctness:boolean|null;
};
export type HistoricalCaseRoster={
 total:number;returned:number;limit:number;
 reasonCounts:Readonly<Record<HistoricalCaseReason,number>>;
 records:readonly HistoricalCase[];
};
const dispositions=["EXCLUDED","NO_PREDICTION","ABSTAIN","EVALUATED"];
const reasons:readonly HistoricalCaseReason[]=[
 "APPLICATION_RELATION_NOT_VERIFIED_AT_CUTOFF",
 "FDA_OUTCOME_NOT_VERIFIED","PREDICTION_NOT_BEFORE_FDA_ACTION",
 "EVIDENCE_CUTOFF_AFTER_PREDICTION","PREDICTION_SOURCE_NOT_VERIFIED_AT_CUTOFF",
 "LATER_PREDICTION_FOR_SAME_APPLICATION",
 "LOCKED_PREDICTION_ABSTAINED","LOCKED_PREDICTION_BEFORE_FDA_DECISION",
 "VERIFIED_OUTCOME_WITHOUT_LOCKED_PREDECISION_PREDICTION"
];
const numeric=(x:unknown):x is number=>typeof x==="number"&&Number.isSafeInteger(x)&&x>=0;
const object=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==="object"&&!Array.isArray(x);
const fail=():never=>{throw Error("HISTORICAL_FDA_CASE_ROSTER_INVALID");};
const date=(x:unknown):x is string=>typeof x==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&
 !Number.isNaN(Date.parse(x+"T00:00:00Z"))&&new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;
const dateTime=(x:unknown):x is string=>typeof x==="string"&&
 /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(x)&&
 Number.isFinite(Date.parse(x));
const fdaUrl=(x:unknown):x is string=>typeof x==="string"&&
 /^https:\/\/(?:[a-z0-9-]+\.)*fda\.gov\//i.test(x)&&!/[\\\s@]/.test(x);
const known=(v:unknown)=>v==="APPROVED"||v==="CRL"||v==="EXTENDED";
const decision=(v:unknown)=>v==="PASS"||v==="CRL"||v==="EXTENSION"||v==="ABSTAIN";
export const caseReasonLabel=(reason:HistoricalCaseReason):string=>({
 APPLICATION_RELATION_NOT_VERIFIED_AT_CUTOFF:"Study and FDA application not linked before forecast",
 FDA_OUTCOME_NOT_VERIFIED:"Official FDA outcome not verified",
 PREDICTION_NOT_BEFORE_FDA_ACTION:"Prediction made on or after FDA action day",
 EVIDENCE_CUTOFF_AFTER_PREDICTION:"Evidence cutoff follows prediction date",
 PREDICTION_SOURCE_NOT_VERIFIED_AT_CUTOFF:"Required prediction evidence unavailable at forecast cutoff",
 LATER_PREDICTION_FOR_SAME_APPLICATION:"Another earlier eligible forecast already represents this application",
 LOCKED_PREDICTION_ABSTAINED:"Locked forecast abstained",
 LOCKED_PREDICTION_BEFORE_FDA_DECISION:"Eligible locked forecast; outcome compared",
 VERIFIED_OUTCOME_WITHOUT_LOCKED_PREDECISION_PREDICTION:"Verified FDA decision with no eligible predecision forecast"
})[reason];

/** Returns null for an older backend that does not yet publish a roster.
 * Malformed or contradictory rosters are rejected; they are never shown as
 * valid or used to measure historical model performance.
 */
export function auditHistoricalCaseRoster(raw:unknown):HistoricalCaseRoster|null{
 if(!object(raw))return fail();
 if(raw.case_review===undefined)return null;
 const data=raw.case_review;
 if(!object(data)||!object(data.reason_counts)||!Array.isArray(data.records)||
    !numeric(data.total)||!numeric(data.returned)||data.limit!==50||
    data.returned!==Math.min(data.total,50)||data.records.length!==data.returned||
    !numeric(raw.prediction_records)||!numeric(raw.number_with_known_outcomes)||
    !numeric(raw.eligible_applications)||!numeric(raw.number_evaluated)||
    !numeric(raw.number_abstained))return fail();
 const total=raw.prediction_records+raw.number_with_known_outcomes-raw.eligible_applications;
 if(data.total!==total||total<0)return fail();
 const keys=Object.keys(data.reason_counts);
 if(keys.some(k=>!reasons.includes(k as HistoricalCaseReason)||!numeric(data.reason_counts[k]))||
    keys.reduce((n,k)=>n+(data.reason_counts[k] as number),0)!==total ||
    data.reason_counts.LOCKED_PREDICTION_ABSTAINED!==raw.number_abstained&&
      (data.reason_counts.LOCKED_PREDICTION_ABSTAINED??0)!==raw.number_abstained ||
    (data.reason_counts.LOCKED_PREDICTION_BEFORE_FDA_DECISION??0)!==raw.number_evaluated ||
    (data.reason_counts.VERIFIED_OUTCOME_WITHOUT_LOCKED_PREDECISION_PREDICTION??0)!==
      raw.number_with_known_outcomes-raw.eligible_applications)return fail();
 const seen=new Set<string>(),records:HistoricalCase[]=[];
 for(const r of data.records){
  if(!object(r)||!dispositions.includes(r.disposition as string)||
      !reasons.includes(r.reason as HistoricalCaseReason)||
      typeof r.application_id!=="string"||!r.application_id.trim()||
      !(r.nct_id===null||typeof r.nct_id==="string"&&/^NCT\d{8}$/.test(r.nct_id))||
      !(r.fda_source_url===null||fdaUrl(r.fda_source_url))||
      !(r.decision_date===null||date(r.decision_date)))return fail();
  const noPrediction=r.disposition==="NO_PREDICTION";
  if(noPrediction){
   if(r.reason!=="VERIFIED_OUTCOME_WITHOUT_LOCKED_PREDECISION_PREDICTION"||
      r.prediction_id!==null||r.nct_id!==null||r.predicted_decision!==null||
      r.prediction_created_at!==null||r.evidence_cutoff!==null||
      !known(r.actual_decision)||r.correctness!==null)return fail();
  }else{
   if(typeof r.prediction_id!=="string"||!r.prediction_id.trim()||
      !r.nct_id||!decision(r.predicted_decision)||
      !dateTime(r.prediction_created_at)||!dateTime(r.evidence_cutoff)||
      Date.parse(r.evidence_cutoff)>Date.parse(r.prediction_created_at)||
      !["APPROVED","CRL","EXTENDED","PENDING"].includes(r.actual_decision as string))return fail();
   if(r.disposition==="EVALUATED"){
    if(r.reason!=="LOCKED_PREDICTION_BEFORE_FDA_DECISION"||
       !known(r.actual_decision)||!r.decision_date||
       r.predicted_decision==="ABSTAIN"||typeof r.correctness!=="boolean"||
       r.prediction_created_at.slice(0,10)>=r.decision_date)return fail();
   }else if(r.disposition==="ABSTAIN"){
    if(r.reason!=="LOCKED_PREDICTION_ABSTAINED"||
       r.predicted_decision!=="ABSTAIN"||r.correctness!==null)return fail();
   }else{
    if(!reasons.slice(0,6).includes(r.reason as HistoricalCaseReason)||
       r.correctness!==null)return fail();
   }
  }
  const key=r.prediction_id||"no-prediction:"+r.application_id;
  if(seen.has(key))return fail();
  seen.add(key);
  records.push({
   predictionId:r.prediction_id as string|null,nctId:r.nct_id as string|null,
   applicationId:r.application_id as string,
   predictedDecision:r.predicted_decision as HistoricalCase["predictedDecision"],
   actualDecision:r.actual_decision as HistoricalCase["actualDecision"],
   decisionDate:r.decision_date as string|null,
   predictionCreatedAt:r.prediction_created_at as string|null,
   evidenceCutoff:r.evidence_cutoff as string|null,
   disposition:r.disposition as HistoricalCaseDisposition,
   reason:r.reason as HistoricalCaseReason,
   fdaSourceUrl:r.fda_source_url as string|null,
   correctness:r.correctness as boolean|null
  });
 }
 return {total:data.total as number,returned:data.returned as number,limit:50,
  reasonCounts:Object.fromEntries(reasons.map(r=>[r,(data.reason_counts as Record<string,number>)[r]??0]))
    as Record<HistoricalCaseReason,number>,records};
}
