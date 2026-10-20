"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Candidate } from "./Workspace";
import TrialFields from "./TrialFields";
import CandidateAssessments, { AssessmentCells, AssessmentHeaders, AssessmentSort, AssessmentStatus, useAssessments } from "./CandidateAssessments";
import { sortByAssessment } from "../lib/candidate-assessments";
import { needsRegistrySort, pageRows, sortPipelineRows, trialId, type PipelineSort, type PipelineSortKey, type RegistrySortIndex } from "../lib/pipeline-data";

const HEADERS: { label: string; key?: PipelineSortKey; sortLabel?: string }[] = [
  { label: "#" }, { label: "Program ID", key: "programId" },
  { label: "Ticker / company", key: "ticker", sortLabel: "ticker" },
  { label: "Drug / study" }, { label: "Indication" }, { label: "Registered phase", key: "registeredPhase" }, { label: "Pipeline stage", key: "stage" },
  { label: "NCT ID", key: "nctId" }, { label: "Trial status", key: "status" },
  { label: "Primary completion", key: "primaryCompletion" }, { label: "PDUFA", key: "pdufaDate" },
  { label: "Priority Review" },
  { label: "Market cap", key: "marketCap" },
  { label: "Registry p-values", key: "pValueCount", sortLabel: "number of reported p-values" },
  { label: "All data" },
];

type TrialSummary = {
  study_title?: string; status?: string; phases?: string[];
  primary_completion_date?: { date?: string; type?: string };
  last_update_posted?: { date?: string }; has_results?: boolean;
  statistical_analyses?: number; p_value_count?: number; p_value_status?: string;
};
type Summaries = { ids: string; records: Record<string, TrialSummary> };

