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
          <details><summary>Eight scientific layers · 40 questions and evidence status</summary>
            {row.scientific_dossier.layers.map((layer) => (
              <details key={layer.layer} style={{ margin: "10px 0", padding: 10, border: "1px solid #bfd0c0" }}>
                <summary><strong>{layer.layer}. {layer.layer_name}</strong> · {layer.questions_with_research_observations}/5 questions with research observations · {layer.independently_completed_assessments}/5 independently assessed</summary>
                <ol start={(layer.layer - 1) * 5 + 1}>
                  {layer.questions.map((question) => (
                    <li key={question.question_id} style={{ marginBottom: 12 }}>
                      <strong>{question.question_id}: {question.question}</strong>
                      <div>Evidence: {question.research_status === "RESEARCH_OBSERVATION_ONLY" ? "Research observation only — not verified" : "Missing predecision source"} · Independent assessment: NOT COMPLETED</div>
                      <div>Required: {question.required_evidence}</div>
                      {question.observations.length > 0 && <details><summary>{question.observations.length} research source observation(s)</summary><ul>{question.observations.map((source) => <li key={source.source_id}>{source.source_id} · {source.available_on} · <a href={source.source_url} target="_blank" rel="noopener noreferrer">Source document ↗</a> · Not independently reviewed</li>)}</ul></details>}
                      {question.excluded_or_quarantined_sources.length > 0 && <div>Excluded or quarantined sources: {question.excluded_or_quarantined_sources.map((source) => source.reason).join(", ")}</div>}
                    </li>
                  ))}
                </ol>
              </details>
            ))}
          </details>
          <details><summary>20 investigation depth levels · independent review status</summary>
            <p>All levels require independently authenticated evidence and review; an observation alone never completes a level.</p>
            <ol>
              {row.scientific_dossier.depth_framework.levels.map((level) => (
                <li key={level.depth_level}>Level {level.depth_level}: {level.status.replaceAll("_", " ")} · {level.independently_reviewed_question_ids.length} independently reviewed questions</li>
              ))}
            </ol>
          </details>
          <p>OUTCOME: No approval probability or PASS/FAIL grade. Reluctant grade: insufficient verified evidence.</p>
          <p>Original prediction cutoff: not authenticated. Evidence blockers:</p>
          <ul>{row.blockers.slice(0, 6).map((reason) => <li key={reason}>{reason.replaceAll("_", " ")}</li>)}</ul>
          <details><summary>Missing documents · independent-review worklist ({row.missing_documents.length})</summary>
            <ol>{row.missing_documents.map((document, index) => <li key={index}>{document}</li>)}</ol>
            <p>Completion requires original document bytes, authenticated publication timing, application/cycle binding, source hashes, independent scientific review, and a proven predecision prediction freeze.</p>
          </details>
          <details><summary>All validation blockers ({row.blockers.length})</summary>
            <ol>{row.blockers.map((reason) => <li key={reason}>{reason.replaceAll("_", " ")}</li>)}</ol>
          </details>
          <p>Missing source documents: {row.missing_documents.length}. This record cannot be used for validated model training.</p>
        </details>
      ))}
    </main>
  );
}
