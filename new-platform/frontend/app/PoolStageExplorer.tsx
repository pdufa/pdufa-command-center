"use client";

import {useEffect,useMemo,useState,type FormEvent} from "react";
import type {DesignationKey} from "../lib/trial-designations";
import styles from "./FunnelWorkspace.module.css";
import PoolDesignationSelector from "./PoolDesignationSelector";
import ToolsResultsSpreadsheet, {type ToolsSpreadsheetRow,type SelectedFiltersSummary} from "./ToolsResultsSpreadsheet";

type StageCount={trials:number;standaloneResults:number;regulatoryEvents:number;total:number};
type StageStats={
  total:number;trials:number;standaloneResults:number;regulatoryEvents:number;
  stages:Record<string,StageCount>;
};
type PoolRow={id:string;ticker:string;company?:string;drug?:string;indication?:string;stage?:string};
type PoolResponse={
  view:string;total:number;limit:number;offset:number;nextOffset:number|null;
  stageStats:StageStats;rows:PoolRow[];
  overview?:{poolAsOf:string|null;poolSourceState:string};
  designationLinkage?:{basis:string;sourceLinkedTrials:number}|null;
  spreadsheetRows?:ToolsSpreadsheetRow[];
  selectionSummary?:SelectedFiltersSummary|null;
};
const groups=[
  {label:"Early clinical",stages:["Early Phase 1","Phase 1","Phase 1/2","Phase 2","Phase 2/3"]},
  {label:"Phase 3 and results",stages:["Phase 3","Phase 3 Results"]},
  {label:"FDA regulatory and later",stages:["NDA/BLA Submission","FDA Acceptance","PDUFA Decision","Post-Decision","Phase 4"]},
  {label:"Unknown / N.A.",stages:["Not Applicable","Unknown"]},
] as const;
const stages=groups.flatMap(group=>[...group.stages]);
const count=(n:number)=>n.toLocaleString("en-US");
const value=(v?:string)=>v?.trim()||"Not recorded";
const stageCount=(stat:StageCount|undefined)=>stat?.trials??0;

