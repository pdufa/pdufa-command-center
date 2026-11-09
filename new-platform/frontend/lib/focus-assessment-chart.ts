/**
 * Exact FDA application-cycle prediction audit.
 *
 * The current source registry intentionally has no synthetic predictions or
 * retrospective guesses. A completed and frozen prediction alone does not
 * establish accuracy; accuracy requires a later, verified FDA decision.
 * Approval vs CRL is a binary primary-decision comparison. A review delay
 * may precede either one and must be evaluated separately, never as a third
 * mutually exclusive wedge of this pie chart.
 */
import registry from "../data/fdaPredictionDecisionAudit.json";

export type Decision="APPROVAL"|"CRL";
export type CalibrationStatus="VALIDATED"|"NOT_VALIDATED";
export type PredictionDecisionRecord={
  predictionId:string;
  applicationCycleId:string;
  ticker:string;
  ncts:string[];
  drug:string;
  indication:string;
  status:"COMPLETED"|"DRAFT";
  completedAt:string|null;
  predictedOutcome:Decision|"ABSTAIN";
  calibrationStatus:CalibrationStatus;
  approvalProbability:number|null;
  crlProbability:number|null;
  evaluationCohort:"PROSPECTIVE"|"HISTORICAL_LOCKED";
  actualOutcome:Decision|"PENDING"|"OTHER"|null;
  actualDecisionAt:string|null;
  actualDecisionSourceUrl:string|null;
  actualDecisionVerified:boolean;
};

export type PieSlice={
  key:string;label:string;value:number;color:string;
};
export type CompletedPrediction={
  predictionId:string;
  applicationCycleId:string;
  ticker:string;
  ncts:string[];
  drug:string;
  indication:string;
  completedAt:string;
  predictedOutcome:Decision;
  calibrationStatus:CalibrationStatus;
  actualOutcome:Decision|"PENDING";
  actualDecisionAt:string|null;
  actualSourceUrl:string|null;
  probabilitySlices:PieSlice[];
};

export type PredictionAccuracySummary={
  totalCompleted:number;
  compared:number;
  correct:number;
  incorrect:number;
  awaitingDecision:number;
  accuracyPercent:number|null;
  comparisonSlices:PieSlice[];
  latest:CompletedPrediction|null;
  auditAsOf:string|null;
  cohortScope:"PROSPECTIVE_AND_PREDECISION_LOCKED_HISTORICAL";
};

const matchIso=(s:unknown):s is string=>
  typeof s==="string"&&
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(s)&&
  Number.isFinite(Date.parse(s));
const decision=(x:unknown):x is Decision=>x==="APPROVAL"||x==="CRL";
const validNct=(x:unknown)=>typeof x==="string"&&/^NCT\d{8}$/.test(x);
const validHttps=(x:unknown)=>typeof x==="string"&&/^https:\/\/[^\s/]+(?:\/[^\s]*)?$/.test(x);
const validProbability=(x:unknown)=>typeof x==="number"&&Number.isFinite(x)&&x>=0&&x<=1;

export function summarizeFdaPredictionAccuracy(
  rows:readonly PredictionDecisionRecord[],
  auditAsOf:string|null=null
):PredictionAccuracySummary{
  const frozen=rows.filter(row=>
    row&&row.status==="COMPLETED"&&
    typeof row.predictionId==="string"&&row.predictionId.length>0&&
    typeof row.applicationCycleId==="string"&&row.applicationCycleId.length>0&&
    typeof row.ticker==="string"&&row.ticker.length>0&&
    Array.isArray(row.ncts)&&row.ncts.length>0&&row.ncts.every(validNct)&&
    matchIso(row.completedAt)&&decision(row.predictedOutcome)&&
    ["PROSPECTIVE","HISTORICAL_LOCKED"].includes(row.evaluationCohort)
  ).sort((a,b)=>Date.parse(a.completedAt!)-Date.parse(b.completedAt!)||
      a.predictionId.localeCompare(b.predictionId));

  // Evaluate only the FIRST completed/frozen forecast for each application
  // cycle. Later revised forecasts must not inflate accuracy or cherry-pick
  // the version nearest to the already-known decision.
  const primaryByCycle=new Map<string,PredictionDecisionRecord>();
  for(const row of frozen){
    if(!primaryByCycle.has(row.applicationCycleId))
      primaryByCycle.set(row.applicationCycleId,row);
  }
  let correct=0,incorrect=0,awaitingDecision=0;
  for(const row of primaryByCycle.values()){
    const matched=decision(row.actualOutcome)&&
      matchIso(row.actualDecisionAt)&&
      Date.parse(row.actualDecisionAt)>Date.parse(row.completedAt!)&&
      row.actualDecisionVerified===true&&validHttps(row.actualDecisionSourceUrl);
    if(!matched){awaitingDecision++;continue;}
    if(row.actualOutcome===row.predictedOutcome)correct++;
    else incorrect++;
  }
  const compared=correct+incorrect;
  const current=frozen.length?frozen[frozen.length-1]:null;
  const calibrated=current?.calibrationStatus==="VALIDATED"&&
    validProbability(current.approvalProbability)&&
    validProbability(current.crlProbability)&&
    Math.abs(current.approvalProbability!+current.crlProbability!-1)<0.0001;
  const latest:CompletedPrediction|null=current?{
    predictionId:current.predictionId,
    applicationCycleId:current.applicationCycleId,
    ticker:current.ticker,
    ncts:current.ncts,
    drug:current.drug,
    indication:current.indication,
    completedAt:current.completedAt!,
    predictedOutcome:current.predictedOutcome as Decision,
    calibrationStatus:current.calibrationStatus,
    actualOutcome:decision(current.actualOutcome)&&
      current.actualDecisionVerified===true&&
      matchIso(current.actualDecisionAt)&&
      Date.parse(current.actualDecisionAt)>Date.parse(current.completedAt!)&&
      validHttps(current.actualDecisionSourceUrl)
      ?current.actualOutcome:"PENDING",
    actualDecisionAt:current.actualDecisionAt,
    actualSourceUrl:validHttps(current.actualDecisionSourceUrl)?current.actualDecisionSourceUrl:null,
    probabilitySlices:calibrated?[
      {key:"approval",label:"FDA approval",value:current.approvalProbability!,color:"#168a6d"},
      {key:"crl",label:"Complete Response Letter",value:current.crlProbability!,color:"#c86b50"}
    ]:[]
  }:null;
  return {
    totalCompleted:primaryByCycle.size,
    compared,correct,incorrect,awaitingDecision,
    accuracyPercent:compared?100*correct/compared:null,
    comparisonSlices:[
      {key:"correct",label:"Prediction matched FDA decision",value:correct,color:"#168a6d"},
      {key:"incorrect",label:"Prediction differed from FDA decision",value:incorrect,color:"#c86b50"}
    ],
    latest,
    auditAsOf,
    cohortScope:"PROSPECTIVE_AND_PREDECISION_LOCKED_HISTORICAL"
  };
}

export function getAssessmentPieData(){
  if(registry.schemaVersion!==1||registry.provenance!=="INDEPENDENT_FDA_DECISION_AUDIT"||
    !Array.isArray(registry.records))throw Error("FDA_DECISION_AUDIT_UNAVAILABLE");
  return summarizeFdaPredictionAccuracy(
    registry.records as PredictionDecisionRecord[],
    registry.asOf
  );
}
