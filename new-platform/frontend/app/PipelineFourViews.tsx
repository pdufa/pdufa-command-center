"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import styles from "./FunnelWorkspace.module.css";
import {
  PIPELINE_RESEARCH_SECTIONS, PIPELINE_RESEARCH_FIELDS, ALL_RESEARCH_FIELD_DEFINITIONS, WORKFLOW_COLUMNS,
  researchFieldResult, verifiedMetricCount, workflowColumn, comparableIndication, comparableResearchGroup,
  type PipelineResearchRow, type ResearchFieldId, type WorkflowColumn,
} from "../lib/pipeline-research-view";
import { loadCompleteResearch } from "../lib/pipeline-research-pagination";
import { pacificToday } from "../lib/pipeline-timeline";
import {validateComparatorInventory} from "../lib/clinical-comparators";
import LiveRegistryReview from "./LiveRegistryReview";
import TrialTimelineSummary from "./TrialTimelineSummary";
import CompanyDateBadges from "./CompanyDateBadges";
import PipelineSponsorReadout from "./PipelineSponsorReadout";
import PipelineEligibilityChecklist from "./PipelineEligibilityChecklist";

type Mode="table"|"dossier"|"kanban"|"analytics";
type Payload={view:string;offset:number;limit:number;total:number;rows:PipelineResearchRow[];
 caveat:string;overview:{censusAsOf:string;matchedCompletedRecords:number;qualifiedPrograms:null;poolSourceState:string}};
