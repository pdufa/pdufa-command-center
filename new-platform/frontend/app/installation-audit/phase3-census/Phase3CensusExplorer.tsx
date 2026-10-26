"use client";

import { useEffect, useMemo, useState } from "react";
import {
  parsePhase3CensusCsv, PHASE3_CENSUS_CSV_PATH,
  PHASE3_CENSUS_STATUS_VALUES,
  type Phase3CensusRegistryStatus, type Phase3CensusRows,
} from "../../../lib/phase3-census-rows";

const PAGE_SIZE = 35;
const labelStatus = (value: string) => value.replaceAll("_", " ").toLowerCase()
  .replace(/\b\w/g, letter => letter.toUpperCase());

/** Public, cached static data only. No calls to scoring, enrollment or trading. */
export default function Phase3CensusExplorer() {
  const [inventory, setInventory] = useState<Phase3CensusRows | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"ALL" | Phase3CensusRegistryStatus>("ALL");
  const [page, setPage] = useState(0);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const response = await fetch(PHASE3_CENSUS_CSV_PATH, { cache: "no-store" });
        if (!response.ok) throw new Error("CSV source unavailable.");
        const data = parsePhase3CensusCsv(await response.text());
        if (active) setInventory(data);
      } catch {
        if (active) setError("Trial inventory not displayed: complete dated CSV could not be checked. No counts have been inferred.");
      }
    })();
    return () => { active = false; };
  }, []);

  const matches = useMemo(() => {
    if (!inventory) return [];
    const find = query.trim().toLocaleLowerCase();
    return inventory.rows.filter(row =>
      (status === "ALL" || row.status === status) &&
      (!find || (row.nctId + " " + row.ticker + " " + row.company)
        .toLocaleLowerCase().includes(find)),
    );
  }, [inventory, query, status]);
  const pages = Math.max(1, Math.ceil(matches.length / PAGE_SIZE));
  const currentPage = Math.min(page, pages - 1);
  const visible = matches.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE);

  return <section aria-label="741 Phase 3 research trial records" style={{marginTop:22}}>
    <p><strong>Qualified Pipeline: NOT ESTABLISHED.</strong> Results below are
      historical registry status records for exact industry lead sponsors, not
      verified active programs, FDA/PDUFA candidates, scientific grades or trade signals.</p>
    <p><a href={PHASE3_CENSUS_CSV_PATH} download>
      Download complete dated 741-row research CSV</a> · <a
      href="https://github.com/pdufa/pdufa-command-center/blob/main/data/phase3_all_years_300m_10b_status.json"
      target="_blank" rel="noopener noreferrer">Source scope and caveats</a></p>
    {error && <p role="alert">{error}</p>}
    {!inventory && !error && <p role="status">Checking complete dated research inventory…</p>}
    {inventory && <>
      <p><strong>{inventory.rows.length.toLocaleString("en-US")} records verified against
        the dated CSV structure · {inventory.uniqueCompanies} unique tickers.</strong></p>
      <div style={{display:"flex",flexWrap:"wrap",gap:12,margin:"18px 0"}}>
        <label style={{display:"grid",gap:5,flex:"1 1 200px"}}>
          Search NCT, ticker or company
          <input type="search" value={query}
            onChange={event => {setQuery(event.target.value);setPage(0);}}
            placeholder="e.g. NCT02142738 or ACAD"
            style={{padding:10,border:"1px solid #94a3b8",borderRadius:7,fontSize:16}}/>
        </label>
        <label style={{display:"grid",gap:5,flex:"1 1 200px"}}>
          ClinicalTrials.gov study status
          <select value={status} onChange={event => {
            setStatus(event.target.value as "ALL" | Phase3CensusRegistryStatus);
            setPage(0);
          }} style={{padding:10,border:"1px solid #94a3b8",borderRadius:7,fontSize:16}}>
            <option value="ALL">All statuses ({inventory.rows.length})</option>
            {PHASE3_CENSUS_STATUS_VALUES.map(code => <option value={code} key={code}>
              {labelStatus(code)} ({inventory.statusCounts[code]})
            </option>)}
          </select>
        </label>
      </div>
      <p role="status"><strong>{matches.length}</strong> matching historical trial records.
        Showing {matches.length ? currentPage * PAGE_SIZE + 1 : 0}–
        {Math.min((currentPage + 1) * PAGE_SIZE, matches.length)}.
        A recruiting label does not confirm sponsor funding, program viability or a PDUFA date.</p>
      <div style={{overflowX:"auto",border:"1px solid #cbd5e1",borderRadius:8}}>
        <table style={{width:"100%",borderCollapse:"collapse",minWidth:620,fontSize:14}}>
          <thead><tr style={{background:"#f1f5f9"}}>
            {["Clinical trial","Ticker","Exact matched company","Registry status","Original source"].map(h =>
              <th key={h} scope="col" style={{padding:11,borderBottom:"2px solid #cbd5e1",textAlign:"left"}}>{h}</th>)}
          </tr></thead>
          <tbody>{visible.map((row,i) => <tr key={row.nctId} style={{background:i%2?"#f8fafc":"#fff"}}>
            <th scope="row" style={{textAlign:"left",padding:10,borderBottom:"1px solid #e2e8f0"}}>{row.nctId}</th>
            <td style={{padding:10,borderBottom:"1px solid #e2e8f0"}}>{row.ticker}</td>
            <td style={{padding:10,borderBottom:"1px solid #e2e8f0"}}>{row.company}</td>
            <td style={{padding:10,borderBottom:"1px solid #e2e8f0",whiteSpace:"nowrap"}}>{labelStatus(row.status)}</td>
            <td style={{padding:10,borderBottom:"1px solid #e2e8f0"}}>
              <a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov record</a>
            </td>
          </tr>)}</tbody>
        </table>
        {!visible.length && <p style={{padding:12}}>No trial records match these filters.</p>}
      </div>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:12,marginTop:14}}>
        <button type="button" onClick={() => setPage(Math.max(0,currentPage-1))}
          disabled={currentPage === 0}>Previous records</button>
        <span>Page {currentPage+1} of {pages}</span>
        <button type="button" onClick={() => setPage(currentPage+1)}
          disabled={currentPage+1 >= pages}>Next records</button>
      </div>
      <p><small>Read-only. Source census generated October 26, 2026.
        No trial is automatically qualified, enrolled or scored, and no
        Pipeline restrictions, GEM JR/GEM/WT memberships, scans or trades are changed.</small></p>
    </>}
  </section>;
}
