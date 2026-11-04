/** Trial-centred, stage-spanning append-only history. Stage is an event property,
 * NEVER part of the trial continuity key. TOP points are not reused as BOTTOM
 * numerical ratings; a score is always scoped to stage and model version.
 */
import type {RaasStage} from "./raas-metric-specs";
export type RaasHistoryScoreKind="UNSCORED"|"PROVISIONAL"|"VALIDATED";
export type RaasHistoryEventKind="FIRST_CAPTURE"|"EVIDENCE_UPDATED"|"STAGE_ADDED"|"SCORE_UPDATED";
export type RaasTrialHistoryEvent={
 readonly eventId:string;readonly nctId:string;readonly ticker:string;
 readonly drug:string;readonly indication:string;readonly stage:RaasStage;
 readonly recordedAt:string;readonly sourceAsOf:string;
 readonly kind:RaasHistoryEventKind;readonly summary:string;
 readonly scoreKind:RaasHistoryScoreKind;readonly score:number|null;
 readonly scoreVersion:string|null;readonly metricCoverage:number;
 readonly metricIds:readonly string[];readonly sourceUrls:readonly string[];
 readonly evidenceFingerprint:string;
};
export type RaasTrialHistoryLedger={
 readonly schemaVersion:1;readonly scope:"RAAS_TRIAL_SCORE_HISTORY";
 readonly note:string;readonly records:readonly RaasTrialHistoryEvent[];
};
const norm=(x:string)=>x.trim().replace(/\s+/g," ").toLowerCase();
const nct=(x:string)=>/^NCT\d{8}$/.test(x);
const iso=(x:string)=>/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(x)&&
 !Number.isNaN(Date.parse(x))&&new Date(x).toISOString()===x;
const day=(x:string)=>/^\d{4}-\d{2}-\d{2}$/.test(x)&&
 !Number.isNaN(Date.parse(x+"T00:00:00Z"))&&new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;
const validUrl=(x:string)=>/^https:\/\/[^\s/]+\/\S*/.test(x);
const idKey=(x:{nctId:string;drug:string;indication:string})=>
 [x.nctId,norm(x.drug),norm(x.indication)].join("|");
export function parseRaasTrialHistory(input:unknown):RaasTrialHistoryLedger{
 if(!input||typeof input!=="object")throw Error("RAAS_HISTORY_INVALID");
 const d=input as RaasTrialHistoryLedger;
 if(d.schemaVersion!==1||d.scope!=="RAAS_TRIAL_SCORE_HISTORY"||
  typeof d.note!=="string"||!Array.isArray(d.records)||d.records.length>200000)
  throw Error("RAAS_HISTORY_INVALID");
 const ids=new Set<string>();let prev="";
 for(const r of d.records){
  if(!r||!r.eventId||ids.has(r.eventId)||!nct(r.nctId)||!r.ticker?.trim()||
     !r.drug?.trim()||!r.indication?.trim()||
     (r.stage!=="pre"&&r.stage!=="post")||!iso(r.recordedAt)||!day(r.sourceAsOf)||
     r.sourceAsOf>r.recordedAt.slice(0,10)||r.recordedAt<prev||
     !["FIRST_CAPTURE","EVIDENCE_UPDATED","STAGE_ADDED","SCORE_UPDATED"].includes(r.kind)||
     !r.summary?.trim()||
     !["UNSCORED","PROVISIONAL","VALIDATED"].includes(r.scoreKind)||
     (r.scoreKind==="UNSCORED"?(r.score!==null||r.scoreVersion!==null):
       !(typeof r.score==="number"&&Number.isFinite(r.score)&&r.score>=0&&r.score<=100&&
        r.scoreVersion?.trim()))||
     !Number.isInteger(r.metricCoverage)||r.metricCoverage<0||r.metricCoverage>30||
     !Array.isArray(r.metricIds)||r.metricIds.length!==r.metricCoverage||
     new Set(r.metricIds).size!==r.metricIds.length||
     r.metricIds.some(x=>typeof x!=="string"||!x.startsWith(r.stage==="pre"?"pre-":"post-"))||
     !Array.isArray(r.sourceUrls)||r.sourceUrls.length>100||
     r.sourceUrls.some(x=>typeof x!=="string"||!validUrl(x))||
     !/^[a-f0-9]{64}$/.test(r.evidenceFingerprint))
    throw Error("RAAS_HISTORY_EVENT_INVALID:"+r?.eventId);
  ids.add(r.eventId);prev=r.recordedAt;
 }
 return d;
}
/** Matching by NCT with exact drug and indication when supplied. A ticker rename
 * can retain the same NCT+therapy, but a different compound NEVER inherits it.
 * Incomplete identity is admitted only for one unambiguous clinical program.
 */
export function historyForTrial(
 ledger:RaasTrialHistoryLedger,
 trial:{nctId:string;ticker:string;drug?:string;indication?:string}
):RaasTrialHistoryEvent[]{
 if(!nct(trial.nctId)||!trial.ticker?.trim())return [];
 const byNct=ledger.records.filter(e=>e.nctId===trial.nctId);
 const drugs=norm(trial.drug||""),ind=norm(trial.indication||"");
 const matched=byNct.filter(e=>(!drugs||norm(e.drug)===drugs)&&
   (!ind||norm(e.indication)===ind));
 const programs=new Set(matched.map(idKey));
 if(programs.size!==1)return [];
 // A wholly unspecified compound/indication may only match a known issuer;
 // do not accidentally merge same NCT transferred among unrelated sponsors.
 if(!drugs&&!ind&&!matched.some(e=>norm(e.ticker)===norm(trial.ticker)))return [];
 return [...matched].sort((a,b)=>a.recordedAt.localeCompare(b.recordedAt)||
   a.eventId.localeCompare(b.eventId));
}
export function currentHistoryScore(
 history:readonly RaasTrialHistoryEvent[],stage:RaasStage
):RaasTrialHistoryEvent|null{
 return [...history].reverse().find(e=>e.stage===stage&&e.score!==null)??null;
}
/** Never compute a delta across pre/post, approval states, or scoring versions. */
export function comparableScoreDelta(
 history:readonly RaasTrialHistoryEvent[],selected:RaasTrialHistoryEvent
):number|null{
 if(selected.score===null)return null;
 const p=[...history].filter(e=>e.recordedAt<selected.recordedAt||
   (e.recordedAt===selected.recordedAt&&e.eventId!==selected.eventId));
 const before=p.reverse().find(e=>e.stage===selected.stage&&
   e.scoreKind===selected.scoreKind&&e.scoreVersion===selected.scoreVersion&&e.score!==null);
 return before?.score===undefined||before.score===null?null:selected.score-before.score;
}