export default function PoolStageExplorer(){
  const [selectedStages,setSelectedStages]=useState<string[]>([]);
  const [selectedDesignations,setSelectedDesignations]=useState<DesignationKey[]>([]);
  const [queryInput,setQueryInput]=useState("");
  const [query,setQuery]=useState("");
  const [offset,setOffset]=useState(0);
  const [page,setPage]=useState<PoolResponse|null>(null);
  const [lastStats,setLastStats]=useState<StageStats|null>(null);
  const [sourceState,setSourceState]=useState("");
  const [sourceDate,setSourceDate]=useState("");
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const hasSelections=selectedStages.length>0||selectedDesignations.length>0;
  const params=useMemo(()=>{
    const p=new URLSearchParams({view:"pool",recordKind:"trials",tools:"1",offset:String(offset),limit:"50"});
    if(selectedStages.length)p.set("stages",selectedStages.join(","));
    if(selectedDesignations.length)p.set("designations",selectedDesignations.join(","));
    if(query.trim())p.set("query",query.trim());
    return p.toString();
  },[selectedStages,selectedDesignations,offset,query]);
  const downloadUrl=useMemo(()=>{
    const p=new URLSearchParams(params);
    p.set("format","csv");
    p.set("offset","0");
    return "/api/scope-funnel?"+p.toString();
  },[params]);
  useEffect(()=>{
    const controller=new AbortController();
    setPage(null);
    setLoading(true);setError("");
    void fetch("/api/scope-funnel?"+params,{cache:"no-store",signal:controller.signal})
      .then(async response=>{
        if(!response.ok){
          const detail=await response.json().catch(()=>null) as {error?:string}|null;
          throw Error(response.status===401?"Sign in to view the saved POOL.":detail?.error||"Source verification unavailable (HTTP "+response.status+").");
        }
        return response.json() as Promise<PoolResponse>;
      })
      .then(result=>{
        if(controller.signal.aborted)return;
        if(result.view!=="pool"||!result.stageStats||!Array.isArray(result.rows)||
          !Number.isSafeInteger(result.total)||!Number.isSafeInteger(result.stageStats.trials)||
          !result.stageStats.stages||result.rows.length>50||
          !Array.isArray(result.spreadsheetRows)||result.spreadsheetRows.length!==result.rows.length||
          !result.selectionSummary)throw Error("Filtered spreadsheet data could not be validated.");
        setLastStats(result.stageStats);
        setSourceState(result.overview?.poolSourceState||"Unknown");
        setSourceDate(result.overview?.poolAsOf||"Not recorded");
        setPage(result);
      })
      .catch(reason=>{if(!controller.signal.aborted){setPage(null);setError(reason instanceof Error?reason.message:"Unable to load POOL stage data");}})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[params]);
  const stats=page?.stageStats||lastStats;
  const matchingTrialLabel=!hasSelections?"0 matching trials":loading?"Calculating matching trials…":error?"Trial count unavailable":page?count(page.total)+" matching trials":"Trial count unavailable";
  function toggleStage(stage:string){
    setSelectedStages(old=>old.includes(stage)?old.filter(item=>item!==stage):[...old,stage]);
    setOffset(0);
  }
  function changeStages(next:string[]){setSelectedStages(next);setOffset(0);}
  function changeDesignations(next:DesignationKey[]){setSelectedDesignations(next);setOffset(0);}
  function submitSearch(event:FormEvent<HTMLFormElement>){event.preventDefault();setQuery(queryInput);setOffset(0);}
  return <section className={styles.panel} aria-label="POOL stage and FDA designation tools" style={{margin:"18px 0"}}>
    <div className={styles.headline}>
      <div>
        <h2>POOL</h2>
        <p className={styles.stageTrialMatchCount} role="status" aria-live="polite" aria-atomic="true">{matchingTrialLabel}</p>
        <p className={styles.muted}>Choose stages and FDA designations independently or together. Both dropdowns start at <strong>0 selected</strong>; the number above counts unique trials matching your selected filters{query?" and search term":""}.</p>
      </div>
    </div>
    <div className={styles.stageDesignationColumns}>
      <div className={styles.stageDropdownColumn}>
        <div className={styles.stageDropdownLabel}>Clinical development stages</div>
        <p className={styles.stageDropdownSubline}>
          Select one or more stages below. Counts beside each stage describe the full POOL.
          {stats?" Full POOL: "+count(stats.trials)+" NCT trials.":""}
        </p>
        <details className={styles.stageDesignationPane}>
          <summary className={styles.stageDesignationSummary}>
            <span>{selectedStages.length===0?"Select clinical trial stages":selectedStages.length+" stages selected"}</span>
            <strong>{selectedStages.length} selected</strong>
          </summary>
          <div className={styles.stageDesignationBody}>
            <div className={styles.stageDropdownActions}>
              <button type="button" onClick={()=>changeStages([...stages])}>Select all</button>
              <button type="button" onClick={()=>changeStages([])}>Clear</button>
            </div>
            <div className={styles.stageDesignationList} role="group" aria-label="Clinical development stages">
              {groups.map(group=><div key={group.label}>
                <div className={styles.stageDesignationGroup}>
                  <span>{group.label}</span>
                  <strong>{stats?count(group.stages.reduce((sum,name)=>sum+stageCount(stats.stages[name]),0)):"—"}</strong>
                </div>
                {group.stages.map(stage=><label key={stage} className={styles.stageCheckboxRow}>
                  <input type="checkbox" checked={selectedStages.includes(stage)} onChange={()=>toggleStage(stage)}/>
                  <span>{stage}</span>
                  <strong>{stats?count(stageCount(stats.stages[stage])):"—"}</strong>
                </label>)}
              </div>)}
            </div>
            <p className={styles.muted}>Unchecked stages have no active selection. Counts alongside stage names describe the complete POOL, not the current combined matches.</p>
          </div>
        </details>
      </div>
      <PoolDesignationSelector selected={selectedDesignations} onChange={changeDesignations}/>
    </div>
    <form onSubmit={submitSearch} className={styles.search} style={{margin:"16px 0"}}>
      <input aria-label="Search trial NCT, ticker, company, drug or disease" type="search"
        value={queryInput} onChange={e=>setQueryInput(e.target.value)} maxLength={100}
        placeholder="Search selected results by NCT, ticker, drug or disease"/>
      <button type="submit">Search results</button>
      <button type="button" onClick={()=>{setQueryInput("");setQuery("");setOffset(0)}}>Clear search</button>
    </form>
    <p className={styles.muted}><strong>Filter logic:</strong> Selected stages are OR; selected designations are OR; choosing from both applies AND. A designation-only selection covers any recorded stage. A stage-only selection does not require a known designation. All counts are read-only.</p>
    {stats&&<p className={styles.muted}>Published POOL: {count(stats.trials)} unique NCT trials, plus {count(stats.standaloneResults+stats.regulatoryEvents)} separate source/event records. Source state: {value(sourceState)} · as of {value(sourceDate)}.</p>}
    {loading&&<p role="status">Calculating matching trial records from saved sources…</p>}
    {error&&<p className={styles.error} role="alert">Results unavailable: {error} (not a verified zero).</p>}
    {!loading&&!error&&!hasSelections&&<p role="status"><strong>0 selected · 0 matching trials.</strong> Check a stage or FDA designation to begin.</p>}
    {hasSelections&&page&&!loading&&selectedDesignations.length>0&&<p className={styles.muted}>
      FDA evidence is linked by exact NCT and ticker. {count(page.designationLinkage?.sourceLinkedTrials??0)} unique NCT trials match the selected designation categories before stage filtering.
    </p>}
    <ToolsResultsSpreadsheet
      rows={page?.spreadsheetRows||[]}
      summary={page?.selectionSummary||null}
      stages={selectedStages}
      designations={selectedDesignations}
      total={page?.total||0}
      offset={offset}
      loading={loading}
      error={error}
      downloadUrl={downloadUrl}
      onPrevious={()=>setOffset(Math.max(0,offset-50))}
      onNext={()=>{if(page?.nextOffset!==null&&page?.nextOffset!==undefined)setOffset(page.nextOffset);}}
      nextOffset={page?.nextOffset??null}
    />
  </section>;
}
