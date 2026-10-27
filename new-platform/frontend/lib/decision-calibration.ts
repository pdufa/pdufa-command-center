/** Point-in-time validation metrics. Never use future outcomes to create a historical forecast. */
export type HistoricalPrediction={programId:string;predictedAt:string;decisionAt:string;approvalProbability:number;approved:boolean;cohort:string};
export type CalibrationSummary={status:"INSUFFICIENT_DATA"|"RESEARCH_ONLY";sampleSize:number;brierScore:number|null;logLoss:number|null;baselineBrier:number|null;improvementVsBaseline:number|null;issues:string[]};
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
 if(issues.length||!rows.length)return {status:"INSUFFICIENT_DATA",sampleSize:rows.length,brierScore:null,logLoss:null,baselineBrier:null,improvementVsBaseline:null,issues};
 const base=approved/rows.length,baselineBrier=base*(1-base),brierScore=total/rows.length;
 return {status:"RESEARCH_ONLY",sampleSize:rows.length,brierScore,logLoss:loss/rows.length,baselineBrier,improvementVsBaseline:baselineBrier-brierScore,issues:[]};
}
