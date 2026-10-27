"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Candidate } from "./Workspace";
import NumericForecastMetrics from "./NumericForecastMetrics";
import { ASSESSMENT_LABELS, ASSESSMENT_STAGES, ASSESSMENT_WEIGHTS, categoryId, downloadJson, scoreFor, stageLabel, validateAssessmentIndex, type AssessmentDetail, type AssessmentIndex, type AssessmentIndexRecord, type AssessmentStage } from "../lib/candidate-assessments";

const n = (value: number) => Number(value.toFixed(2)).toLocaleString("en-US");
const EMPTY = new Map<string, AssessmentIndexRecord>();
type State = { data: AssessmentIndex | null; records: Map<string, AssessmentIndexRecord>; error: string; loading: boolean; refresh: () => void };
const Context = createContext<State>({ data: null, records: EMPTY, error: "", loading: false, refresh() {} });
export const useAssessments = () => useContext(Context);

export function AssessmentProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<AssessmentIndex | null>(null), [error, setError] = useState("");
  const [loading, setLoading] = useState(true), [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    setLoading(true); setError(""); setData(null);
    async function load(attempt = 0) {
      try {
        const response = await fetch("/api/assessments", { cache: "no-store", signal: controller.signal });
        const value = await response.json();
        // The source adapter deliberately rejects concurrent refresh readers.
        // Recover a brief 503 without asking the user to trigger scoring again.
        if (response.status === 503 && attempt < 3) { timer = setTimeout(() => void load(attempt + 1), 2000); return; }
        if (!response.ok) throw new Error(value.error || "Candidate scores are unavailable");
        if (controller.signal.aborted) return;
        if (value.status === "BUILDING" && attempt < 60) { timer = setTimeout(() => void load(attempt + 1), 3000); return; }
        setData(validateAssessmentIndex(value)); setLoading(false); timer = setTimeout(() => void load(), 300000);
      } catch (cause) { if (!controller.signal.aborted) { setError(cause instanceof Error ? cause.message : "Candidate scores are unavailable"); setLoading(false); } }
    }
    void load();
    return () => { controller.abort(); if (timer) clearTimeout(timer); };
  }, [retry]);
  const records = useMemo(() => new Map(data?.records.map(record => [record[0], record]) || []), [data]);
  return <Context.Provider value={{ data, records, error, loading, refresh: () => setRetry(v => v + 1) }}>{children}</Context.Provider>;
}

