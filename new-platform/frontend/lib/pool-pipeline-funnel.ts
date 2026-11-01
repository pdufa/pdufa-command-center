/**
 * Read-only POOL → post-Phase 3 PIPELINE reconciliation.
 *
 * The POOL is the existing published workspace inventory and is NEVER reduced
 * by PIPELINE restrictions. A historical Phase 3 source row is only matched
 * to the POOL by exact NCT AND ticker; company cap pointers are dated, not live.
 * Pending checks must NOT be represented as eligible, approved or trade-ready.
 */
import { parsePhase3CensusCsv, type Phase3CensusRows, type Phase3CensusTrial } from "./phase3-census-rows";
import { parsePhase3CensusSourceDirectory, sourcesForPhase3Trial, type Phase3CensusSourceDirectory } from "./phase3-census-sources";
import { exactProgramTimeline, type TimelineDates, type TimelineSourceFields } from "./pipeline-timeline";

export type PoolTrialRecord = TimelineSourceFields & {
  id:string; ticker:string; company?:string; drug?:string; indication?:string;
  nctId?:string; stage?:string; marketCap?:number|null; capInRange?:boolean;
  capChecked?:string; capSource?:string; phase3Date?:string; phase3Source?:string;
};
export type PoolSnapshot = {
  pipeline:PoolTrialRecord[]; asOf?:string;
  sourceHealth?:{state?:string;clinicalRows?:number;regulatoryRows?:number;
    pipelineSourceParity?:{exactPrograms?:number};
    // Legacy Render branch still returns this retired *metadata key*; it is not
    // a GEM/Streamlit membership or an active filtering dependency.
    streamlitPipelineParity?:{exactPrograms?:number}};
};
export type PostPhase3Review = {
  nctId:string; ticker:string; company:string; drug:string|null; indication:string|null;
  sourceUrl:string; censusStatus:string; capUsd:number; capAsOf:string;
  poolStatus:"EXACT_MATCH"|"UNLINKED"|"TICKER_CONFLICT";
  postPhase3Evidence:"REGISTRY_COMPLETED"|"FINAL_READOUT_NEEDS_PROOF";
  qualification:"NEEDS_REVIEW";
  reasons:string[];
  timeline:TimelineDates;
};
export type FunnelResult = {
  poolRows:PoolTrialRecord[];
  reviewRows:PostPhase3Review[];
  overview:{
    poolRecords:number; poolClinicalRecords:number|null; poolRegulatoryRecords:number|null;
    poolAsOf:string|null; poolSourceState:string;
    historicalPhase3Records:741; historicalCompletedRecords:375;
    matchedPhase3Records:number; matchedCompletedRecords:number;
    missingOrConflicted:number; noncompletedReadoutReview:number;
    qualifiedPrograms:null; censusAsOf:string;
    definition:"POOL_SOURCE_RECORDS_VS_PHASE3_HISTORICAL_RESEARCH";
  };
};

