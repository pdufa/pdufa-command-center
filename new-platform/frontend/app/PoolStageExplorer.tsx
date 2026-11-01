"use client";

import {useEffect,useMemo,useState,type FormEvent} from "react";
import styles from "./FunnelWorkspace.module.css";
import PoolDesignationSelector from "./PoolDesignationSelector";

type GroupKey="all"|"early"|"phase3"|"regulatory"|"other";
type RecordKind="trials"|"all"|"other";
type StageCount={trials:number;standaloneResults:number;regulatoryEvents:number;total:number};
type StageStats={
  total:number;trials:number;standaloneResults:number;regulatoryEvents:number;
  stages:Record<string,StageCount>;
};
type PoolRow={id:string;ticker:string;company?:string;drug?:string;indication?:string;stage?:string;marketCap?:number|null};
type PoolResponse={
  view:string;total:number;limit:number;offset:number;nextOffset:number|null;
  stageStats:StageStats;rows:PoolRow[];datasetVersion?:string;
  overview?:{poolAsOf:string|null;poolSourceState:string};
};
const groups:{id:GroupKey;name:string;description:string;stages:readonly string[]}[]=[
  {id:"early",name:"Early clinical",description:"Early Phase 1 to Phase 2/3",stages:["Early Phase 1","Phase 1","Phase 1/2","Phase 2","Phase 2/3"]},
  {id:"phase3",name:"Phase 3 & results",description:"Pivotal development and reported results",stages:["Phase 3","Phase 3 Results"]},
  {id:"regulatory",name:"FDA & later",description:"Application, decision and follow-up",stages:["NDA/BLA Submission","FDA Acceptance","PDUFA Decision","Post-Decision","Phase 4"]},
  {id:"other",name:"Unknown / N.A.",description:"No trustworthy development-stage label",stages:["Not Applicable","Unknown"]},
];
const stages=groups.flatMap(group=>group.stages);
const count=(n:number)=>n.toLocaleString("en-US");
const value=(v?:string)=>v?.trim()||"Not recorded";
const summaryCount=(stat:StageCount|undefined,kind:RecordKind)=>
  !stat?0:kind==="trials"?stat.trials:kind==="other"?stat.standaloneResults+stat.regulatoryEvents:stat.total;