export function ScoreProgressButton({ label, stage, onScore, rowId }: { label: string; stage: AssessmentStage; onScore?: () => void; rowId?: string }) {
  const { data, records, loading, error, refresh } = useAssessments();
  const [open, setOpen] = useState(false);
  const [requested, setRequested] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const record = rowId ? records.get(rowId) : undefined;
  const totals = data?.totals[stage];
  const score = record ? scoreFor(record, stage) : null;
  const start = () => { setOpen(true); setShowAll(false); setRequested(true); refresh(); };
  return <span style={{ display: "inline-flex", position: "relative", alignItems: "center", gap: 6 }}>
    <button type="button" className="secondary" onClick={start}>{label}</button>
    <button type="button" className="secondary" onClick={() => setOpen(value => !value)} aria-label={"Show scoring status for " + label} aria-expanded={open} title="Scoring status">ⓘ</button>
    {open && <span role="dialog" aria-label={label + " progress"} style={{ position: "absolute", top: "calc(100% + 6px)", left: 0, zIndex: 99999, width: "min(360px, 92vw)", maxWidth: "92vw", padding: 14, border: "1px solid #777", borderRadius: 10, background: "var(--background, white)", color: "var(--foreground, #111)", boxShadow: "0 6px 22px #0003", whiteSpace: "normal" }}>
      <span style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        <strong>{rowId ? "Trial scoring status" : stageLabel(stage) + " list scoring status"}</strong>
        <button type="button" className="secondary" onClick={() => { setOpen(false); setShowAll(false); }} aria-label="Close scoring status">× Close</button>
      </span>
      <span style={{ display: "block", marginTop: 10 }} role="status">{loading ? "Refreshing scoring index…" : error ? "Refresh failed: " + error : requested ? "Scoring index refresh completed." : "Latest available scoring snapshot."}</span>
      {!rowId && totals && <span style={{ display: "block", marginTop: 8 }}>{data?.total.toLocaleString()} processed · {totals.complete.toLocaleString()} complete · {totals.partial.toLocaleString()} partial · {totals.missing.toLocaleString()} missing evidence</span>}
      {rowId && <span style={{ display: "block", marginTop: 8 }}>{score ? score[2] === 0 ? "Awaiting evidence" : score[0] == null ? "Partial assessment · evidence incomplete" : "Complete score: " + score[0] + " / 100" : "No assessment available yet"}</span>}
      {rowId && <button type="button" className="secondary" style={{ marginTop: 10, width: "100%" }} onClick={() => setShowAll(v => !v)} aria-expanded={showAll}>{showAll ? "Hide all 21 scores ↑" : "View all 21 scores & underlying data ↓"}</button>}
      {rowId && showAll && <span style={{ display: "block", marginTop: 10, maxHeight: "50vh", overflowY: "auto" }}>
        <strong>All assessments · {rowId}</strong>
        {ASSESSMENT_STAGES.map(key => { const result = record ? scoreFor(record, key) : undefined; return <span key={key} style={{ display: "block", padding: "8px 0", borderTop: "1px solid #8885" }}>
          <strong>{stageLabel(key)}: {result && result[0] !== null ? n(result[0]) + " / 100" : "Not scored"}</strong>
          <small style={{ display: "block" }}>Observed {result ? n(result[1]) : "0"} points · evidence coverage {result ? n(result[2]) : "0"}%</small>
          {ASSESSMENT_LABELS[key].map((label, i) => <span key={label} style={{ display: "flex", justifyContent: "space-between", gap: 10, padding: "3px 0" }}><span>{categoryId(key, i)} · {label}</span><strong>{result ? n(Number(result[i + 3] ?? 0)) + " / " + n(Number(result[i + 10] ?? 0)) : "Missing evidence"}</strong></span>)}
        </span>; })}
        {!record && <small>There is no recorded assessment for this trial yet. Scores cannot be inferred without source evidence.</small>}
      </span>}
      <small style={{ display: "block", marginTop: 8 }}>These are refresh states and recorded results, not live per-trial job percentages. Closing does not stop the refresh.</small>
    </span>}
  </span>;
}

export function AssessmentStatus({ stage }: { stage: AssessmentStage }) {
  const { data, error, loading, refresh } = useAssessments();
  const totals = data?.totals[stage];
  return <div className="assessment-status" role="status">
    <div><strong>{stageLabel(stage)} scoring · seven assessments / 100 points</strong>
      <p>{loading ? "Assessing the complete Pipeline universe…" : error ? error : data && totals
        ? `${data.total.toLocaleString("en-US")} candidates assessed · ${totals.complete.toLocaleString("en-US")} complete · ${totals.partial.toLocaleString("en-US")} partial · ${totals.missing.toLocaleString("en-US")} awaiting evidence`
        : "Scoring has not loaded."}</p>
      <small>Partial = observed points, with missing evidence unscored. Complete scores alone can be ranked. {data && `Updated ${data.computedAt} · ${data.modelVersion} · ${data.registryLinked.toLocaleString("en-US")} linked registry records.`}</small>
    </div>
    <ScoreProgressButton label={"Score Entire " + stageLabel(stage) + " List"} stage={stage} />
  </div>;
}

