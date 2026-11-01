/**
 * Dedicated, read-only TOOLS POOL inventory. It does not depend on the
 * historical 741-trial Phase 3 census used by the separate PIPELINE view.
 * All NCT counts come from the published Render POOL snapshot.
 */
import {
  isPoolTrial,normalizePoolStage,poolStageStatistics,
  type PoolSnapshot,type PoolTrialRecord
} from "./pool-pipeline-funnel";
import {
  SPECIAL_DESIGNATION_CATEGORIES,
  type DesignationIndex,type DesignationKey
} from "./trial-designations";
import {toolSpreadsheetRow,renderToolsSpreadsheetCsv} from "./tools-spreadsheet";

export function verifiedToolPool(raw:unknown):{
  poolRows:PoolTrialRecord[];
  sourceAsOf:string;
  sourceState:string;
  stageStats:ReturnType<typeof poolStageStatistics>;
}{
  if(!raw||typeof raw!=="object")throw Error("POOL_INVALID_RESPONSE");
  const snapshot=raw as Partial<PoolSnapshot>;
  const rows=snapshot.pipeline;
  const health=snapshot.sourceHealth;
  if(!Array.isArray(rows)||!health)throw Error("POOL_INVALID_RESPONSE");
  if(health.state==="STALE")throw Error("POOL_SOURCE_STALE");
  const parity=health.pipelineSourceParity||health.streamlitPipelineParity;
  if(!parity||!Number.isSafeInteger(parity.exactPrograms)||
     parity.exactPrograms!==rows.length||
     !Number.isSafeInteger(health.clinicalRows)||
     !Number.isSafeInteger(health.regulatoryRows)||
     health.clinicalRows!+health.regulatoryRows!==rows.length||
     rows.some(row=>!row||typeof row.id!=="string"||typeof row.ticker!=="string"||
       typeof row.stage!=="string") ||
     new Set(rows.map(row=>row.id)).size!==rows.length){
    throw Error("POOL_SOURCE_PARITY_FAILED");
  }
  // PARTIAL may still have an internally consistent published inventory.
  // The returned state is shown prominently; it never certifies eligibility.
  return {
    poolRows:rows,stageStats:poolStageStatistics(rows),
    sourceAsOf:typeof snapshot.asOf==="string"?snapshot.asOf:"",
    sourceState:health.state||"UNKNOWN"
  };
}

export function selectToolTrialIds(
  rows:readonly PoolTrialRecord[], index:DesignationIndex, selected:readonly DesignationKey[]
):Set<string>{
  const found=new Set<string>();
  for(const trial of rows){
    if(!isPoolTrial(trial))continue;
    const nct=trial.id.slice(6);
    const linked=index.trialEvents[nct]||[];
    if(linked.some(id=>{
      const program=index.programs[id];
      if(!program||program.ticker!==trial.ticker.toUpperCase())return false;
      return selected.some(key=>{
        const ev=program.designations[key];
        return ev?.status==="GRANTED" && ev.verification!=="UNVERIFIED" && !!ev.source;
      });
    }))found.add(trial.id);
  }
  return found;
}

export function filterToolTrials(
  pool:readonly PoolTrialRecord[],stages:readonly string[],
  designationMatches:ReadonlySet<string>|null,query:string
):PoolTrialRecord[]{
  const q=query.trim().toLowerCase();
  return pool.filter(row=>{
    if(!isPoolTrial(row))return false;
    if(!stages.length && designationMatches===null)return false;
    if(stages.length&&!stages.includes(normalizePoolStage(row.stage)))return false;
    if(designationMatches!==null&&!designationMatches.has(row.id))return false;
    if(q && ![row.id,row.ticker,row.company,row.drug,row.indication]
      .some(v=>(v||"").toLowerCase().includes(q)))return false;
    return true;
  });
}

export function buildToolsResults(
  snapshot:ReturnType<typeof verifiedToolPool>,
  index:DesignationIndex|null,
  selectedStages:readonly string[],
  selectedDesignations:readonly DesignationKey[],
  query:string,offset:number,limit:number
){
  const {poolRows,stageStats,sourceAsOf,sourceState}=snapshot;
  const matchingIds=index?selectToolTrialIds(poolRows,index,selectedDesignations):null;
  const filtered=filterToolTrials(poolRows,selectedStages,matchingIds,query);
  const stageSelectors=selectedStages.map(label=>({
    label,trials:stageStats.stages[label]?.trials??0
  }));
  const designationSelectors=selectedDesignations.map(key=>({
    key,label:SPECIAL_DESIGNATION_CATEGORIES.find(v=>v.key===key)?.label||key,
    linkedTrials:index?selectToolTrialIds(poolRows,index,[key]).size:0
  }));
  const rows=filtered.slice(offset,offset+limit);
  return {
    view:"pool",offset,limit,total:filtered.length,
    nextOffset:offset+limit<filtered.length?offset+limit:null,
    rows,stageStats,
    overview:{
      poolRecords:stageStats.total,poolClinicalRecords:stageStats.trials,
      poolRegulatoryRecords:stageStats.regulatoryEvents+stageStats.standaloneResults,
      poolSourceState:sourceState,poolAsOf:sourceAsOf
    },
    spreadsheetRows:rows.map(row=>toolSpreadsheetRow(row,selectedStages,selectedDesignations,index)),
    selectionSummary:{
      selectedCount:selectedStages.length+selectedDesignations.length,
      stageSelectedCount:selectedStages.length,
      designationSelectedCount:selectedDesignations.length,
      stageTotal:stageSelectors.reduce((sum,v)=>sum+v.trials,0),
      designationCountSum:designationSelectors.reduce((sum,v)=>sum+v.linkedTrials,0),
      designationUniqueTrials:matchingIds?.size??null,
      matchingUniqueTrials:filtered.length,
      stageSelectors,designationSelectors
    },
    designationLinkage:index?{basis:"EXACT_NCT_AND_TICKER",sourceLinkedTrials:matchingIds?.size??0}:null,
    sourceIntegrity:"PARITY_VERIFIED",
    caveat:"Published POOL inventory only; source may be partial. No FDA approval or Pipeline qualification inferred."
  };
}
export {renderToolsSpreadsheetCsv};
