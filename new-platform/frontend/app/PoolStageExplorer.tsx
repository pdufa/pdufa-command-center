"use client";

import {useEffect,useMemo,useState,type FormEvent} from "react";
import styles from "./FunnelWorkspace.module.css";
import PoolDesignationSelector from "./PoolDesignationSelector";

type RecordKind="trials"|"all"|"other";
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
const summaryCount=(stat:StageCount|undefined,kind:RecordKind)=>
  !stat?0:kind==="trials"?stat.trials:kind==="other"?stat.standaloneResults+stat.regulatoryEvents:stat.total;

export default function PoolStageExplorer(){
  const [kind,setKind]=useState<RecordKind>("trials");
  const [selectedStages,setSelectedStages]=useState<string[]>([]);
  const [queryInput,setQueryInput]=useState("");
  const [query,setQuery]=useState("");
  const [offset,setOffset]=useState(0);
  const [page,setPage]=useState<PoolResponse|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const params=useMemo(()=>{
    const p=new URLSearchParams({view:"pool",recordKind:kind,offset:String(offset),limit:"50"});
    if(selectedStages.length)p.set("stages",selectedStages.join(","));
    if(query.trim())p.set("query",query.trim());
    return p.toString();
  },[kind,selectedStages,offset,query]);
  useEffect(()=>{
    const controller=new AbortController();
    setLoading(true);setError("");
    void fetch("/api/scope-funnel?"+params,{cache:"no-store",signal:controller.signal})
      .then(async response=>{
        if(!response.ok)throw Error(response.status===401?"Sign in to view the preserved POOL.":"POOL stages unavailable until source reconciliation succeeds (HTTP "+response.status+").");
        return response.json() as Promise<PoolResponse>;
      })
      .then(result=>{
        if(controller.signal.aborted)return;
        if(result.view!=="pool"||!result.stageStats||!Array.isArray(result.rows)||
          !Number.isSafeInteger(result.total)||!Number.isSafeInteger(result.stageStats.trials)||
          !result.stageStats.stages||result.rows.length>50)throw Error("Stage totals could not be validated.");
        setPage(result);
      })
      .catch(reason=>{if(!controller.signal.aborted){setPage(null);setError(reason instanceof Error?reason.message:"Unable to load POOL stage data");}})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[params]);
  const stats=page?.stageStats;
  const totalForKind=stats?(kind==="trials"?stats.trials:kind==="other"?stats.standaloneResults+stats.regulatoryEvents:stats.total):null;
  function toggleStage(stage:string){
    setSelectedStages(old=>old.includes(stage)?old.filter(item=>item!==stage):[...old,stage]);
    setOffset(0);
  }
  function setStageSelection(next:string[]){setSelectedStages(next);setOffset(0);}
  function submitSearch(event:FormEvent<HTMLFormElement>){event.preventDefault();setQuery(queryInput);setOffset(0);}
  return <section className={styles.panel} aria-label="POOL stage and FDA designation tools" style={{margin:"18px 0"}}>
    <div className={styles.headline}>
      <div>
        <h2>POOL Stage &amp; FDA Designation Selectors</h2>
        <p className={styles.muted}>Choose multiple items from scrollable checklists, as in a filter menu. These tools inspect the preserved POOL; they do not restore GEM JR/GEM or change Pipeline screening rules.</p>
      </div>
      <strong style={{fontSize:19,whiteSpace:"nowrap"}}>{totalForKind===null?"—":count(totalForKind)} {kind==="trials"?"NCT trials":"records"}</strong>
    </div>
    <div className={styles.stageDesignationColumns}>
      <div className={styles.stageDropdownColumn}>
        <label className={styles.stageDropdownLabel} htmlFor="pool-record-kind">Count records by</label>
        <select id="pool-record-kind" className={styles.stageKindSelect} value={kind}
          onChange={e=>{setKind(e.target.value as RecordKind);setOffset(0)}}>
          <option value="trials">Unique NCT clinical trials</option>
          <option value="all">All POOL source records</option>
          <option value="other">Result + regulatory event records</option>
        </select>
        <details className={styles.stageDesignationPane}>
          <summary className={styles.stageDesignationSummary}>
            <span>{selectedStages.length===0?"Select clinical trial stages":selectedStages.length+" stages selected"}</span>
            <strong>{totalForKind===null?"—":count(totalForKind)}</strong>
          </summary>
          <div className={styles.stageDesignationBody}>
            <div className={styles.stageDropdownActions}>
              <button type="button" onClick={()=>setStageSelection([...stages])}>Select all</button>
              <button type="button" onClick={()=>setStageSelection([])}>Clear</button>
            </div>
            <div className={styles.stageDesignationList} role="group" aria-label="Clinical development stages">
              {groups.map(group=><div key={group.label}>
                <div className={styles.stageDesignationGroup}>
                  <span>{group.label}</span>
                  <strong>{stats?count(group.stages.reduce((sum,name)=>sum+summaryCount(stats.stages[name],kind),0)):"—"}</strong>
                </div>
                {group.stages.map(stage=><label key={stage} className={styles.stageCheckboxRow}>
                  <input type="checkbox" checked={selectedStages.includes(stage)}
                    onChange={()=>toggleStage(stage)}/>
                  <span>{stage}</span>
                  <strong>{stats?count(summaryCount(stats.stages[stage],kind)):"—"}</strong>
                </label>)}
              </div>)}
            </div>
            <p className={styles.muted}>Select multiple stages to show all matching records (OR). With nothing checked, all stages are included.</p>
          </div>
        </details>
      </div>
      <PoolDesignationSelector/>
    </div>
    <form onSubmit={submitSearch} className={styles.search} style={{margin:"16px 0"}}>
      <input aria-label="Search trial NCT, ticker, company, drug or disease" type="search"
        value={queryInput} onChange={e=>setQueryInput(e.target.value)} maxLength={100}
        placeholder="Find NCT, ticker, drug or disease"/>
      <button type="submit">Search records</button>
      <button type="button" onClick={()=>{setQueryInput("");setQuery("");setOffset(0)}}>Clear search</button>
    </form>
    <p className={styles.muted}>Left-side counts are unique NCT trial records by recorded stage. The FDA list counts source-linked application/program records separately; it does not automatically intersect with selected POOL stages. Missing data is not counted as a verified designation.</p>
    {stats&&<p className={styles.muted}>Source: {value(page?.overview?.poolSourceState)} · snapshot {value(page?.overview?.poolAsOf||undefined)} · {count(stats.trials)} unique NCT records · {count(stats.standaloneResults+stats.regulatoryEvents)} other source records.</p>}
    {loading&&<p role="status">Loading source-linked stage totals…</p>}
    {error&&<p className={styles.error} role="alert">{error}</p>}
    {page&&!loading&&<>
      <p className={styles.muted} role="status">Selected {selectedStages.length?selectedStages.length+" stages":"all stages"} · Showing {page.total?offset+1:0}–{Math.min(offset+page.rows.length,page.total)} of {count(page.total)} records.</p>
      <div className={styles.scroll}>
        <table className={styles.table} style={{minWidth:800}}>
          <thead><tr><th>Source ID</th><th>Ticker</th><th>Company</th><th>Drug</th><th>Disease / indication</th><th>Development stage</th><th>Record type</th></tr></thead>
          <tbody>{page.rows.map(row=><tr key={row.id}>
            <td>{row.id}</td><td>{value(row.ticker)}</td><td>{value(row.company)}</td>
            <td>{value(row.drug)}</td><td>{value(row.indication)}</td><td>{value(row.stage)}</td>
            <td>{row.id.startsWith("TRIAL|")?"Unique NCT trial":row.id.startsWith("RESULT|")?"Result record":"Regulatory/other record"}</td>
          </tr>)}</tbody>
        </table>
      </div>
      {page.total===0&&<p>No saved records match the current selections. That is not evidence of no eligible candidates.</p>}
      <div className={styles.pagination}>
        <button type="button" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-50))}>Previous</button>
        <span>Page {Math.floor(offset/50)+1} of {Math.max(1,Math.ceil(page.total/50))}</span>
        <button type="button" disabled={page.nextOffset===null} onClick={()=>setOffset(page.nextOffset!)}>Next</button>
      </div>
    </>}
  </section>;
}
