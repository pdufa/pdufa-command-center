import {auditHistoricalEvidence,type HistoricalEvidenceRow} from "./decision-historical-evidence";
import {summarizeHistoricalCalibration,type CalibrationSummary,type DiscriminationSummary} from "./decision-calibration";

/** A declared plan is an audit input, never proof that it was actually frozen in advance. */
export type ChronologicalCalibrationPlan={
 modelVersion:string;
 planSource:string;
 frozenAt:string;
 holdoutStart:string;
 holdoutEnd:string;
 evaluatedAt:string;
 trainingProgramIds:string[];
 holdoutProgramIds:string[];
};
export type ChronologicalCalibrationRow=HistoricalEvidenceRow&{applicationNumber:string;modelVersion:string;subgroup:string};
export type ReliabilityBin={lower:number;upper:number;count:number;meanProbability:number|null;observedApprovalRate:number|null};
export type HistoricalForecastError={
 programId:string;applicationNumber:string;modelVersion:string;subgroup:string;
 predictedAt:string;predictionCapturedAt:string;decisionAt:string;decisionObservedAt:string;
 predictionSource:string;decisionSource:string;
 approvalProbability:number;observedApproved:boolean;probabilityError:number;squaredError:number;logLoss:number;
};
export type ChronologicalHoldoutMetrics={
 brierScore:number;
 logLoss:number;
 trainingBaselineProbability:number;
 baselineBrier:number;
 improvementVsTrainingBaseline:number;
 expectedCalibrationError:number;
 discrimination:DiscriminationSummary;
 forecastErrors:HistoricalForecastError[];
 abstentionCoverage:{evaluatedProbabilities:number;eligibleDecisionCount:null;explicitAbstentionCount:null;coverage:null;unavailableReason:string};
 uncertainty:{confidenceInterval:null;method:null;unavailableReason:string};
 reliabilityBins:ReliabilityBin[];
 subgroups:{name:string;metrics:CalibrationSummary}[];
};
export type ChronologicalCalibrationAssessment={
 status:"NOT_READY"|"RESEARCH_ONLY";
 issues:string[];
 warnings:string[];
 trainingSampleSize:number;
 holdoutSampleSize:number;
 holdout:ChronologicalHoldoutMetrics|null;
 validatedPredictionAccuracy:false;
 tradeAuthorized:false;
};

/** Evaluate an untouched, prespecified time window against a baseline fitted only on
 * outcomes observable before the freeze. This does not train or certify a model.
 * Source documents, the plan's original timestamp, denominator completeness and
 * any later model selection still require independent review outside this function. */
