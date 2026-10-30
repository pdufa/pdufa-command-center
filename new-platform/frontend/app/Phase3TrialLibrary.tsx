"use client";

import { useEffect, useState } from "react";

type Period = "CURRENT" | "PREVIOUS";
type Decision = "APPROVED" | "CRL" | "EXTENDED" | "PENDING";
type Evidence = { id?: string; url: string; retrieved_at?: string; verification_status?: string; sha256?: string };
type Prediction = { prediction_id?: string; decision: string; created_at?: string; evidence_cutoff?: string; actual_decision?: string; actual_decision_date?: string; scientific_readiness?: string; confidence?: number | null; uncertainty?: string; evidence?: Evidence[]; correctness?: boolean | null };
type Trial = {
  nct_id: string; company: string; ticker?: string | null; drug: string; indication: string; trial_title: string;
  phase3_status: string; primary_endpoint_result?: string; results_available: boolean; fda_submission_status?: string;
  pdufa_date?: string | null; actual_decision: Decision; decision_date?: string | null; scientific_readiness?: string;
  readiness_reason?: string; last_verified?: string; source_url?: string; evidence?: Evidence[]; latest_run_id?: string | null;
  predictions?: Prediction[];
};
type Catalog = {
  period: Period; trials: Trial[]; total: number; page: number; page_size: number; pages: number;
  counts: Record<Decision, number>; source_status?: string; last_updated?: string | null;
  ingestion?: Record<string, unknown>; source_health?: Record<string, unknown>; period_definition?: string | Record<string, unknown>;
};
type Preferences = { period: Period; query: string; decision: Decision | "ALL"; sort: string; direction: "asc" | "desc"; page: number };
const DECISIONS: Decision[] = ["APPROVED", "CRL", "EXTENDED", "PENDING"];
const STORAGE_KEY = "pdufa_phase3_library_filters_v1";
const SORTS: [string, string][] = [["last_verified", "Last verified"], ["company", "Company"], ["ticker", "Stock ticker"], ["drug", "Drug"], ["indication", "Indication"], ["trial_title", "Trial title"], ["nct_id", "NCT number"], ["phase3_status", "Phase 3 status"], ["decision", "Actual FDA decision"], ["pdufa_date", "PDUFA date"], ["scientific_readiness", "Scientific readiness"]];
const INITIAL: Preferences = { period: "CURRENT", query: "", decision: "ALL", sort: "last_verified", direction: "desc", page: 1 };
const safeUrl = (value?: string) => typeof value === "string" && value.startsWith("https://");
const count = (value: unknown): value is number => Number.isSafeInteger(value) && Number(value) >= 0;
const dateText = (value?: string | null) => value && Number.isFinite(Date.parse(value)) ? value.replace("T", " ").replace(/\.\d+(?:Z|[+-].*)$/, " UTC") : "Not independently verified";
const textValue = (value: unknown, fallback = "Unknown") => typeof value === "string" && value.trim() ? value : fallback;

export function parseCatalog(value: unknown, period: Period): Catalog {
  if (!value || typeof value !== "object") throw new Error("Invalid trial catalog response.");
  const data = value as Catalog;
  if (data.period !== period || !Array.isArray(data.trials) || !count(data.total) || !count(data.pages) ||
      !count(data.page) || data.page < 1 || !count(data.page_size) || data.page_size < 1 || data.page_size > 100 ||
      !data.counts || DECISIONS.some(key => !count(data.counts[key]))) throw new Error("Invalid trial catalog totals.");
  if (data.trials.length > data.page_size || data.trials.some(row => !row || !/^NCT[0-9]{8}$/.test(row.nct_id) ||
      typeof row.company !== "string" || typeof row.drug !== "string" || typeof row.indication !== "string" ||
      typeof row.trial_title !== "string" || typeof row.results_available !== "boolean" || !DECISIONS.includes(row.actual_decision))) {
    throw new Error("Trial catalog evidence could not be validated.");
  }
  return data;
}

function restoredPreferences(value: unknown): Preferences {
  if (!value || typeof value !== "object") return INITIAL;
  const p = value as Partial<Preferences>;
  return {
    period: p.period === "PREVIOUS" ? "PREVIOUS" : "CURRENT",
    query: typeof p.query === "string" ? p.query.slice(0, 200) : "",
    decision: p.decision === "ALL" || DECISIONS.includes(p.decision as Decision) ? p.decision! : "ALL",
    sort: SORTS.some(([key]) => key === p.sort) ? p.sort! : "last_verified",
    direction: p.direction === "asc" ? "asc" : "desc",
    page: Number.isSafeInteger(p.page) && Number(p.page) > 0 && Number(p.page) < 1000000000 ? Number(p.page) : 1,
  };
}