const NCT=/^NCT\d{8}$/;
const exactNct=(row:PoolTrialRecord):string|null=>{
  const nct=row.nctId || (row.id.startsWith("TRIAL|")?row.id.slice(6):"");
  return NCT.test(nct)?nct:null;
};
function validPool(value:unknown):value is PoolSnapshot {
  if(!value || typeof value!=="object")return false;
  const v=value as Partial<PoolSnapshot>;
  const rows=v.pipeline;
  const health=v.sourceHealth;
  // The independently deployed Render backend may still use the original
  // source-parity metadata name; check either representation without altering
  // source records or qualifying anyone for the restricted Pipeline.
  const parity=health?.pipelineSourceParity||health?.streamlitPipelineParity;
  if(!Array.isArray(rows) || !health
      || typeof health.state!=="string"
      || health.state==="STALE"
      || !parity
      || parity.exactPrograms!==rows.length
      || !Number.isSafeInteger(health.clinicalRows)
      || !Number.isSafeInteger(health.regulatoryRows)
      || health.clinicalRows! + health.regulatoryRows! !== rows.length
      || rows.some(r=>!r || typeof r.id!=="string" || !r.id
        // Unrestricted POOL must retain unresolved issuer/ticker records.
        // Missing ticker is a review item, never an eligibility pass.
        || typeof r.ticker!=="string")) return false;
  return new Set(rows.map(r=>r.id)).size===rows.length;
}
export function reconcilePoolPipeline(raw:unknown,csvText:string,sourceInput:unknown):FunnelResult {
  if(!validPool(raw)) throw new Error("Published master POOL integrity or freshness unavailable");
  const snapshot=raw as PoolSnapshot;
  const census:Phase3CensusRows=parsePhase3CensusCsv(csvText);
  const directory:Phase3CensusSourceDirectory=parsePhase3CensusSourceDirectory(sourceInput,census);
  const exact=new Map<string,PoolTrialRecord>();
  const conflicts=new Set<string>();
  for(const row of snapshot.pipeline){
    const nct=exactNct(row);
    if(!nct)continue;
    if(row.id!=="TRIAL|"+nct)continue;
    if(exact.has(nct)){conflicts.add(nct);continue;}
    exact.set(nct,row);
  }
  let completed=0,matched=0,matchedCompleted=0,missing=0;
  const reviewRows=census.rows.map((trial:Phase3CensusTrial):PostPhase3Review=>{
    const sponsor=sourcesForPhase3Trial(trial,directory);
    const pool=exact.get(trial.nctId);
    const poolStatus:PostPhase3Review["poolStatus"]=
      !pool?"UNLINKED":pool.ticker!==trial.ticker||conflicts.has(trial.nctId)?"TICKER_CONFLICT":"EXACT_MATCH";
    const isCompleted=trial.status==="COMPLETED";
    if(isCompleted)completed++;
    if(poolStatus==="EXACT_MATCH"){matched++;if(isCompleted)matchedCompleted++;}
    else missing++;
    const reasons:string[]=[];
    if(poolStatus!=="EXACT_MATCH")reasons.push("Exact NCT / ticker reconciliation with master POOL not established");
    if(!isCompleted)reasons.push("Not registry completed; verify a final pivotal Phase 3 readout before eligibility");
    reasons.push("Recheck current public listing and market capitalization; the $300M–$10B census is dated");
    reasons.push("Verify sponsor commercial rights and canonical drug–indication program");
    reasons.push("Do not infer efficacy success, NDA/BLA acceptance or a PDUFA date");
    return {
      nctId:trial.nctId,ticker:trial.ticker,company:trial.company,
      drug:poolStatus==="EXACT_MATCH"?(pool?.drug||null):null,
      indication:poolStatus==="EXACT_MATCH"?(pool?.indication||null):null,
      sourceUrl:trial.sourceUrl,censusStatus:trial.status,
      capUsd:sponsor.marketCapUsd,capAsOf:sponsor.marketCapCheckedAt,
      poolStatus,
      timeline:exactProgramTimeline(pool,poolStatus==="EXACT_MATCH"),
      postPhase3Evidence:isCompleted?"REGISTRY_COMPLETED":"FINAL_READOUT_NEEDS_PROOF",
      qualification:"NEEDS_REVIEW",reasons,
    };
  });
  if(completed!==375)throw new Error("Historical completed trial count drifted");
  return {
    poolRows:snapshot.pipeline,
    reviewRows,
    overview:{
      poolRecords:snapshot.pipeline.length,
      poolClinicalRecords:snapshot.sourceHealth?.clinicalRows??null,
      poolRegulatoryRecords:snapshot.sourceHealth?.regulatoryRows??null,
      poolAsOf:snapshot.asOf||null,
      poolSourceState:snapshot.sourceHealth?.state||"UNKNOWN",
      historicalPhase3Records:741,historicalCompletedRecords:375,
      matchedPhase3Records:matched,matchedCompletedRecords:matchedCompleted,
      missingOrConflicted:missing,noncompletedReadoutReview:741-375,
      qualifiedPrograms:null,censusAsOf:directory.censusAsOf,
      definition:"POOL_SOURCE_RECORDS_VS_PHASE3_HISTORICAL_RESEARCH",
    },
  };
}
export const POOL_STAGE_GROUPS = {
  early:["Early Phase 1","Phase 1","Phase 1/2","Phase 2","Phase 2/3"],
  phase3:["Phase 3","Phase 3 Results"],
  regulatory:["NDA/BLA Submission","FDA Acceptance","PDUFA Decision","Post-Decision","Phase 4"],
  other:["Not Applicable","Unknown"],
} as const;
export type PoolStageGroup="all"|keyof typeof POOL_STAGE_GROUPS;
export const POOL_STAGES=Object.values(POOL_STAGE_GROUPS).flat();
export function normalizePoolStage(raw?:string):string {
  return POOL_STAGES.includes(raw as typeof POOL_STAGES[number]) ? raw! : "Unknown";
}
export function poolStageBucket(raw?:string):keyof typeof POOL_STAGE_GROUPS {
  const stage=normalizePoolStage(raw);
  for(const group of Object.keys(POOL_STAGE_GROUPS) as Array<keyof typeof POOL_STAGE_GROUPS>){
    if((POOL_STAGE_GROUPS[group] as readonly string[]).includes(stage))return group;
  }
  return "other";
}
export function poolStageStatistics(rows:PoolTrialRecord[]){
  const groups:{early:number;phase3:number;regulatory:number;other:number}={early:0,phase3:0,regulatory:0,other:0};
  const stages:Record<string,number>={};
  for(const row of rows){
    const stage=normalizePoolStage(row.stage);
    stages[stage]=(stages[stage]||0)+1;
    groups[poolStageBucket(stage)]++;
  }
  return {total:rows.length,groups,stages};
}
export type ScopeView="pool"|"pipeline"|"readout-review"|"census-review";
export function funnelPage(funnel:FunnelResult,view:ScopeView,offset:number,limit:number,query:string,stageGroup:PoolStageGroup="all",stageFilter:string="") {
  const q=query.trim().toLowerCase();
  const matches=(item:PoolTrialRecord|PostPhase3Review)=>[
    item.ticker,item.company,item.drug,item.indication,
    "nctId" in item?item.nctId:null,"id" in item?item.id:null,
  ].some(value=>(value||"").toLowerCase().includes(q));
  const rows=view==="pool"?funnel.poolRows:view==="census-review"?funnel.reviewRows:view==="pipeline"?
    funnel.reviewRows.filter(r=>r.postPhase3Evidence==="REGISTRY_COMPLETED"&&r.poolStatus==="EXACT_MATCH"):
    funnel.reviewRows.filter(r=>r.postPhase3Evidence!=="REGISTRY_COMPLETED"||r.poolStatus!=="EXACT_MATCH");
  const searched=q?rows.filter(matches):rows;
  const stageStats=view==="pool"?poolStageStatistics(funnel.poolRows):undefined;
  const stageFiltered=view==="pool"
    ? searched.filter(row=>{
        const pool=row as PoolTrialRecord;
        if(stageGroup!=="all" && poolStageBucket(pool.stage)!==stageGroup)return false;
        return !stageFilter || normalizePoolStage(pool.stage)===stageFilter;
      })
    :searched;
  return {view,overview:funnel.overview,stageStats,stageGroup,stageFilter,total:stageFiltered.length,offset,limit,
    rows:stageFiltered.slice(offset,offset+limit),
    nextOffset:offset+limit<stageFiltered.length?offset+limit:null,
    qualifiedProgramCount:null,
    caveat:"Research reconciliation only; no independently verified current $300M–$10B post-Phase 3 program count. All historical candidates remain NEEDS REVIEW."};
}