export function evaluateChronologicalCalibration(
 training:ChronologicalCalibrationRow[],holdout:ChronologicalCalibrationRow[],
 plan:ChronologicalCalibrationPlan,minimumPerPartition=30
):ChronologicalCalibrationAssessment{
 const issues:string[]=[];
 const warnings=[
  "Research diagnostics only; declared review flags, model versions, plan timestamps and URLs require independent source verification.",
  "A complete approval/nonapproval denominator, independent forward validation and review of model selection remain required. No validated prediction accuracy or trading authorization is established.",
  "AUROC measures ranking, not calibrated probability or classification accuracy. No classification threshold, abstention policy, complete eligible population or independent uncertainty plan is inferred from these forecast rows."
 ];
 const freeze=Date.parse(plan.frozenAt),start=Date.parse(plan.holdoutStart),end=Date.parse(plan.holdoutEnd),evaluated=Date.parse(plan.evaluatedAt);
 if(![freeze,start,end,evaluated].every(Number.isFinite)||freeze>start||start>=end||end>evaluated)
  issues.push("Invalid frozen plan or chronological holdout boundaries");
 if(!plan.modelVersion.trim())issues.push("Frozen model version required");
 try{const url=new URL(plan.planSource);if(url.protocol!=="https:"||!url.hostname)issues.push("HTTPS frozen plan source required");}
 catch{issues.push("HTTPS frozen plan source required");}
 const seen=new Set<string>();
 const applicationPartitions=new Map<string,"Training"|"Holdout">();
 for(const [name,rows,expected] of [["Training",training,plan.trainingProgramIds],["Holdout",holdout,plan.holdoutProgramIds]] as const){
  const audit=auditHistoricalEvidence(rows,minimumPerPartition);
  issues.push(...audit.issues.map(issue=>`${name}: ${issue}`));
  const declared=new Set(expected);
  if(declared.size!==expected.length||expected.some(id=>!/^PDUFA-\d{6,}$/.test(id)))
   issues.push(`${name}: invalid or duplicate prespecified program identity`);
  if(rows.length!==expected.length||rows.some(row=>!declared.has(row.programId)))
   issues.push(`${name}: cohort differs from prespecified membership; missing cases cannot be silently dropped`);
  for(const row of rows){
   if(seen.has(row.programId))issues.push("Training and holdout identities must be disjoint");
   seen.add(row.programId);
   if(!/^(NDA|BLA)\d{6}$/.test(row.applicationNumber))issues.push(`${name}: canonical FDA application number required`);
   else{
    const partition=applicationPartitions.get(row.applicationNumber);
    if(partition&&partition!==name)issues.push("FDA application cannot cross training and holdout partitions");
    applicationPartitions.set(row.applicationNumber,name);
   }
   if(row.modelVersion!==plan.modelVersion)issues.push(`${name}: forecast model version differs from frozen model`);
   if(!row.subgroup.trim())issues.push(`${name}: subgroup identity required`);
   const predicted=Date.parse(row.predictedAt),captured=Date.parse(row.predictionCapturedAt),observed=Date.parse(row.decisionObservedAt);
   if(name==="Training"){
    if(!Number.isFinite(freeze)||predicted>=freeze||captured>=freeze||observed>=freeze)
     issues.push("Training outcome or forecast unavailable at plan freeze");
   }else{
    if(!Number.isFinite(start)||!Number.isFinite(end)||predicted<start||predicted>=end||captured>=end)
     issues.push("Holdout forecast outside prespecified window");
    if(!Number.isFinite(evaluated)||observed>=evaluated)
     issues.push("Holdout outcome unavailable at evaluation cutoff");
   }
  }
 }
 const result:ChronologicalCalibrationAssessment={status:"NOT_READY",issues,warnings,
  trainingSampleSize:training.length,holdoutSampleSize:holdout.length,holdout:null,
  validatedPredictionAccuracy:false,tradeAuthorized:false};
 if(issues.length)return result;
 const predictions=holdout.map(row=>({programId:row.programId,predictedAt:row.predictedAt,
  decisionAt:row.decisionAt,approvalProbability:row.probability,approved:row.approved,cohort:row.subgroup}));
 const summary=summarizeHistoricalCalibration(predictions,minimumPerPartition);
 if(summary.status!=="RESEARCH_ONLY"||summary.brierScore===null||summary.logLoss===null){
  issues.push(...summary.issues);return result;
 }
 const trainingBaselineProbability=training.filter(row=>row.approved).length/training.length;
 const baselineBrier=holdout.reduce((sum,row)=>sum+(trainingBaselineProbability-Number(row.approved))**2,0)/holdout.length;
 const reliabilityBins:ReliabilityBin[]=Array.from({length:10},(_,index)=>{
  const rows=holdout.filter(row=>Math.min(9,Math.floor(row.probability*10))===index);
  return {lower:index/10,upper:(index+1)/10,count:rows.length,
   meanProbability:rows.length?rows.reduce((sum,row)=>sum+row.probability,0)/rows.length:null,
   observedApprovalRate:rows.length?rows.filter(row=>row.approved).length/rows.length:null};
 });
 const expectedCalibrationError=reliabilityBins.reduce((sum,bin)=>sum+bin.count/holdout.length*Math.abs((bin.meanProbability??0)-(bin.observedApprovalRate??0)),0);
 const subgroups=[...new Set(predictions.map(row=>row.cohort))].sort().map(name=>({name,
  metrics:summarizeHistoricalCalibration(predictions.filter(row=>row.cohort===name),minimumPerPartition)}));
 const forecastErrors:HistoricalForecastError[]=[...holdout].sort((a,b)=>a.programId<b.programId?-1:a.programId>b.programId?1:0).map(row=>{
  const probabilityError=row.probability-Number(row.approved);
  return {programId:row.programId,applicationNumber:row.applicationNumber,modelVersion:row.modelVersion,subgroup:row.subgroup,
   predictedAt:row.predictedAt,predictionCapturedAt:row.predictionCapturedAt,decisionAt:row.decisionAt,decisionObservedAt:row.decisionObservedAt,
   predictionSource:row.predictionSource,decisionSource:row.decisionSource,
   approvalProbability:row.probability,observedApproved:row.approved,probabilityError,squaredError:probabilityError**2,
   logLoss:-Math.log(Math.max(1e-12,row.approved?row.probability:1-row.probability))};
 });
 return {...result,status:"RESEARCH_ONLY",holdout:{brierScore:summary.brierScore,logLoss:summary.logLoss,
  trainingBaselineProbability,baselineBrier,improvementVsTrainingBaseline:baselineBrier-summary.brierScore,
  expectedCalibrationError,discrimination:summary.discrimination,forecastErrors,
  abstentionCoverage:{evaluatedProbabilities:holdout.length,eligibleDecisionCount:null,explicitAbstentionCount:null,coverage:null,
   unavailableReason:"The frozen plan does not enumerate an eligible decision universe, explicit abstentions or a predeclared abstention policy; missing forecasts cannot be counted as abstentions."},
  uncertainty:{confidenceInterval:null,method:null,
   unavailableReason:"No prespecified independent or application-clustered uncertainty analysis is supplied; multiple cycles may share one application."},
  reliabilityBins,subgroups}};
}
