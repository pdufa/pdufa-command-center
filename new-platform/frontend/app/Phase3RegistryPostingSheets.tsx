"use client";
import {useEffect,useMemo,useState} from "react";
import {
  parseRegistryPostingSnapshot,type RegistryPostingRow,type RegistryPostingSnapshot
} from "../lib/phase3-registry-posting";
import {
  EMPTY_POSTING_FILTERS,INITIAL_POSTING_SORT,filterAndSortPostingRows,postingFilterCount,
  type PostingFilters,type PostingSort,type PostingSortKey
} from "../lib/phase3-registry-posting-filters";
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
function TrialSection({kind,rows,query,snapshotDate}:{
  kind:Kind;rows:readonly RegistryPostingRow[];query:string;snapshotDate:string
}){
  const [page,setPage]=useState(0);
  const [filters,setFilters]=useState<PostingFilters>({...EMPTY_POSTING_FILTERS});
  const [sort,setSort]=useState<PostingSort>({...INITIAL_POSTING_SORT});
  const before=kind==="before";
  const label=before?"Before":"Past";
  const tickers=useMemo(()=>[...new Set(rows.map(r=>r.ticker))].sort((a,b)=>a.localeCompare(b)),[rows]);
  const statuses=useMemo(()=>[...new Set(rows.map(r=>r.registryStatus))].sort((a,b)=>a.localeCompare(b)),[rows]);
  const filtered=useMemo(()=>filterAndSortPostingRows(rows,query,filters,sort),[rows,query,filters,sort]);
  const filtersActive=postingFilterCount(filters);
  const pages=Math.ceil(filtered.length/PAGE_SIZE);
  const active=Math.min(page,Math.max(pages-1,0));
  const pageRows=filtered.slice(active*PAGE_SIZE,(active+1)*PAGE_SIZE);
  useEffect(()=>{setPage(0);},[query]);
  const changeFilter=(next:Partial<PostingFilters>)=>{
    setFilters(prev=>({...prev,...next}));setPage(0);
  };
  const resetFilters=()=>{setFilters({...EMPTY_POSTING_FILTERS});setSort({...INITIAL_POSTING_SORT});setPage(0);};
  const changeSort=(key:PostingSortKey)=>{
    setSort(prev=>({key,direction:prev.key===key&&prev.direction==="asc"?"desc":"asc"}));
    setPage(0);
  };
  const sorting=(key:PostingSortKey)=>
    sort.key!==key?"none":sort.direction==="asc"?"ascending":"descending";
  const sortable=(key:PostingSortKey,caption:string)=><button type="button"
    className={css.sortButton} onClick={()=>changeSort(key)}
    aria-label={"Sort "+label+" by "+caption+", "+(sort.key===key?sort.direction:"not sorted")}
    title={"Sort by "+caption}>
    {caption} <span className={css.sortIcon} aria-hidden="true">
      {sort.key!==key?"↕":sort.direction==="asc"?"↑":"↓"}
    </span>
  </button>;
  return <section className={css.sheet} aria-label={before?
      "Top unposted registry results trial spreadsheet":"Bottom posted registry results trial spreadsheet"}>
    <div className={css.sheetHeader}>
      <div>
        <h3>{before?"TOP · REGISTRY RESULTS NOT POSTED":"BOTTOM · REGISTRY RESULTS POSTED"}</h3>
        <p><strong>{before?"No ClinicalTrials.gov results posted":"ClinicalTrials.gov results posted"}</strong>
          {" — "}{before?
            "Not proof that the company has not publicly released data.":
            "Registry results are public, but this does not establish the issuer announcement date."}</p>
      </div>
      <div className={css.sheetActions}>
        <strong aria-live="polite">{fmt(rows.length)} total{query||filtersActive?
          " · "+fmt(filtered.length)+" matching":""}</strong>
        <button type="button" className={css.clearFilters} onClick={resetFilters}
          disabled={!filtersActive&&sort.key==="ticker"&&sort.direction==="asc"}>
          Clear column filters
        </button>
        <button type="button" disabled={!filtered.length}
          onClick={()=>exportCsv(kind,filtered,snapshotDate)}>
          Export {fmt(filtered.length)} matching CSV
        </button>
      </div>
    </div>
    <p className={css.filterHelp}>Filter each column below its heading, or tap a heading to sort.
      Filters apply together with the search above. Each spreadsheet has its own filters.</p>
    <div className={css.scroll} tabIndex={0} role="region"
      aria-label={before?"No registry results posted table":"Registry results posted table"}>
      <table>
        <thead>
          <tr className={css.headingRow}>
            <th scope="col">#</th>
            <th scope="col" aria-sort={sorting("ticker")}>{sortable("ticker","Ticker")}</th>
            <th scope="col" aria-sort={sorting("nctId")}>{sortable("nctId","NCT / Trial")}</th>
            <th scope="col" aria-sort={sorting("company")}>{sortable("company","Company")}</th>
            <th scope="col" aria-sort={sorting("registryStatus")}>{sortable("registryStatus","Registry status")}</th>
            <th scope="col" aria-sort={sorting("resultsCount")}>{sortable("resultsCount","Results posted?")}</th>
            <th scope="col" aria-sort={sorting("resultsFirstPostedDate")}>{sortable("resultsFirstPostedDate","First posted")}</th>
            <th scope="col">Source (NCT)</th>
            <th scope="col">Issuer announcement</th>
          </tr>
          <tr className={css.filterRow}>
            <th scope="col"><span className={css.filterPlaceholder}>Filters</span></th>
            <th scope="col"><select aria-label={label+" filter ticker"} value={filters.ticker}
              onChange={e=>changeFilter({ticker:e.target.value})}>
              <option value="">All tickers</option>
              {tickers.map(ticker=><option value={ticker} key={ticker}>{ticker}</option>)}
            </select></th>
            <th scope="col"><input type="search" aria-label={label+" filter NCT"} placeholder="Find NCT"
              value={filters.nctId} onChange={e=>changeFilter({nctId:e.target.value})} maxLength={40}/></th>
            <th scope="col"><input type="search" aria-label={label+" filter company"} placeholder="Find company"
              value={filters.company} onChange={e=>changeFilter({company:e.target.value})} maxLength={120}/></th>
            <th scope="col"><select aria-label={label+" filter registry status"} value={filters.registryStatus}
              onChange={e=>changeFilter({registryStatus:e.target.value})}>
              <option value="">All statuses</option>
              {statuses.map(status=><option value={status} key={status}>{status.replaceAll("_"," ")}</option>)}
            </select></th>
            <th scope="col"><select aria-label={label+" filter results posted"} value={filters.resultsPosted}
              onChange={e=>changeFilter({resultsPosted:e.target.value as PostingFilters["resultsPosted"]})}>
              <option value="all">All</option><option value="yes">Yes</option><option value="no">No</option>
            </select></th>
            <th scope="col"><div className={css.dateFilters}>
              <select aria-label={label+" filter first-posted date availability"} value={filters.datePresence}
                onChange={e=>changeFilter({datePresence:e.target.value as PostingFilters["datePresence"]})}>
                <option value="all">Any date</option><option value="dated">Date recorded</option>
                <option value="undated">No date</option>
              </select>
              <input type="date" aria-label={label+" first-posted from"} value={filters.from}
                max={filters.to||undefined} onChange={e=>changeFilter({from:e.target.value})}/>
              <input type="date" aria-label={label+" first-posted through"} value={filters.to}
                min={filters.from||undefined} onChange={e=>changeFilter({to:e.target.value})}/>
            </div></th>
            <th scope="col"><span className={css.filterPlaceholder}>Linked to NCT</span></th>
            <th scope="col"><span className={css.filterPlaceholder}>Unclassified</span></th>
          </tr>
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
        </tr>):<tr><td colSpan={9} className={css.empty}>No trials match these column filters or the overall search.</td></tr>}</tbody>
      </table>
    </div>
    <div className={css.pager}>
      <span>{filtered.length?"Showing "+fmt(active*PAGE_SIZE+1)+"–"+fmt(active*PAGE_SIZE+pageRows.length):"Showing 0"} of {fmt(filtered.length)} matching / {fmt(rows.length)} total trials · Page {pages?active+1:0} of {pages}
        {filtersActive?" · "+filtersActive+" active column filter"+(filtersActive===1?"":"s"):""}</span>
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
        <label htmlFor="phase3-postings-query">Search both spreadsheets by ticker, NCT, company, date or registry status</label>
        <div><input id="phase3-postings-query" type="search" value={query}
          onChange={event=>setQuery(event.target.value)} placeholder="Search trials…" maxLength={100}/>
          <button type="button" onClick={()=>setQuery("")} disabled={!query}>Clear</button>
        </div>
      </div>
      <TrialSection key="before" kind="before" rows={data.before} query={query} snapshotDate={data.date}/>
      <TrialSection key="after" kind="after" rows={data.after} query={query} snapshotDate={data.date}/>
      <p className={css.source}>Registry posting snapshot dated <strong>{data.date}</strong> · {data.fresh?"Automatic exact-NCT ClinicalTrials.gov refresh":"Historical static baseline; refresh pending"}. Source census: {data.sourceFile}. Each row links to its NCT source. The displayed registry status comes from the saved dated census, not a verified current FDA qualification. Page reload retrieves the latest successful snapshot.</p>
    </>}
  </section>;
}
