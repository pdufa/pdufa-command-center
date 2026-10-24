import { scoreAuditView } from "../lib/scoring-audit";
import { scoringGapGuidance } from "../lib/scoring-gap-guidance";

/** Original, dated read-only evidence ledger. Never calculates approval, trading,
 * investment readiness, or Gemini-style stage qualifications. */
export default function ScoringInputGapsPanel({ report }: { report: unknown }) {
  const parsed = scoreAuditView(report);
  if (!parsed) return <section className="source-health" aria-label="Nightly scoring evidence status">
    <strong>Scoring inputs: Not verified</strong>
    <p className="subtle">A valid scoring-input audit has not been published or could not be read.
      Missing values are not scores or zero-percent probabilities.</p>
  </section>;
  const {audit, freshness} = parsed;
  const unresolved = audit.checks.filter(check => check.Status === "DATA GAP" || check.Status === "REVIEW");
  const clear = audit.status === "NO_INPUT_GAPS_FOUND" && freshness === "CURRENT";
  return <section className="source-health" aria-label="Nightly scoring evidence status">
    <strong>Scoring-input audit: {audit.status.replaceAll("_", " ")} · {audit.counts.data_gaps} data gaps</strong>
    <p role="status">{freshness === "CURRENT" ? "Saved audit is within 48 hours of publication." :
      freshness === "STALE" ? "Saved audit is older than 48 hours. A new audit is required." :
      "Audit publication time could not be verified. Treat all findings as unverified."}</p>
    <p className="subtle">Audit timestamp: {audit.generated_at_utc} · Source scan #{audit.source_scan.run_id}
      {" "}({audit.source_scan.conclusion}). This is a saved-input inspection, not evidence of complete fresh scan artifacts.</p>
    {!clear && <p className="risk-line">These missing inputs remain REVIEW REQUIRED. Do not substitute stock averages,
      inferred FDA probabilities, invented financing PASS values, or missing-as-zero figures.</p>}
    <details className="nested-expander">
      <summary>Show scoring evidence checks · {unresolved.length} needing attention / {audit.checks.length} inspected</summary>
      <ul>{audit.checks.map((item, i) => {
        const guide = scoringGapGuidance(item);
        return <li key={item.Test + i}>
          <strong>{item.Test} — {item.Status}</strong>
          <p>{item.Result}</p><p className="subtle">{item["Why it matters"]}</p>
          {guide && <div aria-label={"Evidence needed for " + item.Test}>
            <p><strong>Next evidence check:</strong> {guide.nextCheck}</p>
            <p className="subtle">{guide.caveat}</p>
            <p><a href={guide.datasetUrl} target="_blank" rel="noopener noreferrer">
              OPEN SAVED INPUT DATASET ↗ ({guide.dataset})</a></p>
          </div>}
        </li>;
      })}</ul>
      <p className="subtle">{audit.provenance_note}</p>
      <p><a target="_blank" rel="noopener noreferrer"
        href={"https://github.com/pdufa/pdufa-command-center/actions/runs/" + audit.source_scan.run_id}>
        OPEN ORIGINAL NIGHTLY SCAN RUN ↗</a></p>
    </details>
  </section>;
}
