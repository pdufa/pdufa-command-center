/** Fail-closed audit of the read-only, application-scoped historical FDA
 * decision validation endpoint. Only PROSPECTIVE pre-decision predictions
 * count; the API's counts are reconciled before they enter final SURVEY.
 * This audit does not certify the underlying source records or approve a
 * prediction model.
 */
export type FdaDecision="PASS"|"CRL"|"EXTENSION";
export type FdaAccuracy={evaluated:number;correct:number;accuracy:number|null};
export type FinalFdaValidation={
 backendStatus:"NOT_VALIDATED"|"REVIEW_REQUIRED";
 totalApplications:number;knownOutcomes:number;
 predictionRecords:number;temporallyEligible:number;lookaheadExcluded:number;
 selectedApplications:number;scored:number;abstained:number;correct:number;
 accuracyByDecision:Record<FdaDecision,FdaAccuracy>;
 observedAccuracy:number|null;calibration:null;modelValidated:false;
 status:"NO_ELIGIBLE_PREDICTIONS"|"REVIEW_REQUIRED_NOT_VALIDATED";
 verifiedAt:string;limitation:string;
};
const labels=["PASS","CRL","EXTENSION"] as const;
const whole=(value:unknown):value is number=>
 typeof value==="number"&&Number.isSafeInteger(value)&&value>=0;
const obj=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==="object"&&!Array.isArray(v);
const fail=():never=>{throw Error("FDA_HISTORICAL_VALIDATION_INCONSISTENT")};
export function auditFinalFdaValidation(input:unknown):FinalFdaValidation{
 if(!obj(input))return fail();
 const raw=input;
 if(raw.status!=="NOT_VALIDATED"&&raw.status!=="REVIEW_REQUIRED")return fail();
 const fields=[
  "total_applications","eligible_applications","number_evaluated",
  "number_abstained","number_with_known_outcomes","prediction_records",
  "temporally_eligible_predictions","excluded_for_lookahead_or_missing_outcome",
  "unresolved_outcomes"
 ];
 if(fields.some(k=>!whole(raw[k]))||raw.calibration_metrics!==null||
    !obj(raw.counts)||!obj(raw.accuracy_by_decision)||!obj(raw.data_completeness)||
    !whole(raw.counts.correct_predictions)||!whole(raw.counts.scored_predictions)||
    !whole(raw.counts.abstentions)||!whole(raw.data_completeness.applications)||
    !whole(raw.data_completeness.verified_outcomes)||
    typeof raw.verified_at!=="string"||!Number.isFinite(Date.parse(raw.verified_at))||
    typeof raw.limitation!=="string"||raw.limitation.length<25)return fail();
 const total=raw.total_applications as number;
 const eligible=raw.eligible_applications as number;
 const scored=raw.number_evaluated as number;
 const abstained=raw.number_abstained as number;
 const observed=raw.number_with_known_outcomes as number;
 const predictions=raw.prediction_records as number;
 const temporal=raw.temporally_eligible_predictions as number;
 const excluded=raw.excluded_for_lookahead_or_missing_outcome as number;
 const correct=raw.counts.correct_predictions as number;
 if(temporal+excluded!==predictions||eligible>temporal||
    eligible>total||observed>total||eligible>observed||
    raw.unresolved_outcomes!==total-observed||
    scored+abstained!==eligible||correct>scored||
    raw.counts.scored_predictions!==scored||
    raw.counts.abstentions!==abstained||
    raw.data_completeness.applications!==total||
    raw.data_completeness.verified_outcomes!==observed||
    (scored===0&&raw.status!=="NOT_VALIDATED")||
    (scored>0&&raw.status!=="REVIEW_REQUIRED"))return fail();
 const category={} as Record<FdaDecision,FdaAccuracy>;
 for(const key of labels){
  const row=raw.accuracy_by_decision[key];
  if(!obj(row)||!whole(row.evaluated)||!whole(row.correct)||
     row.correct>row.evaluated)return fail();
  const n=row.evaluated as number,c=row.correct as number;
  if(scored<30||n<10){
   if(row.accuracy!==null)return fail();
  }else if(typeof row.accuracy!=="number"||
           !Number.isFinite(row.accuracy)||row.accuracy<0||row.accuracy>1||
           Math.abs(row.accuracy-c/n)>1e-9)return fail();
  category[key]={evaluated:n,correct:c,accuracy:row.accuracy as number|null};
 }
 if(labels.reduce((n,k)=>n+category[k].evaluated,0)!==scored||
    labels.reduce((n,k)=>n+category[k].correct,0)!==correct)return fail();
 return {
  backendStatus:raw.status as FinalFdaValidation["backendStatus"],
  totalApplications:total,knownOutcomes:observed,
  predictionRecords:predictions,temporallyEligible:temporal,lookaheadExcluded:excluded,
  selectedApplications:eligible,scored,abstained,correct,accuracyByDecision:category,
  observedAccuracy:scored>=30?correct/scored:null,
  calibration:null,modelValidated:false,
  status:scored===0?"NO_ELIGIBLE_PREDICTIONS":"REVIEW_REQUIRED_NOT_VALIDATED",
  verifiedAt:raw.verified_at,limitation:raw.limitation
 };
}
