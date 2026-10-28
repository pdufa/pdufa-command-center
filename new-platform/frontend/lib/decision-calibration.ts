/** Point-in-time validation metrics. Never use future outcomes to create a historical forecast. */
export type HistoricalPrediction={programId:string;predictedAt:string;decisionAt:string;approvalProbability:number;approved:boolean;cohort:string};
export type DiscriminationSummary={auroc:number|null;approvalCount:number|null;nonapprovalCount:number|null;unavailableReason:"INVALID_OR_INSUFFICIENT_DATA"|"SINGLE_OUTCOME_CLASS"|null};
export type CalibrationSummary={status:"INSUFFICIENT_DATA"|"RESEARCH_ONLY";sampleSize:number;brierScore:number|null;logLoss:number|null;baselineBrier:number|null;improvementVsBaseline:number|null;discrimination:DiscriminationSummary;issues:string[]};

/** Mann–Whitney rank statistic: tied probabilities share average rank and receive
 * half credit. Outcome labels are used only for evaluation, never forecast creation.
 * No interval is inferred from potentially dependent review cycles. */
function discrimination(rows:HistoricalPrediction[]):DiscriminationSummary{
 const approvalCount=rows.filter(row=>row.approved).length,nonapprovalCount=rows.length-approvalCount;
 if(!approvalCount||!nonapprovalCount)return {auroc:null,approvalCount,nonapprovalCount,unavailableReason:"SINGLE_OUTCOME_CLASS"};
 const sorted=[...rows].sort((a,b)=>a.approvalProbability-b.approvalProbability);
 let approvalRanks=0;
 for(let first=0;first<sorted.length;){
  let after=first+1;
  while(after<sorted.length&&sorted[after].approvalProbability===sorted[first].approvalProbability)after++;
  const averageRank=(first+1+after)/2;
  for(let index=first;index<after;index++)if(sorted[index].approved)approvalRanks+=averageRank;
  first=after;
 }
 const auroc=(approvalRanks-approvalCount*(approvalCount+1)/2)/(approvalCount*nonapprovalCount);
 return {auroc,approvalCount,nonapprovalCount,unavailableReason:null};
}
export function summarizeHistoricalCalibration(rows:HistoricalPrediction[],minimumSample=30):CalibrationSummary{
 const issues:string[]=[];const seen=new Set<string>();let total=0,loss=0,approved=0;
 for(const r of rows){
  const predicted=Date.parse(r.predictedAt),decision=Date.parse(r.decisionAt);
  if(!/^PDUFA-\d{6,}$/.test(r.programId)||seen.has(r.programId)){issues.push("Duplicate or invalid program identity");continue;}
  seen.add(r.programId);
  if(!Number.isFinite(predicted)||!Number.isFinite(decision)||predicted>=decision){issues.push("Prediction must precede decision");continue;}
  if(!Number.isFinite(r.approvalProbability)||r.approvalProbability<0||r.approvalProbability>1||typeof r.approved!=="boolean"){issues.push("Invalid probability or outcome");continue;}
  const y=r.approved?1:0;const p=r.approvalProbability;
  total+=(p-y)**2;loss+=-(y*Math.log(Math.max(1e-12,p))+(1-y)*Math.log(Math.max(1e-12,1-p)));approved+=y;
 }
 if(issues.length||seen.size<minimumSample||!Number.isSafeInteger(minimumSample)||minimumSample<30||rows.length!==seen.size||rows.length!==0&&rows.some(r=>!r.cohort.trim()))issues.push("Independent historical validation requirements not met");
 if(issues.length||!rows.length)return {status:"INSUFFICIENT_DATA",sampleSize:rows.length,brierScore:null,logLoss:null,baselineBrier:null,improvementVsBaseline:null,
  discrimination:{auroc:null,approvalCount:null,nonapprovalCount:null,unavailableReason:"INVALID_OR_INSUFFICIENT_DATA"},issues};
 const base=approved/rows.length,baselineBrier=base*(1-base),brierScore=total/rows.length;
 return {status:"RESEARCH_ONLY",sampleSize:rows.length,brierScore,logLoss:loss/rows.length,baselineBrier,improvementVsBaseline:baselineBrier-brierScore,discrimination:discrimination(rows),issues:[]};
}
