"use client";

import { useEffect, useMemo, useState } from "react";
import type { Candidate } from "./Workspace";
import { type Json, label, object, registrySections, reportedAnalyses, trialId } from "../lib/pipeline-data";

function text(value: Json | undefined) {
  return value === null || value === undefined || value === "" ? "Not reported" :
    typeof value === "boolean" ? value ? "Yes" : "No" : String(value);
}

function FieldBranch({ value, index }: { value: Json; index: number }) {
  const [open, setOpen] = useState(false);
  const item = object(value);
  const title = item.title || item.name || item.measure || item.label || item.id || item.type;
  return <details className="trial-field-branch" open={open} onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>{index + 1}. {title ? text(title) : "Record"}</summary>
    {open && <FieldTree value={value} />}
  </details>;
}

function FieldTree({ value }: { value: Json }) {
  if (Array.isArray(value)) return value.length ? <div className="trial-field-list trial-field-auto-columns">{value.map((item, index) =>
    item && typeof item === "object" ? <FieldBranch key={index} value={item} index={index} /> :
      <div className="trial-field-value" key={index}>{text(item)}</div>)}</div> : <span className="subtle">None reported</span>;
  if (value && typeof value === "object") {
    const entries = Object.entries(value);
    return entries.length ? <dl className="trial-field-grid trial-field-auto-columns">{entries.map(([key, item]) =>
      <div key={key}><dt title={key}>{label(key)}</dt><dd><FieldTree value={item} /></dd></div>)}</dl> : <span className="subtle">None reported</span>;
  }
  if (typeof value === "string" && /^https:\/\/[^\s]+$/.test(value)) {
    return <a href={value} target="_blank" rel="noopener noreferrer">{value} ↗</a>;
  }
  return <span className="trial-field-value">{text(value)}</span>;
}

export default function TrialFields({ row, onClose, standalone = false }: { row: Candidate; onClose?: () => void; standalone?: boolean }) {
  const nct = trialId(row);
  const [study, setStudy] = useState<{ [key: string]: Json } | null>(null);
  const [fetchedAt, setFetchedAt] = useState("");
  const [loading, setLoading] = useState(Boolean(nct));
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [section, setSection] = useState(standalone ? "all-sections" : "reported-statistics");
  const [raw, setRaw] = useState(false);

  useEffect(() => {
    if (!nct) return;
    const controller = new AbortController();
    async function load() {
      setLoading(true); setError("");
      try {
        const linkResponse = await fetch("/api/full-trials/" + nct, { cache: "no-store", signal: controller.signal });
        if (!linkResponse.ok) throw new Error("The saved full trial record is temporarily unavailable.");
        const link = await linkResponse.json() as { url: string };
        const response = await fetch(link.url, { credentials: "omit", cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error("Unable to load the complete trial record. Try again.");
        const value = await response.json() as { [key: string]: Json };
        if (object(object(value.protocolSection).identificationModule).nctId !== nct) throw new Error("Trial identity could not be verified.");
        if (!controller.signal.aborted) {
          setStudy(value); setFetchedAt(response.headers.get("X-Record-Fetched-At") || "");
        }
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Unable to load trial fields.");
      } finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void load();
    return () => controller.abort();
  }, [nct, retry]);

  const sections = useMemo(() => study ? registrySections(study) : [], [study]);
  const analyses = useMemo(() => study ? reportedAnalyses(study) : [], [study]);
  const active = sections.find(item => item.id === section);
  const identification = object(object(study?.protocolSection).identificationModule);
  const studyTitle = typeof identification.briefTitle === "string" ? identification.briefTitle : nct;
  function downloadRecord() {
    if (!study) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(study, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = nct + "-all-fields.json";
    anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <section className="trial-full-details" aria-label={"All fields for " + (nct || row.programId || row.id)}>
    <div className="sectionhead"><div><h3>{standalone ? studyTitle : row.ticker + " · " + (row.drug || row.company || nct)}</h3>
      <p className="subtle">{!standalone && row.programId && <strong>{row.programId} · </strong>}{nct ? nct : "Regulatory / source program"}</p></div>
      <div className="pipeline-actions">
        {study && <button type="button" className="secondary" onClick={downloadRecord}>Download this record · JSON</button>}
        {nct && <a href={"https://clinicaltrials.gov/study/" + nct} target="_blank" rel="noopener noreferrer">Registry source ↗</a>}
        {!standalone && onClose && <button type="button" className="secondary" onClick={onClose}>Close details</button>}
      </div>
    </div>
    {loading && <p role="status">Loading all saved registry fields…</p>}
    {error && <div role="alert"><p className="error">{error}</p><button type="button" className="secondary" onClick={() => setRetry(value => value + 1)}>Retry full record</button></div>}
    {!nct && <p className="subtle">No exact NCT trial is linked to this program. Its available Pipeline fields are listed below.</p>}
    {study && <>
      <div className="trial-section-picker"><label htmlFor="pipeline-trial-section">Browse all registry fields</label>
        <select id="pipeline-trial-section" value={section} onChange={event => { setSection(event.target.value); setRaw(false); }}>
          {standalone && <option value="all-sections">All trial sections · {sections.length}</option>}
          <option value="reported-statistics">Reported p-values · {analyses.length}</option>
          {sections.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select>
        {fetchedAt && <span className="subtle">Saved {new Date(fetchedAt).toLocaleString()}</span>}
      </div>
      {section === "all-sections" ? <div className="trial-all-sections">
        <p className="subtle">Complete saved ClinicalTrials.gov record, grouped by registry section. Expand any module to view every saved field. Unavailable fields are not inferred.</p>
        {sections.map((item, index) => <details key={item.id} className="trial-full-module"
          open={index === 0}>
          <summary>{item.title}</summary><FieldTree value={item.data} />
        </details>)}
      </div> : section === "reported-statistics" ? <div className="trial-statistics">
        <h4>Reported p-values with endpoints and comparison groups</h4>
        {analyses.length ? <div className="table-scroll"><table><thead><tr><th>Endpoint</th><th>Type / time frame</th><th>Comparison groups</th><th>p-value</th><th>Method</th><th>All analysis fields</th></tr></thead>
          <tbody>{analyses.map(item => <tr key={item.outcomeIndex + "-" + item.analysisIndex}>
            <td>{text(item.endpoint)}<small>Outcome {item.outcomeIndex} · analysis {item.analysisIndex}</small></td>
            <td>{text(item.type)}<small>{text(item.timeFrame)}</small></td><td>{item.groups.map(text).join(" vs ") || "Not reported"}</td>
            <td><strong>{text(item.pValue)}</strong></td><td>{text(item.method)}</td>
            <td><FieldBranch value={item.analysis} index={item.analysisIndex - 1} /></td>
          </tr>)}</tbody></table></div> : <p className="subtle">{study.hasResults ? "Results are posted, but no p-values were reported in their statistical analyses." : "No posted result p-values are available for this trial."}</p>}
      </div> : active && <section className="trial-section-fields" aria-label={active.title} key={active.id}><h4>{active.title}</h4><FieldTree value={active.data} /></section>}
      <label className="trial-raw-toggle"><input type="checkbox" checked={raw} onChange={event => setRaw(event.target.checked)} />Show complete original registry JSON</label>
      {raw && <pre className="trial-raw-json">{JSON.stringify(study, null, 2)}</pre>}
    </>}
    {!standalone && <details className="trial-source-fields" open={!nct}><summary>All Pipeline program fields</summary><FieldTree value={row as unknown as Json} /></details>}
  </section>;
}
