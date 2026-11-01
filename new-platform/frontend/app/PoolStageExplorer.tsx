"use client";

import {useEffect,useMemo,useState,type FormEvent} from "react";
import type {DesignationKey} from "../lib/trial-designations";
import styles from "./FunnelWorkspace.module.css";
import PoolDesignationSelector from "./PoolDesignationSelector";

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
          !result.stageStats.stages||result.rows.length>50)throw Error("Stage totals could not be validated.");
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
  const matchCount=!hasSelections?0:!loading&&page?page.total:null;
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
        <h2>POOL Stages &amp; FDA Designation Filters</h2>
        <p className={styles.muted}>Choose stages and FDA designations independently or together. Both dropdowns start at <strong>0 selected</strong>; no matching trials are shown until you select at least one filter.</p>
      </div>
      <strong style={{fontSize:19,whiteSpace:"nowrap"}} aria-live="polite">{matchCount===null?"—":count(matchCount)} matching trials</strong>
    </div>
    <div className={styles.stageDesignationColumns}>
      <div className={styles.stageDropdownColumn}>
        <div className={styles.stageDropdownLabel}>Clinical development stages · {stats?count(stats.trials)+" NCTs in POOL":"Checking source…"}</div>
        <p className={styles.stageDropdownSubline}>Any selected stage qualifies within this list (OR).</p>
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
    {!loading&&page&&hasSelections&&<>
      <p className={styles.muted} role="status">
        <strong>{count(page.total)} matching NCT trial records</strong> · {selectedStages.length} stages, {selectedDesignations.length} designations selected · Showing {page.total?offset+1:0}–{Math.min(offset+page.rows.length,page.total)}.
      </p>
      {selectedDesignations.length>0&&<p className={styles.muted}>
        FDA evidence matched by exact NCT and ticker only. {count(page.designationLinkage?.sourceLinkedTrials??0)} source-linked trials match the selected designations before stage and search filtering. Unlinked or missing designation evidence is not a denial.
      </p>}
      <div className={styles.scroll}>
        <table className={styles.table} style={{minWidth:750}}>
          <thead><tr><th>NCT trial ID</th><th>Ticker</th><th>Company</th><th>Drug</th><th>Disease / indication</th><th>Development stage</th></tr></thead>
          <tbody>{page.rows.map(row=><tr key={row.id}>
            <td>{row.id.replace(/^TRIAL\|/,"")}</td>
            <td>{value(row.ticker)}</td><td>{value(row.company)}</td>
            <td>{value(row.drug)}</td><td>{value(row.indication)}</td><td>{value(row.stage)}</td>
          </tr>)}</tbody>
        </table>
      </div>
      {page.total===0&&<p>No source-linked trials match these selections. This does not establish that no such trials or FDA designations exist; only documented exact links are counted.</p>}
      <div className={styles.pagination}>
        <button type="button" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-50))}>Previous</button>
        <span>Page {Math.floor(offset/50)+1} of {Math.max(1,Math.ceil(page.total/50))}</span>
        <button type="button" disabled={page.nextOffset===null} onClick={()=>setOffset(page.nextOffset!)}>Next</button>
      </div>
    </>}
  </section>;
}
