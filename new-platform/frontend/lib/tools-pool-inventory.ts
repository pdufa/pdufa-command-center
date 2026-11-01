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
     health.clinicalRows!+health.regulatoryRows! !==rows.length||
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

/**
 * Exactly the same NCT + ticker + cited-positive matching used by the TOOLS
 * spreadsheet, independently for every FDA designation. Raw index.trialEvents
 * is NOT a POOL trial count: it can include unlisted or mismatched candidates.
 * A null entry means the source field is unavailable, never zero NCT trials.
 */
export type ToolsDesignationTotal={
  linkedNcts:number;
  nctIds:string[];
  /** POOL-reconciled NCT links, keyed by FDA program event. */
  programNctIds:Record<string,string[]>;
};
export type ToolsDesignationTotals=Record<DesignationKey,ToolsDesignationTotal|null>;
export function toolsDesignationTotals(
  poolRows:readonly PoolTrialRecord[],index:DesignationIndex
):ToolsDesignationTotals{
  return Object.fromEntries(SPECIAL_DESIGNATION_CATEGORIES.map(({key})=>{
    if(!index.availableKeys?.[key])return [key,null];
    const matches=selectToolTrialIds(poolRows,index,[key]);
    const ncts=[...matches].map(id=>id.slice("TRIAL|".length)).sort();
    const byProgram:Record<string,string[]>=Object.create(null);
    for(const trial of poolRows){
      if(!isPoolTrial(trial)||!matches.has(trial.id))continue;
      const nct=trial.id.slice("TRIAL|".length);
      for(const eventKey of index.trialEvents[nct]||[]){
        const program=index.programs[eventKey];
        const evidence=program?.designations[key];
        if(!program||program.ticker!==trial.ticker.toUpperCase()||
           evidence?.status!=="GRANTED"||evidence.verification==="UNVERIFIED"||!evidence.source)continue;
        (byProgram[eventKey]??=[]).push(nct);
      }
    }
    return [key,{linkedNcts:matches.size,nctIds:ncts.slice(0,40),programNctIds:byProgram}];
  })) as ToolsDesignationTotals;
}

/**
 * Faceted FDA trial counts in the exact resultant Phase/search scope.
 * Each choice is evaluated independently, because FDA choices are ORed.
 * Counts are from the full verified POOL, NEVER the 50-row visible page,
 * and use the same exact NCT+ticker cited-GRANTED matching as result filtering.
 * null means no count is established, rather than an invented zero.
 */
export type ToolsContextualDesignationCount={
  matchingTrials:number;
  nctIds:string[];
};
export type ToolsContextualDesignationCounts=Record<DesignationKey,ToolsContextualDesignationCount|null>;
export function toolsContextualDesignationCounts(
  poolRows:readonly PoolTrialRecord[],index:DesignationIndex|null,
  stages:readonly string[],query:string
):ToolsContextualDesignationCounts{
  return Object.fromEntries(SPECIAL_DESIGNATION_CATEGORIES.map(({key})=>{
    if(!index?.availableKeys?.[key])return [key,null];
    const ids=selectToolTrialIds(poolRows,index,[key]);
    // A source with no exact-NCT positives has incomplete coverage:
    // 'unknown', not 'zero trials'. When a known designation has links
    // outside the chosen phase, an observed intersection of 0 IS valid.
    if(ids.size===0)return [key,null];
    const filtered=filterToolTrials(poolRows,stages,ids,query);
    return [key,{matchingTrials:filtered.length,
      nctIds:filtered.slice(0,40).map(row=>row.id.slice("TRIAL|".length))}];
  })) as ToolsContextualDesignationCounts;
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

export type ToolsDesignationProgramRow={
  eventKey:string;ticker:string;drug:string;indication:string;
  designations:{key:DesignationKey;label:string;source:string}[];
  linkedNcts:string[];
};

/** Regulatory program events and trial IDs are different units.
 * Report both, and never infer a stage for a program missing an NCT crosswalk. */
export function designationSourceCoverage(
  poolRows:readonly PoolTrialRecord[],index:DesignationIndex,
  selected:readonly DesignationKey[]
):{
  sourcePrograms:number;linkedPrograms:number;unlinkedPrograms:number;
  linkedNcts:number;noVerifiedNctLinks:boolean;
  programRows:ToolsDesignationProgramRow[];
}{
  const positives=new Map<string,ToolsDesignationProgramRow>();
  for(const program of Object.values(index.programs)){
    const designations=selected.flatMap(key=>{
      const claim=program.designations[key];
      if(claim?.status!=="GRANTED"||claim.verification==="UNVERIFIED"||!claim.source)return [];
      return [{key,label:SPECIAL_DESIGNATION_CATEGORIES.find(c=>c.key===key)?.label||key,source:claim.source}];
    });
    if(designations.length)positives.set(program.eventKey,{
      eventKey:program.eventKey,ticker:program.ticker,drug:program.drug,
      indication:program.indication,designations,linkedNcts:[]
    });
  }
  const linkedTrialIds=new Set<string>();
  for(const row of poolRows){
    if(!isPoolTrial(row))continue;
    const nct=row.id.slice(6);
    for(const key of index.trialEvents[nct]||[]){
      const p=positives.get(key);
      if(!p||p.ticker!==row.ticker.toUpperCase())continue;
      if(!p.linkedNcts.includes(nct))p.linkedNcts.push(nct);
      linkedTrialIds.add(nct);
    }
  }
  const programRows=[...positives.values()].sort((a,b)=>a.ticker.localeCompare(b.ticker)||a.eventKey.localeCompare(b.eventKey));
  const linkedPrograms=programRows.filter(r=>r.linkedNcts.length>0).length;
  return {
    sourcePrograms:programRows.length,linkedPrograms,
    unlinkedPrograms:programRows.length-linkedPrograms,
    linkedNcts:linkedTrialIds.size,
    noVerifiedNctLinks:programRows.length>0 && linkedTrialIds.size===0,
    programRows
  };
}

export function buildToolsResults(
  snapshot:ReturnType<typeof verifiedToolPool>,
  index:DesignationIndex|null,
  selectedStages:readonly string[],
  selectedDesignations:readonly DesignationKey[],
  query:string,offset:number,limit:number
){
  const {poolRows,stageStats,sourceAsOf,sourceState}=snapshot;
  if(selectedDesignations.length>0&&!index)throw Error("FDA_DESIGNATION_EVIDENCE_UNAVAILABLE");
  const matchingIds=index?selectToolTrialIds(poolRows,index,selectedDesignations):null;
  const designationCoverage=index&&selectedDesignations.length>0
    ?designationSourceCoverage(poolRows,index,selectedDesignations):null;
  // TOOLS selects from the complete published clinical POOL. The independent
  // $300M–$10B post–Phase 3 Pipeline screen is informational, NEVER a filter.
  // AND applies between stage and documented NCT-linked designation criteria.
  const filtered=filterToolTrials(poolRows,selectedStages,matchingIds,query);
  const stageSelectors=selectedStages.map(label=>({
    label,trials:stageStats.stages[label]?.trials??0
  }));
  const designationSelectors=selectedDesignations.map(key=>({
    key,label:SPECIAL_DESIGNATION_CATEGORIES.find(v=>v.key===key)?.label||key,
    linkedTrials:index?filterToolTrials(poolRows,selectedStages,
      selectToolTrialIds(poolRows,index,[key]),query).length:0
  }));
  const rows=filtered.slice(offset,offset+limit);
  return {
    view:"pool",offset,limit,total:filtered.length,
    nextOffset:offset+limit<filtered.length?offset+limit:null,
    rows,stageStats,
    designationCoverage,
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
      sourceProgramRecords:designationCoverage?.sourcePrograms??0,
      unlinkedSourceProgramRecords:designationCoverage?.unlinkedPrograms??0,
      noVerifiedNctLinks:designationCoverage?.noVerifiedNctLinks??false,
      stageSelectors,designationSelectors
    },
    designationLinkage:index?{basis:"EXACT_NCT_AND_TICKER",sourceLinkedTrials:matchingIds?.size??0}:null,
    sourceIntegrity:"PARITY_VERIFIED",
    caveat:"Published POOL inventory only; source may be partial. No FDA approval or Pipeline qualification inferred."
  };
}