export function AssessmentHeaders({ stage }: { stage: AssessmentStage }) {
  return <><th>{stageLabel(stage)} score</th><th>Score evidence</th>{ASSESSMENT_LABELS[stage].map((label, i) => <th key={label} title={label + " · " + ASSESSMENT_WEIGHTS[stage][i] + " points"}>{categoryId(stage, i)}<small>{label}</small></th>)}</>;
}
export function AssessmentCells({ row, stage, onOpen }: { row: Candidate; stage: AssessmentStage; onOpen: () => void }) {
  const { records, loading, error } = useAssessments();
  const score = scoreFor(records.get(row.id), stage);
  const open = (value: ReactNode) => <button type="button" className="assessment-score-link" onClick={onOpen} aria-label={"Open " + stageLabel(stage) + " scoring data for " + (row.programId || row.id)}>{value}</button>;
  return <>
    <td className="assessment-score-cell">{open(score ? <><strong>{score[2] === 0 ? "Unscored" : score[0] == null ? n(score[1]) + " observed" : n(score[0]) + " / 100"}</strong><small>{score[2] === 0 ? "Awaiting evidence" : score[0] == null ? "PARTIAL · not ranked" : "COMPLETE"}</small></> : loading ? "Scoring…" : error ? "Unavailable" : "Awaiting assessment")}</td>
    <td>{score ? <><strong>{n(score[2])}%</strong><small>evidence coverage</small></> : "—"}</td>
    {ASSESSMENT_WEIGHTS[stage].map((max, i) => { const coverage = score?.[10 + i], points = score?.[3 + i];
      return <td key={i} className="assessment-category-cell">{open(coverage ? <><strong>{n(points!)} / {max}</strong><small>{coverage >= max - .01 ? "Complete" : n(coverage) + " / " + max + " assessed"}</small></> : <><strong>— / {max}</strong><small>Missing evidence</small></>)}</td>;
    })}
  </>;
}
export function AssessmentSort({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return <label className="assessment-sort">Score order <select value={value} onChange={e => onChange(e.target.value)}>
    <option value="source">Current table order</option><option value="score">Highest complete score</option><option value="coverage">Most evidence available</option>
  </select></label>;
}

function Value({ value }: { value: unknown }) {
  if (value == null || value === "") return <span className="subtle">Not reported</span>;
  if (typeof value === "object") return <pre className="assessment-measurement">{JSON.stringify(value, null, 2)}</pre>;
  return <span>{typeof value === "boolean" ? value ? "Yes" : "No" : String(value)}</span>;
}

export default function CandidateAssessments({ row, initialStage = "PIPELINE" }: { row: Candidate; initialStage?: AssessmentStage }) {
  const [data, setData] = useState<AssessmentDetail | null>(null), [error, setError] = useState("");
  const [stage, setStage] = useState<AssessmentStage>(initialStage), [retry, setRetry] = useState(0);
  const { data: index, refresh: refreshIndex } = useAssessments();
  const [rescoring, setRescoring] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    setData(null); setError("");
    async function load(attempt = 0) {
      try {
        const response = await fetch("/api/assessments?identity=" + encodeURIComponent(row.id), { cache: "no-store", signal: controller.signal });
        const result = await response.json();
        if (response.status === 409 && attempt < 60) { timer = setTimeout(() => void load(attempt + 1), 3000); return; }
        if (response.status === 503 && attempt < 3) { timer = setTimeout(() => void load(attempt + 1), 2000); return; }
        if (!response.ok) throw new Error(result.error || "Detailed scoring evidence is unavailable");
        if (result.id !== row.id || row.programId && result.programId !== row.programId || !result.models || ASSESSMENT_STAGES.some(key => result.models[key]?.categories?.length !== 7)) throw new Error("Exact candidate scoring identity could not be verified");
        if (!controller.signal.aborted) { setData(result); setRescoring(false); }
      } catch (cause) { if (!controller.signal.aborted) { setError(cause instanceof Error ? cause.message : "Scoring evidence is unavailable"); setRescoring(false); } }
    }
    void load();
    return () => { controller.abort(); if (timer) clearTimeout(timer); };
  }, [row.id, row.programId, retry, index?.version]);
  const model = data?.models[stage], change = data?.changes[stage];
  return <section className="candidate-assessments" aria-label={"All candidate assessment scores for " + row.id}>
    <div className="sectionhead"><div><h3>Candidate scores &amp; underlying data</h3><p>{row.ticker} · {row.drug || row.nctId || row.id} · {row.programId || "Exact program: " + row.id}</p></div>
      <button type="button" className="secondary" disabled={rescoring} onClick={() => { setRescoring(true); refreshIndex(); setRetry(v => v + 1); }}>{rescoring ? "Refreshing trial evidence…" : "Score This Trial · All 3 Rankings"}</button>
      {data && <button type="button" className="secondary" onClick={() => downloadJson(data, (row.programId || data.nctId || "candidate") + "-all-scores.json")}>Download all scores &amp; data</button>}
    </div>
    <details className="assessment-ledger" aria-label="Historical FDA PDUFA comparisons"><summary>Historical PDUFA comparisons · NOT READY</summary><p><strong>Decision evidence checklist:</strong> SCIENCE 20/20 independently reviewed; OUTCOME 20/20 independently reviewed; at least three source-verified, pre-cutoff close FDA analogues; complete historical cohort denominator including CRLs and withdrawals; indication-level review-cycle reconciliation. Current trial: NOT VERIFIED. No historical comparison or approval probability is available until the records are connected and reviewed.</p><p>Historical comparisons are mandatory before a DECISION research assessment. No verified comparable FDA decisions are connected to this trial view yet. Prior decisions must match disease subtype, indication, drug mechanism, and primary endpoint, and must precede the prediction date.</p><p>SCIENCE, OUTCOME, and historical evidence must each pass independent review. Historical approval rates are descriptive, not calibrated approval probabilities. No trading recommendation is available.</p></details>
    {rescoring && <p role="status" aria-live="polite">Refreshing scoring index and trial evidence. Updated results will appear below; this does not force a fresh external-source rescan.</p>}
    {!data && !error && <p role="status">Loading all 21 assessments and exact-program evidence…</p>}
    {error && <div role="alert"><p className="error">{error}</p><button type="button" className="secondary" onClick={() => setRetry(v => v + 1)}>Retry scoring data</button></div>}
    {data && model && <>
      <div className="assessment-models" role="group" aria-label="Scoring models">{ASSESSMENT_STAGES.map(key => { const score = data.models[key]; return <button type="button" key={key} className={stage === key ? "active" : "secondary"} aria-pressed={stage === key} onClick={() => setStage(key)}>
        <span>{stageLabel(key)}</span><strong>{score.coverage === 0 ? "Unscored" : score.score == null ? n(score.observedPoints) + " observed points" : n(score.score) + " / 100"}</strong><small>{n(score.coverage)}% evidence · {score.status}</small>
      </button>; })}</div>
      <NumericForecastMetrics detail={data} stage={stage} />
      <details className="assessment-ledger"><summary>Remaining assessments · {ASSESSMENT_STAGES.reduce((sum, key) => sum + data.models[key].categories.filter(c => c.status !== "COMPLETE").length, 0)} incomplete</summary><ul>{ASSESSMENT_STAGES.flatMap(key => data.models[key].categories.filter(c => c.status !== "COMPLETE").map(c => <li key={key + c.id}>{stageLabel(key)} · {c.id} {c.label}: {c.status}</li>))}</ul></details>
      <p className="subtle">{data.qualification.note} Missing = unscored; zero = evaluated and earned no points. The displayed weights and research rules are not statistically calibrated.</p>
      {data.riskFlags.length > 0 && <div className="assessment-risk" role="alert"><strong>Evidence flags</strong><ul>{data.riskFlags.map(flag => <li key={flag}>{flag}</li>)}</ul></div>}
      <p className="small">Assessed {data.asOf} · Model {data.modelVersion} · Registry saved {data.registryFetchedAt || "not available"} · Registry source updated {data.registrySourceDate || "not reported"}.
        {change && <strong> Change: {change.observedPoints >= 0 ? "+" : ""}{n(change.observedPoints)} points; {change.coverage >= 0 ? "+" : ""}{n(change.coverage)}% evidence.</strong>}</p>
      <div className="assessment-categories">{model.categories.map(category => <details key={category.id} className="assessment-category" open>
        <summary><strong>{category.id} · {category.label}</strong><span>{category.coverage ? n(category.observedPoints) : "—"} / {category.maximum} points · {n(category.coverage)} / {category.maximum} assessed · {category.status}</span></summary>
        <div className="table-scroll"><table><thead><tr><th>Underlying measurement</th><th>Actual data</th><th>Individual points</th><th>Rule / calculation</th><th>Source / verification dates</th></tr></thead>
          <tbody>{category.metrics.map(metric => <tr key={metric.id}>
            <td><strong>{metric.label}</strong><small>{metric.status}</small></td><td><Value value={metric.value} />{metric.observations != null && <details><summary>Saved safety / exposure observations</summary><Value value={metric.observations} /></details>}</td>
            <td><strong>{metric.points == null ? "—" : n(metric.points)} / {n(metric.maximum)}</strong><small>{n(metric.coverage)} points of evidence assessed</small></td>
            <td>{metric.rule}{metric.note && <small>{metric.note}</small>}</td>
            <td>{metric.source ? <a href={metric.source} target="_blank" rel="noopener noreferrer">Original source ↗</a> : metric.id.includes(".") ? "Inherited clinical evidence" : "No verified source"}<small>Source date: {metric.sourceDate || "Not reported"}</small><small>Verified: {metric.checkedAt || "Not recorded"}</small></td>
          </tr>)}</tbody></table></div>
      </details>)}</div>
      <details className="assessment-ledger"><summary>Reported statistical results · {data.reportedStatistics.length} comparisons · all p-values, effect sizes and confidence intervals</summary>
        <p className="subtle">Each endpoint and comparison is retained. A minimum p-value is never chosen as a trial result.</p>
        {data.reportedStatistics.length ? <div className="table-scroll"><table><thead><tr><th>Endpoint / type</th><th>Groups</th><th>p-value</th><th>Effect / confidence interval</th><th>Complete analysis</th></tr></thead><tbody>{data.reportedStatistics.map((analysis, i) => <tr key={i}>
          <td><Value value={analysis.endpoint} /><small><Value value={analysis.endpoint_type} /></small><small><Value value={analysis.time_frame} /></small></td><td><Value value={analysis.comparison_groups} /></td><td><Value value={analysis.p_value} /></td>
          <td><Value value={{ parameter: analysis.parameter, estimate: analysis.estimate, confidence: analysis.confidence_level, lower: analysis.confidence_lower, upper: analysis.confidence_upper }} /></td><td><Value value={analysis.analysis_json} /></td>
        </tr>)}</tbody></table></div> : <p>No posted statistical analyses are available in the saved registry record.</p>}
      </details>
      <details className="assessment-ledger"><summary>All candidate and scoring input data</summary><Value value={data.data} /></details>
      <details className="assessment-ledger"><summary>Score and evidence history · {data.history.length} latest changes</summary>
        <p className="subtle">{data.historyStatus === "SAVED" ? "Evidence and score changes are saved for this exact program. Repeated unchanged calculations do not create duplicate entries." : "History recording is currently read-only."}</p>
        <div className="table-scroll"><table><thead><tr><th>Assessed at</th><th>Model version</th>{ASSESSMENT_STAGES.map(key => <th key={key}>{stageLabel(key)}</th>)}<th>Evidence fingerprint</th></tr></thead><tbody>{data.history.map((item, i) => <tr key={i}>
          <td>{item.assessedAt}</td><td>{item.modelVersion}</td>{item.models.map((score, j) => <td key={j}>{n(score[1])} points · {n(score[2])}% evidence</td>)}<td><code>{item.evidenceHash}</code></td>
        </tr>)}</tbody></table></div>
      </details>
    </>}
  </section>;
}
