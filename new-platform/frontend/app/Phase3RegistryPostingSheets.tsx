"use client";
import {useEffect,useMemo,useState} from "react";
import {
  parseRegistryPostingSnapshot,type RegistryPostingRow,type RegistryPostingSnapshot
} from "../lib/phase3-registry-posting";
import css from "./Phase3RegistryPostingSheets.module.css";

const PAGE_SIZE=50;
const fmt=(n:number)=>n.toLocaleString("en-US");
type Kind="before"|"after";
function safeCsvCell(value:string|number){
  const raw=String(value??"");
  const safe=/^[\s]*[=+@-]/.test(raw)?"'"+raw:raw;
  return '"'+safe.replace(/"/g,'""')+'"';
}
function exportCsv(kind:Kind,rows:readonly RegistryPostingRow[]){
  const headings=["Ticker","NCT trial","Company","Registry trial status",
    "ClinicalTrials.gov results count","Registry results classification","Registry snapshot date","ClinicalTrials.gov source"];
  const records=rows.map(row=>[
    row.ticker,row.nctId,row.company,row.registryStatus,row.resultsCount,
    kind==="before"?"NO_REGISTRY_RESULTS_POSTED":"REGISTRY_RESULTS_POSTED",
    "2026-10-18",row.sourceUrl
  ]);
  const csv="\ufeff"+[headings,...records].map(line=>line.map(safeCsvCell).join(",")).join("\r\n")+"\r\n";
  const blob=new Blob([csv],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;a.download="phase3-"+kind+"-registry-results-2026-10-18.csv";
  document.body.appendChild(a);a.click();a.remove();
  window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function TrialSection({kind,rows,query}:{kind:Kind;rows:readonly RegistryPostingRow[];query:string}){
  const [page,setPage]=useState(0);
  const searched=useMemo(()=>{
    const q=query.trim().toLowerCase();
    return !q?rows:rows.filter(row=>
      [row.nctId,row.ticker,row.company,row.registryStatus]
        .some(value=>value.toLowerCase().includes(q)));
  },[rows,query]);
  const pages=Math.ceil(searched.length/PAGE_SIZE);
  const active=Math.min(page,Math.max(pages-1,0));
  const pageRows=searched.slice(active*PAGE_SIZE,(active+1)*PAGE_SIZE);
  const before=kind==="before";
  return <section className={css.sheet} aria-label={before?"Top unposted registry results trial spreadsheet":"Bottom posted registry results trial spreadsheet"}>
    <div className={css.sheetHeader}>
      <div>
        <h3>{before?"TOP · PRE-RELEASE RESEARCH POOL":"BOTTOM · POST-RELEASE RESEARCH POOL"}</h3>
        <p><strong>{before?"No ClinicalTrials.gov results posted":"ClinicalTrials.gov results posted"}</strong>
          {" — "}{before?
            "Not proof that the company has not publicly released data.":
            "Registry results are public, but this does not establish the issuer announcement date."}</p>
      </div>
      <div className={css.sheetActions}>
        <strong>{fmt(rows.length)} trials{query?" · "+fmt(searched.length)+" matching":""}</strong>
        <button type="button" onClick={()=>exportCsv(kind,searched)}>Export all CSV</button>
      </div>
    </div>
    <div className={css.scroll} tabIndex={0} role="region" aria-label={before?"No registry results posted table":"Registry results posted table"}>
      <table>
        <thead>
          <tr><th>#</th><th>Ticker</th><th>NCT / Trial</th><th>Company</th>
            <th>Registry status</th><th>Registry results count</th>
            <th>Source (NCT)</th><th>Issuer announcement</th></tr>
        </thead>
        <tbody>{pageRows.length?pageRows.map((row,index)=><tr key={row.nctId}>
          <td>{active*PAGE_SIZE+index+1}</td>
          <td><strong>{row.ticker}</strong></td>
          <td><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">{row.nctId}</a></td>
          <td>{row.company}</td>
          <td>{row.registryStatus.replaceAll("_"," ")}</td>
          <td>{row.resultsCount}</td>
          <td><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov</a></td>
          <td>Not classified by this scan</td>
        </tr>):<tr><td colSpan={8} className={css.empty}>No records match this search.</td></tr>}</tbody>
      </table>
    </div>
    <div className={css.pager}>
      <span>{searched.length?"Showing "+fmt(active*PAGE_SIZE+1)+"–"+fmt(active*PAGE_SIZE+pageRows.length):"Showing 0"} of {fmt(searched.length)} trials · Page {pages?active+1:0} of {pages}</span>
      <div>
        <button type="button" disabled={active===0} onClick={()=>setPage(Math.max(0,active-1))}>Previous</button>
        <button type="button" disabled={pages===0||active>=pages-1} onClick={()=>setPage(active+1)}>Next</button>
      </div>
    </div>
  </section>;
}
export default function Phase3RegistryPostingSheets(){
  const [data,setData]=useState<RegistryPostingSnapshot|null>(null);
  const [error,setError]=useState("");
  const [query,setQuery]=useState("");
  useEffect(()=>{
    const ctrl=new AbortController();
    void fetch("/phase3-registry-postings-2026-10-18.json",{cache:"no-store",signal:ctrl.signal})
      .then(async response=>{
        if(!response.ok)throw Error("Snapshot unavailable");
        return parseRegistryPostingSnapshot(await response.json());
      })
      .then(snapshot=>{if(!ctrl.signal.aborted)setData(snapshot)})
      .catch(()=>{if(!ctrl.signal.aborted)setError("The 730-trial historical source snapshot could not be verified. Counts are unavailable.")});
    return ()=>ctrl.abort();
  },[]);
  return <section className={css.root} id="tools-phase3-registry-tables" aria-label="730 Phase 3 studies separated by whether registry results are posted">
    <header className={css.heading}>
      <h2>Phase 3 · Two Populated Trial Spreadsheets</h2>
      <p>Historical results-posting research · October 18, 2026 · $300M–$10B issuer-cap screen.</p>
    </header>
    {error?<p role="alert" className={css.warning}>{error}</p>
      :!data?<p role="status">Loading source-verified Phase 3 posting records…</p>:<>
      <div className={css.metrics} aria-label="Reconciled registry posting counts">
        <div><span>No registry results posted</span><strong>{fmt(data.before.length)}</strong></div>
        <div><span>Registry results posted</span><strong>{fmt(data.after.length)}</strong></div>
        <div><span>Total classified NCT records</span><strong>{fmt(data.total)}</strong></div>
      </div>
      <p className={css.warning}><strong>Important:</strong> These two tables reproduce the earlier 404 versus 326 ClinicalTrials.gov results-posting comparison. They are <strong>not</strong> verified issuer pre-release versus post-release totals. A company can announce results before they appear in the registry. Historical completed, terminated and withdrawn trials are retained. The separate October 26 census contains 741 trials, of which 722 overlap this 730-trial snapshot; 8 appear only here and 19 only in the newer census.</p>
      <div className={css.search}>
        <label htmlFor="phase3-postings-query">Search both spreadsheets by ticker, NCT, company or registry status</label>
        <div><input id="phase3-postings-query" type="search" value={query}
          onChange={event=>setQuery(event.target.value)} placeholder="Search 730 trials…" maxLength={100}/>
          <button type="button" onClick={()=>setQuery("")} disabled={!query}>Clear</button>
        </div>
      </div>
      <TrialSection key={"before|"+query} kind="before" rows={data.before} query={query}/>
      <TrialSection key={"after|"+query} kind="after" rows={data.after} query={query}/>
      <p className={css.source}>Source: <a href="https://github.com/pdufa/pdufa-command-center/blob/main/data/phase3_730_full_assessment.csv" target="_blank" rel="noopener noreferrer">730-trial October 18 saved assessment</a>. Each NCT links to ClinicalTrials.gov for current details. These are dated saved statuses, not live registry queries or FDA qualification decisions.</p>
    </>}
  </section>;
}