const FETCH_PAGE_SIZE=200;
const PAGE_SIZE=25;
const modeOptions:{id:Mode;name:string;detail:string}[]=[
 {id:"table",name:"1 · Advanced Table",detail:"Sort, scan, expand"},
 {id:"dossier",name:"2 · Cards + Dossier",detail:"One trial in depth"},
 {id:"kanban",name:"3 · Research Workflow",detail:"Prioritize research gaps"},
 {id:"analytics",name:"4 · Compare + Analytics",detail:"Same-indication comparisons"},
];
function named(row:PipelineResearchRow){return row.drug||"Therapy not verified"}
function trialDay(row:PipelineResearchRow,id:ResearchFieldId,today:string){
 return researchFieldResult(row,id,today);
}
function Dossier({row,today,onClose}:{row:PipelineResearchRow;today:string;onClose:()=>void}){
 const [opened,setOpened]=useState<"all"|"none">("none");
 return <section className={styles.dossier} aria-label={"Detailed trial dossier "+row.nctId}>
   <div className={styles.dossierHeading}>
    <div><div style={{display:"flex",alignItems:"center",flexWrap:"wrap",gap:10}}>
      <h3 style={{margin:0}}>{row.nctId} · {row.ticker}</h3>
      <TrialTimelineSummary timeline={row.timeline} today={today} compact trial={row}/>
      </div>
      <p>{row.company}<CompanyDateBadges nctId={row.nctId} timeline={row.timeline} today={today}/> · {named(row)} · {row.indication||"Indication not verified"}</p>
      <p>Public Phase 3 release: {row.timeline?.phase3DataRelease?.date||"Not verified"} · Verified PDUFA: {row.timeline?.pdufaTarget?.date||"Not verified"}</p>
      <p className={styles.muted}>Source-backed clinical and regulatory research. NCT studies are not necessarily distinct commercial products.</p>
    </div>
    <button type="button" onClick={onClose}>Close trial</button>
   </div>
   <div className={styles.dossierTools}>
    <button type="button" onClick={()=>setOpened("all")}>Expand seven sections</button>
    <button type="button" onClick={()=>setOpened("none")}>Collapse sections</button>
    <a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov source ↗</a>
   </div>
   <LiveRegistryReview nctId={row.nctId}/>
   <PipelineSponsorReadout nctId={row.nctId} ticker={row.ticker}/>
   <PipelineEligibilityChecklist row={row} today={today}/>
   <details className={styles.dossierSection}>
    <summary><strong>Source research fields · evidence groups</strong><span>Reference detail</span></summary>
   {PIPELINE_RESEARCH_SECTIONS.map(section=><details key={row.nctId+"|"+section.title}
      className={styles.dossierSection} open={opened==="all"?true:undefined}>
     <summary><strong>{section.title}</strong><span>{section.fields.length} fields</span></summary>
     <div className={styles.dossierFields}>
      {section.fields.map(field=>{
       const result=researchFieldResult(row,field.id,today);
       return <details key={field.id} className={styles.dossierField}>
        <summary><span>{field.label}</span><strong>{result.value}</strong></summary>
        <div className={styles.dossierEvidence}>
         <p><strong>Purpose:</strong> {field.purpose}</p>
         <p><strong>Assessment:</strong> {result.state==="MISSING"?"Not established":result.state==="RECORD"?"Source record — verify interpretation":result.state==="MODELED"?"Modeled estimate":"Source-verified fact"}</p>
         <p><strong>Reason:</strong> {result.why}</p>
         <p><strong>Required evidence:</strong> {field.evidence}</p>
         {result.method&&<p><strong>Method:</strong> {result.method}</p>}
         {result.confidence&&<p><strong>Confidence:</strong> {result.confidence}</p>}
         {result.sourceUrl&&<p><strong>Source:</strong> <a href={result.sourceUrl} target="_blank" rel="noopener noreferrer">Open evidence ↗</a>{result.sourceDate?" · "+result.sourceDate:""}</p>}
        </div>
       </details>;
      })}
     </div>
    </details>)}
   </details>
   <div className={styles.dossierFoot}>
    <strong>Outstanding qualification checks</strong>
    <ul>{row.reasons.map((reason,i)=><li key={i}>{reason}</li>)}</ul>
    <p>Competitive advantage is not FDA PASS/CRL/EXTENSION probability. An absent metric cannot be ranked.</p>
   </div>
  </section>;
}
function TrialMini({row,today,onOpen}:{row:PipelineResearchRow;today:string;onOpen:()=>void}){
 const due=trialDay(row,"daysToPdufa",today);
 return <button type="button" className={styles.trialMini} onClick={onOpen}>
  <strong>{row.nctId} · {row.ticker}</strong>
  <span>{named(row)}</span>
  <small>{row.indication||"Indication not verified"}</small>
  <span className={styles.muted}>PDUFA: {due.value} · Verify {row.reasons.length} qualification checks</span>
 </button>;
}
export default function PipelineFourViews(){
 const [data,setData]=useState<Payload|null>(null);
 const [fetchError,setFetchError]=useState("");
 const [loading,setLoading]=useState(true);
 const [mode,setMode]=useState<Mode>("table");
 const [query,setQuery]=useState("");
 const [selected,setSelected]=useState<string|null>(null);
 const [page,setPage]=useState(0);
 const [sort,setSort]=useState<"nct"|"ticker"|"pdufa"|"coverage">("ticker");
 const [boardLimit,setBoardLimit]=useState<Record<WorkflowColumn,number>>({
  readout:10,pdufa:10,research:10,approaching:10,cutoff:10,
 });
 const [indication,setIndication]=useState("");
 const [compareIds,setCompareIds]=useState<string[]>([]);
 const [today,setToday]=useState("");
 useEffect(()=>{const update=()=>setToday(pacificToday());update();const timer=setInterval(update,60000);return()=>clearInterval(timer)},[]);
 useEffect(()=>{
  const controller=new AbortController();
  void loadCompleteResearch(async(offset,limit)=>{
   const params=new URLSearchParams({view:"pipeline",offset:String(offset),limit:String(limit)});
   const response=await fetch("/api/scope-funnel?"+params.toString(),{cache:"no-store",signal:controller.signal});
   if(!response.ok)throw Error(response.status===401?"Dashboard sign-in is required for the shared Pipeline research inventory.":"Cannot verify published POOL and historical Phase 3 research data.");
   return response.json();
  },FETCH_PAGE_SIZE).then(raw=>{
     if(!controller.signal.aborted)setData(raw as unknown as Payload);
    }).catch(e=>{if(!controller.signal.aborted)setFetchError(e instanceof Error?e.message:"Data unavailable")})
    .finally(()=>{if(!controller.signal.aborted)setLoading(false)});
  return()=>controller.abort();
 },[]);
 
 const all=data?.rows||[];
 const filtered=useMemo(()=>{
  const q=query.trim().toLocaleLowerCase("en-US");
  const result=q?all.filter(r=>[r.nctId,r.ticker,r.company,r.drug,r.indication].some(t=>t?.toLocaleLowerCase("en-US").includes(q))):[...all];
  result.sort((a,b)=>{
   if(sort==="nct")return a.nctId.localeCompare(b.nctId);
   if(sort==="ticker")return a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId);
   if(sort==="coverage")return verifiedMetricCount(b,today)-verifiedMetricCount(a,today)||a.nctId.localeCompare(b.nctId);
   const av=a.timeline?.pdufaTarget?.date,bv=b.timeline?.pdufaTarget?.date;
   return av&&bv?av.localeCompare(bv):av?-1:bv?1:a.nctId.localeCompare(b.nctId);
  });
  return result;
 },[all,query,sort,today]);
 const totalPages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));
 const activePage=Math.min(page,totalPages-1);
 const visible=filtered.slice(activePage*PAGE_SIZE,(activePage+1)*PAGE_SIZE);
 const selectedRow=filtered.find(r=>r.nctId===selected)||null;
 const buckets=useMemo(()=>{
  const result:Record<WorkflowColumn,PipelineResearchRow[]>={readout:[],pdufa:[],research:[],approaching:[],cutoff:[]};
  for(const row of filtered)result[workflowColumn(row,today)].push(row);
  return result;
 },[filtered,today]);
 const indications=useMemo(()=>{
  const counts=new Map<string,{name:string;rows:PipelineResearchRow[]}>();
  for(const row of filtered){
   const key=comparableResearchGroup(row);
   if(!key)continue;
   const current=counts.get(key)||{name:row.indication!,rows:[]};
   current.rows.push(row);counts.set(key,current);
  }
  return [...counts.entries()].filter(([,x])=>new Set(x.rows.map(r=>r.drug?.trim().toLowerCase())).size>=2).sort((a,b)=>b[1].rows.length-a[1].rows.length);
 },[filtered]);
 const comparable=indications.find(([key])=>key===indication)?.[1].rows||[];
 const chosen=comparable.filter(x=>compareIds.includes(x.nctId)).slice(0,4);
 const metrics=useMemo(()=>{
  const count=(id:ResearchFieldId)=>filtered.filter(row=>researchFieldResult(row,id,today).state==="VERIFIED").length;
  return {readouts:count("daysSinceReadout"),pdufa:count("daysToPdufa"),population:count("eligibleUsPatients"),competitors:count("competitorCount")};
 },[filtered,today]);
 const openTrial=(row:PipelineResearchRow)=>{setSelected(row.nctId)};
 const changeMode=(value:Mode)=>{setMode(value);setSelected(null)};
 const clearSearch=()=>{setQuery("");setPage(0);setSelected(null);setIndication("");setCompareIds([])};
 return <section className={styles.fourViews} aria-label="Four shared Pipeline research views">
  <div className={styles.fourIntro}>
   <div><h2>PIPELINE · Four connected research views</h2>
     <p>One authenticated dataset · clinical and regulatory source evidence · no assumed commercial rank or FDA approval odds</p></div>
   <span className={styles.sharedCount}>{data?data.total.toLocaleString()+" exact-linked research trials":"Awaiting source"}</span>
  </div>
  <div role="tablist" aria-label="Pipeline display mode" className={styles.viewPicker}>
   {modeOptions.map(item=><button key={item.id} type="button" role="tab"
    aria-selected={mode===item.id} className={mode===item.id?styles.viewActive:""}
    onClick={()=>changeMode(item.id)}><strong>{item.name}</strong><small>{item.detail}</small></button>)}
  </div>
  {loading&&<p role="status">Loading one reconciled source for all four research views…</p>}
  {fetchError&&<p role="alert" className={styles.error}>{fetchError} <Link href="/">Dashboard / sign in</Link></p>}
  {data&&<div role="tabpanel" aria-label={modeOptions.find(x=>x.id===mode)?.name}>
   <p className={styles.muted}>This is a historically cap-screened, registry-completed Phase 3 research queue, not 300 independently verified eligible or approved products. Source census: {data.overview.censusAsOf}. No original POOL records have been changed.</p>
   <div className={styles.sharedFilters}>
    <label>Search all {data.total.toLocaleString()} trials
     <input type="search" value={query} onChange={e=>{setQuery(e.target.value);setPage(0);setSelected(null);setCompareIds([]);setIndication("")}} placeholder="NCT, ticker, drug, company or indication"/>
    </label>
    <label>Sort full matching dataset
     <select value={sort} onChange={e=>{setSort(e.target.value as typeof sort);setPage(0)}}>
      <option value="ticker">Ticker / company</option>
      <option value="nct">Trial NCT ID</option>
      <option value="pdufa">Nearest verified PDUFA first</option>
      <option value="coverage">Verified fields first</option>
     </select>
    </label>
    <button type="button" onClick={clearSearch}>Clear search</button>
   </div>
   <p role="status" className={styles.muted}>{filtered.length.toLocaleString()} matching trials · Same filtered source across all views</p>
   {mode==="table"&&<>
    <h3>Trial clinical and regulatory research</h3>
    <p className={styles.muted}>The rightmost three columns identify documented approved therapies, pipeline competitors, and comparative evidence. Horizontal scrolling is available.</p>
    <div className={styles.scroll}><table className={styles.table} aria-label="Trial evidence overview">
     <thead><tr><th>NCT</th><th>Company / ticker</th><th>Proposed therapy / disease</th><th>Public Phase 3 release</th><th>Days since release</th><th>Verified PDUFA date</th><th>Days until PDUFA</th>
      <th>Existing Approved Therapies</th><th>Competing Pipeline Therapies</th><th>Comparative Advantage</th></tr></thead>
     <tbody>{visible.map(row=>{
      const inventory=validateComparatorInventory(row,row.competitorEvidence||[]);
      return <tr key={row.nctId}><td>{row.nctId}</td><td><div style={{display:"flex",alignItems:"center",flexWrap:"wrap",gap:8,minWidth:290}}><strong>{row.ticker}</strong><span>{row.company}<CompanyDateBadges nctId={row.nctId} timeline={row.timeline} today={today}/></span></div></td>
       <td>{named(row)}<small>{row.indication||"Not assessed"}</small></td>
       <td>{row.timeline?.phase3DataRelease?.date||"Not verified"}</td><td>{trialDay(row,"daysSinceReadout",today).value}</td><td>{row.timeline?.pdufaTarget?.date||"Not verified"}</td><td>{trialDay(row,"daysToPdufa",today).value}</td>
       <td>{inventory.accepted.length?inventory.approved+" documented":"Not assessed"}</td>
       <td>{inventory.accepted.length?inventory.pipeline+" documented":"Not assessed"}</td>
       <td>{inventory.rankingAllowed?"Review comparative evidence":"ABSTAIN — insufficient comparable evidence"}</td>
      </tr>;
     })}</tbody>
    </table></div>
    <h3>Compact clinical and commercial review</h3>
    <div className={styles.scroll}><table className={styles.table}>
     <thead><tr><th>Expand</th><th>Trial ID</th><th>Company</th><th>Therapy / indication</th><th>Phase 3 age</th><th>Days to PDUFA</th><th>Competitors</th><th>Strongest verified advantage</th><th>Verified research</th><th>Competitive conclusion</th></tr></thead>
     <tbody>{visible.map(row=><Fragment key={row.nctId}>
      <tr>
       <td><button type="button" aria-expanded={selected===row.nctId} onClick={()=>setSelected(selected===row.nctId?null:row.nctId)}>{selected===row.nctId?"Close":"Expand"}</button></td>
       <td><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">{row.nctId} ↗</a></td>
       <td><div style={{display:"flex",alignItems:"center",flexWrap:"wrap",gap:8,minWidth:290}}><strong>{row.ticker}</strong><span>{row.company}<CompanyDateBadges nctId={row.nctId} timeline={row.timeline} today={today}/></span></div></td>
       <td>{named(row)}<small>{row.indication||"Indication not verified"}</small></td>
       <td>{trialDay(row,"daysSinceReadout",today).value}</td>
       <td>{trialDay(row,"daysToPdufa",today).value}</td>
       <td>{trialDay(row,"competitorCount",today).value}</td>
       <td>{trialDay(row,"clinicalBenefit",today).value}</td>
       <td>{verifiedMetricCount(row,today)} sourced</td>
       <td>{trialDay(row,"verdict",today).value}</td>
      </tr>
      {selected===row.nctId&&<tr><td colSpan={10}><Dossier row={row} today={today} onClose={()=>setSelected(null)}/></td></tr>}
     </Fragment>)}</tbody>
    </table></div>
    <div className={styles.pagination}>
     <button type="button" disabled={activePage===0} onClick={()=>{setPage(activePage-1);setSelected(null)}}>Previous</button>
     <span>Rows {filtered.length?activePage*PAGE_SIZE+1:0}–{Math.min((activePage+1)*PAGE_SIZE,filtered.length)} · Page {activePage+1}/{totalPages}</span>
     <button type="button" disabled={activePage+1>=totalPages} onClick={()=>{setPage(activePage+1);setSelected(null)}}>Next</button>
    </div>
   </>}
   {mode==="dossier"&&<>
    <div className={styles.cardGrid}>
     {visible.map(row=><button key={row.nctId} type="button" className={styles.researchCard}
      onClick={()=>openTrial(row)} aria-pressed={selected===row.nctId}>
       <strong>{row.nctId} · {row.ticker}</strong><span>{row.company}<CompanyDateBadges nctId={row.nctId} timeline={row.timeline} today={today}/></span>
       <b>{named(row)}</b><span>{row.indication||"Indication not verified"}</span>
       <small>Phase 3 age: {trialDay(row,"daysSinceReadout",today).value}</small>
       <small>PDUFA: {trialDay(row,"daysToPdufa",today).value}</small>
       <small>{verifiedMetricCount(row,today)} sourced fields · Open research dossier</small>
      </button>)}
    </div>
    {selectedRow&&<Dossier key={selectedRow.nctId} row={selectedRow} today={today} onClose={()=>setSelected(null)}/>}
    <div className={styles.pagination}>
     <button type="button" disabled={activePage===0} onClick={()=>{setPage(activePage-1);setSelected(null)}}>Previous</button>
     <span>Page {activePage+1} of {totalPages}</span>
     <button type="button" disabled={activePage+1>=totalPages} onClick={()=>{setPage(activePage+1);setSelected(null)}}>Next</button>
    </div>
   </>}
   {mode==="kanban"&&<>
    <p className={styles.muted}>Workflow placement is calculated from verified source coverage and the Phase 3 → PDUFA − 3 timeline. It does not represent positive trial results or trading readiness.</p>
    <div className={styles.boardScroll}><div className={styles.boardGrid}>
     {WORKFLOW_COLUMNS.map(bucket=><section className={styles.boardColumn} key={bucket.id}>
      <div className={styles.boardHeader}><strong>{bucket.label}</strong><span>{buckets[bucket.id].length}</span></div>
      {buckets[bucket.id].slice(0,boardLimit[bucket.id]).map(row=><TrialMini key={row.nctId} row={row} today={today} onOpen={()=>openTrial(row)}/>)}
      {buckets[bucket.id].length>boardLimit[bucket.id]&&<button type="button"
       onClick={()=>setBoardLimit(p=>({...p,[bucket.id]:p[bucket.id]+10}))}>Show next 10</button>}
      {!buckets[bucket.id].length&&<p className={styles.muted}>No matched trials in this category.</p>}
     </section>)}
    </div></div>
    {selectedRow&&<Dossier key={selectedRow.nctId} row={selectedRow} today={today} onClose={()=>setSelected(null)}/>}
   </>}
   {mode==="analytics"&&<>
    <div className={styles.analyticsGrid}>
     {([
      ["Matching trial records",filtered.length],
      ["Verified Phase 3 release dates",metrics.readouts],
      ["Verified PDUFA dates",metrics.pdufa],
      ["Verified eligible U.S. patient counts",metrics.population],
      ["Verified complete competitor counts",metrics.competitors],
     ] as const).map(([title,value])=><div key={title} className={styles.statCard}>
      <small>{title}</small><strong>{value.toLocaleString()}</strong>
     </div>)}
    </div>
    <div className={styles.analyticsPanel}>
     <h3>Evidence coverage by research section</h3>
     <p className={styles.muted}>These percentages measure documented metric coverage, not probability of clinical benefit, FDA approval or trial success.</p>
     {PIPELINE_RESEARCH_SECTIONS.map(section=>{
      const assessed=section.fields.filter(field=>!["evidence","verdict","overallRank"].includes(field.id));
      const verified=assessed.reduce((n,field)=>n+filtered.filter(r=>researchFieldResult(r,field.id,today).state==="VERIFIED").length,0);
      const total=assessed.length*filtered.length;
      const pct=total?Math.round(verified/total*100):0;
      return <div className={styles.coverageRow} key={section.title}>
       <span>{section.title}</span><progress value={verified} max={total||1} aria-label={section.title+" verified evidence coverage"}></progress>
       <strong>{total?pct+"%":"—"}</strong>
      </div>;
     })}
    </div>
    <div className={styles.analyticsPanel}>
     <h3>Compare therapies — verified comparable scope</h3>
     <p className={styles.muted}>Choose up to four exact NCTs only when sources establish the same recorded indication, treatment line, population, endpoint and follow-up. A disease label alone cannot enable comparison. Missing effects remain unassessed.</p>
     <label>Recorded indication
      <select value={indication} onChange={e=>{const key=e.target.value;setIndication(key);const group=indications.find(x=>x[0]===key)?.[1].rows||[];setCompareIds(group.slice(0,2).map(x=>x.nctId))}}>
       <option value="">Select same-indication group</option>
       {indications.map(([key,group])=><option value={key} key={key}>{group.name} ({group.rows.length})</option>)}
      </select>
     </label>
     {!indications.length&&<p>No source-verified comparable group with at least two distinct therapies is available in the filtered selection.</p>}
     {!!indication&&<div className={styles.compareChoices}>
      {comparable.map(row=><label key={row.nctId}>
       <input type="checkbox" checked={compareIds.includes(row.nctId)}
        disabled={!compareIds.includes(row.nctId)&&compareIds.length>=4}
        onChange={e=>setCompareIds(p=>e.target.checked?[...p,row.nctId]:p.filter(id=>id!==row.nctId))}/>
       {row.nctId} · {row.ticker} · {named(row)}
      </label>)}
     </div>}
     {chosen.length>0&&<div className={styles.scroll}><table className={styles.table}>
      <thead><tr><th>Verified / recorded metric</th>{chosen.map(r=><th key={r.nctId}>{r.ticker}<small>{r.nctId}</small></th>)}</tr></thead>
      <tbody>{(["therapy","indication","eligibleUsPatients","closestCompetitor","competitorCount","clinicalBenefit","headToHead","safetyAdvantage","adoption","costDifference","daysSinceReadout","daysToPdufa","verdict"] as ResearchFieldId[]).map(id=>{
       const label=PIPELINE_RESEARCH_FIELDS.find(x=>x.id===id)?.label||id;
       return <tr key={id}><th>{label}</th>{chosen.map(r=><td key={r.nctId}>{researchFieldResult(r,id,today).value}</td>)}</tr>;
      })}</tbody>
     </table></div>}
     {chosen.length===1&&<p className={styles.muted}>Choose another matching-indication trial for a side-by-side view.</p>}
     {chosen.length>0&&<div className={styles.compareActions}>
      {chosen.map(row=><button key={row.nctId} type="button" onClick={()=>openTrial(row)}>Open {row.nctId} dossier</button>)}
     </div>}
    </div>
    {selectedRow&&<Dossier key={selectedRow.nctId} row={selectedRow} today={today} onClose={()=>setSelected(null)}/>}
   </>}
   <p className={styles.muted}>Research assessment period: public pivotal Phase 3 results announcement → PDUFA − 3 calendar days. Restricted Pipeline eligibility ($300M–$10B, U.S.-listed, verified pivotal Phase 3 and commercial rights) requires independent current checks. No probability-of-approval-based competitive ranking.</p>
  </div>}
 </section>;
}

