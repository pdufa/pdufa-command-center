import snapshot from "../../lib/fda-holdout-reconstruction-snapshot.json";

export const dynamic = "force-static";

export default function FdaResearchStatusPage() {
  if (snapshot.researchOnly !== true || snapshot.tradingAuthorized !== false || snapshot.validatedCases !== 0) {
    throw new Error("Research status safety contract violated");
  }
  return (
    <main style={{ maxWidth: 1080, margin: "2rem auto", padding: "1rem", color: "#173126" }}>
      <h1>FDA SCIENCE / OUTCOME — Historical Research</h1>
      <p style={{ background: "#fff3d4", padding: 16, border: "1px solid #8a6c24" }}>
        Research reconstruction only. Original prediction timestamps and independently authenticated source
        evidence are missing. No validated accuracy, approval probability, or authorization to trade.
      </p>
      <p>Research snapshot: {snapshot.asOf} · Historical cases: {snapshot.caseReports.length} · Validated predictions: 0</p>
      <p><a href="/" style={{ textDecoration: "underline" }}>Return to dashboard</a></p>
      {snapshot.caseReports.map((row) => (
        <details key={row.event_key} style={{ marginBottom: 12, background: "#f1f8f2", border: "1px solid #9fb7a5", padding: 14 }}>
          <summary style={{ cursor: "pointer", fontWeight: 700 }}>
            {row.event_key} · SCIENCE: NOT VERIFIED · OUTCOME: ABSTAIN · READY: NO
          </summary>
          <p>Application: {row.application_id ?? "Unverified"} · Reconstruction cutoff: {row.reconstruction_cutoff}</p>
          <p>SCIENCE: {row.scientific_dossier.summary.independently_completed_assessments}/40 independently completed assessments; {row.scientific_dossier.summary.independently_completed_depth_levels}/20 independently completed depth levels.</p>
          <p>OUTCOME: No approval probability or PASS/FAIL grade. Reluctant grade: insufficient verified evidence.</p>
          <p>Original prediction cutoff: not authenticated. Evidence blockers:</p>
          <ul>{row.blockers.slice(0, 6).map((reason) => <li key={reason}>{reason.replaceAll("_", " ")}</li>)}</ul>
          <p>Missing source documents: {row.missing_documents.length}. This record cannot be used for validated model training.</p>
        </details>
      ))}
    </main>
  );
}
