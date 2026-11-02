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
function exportCsv(kind:Kind,rows:readonly RegistryPostingRow[],snapshotDate:string){
  const headings=["Ticker","NCT trial","Company","Registry trial status",
    "Registry results posted","Results first-posted date","Registry classification","Registry checked on","ClinicalTrials.gov source"];
  const records=rows.map(row=>[
    row.ticker,row.nctId,row.company,row.registryStatus,
    row.resultsCount>0?"YES":"NO",row.resultsFirstPostedDate||"",
    kind==="before"?"NO_REGISTRY_RESULTS_POSTED":"REGISTRY_RESULTS_POSTED",
    snapshotDate,row.sourceUrl
  ]);
  const csv="\ufeff"+[headings,...records].map(line=>line.map(safeCsvCell).join(",")).join("\r\n")+"\r\n";
  const blob=new Blob([csv],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;a.download="phase3-"+kind+"-registry-results-"+snapshotDate+".csv";
  document.body.appendChild(a);a.click();a.remove();
  window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function TrialSection({kind,rows,query,snapshotDate}:{kind:Kind;rows:readonly RegistryPostingRow[];query:string;snapshotDate:string}){
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
        <h3>{before?"TOP · REGISTRY RESULTS NOT POSTED":"BOTTOM · REGISTRY RESULTS POSTED"}</h3>
        <p><strong>{before?"No ClinicalTrials.gov results posted":"ClinicalTrials.gov results posted"}</strong>
          {" — "}{before?
            "Not proof that the company has not publicly released data.":
            "Registry results are public, but this does not establish the issuer announcement date."}</p>
      </div>
      <div className={css.sheetActions}>
        <strong>{fmt(rows.length)} trials{query?" · "+fmt(searched.length)+" matching":""}</strong>
        <button type="button" onClick={()=>exportCsv(kind,searched,snapshotDate)}>Export all CSV</button>
      </div>
    </div>
    <div className={css.scroll} tabIndex={0} role="region" aria-label={before?"No registry results posted table":"Registry results posted table"}>
      <table>
        <thead>
          <tr><th>#</th><th>Ticker</th><th>NCT / Trial</th><th>Company</th>
            <th>Registry status</th><th>Results posted?</th><th>First posted</th>
            <th>Source (NCT)</th><th>Issuer announcement</th></tr>
        </thead>
        <tbody>{pageRows.length?pageRows.map((row,index)=><tr key={row.nctId}>
          <td>{active*PAGE_SIZE+index+1}</td>
          <td><strong>{row.ticker}</strong></td>
          <td><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">{row.nctId}</a></td>
          <td>{row.company}</td>
          <td>{row.registryStatus.replaceAll("_"," ")}</td>
          <td>{row.resultsCount>0?"Yes":"No"}</td>
          <td>{row.resultsFirstPostedDate||(row.resultsCount>0?"Legacy scan: date unavailable":"Not posted")}</td>
          <td><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov</a></td>
          <td>Not classified by this scan</td>
        </tr>):<tr><td colSpan={9} className={css.empty}>No records match this search.</td></tr>}</tbody>
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
    void fetch("/phase3-registry-postings-current.json",{cache:"no-store",signal:ctrl.signal})
      .then(async response=>{
        // Preserve the original 730-trial view until the first complete scan
        // publishes a reconciled current registry snapshot. Never combine them.
        if(response.ok)return parseRegistryPostingSnapshot(await response.json());
        const fallback=await fetch("/phase3-registry-postings-2026-10-18.json",{cache:"no-store",signal:ctrl.signal});
        if(!fallback.ok)throw Error("No complete registry snapshot available");
        return parseRegistryPostingSnapshot(await fallback.json());
      })
      .then(snapshot=>{if(!ctrl.signal.aborted)setData(snapshot)})
      .catch(()=>{if(!ctrl.signal.aborted)setError("The saved Phase 3 results-posting snapshot could not be verified. Counts are unavailable.")});
    return ()=>ctrl.abort();
  },[]);
  return <section className={css.root} id="tools-phase3-registry-tables" aria-label="Phase 3 studies separated by whether registry results are posted">
    <header className={css.heading}>
      <h2>Phase 3 · Two Populated Trial Spreadsheets</h2>
      <p>Results-posting research · $300M–$10B issuer-cap screen · automatically refreshed after complete registry downloads.</p>
    </header>
    {error?<p role="alert" className={css.warning}>{error}</p>
      :!data?<p role="status">Loading source-verified Phase 3 posting records…</p>:<>
      <div className={css.metrics} aria-label="Reconciled registry posting counts">
        <div><span>No registry results posted</span><strong>{fmt(data.before.length)}</strong></div>
        <div><span>Registry results posted</span><strong>{fmt(data.after.length)}</strong></div>
        <div><span>Total classified NCT records</span><strong>{fmt(data.total)}</strong></div>
      </div>
      <p className={css.warning}><strong>Important:</strong> These are ClinicalTrials.gov <em>results-posting</em> categories, <strong>not</strong> verified company-announcement pre-release versus post-release totals. A company may announce before posting registry results. Historical, completed, terminated and withdrawn NCTs are retained. {data.fresh?"The latest complete, exact-NCT registry refresh covers "+fmt(data.total)+" trials; issuer-cap membership remains tied to the dated underlying census.":"Showing the October 18 historical 730-trial baseline (404/326), which differs from the newer 741-trial census. Automatic source refresh has not yet published; do not interpret these counts as current."}</p>
      <div className={css.search}>
        <label htmlFor="phase3-postings-query">Search both spreadsheets by ticker, NCT, company or registry status</label>
        <div><input id="phase3-postings-query" type="search" value={query}
          onChange={event=>setQuery(event.target.value)} placeholder="Search trials…" maxLength={100}/>
          <button type="button" onClick={()=>setQuery("")} disabled={!query}>Clear</button>
        </div>
      </div>
      <TrialSection key={"before|"+query} kind="before" rows={data.before} query={query} snapshotDate={data.date}/>
      <TrialSection key={"after|"+query} kind="after" rows={data.after} query={query} snapshotDate={data.date}/>
      <p className={css.source}>Registry posting snapshot dated <strong>{data.date}</strong> · {data.fresh?"Automatic exact-NCT ClinicalTrials.gov refresh":"Historical static baseline; refresh pending"}. Source census: {data.sourceFile}. Each row links to its NCT source. The displayed registry status comes from the saved dated census, not a verified current FDA qualification. Page reload retrieves the latest successful snapshot.</p>
    </>}
  </section>;
}
