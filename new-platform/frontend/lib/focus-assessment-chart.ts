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
  researchOnly?:boolean;
  sourceFreezeUrl?:string;
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
  decisionVerdict:"ACCURATE"|"NOT_ACCURATE"|"AWAITING_DECISION";
  decisionComparisonSlices:PieSlice[];
  probabilitySlices:PieSlice[];
  researchOnly:boolean;
  sourceFreezeUrl:string|null;
};

export type OverallAccuracyTrendPoint={
  date:string;compared:number;correct:number;incorrect:number;
  accuratePct:number;notAccuratePct:number;
};
export type LastPredictionTrendPoint={
  predictionId:string;recordedAt:string;approvalPct:number;crlPct:number;
};
export type PredictionAccuracySummary={
  totalCompleted:number;
  compared:number;
  correct:number;
  incorrect:number;
  awaitingDecision:number;
  accuracyPercent:number|null;
  comparisonSlices:PieSlice[];
  overallTrend:OverallAccuracyTrendPoint[];
  latestTrend:LastPredictionTrendPoint[];
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
  // An actual FDA outcome must occur AFTER the originally frozen forecast;
  // revised forecasts are never allowed to re-score that same application.
  const matchedDecision=(row:PredictionDecisionRecord)=>
    decision(row.actualOutcome)&&matchIso(row.actualDecisionAt)&&
    Date.parse(row.actualDecisionAt)>Date.parse(row.completedAt!)&&
    row.actualDecisionVerified===true&&validHttps(row.actualDecisionSourceUrl);
  const resolved=Array.from(primaryByCycle.values()).filter(matchedDecision);
  let correct=0,incorrect=0;
  for(const row of resolved){
    if(row.actualOutcome===row.predictedOutcome)correct++;
    else incorrect++;
  }
  const awaitingDecision=primaryByCycle.size-resolved.length;
  const compared=correct+incorrect;

  // Cumulative accuracy at each *actual FDA action date*, using the same
  // independently verified applications and denominator as the accuracy pie.
  // Multiple actions on the same date form a single timeline checkpoint.
  const sortedDecisions=[...resolved].sort((a,b)=>
    Date.parse(a.actualDecisionAt!)-Date.parse(b.actualDecisionAt!)||
    a.applicationCycleId.localeCompare(b.applicationCycleId));
  const overallTrend:OverallAccuracyTrendPoint[]=[];
  let runningCorrect=0,runningIncorrect=0;
  for(const row of sortedDecisions){
    if(row.predictedOutcome===row.actualOutcome)runningCorrect++;
    else runningIncorrect++;
    const date=row.actualDecisionAt!.slice(0,10);
    const count=runningCorrect+runningIncorrect;
    const point={
      date,compared:count,correct:runningCorrect,incorrect:runningIncorrect,
      accuratePct:Number((100*runningCorrect/count).toFixed(2)),
      notAccuratePct:Number((100*runningIncorrect/count).toFixed(2))
    };
    if(overallTrend.length&&overallTrend[overallTrend.length-1].date===date)
      overallTrend[overallTrend.length-1]=point;
    else overallTrend.push(point);
  }
  const current=frozen.length?frozen[frozen.length-1]:null;
  const calibrated=current?.calibrationStatus==="VALIDATED"&&
    validProbability(current.approvalProbability)&&
    validProbability(current.crlProbability)&&
    Math.abs(current.approvalProbability!+current.crlProbability!-1)<0.0001;
  const latestDecisionVerified=Boolean(current&&decision(current.actualOutcome)&&
    current.actualDecisionVerified===true&&
    matchIso(current.actualDecisionAt)&&
    Date.parse(current.actualDecisionAt)>Date.parse(current.completedAt!)&&
    validHttps(current.actualDecisionSourceUrl));
  const latestMatched=latestDecisionVerified&&current?.predictedOutcome===current?.actualOutcome;
  // The last trial's competition is the Approval-vs-CRL outlook history
  // for that exact FDA application cycle, never another ticker or trial.
  // Only already-completed and calibrated snapshots can contribute.
  const latestCutoff=current&&matchIso(current.actualDecisionAt)
    ?Date.parse(current.actualDecisionAt):Infinity;
  const latestTrend:LastPredictionTrendPoint[]=current?
    frozen.filter(row=>
      row.applicationCycleId===current.applicationCycleId&&
      row.calibrationStatus==="VALIDATED"&&
      validProbability(row.approvalProbability)&&
      validProbability(row.crlProbability)&&
      Math.abs(row.approvalProbability!+row.crlProbability!-1)<0.0001&&
      Date.parse(row.completedAt!)<latestCutoff&&
      (!matchIso(row.actualDecisionAt)||
        Date.parse(row.completedAt!)<Date.parse(row.actualDecisionAt))
    ).map(row=>({
      predictionId:row.predictionId,recordedAt:row.completedAt!,
      approvalPct:Number((row.approvalProbability!*100).toFixed(2)),
      crlPct:Number((row.crlProbability!*100).toFixed(2))
    })):[];
  const latest:CompletedPrediction|null=current?{
    predictionId:current.predictionId,
    researchOnly:current.researchOnly===true,
    sourceFreezeUrl:validHttps(current.sourceFreezeUrl)?current.sourceFreezeUrl!:null,
    applicationCycleId:current.applicationCycleId,
    ticker:current.ticker,
    ncts:current.ncts,
    drug:current.drug,
    indication:current.indication,
    completedAt:current.completedAt!,
    predictedOutcome:current.predictedOutcome as Decision,
    calibrationStatus:current.calibrationStatus,
    actualOutcome:latestDecisionVerified&&decision(current.actualOutcome)
      ?current.actualOutcome:"PENDING",
    actualDecisionAt:current.actualDecisionAt,
    actualSourceUrl:latestDecisionVerified&&validHttps(current.actualDecisionSourceUrl)?current.actualDecisionSourceUrl:null,
    decisionVerdict:!latestDecisionVerified?"AWAITING_DECISION":latestMatched?"ACCURATE":"NOT_ACCURATE",
    decisionComparisonSlices:[
      {key:"accurate",label:"Accurate",value:latestMatched?1:0,color:"#168a6d"},
      {key:"notAccurate",label:"Not Accurate",value:latestDecisionVerified&&!latestMatched?1:0,color:"#c86b50"}
    ],
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
      {key:"accurate",label:"Accurate",value:correct,color:"#168a6d"},
      {key:"notAccurate",label:"Not Accurate",value:incorrect,color:"#c86b50"}
    ],
    overallTrend,latestTrend,
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
