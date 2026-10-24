"use client";
import {useEffect, useState} from "react";
import {availableCount, type EnrichmentDetail, type EnrichmentIndex, type FieldDetail} from "../lib/shared-enrichment";

type Stage = "PIPELINE" | "GEM_JR" | "GEM";
function useSharedData<T>(url: string, active: boolean) {
  const [state, setState] = useState<{url: string; data?: T; error?: string}>({url: ""});
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    setState({url});
    void fetch(url, {cache: "no-store", signal: controller.signal}).then(async response => {
      if (!response.ok) throw new Error(response.status === 404 ? "No shared record is saved for this exact program yet." : "Shared data is unavailable. Retry to load saved observations.");
      const data = await response.json() as T;
      if (!controller.signal.aborted) setState({url, data});
    }).catch(error => {if (!controller.signal.aborted) setState({url, error: error instanceof Error ? error.message : "Shared data is unavailable."});});
    return () => controller.abort();
  }, [url, active, attempt]);
  return {data: state.url === url ? state.data : undefined, error: state.url === url ? state.error : undefined, retry: () => setAttempt(n => n+1)};
}
function Status({error, retry}: {error?: string; retry: () => void}) {
  return <p role="status">{error || "Loading shared research data…"} {error && <button type="button" className="secondary" onClick={retry}>RETRY</button>}</p>;
}
export default function SharedEnrichment({stage = "PIPELINE"}: {stage?: Stage}) {
  const [open, setOpen] = useState(false), [selected, setSelected] = useState<Stage>(stage);
  const {data, error, retry} = useSharedData<EnrichmentIndex>("/api/shared-enrichment", open);
  const list = data?.lists?.[selected];
  return <details className="panel shared-enrichment" onToggle={e => setOpen(e.currentTarget.open)}>
    <summary><strong>SHARED DATA SETUP · 50 fields · Pipeline / GEM JR / GEM</strong></summary>
    <p>One company record supplies financial and market facts to all three lists. Clinical and FDA evidence stays attached to its exact trial or application.</p>
    {!data ? <Status error={error} retry={retry}/> : <>
      <p><strong>Coverage: {data.status}</strong> · Published {new Date(data.generatedAt).toLocaleString("en-US", {timeZone: "America/Los_Angeles", timeZoneName: "short"})} · {data.companyCount.toLocaleString()} companies</p>
      <p className="subtle">35 source fields · 10 calculated metrics · 5 modeled assessments. These are data fields; selected restrictions and FS / FA presets remain independent.</p>
      <label>Show coverage for <select aria-label="Shared data coverage list" value={selected} onChange={e => setSelected(e.target.value as Stage)}>
        <option value="PIPELINE">Pipeline</option><option value="GEM_JR">GEM JR</option><option value="GEM">GEM</option>
      </select></label>
      <p>{list?.records.toLocaleString()} exact program records · coverage as of {data.asOf}</p>
      {data.financialCollection?.status && <p className="subtle">SEC expansion: {data.financialCollection.status} · {data.financialCollection.collected ?? 0} collected in the last batch · {data.financialCollection.remaining ?? 0} awaiting refresh.</p>}
      {data.marketCollection?.configuration && <p className="subtle">Alpaca: {data.marketCollection.configuration.replaceAll("_", " ")} · {data.marketCollection.collected ?? 0} collected in the last batch. Existing saved market sources remain labeled.</p>}
      <div style={{overflowX: "auto"}}><table><caption>Availability for each field in {selected.replace("_", " ")}</caption><thead><tr><th>Field</th><th>Type / source</th><th>Available</th><th>Stale</th><th>Review / conflict</th><th>Missing</th></tr></thead><tbody>
        {data.fields.map(field => {const counts = list?.fields[field.id]; return <tr key={field.id}>
          <th scope="row">{field.label}<small style={{display: "block", fontWeight: 400}}>{field.group}</small></th>
          <td>{field.kind}<small style={{display: "block"}}>{field.source}</small></td>
          <td>{counts ? availableCount(counts).toLocaleString() : "—"}</td><td>{counts?.STALE.toLocaleString()}</td><td>{counts ? (counts.REVIEW+counts.CONFLICTING).toLocaleString() : "—"}</td><td>{counts?.MISSING.toLocaleString()}</td>
        </tr>;})}
      </tbody></table></div>
      <p className="subtle">The existing nightly sequence refreshes these observations after source collection. Missing values stay missing. Open DETAILS on a program to inspect its values, sources, dates and calculation rules.</p>
    </>}
  </details>;
}

function FieldValue({field}: {field: FieldDetail}) {
  const value = field.value;
  if (value === null || value === undefined) return <>Not available</>;
  if (typeof value === "boolean") return <>{value ? "Yes" : "No"}</>;
  if (typeof value === "number") return <>{value.toLocaleString("en-US", {maximumFractionDigits: 4})}</>;
  if (typeof value === "string") return <>{value}</>;
  return <pre style={{whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontSize: ".85em", maxHeight: 240, overflow: "auto"}}>{JSON.stringify(value, null, 2)}</pre>;
}
export function SharedProgramFields({ticker, exactKey}: {ticker?: string; exactKey?: string}) {
  const [open, setOpen] = useState(false);
  const url = "/api/shared-enrichment?ticker="+encodeURIComponent(ticker || "")+(exactKey ? "&id="+encodeURIComponent(exactKey) : "");
  const {data, error, retry} = useSharedData<EnrichmentDetail>(url, open && !!ticker);
  const [group, setGroup] = useState("All fields");
  const groups = data ? [...new Set(data.fields.map(f => f.group))] : [];
  return <details className="panel shared-enrichment" style={{padding: 12, marginBottom: 10}} onToggle={e => setOpen(e.currentTarget.open)}>
    <summary><strong>SHARED RESEARCH FIELDS · values, evidence and missing data</strong></summary>
    {!ticker ? <p>A verified company ticker is required to match shared observations.</p> : !data ? <Status error={error} retry={retry}/> : <>
      <p>Company: {data.ticker} · {data.exactKey ? "Exact trial / application matched" : "Company facts only"} · Evaluated {data.evaluatedOn}</p>
      <label>Field group <select aria-label="Shared research field group" value={group} onChange={e => setGroup(e.target.value)}><option>All fields</option>{groups.map(g => <option key={g}>{g}</option>)}</select></label>
      {data.fields.filter(f => group === "All fields" || f.group === group).map(field => <article key={field.id} style={{padding: "10px 0", borderBottom: "1px solid #ccc", overflowWrap: "anywhere"}}>
        <strong>{field.label}</strong> · <span>{field.status}</span><div><FieldValue field={field}/></div>
        <small>{field.kind} · {field.source}</small>
        {field.rule && <p className="subtle">{field.rule}</p>}
        {(field.observedAt || field.retrievedAt) && <p className="subtle">Observation / period: {field.observedAt || "not recorded"} · Original source check: {field.retrievedAt || "not recorded"}</p>}
        {field.note && <p className="subtle">{field.note}</p>}
        {field.sourceUrl && <a href={field.sourceUrl} target="_blank" rel="noopener noreferrer">OPEN EVIDENCE ↗</a>}
      </article>)}
    </>}
  </details>;
}
