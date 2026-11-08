/**
 * Historical outcomes are NOT training examples until temporal provenance is
 * independently verified. No hard-coded FOCUS outcome or simulated efficacy
 * source is used in the real application. This evaluator is a research tool:
 * even good retrospective metrics do not enable live percentage forecasts.
 */
export type BacktestOutcome="APPROVAL"|"CRL"|"REVIEW_DELAY";
export type LockedHistoricalCase={
  cycleId:string;issuer:string;predictionAt:string;featureCutoff:string;outcomeAt:string;
  outcomeSourceUrl:string;
  probability:Record<BacktestOutcome,number>;
  observed:Record<BacktestOutcome,boolean>;
};
export type OutcomeCalibration={
  outcome:BacktestOutcome;holdoutCount:number;positives:number;negatives:number;
  brierScore:number|null;expectedCalibrationError:number|null;
};
export type HistoricalCalibration={
  status:"RESEARCH_ONLY_NOT_RELEASED";
  inputCount:number;eligibleCount:number;excludedCount:number;
  chronologicalTrainingCount:number;chronologicalHoldoutCount:number;
  metrics:OutcomeCalibration[];
  releasePermitted:false;missing:string[];
  explanation:string;
};
const OUTCOMES:BacktestOutcome[]=["APPROVAL","CRL","REVIEW_DELAY"];
const ISO=/^\d{4}-\d{2}-\d{2}$/;
const validDate=(s:string)=>ISO.test(s)&&!Number.isNaN(Date.parse(s+"T00:00:00Z"));
export function evaluateHistoricalCalibration(rows:readonly LockedHistoricalCase[]):HistoricalCalibration{
  const seen=new Set<string>();
  const eligible=rows.filter(row=>{
    if(!row||typeof row.cycleId!=="string"||!row.cycleId.trim()||
      typeof row.issuer!=="string"||!row.issuer.trim()||seen.has(row.cycleId))return false;
    if(![row.predictionAt,row.featureCutoff,row.outcomeAt].every(validDate)||
      row.featureCutoff>row.predictionAt||row.predictionAt>=row.outcomeAt)return false;
    if(!/^https:\/\//.test(row.outcomeSourceUrl))return false;
    if(!OUTCOMES.every(k=>Number.isFinite(row.probability[k])&&row.probability[k]>=0&&row.probability[k]<=1&&
      typeof row.observed[k]==="boolean"))return false;
    if(row.observed.APPROVAL&&row.observed.CRL)return false;
    seen.add(row.cycleId);
    return true;
  }).sort((a,b)=>a.outcomeAt.localeCompare(b.outcomeAt)||a.cycleId.localeCompare(b.cycleId));
  // Holdout is chronologically later by resolved FDA decision, never randomized
  // across older and newer regulatory regimes. No training is performed here.
  const holdoutStart=Math.floor(eligible.length*0.7);
  const holdout=eligible.slice(holdoutStart);
  const metrics=OUTCOMES.map(outcome=>{
    const positives=holdout.filter(x=>x.observed[outcome]).length;
    const bins=Array.from({length:5},()=>[] as LockedHistoricalCase[]);
    for(const row of holdout)bins[Math.min(4,Math.floor(row.probability[outcome]*5))].push(row);
    const brier=holdout.reduce((sum,x)=>sum+(x.probability[outcome]-Number(x.observed[outcome]))**2,0);
    const ece=bins.reduce((sum,bin)=>{
      if(!bin.length)return sum;
      const p=bin.reduce((n,x)=>n+x.probability[outcome],0)/bin.length;
      const o=bin.filter(x=>x.observed[outcome]).length/bin.length;
      return sum+bin.length/holdout.length*Math.abs(p-o);
    },0);
    return {outcome,holdoutCount:holdout.length,positives,negatives:holdout.length-positives,
      brierScore:holdout.length?Number((brier/holdout.length).toFixed(4)):null,
      expectedCalibrationError:holdout.length?Number(ece.toFixed(4)):null};
  });
  const missing=[
    "Independent verification of dated FDA application outcomes and evidence availability",
    "Frozen and reproducible model predictions recorded before each outcome",
    "Issuer-grouped checks to prevent overlapping sponsor and program leakage",
    "Prospective external validation, regime-shift testing, uncertainty intervals and governance approval",
    "Outcome-specific minimum positive/negative events and clinically appropriate performance gates"
  ];
  if(eligible.length<100)missing.unshift("Fewer than 100 valid historical applications; sample size is insufficient for this internal research gate.");
  if(metrics.some(x=>x.positives<20||x.negatives<20))
    missing.unshift("At least one temporal holdout outcome has fewer than 20 positive or negative examples.");
  return {status:"RESEARCH_ONLY_NOT_RELEASED",inputCount:rows.length,
    eligibleCount:eligible.length,excludedCount:rows.length-eligible.length,
    chronologicalTrainingCount:holdoutStart,chronologicalHoldoutCount:holdout.length,
    metrics,releasePermitted:false,missing,
    explanation:"Brier and calibration error summarize a historical locked holdout only. This function does not fit a model, certify cohort representativeness, validate original source truth, or unlock prospective percentages."};
}
export const HISTORICAL_CALIBRATION=evaluateHistoricalCalibration([]);
