import Link from "next/link";
import snapshot from "../../lib/fda-holdout-reconstruction-snapshot.json";
import { auditHoldoutReconstruction } from "../../lib/fda-holdout-reconstruction";

export const dynamic = "force-static";

/**
 * Research preview only. The historical holdout cases are NOT represented as
 * current eligible Phase 3/GEM JR/GEM/WT trials. A real source-backed live
 * candidate feed and prediction job API must be connected before START runs.
 */
export default function PredictionsPage() {
  const report = auditHoldoutReconstruction(snapshot);
  return (
    <main style={{maxWidth: 1100, margin: "2rem auto", padding: 20, color: "#173126"}}>
      <h1>PREDICTIONS</h1>
      <p style={{background: "#fff3d4", border: "1px solid #8a6c24", padding: 16}}>
        Research preview — not a live prediction service or authorization to trade.
        No calibrated PASS / CRL / EXTENSION probabilities are available.
      </p>
      <p><Link href="/">Dashboard</Link> · <Link href="/fda-research-status">Historical science research</Link></p>
      <section style={{background: "#f1f8f2", border: "1px solid #9fb7a5", padding: 18}}>
        <h2>Choose eligible trial</h2>
        <label htmlFor="eligible-trials">Phase 3 data released / GEM JR / GEM / WT</label><br/>
        <select id="eligible-trials" disabled aria-label="Eligible trial list not connected"
          style={{padding: 10, width: "100%", maxWidth: 620}}>
          <option>Live eligible trial feed not connected</option>
        </select>
        <p><button disabled style={{padding: "10px 18px"}}>START PREDICTION</button></p>
        <p>Connect verified trial source records and a persistent prediction worker to enable this action.
          Existing Pipeline/GEM JR/GEM/WT filters and FS/FA presets remain unchanged.</p>
      </section>
      <h2>Scientific assessment checklist — historical research examples</h2>
      <p>These are retrospective research dossiers, not currently eligible trials or prospective predictions.
        Expand a case and scientific layer to inspect the existing 40 assessment questions.</p>
      {report.caseReports.map((row) => (
        <details key={row.event_key} style={{border: "1px solid #9fb7a5", padding: 14, marginBottom: 12}}>
          <summary style={{cursor: "pointer", fontWeight: 700}}>
            {row.event_key} — 0/40 independently completed · ABSTAIN
          </summary>
          <p>Readiness: NOT READY · 50-level investigation: 0/50 independently completed</p>
          <progress value={0} max={40} aria-label="Independently completed scientific assessments" />
          {row.scientific_dossier.layers.map((layer) => (
            <details key={layer.layer} style={{margin: "12px 0", padding: 10, background: "#f1f8f2"}}>
              <summary>{layer.layer}. {layer.layer_name} — {layer.independently_completed_assessments}/5 independently assessed</summary>
              <ol>{layer.questions.map((q) => (
                <li key={q.question_id} style={{margin: "12px 0"}}>
                  <details><summary>{q.question_id}: {q.question} — NOT VERIFIED</summary>
                    <p>Required evidence: {q.required_evidence}</p>
                    <p>Scientific rationale: {q.scientific_rationale}</p>
                    <p>Independent assessment: NOT COMPLETED. Confidence: NOT ESTABLISHED.</p>
                    {q.observations.map(s => <p key={s.source_id}><a href={s.source_url} target="_blank" rel="noopener noreferrer">{s.source_id} ↗</a> — Research observation only, not independently verified.</p>)}
                  </details>
                </li>
              ))}</ol>
            </details>
          ))}
        </details>
      ))}
    </main>
  );
}
