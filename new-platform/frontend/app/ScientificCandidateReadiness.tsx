"use client";

import { useEffect, useState } from "react";
import { isScientificCandidates, object, scientificCount, scientificTime, sourceUrl, type CandidateSummary, type ScientificCandidates } from "../lib/scientific-candidates";

const label = (key: string) => key.replaceAll("_", " ").replace(/\b\w/g, ch => ch.toUpperCase());

function EvidenceValue({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null || value === undefined || value === "") return <span>Missing / not independently established</span>;
  if (typeof value === "string") {
    const url = sourceUrl(value);
    return url ? <a href={url} target="_blank" rel="noopener noreferrer">{value} ↗</a> : <span>{value}</span>;
  }
  if (typeof value === "number" || typeof value === "boolean") return <span>{String(value)}</span>;
  if (Array.isArray(value)) return value.length ? <ol>{value.map((entry, index) =>
    <li key={index}><EvidenceValue value={entry} depth={depth + 1} /></li>)}</ol> : <span>No evidence recorded</span>;
  if (object(value) && depth < 8) return <dl style={{ margin: "8px 0", overflowWrap: "anywhere" }}>
    {Object.entries(value).map(([key, entry]) => <div key={key} style={{ margin: "8px 0" }}>
      <dt style={{ fontWeight: 600 }}>{label(key)}</dt><dd style={{ marginLeft: 16 }}><EvidenceValue value={entry} depth={depth + 1} /></dd>
    </div>)}
  </dl>;
  return <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(value, null, 2)}</pre>;
}

function CandidateDossier({ candidate }: { candidate: CandidateSummary }) {
  const [open, setOpen] = useState(false);
  const [dossier, setDossier] = useState<Record<string, unknown> | null>(null);
  const [message, setMessage] = useState("Expand to retrieve this trial’s persisted evidence dossier.");
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setDossier(null);
    setMessage("Loading persisted evidence dossier…");
    fetch("/api/scientific-candidates/" + candidate.nct_id, { cache: "no-store", signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error(response.status === 401 ? "Sign-in expired. Sign in again." : "The saved dossier could not be verified.");
        const data: unknown = await response.json();
        if (!object(data)) throw new Error("Incomplete dossier response.");
        if (!controller.signal.aborted) { setDossier(data); setMessage(""); }
      }).catch(error => {
        if (!controller.signal.aborted) { setDossier(null); setMessage(String(error.message || error)); }
      });
    return () => controller.abort();
  }, [open, candidate.nct_id]);
  return <details onToggle={event => setOpen(event.currentTarget.open)} style={{ borderTop: "1px solid #a8b4aa", padding: "10px 0" }}>
    <summary style={{ cursor: "pointer", fontWeight: 700 }}>{candidate.nct_id} · {candidate.readiness} · {candidate.products.join(", ") || "Product unresolved"}</summary>
    <p>{candidate.explanation}</p>
    <p><strong>Sponsor:</strong> {candidate.sponsor || "Unresolved"}<br /><strong>Indication:</strong> {candidate.indications.join("; ") || "Unresolved"}<br />
      <strong>Last checked:</strong> {scientificTime(candidate.last_verified)}</p>
    {message ? <p role="status">{message}</p> : null}
    {dossier ? <EvidenceValue value={dossier} /> : null}
  </details>;
}

export default function ScientificCandidateReadiness() {
  const [open, setOpen] = useState(false);
  const [report, setReport] = useState<ScientificCandidates | null>(null);
  const [message, setMessage] = useState("Expand to load persisted candidate investigations and readiness counts.");
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setReport(null);
    setMessage("Loading scientific candidate readiness…");
    fetch("/api/scientific-candidates", { cache: "no-store", signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error(response.status === 401 ? "Sign-in expired. Sign in again." : "Saved readiness results are unavailable; no counts can be confirmed.");
        const data: unknown = await response.json();
        if (!isScientificCandidates(data)) throw new Error("Readiness counts or provenance are incomplete; no results inferred.");
        if (!controller.signal.aborted) { setReport(data); setMessage(""); }
      }).catch(error => {
        if (!controller.signal.aborted) { setReport(null); setMessage(String(error.message || error)); }
      });
    return () => controller.abort();
  }, [open]);
  const metrics = report ? [
    ["Candidates identified", report.candidates_identified], ["Candidates independently checked", report.candidates_independently_checked],
    ["READY", report.ready], ["RELUCTANT", report.reluctant], ["NOT READY", report.not_ready],
    ["Regulatory identifiers verified", report.regulatory_identifiers_verified], ["Regulatory identifiers unresolved", report.regulatory_identifiers_unresolved],
    ["Full scientific investigations completed", report.full_scientific_investigations_completed], ["Scientific dossiers created", report.scientific_dossiers_created],
  ] as const : [];
  return <section className="panel" aria-label="Scientific candidate readiness">
    <details onToggle={event => setOpen(event.currentTarget.open)}>
      <summary style={{ cursor: "pointer", fontWeight: 800 }}>SCIENTIFIC CANDIDATE READINESS</summary>
      {message ? <p role="status">{message}</p> : null}
      {report ? <>
        <p>Saved verification status: <strong>{report.status}</strong>. Last checked: {scientificTime(report.last_verified)}.</p>
        <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
          {metrics.map(([title, count]) => <div key={title}><dt>{title}</dt><dd style={{ margin: "4px 0", fontWeight: 700 }}>{scientificCount(count)}</dd></div>)}
        </dl>
        <p className="subtle">READY, RELUCTANT and NOT READY describe evidence readiness. They are not approval predictions. A readiness category or a dossier does not mean the existing 40 assessments are complete. No filters, list memberships or trading controls are activated here.</p>
        <details><summary>Regulatory identifier reconciliation</summary>
          {report.regulatory_identifiers.length ? report.regulatory_identifiers.map((identifier, index) =>
            <article key={identifier.associated_nct_id + identifier.identifier + index} style={{ borderTop: "1px solid #a8b4aa", padding: 10 }}>
              <h3>{identifier.identifier} · {identifier.status}</h3>
              <p>{identifier.associated_nct_id} · {identifier.sponsor} · {identifier.products.join(", ")}</p>
              <p>Last checked: {scientificTime(identifier.verified_at)}</p><EvidenceValue value={identifier.evidence} />
            </article>) : <p>No persisted reconciliation results are available.</p>}
        </details>
        <details><summary>Per-trial dossiers and source evidence ({report.candidates.length})</summary>
          {report.candidates.map(candidate => <CandidateDossier key={candidate.nct_id} candidate={candidate} />)}
        </details>
      </> : null}
    </details>
  </section>;
}
