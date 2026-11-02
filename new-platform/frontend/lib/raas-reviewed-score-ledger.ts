/** Approved calibration registry and immutable dated RAAS snapshot ledger.
 * A measurement, exploratory grade, or user-entered opinion is NOT an approved RAAS rating.
 */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {computeRaasScore,type MetricRating,type RiskGate,type RaasResult,type Snapshot} from "./raas-score-engine";
export type CalibrationApproval={
 metricId:string;stage:RaasStage;benchmarkId:string;ruleVersion:string;
 validatedAt:string;validationSourceUrl:string;outOfSampleTrials:number;
 benchmarkDescription:string;scoreThresholds:{grade:0|25|50|75|100;rule:string}[];
 status:"APPROVED_FOR_COMPOSITE";
};
export type CalibrationRegistry={
 schemaVersion:1;scope:"RAAS_VALIDATED_METRIC_CALIBRATIONS";sourceAsOf:string;
 note:string;entries:CalibrationApproval[];
};
export type RaasReviewedSnapshot={
 nctId:string;ticker:string;drug:string;indication:string;stage:RaasStage;
 snapshot:Snapshot;asOf:string;reviewedAt:string;reviewer:string;
 ratings:MetricRating[];gates:RiskGate[];note:string;
};
export type RaasReviewedLedger={
 schemaVersion:1;scope:"RAAS_REVIEWED_TRIAL_SNAPSHOTS";sourceAsOf:string;
 note:string;records:RaasReviewedSnapshot[];
};
const day=(s:string):boolean=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 Number.isFinite(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const url=(s:string):boolean=>/^https:\/\/[^\s/]+\/\S+/.test(s);
const key=(r:{nctId:string;ticker:string;drug:string;indication:string;stage:RaasStage})=>
 [r.nctId,r.ticker,r.drug,r.indication,r.stage].map(s=>s.trim().toLowerCase()).join("|");
const allIds=(stage:RaasStage)=>new Set(RAAS_METRIC_CATALOG[stage].flatMap(g=>g.metrics.map(m=>m.id)));
export function parseRaasCalibrations(input:unknown):CalibrationRegistry{
 if(!input||typeof input!=="object")throw Error("RAAS_CALIBRATIONS_INVALID");
 const feed=input as CalibrationRegistry;
 if(feed.schemaVersion!==1||feed.scope!=="RAAS_VALIDATED_METRIC_CALIBRATIONS"||
    !day(feed.sourceAsOf)||!Array.isArray(feed.entries)||feed.entries.length>100)
    throw Error("RAAS_CALIBRATIONS_INVALID");
 const seen=new Set<string>();
 for(const r of feed.entries){
  if(!r||!(r.stage==="pre"||r.stage==="post")||!allIds(r.stage).has(r.metricId)||
    !r.benchmarkId?.trim()||!r.ruleVersion?.trim()||!r.benchmarkDescription?.trim()||
    !day(r.validatedAt)||r.validatedAt>feed.sourceAsOf||!url(r.validationSourceUrl)||
    !Number.isInteger(r.outOfSampleTrials)||r.outOfSampleTrials<30||
    r.status!=="APPROVED_FOR_COMPOSITE"||
    !Array.isArray(r.scoreThresholds)||r.scoreThresholds.length!==5||
    ![0,25,50,75,100].every(grade=>r.scoreThresholds.some(x=>x?.grade===grade&&x.rule?.trim())))
    throw Error("RAAS_CALIBRATION_NOT_VALIDATED");
  const id=r.stage+"|"+r.metricId;if(seen.has(id))throw Error("RAAS_CALIBRATION_DUPLICATED");
  seen.add(id);
 }
 return feed;
}
export function parseRaasReviewedLedger(input:unknown):RaasReviewedLedger{
 if(!input||typeof input!=="object")throw Error("RAAS_LEDGER_INVALID");
 const feed=input as RaasReviewedLedger;
 if(feed.schemaVersion!==1||feed.scope!=="RAAS_REVIEWED_TRIAL_SNAPSHOTS"||
    !day(feed.sourceAsOf)||!Array.isArray(feed.records)||feed.records.length>10000)
    throw Error("RAAS_LEDGER_INVALID");
 const seen=new Set<string>();
 for(const r of feed.records){
  if(!r||!/^NCT\d{8}$/.test(r.nctId)||!r.ticker?.trim()||
    !r.drug?.trim()||!r.indication?.trim()||
    (r.stage!=="pre"&&r.stage!=="post")||
    !["ENTRY","CURRENT","EXIT"].includes(r.snapshot)||
    !day(r.asOf)||!day(r.reviewedAt)||r.asOf>feed.sourceAsOf||
    r.reviewedAt<r.asOf||r.reviewedAt>feed.sourceAsOf||
    !r.reviewer?.trim()||!r.note?.trim()||
    !Array.isArray(r.ratings)||!Array.isArray(r.gates)||
    r.ratings.some(item=>!item||item.nctId!==r.nctId||item.ticker.trim().toLowerCase()!==r.ticker.trim().toLowerCase()||
      item.stage!==r.stage||item.snapshot!==r.snapshot||!allIds(r.stage).has(item.metricId)))
    throw Error("RAAS_SNAPSHOT_INVALID");
  const id=key(r)+"|"+r.snapshot+"|"+r.asOf;
  if(seen.has(id))throw Error("RAAS_SNAPSHOT_DUPLICATED");
  seen.add(id);
 }
 return feed;
}
export function reviewedScoreForTrial(
 ledger:RaasReviewedLedger,registry:CalibrationRegistry,
 trial:{nctId:string;ticker:string;drug:string;indication:string},
 stage:RaasStage,snapshot:Snapshot,asOf:string
):{record:RaasReviewedSnapshot;score:RaasResult;acceptedRatings:MetricRating[];excludedRatings:number}|null{
 if(!day(asOf)||asOf>ledger.sourceAsOf||asOf>registry.sourceAsOf)return null;
 const trialKey=key({...trial,stage});
 const matching=ledger.records.filter(r=>key(r)===trialKey&&r.snapshot===snapshot&&r.asOf<=asOf);
 if(!matching.length)return null;
 matching.sort((a,b)=>b.asOf.localeCompare(a.asOf));
 const record=matching[0];
 const approved=new Map(registry.entries.filter(c=>c.stage===stage&&c.validatedAt<=record.asOf)
   .map(c=>[c.metricId,c]));
 // Reject a rating that lacks the EXACT approved benchmark and pre-readout validation.
 const accepted=record.ratings.filter(r=>{
  const cal=approved.get(r.metricId);
  return !!cal&&cal.benchmarkId===r.benchmarkId&&cal.validatedAt<=r.assessedAt;
 });
 const grade=computeRaasScore({stage,snapshot,asOf:record.asOf,
  trial:{nctId:trial.nctId,ticker:trial.ticker},ratings:accepted,gates:record.gates});
 return {record,score:grade,acceptedRatings:accepted,
  excludedRatings:record.ratings.length-accepted.length};
}
