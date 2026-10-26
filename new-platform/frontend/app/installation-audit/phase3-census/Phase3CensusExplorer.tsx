"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import Phase3EvidenceDetails from "./Phase3EvidenceDetails";
import { buildPhase3EvidenceGapCsv, summarizePhase3EvidenceGaps, type PipelineCensusGapSummary } from "../../../lib/phase3-census-evidence-gaps";
import {
  parsePhase3CensusCsv, PHASE3_CENSUS_CSV_PATH,
  PHASE3_CENSUS_STATUS_VALUES,
  type Phase3CensusRegistryStatus, type Phase3CensusRows,
} from "../../../lib/phase3-census-rows";
import { PHASE3_CENSUS_SOURCES_PATH, parsePhase3CensusSourceDirectory, type Phase3CensusSourceDirectory } from "../../../lib/phase3-census-sources";

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
  const [rawSource, setRawSource] = useState("");
  const [gapSummary, setGapSummary] = useState<PipelineCensusGapSummary | null>(null);
  const [selectedNct, setSelectedNct] = useState<string | null>(null);
  const [sourceDirectory, setSourceDirectory] = useState<Phase3CensusSourceDirectory | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [response,directoryResponse] = await Promise.all([
          fetch(PHASE3_CENSUS_CSV_PATH, { cache:"no-store" }),
          fetch(PHASE3_CENSUS_SOURCES_PATH, { cache:"no-store" }),
        ]);
        if (!response.ok || !directoryResponse.ok) throw new Error("Saved research sources unavailable.");
        const [source,directoryValue] = await Promise.all([response.text(),directoryResponse.json()]);
        const data = parsePhase3CensusCsv(source);
        const gaps = summarizePhase3EvidenceGaps(data);
        const directory = parsePhase3CensusSourceDirectory(directoryValue,data);
        if (active) {
          setInventory(data);
          setGapSummary(gaps);
          setRawSource(source);
          setSourceDirectory(directory);
        }
      } catch {
        if (active) setError("Trial inventory not displayed: complete dated CSV and saved company source mappings could not be checked. No counts have been inferred.");
      }
    })();
    return () => { active = false; };
  }, []);

  function downloadUnverifiedEvidenceGaps() {
    if (!inventory || !rawSource || !gapSummary || !sourceDirectory) return;
    try {
      const csv = buildPhase3EvidenceGapCsv(rawSource,sourceDirectory);
      const url = URL.createObjectURL(new Blob([csv], { type:"text/csv;charset=utf-8" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "phase3_741_pipeline_evidence_gaps_NOT_QUALIFIED_2026-10-26.csv";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1500);
    } catch {
      setError("Evidence-gap export refused: source inventory is incomplete or inconsistent.");
      setRawSource("");
      setGapSummary(null);
      setInventory(null);
      setSourceDirectory(null);
    }
  }

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
      {gapSummary && <section aria-label="Pipeline evidence readiness across 741 research records"
        style={{padding:12,margin:"14px 0",border:"1px solid #cbd5e1",borderRadius:8,background:"#f8fafc"}}>
        <strong>Registry status groups: {gapSummary.registryOpenRecords} open ·
          {" "}{gapSummary.registryClosedRecords} completed/terminated/withdrawn ·
          {" "}{gapSummary.registryUnknownRecords} unknown.</strong>
        <p>All 741 records retain five missing independent source-evidence gates.
          Phase 3 identity and listed-company market-cap range are census-level matches,
          not fresh trial-by-trial qualification checks.
          Qualified Pipeline total: <strong>UNKNOWN</strong>.</p>
        <p><strong>Source-linked checklist:</strong> 741 exact NCT/ticker pairs linked to
          130 saved company filing and market-cap records, with original registry links
          and clearly labelled general FDA research entry points. The checklist identifies
          two structured rechecks, four document-reconciliation tasks and one rule-by-rule
          check per trial. These are checking methods; no fresh source recheck or FDA match is claimed.</p>
        <button type="button" onClick={downloadUnverifiedEvidenceGaps}>
          Download 741-row Pipeline evidence-gap checklist (CSV)
        </button>
      </section>}
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
            {["Clinical trial","Ticker","Exact matched company","Registry status","Original source","Evidence gaps"].map(h =>
              <th key={h} scope="col" style={{padding:11,borderBottom:"2px solid #cbd5e1",textAlign:"left"}}>{h}</th>)}
          </tr></thead>
          <tbody>{visible.map((row,i) => <Fragment key={row.nctId}><tr style={{background:i%2?"#f8fafc":"#fff"}}>
            <th scope="row" style={{textAlign:"left",padding:10,borderBottom:"1px solid #e2e8f0"}}>{row.nctId}</th>
            <td style={{padding:10,borderBottom:"1px solid #e2e8f0"}}>{row.ticker}</td>
            <td style={{padding:10,borderBottom:"1px solid #e2e8f0"}}>{row.company}</td>
            <td style={{padding:10,borderBottom:"1px solid #e2e8f0",whiteSpace:"nowrap"}}>{labelStatus(row.status)}</td>
            <td style={{padding:10,borderBottom:"1px solid #e2e8f0"}}>
              <a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov record</a>
            </td>
            <td style={{padding:10,borderBottom:"1px solid #e2e8f0"}}>
              <button type="button" aria-expanded={selectedNct===row.nctId} aria-controls={"evidence-"+row.nctId}
                onClick={() => setSelectedNct(selectedNct===row.nctId?null:row.nctId)}>
                {selectedNct===row.nctId?"Close checklist":"View seven evidence gates"}
              </button>
            </td>
          </tr>
          {selectedNct===row.nctId && sourceDirectory && <tr id={"evidence-"+row.nctId}>
            <td colSpan={6} style={{padding:12}}>
              <button type="button" onClick={() => setSelectedNct(null)}>Close evidence checklist</button>
              <Phase3EvidenceDetails trial={row} directory={sourceDirectory}/>
            </td>
          </tr>}
          </Fragment>)}</tbody>
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
