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
