"use client";
import {useEffect,useMemo,useState} from "react";
import {parsePhase3CensusCsv} from "../lib/phase3-census-rows";
import {classifyPhase3Readouts,type ReadoutClassification,type ReadoutRow} from "../lib/phase3-public-readout";
import css from "./Phase3ReadoutSheets.module.css";

type Bucket="pre"|"post"|"unverified";
const LIMIT=50;
const number=(v:number)=>v.toLocaleString("en-US");
const txt=(v:string)=>v||"Not established";
function csvCell(v:string|number){
  const value=String(v??"");
  const safe=/^[=+@-]/.test(value)?"'"+value:value;
  return '"'+safe.replace(/"/g,'""')+'"';
}
function downloadCsv(bucket:Bucket,rows:ReadoutRow[]){
  const fields=["NCT","Ticker","Company","ClinicalTrials.gov status","Release classification","Evidence date","Drug","Indication","Release evidence","Registry link"];
  const table=[fields,...rows.map(row=>[
    row.nctId,row.ticker,row.company,row.status,
    bucket==="pre"?"No public issuer release verified as of source check":
      bucket==="post"?"Public issuer Phase 3 readout confirmed":"Unverified",
    row.evidence?.evidenceDate||"",row.evidence?.drug||"",row.evidence?.indication||"",
    row.evidence?.evidenceUrl||"",row.sourceUrl
  ])];
  const csv="\ufeff"+table.map(r=>r.map(csvCell).join(",")).join("\r\n")+"\r\n";
  const blob=new Blob([csv],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob);
  const anchor=document.createElement("a");
  anchor.href=url;anchor.download="phase3-"+bucket+"-readout-research.csv";
  document.body.append(anchor);anchor.click();anchor.remove();
  window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function TrialTable({rows,bucket}:{rows:ReadoutRow[];bucket:Bucket}){
  return <div className={css.tableScroll} role="region" aria-label={bucket+" Phase 3 trial spreadsheet"} tabIndex={0}>
    <table className={css.table}>
      <thead><tr>
        <th>#</th><th>Ticker</th><th>NCT / trial</th><th>Company</th>
        <th>Drug / therapy</th><th>Indication</th><th>Registered status</th>
        <th>{bucket==="pre"?"Source checked":bucket==="post"?"Public release date":"Public release"}</th><th>Source evidence</th>
      </tr></thead>
      <tbody>{rows.length?rows.map((row,i)=><tr key={row.nctId}>
        <td>{i+1}</td><td><strong>{row.ticker}</strong></td>
        <td><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">{row.nctId}</a></td>
        <td>{row.company}</td><td>{txt(row.evidence?.drug||"")}</td>
        <td>{txt(row.evidence?.indication||"")}</td><td>{row.status.replaceAll("_"," ")}</td>
        <td>{row.evidence?.evidenceDate||"Not verified"}</td>
        <td>{row.evidence
          ? <a href={row.evidence.evidenceUrl} target="_blank" rel="noopener noreferrer">
            {bucket==="pre"?"Dated issuer check":"Public readout source"}</a>
          : "Not verified"}</td>
      </tr>):<tr><td colSpan={9} className={css.empty}>No documented matches in this view. Unknown-release trials are not counted as pre-release.</td></tr>}</tbody>
    </table>
  </div>;
}
function Spreadsheet({bucket,rows,query,caption}:{bucket:"pre"|"post";rows:ReadoutRow[];query:string;caption:string}){
  const matched=useMemo(()=>{
    const q=query.trim().toLowerCase();
    return !q?rows:rows.filter(x=>
      [x.nctId,x.ticker,x.company,x.evidence?.drug||"",x.evidence?.indication||""]
        .some(field=>field.toLowerCase().includes(q)));
  },[rows,query]);
  const pre=bucket==="pre";
  return <section className={css.sheet} aria-label={pre?"Top pre-release spreadsheet":"Bottom post-release spreadsheet"}>
    <div className={css.sheetHeading}>
      <div>
        <h3>{pre?"TOP SPREADSHEET · PRE-RELEASE":"BOTTOM SPREADSHEET · POST-RELEASE"}</h3>
        <p>{caption}</p>
      </div>
      <div className={css.actions}>
        <strong>{number(rows.length)} documented trials{query?" · "+matched.length+" matching":""}</strong>
        <button type="button" onClick={()=>downloadCsv(bucket,matched)}>Export CSV</button>
      </div>
    </div>
    <TrialTable rows={matched} bucket={bucket}/>
  </section>;
}
/** Full historical issuer-cap census with dated issuer readouts, never registry-result proxy. */
export default function Phase3ReadoutSheets(){
  const [data,setData]=useState<ReadoutClassification|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [query,setQuery]=useState("");
  const [unknownPage,setUnknownPage]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();
    Promise.all([
      fetch("/phase3-census-2026-10-26.csv",{cache:"no-store",signal:controller.signal}),
      fetch("/phase3-public-readout-evidence-2026-11-01.json",{cache:"no-store",signal:controller.signal})
    ]).then(async ([census,evidence])=>{
      if(!census.ok||!evidence.ok)throw Error("Published sources unavailable.");
      const censusData=parsePhase3CensusCsv(await census.text());
      const result=classifyPhase3Readouts(await evidence.json(),censusData.rows);
      return result;
    }).then(result=>{if(!controller.signal.aborted)setData(result);})
      .catch(()=>{if(!controller.signal.aborted)setError("Release-classification evidence could not be validated. No counts asserted.");})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[]);
  const unknown=useMemo(()=>{
    const q=query.trim().toLowerCase();
    return data?.unverified.filter(x=>!q||
      [x.nctId,x.ticker,x.company,x.status].some(s=>s.toLowerCase().includes(q)))||[];
  },[data,query]);
  const pages=Math.ceil(unknown.length/LIMIT);
  const activePage=Math.min(unknownPage,Math.max(0,pages-1));
  if(loading)return <section className={css.root} role="status">Loading dated Phase 3 release spreadsheets…</section>;
  if(error||!data)return <section className={css.root} role="alert">{error||"Readout research unavailable"}</section>;
  return <section className={css.root} id="tools-phase3-release-sheets" aria-label="Pre-release and post-release Phase 3 spreadsheets">
    <div className={css.title}>
      <h2>Phase 3 · Public Data Release</h2>
      <p>Two independent, source-linked spreadsheets from the {number(data.total)}-trial October 26, 2026 historical $300M–$10B issuer-cap census. Counted by distinct NCT, not by company or indication.</p>
    </div>
    <div className={css.metrics}>
      <div><span>Pre-release · as last checked</span><strong>{number(data.pre.length)}</strong></div>
      <div><span>Post-release · documented</span><strong>{number(data.post.length)}</strong></div>
      <div><span>Release not established</span><strong>{number(data.unverified.length)}</strong></div>
    </div>
    <p className={css.caveat}><strong>Important:</strong> Pre-release means no issuer readout was identified at a dated source check (October 11, 2026); it is not a guarantee that the study is still unreleased today. Post-release requires a source-backed public Phase 3 announcement. ClinicalTrials.gov results-posting and “COMPLETED” status alone do not establish either category. This is historical research, not a current PDUFA-qualified or stock-buy list.</p>
    <label className={css.searchLabel} htmlFor="phase3-readout-search">Find an NCT, ticker, company, drug or indication across both spreadsheets</label>
    <div className={css.searchRow}>
      <input id="phase3-readout-search" type="search" value={query}
        onChange={e=>{setQuery(e.target.value);setUnknownPage(0)}}
        placeholder="Search trials…" maxLength={90}/>
      <button type="button" onClick={()=>{setQuery("");setUnknownPage(0)}} disabled={!query}>Clear</button>
    </div>
    <Spreadsheet bucket="pre" rows={data.pre} query={query}
      caption="Trials without a documented issuer public release at their source-check date. Each row retains the check date and issuer link."/>
    <Spreadsheet bucket="post" rows={data.post} query={query}
      caption="Trials with a documented company public Phase 3 results announcement, including release date and original source."/>
    <details className={css.unverified}>
      <summary><strong>Release status not verified · {number(data.unverified.length)} trials</strong> <span>Expand for research queue</span></summary>
      <div className={css.pendingBody}>
        <p>These NCTs are neither assumed pre-release nor post-release. They require dated issuer announcement searches or other direct public-results evidence. A missing registry posting is not evidence of an unreleased readout.</p>
        <div className={css.actions}>
          <strong>{number(unknown.length)} matching unverified NCTs</strong>
          <button type="button" onClick={()=>downloadCsv("unverified",unknown)}>Export unverified CSV</button>
        </div>
        <div className={css.tableScroll} role="region" aria-label="Unverified Phase 3 readout research queue" tabIndex={0}>
          <table className={css.table}>
            <thead><tr><th>NCT</th><th>Ticker</th><th>Company</th><th>Registry status</th><th>Public readout</th></tr></thead>
            <tbody>{unknown.slice(activePage*LIMIT,(activePage+1)*LIMIT).map(row=><tr key={row.nctId}>
              <td><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">{row.nctId}</a></td>
              <td>{row.ticker}</td><td>{row.company}</td><td>{row.status.replaceAll("_"," ")}</td>
              <td>Not verified — research required</td>
            </tr>)}</tbody>
          </table>
        </div>
        <div className={css.pagination}>
          <button type="button" disabled={activePage===0} onClick={()=>setUnknownPage(n=>Math.max(0,n-1))}>Previous 50</button>
          <span>Page {pages?activePage+1:0} of {pages}</span>
          <button type="button" disabled={activePage>=pages-1} onClick={()=>setUnknownPage(n=>n+1)}>Next 50</button>
        </div>
      </div>
    </details>
    <p className={css.footer}>Dated source files: {data.sourceFiles.join(" and ")}. Classification research snapshot: {data.sourceAsOf}. Unverified does not mean unreleased, and all counts remain limited by the 741-trial issuer-cap research census.</p>
  </section>;
}
