import snapshot from '../data/focus123EvidenceReadiness20261115.json';

export type ReadinessScore={
 nct:string;level:number;runId:string;reportHash:string;executedAt:string;
 checkCount:number;sourceVerified:number;notYetExpected:number;
 applicable:number;unresolved:number;evidenceReadinessScore:number;
};
type ScientificSlot={mode?:string;nct?:string;level?:number;runId?:string;
 engineVersion?:string;executedAt?:string;score?:{kind?:string;value?:number|null}}|null|undefined;

const byKey=new Map<string,ReadinessScore>();
for(const row of snapshot.rows){
 if(/^NCT[0-9]{8}$/.test(row.nct)&&[1,2,3].includes(row.level)&&
  row.applicable>0&&row.sourceVerified>=0&&row.sourceVerified<=row.applicable&&
  row.applicable===row.checkCount-row.notYetExpected&&row.unresolved>=0&&
  row.evidenceReadinessScore===Math.round(100*row.sourceVerified/row.applicable)){
   byKey.set(row.nct+':'+row.level,row);
 }
}
export const FOCUS_READINESS_METHOD=
 'Provisional SOURCE_VERIFIED documentation checks ÷ applicable checks × 100, rounded; '+
 'NOT_YET_EXPECTED excluded. This does not measure efficacy, safety, '+
 'clinical success, FDA approval direction or probability.';
export const FOCUS_READINESS_SNAPSHOT=snapshot;

export function provisionalFocusScore(nct:string,level:number,report?:ScientificSlot):ReadinessScore|null{
 if(snapshot.kind!=='FOCUS_PROVISIONAL_SOURCE_EVIDENCE_READINESS_NOT_FDA_FORECAST'||
   snapshot.noApprovalProbabilities!==true||snapshot.noValidatedScientificScore!==true||
   snapshot.trials!==32||snapshot.reports!==96||byKey.size!==96)return null;
 if(!report||report.nct!==nct||report.level!==level||report.mode!=='CURRENT_EVIDENCE'||
  report.score?.kind!=='NOT_VALIDATED'||report.score?.value!==null||
  report.engineVersion!==snapshot.researchVersion+'/level-'+level)return null;
 const row=byKey.get(nct+':'+level);
 if(!row||row.runId!==report.runId||row.executedAt!==report.executedAt)return null;
 return row;
}


/**
 * Combined cross-sectional documentary readiness for all three saved research
 * levels. Pooling the verified/applicable check COUNTS (not averaging level
 * percentages) gives each explicitly applicable question equal weight.
 *
 * This is NOT a calibrated approval probability, a scientific efficacy score,
 * the unfinished 20-dimension rubric, or a directional FDA forecast.
 */
export type OverallEvidenceReadiness={
 evidenceReadinessScore:number;sourceVerified:number;applicable:number;
 unresolved:number;levelScores:[ReadinessScore,ReadinessScore,ReadinessScore];
};
export type FocusReadinessLevels=Record<string,{report?:ScientificSlot}|null|undefined>;

export function provisionalFocusOverall(nct:string,levels?:FocusReadinessLevels):OverallEvidenceReadiness|null{
 if(!levels)return null;
 const a=provisionalFocusScore(nct,1,levels['1']?.report);
 const b=provisionalFocusScore(nct,2,levels['2']?.report);
 const c=provisionalFocusScore(nct,3,levels['3']?.report);
 if(!a||!b||!c)return null;
 const levelScores:[ReadinessScore,ReadinessScore,ReadinessScore]=[a,b,c];
 const sourceVerified=levelScores.reduce((sum,x)=>sum+x.sourceVerified,0);
 const applicable=levelScores.reduce((sum,x)=>sum+x.applicable,0);
 const unresolved=levelScores.reduce((sum,x)=>sum+x.unresolved,0);
 return applicable>0?{
   evidenceReadinessScore:Math.round(100*sourceVerified/applicable),
   sourceVerified,applicable,unresolved,levelScores
 }:null;
}
export const FOCUS_OVERALL_READINESS_METHOD=
 'Overall provisional evidence readiness = 100 × the sum of strictly SOURCE_VERIFIED checks across L1–L3 ÷ '+
 'the sum of applicable checks across L1–L3, rounded. Excludes NOT_YET_EXPECTED. '+
 'Not a weighted clinical score, FDA approval prediction, scientific validation, or an average of level percentages.';

export function focusSavedDirection(nct:string,levels?:FocusReadinessLevels):'ABSTAIN'|'NOT AVAILABLE'{
 // Never infer a directional FDA call or numeric confidence from evidence readiness.
 // Only show the existing saved abstention when all three original report
 // identities and versioned source scores still match.
 if(!provisionalFocusOverall(nct,levels))return 'NOT AVAILABLE';
 return [1,2,3].every(l=>{
  const report=levels?.[String(l)]?.report;
  return report&&report.nct===nct&&report.level===l&&report.mode==='CURRENT_EVIDENCE'&&
   (report as {fdaPrediction?:{outcome?:string}}).fdaPrediction?.outcome==='ABSTAIN';
 })?'ABSTAIN':'NOT AVAILABLE';
}