/**
 * Opening TOOLS inventory is an explicit read-only view of the published POOL.
 * It is NOT a filter result: legacy calls with no checked filters still return
 * zero. Preserve source identities and never attach unreviewed FDA designations.
 */
export function buildToolsOpeningInventory(
  snapshot:ReturnType<typeof verifiedToolPool>,offset:number,limit:number
){
  const all=snapshot.poolRows.filter(isPoolTrial);
  const rows=all.slice(offset,offset+limit);
  return {
    view:"pool",inventoryMode:true,offset,limit,total:all.length,
    nextOffset:offset+limit<all.length?offset+limit:null,
    rows,stageStats:snapshot.stageStats,
    designationCoverage:null,
    overview:{
      poolRecords:snapshot.stageStats.total,
      poolClinicalRecords:snapshot.stageStats.trials,
      poolRegulatoryRecords:snapshot.stageStats.regulatoryEvents+snapshot.stageStats.standaloneResults,
      poolSourceState:snapshot.sourceState,poolAsOf:snapshot.sourceAsOf
    },
    spreadsheetRows:rows.map(row=>toolSpreadsheetRow(row,[],[],null)),
    selectionSummary:{
      selectedCount:0,stageSelectedCount:0,designationSelectedCount:0,
      stageTotal:0,designationCountSum:0,designationUniqueTrials:null,
      matchingUniqueTrials:all.length,sourceProgramRecords:0,unlinkedSourceProgramRecords:0,
      noVerifiedNctLinks:false,stageSelectors:[],designationSelectors:[]
    },
    designationLinkage:null,sourceIntegrity:"PARITY_VERIFIED",
    caveat:"Unfiltered published NCT inventory only; not a checked filter result, FDA-designation match or Pipeline qualification."
  };
}

/** Program records without verified NCT joins must never be exported as clinical trials. */
export function renderUnlinkedFdaProgramCsv(
  coverage:ReturnType<typeof designationSourceCoverage>,sourceAsOf:string
):string{
  const cell=(value:string)=>{
    const clean=value.replace(/[\r\n\t]+/g," ").trim();
    const safe=/^[=+\-@]/.test(clean)?"'"+clean:clean;
    return '"'+safe.replace(/"/g,'""')+'"';
  };
  const header=[
    "Record type","FDA program event key","Ticker","Drug / therapy",
    "Disease / indication","Selected FDA source categories","Linked NCT ID",
    "Clinical stage","Evidence source URL","POOL source as of"
  ];
  const rows=[header.map(cell).join(",")];
  for(const program of coverage.programRows){
    rows.push([
      "FDA PROGRAM EVENT — NOT A CLINICAL TRIAL",program.eventKey,program.ticker,
      program.drug,program.indication,program.designations.map(d=>d.label).join(" | "),
      program.linkedNcts.join(" | "),
      program.linkedNcts.length?"Check source NCT separately":"NOT ESTABLISHED",
      [...new Set(program.designations.map(d=>d.source))].join(" | "),
      sourceAsOf
    ].map(cell).join(","));
  }
  return "\uFEFF"+rows.join("\r\n")+"\r\n";
}

export {renderToolsSpreadsheetCsv};