export default function PoolStageExplorer(){
  const [kind,setKind]=useState<RecordKind>("trials");
  const [group,setGroup]=useState<GroupKey>("all");
  const [stage,setStage]=useState("");
  const [queryInput,setQueryInput]=useState("");
  const [query,setQuery]=useState("");
  const [offset,setOffset]=useState(0);
  const [page,setPage]=useState<PoolResponse|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const params=useMemo(()=>{
    const p=new URLSearchParams({view:"pool",recordKind:kind,stageGroup:group,offset:String(offset),limit:"50"});
    if(stage)p.set("stage",stage);
    if(query.trim())p.set("query",query.trim());
    return p.toString();
  },[kind,group,stage,offset,query]);
  useEffect(()=>{
    const controller=new AbortController();
    setLoading(true);setError("");
    void fetch("/api/scope-funnel?"+params,{cache:"no-store",signal:controller.signal})
      .then(async response=>{
        if(!response.ok)throw Error(response.status===401?"Sign in to view the published POOL inventory.":"POOL stages are unavailable until source reconciliation succeeds (HTTP "+response.status+").");
        return response.json() as Promise<PoolResponse>;
      })
      .then(result=>{
        if(controller.signal.aborted)return;
        if(result.view!=="pool"||!result.stageStats||!Array.isArray(result.rows)||
          !Number.isSafeInteger(result.total)||!Number.isSafeInteger(result.stageStats.trials)||
          !Array.isArray(stages)||!result.stageStats.stages ||
          result.rows.length>50)throw Error("Stage data did not pass validation.");
        setPage(result);
      })
      .catch(e=>{if(!controller.signal.aborted){setPage(null);setError(e instanceof Error?e.message:"Unable to load POOL stages");}})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[params]);
  const stats=page?.stageStats;
  const totalForKind=stats?(kind==="trials"?stats.trials:kind==="other"?stats.standaloneResults+stats.regulatoryEvents:stats.total):null;
  function selectGroup(next:GroupKey){setGroup(next);setStage("");setOffset(0);}
  function selectStage(next:string){setStage(next);setGroup("all");setOffset(0);}
  function submitSearch(event:FormEvent<HTMLFormElement>){event.preventDefault();setQuery(queryInput);setOffset(0);}
  return <section className={styles.panel} aria-label="POOL trial stages with selectors" style={{margin:"20px 0"}}>
    <div className={styles.headline}>
      <div>
        <h2>POOL — Trial Stages &amp; FDA Designations</h2>
        <p className={styles.muted}>Browse the complete preserved POOL by recorded stage. GEM JR and GEM are not part of this view. This is a stage inventory, not a Pipeline eligibility decision.</p>
      </div>
      <strong style={{fontSize:20}}>{totalForKind===null?"—":count(totalForKind)} {kind==="trials"?"NCT trials":"records"}</strong>
    </div>
    <div style={{display:"flex",gap:12,flexWrap:"wrap",alignItems:"end",margin:"14px 0"}}>
      <label style={{display:"flex",flexDirection:"column",gap:5,fontSize:13,fontWeight:700}}>
        Record type
        <select value={kind} onChange={e=>{setKind(e.target.value as RecordKind);setOffset(0)}} style={{padding:9,borderRadius:7}}>
          <option value="trials">Clinical trials (unique NCT records)</option>
          <option value="all">All POOL records (trials + events)</option>
          <option value="other">Standalone results + regulatory records</option>
        </select>
      </label>
      <form className={styles.search} onSubmit={submitSearch}>
        <input aria-label="Search POOL trials by ticker, NCT, company, drug or indication" type="search"
          value={queryInput} onChange={e=>setQueryInput(e.target.value)} maxLength={100}
          placeholder="NCT, ticker, drug, disease"/>
        <button type="submit">Search</button>
        <button type="button" onClick={()=>{setQueryInput("");setQuery("");setOffset(0)}}>Clear</button>
      </form>
    </div>
    <div className={styles.stageDesignationColumns}>
      <details className={styles.stageDesignationPane}>
        <summary className={styles.stageDesignationSummary}>
          <span>Clinical Development Stages</span>
          <strong>{totalForKind===null?"—":count(totalForKind)} {kind==="trials"?"trials":"records"}</strong>
        </summary>
        <div className={styles.stageDesignationBody}>
          <p className={styles.muted}>Select any stage to display its trials below. Counts are drawn from the preserved POOL, using one source record per NCT.</p>
          <button type="button" className={styles.stageDesignationRow}
            aria-pressed={group==="all"&&!stage} onClick={()=>selectGroup("all")}>
            <span><strong>All stages</strong></span>
            <strong>{totalForKind===null?"—":count(totalForKind)}</strong>
          </button>
          <div className={styles.stageDesignationList} role="group" aria-label="Select a POOL trial stage">
            {groups.map(g=>{
              const subtotal=stats?g.stages.reduce((sum,name)=>sum+summaryCount(stats.stages[name],kind),0):null;
              return <div key={g.id}>
                <button type="button" className={styles.stageDesignationGroup}
                  aria-pressed={group===g.id&&!stage} onClick={()=>selectGroup(g.id)}>
                  <span>{g.name}</span><strong>{subtotal===null?"—":count(subtotal)}</strong>
                </button>
                {g.stages.map(name=><button type="button" key={name}
                  className={styles.stageDesignationRow}
                  aria-pressed={stage===name} onClick={()=>selectStage(name)}>
                  <span>{name}</span>
                  <strong>{stats?count(summaryCount(stats.stages[name],kind)):"—"}</strong>
                </button>)}
              </div>;
            })}
          </div>
          <p className={styles.muted}>A recorded stage does not certify a successful trial or FDA approval.</p>
        </div>
      </details>
      <PoolDesignationSelector/>
    </div>
    <p className={styles.muted}>Unique NCT counts use one preserved TRIAL|NCT identifier per trial. Standalone result announcements and FDA application/event records are shown separately; their totals must not be added to unique trial counts. Recorded stages are source classifications, not proof of FDA acceptance or approval.</p>
    {stats&&<p className={styles.muted}>Inventory composition: {count(stats.trials)} unique NCT trial records · {count(stats.standaloneResults)} standalone result records · {count(stats.regulatoryEvents)} regulatory/other records. Source: {value(page?.overview?.poolSourceState)}; snapshot {value(page?.overview?.poolAsOf||undefined)}.</p>}
    {loading&&<p role="status">Checking the published POOL and stage counts…</p>}
    {error&&<p role="alert" className={styles.error}>{error}</p>}
    {page&&!loading&&<>
      <p className={styles.muted} role="status">
        Selected: <strong>{stage||groups.find(g=>g.id===group)?.name||"All stages"}</strong> · Showing {page.total?offset+1:0}–{Math.min(offset+page.rows.length,page.total)} of {count(page.total)} matching source records.
      </p>
      <div className={styles.scroll}>
        <table className={styles.table} style={{minWidth:820}}>
          <thead><tr><th>Source ID</th><th>Ticker</th><th>Company</th><th>Drug</th><th>Indication / disease</th><th>Recorded stage</th><th>Record type</th></tr></thead>
          <tbody>{page.rows.map(row=><tr key={row.id}>
            <td>{row.id}</td><td>{value(row.ticker)}</td><td>{value(row.company)}</td>
            <td>{value(row.drug)}</td><td>{value(row.indication)}</td><td>{value(row.stage)}</td>
            <td>{row.id.startsWith("TRIAL|")?"Unique NCT trial":row.id.startsWith("RESULT|")?"Result announcement":"Regulatory / other"}</td>
          </tr>)}</tbody>
        </table>
      </div>
      {page.total===0&&<p>No matching records for this selection; this is not proof that no drug candidates qualify for PIPELINE.</p>}
      <div className={styles.pagination}>
        <button type="button" disabled={loading||offset===0} onClick={()=>setOffset(Math.max(0,offset-50))}>Previous</button>
        <span>Page {Math.floor(offset/50)+1} of {Math.max(1,Math.ceil(page.total/50))}</span>
        <button type="button" disabled={loading||page.nextOffset===null} onClick={()=>setOffset(page.nextOffset!)}>Next</button>
      </div>
    </>}
  </section>;
}
