"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Candidate } from "./Workspace";
import TrialFields from "./TrialFields";
import { pageRows, trialId } from "../lib/pipeline-data";

type TrialSummary = {
  study_title?: string; status?: string; phases?: string[];
  primary_completion_date?: { date?: string; type?: string };
  last_update_posted?: { date?: string }; has_results?: boolean;
  statistical_analyses?: number; p_value_count?: number; p_value_status?: string;
};
type Summaries = { ids: string; records: Record<string, TrialSummary> };

export default function PipelineData({ rows }: { rows: Candidate[] }) {
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(25);
  const [selected, setSelected] = useState("");
  const [summaries, setSummaries] = useState<Summaries>({ ids: "", records: {} });
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const detailsRef = useRef<HTMLDivElement>(null);
  const ordered = useMemo(() => [...rows].sort((a, b) =>
    a.ticker.localeCompare(b.ticker) || (a.drug || "").localeCompare(b.drug || "") || a.id.localeCompare(b.id)
  ), [rows]);
  const current = pageRows(ordered, page, size);
  const ids = [...new Set(current.rows.map(trialId).filter(Boolean))].sort().join(",");
  const selectedRow = current.rows.find(row => row.id === selected);

  useEffect(() => {
    if (selected) detailsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [selected]);

  useEffect(() => {
    if (!ids) return;
    const controller = new AbortController();
    async function load() {
      setError("");
      try {
        const response = await fetch("/api/full-trials/rows?ids=" + encodeURIComponent(ids), { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error("Saved registry summaries are unavailable. Pipeline rows remain listed below.");
        const data = await response.json() as { records: Record<string, TrialSummary> };
        if (!controller.signal.aborted) setSummaries({ ids, records: data.records });
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Unable to load registry summaries.");
      }
    }
    void load();
    return () => controller.abort();
  }, [ids, retry]);

  function navigate(next: number) { setPage(next); setSelected(""); }
  const enriched = summaries.ids === ids ? summaries.records : {};
  const loading = Boolean(ids && summaries.ids !== ids && !error);
  return <section className="panel pipeline-data" aria-labelledby="pipeline-data-title">
    <div className="sectionhead"><div><h3 id="pipeline-data-title">PIPELINE DATA</h3>
      <p className="subtle">Matches the checked stages and all other Pipeline filters. No checked stages means all stages. Select <strong>All fields</strong> to browse each complete record.</p></div>
      <span className="counter" aria-live="polite">{rows.length.toLocaleString("en-US")} matching trials / programs</span>
    </div>
    <div className="pipeline-data-pagination">
      <p role="status">Showing {current.start.toLocaleString("en-US")}–{current.end.toLocaleString("en-US")} of {rows.length.toLocaleString("en-US")}{loading ? " · Loading registry summaries…" : ""}</p>
      <label>Rows per page <select value={size} onChange={event => { setSize(Number(event.target.value)); navigate(0); }}><option value={25}>25</option><option value={50}>50</option></select></label>
      <div className="pipeline-actions">
        <button type="button" className="secondary" disabled={current.page === 0} onClick={() => navigate(current.page - 1)}>Previous</button>
        <span>Page {current.page + 1} / {current.pages}</span>
        <button type="button" className="secondary" disabled={current.page + 1 >= current.pages} onClick={() => navigate(current.page + 1)}>Next</button>
      </div>
    </div>
    {error && <div role="alert" className="pipeline-data-error"><span className="error">{error}</span> <button type="button" className="secondary" onClick={() => setRetry(value => value + 1)}>Retry summaries</button></div>}
    {rows.length ? <div className="table-scroll pipeline-data-scroll"><table>
      <caption className="visually-hidden">Filtered Pipeline trials and programs. The matching count uses the same records as the phase and date totals.</caption>
      <thead><tr><th>#</th><th>Program ID</th><th>Ticker / company</th><th>Drug / study</th><th>Indication</th><th>Pipeline stage</th><th>NCT ID</th><th>Trial status</th><th>Primary completion</th><th>PDUFA</th><th>Market cap</th><th>Registry p-values</th><th>All data</th></tr></thead>
      <tbody>{current.rows.map((row, index) => {
        const nct = trialId(row), saved = enriched[nct];
        const active = selected === row.id;
        return <tr key={row.id} className={active ? "selected-record" : ""}>
          <td>{current.start + index}</td><td className="permanent-id">{row.programId || "Not assigned"}</td>
          <td><strong>{row.ticker}</strong><small>{row.company}</small></td>
          <td className="pipeline-study-cell"><strong>{row.drug || saved?.study_title || "Not reported"}</strong>{saved?.study_title && <small>{saved.study_title}</small>}</td>
          <td className="pipeline-study-cell">{row.indication || "Not reported"}</td><td>{row.stage || "Unknown"}</td>
          <td>{nct ? <a href={"https://clinicaltrials.gov/study/" + nct} target="_blank" rel="noopener noreferrer">{nct} ↗</a> : "No linked trial"}</td>
          <td>{saved?.status?.replaceAll("_", " ") || (nct ? loading ? "Loading…" : "Not available" : "Regulatory program")}</td>
          <td>{saved?.primary_completion_date?.date || "Not reported"}<small>{saved?.primary_completion_date?.type}</small></td>
          <td>{row.pdufaDate || "Not reported"}</td><td>{row.marketCap == null ? "Not verified" : "$" + (row.marketCap / (row.marketCap >= 1e9 ? 1e9 : 1e6)).toFixed(1) + (row.marketCap >= 1e9 ? "B" : "M")}</td>
          <td>{saved ? <><strong>{saved.p_value_count || 0} reported</strong><small>{saved.p_value_status?.replaceAll("_", " ")}</small></> : nct && loading ? "Loading…" : "Not available"}</td>
          <td><button type="button" className="secondary" aria-expanded={active} aria-controls={active ? "pipeline-expanded-record" : undefined} onClick={() => setSelected(active ? "" : row.id)}>{active ? "Close fields" : "All fields"}</button></td>
        </tr>;
      })}</tbody>
    </table></div> : <p className="pipeline-data-empty">No trials or programs match these filters. Uncheck a stage or date filter, or clear the search to broaden the list. No checked stages means all stages.</p>}
    <div className="pipeline-data-pagination pipeline-data-footer"><span>Phase total · {rows.length.toLocaleString("en-US")}</span><div className="pipeline-actions">
      <button type="button" className="secondary" disabled={current.page === 0} onClick={() => navigate(current.page - 1)}>Previous</button>
      <button type="button" className="secondary" disabled={current.page + 1 >= current.pages} onClick={() => navigate(current.page + 1)}>Next</button>
    </div></div>
    {selectedRow && <div id="pipeline-expanded-record" ref={detailsRef}><TrialFields key={selectedRow.id} row={selectedRow} onClose={() => setSelected("")} /></div>}
  </section>;
}