function SourceLinks({ evidence, sourceUrl }: { evidence?: Evidence[]; sourceUrl?: string }) {
  const links = (evidence || []).filter(item => safeUrl(item.url));
  if (!links.length && safeUrl(sourceUrl)) links.push({ url: sourceUrl! });
  return links.length ? <details><summary>Evidence · {links.length}</summary><ul>{links.map((item, index) =>
    <li key={(item.id || item.url) + index}><a href={item.url} target="_blank" rel="noopener noreferrer">Source {index + 1}</a>
      {item.verification_status ? " · " + item.verification_status : ""}{item.retrieved_at ? " · " + dateText(item.retrieved_at) : ""}</li>)}</ul></details> : <span>Evidence not available</span>;
}

function Metrics({ value }: { value: unknown }) {
  if (value === null || value === undefined) return <span>Not measurable</span>;
  if (typeof value === "number" || typeof value === "string") return <span>{String(value)}</span>;
  if (typeof value === "boolean") return <span>{value ? "Yes" : "No"}</span>;
  if (Array.isArray(value)) return <ul>{value.map((item, index) => <li key={index}><Metrics value={item} /></li>)}</ul>;
  if (typeof value === "object") return <dl>{Object.entries(value).map(([key, item]) => <div key={key} style={{ marginBottom: 8 }}><dt><strong>{key.replaceAll("_", " ")}</strong></dt><dd style={{ marginLeft: 16 }}><Metrics value={item} /></dd></div>)}</dl>;
  return <span>Unknown</span>;
}

function Predictions({ trials }: { trials: Trial[] }) {
  const rows = trials.flatMap(trial => (trial.predictions || []).map(prediction => ({ trial, prediction })));
  return <details className="panel" aria-label="Predicted versus actual FDA decisions" style={{ margin: "14px 0", padding: 12 }}>
    <summary><strong>PREDICTED FDA DECISION vs. ACTUAL FDA DECISION</strong></summary>
    <p className="subtle">Only saved, timestamped predictions are shown. A trial&apos;s endpoint result is separate from its FDA application outcome. Missing evidence retains ABSTAIN; source ingestion does not complete scientific assessments.</p>
    {rows.length ? <div style={{ overflowX: "auto" }}><table style={{ minWidth: 1100, width: "100%" }}><thead><tr>
      {["NCT", "Predicted decision", "Actual FDA decision", "Prediction created", "Evidence cutoff", "Actual decision date", "Scientific readiness", "Confidence / uncertainty", "Correctness", "Evidence"].map(label => <th scope="col" key={label}>{label}</th>)}
    </tr></thead><tbody>{rows.map(({ trial, prediction }, index) => <tr key={prediction.prediction_id || trial.nct_id + "-" + index}>
      <td>{trial.nct_id}</td><td>{["PASS", "CRL", "EXTENSION", "ABSTAIN"].includes(prediction.decision) ? prediction.decision : "ABSTAIN"}</td>
      <td>{textValue(prediction.actual_decision, trial.actual_decision)}</td><td>{dateText(prediction.created_at)}</td><td>{dateText(prediction.evidence_cutoff)}</td>
      <td>{dateText(prediction.actual_decision_date)}</td><td>{textValue(prediction.scientific_readiness, "NOT READY")}</td>
      <td>{typeof prediction.confidence === "number" ? prediction.confidence.toLocaleString() : "Not calibrated"} · {textValue(prediction.uncertainty, "Uncertainty not quantified")}</td>
      <td>{typeof prediction.correctness === "boolean" ? prediction.correctness ? "Correct" : "Incorrect" : "Not objectively evaluated"}</td>
      <td><SourceLinks evidence={prediction.evidence} /></td>
    </tr>)}</tbody></table></div> : <p>No eligible saved prospective predictions for the displayed trials. No retrospective forecast or approval probability has been generated.</p>}
  </details>;
}