export default function PipelineData({ rows, filterSummary }: { rows: Candidate[]; filterSummary?: string }) {
  const [page, setPage] = useState(0);
  const [scoreOrder, setScoreOrder] = useState("source");
  const { records: assessmentRecords } = useAssessments();
  const [size, setSize] = useState(25);
  const [selected, setSelected] = useState("");
  const [summaries, setSummaries] = useState<Summaries>({ ids: "", records: {} });
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [sort, setSort] = useState<PipelineSort>({ key: "ticker", direction: "asc" });
  const [sortIndex, setSortIndex] = useState<RegistrySortIndex | null>(null);
  const [sortLoading, setSortLoading] = useState<PipelineSortKey | null>(null);
  const [sortError, setSortError] = useState("");
  const sortController = useRef<AbortController | null>(null);
  const detailsRef = useRef<HTMLDivElement>(null);
  const ordered = useMemo(() => sortByAssessment(sortPipelineRows(rows, sort, sortIndex || {}), assessmentRecords, "PIPELINE", scoreOrder), [rows, sort, sortIndex, assessmentRecords, scoreOrder]);
  const current = pageRows(ordered, page, size);
  const ids = [...new Set(current.rows.map(trialId).filter(Boolean))].sort().join(",");
  const selectedRow = current.rows.find(row => row.id === selected);

  useEffect(() => {
    if (selected) detailsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [selected]);

  useEffect(() => () => sortController.current?.abort(), []);

  async function changeSort(key: PipelineSortKey) {
    if (sortLoading) return;
    const next: PipelineSort = { key, direction: sort.key === key && sort.direction === "asc" ? "desc" : "asc" };
    setSortError("");
    if (needsRegistrySort(key) && !sortIndex) {
      const controller = new AbortController();
      sortController.current = controller;
      setSortLoading(key);
      try {
        const response = await fetch("/api/full-trials/sort-index", { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error("Unable to load registry sorting data. Click the column header to retry.");
        const data = await response.json() as { records: RegistrySortIndex };
        if (!data.records || typeof data.records !== "object" || Array.isArray(data.records)) throw new Error("Registry sorting data is unavailable.");
        if (controller.signal.aborted) return;
        setSortIndex(data.records);
      } catch (cause) {
        if (!controller.signal.aborted) setSortError(cause instanceof Error ? cause.message : "Unable to sort registry fields.");
        return;
      } finally { if (!controller.signal.aborted) setSortLoading(null); }
    }
    setSort(next); setScoreOrder("source"); setPage(0); setSelected("");
  }

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
  return <section className="panel pipeline-data" aria-labelledby="pipeline-data-title" aria-busy={sortLoading !== null}>
    <div className="sectionhead"><div><h3 id="pipeline-data-title">PIPELINE DATA</h3>
      <p className="subtle">Results from DISPLAY TRIALS. Select a linked trial or <strong>Full sheet</strong> to open its saved complete record in a new browser tab. Programs without an NCT retain inline fields.</p>
      {filterSummary && <p className="subtle pipeline-applied-filters">{filterSummary}</p>}</div>
      <span className="counter" aria-live="polite">{rows.length.toLocaleString("en-US")} matching trials / programs</span>
    </div>
    <AssessmentStatus stage="PIPELINE" />
    <AssessmentSort value={scoreOrder} onChange={value => { setScoreOrder(value); setPage(0); setSelected(""); }} />
    <p className="subtle small">Click a column heading to sort all matching trials; click again to reverse the order.</p>
    {sortLoading && <p role="status" className="pipeline-sort-status">Preparing {HEADERS.find(column => column.key === sortLoading)?.label.toLowerCase()} sorting for the complete list…</p>}
    {sortError && <p role="alert" className="error">{sortError}</p>}
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
      <thead><tr>{HEADERS.map(column => {
        const key = column.key, active = key === sort.key;
        return <th key={column.label} aria-sort={key ? active ? sort.direction === "asc" ? "ascending" : "descending" : "none" : undefined}>
          {key ? <button type="button" className="pipeline-sort-button" disabled={sortLoading !== null}
            title={"Sort by " + (column.sortLabel || column.label.toLowerCase())}
            aria-label={"Sort by " + (column.sortLabel || column.label.toLowerCase()) + ", " + (active && sort.direction === "asc" ? "descending" : "ascending")}
            onClick={() => void changeSort(key)}>{column.label}<span aria-hidden="true">{active ? sort.direction === "asc" ? "▲" : "▼" : "↕"}</span></button> : column.label}
        </th>;
      })}<AssessmentHeaders stage="PIPELINE" /></tr></thead>
      <tbody>{current.rows.map((row, index) => {
        const nct = trialId(row), saved = enriched[nct];
        const active = selected === row.id;
        return <tr key={row.id} className={active ? "selected-record" : ""}>
          <td>{current.start + index}</td><td className="permanent-id">{row.programId || "Not assigned"}</td>
          <td><strong>{row.ticker}</strong><small>{row.company}</small></td>
          <td className="pipeline-study-cell"><strong>{nct ?
            <a className="trial-sheet-link" href={"/trial/" + nct} target="_blank" rel="noopener noreferrer">{row.drug || saved?.study_title || nct} ↗</a> :
            row.drug || saved?.study_title || "Not reported"}</strong>{saved?.study_title && <small>{saved.study_title}</small>}</td>
          <td className="pipeline-study-cell">{row.indication || "Not reported"}</td><td>{row.trialFilters?.registeredPhase || "Unknown"}</td><td>{row.stage || "Unknown"}</td>
          <td>{nct ? <a className="trial-sheet-link" href={"/trial/" + nct} target="_blank" rel="noopener noreferrer">{nct} · Full trial ↗</a> : "No linked trial"}</td>
          <td>{saved?.status?.replaceAll("_", " ") || (nct ? loading ? "Loading…" : "Not available" : "Regulatory program")}</td>
          <td>{saved?.primary_completion_date?.date || "Not reported"}<small>{saved?.primary_completion_date?.type}</small></td>
          <td>{row.pdufaDate || "Not reported"}</td>
          <td>{row.priorityReview?.status === "FDA_VERIFIED" && row.priorityReview.source
            ? <a href={row.priorityReview.source} target="_blank" rel="noopener noreferrer" title="FDA document confirming this application's Priority Review designation">
                <strong>IMP: Priority Review</strong> ↗
              </a>
            : <span title="No application-specific FDA Priority Review evidence has been verified">Not verified</span>}</td>
          <td>{row.marketCap == null ? "Not verified" : "$" + (row.marketCap / (row.marketCap >= 1e9 ? 1e9 : 1e6)).toFixed(1) + (row.marketCap >= 1e9 ? "B" : "M")}</td>
          <td>{saved ? <><strong>{saved.p_value_count || 0} reported</strong><small>{saved.p_value_status?.replaceAll("_", " ")}</small></> : nct && loading ? "Loading…" : "Not available"}</td>
          <td>{nct
            ? <a className="secondary trial-sheet-link trial-sheet-action" href={"/trial/" + nct} target="_blank" rel="noopener noreferrer">Full sheet ↗</a>
            : <button type="button" className="secondary" aria-expanded={active} aria-controls={active ? "pipeline-expanded-record" : undefined} onClick={() => setSelected(active ? "" : row.id)}>{active ? "Close fields" : "Program fields"}</button>}</td>
          <AssessmentCells row={row} stage="PIPELINE" onOpen={() => setSelected(active ? "" : row.id)} />
        </tr>;
      })}</tbody>
    </table></div> : <p className="pipeline-data-empty">No trials or programs match these filters. Uncheck a stage, date or trial filter, or clear the search to broaden the list. Unknown evidence does not pass a selected qualification criterion.</p>}
    <div className="pipeline-data-pagination pipeline-data-footer"><span>Phase total · {rows.length.toLocaleString("en-US")}</span><div className="pipeline-actions">
      <button type="button" className="secondary" disabled={current.page === 0} onClick={() => navigate(current.page - 1)}>Previous</button>
      <button type="button" className="secondary" disabled={current.page + 1 >= current.pages} onClick={() => navigate(current.page + 1)}>Next</button>
    </div></div>
    {selectedRow && <div id="pipeline-expanded-record" ref={detailsRef}><CandidateAssessments key={selectedRow.id + "-scores"} row={selectedRow} /><TrialFields key={selectedRow.id} row={selectedRow} onClose={() => setSelected("")} /></div>}
  </section>;
}