export default function Phase3TrialLibrary({ onAnalyze }: { onAnalyze: (nct: string, runId?: string) => void }) {
  const [preferences, setPreferences] = useState<Preferences>(INITIAL);
  const [restored, setRestored] = useState(false);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [selected, setSelected] = useState("");
  const [validation, setValidation] = useState<Record<string, unknown> | null>(null);
  const [validationError, setValidationError] = useState("");
  const [validationLoading, setValidationLoading] = useState(false);
  const change = (next: Partial<Preferences>) => setPreferences(current => ({ ...current, page: 1, ...next }));

  useEffect(() => {
    try { setPreferences(restoredPreferences(JSON.parse(localStorage.getItem(STORAGE_KEY) || "null"))); } catch { /* Defaults remain available. */ }
    try {
      const pointer = JSON.parse(localStorage.getItem("pdufa_nct_processing_run_v1") || "null");
      if (typeof pointer?.nct_id === "string" && /^NCT[0-9]{8}$/.test(pointer.nct_id)) setSelected(pointer.nct_id);
    } catch { /* Processing owns its saved pointer. */ }
    setRestored(true);
  }, []);
  useEffect(() => {
    if (!restored) return;
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences)); } catch { /* Search works without local storage. */ }
  }, [preferences, restored]);
  useEffect(() => {
    if (!restored) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true); setError(""); setCatalog(null);
      const params = new URLSearchParams({ period: preferences.period, q: preferences.query, decision: preferences.decision,
        sort: preferences.sort, dir: preferences.direction, page: String(preferences.page), page_size: "25" });
      try {
        const response = await fetch("/api/phase3-trials?" + params.toString(), { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error(response.status === 401 ? "Sign in to access the verified trial library." : "Verified trial catalog unavailable (" + response.status + ").");
        const next = parseCatalog(await response.json(), preferences.period);
        if (!controller.signal.aborted) setCatalog(next);
      } catch (failure) {
        if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Unable to load the verified trial catalog.");
      } finally { if (!controller.signal.aborted) setLoading(false); }
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [preferences, refresh, restored]);
  useEffect(() => {
    const interval = setInterval(() => setRefresh(value => value + 1), 30000);
    return () => clearInterval(interval);
  }, []);

  const counts = catalog?.counts;
  const allCount = counts ? DECISIONS.reduce((total, decision) => total + counts[decision], 0) : null;
  const ingestion = catalog?.ingestion || {};
  const progress = [ingestion.records_imported, ingestion.processed, ingestion.imported, ingestion.verified_trials, ingestion.completed].find(count);
  const expected = [ingestion.expected_total, ingestion.total_count, ingestion.discovered].find(count);
  const scheduling = ingestion.scheduling && typeof ingestion.scheduling === "object" ? ingestion.scheduling as Record<string, unknown> : {};
  const pages = Math.max(1, catalog?.pages || 1);
  const sortColumn = (sort: string) => change({ sort, direction: preferences.sort === sort && preferences.direction === "asc" ? "desc" : "asc" });
  const heading = (label: string, sort?: string) => <th scope="col" key={label} style={{ textAlign: "left", padding: 10, verticalAlign: "top", borderBottom: "1px solid #c8d1c8" }}>
    {sort ? <button type="button" className="secondary" onClick={() => sortColumn(sort)} aria-label={"Sort by " + label}>{label}{preferences.sort === sort ? preferences.direction === "asc" ? " ↑" : " ↓" : ""}</button> : label}</th>;
  async function loadValidation() {
    if (validationLoading) return;
    setValidationLoading(true); setValidationError("");
    try {
      const response = await fetch("/api/phase3-trials/validation", { cache: "no-store" });
      if (!response.ok) throw new Error("Historical validation is unavailable.");
      const data: unknown = await response.json();
      if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error("Invalid historical validation response.");
      setValidation(data as Record<string, unknown>);
    } catch (failure) { setValidationError(failure instanceof Error ? failure.message : "Historical validation is unavailable."); }
    finally { setValidationLoading(false); }
  }

  return <section className="panel" id="phase3-trial-library" aria-label="Phase 3 trial library" style={{ minWidth: 0, marginTop: 18 }}>
    <h2>Phase 3 Trial Library</h2>
    <p className="subtle">Verified Phase 3 trial identities and posted results. Actual FDA application decisions require separate regulatory evidence. Unknown outcomes stay PENDING / UNKNOWN.</p>
    <h3>SEARCH TRIALS</h3>
    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "end" }}>
      <label>Period <select aria-label="Search period" value={preferences.period} onChange={event => change({ period: event.target.value as Period, decision: "ALL" })}>
        <option value="CURRENT">CURRENT</option><option value="PREVIOUS">PREVIOUS / HISTORICAL</option>
      </select></label>
      <label style={{ flex: "1 1 260px" }}>Company, ticker, drug, indication or NCT
        <input type="search" aria-label="Search trials" maxLength={200} value={preferences.query} onChange={event => change({ query: event.target.value })} placeholder="Search all matching trials" style={{ width: "100%", boxSizing: "border-box" }} />
      </label>
      <label>Sort <select aria-label="Sort trials" value={preferences.sort} onChange={event => change({ sort: event.target.value })}>{SORTS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <button type="button" className="secondary" onClick={() => change({ direction: preferences.direction === "asc" ? "desc" : "asc" })}>{preferences.direction === "asc" ? "Ascending ↑" : "Descending ↓"}</button>
      <button type="button" onClick={() => setRefresh(value => value + 1)} disabled={loading}>{loading ? "Loading…" : "Refresh verified trials"}</button>
    </div>
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "14px 0" }} aria-label="FDA decision results">
      <button type="button" className="secondary" onClick={() => change({ decision: "ALL" })} aria-pressed={preferences.decision === "ALL"}>All · {allCount === null ? "—" : allCount.toLocaleString()}</button>
      {DECISIONS.map(decision => <button key={decision} type="button" className="secondary" aria-pressed={preferences.decision === decision} onClick={() => change({ decision })} style={{ minWidth: 130, minHeight: 48 }}>
        {decision === "APPROVED" ? "🟢" : decision === "CRL" ? "🔴" : decision === "EXTENDED" ? "🟠" : "⚪"} {decision} · {counts ? counts[decision].toLocaleString() : "—"}
      </button>)}
    </div>
    <p role="status" aria-live="polite">{loading ? "Loading verified trial records…" : error || (catalog ? catalog.total.toLocaleString() + " matching trials · page " + catalog.page + " of " + pages : "Connecting to the verified trial catalog…")}</p>
    {catalog ? <div className="subtle" aria-label="Trial library source health">
      <p>Source: {textValue(catalog.source_status, "Unknown")} · Last updated: {dateText(catalog.last_updated)} · Synchronization: {textValue(ingestion.status ?? ingestion.state, "Status not available")}
        {progress !== undefined ? " · " + progress.toLocaleString() + " imported" : ""}{expected !== undefined ? " / " + expected.toLocaleString() + " discovered" : ""}</p>
      <p>Automatic synchronization: {scheduling.verified_execution === true && typeof scheduling.last_automatic_execution_at === "string" ? "execution verified " + dateText(scheduling.last_automatic_execution_at) : "scheduled execution not yet verified"}.
        {typeof scheduling.next_due_at === "string" ? " Next due: " + dateText(scheduling.next_due_at) + "." : ""}
        {count(ingestion.records_rejected) ? " Records requiring source review: " + ingestion.records_rejected.toLocaleString() + "." : ""}</p>
      {catalog.period_definition ? <p>{typeof catalog.period_definition === "string" ? catalog.period_definition : textValue(catalog.period_definition[preferences.period], "Period follows verified study completion dates and ongoing status.")}</p> : null}
      {catalog.source_health ? <details><summary>Source verification health</summary><ul>{Object.entries(catalog.source_health).map(([source, value]) => <li key={source}>{source.replaceAll("_", " ")}: {typeof value === "string" || typeof value === "number" ? String(value) : value && typeof value === "object" ? textValue((value as Record<string, unknown>).status ?? (value as Record<string, unknown>).state, "Evidence checks recorded") : "Unknown"}</li>)}</ul></details> : null}
    </div> : null}
    {selected ? <p className="subtle" role="status">Selected trial: <strong>{selected}</strong>. Its saved processing state remains in the existing analysis system.</p> : null}
    <div role="region" aria-label="Scrollable Phase 3 trial table" tabIndex={0} style={{ maxHeight: 580, overflow: "auto", border: "1px solid #c8d1c8", maxWidth: "100%" }}>
      <table className="phase3-library-table" style={{ width: "100%", borderCollapse: "collapse", minWidth: 2400 }}>
        <thead><tr>{heading("Company", "company")}{heading("Stock ticker", "ticker")}{heading("Drug", "drug")}{heading("Indication", "indication")}{heading("Trial title", "trial_title")}{heading("NCT number", "nct_id")}{heading("Phase 3 status", "phase3_status")}{heading("Primary endpoint result")}{heading("Results availability")}{heading("FDA submission status")}{heading("PDUFA date", "pdufa_date")}{heading("Actual FDA decision", "decision")}{heading("Scientific readiness", "scientific_readiness")}{heading("Last verified date", "last_verified")}{heading("Analyze")}</tr></thead>
        <tbody>{catalog?.trials.map(trial => <tr key={trial.nct_id} data-nct-id={trial.nct_id} aria-selected={selected === trial.nct_id}>
          <td>{trial.company}</td><td>{trial.ticker || "Not verified"}</td><td>{trial.drug}</td><td>{trial.indication}</td><td>{trial.trial_title}</td>
          <td><a href={"https://clinicaltrials.gov/study/" + trial.nct_id} target="_blank" rel="noopener noreferrer">{trial.nct_id}</a></td><td>{trial.phase3_status}</td>
          <td style={{ maxWidth: 360, overflowWrap: "anywhere" }}>{textValue(trial.primary_endpoint_result, "Posted results require endpoint interpretation")}</td>
          <td>{trial.results_available ? "Posted results verified" : "Not verified"}</td><td>{textValue(trial.fda_submission_status, "UNKNOWN")}</td><td>{dateText(trial.pdufa_date)}</td>
          <td>{trial.actual_decision === "PENDING" ? "PENDING / UNKNOWN" : trial.actual_decision}{trial.decision_date ? <><br />{dateText(trial.decision_date)}</> : null}</td>
          <td title={trial.readiness_reason}>{textValue(trial.scientific_readiness, "NOT READY")}</td><td>{dateText(trial.last_verified)}<SourceLinks evidence={trial.evidence} sourceUrl={trial.source_url} /></td>
          <td><button type="button" aria-label={"Analyze " + trial.nct_id} onClick={() => { setSelected(trial.nct_id); onAnalyze(trial.nct_id, trial.latest_run_id || undefined); }}>ANALYZE</button></td>
        </tr>)}
          {!catalog?.trials.length && <tr><td colSpan={15} style={{ padding: 18 }}>{loading ? "Retrieving verified trial records…" : error || "No matching verified trials. Adjust the period, search or FDA decision filter."}</td></tr>}
        </tbody>
      </table>
    </div>
    <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", margin: "12px 0" }} aria-label="Trial pagination">
      <button type="button" className="secondary" disabled={loading || preferences.page <= 1} onClick={() => change({ page: preferences.page - 1 })}>Previous page</button>
      <span>Page {catalog?.page || preferences.page} of {pages} · 25 records per page</span>
      <button type="button" className="secondary" disabled={loading || !catalog || catalog.page >= pages} onClick={() => change({ page: preferences.page + 1 })}>Next page</button>
    </div>
    <Predictions trials={catalog?.trials || []} />
    <details className="panel" aria-label="Historical prediction validation" style={{ padding: 12 }}>
      <summary><strong>Historical prediction validation</strong></summary>
      <p>Only immutable predictions with evidence cutoffs before independently verified decisions are eligible. Library ingestion alone produces no accuracy estimate.</p>
      <button type="button" className="secondary" onClick={() => void loadValidation()} disabled={validationLoading}>{validationLoading ? "Loading…" : "Load persisted validation results"}</button>
      {validationError ? <p role="alert">{validationError}</p> : null}
      {validation ? <Metrics value={validation} /> : null}
    </details>
    <p className="subtle">Company tickers, submissions, PDUFA dates and FDA decisions remain unknown until separately verified. No approval probability, completed scientific investigation or trading authorization is inferred from this library.</p>
    <style>{".phase3-library-table td{padding:10px;vertical-align:top;border-bottom:1px solid #c8d1c8;max-width:360px;overflow-wrap:anywhere}.phase3-library-table th{position:sticky;top:0;background:#f4f7f2;z-index:1}.phase3-library-table tr[aria-selected=true]{background:#e6f1e5}#phase3-trial-library select,#phase3-trial-library input{max-width:100%}@media(max-width:600px){.phase3-library-table td,.phase3-library-table th{font-size:13px;padding:8px}}"}</style>
  </section>;
}
